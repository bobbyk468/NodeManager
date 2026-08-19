#!/usr/bin/env python3
"""
run_gemini_skeptical_verifier_full.py -- tests the Finding 5 skepticism
fix on Gemini, on the FULL 46-question, n=1,262 real Mohler dataset
(properly powered, unlike the n=300/11-question GPT/DeepSeek subsets).

Reuses ALREADY-CACHED work that doesn't depend on the verifier prompt:
extraction/comparison/misconceptions (data/mohler_real_phaseA_signals.json)
and Bloom's/SOLO depth classification (blooms_level/solo_level fields in
data/mohler_real_eval_results.json) -- neither changes when the verifier's
evidence-presentation instructions change. Only the verifier stage itself
is re-run, under conceptgrade/verifier.py's CURRENT template (which now
includes the Finding 5 skepticism instruction by default), in a fresh
batch-cache directory so it can't collide with the old cached verifier
responses computed under the pre-Finding-5 prompt.

Run:
    python3 run_gemini_skeptical_verifier_full.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"

PHASE_A_PATH = DATA / "mohler_real_phaseA_signals.json"
EXISTING_RESULTS_PATH = DATA / "mohler_real_eval_results.json"
BATCH_DIR = DATA / "mohler_real_verifier_skeptical_batches"
OUT_PATH = DATA / "mohler_real_verifier_skeptical.json"

CHUNK_SIZE = 25
LIVE_MODEL = "gemini-2.5-flash"

BLOOMS_LABELS = {1: "Remember", 2: "Understand", 3: "Apply", 4: "Analyze", 5: "Evaluate", 6: "Create"}
SOLO_LABELS = {1: "Prestructural", 2: "Unistructural", 3: "Multistructural", 4: "Relational", 5: "Extended Abstract"}


def _load_gemini_key() -> str:
    env_path = BASE.parent / "backend" / ".env"
    for line in env_path.read_text().splitlines():
        m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
        if m:
            return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def _chunks(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield i // size, rows[i:i + size]


def _call_batched(client, system_prompt: str, user_prompt: str, tag: str) -> dict:
    from conceptgrade.llm_client import parse_llm_json
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = BATCH_DIR / f"{tag}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    last_exc = None
    for attempt in range(3):
        try:
            messages = [{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}]
            resp = client.chat.completions.create(
                model=LIVE_MODEL, messages=messages, temperature=0.0, max_tokens=8192,
            )
            raw_text = resp.choices[0].message.content
            parsed = parse_llm_json(raw_text)
            cache_path.write_text(json.dumps({"raw_text": raw_text, "parsed": parsed}, indent=2))
            return {"raw_text": raw_text, "parsed": parsed}
        except Exception as e:
            last_exc = e
            wait = 3 * (2 ** attempt)
            print(f"    [retry] {tag} attempt {attempt+1}/3 failed ({type(e).__name__}: {e}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"{tag}: failed after 3 retries") from last_exc


def run_verifier_batch(rows: list[dict], client, verifier) -> dict:
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
            raw = float(v["verified_score"]) if isinstance(v, dict) and "verified_score" in v else (
                float(next(iter(v.values()))) if isinstance(v, dict) and len(v) == 1 else float(v)
            )
            out[r["sample_id"]] = max(0.0, min(5.0, round(raw * 4) / 4))
        print(f"  Verifier chunk {chunk_i}: {len(chunk)} samples done")
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="limit to first N rows (0 = all)")
    args = ap.parse_args()

    if not PHASE_A_PATH.exists():
        print(f"Missing {PHASE_A_PATH}")
        return 1
    rows = json.loads(PHASE_A_PATH.read_text())
    if args.n:
        rows = rows[:args.n]
    existing = {r["id"]: r for r in json.loads(EXISTING_RESULTS_PATH.read_text())["results"]}
    print(f"Phase A rows: {len(rows)}  existing depth data: {len(existing)}")

    for r in rows:
        ex = existing.get(r["sample_id"])
        if ex is None:
            r["_depth"] = {"blooms": {"level": 1, "label": "Remember"}, "solo": {"level": 1, "label": "Prestructural"}}
            continue
        b_level = ex.get("blooms_level", 1)
        s_level = ex.get("solo_level", 1)
        r["_depth"] = {
            "blooms": {"level": b_level, "label": BLOOMS_LABELS.get(b_level, "Remember")},
            "solo": {"level": s_level, "label": SOLO_LABELS.get(s_level, "Prestructural")},
        }

    from conceptgrade.llm_client import LLMClient
    from conceptgrade.verifier import LLMVerifier

    key = _load_gemini_key()
    client = LLMClient(api_key=key)
    verifier = LLMVerifier(api_key=key, model=LIVE_MODEL, verifier_weight=1.0)

    print("\nRunning skeptical-evidence verifier (Finding 5 prompt) on Gemini, full 1,262 samples...")
    verified_scores = run_verifier_batch(rows, client, verifier)

    n_complete = sum(1 for r in rows if r["sample_id"] in verified_scores)
    OUT_PATH.write_text(json.dumps(verified_scores, indent=2))
    print(f"\nDone: {n_complete}/{len(rows)} complete. Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
