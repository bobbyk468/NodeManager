#!/usr/bin/env python3
"""
run_budget_matched_real_batched.py — Experiment #1 (call-budget-matched
baseline) re-run on the real Mohler data, batched.

The original run_budget_matched_baseline.py --live ran this on the
fabricated 120-sample fixture, one sample per API call (630 calls). This
version runs on the real 1,262-sample data, batching CHUNK_SIZE samples
per call within each of 7 independent rounds (temperature=0.7, matching
the original design's requirement for genuine independent variation
across attempts) -- cutting ~8,834 individual judgments down to ~357
batched calls (7 rounds x ~51 batches/round).

Every batch response is cached to disk immediately
(data/budget_matched_real_batches/*.json), fully resumable.

Run:
    python3 run_budget_matched_real_batched.py
    python3 run_budget_matched_real_batched.py --status
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
BATCH_DIR = DATA / "budget_matched_real_batches"
OUT_PATH = DATA / "budget_matched_real_results.json"
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


def call_batched(client, system_prompt: str, user_prompt: str, tag: str, temperature: float):
    from conceptgrade.llm_client import parse_llm_json

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = BATCH_DIR / f"{tag}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    last_exc = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=LIVE_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=8192,
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

    from generate_batch_scoring_prompts import SCORING_GUIDE

    with (DATA / "mohler_real" / "mohler_real_kg_aligned.json").open() as f:
        raw = json.load(f)["samples"]
    with (DATA / "mohler_real_eval_results.json").open() as f:
        cached = {r["id"]: r for r in json.load(f)["results"]}

    n_chunks = (len(raw) + CHUNK_SIZE - 1) // CHUNK_SIZE
    total_batches = N_ROUNDS * n_chunks

    if args.status:
        done = len(list(BATCH_DIR.glob("budget_r*_c*.json"))) if BATCH_DIR.exists() else 0
        print(f"Budget-matched batches: {done}/{total_batches}")
        return 0

    from conceptgrade.llm_client import LLMClient
    key = _load_gemini_key()
    client = LLMClient(api_key=key)

    def build_prompt(batch: list[dict]) -> str:
        system = f"""{SCORING_GUIDE}

You are an expert grader. This is one independent attempt in a
self-consistency ensemble: grade each student answer below as if you
were one of several graders reaching your own judgment without seeing
the others'. Grade using ONLY the question, reference answer, and
student answer -- no external knowledge graph or structured evidence.

Return a JSON object:
{{
  "scores": {{
    "<id>": X.X,
    ...
  }}
}}

