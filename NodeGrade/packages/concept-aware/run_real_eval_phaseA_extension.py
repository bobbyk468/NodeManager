#!/usr/bin/env python3
"""
run_real_eval_phaseA_extension.py — Phase A for the 109-response,
4-question EXTENSION to the real KG-aligned Mohler subset (2026-07-28).

Mirrors run_real_eval_phaseA_signals.py exactly (same extraction config,
same confidence threshold, same components), but loads from
data/mohler_real/mohler_real_kg_extension.json instead of the frozen
46-question file, and writes to a separate output file so the original
Phase A signals file (the reproducibility anchor for every number in the
paper so far) is never touched.

Output: data/mohler_real_extension_phaseA_signals.json (resumable/checkpointed).

Run:
    python3 run_real_eval_phaseA_extension.py
    python3 run_real_eval_phaseA_extension.py --status
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
EXT_PATH = DATA / "mohler_real" / "mohler_real_kg_extension.json"
OUT_PATH = DATA / "mohler_real_extension_phaseA_signals.json"

EXTRACTION_CONFIDENCE_THRESHOLD = 0.70  # matches the paper's tuned default


def _load_gemini_key() -> str:
    env_path = BASE.parent / "backend" / ".env"
    with env_path.open() as f:
        for line in f:
            m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
            if m:
                return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def _build_components(key: str):
    from concept_extraction.self_consistent_extractor import SelfConsistentExtractor
    from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
    from misconception_detection.detector import MisconceptionDetector, FalseBeliefDetector
    from knowledge_graph.domain_graph import DomainKnowledgeGraph

    with (DATA / "ds_knowledge_graph.json").open() as f:
        kg_data = json.load(f)
    frozen_v1_kg = DomainKnowledgeGraph.from_dict(kg_data)
    assert frozen_v1_kg.num_relationships == 138, (
        f"Expected frozen v1.0-expert KG (138 rel), got {frozen_v1_kg.num_relationships}"
    )

    extractor = SelfConsistentExtractor(
        domain_graph=frozen_v1_kg, api_key=key, model="gemini-2.5-flash",
        n_runs=3, min_votes=2, inter_run_delay=1.0,
    )
    comparator = ConfidenceWeightedComparator(domain_graph=frozen_v1_kg)
    misc_detector = MisconceptionDetector(api_key=key, model="gemini-2.5-flash")
    fb_detector = FalseBeliefDetector(api_key=key, model="gemini-2.5-flash")
    return extractor, comparator, misc_detector, fb_detector


def _filter_by_threshold(concept_graph_obj, threshold: float):
    raw_concepts = concept_graph_obj.concepts if isinstance(concept_graph_obj.concepts, list) else []
    filtered_concepts = [c for c in raw_concepts if c.confidence >= threshold]
    concept_ids = {c.concept_id for c in filtered_concepts}
    filtered_relationships = [
        r for r in (concept_graph_obj.relationships or [])
        if r.source_id in concept_ids and r.target_id in concept_ids
    ]
    concept_graph_obj.concepts = filtered_concepts
    concept_graph_obj.relationships = filtered_relationships
    return concept_graph_obj


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    with EXT_PATH.open() as f:
        ext = json.load(f)
    samples = ext["samples"]

    existing: dict = {}
    if OUT_PATH.exists():
        existing = {r["sample_id"]: r for r in json.loads(OUT_PATH.read_text())}

    if args.status:
        print(f"Extension Phase A signals: {len(existing)}/{len(samples)}")
        return 0

    key = _load_gemini_key()
    extractor, comparator, misc_detector, fb_detector = _build_components(key)

    out_rows = list(existing.values())
    done_ids = set(existing.keys())

    t_start = time.time()
    for i, s in enumerate(samples):
        sid = s["id"]
        if sid in done_ids:
            continue
        elapsed = time.time() - t_start
        print(f"[{i+1}/{len(samples)}] {sid} ({s['qid']}) ... elapsed {elapsed:.0f}s", flush=True)

        last_exc = None
        for attempt in range(3):
            try:
                concept_graph_obj = extractor.extract(question=s["question"], student_answer=s["student_answer"])
                concept_graph_obj = _filter_by_threshold(concept_graph_obj, EXTRACTION_CONFIDENCE_THRESHOLD)
                concept_graph = concept_graph_obj.to_dict()

                comparison = comparator.compare(student_graph=concept_graph_obj, question=s["question"]).to_dict()

                misc_report = misc_detector.detect(
                    question=s["question"], student_answer=s["student_answer"],
                    concept_graph=concept_graph, comparison_result=comparison,
                )
                misconceptions = {
                    "total_misconceptions": misc_report.total_misconceptions,
                    "critical_count": misc_report.critical_count,
                    "moderate_count": misc_report.moderate_count,
                    "minor_count": misc_report.minor_count,
                    "overall_accuracy": misc_report.overall_accuracy,
                    "summary": misc_report.summary,
                    "misconceptions": [
                        {"severity": m.severity.value, "description": m.explanation,
                         "student_claim": m.student_claim} for m in misc_report.misconceptions
                    ],
                }

                false_beliefs = fb_detector.detect(question=s["question"], student_answer=s["student_answer"])
                false_beliefs_out = [
                    {"severity": fb.severity.value, "student_claim": fb.student_claim,
                     "explanation": fb.explanation} for fb in false_beliefs
                ]
                break
            except Exception as e:
                last_exc = e
                wait = 3 * (2 ** attempt)
                print(f"    [retry] {sid} attempt {attempt+1}/3 failed "
                      f"({type(e).__name__}: {e}); retrying in {wait}s", flush=True)
                time.sleep(wait)
        else:
            raise RuntimeError(f"{sid}: failed after 3 retries") from last_exc

        row = {
            "sample_id": sid, "question_id": s["qid"],
            "question": s["question"], "reference_answer": s["reference_answer"],
            "student_answer": s["student_answer"], "human_score": s["score_avg"],
            "concept_graph": concept_graph, "comparison_result": comparison,
            "misconceptions": misconceptions, "false_beliefs": false_beliefs_out,
        }
        out_rows.append(row)
        OUT_PATH.write_text(json.dumps(out_rows, indent=2))
        print(f"    -> {len(concept_graph['concepts'])} concepts, "
              f"{misconceptions['total_misconceptions']} misconceptions, "
              f"{len(false_beliefs_out)} false beliefs, out_of_kg={concept_graph.get('out_of_kg_domain')}",
              flush=True)

        if (i + 1) % 10 == 0:
            print(f"    [status] {i+1}/{len(samples)} done, {time.time()-t_start:.0f}s elapsed", flush=True)

    print(f"\nDone: {len(out_rows)}/{len(samples)} in {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
