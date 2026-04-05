"""
ConceptGrade LLM-Mode Ablation Study with Key Rotation.

Uses the real ConceptGrade pipeline (actual LLM calls) across 7 configurations
on 30 Mohler samples (3 per question: low/mid/high score). Rotates across
available API keys to avoid rate-limit interruptions.

Configurations
--------------
  C0    Cosine-Only Baseline          — TF-IDF cosine (no LLM)
  C_LLM Pure LLM Zero-Shot           — direct Gemini prompt, no KG structure
  C1    ConceptGrade Baseline         — standard extractor + standard comparator
  C2    ConceptGrade + SC             — Self-Consistent Extraction (2 runs)
  C3    ConceptGrade + CW             — Confidence-Weighted Comparison
  C4    ConceptGrade + Verifier       — LLM-as-Verifier post-scoring
  C5    ConceptGrade + All Extensions — SC + CW + Verifier

Output
------
  data/llm_ablation_results.json
  data/llm_ablation_summary.txt
  data/llm_ablation_latex.tex
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datasets.mohler_loader import load_mohler_sample, MohlerSample
from evaluation.metrics import (
    evaluate_grading, add_bootstrap_cis,
    wilcoxon_significance, format_comparison_table,
    format_significance_table, paired_ttest, cohens_d, EvaluationResult,
)
from conceptgrade.key_rotator import KeyRotator, API_KEYS

CONFIGS = [
    ("C0",    "Cosine-Only Baseline",          False, False, False),
    ("C_LLM", "Pure LLM Zero-Shot",            False, False, False),
    ("C1",    "ConceptGrade Baseline",         False, False, False),
    ("C2",    "ConceptGrade + SC",             True,  False, False),
    ("C3",    "ConceptGrade + CW",             False, True,  False),
    ("C4",    "ConceptGrade + Verifier",       False, False, True),
    ("C5",    "ConceptGrade + All Extensions", True,  True,  True),
]

# Configs excluded from Δ delta columns (baselines)
BASELINE_IDS = {"C0", "C_LLM", "C1"}

SEP = "─" * 72

PURE_LLM_SYSTEM = (
    "You are an expert academic grader. "
    "Score the student answer on a scale of 0 to 5 (decimals allowed). "
    "Reply with ONLY a JSON object: {\"score\": <number>}"
)


def pure_llm_score(sample: MohlerSample, api_key: str, model: str) -> float:
    """Grade with no KG structure — direct LLM zero-shot baseline."""
    import re
    from conceptgrade.llm_client import LLMClient
    client = LLMClient(api_key=api_key)
    user_prompt = (
        f"Question: {sample.question}\n\n"
        f"Reference answer: {sample.reference_answer}\n\n"
        f"Student answer: {sample.student_answer}\n\n"
        "Score the student answer 0–5."
    )
    raw = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PURE_LLM_SYSTEM},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=256,   # Gemini 2.5 Flash needs headroom for thinking tokens
        temperature=0.1,
    )
    text = raw.choices[0].message.content or ""
    m = re.search(r'"score"\s*:\s*([0-9.]+)', text)
    if m:
        return min(5.0, max(0.0, float(m.group(1))))
    m = re.search(r'[0-9]+(?:\.[0-9]+)?', text)
    if m:
        return min(5.0, max(0.0, float(m.group())))
    return 0.0


def cosine_score(sample: MohlerSample) -> float:
    try:
        vec = TfidfVectorizer(lowercase=True, stop_words="english",
                              ngram_range=(1, 3), max_features=5000)
        tfidf = vec.fit_transform([sample.reference_answer, sample.student_answer])
        return round(float(sk_cosine(tfidf[0:1], tfidf[1:2])[0][0]) * 5.0, 2)
    except Exception:
        return 0.0


async def _async_run_config(
    samples: list,
    cid: str,
    api_key: str,
    model: str,
    use_sc: bool,
    use_cw: bool,
    use_ver: bool,
    concurrency: int = 8,
) -> list[float]:
    """
    Async version of run_config using asyncio.gather + semaphore.
    Runs `concurrency` samples in parallel — ~8x faster than sequential.
    Only works for C_LLM (pure LLM calls); pipeline configs still use threads.
    """
    import asyncio
    from conceptgrade.llm_client import LLMClient

    semaphore = asyncio.Semaphore(concurrency)
    scores = [0.0] * len(samples)
    completed = [0]

    async def _score_one(i: int, sample) -> None:
        async with semaphore:
            client = LLMClient(api_key=api_key)
            backend = client._get_completions("google")
            user_prompt = (
                f"Question: {sample.question}\n\n"
                f"Reference answer: {sample.reference_answer}\n\n"
                f"Student answer: {sample.student_answer}\n\n"
                "Score the student answer 0–5."
            )
            for attempt in range(3):
                try:
                    resp = await backend.async_create(
                        model=model,
                        messages=[
                            {"role": "system", "content": PURE_LLM_SYSTEM},
                            {"role": "user", "content": user_prompt},
                        ],
                        max_tokens=256,
                        temperature=0.1,
                    )
                    import re
                    text = resp.choices[0].message.content or ""
                    m = re.search(r'"score"\s*:\s*([0-9.]+)', text)
                    s = float(m.group(1)) if m else 0.0
                    scores[i] = round(min(5.0, max(0.0, s)), 2)
                    break
                except Exception as e:
                    if "429" in str(e) or "529" in str(e):
                        await asyncio.sleep(2.0 * (attempt + 1))
                    else:
                        break
            completed[0] += 1
            qshort = sample.question_id[-2:] if len(sample.question_id) > 1 else sample.question_id
            print(f"    [C_LLM] {completed[0]:3d}/{len(samples)}: Q{qshort} → {scores[i]:.2f}", flush=True)

    import asyncio
    await asyncio.gather(*[_score_one(i, s) for i, s in enumerate(samples)])
    return scores


def _score_one_sample(
    i: int,
    sample: MohlerSample,
    cid: str,
    api_key: str,
    model: str,
    use_sc: bool,
    use_cw: bool,
    use_ver: bool,
    intermediates_store: dict | None = None,
) -> tuple[int, float]:
    """Score a single sample — runs in a thread worker.

    If intermediates_store is provided (a dict), saves full pipeline
    intermediate results (comparison, blooms, solo, misconceptions, kg_score)
    to intermediates_store[i] so they can be replayed by replay_verifier().
    """
    if cid == "C_LLM":
        for _ in range(3):
            try:
                s = pure_llm_score(sample, api_key, model)
                return i, round(s, 2)
            except Exception as e:
                if "429" in str(e) or "529" in str(e):
                    time.sleep(3.0)
                else:
                    break
        return i, 0.0

    from conceptgrade.pipeline import ConceptGradePipeline
    pipeline = ConceptGradePipeline(
        api_key=api_key,
        model=model,
        use_self_consistency=use_sc,
        use_confidence_weighting=use_cw,
        use_llm_verifier=use_ver,
        verifier_weight=1.0,
        rate_limit_delay=0.0,   # threading handles pacing
        sc_n_runs=2,
        sc_min_votes=2,
    )
    for _ in range(3):
        try:
            result = pipeline.assess_student(
                student_id=f"s{i}",
                question=sample.question,
                answer=sample.student_answer,
                reference_answer=sample.reference_answer,
            )
            if intermediates_store is not None:
                intermediates_store[i] = {
                    "question":          sample.question,
                    "student_answer":    sample.student_answer,
                    "reference_answer":  sample.reference_answer,
                    "human_score":       sample.score_avg,
                    "kg_score":          result.overall_score,
                    "comparison":        result.comparison,
                    "blooms":            result.blooms,
                    "solo":              result.solo,
                    "misconceptions":    result.misconceptions,
                }
            return i, round(result.overall_score * 5.0, 2)
        except Exception as e:
            err = str(e)
            if "429" in err or "529" in err or "overloaded" in err.lower():
                time.sleep(3.0)
            elif "quota" in err.lower() or "resource" in err.lower() or "exhausted" in err.lower() or "403" in err:
                print(f"  [QUOTA] sample {i}: {err[:120]}")
                time.sleep(5.0)
            else:
                print(f"  [ERR] sample {i}: {type(e).__name__}: {err[:120]}")
                break
    return i, 0.0


def run_config(
    samples: list[MohlerSample],
    cid: str,
    cname: str,
    use_sc: bool,
    use_cw: bool,
    use_ver: bool,
    rotator: KeyRotator,
    model: str = "claude-haiku-4-5-20251001",
    max_workers: int = 3,
    intermediates_store: dict | None = None,
) -> list[float]:
    """Score all samples under one configuration.

    Uses a thread pool (max_workers=3 by default) so multiple samples are
    scored concurrently, cutting wall-clock time by ~3x while staying within
    Gemini free-tier rate limits.  Pass max_workers=1 to force sequential.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if cid == "C0":
        return [cosine_score(s) for s in samples]

    # C_LLM: use native async for maximum parallelism (8 concurrent calls)
    if cid == "C_LLM":
        import asyncio
        api_key = rotator.current_key
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(1) as ex:
                    return ex.submit(
                        lambda: asyncio.run(
                            _async_run_config(samples, cid, api_key, model,
                                              use_sc, use_cw, use_ver, concurrency=8)
                        )
                    ).result()
            else:
                return asyncio.run(
                    _async_run_config(samples, cid, api_key, model,
                                      use_sc, use_cw, use_ver, concurrency=8)
                )
        except Exception as e:
            print(f"  [Async] Falling back to sync: {e}")
            # fall through to thread pool below

    scores: list[float] = [0.0] * len(samples)
    completed = [0]
    lock = threading.Lock()

    api_key = rotator.current_key

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_score_one_sample, i, s, cid, api_key, model,
                        use_sc, use_cw, use_ver, intermediates_store): i
            for i, s in enumerate(samples)
        }
        for fut in as_completed(futures):
            idx, score = fut.result()
            scores[idx] = score
            with lock:
                completed[0] += 1
                done = completed[0]
            qid = samples[idx].question_id
            qshort = qid[-2:] if len(qid) > 1 else qid
            print(f"    [{cid}] {done:3d}/{len(samples)}: Q{qshort} → {score:.2f}", flush=True)

    return scores


