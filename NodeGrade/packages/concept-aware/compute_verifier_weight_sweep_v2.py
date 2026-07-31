#!/usr/bin/env python3
"""
compute_verifier_weight_sweep_v2.py — Verifier-weight sweep using the
pipeline's TRUE internal kg_score (kg_weight=0.05 * KG-formula +
holistic_weight=0.95 * holistic LLM score), now that the holistic score
has been computed on real data (compute_holistic_score_batched.py).

This supersedes compute_verifier_weight_sweep.py, which used only the
pure KG-formula (equivalent to kg_weight=1.0) as an approximation because
the holistic score hadn't been computed yet. This version is the exact
pipeline.py formula, no approximation.

Run:
    python3 compute_verifier_weight_sweep_v2.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

BASE = Path(__file__).parent

KG_WEIGHT = 0.05
HOLISTIC_WEIGHT = 0.95


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
    with (BASE / "data" / "holistic_score_real.json").open() as f:
        holistic = json.load(f)

    rows = []
    for r in phase_b:
        a = phase_a[r["id"]]
        kg_formula = compute_kg_formula_score(
            a["comparison_result"].get("scores", {}),
            r["blooms_level"], r["solo_level"], a["misconceptions"],
        )
        h = holistic.get(r["id"])
        if h is None:
            continue
        true_kg_score = KG_WEIGHT * kg_formula + HOLISTIC_WEIGHT * h
        rows.append({
            "id": r["id"], "qid": r["qid"], "human_score": r["human_score"],
            "cllm_score": r["cllm_score"],
            "verified_score_01": r["c5_score"] / 5.0,
            "true_kg_score_01": true_kg_score,
            "kg_formula_only_01": kg_formula,
            "holistic_only_01": h,
        })

    human = np.array([r["human_score"] for r in rows])
    cllm = np.array([r["cllm_score"] for r in rows])
    verified = np.array([r["verified_score_01"] for r in rows]) * 5.0
    kg_true = np.array([r["true_kg_score_01"] for r in rows]) * 5.0
    kg_formula_only = np.array([r["kg_formula_only_01"] for r in rows]) * 5.0
    holistic_only = np.array([r["holistic_only_01"] for r in rows]) * 5.0

    def mae(pred):
        return float(np.mean(np.abs(human - pred)))

    print(f"n = {len(rows)}")
    print(f"C_LLM MAE                    = {mae(cllm):.4f}")
    print(f"C5_fix (w=1.0, current) MAE  = {mae(verified):.4f}")
    print(f"True kg_score alone (w=0.0) MAE = {mae(kg_true):.4f}  "
          f"(0.05*KG-formula + 0.95*holistic)")
    print(f"  -- component breakdown: KG-formula-only MAE={mae(kg_formula_only):.4f}, "
          f"holistic-LLM-only MAE={mae(holistic_only):.4f}")

    print("\nSweep: final = (1-w)*true_kg_score + w*verified")
    err_cllm = np.abs(human - cllm)
    results = []
    best = None
    for w in [1.0, 0.95, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]:
        blend = (1 - w) * kg_true + w * verified
        blend = np.clip(np.round(blend * 4) / 4, 0, 5)
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
    if best["mae"] < mae(verified) and best["verifier_weight"] < 1.0:
        print("=> A blended weight beats the current w=1.0 config.")
        err_best = np.abs(human - np.clip(np.round(((1-best['verifier_weight'])*kg_true +
                    best['verifier_weight']*verified) * 4) / 4, 0, 5))
        _, p_best_vs_current = wilcoxon(err_best, np.abs(human - verified), alternative="less", zero_method="wilcox")
        print(f"   Significance vs current w=1.0: one-tailed p={p_best_vs_current:.4f}")
    else:
        print("=> w=1.0 (current config, fully discarding kg_score) remains best.")

    out = {
        "n": len(rows), "mae_cllm": mae(cllm), "mae_verified_w1": mae(verified),
        "mae_true_kg_w0": mae(kg_true),
        "mae_kg_formula_only": mae(kg_formula_only), "mae_holistic_only": mae(holistic_only),
        "sweep": results,
    }
    out_path = BASE / "data" / "verifier_weight_sweep_v2_true_kgscore.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
