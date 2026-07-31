#!/usr/bin/env python3
"""
run_reference_answer_extraction.py — extracts concepts from the Mohler
REFERENCE answers (not student answers) for all unique in-domain questions,
using the real ConceptExtractor (same class, same prompt, same model as
all student-answer extraction this session). This is the candidate
`expected_concepts` source proposed in round 3 of the algorithm-fix
review (docs/ALGORITHM_FIX_REVIEW_REQUEST_ROUND3.md), approved by the
user after both external reviewers converged on it and after a free
manual premise check confirmed Mohler reference answers are concise
(1-3 sentences), similarly dense to student answers.

Live API spend: one call per UNIQUE in-domain question (42, per the
round-3 document's count), reusing the extraction result across all
responses to that question -- NOT one call per response. Resumable:
each result is cached to disk immediately.

Run:
    python3 run_reference_answer_extraction.py
    python3 run_reference_answer_extraction.py --status
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"
OUT_PATH = DATA / "reference_concepts_mohler.json"
LIVE_MODEL = "gemini-2.5-flash"


def _load_gemini_key() -> str:
    env_path = BASE.parent / "backend" / ".env"
    with env_path.open() as f:
        for line in f:
            m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
            if m:
                return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    from knowledge_graph.domain_graph import DomainKnowledgeGraph
    from concept_extraction.extractor import ConceptExtractor

    kg_dict = json.loads((DATA / "ds_knowledge_graph.json").read_text())
    domain_graph = DomainKnowledgeGraph.from_dict(kg_dict)
    assert len(domain_graph.get_all_relationships()) == 138

    phase_a = json.loads((DATA / "mohler_real_phaseA_signals.json").read_text())
    unique_questions: dict[str, dict] = {}
    for r in phase_a:
        if r["concept_graph"].get("out_of_kg_domain"):
            continue
        qid = r["question_id"]
        if qid not in unique_questions:
            unique_questions[qid] = {
                "question_id": qid,
                "question": r["question"],
                "reference_answer": r["reference_answer"],
            }

    print(f"Unique in-domain questions: {len(unique_questions)}")

    existing: dict[str, dict] = {}
    if OUT_PATH.exists():
        existing = {r["question_id"]: r for r in json.loads(OUT_PATH.read_text())}
        print(f"Already cached: {len(existing)}")

    if args.status:
        remaining = [qid for qid in unique_questions if qid not in existing]
        print(f"Remaining: {len(remaining)}")
        return 0

    api_key = _load_gemini_key()
    extractor = ConceptExtractor(domain_graph=domain_graph, api_key=api_key, model=LIVE_MODEL)

    results = list(existing.values())
    n_new_calls = 0
    for qid, qdata in unique_questions.items():
        if qid in existing:
            continue
        try:
            # Reuse extract(question, student_answer) with the reference
            # answer in the student_answer slot -- identical prompt/model/
            # ontology-focusing logic as all real student extractions.
            graph = extractor.extract(qdata["question"], qdata["reference_answer"])
        except Exception as e:
            print(f"  [ERROR] {qid}: {e}")
            continue
        n_new_calls += 1
        results.append({
            "question_id": qid,
            "question": qdata["question"],
            "reference_answer": qdata["reference_answer"],
            "concepts": [c.to_dict() if hasattr(c, "to_dict") else c.__dict__ for c in graph.concepts],
            "relationships": [r.to_dict() if hasattr(r, "to_dict") else r.__dict__ for r in graph.relationships],
            "domain_match_score": graph.domain_match_score,
            "out_of_kg_domain": graph.out_of_kg_domain,
        })
        print(f"  [{n_new_calls}] {qid}: {len(graph.concepts)} concepts -> "
              f"{[c.concept_id for c in graph.concepts]}")
        OUT_PATH.write_text(json.dumps(results, indent=2))

    print(f"\nNew live calls made this run: {n_new_calls}")
    print(f"Total cached: {len(results)}/{len(unique_questions)}")
    print(f"[saved] {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
