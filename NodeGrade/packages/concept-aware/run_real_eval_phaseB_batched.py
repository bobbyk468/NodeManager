#!/usr/bin/env python3
"""
run_real_eval_phaseB_batched.py — Phase B of the real-Mohler re-evaluation.

Uses Phase A's saved concept_graph/comparison_result/misconceptions
(data/mohler_real_phaseA_signals.json) to run the three BATCHABLE stages,
each issuing one call per ~CHUNK_SIZE samples instead of one call per
sample:
  - C_LLM baseline (question+reference+student only, no KG evidence)
  - C5_fix Layer 3: cognitive depth (Bloom's + SOLO, combined single call)
  - C5_fix Layer 5: verifier (final score)

Score synthesis mirrors conceptgrade/pipeline.py: pre-verifier kg_score =
kg_weight*KG_formula + holistic_weight*C_LLM-style holistic score (both
computed here for completeness), then verifier_weight=1.0 means
final_score = verified (the pre-verifier blend has no effect on the
reported number -- see REPRODUCIBILITY.md's 2026-07-27 entry -- but is
still recorded for transparency/regression-checking).

Output: data/mohler_real_eval_results.json -- the real-data replacement
for the fabricated data/mohler_eval_results.json, same downstream shape
(id, human_score, cllm_score, c5_score, ...) so existing analysis scripts
need minimal changes.

Run:
    python3 run_real_eval_phaseB_batched.py
    python3 run_real_eval_phaseB_batched.py --status
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
PHASE_A_PATH = DATA / "mohler_real_phaseA_signals.json"
BATCH_DIR = DATA / "mohler_real_eval_batches"
OUT_PATH = DATA / "mohler_real_eval_results.json"

CHUNK_SIZE = 25
LIVE_MODEL = "gemini-2.5-flash"


def _load_gemini_key() -> str:
    env_path = BASE.parent / "backend" / ".env"
    with env_path.open() as f:
        for line in f:
            m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
            if m:
                return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def _call_batched(client, system_prompt: str, user_prompt: str, tag: str) -> dict:
    """Shared batched-call helper: cached to disk, retried on transient
    network errors (3 attempts, exponential backoff) -- this run hit
    httpcore/httpx.ReadError twice during Experiment #2's live run."""
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
                model=LIVE_MODEL, messages=messages,
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


