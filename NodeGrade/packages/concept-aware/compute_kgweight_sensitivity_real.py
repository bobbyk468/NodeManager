#!/usr/bin/env python3
"""
compute_kgweight_sensitivity_real.py — kg_weight sensitivity sweep on real
Mohler data, ZERO new API calls.

This is a DIFFERENT sweep from compute_verifier_weight_sweep_v2.py:
  - verifier_weight sweep: final = (1-w)*kg_score + w*verified
    (blends the pre-verifier score against the verifier's judgment)
  - kg_weight sweep (this script): kg_score = kg_weight*kg_formula +
    holistic_weight*holistic, holistic_weight = 1-kg_weight
    (blends the two components INSIDE the pre-verifier kg_score itself,
    per pipeline.py's actual constructor default kg_weight=0.05)

Both kg_formula (deterministic KG-formula score) and holistic (LLM
holistic score with KG evidence) are already cached per-sample from
earlier work in this session, so the full grid is free.

Run:
    python3 compute_kgweight_sensitivity_real.py
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
    with (BASE / "data" / "holistic_score_real.json").open() as f:
        holistic = json.load(f)

    human, kg_formula, hol = [], [], []
    for r in phase_b:
        a = phase_a[r["id"]]
        h = holistic.get(r["id"])
        if h is None:
            continue
        kf = compute_kg_formula_score(
            a["comparison_result"].get("scores", {}),
            r["blooms_level"], r["solo_level"], a["misconceptions"],
        )
        human.append(r["human_score"])
        kg_formula.append(kf)
        hol.append(h)

    human = np.array(human)
    kg_formula = np.array(kg_formula)
    hol = np.array(hol)
    n = len(human)

    def mae(pred_01):
        pred_5 = np.clip(np.round(pred_01 * 5.0 * 4) / 4, 0, 5)
        return float(np.mean(np.abs(human - pred_5)))

    err_default = None
    print(f"n = {n}")
    print("Sweep: kg_score = kg_weight*kg_formula + (1-kg_weight)*holistic")
    results = []
    for kw in [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        blend = kw * kg_formula + (1 - kw) * hol
        pred_5 = np.clip(np.round(blend * 5.0 * 4) / 4, 0, 5)
        m = float(np.mean(np.abs(human - pred_5)))
        marker = "  <-- deployed default (kg_weight=0.05)" if abs(kw - 0.05) < 1e-9 else ""
        print(f"  kg_weight={kw:.2f}  MAE={m:.4f}{marker}")
        results.append({"kg_weight": kw, "mae": m})

    best = min(results, key=lambda r: r["mae"])
    default = next(r for r in results if abs(r["kg_weight"] - 0.05) < 1e-9)
    print(f"\nDeployed default (kg_weight=0.05): MAE={default['mae']:.4f}")
    print(f"Best in sweep: kg_weight={best['kg_weight']} MAE={best['mae']:.4f}")
    if best["kg_weight"] != 0.05:
        blend_best = best["kg_weight"] * kg_formula + (1 - best["kg_weight"]) * hol
        pred_best = np.clip(np.round(blend_best * 5.0 * 4) / 4, 0, 5)
        blend_def = 0.05 * kg_formula + 0.95 * hol
        pred_def = np.clip(np.round(blend_def * 5.0 * 4) / 4, 0, 5)
        err_best = np.abs(human - pred_best)
        err_def = np.abs(human - pred_def)
        _, p = wilcoxon(err_best, err_def, alternative="less", zero_method="wilcox")
        print(f"Significance of best vs deployed default: one-tailed p={p:.4f}")
        results_meta = {"best_beats_default": True, "p_one_tailed": float(p)}
    else:
        results_meta = {"best_beats_default": False}

    out = {
        "n": n, "sweep": results, "deployed_default_kg_weight": 0.05,
        "deployed_default_mae": default["mae"], "best": best,
        **results_meta,
    }
    out_path = BASE / "data" / "kgweight_sensitivity_real.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
