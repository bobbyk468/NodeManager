#!/usr/bin/env python3
"""
compute_verifier_weight_sweep.py — Test whether letting the KG-computed
score actually influence the final grade (verifier_weight < 1.0) helps,
using ONLY already-collected data (zero new LLM calls).

Motivation
----------
The evaluated C5_fix configuration uses verifier_weight=1.0, meaning
final_score = verified (the LLM verifier's own judgment) with ZERO
mathematical contribution from the pre-verifier kg_score -- confirmed by
direct code inspection (conceptgrade/verifier.py:
final = (1-verifier_weight)*kg_score + verifier_weight*verified).
The KG evidence reaches the verifier only as prompt context, not as a
numeric anchor. This script tests the natural follow-up question: does
actually blending in the KG signal (verifier_weight < 1.0) improve
results relative to the untuned verifier_weight=1.0 config, or relative
to C_LLM?

What this reuses vs. approximates
----------------------------------
"verified" is exactly what's already cached as c5_score in
data/mohler_real_eval_results.json (since verifier_weight=1.0 was used
to produce it, final_score == verified_score for every real sample).

"kg_score" here is conceptgrade/pipeline.py's _compute_overall_score()
formula (concept coverage / relationship accuracy / integration,
Bloom's + SOLO depth, misconception penalty) -- fully offline-computable
from data/mohler_real_phaseA_signals.json (comparison_result,
misconceptions) and data/mohler_real_eval_results.json (blooms_level,
solo_level). This is a SIMPLIFICATION of the pipeline's true internal
kg_score (which also blends in a separate "holistic" LLM call at 0.95
weight, a call this project has not made for the real dataset) --
we use the pure deterministic KG-formula component only. This is
disclosed explicitly wherever this script's results are reported.

Run:
    python3 compute_verifier_weight_sweep.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

BASE = Path(__file__).parent


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
    with (BASE / "data" / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = {r["sample_id"]: r for r in json.load(f)}
    with (BASE / "data" / "mohler_real_eval_results.json").open() as f:
        phase_b = json.load(f)["results"]

    rows = []
    for r in phase_b:
        a = phase_a[r["id"]]
        kg_formula = compute_kg_formula_score(
            a["comparison_result"].get("scores", {}),
            r["blooms_level"], r["solo_level"],
            a["misconceptions"],
        )
        rows.append({
            "id": r["id"], "qid": r["qid"], "human_score": r["human_score"],
            "cllm_score": r["cllm_score"],
            "verified_score_01": r["c5_score"] / 5.0,  # verified == c5_score since verifier_weight was 1.0
            "kg_formula_score_01": kg_formula,  # 0-1 scale, matching verified_score_01
        })

    human = np.array([r["human_score"] for r in rows])
    cllm = np.array([r["cllm_score"] for r in rows])
    verified = np.array([r["verified_score_01"] for r in rows]) * 5.0
    kg = np.array([r["kg_formula_score_01"] for r in rows]) * 5.0

    def mae(pred):
        return float(np.mean(np.abs(human - pred)))

    print(f"n = {len(rows)}")
    print(f"C_LLM MAE          = {mae(cllm):.4f}")
    print(f"C5_fix (w=1.0) MAE = {mae(verified):.4f}   (== current paper headline)")
    print(f"Pure KG-formula MAE = {mae(kg):.4f}  (w=0.0, for reference -- expected weak, no reference-answer grounding)")

    print("\nSweep: final = (1-w)*kg_formula + w*verified")
    results = []
    err_cllm = np.abs(human - cllm)
    best = None
    for w in [1.0, 0.95, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]:
        blend = (1 - w) * kg + w * verified
        blend = np.clip(np.round(blend * 4) / 4, 0, 5)  # nearest 0.25, matching pipeline convention
        m = mae(blend)
        err_blend = np.abs(human - blend)
        _, p_vs_cllm = wilcoxon(err_blend, err_cllm, alternative="less", zero_method="wilcox")
        row = {"verifier_weight": w, "mae": m, "p_one_tailed_vs_cllm": float(p_vs_cllm)}
        results.append(row)
        marker = "  <-- current config" if w == 1.0 else ""
        print(f"  w={w:.2f}  MAE={m:.4f}  p(beats C_LLM, one-tailed)={p_vs_cllm:.4f}{marker}")
        if best is None or m < best["mae"]:
            best = row

    print(f"\nBest verifier_weight by MAE: w={best['verifier_weight']} (MAE={best['mae']:.4f})")
    if best["mae"] < mae(cllm) and best["verifier_weight"] < 1.0:
        print("=> A KG-blended weight beats both C_LLM and the current w=1.0 config.")
    elif best["verifier_weight"] == 1.0:
        print("=> w=1.0 (current config, fully discarding KG score) remains best; "
              "blending in the pure KG-formula score does not help on this data.")

    out = {
        "n": len(rows),
        "mae_cllm": mae(cllm),
        "mae_verified_w1": mae(verified),
        "mae_kg_formula_w0": mae(kg),
        "sweep": results,
        "note": "kg_formula_score is pipeline.py's _compute_overall_score() output "
                "(pure deterministic KG formula), NOT the pipeline's true internal "
                "pre-verifier kg_score (which also blends a separate holistic LLM "
                "call at 0.95 weight -- not run for the real dataset). See script docstring.",
    }
    out_path = BASE / "data" / "verifier_weight_sweep.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
