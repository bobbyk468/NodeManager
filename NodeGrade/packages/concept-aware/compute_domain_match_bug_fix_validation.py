#!/usr/bin/env python3
"""
compute_domain_match_bug_fix_validation.py — diagnoses AND fixes AND
validates, entirely offline (zero new API calls), a real bug found
during a failure-mode analysis of the pre-Verifier KG-grounded score.

ROOT CAUSE (concept_extraction/extractor.py, _build_question_ontology):
the domain-match keyword matcher tokenizes the question with
`question.lower().split()`, which does NOT strip trailing punctuation.
For a question like "What is a queue?", the token "queue?" (with the
question mark attached) is checked as a literal substring against KG
concept text -- and never matches "queue" without the punctuation. Any
question of the form "What is a <KG-concept>?" -- an entire class of
basic definitional questions -- gets domain_match_score=0.0 and is
incorrectly short-circuited to zero score by the OUT_OF_KG_DOMAIN gate,
regardless of how good the student's answer or concept extraction was.

This affects 106/1,262 real Mohler samples (8.4%), across exactly 4
questions: "What is a stack?" (E08.Q01), "What is a queue?" (E09.Q01,
E12.Q06), "What is a tree?" (E10.Q01) -- exactly the pattern predicted.

Because domain-match scoring and the deterministic KG-comparator make
NO LLM calls, this bug can be fixed and its real impact measured
entirely offline: the concepts for these 106 samples were already
correctly extracted (using the full-ontology fallback, which still
works when domain-match seeding fails) and are already cached; only the
downstream domain_match_score / out_of_kg_domain gate and the
comparator's scoring were wrong. This script re-tokenizes correctly,
re-runs the real ConfidenceWeightedComparator on the same cached
concepts, and measures the actual before/after impact on kg_score
accuracy -- a genuine, offline-validated fix, not just a diagnosed
failure mode.

Run:
    python3 compute_domain_match_bug_fix_validation.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, wilcoxon

BASE = Path(__file__).parent


def domain_match_score_FIXED(question: str, all_concepts: list) -> tuple[float, list[str]]:
    """Corrected re-implementation of _build_question_ontology's domain-match
    scoring: tokenizes with word-boundary regex (strips punctuation) instead
    of naive .split(). Everything else (the seed->score mapping formula) is
    unchanged from the original, so this isolates the punctuation bug as the
    only variable changed."""
    q_lower = question.lower()
    q_words = [w for w in re.findall(r"[a-z']+", q_lower) if len(w) > 3]

    seed_ids = []
    for c in all_concepts:
        text = f"{c.id} {c.name} {c.description} {' '.join(c.aliases or [])}".lower()
        if any(w in text for w in q_words):
            seed_ids.append(c.id)

    total_concepts = max(1, len(all_concepts))
    if seed_ids:
        raw = len(seed_ids) / total_concepts
        score = max(0.05, min(1.0, raw * 5.0 + 0.05))
    else:
        score = 0.0
    return score, seed_ids


def domain_match_score_ORIGINAL(question: str, all_concepts: list) -> tuple[float, list[str]]:
    """Exact reproduction of the ORIGINAL (buggy) tokenization, for
    side-by-side comparison / regression check against the real cached
    domain_match_score values."""
    q_lower = question.lower()
    q_words = [w for w in q_lower.split() if len(w) > 3]

    seed_ids = []
    for c in all_concepts:
        text = f"{c.id} {c.name} {c.description} {' '.join(c.aliases or [])}".lower()
        if any(w in text for w in q_words):
            seed_ids.append(c.id)

    total_concepts = max(1, len(all_concepts))
    if seed_ids:
        raw = len(seed_ids) / total_concepts
        score = max(0.05, min(1.0, raw * 5.0 + 0.05))
    else:
        score = 0.0
    return score, seed_ids


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


def main() -> int:
    import sys
    sys.path.insert(0, str(BASE))
    from concept_extraction.extractor import ExtractedConcept, ExtractedRelationship, StudentConceptGraph
    from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
    from knowledge_graph.domain_graph import DomainKnowledgeGraph

    with (BASE / "data" / "ds_knowledge_graph.json").open() as f:
        kg_data = json.load(f)
    kg = DomainKnowledgeGraph.from_dict(kg_data)
    assert kg.num_relationships == 138, f"KG drift: {kg.num_relationships}"
    all_concepts = kg.get_all_concepts()
    comparator = ConfidenceWeightedComparator(domain_graph=kg)

    with (BASE / "data" / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = json.load(f)
    with (BASE / "data" / "mohler_real_eval_results.json").open() as f:
        phase_b = {r["id"]: r for r in json.load(f)["results"]}

    # ------------------------------------------------------------------
    # Step 1: regression-check the ORIGINAL tokenization against real
    # cached domain_match_score values, to confirm the reproduction is
    # faithful before trusting the "fixed" numbers.
    # ------------------------------------------------------------------
    mismatches = 0
    checked = 0
    for r in phase_a:
        cached_score = r["concept_graph"].get("domain_match_score")
        if cached_score is None:
            continue
        repro_score, _ = domain_match_score_ORIGINAL(r["question"], all_concepts)
        checked += 1
        # cached values are round(x, 4); compare with a tolerance that
        # accounts for that rounding, not floating-point exactness.
        if abs(repro_score - cached_score) > 5e-4:
            mismatches += 1
            if mismatches <= 5:
                print(f"    [mismatch] cached={cached_score} repro={repro_score:.6f} q={r['question'][:60]!r}")
    print(f"Regression check (original tokenization vs.\\ cached values, tolerance 5e-4): "
          f"{checked - mismatches}/{checked} match ({mismatches} mismatches)")
    if mismatches > 0:
        print("  WARNING: reproduction is not a perfect match -- results below should be treated "
              "as approximate, not exact, until this is resolved.")

    # ------------------------------------------------------------------
    # Step 2: for every sample originally flagged out_of_kg_domain, apply
    # the FIXED tokenization and re-run the real comparator on the
    # already-extracted (unchanged) concepts.
    # ------------------------------------------------------------------
    affected_qids = set()
    n_flagged_original = 0
    n_flipped_to_in_domain = 0
    rows = []

    for r in phase_a:
        cg = r["concept_graph"]
        was_out_of_kg = cg.get("out_of_kg_domain", False)
        if not was_out_of_kg:
            continue
        n_flagged_original += 1
        affected_qids.add(r["question_id"])

        fixed_score, fixed_seeds = domain_match_score_FIXED(r["question"], all_concepts)
        now_in_domain = fixed_score >= 0.05

        b = phase_b.get(r["sample_id"])
        if b is None:
            continue

        if now_in_domain:
            n_flipped_to_in_domain += 1
            # Re-run the real comparator on the SAME already-extracted concepts,
            # now that the domain gate won't short-circuit it.
            concepts = [ExtractedConcept(concept_id=c["concept_id"], confidence=c["confidence"],
                                          evidence=c.get("evidence", ""), is_correct_usage=c.get("is_correct_usage", True))
                        for c in cg.get("concepts", [])]
            kept_ids = {c.concept_id for c in concepts}
            relationships = [ExtractedRelationship(source_id=rel["source_id"], target_id=rel["target_id"],
                                                     relation_type=rel.get("relation_type", ""),
                                                     confidence=rel.get("confidence", 1.0),
                                                     evidence=rel.get("evidence", ""),
                                                     is_correct=rel.get("is_correct", True),
                                                     misconception_note=rel.get("misconception_note", ""))
                              for rel in cg.get("relationships", [])
                              if rel["source_id"] in kept_ids and rel["target_id"] in kept_ids]
            sg = StudentConceptGraph(question=cg.get("question", ""), student_answer=cg.get("student_answer", ""),
                                      concepts=concepts, relationships=relationships,
                                      unmapped_terms=cg.get("unmapped_terms", []),
                                      overall_depth=cg.get("overall_depth", "surface"),
                                      domain_match_score=fixed_score)  # the fix
            new_result = comparator.compare(student_graph=sg, question=r["question"])
            new_scores = new_result.to_dict()["scores"]
        else:
            new_scores = {"concept_coverage": 0.0, "relationship_accuracy": 0.0, "integration_quality": 0.0}

        old_kg_formula = compute_kg_formula_score(
            r["comparison_result"].get("scores", {}), b["blooms_level"], b["solo_level"], r["misconceptions"])
        new_kg_formula = compute_kg_formula_score(
            new_scores, b["blooms_level"], b["solo_level"], r["misconceptions"])

        rows.append({
            "id": r["sample_id"], "qid": r["question_id"], "human_score": r["human_score"],
            "cllm_score": b["cllm_score"],
            "original_domain_match_score": cg.get("domain_match_score"),
            "fixed_domain_match_score": fixed_score,
            "now_in_domain": now_in_domain,
            "old_kg_formula_01": old_kg_formula, "new_kg_formula_01": new_kg_formula,
            "new_scores": new_scores,
        })

    print(f"\nSamples originally flagged out_of_kg_domain: {n_flagged_original}")
    print(f"Affected questions: {sorted(affected_qids)}")
    print(f"Of those, now correctly reclassified as in-domain after the fix: "
          f"{n_flipped_to_in_domain}/{n_flagged_original}")

    # ------------------------------------------------------------------
    # Step 3: quantify the impact on kg_score accuracy, for the affected
    # samples and for the dataset as a whole.
    # ------------------------------------------------------------------
    human = np.array([r["human_score"] for r in rows])
    old_kg = np.clip(np.round(np.array([r["old_kg_formula_01"] for r in rows]) * 5 * 4) / 4, 0, 5)
    new_kg = np.clip(np.round(np.array([r["new_kg_formula_01"] for r in rows]) * 5 * 4) / 4, 0, 5)
    cllm = np.array([r["cllm_score"] for r in rows])

    mae_old = float(np.mean(np.abs(human - old_kg)))
    mae_new = float(np.mean(np.abs(human - new_kg)))
    mae_cllm_affected = float(np.mean(np.abs(human - cllm)))

    print(f"\n=== Impact on the {len(rows)} affected samples (deterministic KG-formula score only) ===")
    print(f"  Before fix: MAE={mae_old:.4f}")
    print(f"  After fix:  MAE={mae_new:.4f}  ({(mae_old-mae_new)/mae_old*100:+.1f}% change)")
    print(f"  For reference, C_LLM MAE on these same samples: {mae_cllm_affected:.4f}")

    err_old = np.abs(human - old_kg)
    err_new = np.abs(human - new_kg)
    _, p = wilcoxon(err_new, err_old, alternative="less", zero_method="wilcox")
    print(f"  Wilcoxon (fix improves over no-fix), one-tailed p={p:.4f}")

    # Now compute the effect on the FULL dataset's kg_score (all 1,262 samples,
    # with these 106 corrected and the rest unchanged), for the headline number.
    with (BASE / "data" / "ablation_three_condition_real.json").open() as f:
        full_abl = json.load(f)["per_sample"]
    fixed_by_id = {r["id"]: r for r in rows}
    full_human = []
    full_old_kg = []
    full_new_kg = []
    for r in full_abl:
        full_human.append(r["human_score"])
        full_old_kg.append(r["kg_score"])
        if r["id"] in fixed_by_id:
            fr = fixed_by_id[r["id"]]
            new_val = float(np.clip(round(fr["new_kg_formula_01"] * 5 * 4) / 4, 0, 5))
            full_new_kg.append(new_val)
        else:
            full_new_kg.append(r["kg_score"])
    full_human = np.array(full_human)
    full_old_kg = np.array(full_old_kg)
    full_new_kg = np.array(full_new_kg)

    mae_full_old = float(np.mean(np.abs(full_human - full_old_kg)))
    mae_full_new = float(np.mean(np.abs(full_human - full_new_kg)))
    r_full_old = float(pearsonr(full_human, full_old_kg)[0])
    r_full_new = float(pearsonr(full_human, full_new_kg)[0])

    print(f"\n=== Impact on the FULL real Mohler kg_score (n=1,262), fixing just these 106 samples ===")
    print(f"  Before fix: MAE={mae_full_old:.4f}  r={r_full_old:.4f}")
    print(f"  After fix:  MAE={mae_full_new:.4f}  r={r_full_new:.4f}")
    print(f"  MAE change: {(mae_full_old-mae_full_new)/mae_full_old*100:+.2f}%")
    print(f"  (for reference, C_LLM MAE=1.2821, C5_fix/full-architecture MAE=1.1771)")

    err_full_old = np.abs(full_human - full_old_kg)
    err_full_new = np.abs(full_human - full_new_kg)
    _, p_full = wilcoxon(err_full_new, err_full_old, alternative="less", zero_method="wilcox")
    print(f"  Wilcoxon (fix improves full-dataset kg_score), one-tailed p={p_full:.4f}")

    out = {
        "bug_description": "domain-match tokenizer in _build_question_ontology does not strip "
                            "trailing punctuation, so questions of the form 'What is a <concept>?' "
                            "never match their own defining KG concept, causing a false "
                            "out_of_kg_domain classification.",
        "n_affected_original": n_flagged_original,
        "affected_questions": sorted(affected_qids),
        "n_flipped_to_in_domain_after_fix": n_flipped_to_in_domain,
        "affected_samples_only": {
            "mae_before_fix": mae_old, "mae_after_fix": mae_new,
            "mae_change_pct": (mae_old - mae_new) / mae_old * 100,
            "wilcoxon_p_one_tailed": float(p),
            "cllm_mae_same_samples": mae_cllm_affected,
        },
        "full_dataset_kg_score": {
            "mae_before_fix": mae_full_old, "mae_after_fix": mae_full_new,
            "r_before_fix": r_full_old, "r_after_fix": r_full_new,
            "mae_change_pct": (mae_full_old - mae_full_new) / mae_full_old * 100,
            "wilcoxon_p_one_tailed": float(p_full),
        },
        "per_sample": rows,
    }
    out_path = BASE / "data" / "domain_match_bug_fix_validation.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