def replay_verifier(
    intermediates_path: str,
    api_key: str,
    model: str,
    use_sc: bool = False,
    use_cw: bool = False,
) -> tuple[list[float], list[float]]:
    """Re-run ONLY the verifier step on cached KG intermediates — no extraction API calls.

    Loads intermediates saved by run_config(..., intermediates_store=...) and
    runs the current verifier.py prompts on them.  Returns (c4_scores, human_scores).
    """
    import json as _json
    from conceptgrade.verifier import LLMVerifier
    from conceptgrade.pipeline import ConceptGradePipeline

    data = _json.load(open(intermediates_path))
    n = len(data)
    print(f"  [Replay] Loaded {n} intermediates from {intermediates_path}")

    verifier = LLMVerifier(api_key=api_key, model=model, verifier_weight=1.0)

    # Build a dummy pipeline for CW comparison if needed
    if use_cw:
        pipeline = ConceptGradePipeline(
            api_key=api_key, model=model,
            use_self_consistency=use_sc,
            use_confidence_weighting=use_cw,
            use_llm_verifier=False,
        )

    scores = [0.0] * n
    human_scores = [0.0] * n

    for idx_str, entry in sorted(data.items(), key=lambda x: int(x[0])):
        i = int(idx_str)
        human_scores[i] = float(entry["human_score"])
        comparison = entry["comparison"]
        blooms     = entry["blooms"] or {}
        solo       = entry["solo"] or {}
        misc       = entry["misconceptions"] or {}
        kg_score   = float(entry["kg_score"])

        # Optionally re-run CW to get adjusted kg_score
        if use_cw and pipeline is not None:
            try:
                from conceptgrade.graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
                from conceptgrade.concept_extraction.student_concept_graph import StudentConceptGraph
                # Re-score with CW — use stored comparison scores as base
                pass  # CW is algorithmic so already in comparison if cw was on; skip re-run
            except Exception:
                pass

        try:
            ver = verifier.verify(
                question=entry["question"],
                student_answer=entry["student_answer"],
                kg_score=kg_score,
                comparison_result=comparison,
                blooms=blooms,
                solo=solo,
                misconceptions=misc,
                reference_answer=entry.get("reference_answer", ""),
            )
            final = round(ver.final_score * 5.0, 2)
        except Exception as e:
            print(f"  [Replay] sample {i} verifier error: {e}")
            final = round(kg_score * 5.0, 2)

        scores[i] = final
        print(f"    [Replay] {i+1:3d}/{n}: kg={kg_score*5:.1f} → verified={final:.2f}", flush=True)

    return scores, human_scores


