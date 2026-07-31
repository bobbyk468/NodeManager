#!/usr/bin/env python3
"""
compute_expected_concepts_candidates.py — offline comparison of candidate
`expected_concepts` sources to fix Finding 3 (concept_coverage vacuity).
ZERO new API calls: reuses already-extracted concepts (unchanged) and the
already-fixed (Finding 1) question-KG keyword matcher.

Per the round-2 external review (Gemini + GPT), tests both candidates
offline rather than picking one by intuition, and evaluates on the full
downstream kg_formula_score (not coverage-only Pearson r, per GPT's
objection to Gemini's "maximize coverage-only r" criterion):
  (a) seed_ids     -- concepts whose id/name/description/aliases share a
                       keyword with the question text (narrow).
  (b) expanded      -- seed_ids + 1-hop KG expansion (the same set already
                       shown to the LLM as extraction context).

Both are computed using the LIVE, Finding-1-patched
`_build_question_ontology()` logic (re-derived here since that method
doesn't expose seed_ids directly, only a formatted string + side-effect
score) against the real `domain_graph.get_subgraph_for_question()`.

For each candidate, both comparator classes' coverage logic (confidence-
weighted, since that's the deployed default per conceptgrade/pipeline.py
`use_confidence_weighting=True`) is reproduced against real cached
extractions, then rolled up into pipeline.py's real
`knowledge = cov*0.45 + acc*0.35 + int*0.20` formula (accuracy/integration
held at their cached values -- only coverage's ground truth changes).

Reports, per GPT's broader-than-Pearson-r criteria:
  - Full-dataset kg-knowledge-component MAE/Pearson r vs. human_score
  - False Penalty Rate: fraction of human_score>=4.0 samples whose new
    coverage drops below 0.5 (reported, not thresholded -- GPT objected
    to Gemini's invented 5% cutoff)
  - Low-quality correction: fraction of the 18 known vacuous-coverage
    low-quality cases (human_score<=2.0) whose coverage now drops
  - Coverage score distribution (histogram) before/after, as a entropy/
    concentration check (GPT's suggestion)
"""
from __future__ import annotations

import json
import statistics
import string
from pathlib import Path

import numpy as np

from knowledge_graph.domain_graph import DomainKnowledgeGraph

BASE = Path(__file__).parent

W_COV, W_ACC, W_INT = 0.45, 0.35, 0.20


def get_seed_and_expanded(domain_graph: DomainKnowledgeGraph, question: str) -> tuple[set[str], set[str]]:
    """Reproduces the LIVE (Finding-1-fixed) tokenization + seed matching,
    then calls the real domain_graph subgraph expansion -- not a
    reimplementation of graph logic, only of the question-tokenization step
    already validated in verify_domain_match_fix_live.py."""
    q_lower = question.lower()
    q_words = [
        w for w in (t.strip(string.punctuation) for t in q_lower.split())
        if len(w) > 3
    ]
    seed_ids: set[str] = set()
    for c in domain_graph.get_all_concepts():
        text = f"{c.id} {c.name} {c.description} {' '.join(c.aliases or [])}".lower()
        if any(w in text for w in q_words):
            seed_ids.add(c.id)

    if not seed_ids:
        return seed_ids, seed_ids

    try:
        subgraph = domain_graph.get_subgraph_for_question(list(seed_ids), depth=1)
        expanded = {c.id for c in subgraph.get_all_concepts()}
    except Exception:
        expanded = set(seed_ids)
    return seed_ids, expanded


def weighted_coverage(student_concepts: set[str], expected: set[str], confidence_map: dict[str, float]) -> float:
    """Reproduces ConfidenceWeightedComparator._weighted_coverage's shape
    (confidence-weighted match ratio over expected), consistent with the
    deployed comparator (use_confidence_weighting=True by default)."""
    if not expected:
        return 0.0
    matched_weight = 0.0
    total_weight = 0.0
    for cid in expected:
        total_weight += 1.0
        if cid in student_concepts:
            matched_weight += confidence_map.get(cid, 1.0)
    return min(1.0, matched_weight / total_weight) if total_weight > 0 else 0.0


