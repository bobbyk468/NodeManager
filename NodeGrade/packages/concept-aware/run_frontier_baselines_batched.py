#!/usr/bin/env python3
"""
run_frontier_baselines_batched.py -- C_LLM-style zero-shot baseline on the
real Mohler sample, run with a frontier model other than Gemini, via
OpenRouter.

Mirrors run_real_eval_phaseB_batched.py's run_cllm_batch() exactly (same
build_cllm_prompt from generate_batch_scoring_prompts.py, same CHUNK_SIZE,
same 0.25-increment rounding, same output shape) but swaps LIVE_MODEL for
one routed through OpenRouter, and writes to a model-specific output file
instead of overwriting the Gemini results.

This is the C_LLM baseline only -- NOT a re-run of the full 5-layer
C5_fix pipeline with a different model. The paper's design deliberately
keeps one model across all layers to avoid a model-choice confound
(see paper/main.tex, "Concept extraction model"); swapping models here
is scoped to the future-work item of frontier-LLM baseline comparisons
(paper/main.tex Introduction and Conclusion), not to re-running
ConceptGrade itself under a different model.

Output: data/mohler_real_eval_results_<tag>.json, shape
{"dataset", "n", "n_complete", "results": [{"id", "qid", "human_score",
"<tag>_score"}, ...]} -- same downstream shape as the Gemini results
file (mohler_real_eval_results.json) modulo the score field name, so
existing per-dataset analysis code needs only a field-name change.

Run:
    python3 run_frontier_baselines_batched.py --model claude
    python3 run_frontier_baselines_batched.py --model gpt
    python3 run_frontier_baselines_batched.py --model deepseek
    python3 run_frontier_baselines_batched.py --model claude --status
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"
PHASE_A_PATH = DATA / "mohler_real_phaseA_signals.json"

CHUNK_SIZE = 25

# tag -> OpenRouter model id
# Note: the ":batch" suffix variants OpenRouter lists (~50% cheaper) require
# their separate async batch-job endpoint (submit/poll/wait, up to ~24h
# turnaround), not the regular chat completions endpoint used here. For a
# job this size (~$0.50 total, ~$0.11 of that being Claude's batch/live
# price gap) that complexity isn't worth it, so these are the regular,
# synchronous model IDs -- cost reduction here comes entirely from the
# CHUNK_SIZE=25 request-batching below, same mechanism used for Gemini.
MODELS = {
    "claude":   "anthropic/claude-sonnet-5",
    "gpt":      "openai/gpt-5.6-terra",
    "deepseek": "deepseek/deepseek-chat-v3.1",
}


def _chunks(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield i // size, rows[i:i + size]


def _call_batched(client, model: str, user_prompt: str, batch_dir: Path, tag: str) -> dict:
    """Same retry/caching discipline as run_real_eval_phaseB_batched.py's
    _call_batched: 3 attempts, exponential backoff, cached to disk so a
    partial run resumes without re-paying for already-completed chunks."""
    from conceptgrade.llm_client import parse_llm_json

    batch_dir.mkdir(parents=True, exist_ok=True)
    cache_path = batch_dir / f"{tag}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    last_exc = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.0, max_tokens=8192,
            )
            raw_text = resp.choices[0].message.content
            parsed = parse_llm_json(raw_text)
            cache_path.write_text(json.dumps({"raw_text": raw_text, "parsed": parsed}, indent=2))
            return {"raw_text": raw_text, "parsed": parsed}
        except Exception as e:
            last_exc = e
            wait = 3 * (2 ** attempt)
            print(f"    [retry] {tag} attempt {attempt+1}/3 failed ({type(e).__name__}: {e}); "
                  f"retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"{tag}: failed after 3 retries") from last_exc


def run_baseline_batch(rows: list[dict], client, model: str, batch_dir: Path) -> dict:
    """Returns {sample_id: score}. Identical prompt/parsing logic to
    run_real_eval_phaseB_batched.py's run_cllm_batch()."""
    from generate_batch_scoring_prompts import build_cllm_prompt

    out = {}
    for chunk_i, chunk in _chunks(rows, CHUNK_SIZE):
        batch = [{"id": r["sample_id"], "question": r["question"],
                  "reference_answer": r["reference_answer"],
                  "student_answer": r["student_answer"]} for r in chunk]
        prompt = build_cllm_prompt(batch)
        tag = f"c{chunk_i}"
        result = _call_batched(client, model, prompt, batch_dir, tag)
        scores = result["parsed"].get("scores", result["parsed"])
        for r in chunk:
            v = scores.get(r["sample_id"])
            if v is None:
                print(f"    [warn] no score for {r['sample_id']} (chunk {chunk_i})")
                continue
            out[r["sample_id"]] = max(0.0, min(5.0, round(float(v) * 4) / 4))
        print(f"  chunk {chunk_i}: {len(chunk)} samples done")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, choices=sorted(MODELS.keys()))
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    tag = args.model
    model_id = MODELS[tag]
    batch_dir = DATA / f"mohler_real_eval_batches_{tag}"
    out_path = DATA / f"mohler_real_eval_results_{tag}.json"

    if not PHASE_A_PATH.exists():
        print(f"Missing {PHASE_A_PATH} -- run run_real_eval_phaseA_signals.py first.")
        return 1
    rows = json.loads(PHASE_A_PATH.read_text())
    print(f"Phase A rows available: {len(rows)}")
    print(f"Model: {model_id} (tag={tag})")

    if args.status:
        n_cached = len(list(batch_dir.glob("c*.json"))) if batch_dir.exists() else 0
        n_expected = (len(rows) + CHUNK_SIZE - 1) // CHUNK_SIZE
        print(f"Chunks cached: {n_cached}/{n_expected}")
        if out_path.exists():
            done = json.loads(out_path.read_text())
            print(f"Output written: {done['n_complete']}/{done['n']} complete")
        return 0

    from conceptgrade.llm_client import LLMClient, load_openrouter_key

    key = load_openrouter_key()
    client = LLMClient(api_key=key)

    print(f"\n[1/1] {tag} baseline (batched, chunk size {CHUNK_SIZE})...")
    scores = run_baseline_batch(rows, client, model_id, batch_dir)

    results = []
    for r in rows:
        results.append({
            "id": r["sample_id"], "qid": r["question_id"],
            "human_score": r["human_score"],
            f"{tag}_score": scores.get(r["sample_id"]),
        })

    n_complete = sum(1 for r in results if r[f"{tag}_score"] is not None)
    out_path.write_text(json.dumps({
        "dataset": "mohler_real_kg_aligned",
        "model": model_id,
        "n": len(results),
        "n_complete": n_complete,
        "results": results,
    }, indent=2))
    print(f"\nDone: {n_complete}/{len(results)} complete. Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