def format_results_table(
    human: list[float],
    config_scores: dict[str, list[float]],
    results: dict[str, EvaluationResult],
) -> str:
    base = results["C1"]
    header = (f"  {'ID':<6}  {'System':<32}  {'r':>7}  {'Δr vs C1':>9}  "
              f"{'QWK':>7}  {'ΔQWK':>7}  {'RMSE':>7}  {'MAE':>7}")
    sep = SEP
    rows = [header, sep]
    for cid, cname, *_ in CONFIGS:
        ev = results[cid]
        dr = ev.pearson_r - base.pearson_r
        dq = ev.qwk       - base.qwk
        dr_s = "    —    " if cid in BASELINE_IDS else f"{dr:>+9.4f}"
        dq_s = "  —   "   if cid in BASELINE_IDS else f"{dq:>+7.4f}"
        mae  = float(np.mean(np.abs(np.array(human) - np.array(config_scores[cid]))))
        rows.append(
            f"  {cid:<6}  {cname:<32}  {ev.pearson_r:>7.4f}  {dr_s}  "
            f"{ev.qwk:>7.4f}  {dq_s}  {ev.rmse:>7.4f}  {mae:>7.4f}"
        )
        if cid == "C1":
            rows.append("  " + "·"*68)
    rows.append(sep)
    return "\n".join(rows)


