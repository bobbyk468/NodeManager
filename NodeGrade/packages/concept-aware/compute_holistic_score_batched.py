#!/usr/bin/env python3
"""
compute_holistic_score_batched.py — Batched real-data computation of the
pipeline's true internal holistic LLM score (conceptgrade/pipeline.py's
_run_llm_holistic_score), needed to reconstruct the TRUE pre-verifier
kg_score = kg_weight*KG_formula + holistic_weight*holistic_score
(default 0.05/0.95), for the verifier-weight sweep experiment.

This is a genuinely new LLM call type not yet run on real data (distinct
from C_LLM's zero-shot prompt and from the verifier's prompt). Batched in
chunks of CHUNK_SIZE samples per call (same pattern as
run_real_eval_phaseB_batched.py) to cut ~1,262 individual calls down to
~51 batched calls.

Every batch response is cached to disk immediately
(data/holistic_score_batches/*.json) so a crash or interruption loses at
most one in-flight batch, not prior progress. Final combined result:
data/holistic_score_real.json.

Run:
    python3 compute_holistic_score_batched.py
    python3 compute_holistic_score_batched.py --status
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
BATCH_DIR = DATA / "holistic_score_batches"
OUT_PATH = DATA / "holistic_score_real.json"
CHUNK_SIZE = 25
LIVE_MODEL = "gemini-2.5-flash"

BLOOM_BANDS = {
    1: (0.0, 2.0), 2: (1.0, 3.0), 3: (2.0, 4.0),
    4: (3.0, 5.0), 5: (3.5, 5.0), 6: (4.0, 5.0),
}


def _load_gemini_key() -> str:
    env_path = BASE.parent / "backend" / ".env"
    with env_path.open() as f:
        for line in f:
            m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
            if m:
                return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def build_sample_block(row: dict, phase_a: dict) -> str:
    """Mirror pipeline.py's _run_llm_holistic_score user_prompt content,
    per-sample, for inclusion in a batched multi-sample prompt."""
    a = phase_a[row["id"]]
    concepts = a["concept_graph"].get("concepts", [])
    concept_list = ", ".join(c.get("concept_id", c.get("id", "?")) for c in concepts[:10]) or "none"
    misc = a["misconceptions"]
    num_misc = misc.get("total_misconceptions", 0)
    critical = misc.get("critical_count", 0)
    scores = a["comparison_result"].get("scores", {})
    rel_accuracy = scores.get("relationship_accuracy", 0.0)
    integration = scores.get("integration_quality", 0.0)
    coverage = scores.get("concept_coverage", 0.0)
    bloom_level = row["blooms_level"]
    solo_level = row["solo_level"]
    band_min, band_max = BLOOM_BANDS.get(bloom_level, (0.5, 1.6))

    breadth_warning = ""
    if len(concepts) >= 5 and integration < 0.30:
        breadth_warning = (
            "\nWARNING: Student mentions many concepts but KG integration quality "
            f"is low ({integration:.2f}/1.0) — breadth without depth. "
            "Do NOT reward concept count alone; score for demonstrated understanding."
        )
    prose_warning = ""
    if coverage < 0.10 and len(concepts) == 0:
        prose_warning = (
            "\nWARNING: No domain concepts identified in the KG. "
            "If the answer reads well but contains no substantive CS content, score low."
        )

    return (
        f"=== SAMPLE ID: {row['id']} ===\n"
        f"QUESTION: {a['question']}\n\n"
        f"REFERENCE ANSWER (expert model answer):\n{a['reference_answer']}\n\n"
        f"STUDENT ANSWER:\n{a['student_answer']}\n\n"
        f"KNOWLEDGE GRAPH EVIDENCE (structural grounding beyond the reference):\n"
        f"- Concepts identified: {len(concepts)} ({concept_list})\n"
        f"- KG concept coverage: {coverage:.2f}/1.0\n"
        f"- KG relationship accuracy: {rel_accuracy:.2f}/1.0\n"
        f"- KG integration quality: {integration:.2f}/1.0\n"
        f"- Bloom's level: L{bloom_level}/6\n"
        f"- SOLO level: L{solo_level}/5\n"
        f"- Misconceptions: {num_misc} total, {critical} critical"
        f"{breadth_warning}{prose_warning}\n\n"
        f"Bloom's L{bloom_level} band for THIS sample: [{band_min}, {band_max}] / 5.\n"
    )


SYSTEM_PROMPT = (
    "You are an expert educator. For EACH sample below, compare the student answer "
    "to the reference answer, then score strictly within that sample's declared "
    "Bloom's band. Use KG evidence to verify depth and detect misconceptions.\n\n"
    "SCORING RUBRIC — compare student answer to reference, then constrain within Bloom's band:\n"
    "  L1 Remember:   [0.0, 2.0] / 5\n"
    "  L2 Understand: [1.0, 3.0] / 5\n"
    "  L3 Apply:      [2.0, 4.0] / 5\n"
    "  L4 Analyze:    [3.0, 5.0] / 5\n"
    "  L5 Evaluate:   [3.5, 5.0] / 5\n"
    "  L6 Create:     [4.0, 5.0] / 5\n"
    "Complete coverage of reference key points → near ceiling. "
    "Missing key points → near floor. "
    "Each critical misconception lowers score by 0.5 within band.\n\n"
    "Return ONLY valid JSON, one entry per sample:\n"
    "{\n  \"scores\": {\n    \"<SAMPLE ID>\": <float within that sample's band>,\n"
    "    ...\n  }\n}"
)


def call_batched(client, system_prompt: str, user_prompt: str, tag: str):
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
                temperature=0.1,
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

    with (DATA / "mohler_real_eval_results.json").open() as f:
        rows = json.load(f)["results"]
    with (DATA / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = {r["sample_id"]: r for r in json.load(f)}

    n_chunks = (len(rows) + CHUNK_SIZE - 1) // CHUNK_SIZE

    if args.status:
        done = len(list(BATCH_DIR.glob("holistic_c*.json"))) if BATCH_DIR.exists() else 0
        print(f"Holistic-score batches: {done}/{n_chunks}")
        return 0

    from conceptgrade.llm_client import LLMClient
    key = _load_gemini_key()
    client = LLMClient(api_key=key)

    scores: dict[str, float] = {}
    t_start = time.time()
    for chunk_i in range(n_chunks):
        chunk = rows[chunk_i * CHUNK_SIZE: (chunk_i + 1) * CHUNK_SIZE]
        tag = f"holistic_c{chunk_i}"
        cache_path = BATCH_DIR / f"{tag}.json"
        if not cache_path.exists():
            blocks = [build_sample_block(r, phase_a) for r in chunk]
            user_prompt = "\n\n".join(blocks)
            call_batched(client, SYSTEM_PROMPT, user_prompt, tag)

        result = json.loads(cache_path.read_text())
        parsed_scores = result["parsed"].get("scores", result["parsed"])
        for r in chunk:
            v = parsed_scores.get(r["id"])
            if v is None:
                print(f"    [warn] no holistic score for {r['id']} (chunk {chunk_i})", flush=True)
                continue
            scores[r["id"]] = float(v) / 5.0  # store 0-1 scale, matching pipeline convention

        elapsed = time.time() - t_start
        print(f"[{chunk_i+1}/{n_chunks}] batch done ({len(chunk)} samples) "
              f"-- elapsed {elapsed:.0f}s -- {len(scores)}/{len(rows)} scores collected", flush=True)

    OUT_PATH.write_text(json.dumps(scores, indent=2))
    print(f"\nDone: {len(scores)}/{len(rows)} holistic scores. Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
