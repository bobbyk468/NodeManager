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
    format_significance_table, EvaluationResult,
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


def run_config(
    samples: list[MohlerSample],
    cid: str,
    cname: str,
    use_sc: bool,
    use_cw: bool,
    use_ver: bool,
    rotator: KeyRotator,
    model: str = "claude-haiku-4-5-20251001",
) -> list[float]:
    """Score all samples under one configuration."""

    if cid == "C0":
        return [cosine_score(s) for s in samples]

    if cid == "C_LLM":
        scores = []
        for i, sample in enumerate(samples):
            print(f"    [C_LLM] {i+1:2d}/{len(samples)}: Q{sample.question_id[-2:] if len(sample.question_id)>1 else sample.question_id} ", end="", flush=True)
            for attempt in range(len(rotator._keys) + 1):
                try:
                    s = pure_llm_score(sample, rotator.current_key, model)
                    print(f"→ {s:.2f}")
                    scores.append(round(s, 2))
                    break
                except Exception as e:
                    err = str(e)
                    is_rate_limit = ("429" in err or "rate_limit" in err.lower()
                                     or "overloaded" in err.lower() or "529" in err)
                    if is_rate_limit:
                        rotator.next_key()
                        print(f"\n      [RateLimit] rotating...", end="")
                        time.sleep(2.0)
                    else:
                        print(f"\n      ERROR: {err[:80]}")
                        scores.append(0.0)
                        break
            else:
                scores.append(0.0)
            time.sleep(0.5)
        return scores

    from conceptgrade.pipeline import ConceptGradePipeline

    scores = []
    pipeline = None

    for i, sample in enumerate(samples):
        print(f"    [{cid}] {i+1:2d}/{len(samples)}: Q{sample.question_id[-2:] if len(sample.question_id)>1 else sample.question_id} ", end="", flush=True)

        # Build (or rebuild) pipeline with current key
        api_key = rotator.current_key
        if pipeline is None or pipeline.api_key != api_key:
            pipeline = ConceptGradePipeline(
                api_key=api_key,
                model=model,
                use_self_consistency=use_sc,
                use_confidence_weighting=use_cw,
                use_llm_verifier=use_ver,
                verifier_weight=1.0,
                rate_limit_delay=1.5,
                sc_n_runs=2,
                sc_min_votes=2,
            )

        success = False
        for attempt in range(len(rotator._keys) + 1):
            try:
                result = pipeline.assess_student(
                    student_id=f"s{i}",
                    question=sample.question,
                    answer=sample.student_answer,
                    reference_answer=sample.reference_answer,
                )
                score = round(result.overall_score * 5.0, 2)
                print(f"→ {score:.2f}")
                scores.append(score)
                success = True
                break
            except Exception as e:
                err = str(e)
                is_rate_limit = ("429" in err or "rate_limit" in err.lower()
                                 or "overloaded" in err.lower() or "529" in err)
                if is_rate_limit:
                    new_key = rotator.next_key()
                    print(f"\n      [RateLimit] rotating to key {rotator._idx + 1}...", end="")
                    pipeline = ConceptGradePipeline(
                        api_key=new_key,
                        model=model,
                        use_self_consistency=use_sc,
                        use_confidence_weighting=use_cw,
                        use_llm_verifier=use_ver,
                        verifier_weight=1.0,
                        rate_limit_delay=1.5,
                        sc_n_runs=2,
                        sc_min_votes=2,
                    )
                    time.sleep(2.0)
                else:
                    print(f"\n      ERROR: {err[:80]}")
                    scores.append(0.0)
                    success = True
                    break

        if not success:
            print(f"\n      All keys exhausted — using 0")
            scores.append(0.0)

        time.sleep(0.5)

    return scores


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


def main(model_override: str | None = None):
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

    # Stratified sampling: 3 samples per question (low/mid/high score bands).
    # n=30 with score distribution {0:10, 2:10, 5:10} for good Pearson r variance.
    # Each independent Groq org contributes ~100K TPD; budget scales with key count.
    full_dataset = load_mohler_sample()
    qids = list(full_dataset.questions.keys())
    stratified = []
    for qid in qids:
        q_samples = full_dataset.get_by_question(qid)
        sorted_s = sorted(q_samples, key=lambda s: s.score_avg)
        n = len(sorted_s)
        stratified.extend([sorted_s[0], sorted_s[n // 2], sorted_s[-1]])

    dataset = full_dataset
    dataset.samples = stratified
    samples  = dataset.samples
    human    = [s.score_avg for s in samples]
    rotator  = KeyRotator(active_keys)

    print(f"\nDataset: {len(samples)} samples, {dataset.num_questions} questions")
    print(f"Score distribution: {dataset.score_distribution()}\n")

    config_scores: dict[str, list[float]] = {}
    t_total = time.time()

    for cid, cname, use_sc, use_cw, use_ver in CONFIGS:
        print(f"\n{SEP}")
        print(f"  {cid}: {cname}")
        print(SEP)
        t0 = time.time()
        scores = run_config(samples, cid, cname, use_sc, use_cw, use_ver, rotator,
                            model=default_model)
        elapsed = time.time() - t0
        config_scores[cid] = scores
        ev = evaluate_grading(human, scores, task_name=cname)
        print(f"  → r={ev.pearson_r:.4f}  QWK={ev.qwk:.4f}  RMSE={ev.rmse:.4f}  [{elapsed:.0f}s]")

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

    # Wilcoxon significance vs C1 and vs C_LLM
    print(f"\n  Significance vs C1 (Wilcoxon signed-rank):")
    base_scores = config_scores["C1"]
    for cid, cname, *_ in CONFIGS:
        if cid in ("C0", "C1"):
            continue
        t = wilcoxon_significance(
            human, config_scores[cid], base_scores,
            cname, "ConceptGrade Baseline"
        )
        sig = "p<0.05 ✓" if t["significant"] else "n.s."
        print(f"  {cid}: W={t['statistic']:.1f}  p={t['p_value']:.4f}  {sig}")

    print(f"\n  Significance vs C_LLM (Pure LLM Zero-Shot):")
    pure_scores = config_scores["C_LLM"]
    for cid in ("C1", "C5"):
        cname = next(cn for ci, cn, *_ in CONFIGS if ci == cid)
        t = wilcoxon_significance(
            human, config_scores[cid], pure_scores,
            cname, "Pure LLM Zero-Shot"
        )
        sig = "p<0.05 ✓" if t["significant"] else "n.s."
        print(f"  {cid} vs C_LLM: W={t['statistic']:.1f}  p={t['p_value']:.4f}  {sig}")

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
    args = parser.parse_args()
    main(model_override=args.model)