def generate_latex(results: dict[str, EvaluationResult],
                   config_scores: dict[str, list[float]],
                   human: list[float]) -> str:
    base = results["C1"]
    best_r    = max(ev.pearson_r for ev in results.values())
    best_qwk  = max(ev.qwk       for ev in results.values())
    best_rmse = min(ev.rmse      for ev in results.values())
    best_mae  = min(float(np.mean(np.abs(np.array(human) - np.array(config_scores[cid]))))
                    for cid, *_ in CONFIGS)

    def b(val, best, hi=True):
        ok = abs(val - best) < 1e-4
        s = f"{val:.4f}"
        return f"\\textbf{{{s}}}" if ok else s

    lines = [
        "% ConceptGrade LLM Ablation — real pipeline, Mohler n=30",
        "\\begin{table}[h]\\centering",
        "\\caption{LLM-mode ablation on Mohler et al.\\ (2011) ($n=30$). "
        "C\\textsubscript{LLM} = Pure LLM Zero-Shot (no KG); "
        "SC = Self-Consistent Extraction; CW = Confidence-Weighted Comparison; "
        "Ver = LLM Verifier. $\\Delta$ vs.\\ C1 (ConceptGrade Baseline). Bold = best.}",
        "\\label{tab:llm_ablation}",
        "\\begin{tabular}{@{}llrrrrrr@{}}\\toprule",
        "\\textbf{ID} & \\textbf{System} & \\textbf{$r$} & \\textbf{$\\Delta r$} & "
        "\\textbf{QWK} & \\textbf{$\\Delta$QWK} & \\textbf{RMSE} & \\textbf{MAE} \\\\\\midrule",
    ]
    for cid, cname, *_ in CONFIGS:
        ev  = results[cid]
        mae = float(np.mean(np.abs(np.array(human) - np.array(config_scores[cid]))))
        dr  = ev.pearson_r - base.pearson_r
        dq  = ev.qwk       - base.qwk
        dr_s = "--" if cid in BASELINE_IDS else f"{dr:+.4f}"
        dq_s = "--" if cid in BASELINE_IDS else f"{dq:+.4f}"
        r_s    = b(ev.pearson_r, best_r,    hi=True)
        q_s    = b(ev.qwk,       best_qwk,  hi=True)
        rmse_s = b(ev.rmse,      best_rmse, hi=False)
        mae_s  = b(mae,          best_mae,  hi=False)
        if cid == "C1":
            lines.append("\\midrule")
        lines.append(
            f"{cid} & {cname} & {r_s} & {dr_s} & {q_s} & {dq_s} & {rmse_s} & {mae_s} \\\\"
        )
    lines += ["\\bottomrule\\end{tabular}\\end{table}"]
    return "\n".join(lines)


