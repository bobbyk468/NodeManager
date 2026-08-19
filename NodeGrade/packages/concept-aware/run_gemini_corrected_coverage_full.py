#!/usr/bin/env python3
"""
run_gemini_corrected_coverage_full.py -- a genuine architecture-level
fix, not another prompt-wording variant: replaces the tautological
concept_coverage evidence (Finding 3 -- "expected concepts" defaults to
the student's own extracted concepts, so it's inflated for ~36% of
samples) with REAL reference-answer-grounded coverage, computed offline
from data/reference_concepts_mohler.json (42 questions, already cached
from Finding 3's investigation -- ConceptExtractor.extract() run for
real on each question's reference answer).

Finding 3 tested this exact reference-grounded coverage once before, but
only as an input to the old NUMERIC FORMULA blend, where it made things
worse (MAE +14%). That result doesn't transfer here: this project has
since found the numeric formula is dead weight regardless of what feeds
it (Finding 4), and that the verifier's OWN judgment over evidence
presented in-context behaves completely differently (Finding 5). This
tests reference-grounded coverage as verifier evidence-in-context for
the first time.

The chain/relationship-coverage evidence (Finding 2, still unfixed) keeps
its existing targeted-skepticism caveat. Only the concept-coverage lines
are replaced.

Run:
    python3 run_gemini_corrected_coverage_full.py [--n N]
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
REF_CONCEPTS_PATH = DATA / "reference_concepts_mohler.json"
BATCH_DIR = DATA / "mohler_real_verifier_corrected_cov_batches"
OUT_PATH = DATA / "mohler_real_verifier_corrected_cov.json"

CHUNK_SIZE = 25
LIVE_MODEL = "gemini-2.5-flash"

BLOOMS_LABELS = {1: "Remember", 2: "Understand", 3: "Apply", 4: "Analyze", 5: "Evaluate", 6: "Create"}
SOLO_LABELS = {1: "Prestructural", 2: "Unistructural", 3: "Multistructural", 4: "Relational", 5: "Extended Abstract"}

CHAIN_SKEPTICISM_NOTE = (
    "\n\nNOTE on the evidence below: \"Concepts the student demonstrated\" and "
    "\"missing\" concepts have been verified against the reference answer's "
    "actual key concepts and can be trusted. \"Causal chain coverage\" is "
    "LESS reliable: it can show as zero or low even for a fully correct "
    "answer that never needed to state an explicit causal relationship "
    "between two concepts. Do NOT penalize the student for low chain "
    "coverage unless the reference answer itself required explaining such "
    "a relationship.\n"
)


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


def compute_corrected_coverage(student_concepts: set, ref_concepts: set) -> tuple[str, str]:
    if not ref_concepts:
        return "(reference concept set unavailable for this question)", "(unavailable)"
    matched = ref_concepts & student_concepts
    missing = ref_concepts - student_concepts
    matched_str = ", ".join(sorted(matched)) if matched else "none"
    missing_str = ", ".join(sorted(missing)) if missing else "none"
    return matched_str, missing_str


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

            # Replace the generic Finding-5 skepticism paragraph (if present)
            # with the chain-specific note, and surgically replace the
            # concept-coverage lines with corrected, reference-grounded values.
            generic_marker = "IMPORTANT — the KNOWLEDGE GRAPH EVIDENCE below was extracted"
            kg_marker = "KNOWLEDGE GRAPH EVIDENCE:"
            gpos = evidence.find(generic_marker)
            kpos = evidence.find(kg_marker)
            if gpos != -1 and kpos != -1:
                evidence = evidence[:gpos] + CHAIN_SKEPTICISM_NOTE.strip() + "\n\n" + evidence[kpos:]
            elif kpos != -1:
                evidence = evidence[:kpos] + CHAIN_SKEPTICISM_NOTE.strip() + "\n\n" + evidence[kpos:]

            matched_str, missing_str = r["_corrected_coverage"]
            evidence = re.sub(
                r"- Concepts the student demonstrated:.*",
                f"- Concepts the student demonstrated (verified against reference answer): {matched_str}",
                evidence,
            )
            evidence = re.sub(
                r"- Additional reference topics not addressed by student:.*",
                f"- Reference concepts the student did NOT demonstrate: {missing_str}",
                evidence,
            )
            evidence = re.sub(
                r"- Minor reference topics not mentioned:.*\n?",
                "",
                evidence,
            )

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
    ap.add_argument("--n", type=int, default=0)
    args = ap.parse_args()

    rows = json.loads(PHASE_A_PATH.read_text())
    if args.n:
        rows = rows[:args.n]
    existing = {r["id"]: r for r in json.loads(EXISTING_RESULTS_PATH.read_text())["results"]}
    ref_by_q = {r["question_id"]: r for r in json.loads(REF_CONCEPTS_PATH.read_text())}
    print(f"Phase A rows: {len(rows)}  reference concept sets: {len(ref_by_q)}")

    skipped_no_ref = 0
    usable_rows = []
    for r in rows:
        ex = existing.get(r["id"] if "id" in r else r["sample_id"])
        sid = r["sample_id"]
        ex = existing.get(sid)
        b_level = ex.get("blooms_level", 1) if ex else 1
        s_level = ex.get("solo_level", 1) if ex else 1
        r["_depth"] = {
            "blooms": {"level": b_level, "label": BLOOMS_LABELS.get(b_level, "Remember")},
            "solo": {"level": s_level, "label": SOLO_LABELS.get(s_level, "Prestructural")},
        }
        ref_entry = ref_by_q.get(r["question_id"])
        ref_concepts = {c["concept_id"] for c in ref_entry["concepts"] if c.get("is_correct_usage", True)} if ref_entry else set()
        if not ref_concepts:
            skipped_no_ref += 1
            continue
        student_concepts = {c["concept_id"] for c in r["concept_graph"].get("concepts", []) if c.get("is_correct_usage", True)}
        r["_corrected_coverage"] = compute_corrected_coverage(student_concepts, ref_concepts)
        usable_rows.append(r)

    print(f"Usable rows (have a real reference concept set): {len(usable_rows)}  skipped (no ref concepts): {skipped_no_ref}")

    from conceptgrade.llm_client import LLMClient
    from conceptgrade.verifier import LLMVerifier

    key = _load_gemini_key()
    client = LLMClient(api_key=key)
    verifier = LLMVerifier(api_key=key, model=LIVE_MODEL, verifier_weight=1.0)

    print("\nRunning CORRECTED-coverage verifier on Gemini...")
    verified_scores = run_verifier_batch(usable_rows, client, verifier)

    n_complete = sum(1 for r in usable_rows if r["sample_id"] in verified_scores)
    OUT_PATH.write_text(json.dumps(verified_scores, indent=2))
    print(f"\nDone: {n_complete}/{len(usable_rows)} complete. Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
