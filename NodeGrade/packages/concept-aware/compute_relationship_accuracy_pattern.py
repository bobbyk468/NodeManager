#!/usr/bin/env python3
"""
compute_relationship_accuracy_pattern.py — quantifies the second
inductively-identified failure pattern: relationship_accuracy_score=0.0
(by deliberate design, Framework Fix #15) whenever a student extracts
zero relationships, which happens systematically for short single-concept
factual answers regardless of correctness. ZERO new API calls: reuses
cached Phase A extraction + ablation data.

Question: how often does "zero relationships extracted" coincide with a
genuinely correct (high human_score) answer, and what does it cost the
kg_formula score specifically via the accuracy component?
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

BASE = Path(__file__).parent


def main() -> int:
    with (BASE / "data" / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = {r["sample_id"]: r for r in json.load(f)}
    with (BASE / "data" / "ablation_three_condition_real.json").open() as f:
        abl = json.load(f)["per_sample"]

    rows = []
    for r in abl:
        a = phase_a.get(r["id"])
        if a is None:
            continue
        cg = a["concept_graph"]
        if cg.get("out_of_kg_domain"):
            continue  # separate, already-diagnosed failure mode; exclude here
        n_concepts = len(cg.get("concepts", []))
        n_rels = len(cg.get("relationships", []))
        rows.append({
            "id": r["id"], "qid": r["qid"],
            "human_score": r["human_score"], "kg_score": r["kg_score"],
            "cllm_score": r["cllm_score"],
            "n_concepts": n_concepts, "n_relationships": n_rels,
            "scores": a["comparison_result"].get("scores", {}),
        })

    print(f"In-domain samples analyzed: {len(rows)}")

    zero_rel = [r for r in rows if r["n_relationships"] == 0]
    has_rel = [r for r in rows if r["n_relationships"] > 0]
    print(f"\nZero relationships extracted: {len(zero_rel)}/{len(rows)} "
          f"({100*len(zero_rel)/len(rows):.1f}%)")
    print(f"  Mean human_score in this group: {statistics.mean(r['human_score'] for r in zero_rel):.3f}")
    print(f"  Mean human_score with relationships: {statistics.mean(r['human_score'] for r in has_rel):.3f}")

    # Are zero-relationship answers disproportionately single-concept (structurally can't have a relationship)?
    single_concept_zero_rel = [r for r in zero_rel if r["n_concepts"] <= 1]
    print(f"\nOf the {len(zero_rel)} zero-relationship cases, "
          f"{len(single_concept_zero_rel)} ({100*len(single_concept_zero_rel)/max(1,len(zero_rel)):.1f}%) "
          f"have <=1 extracted concept (structurally cannot express a relationship)")
    multi_concept_zero_rel = [r for r in zero_rel if r["n_concepts"] > 1]
    print(f"{len(multi_concept_zero_rel)} have >1 concept but still zero relationships "
          f"(a real missed-connection case, not a structural non-applicability)")

    # Focus: high-human-score (genuinely correct) zero-relationship answers
    correct_zero_rel = [r for r in zero_rel if r["human_score"] >= 4.0]
    print(f"\nZero-relationship cases with human_score>=4.0 (graded as correct/near-correct): "
          f"{len(correct_zero_rel)}/{len(zero_rel)} ({100*len(correct_zero_rel)/max(1,len(zero_rel)):.1f}%)")
    if correct_zero_rel:
        mae_kg = statistics.mean(abs(r["kg_score"] - r["human_score"]) for r in correct_zero_rel)
        mae_cllm = statistics.mean(abs(r["cllm_score"] - r["human_score"]) for r in correct_zero_rel)
        print(f"  On this subgroup: kg_score MAE={mae_kg:.3f}, C_LLM MAE={mae_cllm:.3f} "
              f"(kg_score {'WORSE' if mae_kg > mae_cllm else 'better'} by {abs(mae_kg-mae_cllm):.3f})")
        acc_scores = [r["scores"].get("relationship_accuracy_score", r["scores"].get("accuracy")) for r in correct_zero_rel]
        acc_scores = [a for a in acc_scores if a is not None]
        if acc_scores:
            print(f"  accuracy_score in this subgroup: mean={statistics.mean(acc_scores):.3f} "
                  f"(all forced to 0.0 by design if n_relationships==0)")

    # Overall MAE impact: full in-domain set, zero-rel vs has-rel
    mae_kg_zero = statistics.mean(abs(r["kg_score"] - r["human_score"]) for r in zero_rel)
    mae_kg_has = statistics.mean(abs(r["kg_score"] - r["human_score"]) for r in has_rel)
    mae_cllm_zero = statistics.mean(abs(r["cllm_score"] - r["human_score"]) for r in zero_rel)
    print(f"\nFull-group comparison:")
    print(f"  zero-relationship group: kg_score MAE={mae_kg_zero:.3f}, C_LLM MAE={mae_cllm_zero:.3f}, n={len(zero_rel)}")
    print(f"  has-relationship group:  kg_score MAE={mae_kg_has:.3f}, n={len(has_rel)}")

    out = {
        "n_total_indomain": len(rows),
        "n_zero_relationships": len(zero_rel),
        "n_single_concept_zero_rel": len(single_concept_zero_rel),
        "n_multi_concept_zero_rel": len(multi_concept_zero_rel),
        "n_correct_zero_rel_(human>=4)": len(correct_zero_rel),
        "mae_kg_zero_rel_group": mae_kg_zero,
        "mae_cllm_zero_rel_group": mae_cllm_zero,
        "mae_kg_has_rel_group": mae_kg_has,
        "mae_kg_correct_zero_rel_subgroup": mae_kg if correct_zero_rel else None,
        "mae_cllm_correct_zero_rel_subgroup": mae_cllm if correct_zero_rel else None,
    }
    out_path = BASE / "data" / "relationship_accuracy_pattern.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