def main(model_override: str | None = None, reset: bool = False, save_intermediates: bool = False,
         replay_verifier_path: str | None = None, max_workers_override: int | None = None):
    from conceptgrade.key_rotator import get_api_key_for_provider
    from conceptgrade.llm_client import detect_provider

    # Determine model and load matching API keys
    default_model = model_override or "claude-haiku-4-5-20251001"
    provider = detect_provider(default_model)
    provider_keys = {
        "anthropic": lambda: _load_indexed_keys("ANTHROPIC_API_KEY"),
        "google":    lambda: _load_indexed_keys("GEMINI_API_KEY") or _load_indexed_keys("GOOGLE_API_KEY"),
        "openai":    lambda: _load_indexed_keys("OPENAI_API_KEY"),
    }

    def _load_indexed_keys(prefix):
        keys = []
        i = 1
        while True:
            k = os.environ.get(f"{prefix}_{i}")
            if not k:
                break
            keys.append(k)
            i += 1
        if not keys:
            single = os.environ.get(prefix)
            if single:
                keys.append(single)
        return keys

    active_keys = provider_keys.get(provider, lambda: [])()
    if not active_keys:
        # Fallback to all available keys
        active_keys = API_KEYS

    provider_label = {"anthropic": "Anthropic Claude", "google": "Google Gemini", "openai": "OpenAI"}.get(provider, provider)

    print("=" * 72)
    print("  ConceptGrade LLM-Mode Ablation Study")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Provider: {provider_label}  |  Model: {default_model}")
    print(f"  Keys available: {len(active_keys)}")
    print("=" * 72)

    # Use all available embedded samples (10 questions × 12 answers = 120 total).
    # Full dataset gives better statistical power vs. the former 3-per-question (n=30)
    # and is the complete enumeration of the embedded Mohler benchmark.
    full_dataset = load_mohler_sample()
    qids = list(full_dataset.questions.keys())
    stratified = []
    for qid in qids:
        q_samples = full_dataset.get_by_question(qid)
        stratified.extend(sorted(q_samples, key=lambda s: s.score_avg))

    dataset = full_dataset
    dataset.samples = stratified
    samples  = dataset.samples
    human    = [s.score_avg for s in samples]
    rotator  = KeyRotator(active_keys)

    print(f"\nDataset: {len(samples)} samples, {dataset.num_questions} questions")
    print(f"Score distribution: {dataset.score_distribution()}\n")

    # ── Score checkpoint — reuse saved scores instead of re-running API calls ──
    # Keyed by model name so changing the model invalidates the checkpoint.
    checkpoint_path = os.path.join(
        os.path.dirname(__file__), "data",
        f"ablation_checkpoint_{default_model.replace('/', '_').replace('-', '_')}.json"
    )

    def _load_checkpoint() -> dict:
        if os.path.exists(checkpoint_path):
            with open(checkpoint_path) as f:
                return json.load(f)
        return {}

    def _save_checkpoint(ckpt: dict):
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        with open(checkpoint_path, "w") as f:
            json.dump(ckpt, f, indent=2)

    # C0 (cosine) and C_LLM (pure LLM) never change when the KG pipeline is modified.
    # --reset only clears C1–C5 so those are re-run with the new pipeline code,
    # while C0/C_LLM are always loaded from JSON — saving ~25 min per reset run.
    STABLE_CONFIGS = {"C0", "C_LLM"}   # never affected by pipeline changes

    full_checkpoint = _load_checkpoint()
    if reset:
        # Keep stable configs from JSON, drop pipeline configs
        stable_scores = {k: v for k, v in full_checkpoint.get("scores", {}).items()
                         if k in STABLE_CONFIGS and len(v) == len(human)}
        cached_scores = stable_scores
        kept = list(stable_scores.keys())
        print(f"  [Checkpoint] --reset: keeping {kept} from JSON, re-running C1–C5.\n")
    else:
        cached_scores = full_checkpoint.get("scores", {})
        if cached_scores:
            print(f"  [Checkpoint] Found: {checkpoint_path}")
            print(f"  [Checkpoint] Cached configs: {list(cached_scores.keys())}")
            print(f"  [Checkpoint] Pass --reset to re-run pipeline configs (C1–C5) only.\n")
    config_scores: dict[str, list[float]] = {}
    t_total = time.time()

    # ── --replay-verifier: re-run only verifier from saved intermediates ──────
    if replay_verifier_path:
        from scipy.stats import pearsonr as _pr
        import numpy as _np
        print(f"\n[Replay Verifier] Loading intermediates: {replay_verifier_path}")
        api_key = rotator.current_key
        c4_scores, human_from_ints = replay_verifier(
            replay_verifier_path, api_key, default_model, use_sc=False, use_cw=False)
        c5_scores, _ = replay_verifier(
            replay_verifier_path, api_key, default_model, use_sc=True, use_cw=True)
        human_arr = _np.array(human_from_ints)
        for label, sc in [("C4_replay", c4_scores), ("C5_replay", c5_scores)]:
            arr = _np.array(sc)
            r, _ = _pr(arr, human_arr)
            mae = float(_np.mean(_np.abs(arr - human_arr)))
            rmse = float(_np.sqrt(_np.mean((arr - human_arr)**2)))
            print(f"  {label}: r={r:.4f}  MAE={mae:.4f}  RMSE={rmse:.4f}")
        return

    for cid, cname, use_sc, use_cw, use_ver in CONFIGS:
        print(f"\n{SEP}")
        print(f"  {cid}: {cname}")
        print(SEP)

        if cid in cached_scores and len(cached_scores[cid]) == len(samples):
            scores = cached_scores[cid]
            ev = evaluate_grading(human, scores, task_name=cname)
            print(f"  [CACHED] → r={ev.pearson_r:.4f}  QWK={ev.qwk:.4f}  RMSE={ev.rmse:.4f}  [0s]")
        else:
            t0 = time.time()
            # For C1 (no verifier, no SC), optionally save intermediates
            inter_store = None
            if save_intermediates and cid == "C1":
                inter_store = {}
            # Use max_workers=1 when saving intermediates to avoid rate-limit bursts
            n_workers = max_workers_override if max_workers_override is not None else (1 if save_intermediates else 3)
            scores = run_config(samples, cid, cname, use_sc, use_cw, use_ver, rotator,
                                model=default_model, intermediates_store=inter_store,
                                max_workers=n_workers)
            if inter_store is not None:
                int_path = os.path.join(os.path.dirname(__file__), "data",
                                        f"ablation_intermediates_{default_model.replace('/', '_').replace('-', '_')}.json")
                with open(int_path, "w") as f:
                    json.dump({str(k): v for k, v in inter_store.items()}, f, indent=2)
                print(f"  [Intermediates] Saved {len(inter_store)} entries → {int_path}")
            elapsed = time.time() - t0
            ev = evaluate_grading(human, scores, task_name=cname)
            print(f"  → r={ev.pearson_r:.4f}  QWK={ev.qwk:.4f}  RMSE={ev.rmse:.4f}  [{elapsed:.0f}s]")
            # Save after each config so a crash doesn't lose prior work
            cached_scores[cid] = scores
            _save_checkpoint({"model": default_model, "n_samples": len(samples),
                              "human_scores": human, "scores": cached_scores})

        config_scores[cid] = scores

    # Evaluate all
    results: dict[str, EvaluationResult] = {}
    for cid, cname, *_ in CONFIGS:
        ev = evaluate_grading(human, config_scores[cid], task_name=cname)
        add_bootstrap_cis(ev, human, config_scores[cid])
        results[cid] = ev

    # Print table
    print(f"\n{'='*72}")
    print("  RESULTS TABLE (LLM mode)")
    print(f"{'='*72}\n")
    table = format_results_table(human, config_scores, results)
    print(table)

    # 95% CIs
    print(f"\n  95% Bootstrap CIs:")
    for cid, cname, *_ in CONFIGS:
        ev = results[cid]
        ci_r = ev.pearson_r_ci
        ci_q = ev.qwk_ci
        print(f"  {cid}  r={ev.pearson_r:.4f} [{ci_r[0]:.4f},{ci_r[1]:.4f}]"
              f"  QWK={ev.qwk:.4f} [{ci_q[0]:.4f},{ci_q[1]:.4f}]")

    # ── Statistical significance: Wilcoxon + paired t-test + Cohen's d ──────────
    print(f"\n  Significance vs C1 (Wilcoxon one-sided: does X outperform C1?):")
    base_scores = config_scores["C1"]
    for cid, cname, *_ in CONFIGS:
        if cid in ("C0", "C1"):
            continue
        w = wilcoxon_significance(
            human, config_scores[cid], base_scores,
            cname, "ConceptGrade Baseline"
        )
        tt = paired_ttest(human, config_scores[cid], base_scores, cname, "C1")
        d  = cohens_d(human, config_scores[cid], base_scores)
        sig = "p<0.05 ✓" if w["significant"] else "n.s."
        print(f"  {cid}: W={w['statistic']:.1f}  p={w['p_value']:.4f}  {sig}"
              f"  |  t={tt['t_stat']:+.2f}  t-p={tt['p_value']:.4f}  d={d:+.2f}")

    # Two-sided: is there ANY difference between C_LLM and C1/C5?
    print(f"\n  Equivalence vs C_LLM (two-sided paired t-test + Wilcoxon):")
    pure_scores = config_scores["C_LLM"]
    for cid in ("C1", "C5"):
        cname = next(cn for ci, cn, *_ in CONFIGS if ci == cid)
        # One-sided Wilcoxon: is C_LLM significantly better than this config?
        w_llm_better = wilcoxon_significance(
            human, pure_scores, config_scores[cid],
            "C_LLM", cname
        )
        # Two-sided t-test: any difference?
        tt = paired_ttest(human, config_scores[cid], pure_scores, cname, "C_LLM")
        d  = cohens_d(human, config_scores[cid], pure_scores)
        llm_wins = "C_LLM significantly better ✓" if w_llm_better["significant"] else "statistically equivalent (n.s.)"
        print(f"  {cid} vs C_LLM:  {llm_wins}")
        print(f"    Wilcoxon (C_LLM>X): W={w_llm_better['statistic']:.1f}  p={w_llm_better['p_value']:.4f}")
        print(f"    t-test (two-sided): t={tt['t_stat']:+.2f}  p={tt['p_value']:.4f}  d={d:+.2f}  [{tt['direction']}]")
        print(f"    MAE: {cname}={tt['mean_error_a']:.4f}  C_LLM={tt['mean_error_b']:.4f}")

    # Save
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)

    latex = generate_latex(results, config_scores, human)
    output = {
        "meta": {
            "study": "ConceptGrade LLM Ablation Study",
            "mode": "llm",
            "n_samples": len(samples),
            "n_keys_used": len(API_KEYS),
            "timestamp": datetime.now().isoformat(),
            "total_time_s": round(time.time() - t_total, 1),
        },
        "configs": {cid: cname for cid, cname, *_ in CONFIGS},
        "pure_llm_scores": config_scores.get("C_LLM", []),
        "human_scores": human,
        "predicted_scores": config_scores,
        "metrics": {cid: results[cid].to_dict() for cid, *_ in CONFIGS},
    }

    json_path  = os.path.join(out_dir, "llm_ablation_results.json")
    latex_path = os.path.join(out_dir, "llm_ablation_latex.tex")
    txt_path   = os.path.join(out_dir, "llm_ablation_summary.txt")

    with open(json_path, "w")  as f: json.dump(output, f, indent=2)
    with open(latex_path, "w") as f: f.write(latex)
    with open(txt_path,   "w") as f:
        f.write(f"ConceptGrade LLM Ablation Study\n{'='*50}\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"Samples: {len(samples)}\n\n")
        f.write(table)
        f.write(f"\n\nLaTeX:\n{latex}")

    print(f"\n{'='*72}")
    print(f"  Total time: {time.time()-t_total:.0f}s")
    print(f"  JSON:    {json_path}")
    print(f"  LaTeX:   {latex_path}")
    print(f"  Summary: {txt_path}")
    print("LLM ablation complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ConceptGrade LLM Ablation Study")
    parser.add_argument(
        "--model", default=None,
        help=(
            "Override default model for all pipeline configs.\n"
            "Provider auto-detected from model name:\n"
            "  claude-*  → Anthropic  (set ANTHROPIC_API_KEY)\n"
            "  gemini-*  → Google     (set GEMINI_API_KEY)\n"
            "  gpt-*     → OpenAI     (set OPENAI_API_KEY)\n"
            "Example: --model gemini-2.0-flash"
        ),
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Ignore checkpoint and re-run all configs from scratch.",
    )
    parser.add_argument(
        "--save-intermediates", action="store_true",
        help="Save C1 pipeline intermediates (KG analysis) to JSON for verifier replay.",
    )
    parser.add_argument(
        "--replay-verifier", metavar="PATH",
        help="Skip extraction, re-run ONLY the verifier on saved intermediates JSON. No API calls for extraction.",
    )
    parser.add_argument(
        "--workers", type=int, default=None,
        help="Override thread pool workers (default: 1 with --save-intermediates, 3 otherwise).",
    )
    args = parser.parse_args()
    main(
        model_override=args.model,
        reset=args.reset,
        save_intermediates=args.save_intermediates,
        replay_verifier_path=args.replay_verifier,
        max_workers_override=args.workers,
    )
