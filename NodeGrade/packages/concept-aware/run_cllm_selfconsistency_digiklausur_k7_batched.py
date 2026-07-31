#!/usr/bin/env python3
"""
run_cllm_selfconsistency_digiklausur_k7_batched.py — completes the
DigiKlausur fair-control check to the full K=7 (matching Mohler's design
exactly), reusing the K=3 batches already collected
(run_cllm_selfconsistency_digiklausur_k3_batched.py, rounds 0-2, 78
batches) and adding rounds 3-6 (104 more batches) to the SAME batch
cache directory. Batch-level caching means already-completed rounds are
skipped automatically; only the 104 new batches are called.

Uses generate_batch_scoring_prompts.build_cllm_prompt (the actual prompt
that produced DigiKlausur's original single-call C_LLM score), K=7,
temperature=0.7, mean-aggregated -- identical design to the Mohler fair
control (compute_cllm_x7_vs_verifier_x7_control.py) for direct
comparability.

Run:
    python3 run_cllm_selfconsistency_digiklausur_k7_batched.py
    python3 run_cllm_selfconsistency_digiklausur_k7_batched.py --status
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
BATCH_DIR = DATA / "digiklausur_cllm_selfconsistency_k3_batches"  # reused, now holds K=7 worth
OUT_PATH = DATA / "digiklausur_cllm_selfconsistency_k7_results.json"
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
    with (DATA / "digiklausur_eval_results.json").open() as f:
        cached = {r["id"]: r for r in json.load(f)["results"]}

    n_chunks = (len(records) + CHUNK_SIZE - 1) // CHUNK_SIZE
    total_batches = N_ROUNDS * n_chunks

    if args.status:
        done = len(list(BATCH_DIR.glob("dkc_r*_c*.json"))) if BATCH_DIR.exists() else 0
        print(f"DigiKlausur C_LLM self-consistency (K=7) batches: {done}/{total_batches}")
        return 0

    from conceptgrade.llm_client import LLMClient
    from generate_batch_scoring_prompts import build_cllm_prompt

    key = _load_gemini_key()
    client = LLMClient(api_key=key)

    attempts: dict[int, list[float]] = {r["id"]: [] for r in records}
    t_start = time.time()
    batch_num = 0
    for round_i in range(N_ROUNDS):
        for chunk_i in range(n_chunks):
            batch_num += 1
            chunk = records[chunk_i * CHUNK_SIZE: (chunk_i + 1) * CHUNK_SIZE]
            tag = f"dkc_r{round_i}_c{chunk_i}"
            cache_path = BATCH_DIR / f"{tag}.json"
            if not cache_path.exists():
                prompt = build_cllm_prompt(chunk)
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
        mean_score = round(statistics.mean(atts) * 4) / 4 if atts else None
        c = cached[r["id"]]
        results.append({
            "id": r["id"], "qid": r["question_id"], "human_score": c["human_score"],
            "cllm_1call": c["cllm_score"], "c5fix_x7_single": c["c5_score"],
            "cllm_k7_attempts": atts, "cllm_k7_mean": mean_score,
        })

    n_complete = sum(1 for r in results if r["cllm_k7_mean"] is not None)
    human = np.array([r["human_score"] for r in results if r["cllm_k7_mean"] is not None])
    cllm1 = np.array([r["cllm_1call"] for r in results if r["cllm_k7_mean"] is not None])
    cllm_k7 = np.array([r["cllm_k7_mean"] for r in results if r["cllm_k7_mean"] is not None])

    c5x7 = json.loads((DATA / "digiklausur_c5fix_selfconsistency_results.json").read_text())["per_sample"]
    c5x7_by_id = {r["id"]: r for r in c5x7}
    verif_x7 = []
    for r in results:
        if r["cllm_k7_mean"] is None:
            continue
        v = c5x7_by_id[r["id"]]
        verif_x7.append(round(statistics.mean(v["c5fix_x7_attempts"]) * 4) / 4)
    verif_x7 = np.array(verif_x7)

    def mae(pred):
        return float(np.mean(np.abs(human - pred)))

    print(f"\n=== DigiKlausur K=7 fair-control check (n={n_complete}) ===")
    print(f"  C_LLM (1 call)         MAE={mae(cllm1):.4f}  r={pearsonr(human,cllm1)[0]:.4f}")
    print(f"  C_LLM K=7 (mean)       MAE={mae(cllm_k7):.4f}  r={pearsonr(human,cllm_k7)[0]:.4f}")
    print(f"  C5fix x7 (mean)        MAE={mae(verif_x7):.4f}  r={pearsonr(human,verif_x7)[0]:.4f}")

    err_cllm1 = np.abs(human - cllm1)
    err_cllmk7 = np.abs(human - cllm_k7)
    err_verifx7 = np.abs(human - verif_x7)

    _, p_h2h_two = wilcoxon(err_verifx7, err_cllmk7, alternative="two-sided", zero_method="wilcox")
    _, p_h2h_one = wilcoxon(err_verifx7, err_cllmk7, alternative="less", zero_method="wilcox")
    print(f"\nC5fix x7 (mean) vs C_LLM K=7 (mean) -- THE FAIR CONTROL: "
          f"{(mae(cllm_k7)-mae(verif_x7))/mae(cllm_k7)*100:+.1f}% MAE change, "
          f"p_two={p_h2h_two:.4f} p_one={p_h2h_one:.4f}")

    qids = [r["qid"] for r in results if r["cllm_k7_mean"] is not None]
    import collections
    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)
    qerr_verif = np.array([np.mean(err_verifx7[idx]) for idx in by_q.values()])
    qerr_cllmk7 = np.array([np.mean(err_cllmk7[idx]) for idx in by_q.values()])
    _, pq_two = wilcoxon(qerr_verif, qerr_cllmk7, alternative="two-sided", zero_method="wilcox")
    _, pq_one = wilcoxon(qerr_verif, qerr_cllmk7, alternative="less", zero_method="wilcox")
    wins = sum(1 for a, b in zip(qerr_verif, qerr_cllmk7) if a < b)
    n_q = len(by_q)
    n_sig_one = n_sig_two = 0
    for i in range(n_q):
        keep = [j for j in range(n_q) if j != i]
        _, p_t = wilcoxon(qerr_verif[keep], qerr_cllmk7[keep], alternative="two-sided", zero_method="wilcox")
        _, p_o = wilcoxon(qerr_verif[keep], qerr_cllmk7[keep], alternative="less", zero_method="wilcox")
        if p_o < 0.05:
            n_sig_one += 1
        if p_t < 0.05:
            n_sig_two += 1

    print(f"cluster (K=7 fair control): p_two={pq_two:.4f} p_one={pq_one:.4f} wins={wins}/{n_q}")
    print(f"LOOCV (K=7 fair control): one-tail sig={n_sig_one}/{n_q}, two-tail sig={n_sig_two}/{n_q}")

    out = {
        "n": n_complete, "n_questions": n_q, "k": 7,
        "mae_cllm_1call": mae(cllm1), "mae_cllm_k7": mae(cllm_k7), "mae_c5fix_x7": mae(verif_x7),
        "c5fix_x7_vs_cllm_k7_p_two": float(p_h2h_two), "c5fix_x7_vs_cllm_k7_p_one": float(p_h2h_one),
        "c5fix_x7_vs_cllm_k7_cluster_p_two": float(pq_two), "c5fix_x7_vs_cllm_k7_cluster_p_one": float(pq_one),
        "c5fix_x7_vs_cllm_k7_cluster_wins": wins,
        "loocv_one_tailed_significant_folds": n_sig_one, "loocv_two_tailed_significant_folds": n_sig_two,
        "per_sample": results,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
