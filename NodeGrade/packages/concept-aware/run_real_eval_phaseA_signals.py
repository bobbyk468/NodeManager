#!/usr/bin/env python3
"""
run_real_eval_phaseA_signals.py — Phase A of the real-Mohler re-evaluation.

Runs the per-sample, live, UNBATCHED stages for all 1,262 real
KG-aligned Mohler responses (data/mohler_real/mohler_real_kg_aligned.json):
  - Layer 1: concept extraction (3x self-consistency, matching the
    evaluated C5_fix config: extraction_confidence_threshold=0.70, the
    paper's tuned default -- NOT 0.0 as in Experiment #2's Phase 1,
    which needed the raw unfiltered signal for a tau grid search this
    run doesn't need).
  - Layer 2: KG comparison (offline, algorithmic, no LLM) against the
    frozen v1.0-expert KG (data/ds_knowledge_graph.json).
  - Layer 4: misconception detection (conditional -- skipped by
    MisconceptionDetector.detect() itself when there are no incorrect
    relationships) + false-belief detection (always 1 call).

Layers 3 (depth) and 5 (verifier), plus the C_LLM baseline, are handled
by run_real_eval_phaseB_batched.py using batched multi-sample prompts
now that Phase A's concept_graph/comparison_result are available.

Output: data/mohler_real_phaseA_signals.json (resumable/checkpointed).

Run:
    python3 run_real_eval_phaseA_signals.py
    python3 run_real_eval_phaseA_signals.py --status
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
OUT_PATH = DATA / "mohler_real_phaseA_signals.json"

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
    """Mirror conceptgrade/pipeline.py's post-extraction confidence filter
    (lines ~351-386) exactly, so Phase A produces the same filtered graph
    the live pipeline would at this threshold."""
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

    from datasets.mohler_loader import load_mohler_sample
    dataset = load_mohler_sample()

    existing: dict = {}
    if OUT_PATH.exists():
        existing = {r["sample_id"]: r for r in json.loads(OUT_PATH.read_text())}

    if args.status:
        print(f"Phase A signals: {len(existing)}/{dataset.num_samples}")
        return 0

    key = _load_gemini_key()
    extractor, comparator, misc_detector, fb_detector = _build_components(key)

    out_rows = list(existing.values())
    done_ids = set(existing.keys())

    import time

    for i, s in enumerate(dataset.samples):
        if s.sample_id in done_ids:
            continue
        print(f"[{i+1}/{dataset.num_samples}] {s.sample_id} ({s.question_id}) ...", flush=True)

        last_exc = None
        for attempt in range(3):
            try:
                concept_graph_obj = extractor.extract(question=s.question, student_answer=s.student_answer)
                concept_graph_obj = _filter_by_threshold(concept_graph_obj, EXTRACTION_CONFIDENCE_THRESHOLD)
                concept_graph = concept_graph_obj.to_dict()

                comparison = comparator.compare(student_graph=concept_graph_obj, question=s.question).to_dict()

                misc_report = misc_detector.detect(
                    question=s.question, student_answer=s.student_answer,
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

                false_beliefs = fb_detector.detect(question=s.question, student_answer=s.student_answer)
                false_beliefs_out = [
                    {"severity": fb.severity.value, "student_claim": fb.student_claim,
                     "explanation": fb.explanation} for fb in false_beliefs
                ]
                break
            except Exception as e:
                last_exc = e
                wait = 3 * (2 ** attempt)
                print(f"    [retry] {s.sample_id} attempt {attempt+1}/3 failed "
                      f"({type(e).__name__}: {e}); retrying in {wait}s")
                time.sleep(wait)
        else:
            raise RuntimeError(f"{s.sample_id}: failed after 3 retries") from last_exc

        row = {
            "sample_id": s.sample_id, "question_id": s.question_id,
            "question": s.question, "reference_answer": s.reference_answer,
            "student_answer": s.student_answer, "human_score": s.score_avg,
            "concept_graph": concept_graph, "comparison_result": comparison,
            "misconceptions": misconceptions, "false_beliefs": false_beliefs_out,
        }
        out_rows.append(row)
        OUT_PATH.write_text(json.dumps(out_rows, indent=2))
        print(f"    -> {len(concept_graph['concepts'])} concepts, "
              f"{misconceptions['total_misconceptions']} misconceptions, "
              f"{len(false_beliefs_out)} false beliefs")

    print(f"\nDone: {len(out_rows)}/{dataset.num_samples} in {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
