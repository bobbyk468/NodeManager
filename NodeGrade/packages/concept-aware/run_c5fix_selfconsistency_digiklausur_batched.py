#!/usr/bin/env python3
"""
run_c5fix_selfconsistency_digiklausur_batched.py — tests whether the
Verifier self-consistency finding (K=7, temperature=0.7, median) that
robustly beat C_LLM on Mohler also generalises to DigiKlausur, the
single cross-dataset check needed to move from "works on Mohler" to
"works in general" (or to honestly confirm it doesn't).

DigiKlausur's original C5_fix score was produced by a different, older
code path than Mohler's (generate_batch_scoring_prompts.build_c5fix_prompt,
not conceptgrade/verifier.py's LLMVerifier) -- reusing that SAME prompt
builder for self-consistency keeps this experiment faithful to how
DigiKlausur's headline c5_score was actually produced, rather than
retrofitting the Mohler-specific verifier code path onto a dataset it
was never run on.

Design: 7 independent calls per response at temperature=0.7 (same K,
same temperature as the Mohler experiment), median-aggregated. KG
evidence (matched_concepts, chain_pct -- from the already-cached
data/digiklausur_precomputed.json) is identical across rounds; only the
LLM's holistic judgment is resampled.

n=646 (matches the established headline DigiKlausur numbers in
compute_cross_dataset_significance.py, NOT the deduplicated n=617/n=in some
analyses -- this is deliberate, for direct comparability).

Run:
    python3 run_c5fix_selfconsistency_digiklausur_batched.py
    python3 run_c5fix_selfconsistency_digiklausur_batched.py --status
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
BATCH_DIR = DATA / "digiklausur_c5fix_selfconsistency_batches"
OUT_PATH = DATA / "digiklausur_c5fix_selfconsistency_results.json"
CHUNK_SIZE = 25
N_ROUNDS = 7
LIVE_MODEL = "gemini-2.5-flash"


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

    with (DATA / "digiklausur_dataset.json").open() as f:
        records = json.load(f)
    with (DATA / "digiklausur_precomputed.json").open() as f:
        features = json.load(f)
    with (DATA / "digiklausur_eval_results.json").open() as f:
        cached = {r["id"]: r for r in json.load(f)["results"]}

    n_chunks = (len(records) + CHUNK_SIZE - 1) // CHUNK_SIZE
    total_batches = N_ROUNDS * n_chunks

    if args.status:
        done = len(list(BATCH_DIR.glob("dk_r*_c*.json"))) if BATCH_DIR.exists() else 0
        print(f"DigiKlausur C5fix self-consistency batches: {done}/{total_batches}")
        return 0

    from conceptgrade.llm_client import LLMClient
    from generate_batch_scoring_prompts import build_c5fix_prompt

    key = _load_gemini_key()
    client = LLMClient(api_key=key)

    attempts: dict[int, list[float]] = {r["id"]: [] for r in records}
    t_start = time.time()
    batch_num = 0
    for round_i in range(N_ROUNDS):
        for chunk_i in range(n_chunks):
            batch_num += 1
            chunk = records[chunk_i * CHUNK_SIZE: (chunk_i + 1) * CHUNK_SIZE]
            tag = f"dk_r{round_i}_c{chunk_i}"
            cache_path = BATCH_DIR / f"{tag}.json"
            if not cache_path.exists():
                prompt = build_c5fix_prompt(chunk, features)
                _call_batched(client, "", prompt, tag, temperature=0.7)

            result = json.loads(cache_path.read_text())
            scores = result["parsed"].get("scores", result["parsed"])
            for r in chunk:
                v = scores.get(str(r["id"]))
                if v is None:
                    print(f"    [warn] no score for {r['id']} in {tag}", flush=True)
                    continue
                attempts[r["id"]].append(max(0.0, min(5.0, float(v))))

            elapsed = time.time() - t_start
            print(f"[{batch_num}/{total_batches}] round {round_i+1}/{N_ROUNDS} "
                  f"batch {chunk_i+1}/{n_chunks} done -- elapsed {elapsed:.0f}s", flush=True)
            if batch_num % 10 == 0:
                print(f"    [status] {batch_num}/{total_batches} batches done, {elapsed:.0f}s elapsed", flush=True)

    import statistics
    import numpy as np
    from scipy.stats import wilcoxon, pearsonr, spearmanr

    results = []
    for r in records:
        atts = attempts[r["id"]]
        median_score = round(statistics.median(atts) * 4) / 4 if atts else None
        c = cached[r["id"]]
        results.append({
            "id": r["id"], "qid": r["question_id"], "human_score": c["human_score"],
            "cllm_score": c["cllm_score"], "c5_fix_single": c["c5_score"],
            "c5fix_x7_attempts": atts, "c5fix_x7_median": median_score,
        })

    n_complete = sum(1 for r in results if r["c5fix_x7_median"] is not None)
    human = np.array([r["human_score"] for r in results if r["c5fix_x7_median"] is not None])
    cllm = np.array([r["cllm_score"] for r in results if r["c5fix_x7_median"] is not None])
    c5_single = np.array([r["c5_fix_single"] for r in results if r["c5fix_x7_median"] is not None])
    x7 = np.array([r["c5fix_x7_median"] for r in results if r["c5fix_x7_median"] is not None])

    def mae(pred):
        return float(np.mean(np.abs(human - pred)))

    print(f"\n=== DigiKlausur point estimates (n={n_complete}) ===")
    print(f"  C_LLM              MAE={mae(cllm):.4f}  r={pearsonr(human,cllm)[0]:.4f}  rho={spearmanr(human,cllm)[0]:.4f}")
    print(f"  C5_fix (single)    MAE={mae(c5_single):.4f}  r={pearsonr(human,c5_single)[0]:.4f}  rho={spearmanr(human,c5_single)[0]:.4f}")
    print(f"  C5fix x7 (median)  MAE={mae(x7):.4f}  r={pearsonr(human,x7)[0]:.4f}  rho={spearmanr(human,x7)[0]:.4f}")

    err_cllm = np.abs(human - cllm)
    err_single = np.abs(human - c5_single)
    err_x7 = np.abs(human - x7)

    _, p_x7_cllm_two = wilcoxon(err_x7, err_cllm, alternative="two-sided", zero_method="wilcox")
    _, p_x7_cllm_one = wilcoxon(err_x7, err_cllm, alternative="less", zero_method="wilcox")
    print(f"\nC5fix x7 vs C_LLM: {(mae(cllm)-mae(x7))/mae(cllm)*100:+.1f}% MAE change, "
          f"p_two={p_x7_cllm_two:.4f} p_one={p_x7_cllm_one:.4f}")

    _, p_x7_single_two = wilcoxon(err_x7, err_single, alternative="two-sided", zero_method="wilcox")
    _, p_x7_single_one = wilcoxon(err_x7, err_single, alternative="less", zero_method="wilcox")
    print(f"C5fix x7 vs C5_fix(single): {(mae(c5_single)-mae(x7))/mae(c5_single)*100:+.1f}% MAE change, "
          f"p_two={p_x7_single_two:.4f} p_one={p_x7_single_one:.4f}")

    qids = [r["qid"] for r in results if r["c5fix_x7_median"] is not None]
    import collections
    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)
    qerr_x7 = np.array([np.mean(err_x7[idx]) for idx in by_q.values()])
    qerr_cllm = np.array([np.mean(err_cllm[idx]) for idx in by_q.values()])
    _, pq_two = wilcoxon(qerr_x7, qerr_cllm, alternative="two-sided", zero_method="wilcox")
    _, pq_one = wilcoxon(qerr_x7, qerr_cllm, alternative="less", zero_method="wilcox")
    wins = sum(1 for a, b in zip(qerr_x7, qerr_cllm) if a < b)
    print(f"\nC5fix x7 vs C_LLM, question-clustered ({len(by_q)} questions): "
          f"p_two={pq_two:.4f} p_one={pq_one:.4f} wins={wins}/{len(by_q)}")

    out = {
        "dataset": "digiklausur", "n": n_complete,
        "mae_cllm": mae(cllm), "mae_c5_single": mae(c5_single), "mae_c5fix_x7": mae(x7),
        "c5fix_x7_vs_cllm_p_two": float(p_x7_cllm_two), "c5fix_x7_vs_cllm_p_one": float(p_x7_cllm_one),
        "c5fix_x7_vs_single_p_two": float(p_x7_single_two), "c5fix_x7_vs_single_p_one": float(p_x7_single_one),
        "c5fix_x7_vs_cllm_cluster_p_two": float(pq_two), "c5fix_x7_vs_cllm_cluster_p_one": float(pq_one),
        "c5fix_x7_vs_cllm_cluster_wins": wins, "c5fix_x7_vs_cllm_cluster_n_q": len(by_q),
        "per_sample": results,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
