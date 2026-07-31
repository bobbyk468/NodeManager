#!/usr/bin/env python3
"""
compute_relationship_accuracy_fix_estimate.py — estimates the impact of a
candidate structural fix for the relationship_accuracy=0.0-by-design issue
found in compute_relationship_accuracy_pattern.py: when a student's answer
structurally cannot express a relationship (<=1 extracted concept), exclude
the accuracy dimension from the "knowledge" weighted sum instead of forcing
it to 0, renormalizing coverage/integration weights to fill the gap.

pipeline.py's exact formula (conceptgrade/pipeline.py:_compute_overall_score):
    knowledge = cov*0.45 + acc*0.35 + int*0.20
    depth     = blooms_norm*0.55 + solo_norm*0.45   [NOT cached per-sample -- excluded here]
    kg_formula_score = (knowledge*0.60 + depth*0.40) * (1 - misc_penalty)

Per-sample blooms/SOLO/misconception-penalty values are not present in the
cached Phase A signals file, so this script computes the KNOWLEDGE-component
shift exactly (fully available from cached scores), and reports a bounded
ESTIMATE (not an exact recomputation) of the final kg_formula_score impact,
assuming misc_penalty=0 (reasonable for the target subgroup: human-graded
correct answers, human_score>=4.0, unlikely to carry misconception flags).
This estimate is explicitly upper-bound-ish: the true effect will be
somewhat smaller once the unaffected depth term and any nonzero misc_penalty
are folded in via the *0.60 and *(1-misc_penalty) factors.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

BASE = Path(__file__).parent

W_COV, W_ACC, W_INT = 0.45, 0.35, 0.20


def main() -> int:
    with (BASE / "data" / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = {r["sample_id"]: r for r in json.load(f)}
    with (BASE / "data" / "ablation_three_condition_real.json").open() as f:
        abl = json.load(f)["per_sample"]

    affected = []
    for r in abl:
        a = phase_a.get(r["id"])
        if a is None:
            continue
        cg = a["concept_graph"]
        if cg.get("out_of_kg_domain"):
            continue
        n_concepts = len(cg.get("concepts", []))
        n_rels = len(cg.get("relationships", []))
        if n_rels != 0 or n_concepts > 1:
            continue  # only the structurally-non-applicable subgroup
        scores = a["comparison_result"]["scores"]
        cov = scores["concept_coverage"]
        acc = scores["relationship_accuracy"]  # == 0.0 by construction here
        integ = scores["integration_quality"]

        knowledge_orig = cov * W_COV + acc * W_ACC + integ * W_INT
        # Renormalize over coverage+integration only (drop accuracy dimension)
        w_sum = W_COV + W_INT
        knowledge_fixed = cov * (W_COV / w_sum) + integ * (W_INT / w_sum)

        affected.append({
            "id": r["id"], "human_score": r["human_score"],
            "kg_score": r["kg_score"], "cllm_score": r["cllm_score"],
            "knowledge_orig": knowledge_orig, "knowledge_fixed": knowledge_fixed,
            "delta_knowledge": knowledge_fixed - knowledge_orig,
        })

    print(f"Structurally-non-applicable subgroup (<=1 concept, 0 relationships): n={len(affected)}")
    mean_delta_k = statistics.mean(a["delta_knowledge"] for a in affected)
    print(f"Mean knowledge-component shift from the fix: +{mean_delta_k:.4f} (0-1 scale)")

    # Bounded estimate of kg_formula_score impact assuming misc_penalty=0, depth unaffected:
    # kg_formula_delta_est = delta_knowledge * 0.60 (knowledge's weight in the final blend), on a 0-1 scale,
    # converted to the 0-5 scale used by kg_score for comparability.
    est_score_deltas = [a["delta_knowledge"] * 0.60 * 5.0 for a in affected]
    mean_est_delta = statistics.mean(est_score_deltas)
    print(f"Estimated kg_formula_score shift (0-5 scale, assuming misc_penalty=0): +{mean_est_delta:.3f}")

    # Apply the estimated shift and see the MAE impact on this subgroup
    orig_mae = statistics.mean(abs(a["kg_score"] - a["human_score"]) for a in affected)
    est_fixed_scores = [min(5.0, a["kg_score"] + d) for a, d in zip(affected, est_score_deltas)]
    est_fixed_mae = statistics.mean(abs(s - a["human_score"]) for s, a in zip(est_fixed_scores, affected))
    cllm_mae = statistics.mean(a["cllm_score"] - 0 if False else abs(a["cllm_score"] - a["human_score"]) for a in affected)
    print(f"\nOn this subgroup (n={len(affected)}):")
    print(f"  kg_score MAE, current (accuracy forced to 0):        {orig_mae:.3f}")
    print(f"  kg_score MAE, ESTIMATED after fix (upper-bound-ish): {est_fixed_mae:.3f}")
    print(f"  C_LLM MAE (comparison target):                       {cllm_mae:.3f}")
    print(f"\nCaveat: this is an estimate of the knowledge-component effect only (exact, cached),")
    print(f"projected onto the final score assuming misc_penalty=0 and depth held constant.")
    print(f"It is NOT a re-run of the real pipeline scoring function end-to-end (blooms/SOLO/misc")
    print(f"penalty per-sample are not present in the cached Phase A file), so treat the final-score")
    print(f"MAE figures above as directional, not as precise as the domain-match bug-fix validation.")

    out_path = BASE / "data" / "relationship_accuracy_fix_estimate.json"
    out_path.write_text(json.dumps({
        "n_affected": len(affected),
        "mean_delta_knowledge": mean_delta_k,
        "mean_estimated_score_delta_0to5": mean_est_delta,
        "orig_mae_subgroup": orig_mae,
        "estimated_fixed_mae_subgroup": est_fixed_mae,
        "cllm_mae_subgroup": cllm_mae,
        "caveat": "Estimate assumes misc_penalty=0 and depth unaffected; blooms/SOLO/misc "
                  "per-sample values not present in cached Phase A file, so this is NOT an "
                  "exact end-to-end pipeline re-run like the domain-match bug-fix validation.",
    }, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
