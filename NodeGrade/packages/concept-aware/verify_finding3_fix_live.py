#!/usr/bin/env python3
"""
verify_finding3_fix_live.py — end-to-end validation of the live Finding-3
fix (coverage_validated flag + pipeline.py knowledge-formula exclusion)
against all 1,156 in-domain cached real Mohler samples. ZERO new API
calls: re-runs the REAL, now-patched ConfidenceWeightedComparator.compare()
on already-extracted (unchanged) concepts, then the REAL, now-patched
pipeline.py knowledge-formula logic (reproduced here at the "knowledge"
sub-score level, since _compute_overall_score also needs blooms/SOLO/misc
data not cached at this granularity -- see round-1 caveat, same limitation
as the earlier Finding 2 estimate).
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np

from knowledge_graph.domain_graph import DomainKnowledgeGraph
from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
from concept_extraction.extractor import StudentConceptGraph, ExtractedConcept, ExtractedRelationship

BASE = Path(__file__).parent
W_COV, W_ACC, W_INT = 0.45, 0.35, 0.20


def main() -> int:
    kg_dict = json.loads((BASE / "data" / "ds_knowledge_graph.json").read_text())
    domain_graph = DomainKnowledgeGraph.from_dict(kg_dict)
    assert len(domain_graph.get_all_relationships()) == 138

    comparator = ConfidenceWeightedComparator(domain_graph=domain_graph)

    phase_a = json.loads((BASE / "data" / "mohler_real_phaseA_signals.json").read_text())
    abl = {r["id"]: r for r in json.loads((BASE / "data" / "ablation_three_condition_real.json").read_text())["per_sample"]}

    rows = []
    n_flagged_unvalidated = 0
    for r in phase_a:
        cg = r["concept_graph"]
        if cg.get("out_of_kg_domain"):
            continue
        sg = StudentConceptGraph(
            question=r["question"], student_answer=r["student_answer"],
            concepts=[ExtractedConcept(**c) for c in cg["concepts"]],
            relationships=[ExtractedRelationship(**rel) for rel in cg["relationships"]],
            domain_match_score=cg["domain_match_score"],
        )
        # Live call: real compare(), no expected_concepts -- the actual
        # production call shape (conceptgrade/pipeline.py:476).
        result = comparator.compare(student_graph=sg)
        d = result.to_dict()
        scores = d["scores"]
        if not scores.get("coverage_validated", True):
            n_flagged_unvalidated += 1

        cov = scores["concept_coverage"]
        acc = scores["relationship_accuracy"]
        integ = scores["integration_quality"]

        if scores.get("coverage_validated", True):
            know_new = cov * W_COV + acc * W_ACC + integ * W_INT
        else:
            w_sum = W_ACC + W_INT
            know_new = acc * (W_ACC / w_sum) + integ * (W_INT / w_sum)
        know_old = cov * W_COV + acc * W_ACC + integ * W_INT  # pre-fix formula, same cached scores

        cllm_err = abs(abl[r["sample_id"]]["cllm_score"] - r["human_score"]) if r["sample_id"] in abl else None
        rows.append({
            "id": r["sample_id"], "human": r["human_score"],
            "know_old": know_old, "know_new": know_new, "cllm_err": cllm_err,
        })

    print(f"In-domain samples: {len(rows)}")
    print(f"Flagged coverage_validated=False (expected: ALL, since compare() called with no expected_concepts): "
          f"{n_flagged_unvalidated}/{len(rows)}")
    print(f"  -> {'PASS' if n_flagged_unvalidated == len(rows) else 'FAIL'}")

    human = np.array([r["human"] for r in rows])
    know_old = np.array([r["know_old"] for r in rows]) * 5.0
    know_new = np.array([r["know_new"] for r in rows]) * 5.0

    mae_old = float(np.mean(np.abs(know_old - human)))
    mae_new = float(np.mean(np.abs(know_new - human)))
    r_old = float(np.corrcoef(know_old, human)[0, 1])
    r_new = float(np.corrcoef(know_new, human)[0, 1])

    print(f"\nKnowledge-component (0-5 scale) MAE vs human:")
    print(f"  before fix (coverage always trusted): {mae_old:.3f}")
    print(f"  after fix  (coverage excluded, renormalized): {mae_new:.3f}")
    print(f"Pearson r vs human:")
    print(f"  before: {r_old:.4f}   after: {r_new:.4f}")

    # Hard-case check (consistent with round-4's methodology)
    hard = [i for i, r in enumerate(rows) if r["cllm_err"] is not None and r["cllm_err"] > 1.0]
    easy = [i for i, r in enumerate(rows) if r["cllm_err"] is not None and r["cllm_err"] <= 1.0]
    for label, idx in [("hard (C_LLM wrong)", hard), ("easy (C_LLM right)", easy)]:
        h = human[idx]
        mae_o = float(np.mean(np.abs(know_old[idx] - h)))
        mae_n = float(np.mean(np.abs(know_new[idx] - h)))
        print(f"  {label}: n={len(idx)}  before MAE={mae_o:.3f}  after MAE={mae_n:.3f}")

    # FPR check
    high_q = human >= 4.0
    know_new_frac = know_new / 5.0
    fpr_new = float(np.mean(know_new_frac[high_q] < 0.5))
    know_old_frac = know_old / 5.0
    fpr_old = float(np.mean(know_old_frac[high_q] < 0.5))
    print(f"\nFalse Penalty Rate on human>=4.0 (n={int(high_q.sum())}): before={fpr_old:.4f} after={fpr_new:.4f}")

    out_path = BASE / "data" / "finding3_fix_live_validation.json"
    out_path.write_text(json.dumps({
        "n_samples": len(rows), "n_flagged_unvalidated": n_flagged_unvalidated,
        "mae_before": mae_old, "mae_after": mae_new,
        "pearson_r_before": r_old, "pearson_r_after": r_new,
        "fpr_before": fpr_old, "fpr_after": fpr_new,
    }, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
