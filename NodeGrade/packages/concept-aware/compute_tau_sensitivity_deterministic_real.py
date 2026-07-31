#!/usr/bin/env python3
"""
compute_tau_sensitivity_deterministic_real.py — confidence-threshold (tau)
sensitivity sweep for the DETERMINISTIC KG-comparison layer, real Mohler
data, ZERO new API calls.

Background: the original Experiment #2 design (question-held-out CV
retuning of tau) needs new LLM calls for two reasons: (1) tau < 0.70
requires fresh extraction, since Phase A discarded sub-0.70-confidence
concepts before saving (confirmed by direct inspection); (2) even for
tau >= 0.70, the pipeline's holistic-LLM score and verifier score both
embed the tau-filtered concept list directly in their prompts (covered
concepts, missing concepts, coverage numbers), so a genuine re-grade at
a different tau needs fresh LLM calls for both stages.

However, one layer is fully offline-reconstructable: the deterministic
KG-comparison (graph_comparison/confidence_weighted_comparator.py,
ConfidenceWeightedComparator.compare()) has NO LLM calls -- it is pure
networkx graph matching against the frozen KG. Phase A already stored
every extracted concept at every confidence value >= 0.70 (the
extraction floor), so re-filtering at higher tau and re-running the
same comparator used live reproduces exactly what the deterministic
layer would output at that tau, offline.

This does NOT tell us how C5_fix (verifier-driven) would change with
tau -- only how the pre-verifier deterministic layer's coverage/
accuracy/integration and downstream kg_formula score respond to
stricter confidence filtering.

Run:
    python3 compute_tau_sensitivity_deterministic_real.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from concept_extraction.extractor import ExtractedConcept, ExtractedRelationship, StudentConceptGraph
from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
from knowledge_graph.domain_graph import DomainKnowledgeGraph


def compute_kg_formula_score(comparison_scores: dict, blooms_level: int, solo_level: int,
                               misconceptions: dict) -> float:
    """Exact port of conceptgrade/pipeline.py's _compute_overall_score()."""
    concept_coverage = comparison_scores.get("concept_coverage", 0)
    rel_accuracy = comparison_scores.get("relationship_accuracy", 0)
    integration = comparison_scores.get("integration_quality", 0)
    blooms_normalized = (blooms_level - 1) / 5
    solo_normalized = (solo_level - 1) / 4
    n_misc = misconceptions.get("total_misconceptions", 0)
    critical = misconceptions.get("critical_count", 0)
    misc_penalty = min(0.30, n_misc * 0.06 + critical * 0.10)
    knowledge = concept_coverage * 0.45 + rel_accuracy * 0.35 + integration * 0.20
    depth = blooms_normalized * 0.55 + solo_normalized * 0.45
    score = (knowledge * 0.60 + depth * 0.40) * (1.0 - misc_penalty)
    return min(1.0, max(0.0, score))


def rebuild_student_graph(sample_id: str, cg: dict, tau: float) -> StudentConceptGraph:
    concepts = [
        ExtractedConcept(
            concept_id=c["concept_id"], confidence=c["confidence"],
            evidence=c.get("evidence", ""), is_correct_usage=c.get("is_correct_usage", True),
        )
        for c in cg.get("concepts", []) if c["confidence"] >= tau
    ]
    kept_ids = {c.concept_id for c in concepts}
    relationships = [
        ExtractedRelationship(
            source_id=r["source_id"], target_id=r["target_id"],
            relation_type=r.get("relation_type", ""), confidence=r.get("confidence", 1.0),
            evidence=r.get("evidence", ""), is_correct=r.get("is_correct", True),
            misconception_note=r.get("misconception_note", ""),
        )
        for r in cg.get("relationships", [])
        if r["source_id"] in kept_ids and r["target_id"] in kept_ids
    ]
    return StudentConceptGraph(
        question=cg.get("question", ""), student_answer=cg.get("student_answer", ""),
        concepts=concepts, relationships=relationships,
        unmapped_terms=cg.get("unmapped_terms", []), overall_depth=cg.get("overall_depth", "surface"),
        domain_match_score=cg.get("domain_match_score", 1.0),
    )


def main() -> int:
    with (BASE / "data" / "ds_knowledge_graph.json").open() as f:
        kg_data = json.load(f)
    frozen_kg = DomainKnowledgeGraph.from_dict(kg_data)
    assert frozen_kg.num_relationships == 138, f"KG drift: {frozen_kg.num_relationships}"
    comparator = ConfidenceWeightedComparator(domain_graph=frozen_kg)

    with (BASE / "data" / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = json.load(f)
    with (BASE / "data" / "mohler_real_eval_results.json").open() as f:
        phase_b = {r["id"]: r for r in json.load(f)["results"]}

    taus = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
    per_tau_rows = {t: [] for t in taus}

    for a in phase_a:
        sid = a["sample_id"]
        b = phase_b.get(sid)
        if b is None:
            continue
        cg = a["concept_graph"]
        for tau in taus:
            sg = rebuild_student_graph(sid, cg, tau)
            cmp_result = comparator.compare(student_graph=sg, question=cg.get("question", ""))
            cmp_dict = cmp_result.to_dict()["scores"]
            kg_formula = compute_kg_formula_score(
                cmp_dict, b["blooms_level"], b["solo_level"], a["misconceptions"],
            )
            per_tau_rows[tau].append({
                "id": sid, "qid": b["qid"], "human_score": b["human_score"],
                "concept_coverage": cmp_dict.get("concept_coverage", 0.0),
                "relationship_accuracy": cmp_dict.get("relationship_accuracy", 0.0),
                "integration_quality": cmp_dict.get("integration_quality", 0.0),
                "kg_formula_score_01": kg_formula,
                "n_concepts_kept": len(sg.concepts),
            })

    print(f"n = {len(per_tau_rows[0.70])}")
    print("\nSweep: deterministic KG-formula score under stricter confidence filtering")
    results = []
    for tau in taus:
        rows = per_tau_rows[tau]
        human = np.array([r["human_score"] for r in rows])
        kgf = np.array([r["kg_formula_score_01"] for r in rows]) * 5.0
        kgf = np.clip(np.round(kgf * 4) / 4, 0, 5)
        mae = float(np.mean(np.abs(human - kgf)))
        r_corr = float(np.corrcoef(human, kgf)[0, 1]) if np.std(kgf) > 0 else float("nan")
        avg_cov = float(np.mean([r["concept_coverage"] for r in rows]))
        avg_n_concepts = float(np.mean([r["n_concepts_kept"] for r in rows]))
        marker = "  <-- extraction floor (all Phase A data)" if tau == 0.70 else ""
        print(f"  tau={tau:.2f}  MAE={mae:.4f}  r={r_corr:.4f}  "
              f"avg_coverage={avg_cov:.4f}  avg_n_concepts_kept={avg_n_concepts:.2f}{marker}")
        results.append({"tau": tau, "mae": mae, "r": r_corr, "avg_coverage": avg_cov,
                         "avg_n_concepts_kept": avg_n_concepts})

    out = {"n": len(per_tau_rows[0.70]), "sweep": results,
           "note": "Deterministic KG-comparison layer only (pre-holistic, pre-verifier). "
                   "Does not reflect how C5_fix (verifier-driven) would respond to tau, "
                   "since the holistic and verifier prompts both embed tau-filtered "
                   "concept evidence and were not re-run at these tau values."}
    out_path = BASE / "data" / "tau_sensitivity_deterministic_real.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
