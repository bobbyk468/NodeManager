#!/usr/bin/env python3
"""
run_verifier_selfconsistency_real_batched.py — tests whether the
Verifier's own judgment is noisy enough that self-consistency
ensembling (K=7 independent calls, temperature=0.7, median-aggregated)
reduces error, on the real 46-question/1,262-response Mohler set.

The deployed pipeline calls the Verifier ONCE per response at
temperature=0.0. This is a genuinely untried mechanism (distinct from
the retracted C_LLM/C5_fix ensemble, which failed cross-validation):
instead of blending in a different, weaker system, this resamples the
SAME verifier judgment multiple times independently and aggregates,
exactly mirroring the already-validated C_LLM x7 budget-matched
experiment's design (run_budget_matched_real_batched.py), so the two
are directly comparable at equal call budget (357 batched calls each).

The KG evidence (comparison_result, Bloom's/SOLO levels, misconceptions)
is IDENTICAL across all 7 rounds -- only the verifier's own holistic
judgment is resampled. This isolates verifier-judgment noise as the
variable under test.

Every batch response is cached to disk immediately
(data/verifier_selfconsistency_batches/*.json), fully resumable.

Run:
    python3 run_verifier_selfconsistency_real_batched.py
    python3 run_verifier_selfconsistency_real_batched.py --status
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"
BATCH_DIR = DATA / "verifier_selfconsistency_batches"
OUT_PATH = DATA / "verifier_selfconsistency_real_results.json"
CHUNK_SIZE = 25
N_ROUNDS = 7
LIVE_MODEL = "gemini-2.5-flash"

BLOOMS_LABELS = {1: "Remember", 2: "Understand", 3: "Apply", 4: "Analyze", 5: "Evaluate", 6: "Create"}
SOLO_LABELS = {1: "Prestructural", 2: "Unistructural", 3: "Multistructural", 4: "Relational", 5: "Extended Abstract"}


def _load_gemini_key() -> str:
    env_path = BASE.parent / "backend" / ".env"
    with env_path.open() as f:
        for line in f:
            m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
            if m:
                return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def _call_batched(client, system_prompt: str, user_prompt: str, tag: str, temperature: float) -> dict:
    from conceptgrade.llm_client import parse_llm_json

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = BATCH_DIR / f"{tag}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    last_exc = None
    for attempt in range(3):
        try:
            messages = [{"role": "user", "content": user_prompt}]
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            resp = client.chat.completions.create(
                model=LIVE_MODEL, messages=messages, temperature=temperature, max_tokens=8192,
            )
            raw_text = resp.choices[0].message.content
            parsed = parse_llm_json(raw_text)
            cache_path.write_text(json.dumps({"raw_text": raw_text, "parsed": parsed}, indent=2))
            return {"raw_text": raw_text, "parsed": parsed}
        except Exception as e:
            last_exc = e
            wait = 3 * (2 ** attempt)
            print(f"    [retry] {tag} attempt {attempt+1}/3 failed ({type(e).__name__}: {e}); "
                  f"retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"{tag}: failed after 3 retries") from last_exc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    with (DATA / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = {r["sample_id"]: r for r in json.load(f)}
    with (DATA / "mohler_real_eval_results.json").open() as f:
        cached = {r["id"]: r for r in json.load(f)["results"]}

    sample_ids = list(cached.keys())
    n_chunks = (len(sample_ids) + CHUNK_SIZE - 1) // CHUNK_SIZE
    total_batches = N_ROUNDS * n_chunks

    if args.status:
        done = len(list(BATCH_DIR.glob("verifsc_r*_c*.json"))) if BATCH_DIR.exists() else 0
        print(f"Verifier self-consistency batches: {done}/{total_batches}")
        return 0

    from conceptgrade.llm_client import LLMClient
    from conceptgrade.verifier import LLMVerifier

    key = _load_gemini_key()
    client = LLMClient(api_key=key)
    verifier = LLMVerifier(api_key=key, model=LIVE_MODEL, verifier_weight=1.0)

    def build_batch_prompt(chunk_ids: list[str]) -> tuple[str, str]:
        blocks = []
        system_prompt = None
        for sid in chunk_ids:
            a = phase_a[sid]
            c = cached[sid]
            blooms = {"level": c["blooms_level"], "label": BLOOMS_LABELS[c["blooms_level"]]}
            solo = {"level": c["solo_level"], "label": SOLO_LABELS[c["solo_level"]]}
            sys_p, user_p, _ = verifier.build_user_prompt(
                question=a["question"], student_answer=a["student_answer"],
                comparison_result=a["comparison_result"],
                blooms=blooms, solo=solo, misconceptions=a["misconceptions"],
                reference_answer=a["reference_answer"], mode="sag",
            )
            system_prompt = sys_p
            marker = "\nReturn ONLY valid JSON:"
            idx = user_p.rfind(marker)
            evidence = user_p[:idx] if idx != -1 else user_p
            blocks.append(f"=== SAMPLE ID: {sid} ===\n{evidence}")

        footer = (
            "\n\nFor EACH sample above, independently apply the scoring guide as if you "
            "were one of several graders reaching your own holistic judgment without "
            "seeing the others'. Return ONLY valid JSON:\n"
            "{\n  \"scores\": {\n    \"<SAMPLE ID>\": {\n"
            "      \"verified_score\": <float 0.0-5.0 in 0.25 increments>\n"
            "    }, ...\n  }\n}"
        )
        return system_prompt, "\n\n".join(blocks) + footer

    attempts: dict[str, list[float]] = {sid: [] for sid in sample_ids}
    t_start = time.time()
    batch_num = 0
    for round_i in range(N_ROUNDS):
        for chunk_i in range(n_chunks):
            batch_num += 1
            chunk_ids = sample_ids[chunk_i * CHUNK_SIZE: (chunk_i + 1) * CHUNK_SIZE]
            tag = f"verifsc_r{round_i}_c{chunk_i}"
            cache_path = BATCH_DIR / f"{tag}.json"
            if not cache_path.exists():
                system_prompt, prompt = build_batch_prompt(chunk_ids)
                _call_batched(client, system_prompt, prompt, tag, temperature=0.7)

            result = json.loads(cache_path.read_text())
            scores = result["parsed"].get("scores", result["parsed"])
            for sid in chunk_ids:
                v = scores.get(sid)
                if v is None:
                    print(f"    [warn] no score for {sid} in {tag}", flush=True)
                    continue
                raw = float(v["verified_score"]) if isinstance(v, dict) else float(v)
                attempts[sid].append(max(0.0, min(5.0, raw)))

            elapsed = time.time() - t_start
            print(f"[{batch_num}/{total_batches}] round {round_i+1}/{N_ROUNDS} "
                  f"batch {chunk_i+1}/{n_chunks} done -- elapsed {elapsed:.0f}s", flush=True)
            if batch_num % 10 == 0:
                print(f"    [status] {batch_num}/{total_batches} batches done, {elapsed:.0f}s elapsed", flush=True)

    import statistics
    import numpy as np
    from scipy.stats import wilcoxon

    results = []
    for sid in sample_ids:
        atts = attempts[sid]
        median_score = round(statistics.median(atts) * 4) / 4 if atts else None
        c = cached[sid]
        results.append({
            "id": sid, "qid": c["qid"], "human_score": c["human_score"],
            "cllm_score": c["cllm_score"], "c5_fix_single": c["c5_score"],
            "verifier_x7_attempts": atts, "verifier_x7_median": median_score,
        })

    n_complete = sum(1 for r in results if r["verifier_x7_median"] is not None)
    human = np.array([r["human_score"] for r in results if r["verifier_x7_median"] is not None])
    cllm = np.array([r["cllm_score"] for r in results if r["verifier_x7_median"] is not None])
    c5_single = np.array([r["c5_fix_single"] for r in results if r["verifier_x7_median"] is not None])
    verif_x7 = np.array([r["verifier_x7_median"] for r in results if r["verifier_x7_median"] is not None])

    def mae(pred):
        return float(np.mean(np.abs(human - pred)))

    print(f"\n=== Point estimates (n={n_complete}) ===")
    print(f"  C_LLM (1 call)          MAE={mae(cllm):.4f}")
    print(f"  C5_fix (verifier x1)    MAE={mae(c5_single):.4f}")
    print(f"  Verifier x7 (median)    MAE={mae(verif_x7):.4f}")

    err_c5single = np.abs(human - c5_single)
    err_x7 = np.abs(human - verif_x7)
    err_cllm = np.abs(human - cllm)

    _, p_x7_vs_single_two = wilcoxon(err_x7, err_c5single, alternative="two-sided", zero_method="wilcox")
    _, p_x7_vs_single_one = wilcoxon(err_x7, err_c5single, alternative="less", zero_method="wilcox")
    print(f"\nVerifier x7 vs C5_fix (single call): "
          f"{(mae(c5_single)-mae(verif_x7))/mae(c5_single)*100:+.1f}% MAE change, "
          f"p_two={p_x7_vs_single_two:.4f} p_one={p_x7_vs_single_one:.4f}")

    _, p_x7_vs_cllm_two = wilcoxon(err_x7, err_cllm, alternative="two-sided", zero_method="wilcox")
    _, p_x7_vs_cllm_one = wilcoxon(err_x7, err_cllm, alternative="less", zero_method="wilcox")
    print(f"Verifier x7 vs C_LLM: "
          f"{(mae(cllm)-mae(verif_x7))/mae(cllm)*100:+.1f}% MAE change, "
          f"p_two={p_x7_vs_cllm_two:.4f} p_one={p_x7_vs_cllm_one:.4f}")

    from scipy.stats import pearsonr, spearmanr
    print(f"\nCorrelation: C_LLM r={pearsonr(human,cllm)[0]:.4f} rho={spearmanr(human,cllm)[0]:.4f}")
    print(f"             C5_fix(x1) r={pearsonr(human,c5_single)[0]:.4f} rho={spearmanr(human,c5_single)[0]:.4f}")
    print(f"             Verifier x7 r={pearsonr(human,verif_x7)[0]:.4f} rho={spearmanr(human,verif_x7)[0]:.4f}")

    qids = [r["qid"] for r in results if r["verifier_x7_median"] is not None]
    import collections
    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)
    qerr_x7 = np.array([np.mean(err_x7[idx]) for idx in by_q.values()])
    qerr_cllm = np.array([np.mean(err_cllm[idx]) for idx in by_q.values()])
    _, pq_two = wilcoxon(qerr_x7, qerr_cllm, alternative="two-sided", zero_method="wilcox")
    _, pq_one = wilcoxon(qerr_x7, qerr_cllm, alternative="less", zero_method="wilcox")
    wins = sum(1 for a, b in zip(qerr_x7, qerr_cllm) if a < b)
    print(f"\nVerifier x7 vs C_LLM, question-clustered ({len(by_q)} questions): "
          f"p_two={pq_two:.4f} p_one={pq_one:.4f} wins={wins}/{len(by_q)}")

    out = {
        "n": n_complete,
        "mae_cllm": mae(cllm), "mae_c5_single": mae(c5_single), "mae_verifier_x7": mae(verif_x7),
        "verifier_x7_vs_single_p_two": float(p_x7_vs_single_two),
        "verifier_x7_vs_single_p_one": float(p_x7_vs_single_one),
        "verifier_x7_vs_cllm_p_two": float(p_x7_vs_cllm_two),
        "verifier_x7_vs_cllm_p_one": float(p_x7_vs_cllm_one),
        "verifier_x7_vs_cllm_cluster_p_two": float(pq_two),
        "verifier_x7_vs_cllm_cluster_p_one": float(pq_one),
        "verifier_x7_vs_cllm_cluster_wins": wins,
        "verifier_x7_vs_cllm_cluster_n_q": len(by_q),
        "per_sample": results,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