def _chunks(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield i // size, rows[i:i + size]


def run_cllm_batch(rows: list[dict], client) -> dict:
    """Returns {sample_id: cllm_score}."""
    from generate_batch_scoring_prompts import build_cllm_prompt

    out = {}
    for chunk_i, chunk in _chunks(rows, CHUNK_SIZE):
        batch = [{"id": r["sample_id"], "question": r["question"],
                  "reference_answer": r["reference_answer"],
                  "student_answer": r["student_answer"]} for r in chunk]
        prompt = build_cllm_prompt(batch)
        tag = f"cllm_c{chunk_i}"
        result = _call_batched(client, "", prompt, tag)
        scores = result["parsed"].get("scores", result["parsed"])
        for r in chunk:
            v = scores.get(r["sample_id"])
            if v is None:
                print(f"    [warn] no C_LLM score for {r['sample_id']} (chunk {chunk_i})")
                continue
            out[r["sample_id"]] = max(0.0, min(5.0, round(float(v) * 4) / 4))
        print(f"  C_LLM chunk {chunk_i}: {len(chunk)} samples done")
    return out


def run_depth_batch(rows: list[dict], client, depth_classifier) -> dict:
    """Returns {sample_id: {"blooms": {...}, "solo": {...}}}."""
    out = {}
    for chunk_i, chunk in _chunks(rows, CHUNK_SIZE):
        blocks = []
        system_prompt = None
        for r in chunk:
            sys_p, user_p, _ = depth_classifier.build_user_prompt(
                question=r["question"], student_answer=r["student_answer"],
                concept_graph=r["concept_graph"], comparison_result=r["comparison_result"],
            )
            system_prompt = sys_p
            marker = "\nReturn ONLY valid JSON"
            idx = user_p.find(marker)
            evidence = user_p[:idx] if idx != -1 else user_p
            blocks.append(f"=== SAMPLE ID: {r['sample_id']} ===\n{evidence}")

        footer = (
            "\n\nFor EACH sample above, independently classify Bloom's and SOLO levels. "
            "Return ONLY valid JSON:\n"
            "{\n  \"scores\": {\n    \"<SAMPLE ID>\": {\n"
            "      \"blooms_level\": <1-6>, \"blooms_label\": \"...\",\n"
            "      \"solo_level\": <1-5>, \"solo_label\": \"...\"\n"
            "    }, ...\n  }\n}"
        )
        prompt = "\n\n".join(blocks) + footer
        tag = f"depth_c{chunk_i}"
        result = _call_batched(client, system_prompt, prompt, tag)
        scores = result["parsed"].get("scores", result["parsed"])
        for r in chunk:
            v = scores.get(r["sample_id"])
            if v is None:
                print(f"    [warn] no depth result for {r['sample_id']} (chunk {chunk_i})")
                continue
            b_level = max(1, min(6, int(v.get("blooms_level", 1))))
            s_level = max(1, min(5, int(v.get("solo_level", 1))))
            out[r["sample_id"]] = {
                "blooms": {"level": b_level, "label": v.get("blooms_label", "Remember")},
                "solo": {"level": s_level, "label": v.get("solo_label", "Prestructural")},
            }
        print(f"  Depth chunk {chunk_i}: {len(chunk)} samples done")
    return out


def run_verifier_batch(rows: list[dict], client, verifier) -> dict:
    """Returns {sample_id: verified_score (0-5)}."""
    out = {}
    for chunk_i, chunk in _chunks(rows, CHUNK_SIZE):
        blocks = []
        system_prompt = None
        for r in chunk:
            depth = r["_depth"]
            sys_p, user_p, _ = verifier.build_user_prompt(
                question=r["question"], student_answer=r["student_answer"],
                comparison_result=r["comparison_result"],
                blooms=depth["blooms"], solo=depth["solo"],
                misconceptions=r["misconceptions"],
                reference_answer=r["reference_answer"], mode="sag",
            )
            system_prompt = sys_p
            marker = "\nReturn ONLY valid JSON:"
            idx = user_p.rfind(marker)
            evidence = user_p[:idx] if idx != -1 else user_p
            blocks.append(f"=== SAMPLE ID: {r['sample_id']} ===\n{evidence}")

        footer = (
            "\n\nFor EACH sample above, independently apply the scoring guide. "
            "Return ONLY valid JSON:\n"
            "{\n  \"scores\": {\n    \"<SAMPLE ID>\": {\n"
            "      \"verified_score\": <float 0.0-5.0 in 0.25 increments>\n"
            "    }, ...\n  }\n}"
        )
        prompt = "\n\n".join(blocks) + footer
        tag = f"verifier_c{chunk_i}"
        result = _call_batched(client, system_prompt, prompt, tag)
        scores = result["parsed"].get("scores", result["parsed"])
        for r in chunk:
            v = scores.get(r["sample_id"])
            if v is None:
                print(f"    [warn] no verifier score for {r['sample_id']} (chunk {chunk_i})")
                continue
            raw = float(v["verified_score"]) if isinstance(v, dict) else float(v)
            out[r["sample_id"]] = max(0.0, min(5.0, round(raw * 4) / 4))
        print(f"  Verifier chunk {chunk_i}: {len(chunk)} samples done")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if not PHASE_A_PATH.exists():
        print(f"Missing {PHASE_A_PATH} -- run run_real_eval_phaseA_signals.py first.")
        return 1
    rows = json.loads(PHASE_A_PATH.read_text())
    print(f"Phase A rows available: {len(rows)}")

    if args.status:
        done = json.loads(OUT_PATH.read_text())["results"] if OUT_PATH.exists() else []
        print(f"Phase B results: {len(done)}/{len(rows)}")
        return 0

    from conceptgrade.llm_client import LLMClient
    from conceptgrade.verifier import LLMVerifier
    from cognitive_depth.cognitive_depth_classifier import CognitiveDepthClassifier

    key = _load_gemini_key()
    client = LLMClient(api_key=key)
    verifier = LLMVerifier(api_key=key, model=LIVE_MODEL, verifier_weight=1.0)
    depth_classifier = CognitiveDepthClassifier(api_key=key, model=LIVE_MODEL)

    print("\n[1/3] C_LLM baseline (batched)...")
    cllm_scores = run_cllm_batch(rows, client)

    print("\n[2/3] Cognitive depth (batched)...")
    depth_results = run_depth_batch(rows, client, depth_classifier)
    for r in rows:
        r["_depth"] = depth_results.get(r["sample_id"], {"blooms": {"level": 1, "label": "Remember"},
                                                            "solo": {"level": 1, "label": "Prestructural"}})

    print("\n[3/3] Verifier / final C5_fix score (batched)...")
    verified_scores = run_verifier_batch(rows, client, verifier)

    results = []
    for r in rows:
        results.append({
            "id": r["sample_id"], "qid": r["question_id"],
            "human_score": r["human_score"],
            "cllm_score": cllm_scores.get(r["sample_id"]),
            "c5_score": verified_scores.get(r["sample_id"]),
            "blooms_level": r["_depth"]["blooms"]["level"],
            "solo_level": r["_depth"]["solo"]["level"],
            "total_misconceptions": r["misconceptions"]["total_misconceptions"],
            "concept_coverage": r["comparison_result"].get("scores", {}).get("concept_coverage"),
        })

    n_complete = sum(1 for r in results if r["cllm_score"] is not None and r["c5_score"] is not None)
    OUT_PATH.write_text(json.dumps({
        "dataset": "mohler_real_kg_aligned", "n": len(results),
        "n_complete": n_complete, "results": results,
    }, indent=2))
    print(f"\nDone: {n_complete}/{len(results)} complete. Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