Grade all {len(batch)} samples. Use 0.25 increments only."""
        parts = []
        for r in batch:
            parts.append(
                f"--- SAMPLE ID: {r['id']} ---\n"
                f"QUESTION: {r['question']}\n\n"
                f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
                f"STUDENT ANSWER:\n{r['student_answer']}"
            )
        header = f"{system}\n\n{'='*70}\n\n"
        body = "\n\n".join(parts)
        footer = f"\n\n{'='*70}\nGrade all {len(batch)} samples. Return only the JSON object."
        return header + body + footer

    attempts: dict[str, list[float]] = {r["id"]: [] for r in raw}
    t_start = time.time()
    batch_num = 0
    for round_i in range(N_ROUNDS):
        for chunk_i in range(n_chunks):
            batch_num += 1
            chunk = raw[chunk_i * CHUNK_SIZE: (chunk_i + 1) * CHUNK_SIZE]
            tag = f"budget_r{round_i}_c{chunk_i}"
            cache_path = BATCH_DIR / f"{tag}.json"
            if not cache_path.exists():
                batch = [{"id": r["id"], "question": r["question"],
                          "reference_answer": r["reference_answer"],
                          "student_answer": r["student_answer"]} for r in chunk]
                prompt = build_prompt(batch)
                call_batched(client, "", prompt, tag, temperature=0.7)

            result = json.loads(cache_path.read_text())
            scores = result["parsed"].get("scores", result["parsed"])
            for r in chunk:
                v = scores.get(r["id"])
                if v is not None:
                    attempts[r["id"]].append(float(v))
                else:
                    print(f"    [warn] no score for {r['id']} in {tag}", flush=True)

            elapsed = time.time() - t_start
            print(f"[{batch_num}/{total_batches}] round {round_i+1}/{N_ROUNDS} "
                  f"batch {chunk_i+1}/{n_chunks} done -- elapsed {elapsed:.0f}s", flush=True)

    # Aggregate: median of 7 attempts per sample, nearest 0.25
    import statistics
    import numpy as np
    from scipy.stats import wilcoxon

    results = []
    for r in raw:
        atts = attempts[r["id"]]
        if len(atts) < N_ROUNDS:
            print(f"[warn] {r['id']} only has {len(atts)}/{N_ROUNDS} attempts")
        median_score = round(statistics.median(atts) * 4) / 4 if atts else None
        c = cached[r["id"]]
        results.append({
            "id": r["id"], "qid": c["qid"], "human_score": c["human_score"],
            "cllm_1call": c["cllm_score"], "c5_fix": c["c5_score"],
            "cllm_x7_attempts": atts, "cllm_x7_median": median_score,
        })

    n_complete = sum(1 for r in results if r["cllm_x7_median"] is not None)
    human = np.array([r["human_score"] for r in results if r["cllm_x7_median"] is not None])
    cllm1 = np.array([r["cllm_1call"] for r in results if r["cllm_x7_median"] is not None])
    c5 = np.array([r["c5_fix"] for r in results if r["cllm_x7_median"] is not None])
    cllm7 = np.array([r["cllm_x7_median"] for r in results if r["cllm_x7_median"] is not None])

    def mae(pred):
        return float(np.mean(np.abs(human - pred)))

    mae_cllm1, mae_cllm7, mae_c5 = mae(cllm1), mae(cllm7), mae(c5)
    err_cllm1 = np.abs(human - cllm1)
    err_cllm7 = np.abs(human - cllm7)
    err_c5 = np.abs(human - c5)

    _, p_budget_helps = wilcoxon(err_cllm7, err_cllm1, alternative="less", zero_method="wilcox")
    _, p_c5_vs_x7_two = wilcoxon(err_c5, err_cllm7, alternative="two-sided", zero_method="wilcox")
    _, p_c5_vs_x7_one = wilcoxon(err_c5, err_cllm7, alternative="less", zero_method="wilcox")

    print(f"\n=== Point estimates (n={n_complete}) ===")
    print(f"  C_LLM (1 call)       MAE={mae_cllm1:.4f}")
    print(f"  C_LLM_x7 (7 calls)   MAE={mae_cllm7:.4f}")
    print(f"  C5_fix (7 calls)     MAE={mae_c5:.4f}")
    red_budget = (mae_cllm1 - mae_cllm7) / mae_cllm1 * 100
    print(f"\nC_LLM_x7 vs C_LLM: {red_budget:+.1f}% MAE change, one-tailed p={p_budget_helps:.4f}")
    red_c5_vs_x7 = (mae_cllm7 - mae_c5) / mae_cllm7 * 100 if mae_cllm7 > 0 else 0.0
    print(f"C5_fix vs C_LLM_x7 (budget-matched): {red_c5_vs_x7:+.1f}% MAE change, "
          f"two-tailed p={p_c5_vs_x7_two:.4f}, one-tailed p={p_c5_vs_x7_one:.4f}")

    out = {
        "n": n_complete, "mae_cllm_1call": mae_cllm1, "mae_cllm_x7": mae_cllm7, "mae_c5fix": mae_c5,
        "budget_alone_reduction_pct": red_budget, "budget_alone_p_one_tailed": float(p_budget_helps),
        "c5fix_vs_budget_matched_reduction_pct": red_c5_vs_x7,
        "c5fix_vs_budget_matched_p_two_tailed": float(p_c5_vs_x7_two),
        "c5fix_vs_budget_matched_p_one_tailed": float(p_c5_vs_x7_one),
        "per_sample": results,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