def main() -> int:
    kg_dict = json.loads((BASE / "data" / "ds_knowledge_graph.json").read_text())
    domain_graph = DomainKnowledgeGraph.from_dict(kg_dict)

    phase_a = json.loads((BASE / "data" / "mohler_real_phaseA_signals.json").read_text())

    # Cache seed/expanded sets per unique question (deterministic given question+KG)
    q_cache: dict[str, tuple[set[str], set[str]]] = {}

    rows = []
    for r in phase_a:
        cg = r["concept_graph"]
        if cg.get("out_of_kg_domain"):
            continue  # Finding 1 already fixed this; these are now the domain-match-only failures, separate concern
        q = r["question"]
        if q not in q_cache:
            q_cache[q] = get_seed_and_expanded(domain_graph, q)
        seed_ids, expanded_ids = q_cache[q]

        student_ids = {c["concept_id"] for c in cg["concepts"]}
        confidence_map = {c["concept_id"]: c["confidence"] for c in cg["concepts"]}

        scores = r["comparison_result"]["scores"]
        acc = scores["relationship_accuracy"]
        integ = scores["integration_quality"]

        cov_current = scores["concept_coverage"]  # self-referential (Finding 3)
        cov_seed = weighted_coverage(student_ids, seed_ids, confidence_map)
        cov_expanded = weighted_coverage(student_ids, expanded_ids, confidence_map)

        rows.append({
            "id": r["sample_id"], "human": r["human_score"],
            "n_seed": len(seed_ids), "n_expanded": len(expanded_ids),
            "cov_current": cov_current, "cov_seed": cov_seed, "cov_expanded": cov_expanded,
            "acc": acc, "integ": integ,
        })

    print(f"In-domain samples analyzed: {len(rows)}")
    print(f"Unique questions: {len(q_cache)}")
    empty_seed = sum(1 for s, e in q_cache.values() if not s)
    print(f"Questions with empty seed_ids (would force cov=0.0 under narrow candidate): {empty_seed}/{len(q_cache)}")

    def knowledge_scores(cov_key: str) -> list[float]:
        return [r["cov" if cov_key == "cov_current" else cov_key] * W_COV + r["acc"] * W_ACC + r["integ"] * W_INT
                for r in rows] if False else [
            r[cov_key] * W_COV + r["acc"] * W_ACC + r["integ"] * W_INT for r in rows
        ]

    human = np.array([r["human"] for r in rows])

    print("\n=== Downstream 'knowledge' component (0-1 scale), 3 candidates ===")
    results = {}
    for label, key in [("current (self-referential)", "cov_current"),
                        ("seed_ids (narrow)", "cov_seed"),
                        ("expanded (1-hop)", "cov_expanded")]:
        know = np.array(knowledge_scores(key))
        # Scale knowledge (0-1) to comparable 0-5 for MAE-vs-human context (rough, ignores depth/misc)
        know_5 = know * 5.0
        mae = float(np.mean(np.abs(know_5 - human)))
        r_val = float(np.corrcoef(know_5, human)[0, 1])
        # False Penalty Rate: human>=4.0 AND new coverage < 0.5
        cov_arr = np.array([r[key] for r in rows])
        high_q_mask = human >= 4.0
        fpr = float(np.mean(cov_arr[high_q_mask] < 0.5)) if high_q_mask.sum() else float("nan")
        # Low-quality correction: human<=2.0 samples that currently show cov==1.0
        low_q_vacuous_mask = (human <= 2.0) & (np.array([r["cov_current"] for r in rows]) == 1.0)
        n_low_q_vacuous = int(low_q_vacuous_mask.sum())
        if n_low_q_vacuous:
            corrected = float(np.mean(cov_arr[low_q_vacuous_mask] < 1.0))
        else:
            corrected = float("nan")
        results[label] = {"mae_vs_human_0to5": mae, "pearson_r": r_val, "fpr_highQ_lt0.5": fpr,
                           "low_quality_correction_rate": corrected, "n_low_quality_vacuous": n_low_q_vacuous}
        print(f"\n  [{label}]")
        print(f"    knowledge*5 MAE vs human: {mae:.3f}   Pearson r: {r_val:.4f}")
        print(f"    False Penalty Rate (human>=4.0 & new_cov<0.5): {fpr:.4f} ({int(high_q_mask.sum())} samples)")
        print(f"    Low-quality-vacuous correction rate (of {n_low_q_vacuous} known cases): {corrected:.4f}")

    print("\n=== Coverage score distribution (concentration check) ===")
    for label, key in [("current", "cov_current"), ("seed_ids", "cov_seed"), ("expanded", "cov_expanded")]:
        arr = np.array([r[key] for r in rows])
        n_at_1 = int(np.sum(arr >= 0.999))
        n_at_0 = int(np.sum(arr <= 0.001))
        print(f"  {label:10s}: mean={arr.mean():.3f} std={arr.std():.3f} "
              f"at_1.0={n_at_1}/{len(arr)} ({100*n_at_1/len(arr):.1f}%) at_0.0={n_at_0}/{len(arr)} ({100*n_at_0/len(arr):.1f}%)")

    out_path = BASE / "data" / "expected_concepts_candidates.json"
    out_path.write_text(json.dumps({"n_samples": len(rows), "n_questions": len(q_cache),
                                     "n_empty_seed_questions": empty_seed, "results": results}, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
