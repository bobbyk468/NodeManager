#!/usr/bin/env python3
"""
compute_pipeline_weight_tuning.py -- Option C: does properly tuning the
verifier blend weight rescue the GPT-backbone pipeline from Option A's
negative result (compute_pipeline_backbone_significance.py: pipeline
underperforms GPT's own zero-shot baseline at verifier_weight=1.0)?

Blends two already-cached, zero-new-API-call signals per sample:
  - kg_formula_score: the deterministic KG-formula composite (concept
    coverage / relationship accuracy / integration + Bloom's/SOLO depth +
    misconception penalty), recomputed offline via the EXACT formula in
    conceptgrade/pipeline.py's ConceptGradePipeline._compute_overall_score
    (copied verbatim below, not reimplemented from scratch, to avoid any
    drift from the real deployed formula). Adapted only in how it reads
    the misconceptions dict: run_frontier_pipeline_phaseA_batched.py
    stores "critical_count" flat, not pipeline.py's nested
    "by_severity.critical" (MisconceptionReport.to_dict() shape) -- same
    number, different key path.
  - verified_score: the LLM verifier's score from Phase B
    (run_frontier_pipeline_phaseB_batched.py), i.e. gpt_c5_score, which
    was computed at verifier_weight=1.0 (100% verifier, 0% KG blend) --
    so it IS already the pure "verified_score" component needed here.

This intentionally does NOT reproduce pipeline.py's full 3-stage cascade
(kg_formula -> +holistic_score blend -> +verifier blend), because
holistic_score requires a fresh, uncached LLM call this experiment does
not make. It directly tests the higher-level question: does blending in
the deterministic KG signal at a properly-tuned weight help, versus the
verifier alone? This is a deliberate scope choice, not an oversight --
documented here so the comparison is read correctly.

Uses 5-fold cross-validation to select the verifier_weight that
minimizes MAE against human_score, to avoid the exact failure mode
already caught and retracted once in this paper (an unjustified,
post-hoc-selected blend weight -- see REPRODUCIBILITY.md). The weight is
selected only on training folds each time; reported performance is the
held-out fold average, never the training-fold number.

Run:
    python3 compute_pipeline_weight_tuning.py --model gpt
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

BASE = Path(__file__).parent
SEED = 42
K_FOLDS = 5
WEIGHT_GRID = [round(w, 2) for w in np.arange(0.0, 1.01, 0.1)]


def compute_kg_formula_score(comparison: dict, blooms_level: int, solo_level: int,
                              misconceptions: dict) -> float:
    """Verbatim port of ConceptGradePipeline._compute_overall_score
    (conceptgrade/pipeline.py), use_hierarchical_kg=False (matches the
    non-hierarchical config used throughout this paper's real evaluation
    scripts). Only the misconceptions key path is adapted, per the module
    docstring above."""
    scores = comparison.get("scores", {})
    concept_coverage = scores.get("concept_coverage", 0)
    rel_accuracy = scores.get("relationship_accuracy", 0)
    integration = scores.get("integration_quality", 0)

    blooms_normalized = (blooms_level - 1) / 5
    solo_normalized = (solo_level - 1) / 4

    if "error" in misconceptions:
        misc_penalty = 0.0
    else:
        n_misc = misconceptions.get("total_misconceptions", 0)
        critical = misconceptions.get("critical_count", 0)  # adapted key path, see docstring
        misc_penalty = min(0.30, n_misc * 0.06 + critical * 0.10)

    knowledge = concept_coverage * 0.45 + rel_accuracy * 0.35 + integration * 0.20
    depth = blooms_normalized * 0.55 + solo_normalized * 0.45
    score = (knowledge * 0.60 + depth * 0.40) * (1.0 - misc_penalty)
    return min(1.0, max(0.0, score))


def blended_score(kg_formula_0to1: float, verified_0to5: float, w: float) -> float:
    kg_0to5 = kg_formula_0to1 * 5.0
    final = (1.0 - w) * kg_0to5 + w * verified_0to5
    return max(0.0, min(5.0, final))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, choices=["claude", "gpt", "deepseek"])
    args = ap.parse_args()
    tag = args.model

    phase_a = {r["sample_id"]: r for r in json.loads((BASE / "data" / f"{tag}_pipeline_phaseA_signals.json").read_text())}
    phase_b = json.loads((BASE / "data" / f"{tag}_pipeline_eval_results.json").read_text())
    baseline_raw = json.loads((BASE / "data" / f"mohler_real_eval_results_{tag}.json").read_text())
    baseline = {r["id"]: r[f"{tag}_score"] for r in baseline_raw["results"]}

    rows = []
    for r in phase_b["results"]:
        sid = r["id"]
        if r[f"{tag}_c5_score"] is None or sid not in phase_a or sid not in baseline:
            continue
        pa = phase_a[sid]
        kg = compute_kg_formula_score(pa["comparison_result"], r["blooms_level"], r["solo_level"], pa["misconceptions"])
        rows.append({
            "id": sid, "qid": r["qid"], "human": r["human_score"],
            "kg_formula": kg, "verified": r[f"{tag}_c5_score"], "zeroshot": baseline[sid],
        })
    n = len(rows)
    print(f"n usable samples: {n}")

    human = np.array([x["human"] for x in rows])
    kg_formula = np.array([x["kg_formula"] for x in rows])
    verified = np.array([x["verified"] for x in rows])
    zeroshot = np.array([x["zeroshot"] for x in rows])

    mae_zeroshot = float(np.abs(human - zeroshot).mean())
    mae_w1 = float(np.abs(human - verified).mean())  # w=1.0 == current deployed config == Option A's tested pipeline
    print(f"Zero-shot MAE:            {mae_zeroshot:.4f}")
    print(f"Pipeline @ w=1.0 (Opt A):  {mae_w1:.4f}")

    # 5-fold CV: select w on train folds (min MAE vs human), report held-out fold MAE only.
    rng = np.random.default_rng(SEED)
    idx = rng.permutation(n)
    folds = np.array_split(idx, K_FOLDS)

    fold_best_w = []
    fold_heldout_mae = []
    fold_heldout_mae_at_w1 = []
    for k in range(K_FOLDS):
        test_idx = folds[k]
        train_idx = np.concatenate([folds[j] for j in range(K_FOLDS) if j != k])

        train_maes = []
        for w in WEIGHT_GRID:
            pred = np.array([blended_score(kg_formula[i], verified[i], w) for i in train_idx])
            train_maes.append(np.abs(human[train_idx] - pred).mean())
        best_w = WEIGHT_GRID[int(np.argmin(train_maes))]
        fold_best_w.append(best_w)

        pred_test = np.array([blended_score(kg_formula[i], verified[i], best_w) for i in test_idx])
        fold_heldout_mae.append(float(np.abs(human[test_idx] - pred_test).mean()))
        fold_heldout_mae_at_w1.append(float(np.abs(human[test_idx] - verified[test_idx]).mean()))

    print(f"\nPer-fold selected w: {fold_best_w}")
    print(f"Per-fold held-out MAE (tuned w):  {[f'{m:.4f}' for m in fold_heldout_mae]}")
    print(f"Per-fold held-out MAE (w=1.0):    {[f'{m:.4f}' for m in fold_heldout_mae_at_w1]}")

    cv_mae_tuned = float(np.mean(fold_heldout_mae))
    cv_mae_w1 = float(np.mean(fold_heldout_mae_at_w1))
    print(f"\nCV-averaged held-out MAE, tuned w:  {cv_mae_tuned:.4f}")
    print(f"CV-averaged held-out MAE, w=1.0:    {cv_mae_w1:.4f}")
    print(f"CV-averaged held-out MAE, zero-shot: {mae_zeroshot:.4f}")

    diff = np.array(fold_heldout_mae_at_w1) - np.array(fold_heldout_mae)
    if len(diff) >= 5 and not np.allclose(diff, 0):
        w_stat, p_tuned_vs_w1 = wilcoxon(diff)
    else:
        p_tuned_vs_w1 = float("nan")
    tuned_vs_zeroshot_pct = (mae_zeroshot - cv_mae_tuned) / mae_zeroshot * 100
    tuned_vs_w1_pct = (cv_mae_w1 - cv_mae_tuned) / cv_mae_w1 * 100

    print(f"\nTuned pipeline vs zero-shot:  {tuned_vs_zeroshot_pct:+.1f}% MAE change")
    print(f"Tuned pipeline vs w=1.0:      {tuned_vs_w1_pct:+.1f}% MAE change (fold-paired Wilcoxon p={p_tuned_vs_w1:.4g}, n_folds={K_FOLDS})")

    verdict_vs_zeroshot = "beats zero-shot" if cv_mae_tuned < mae_zeroshot else "still worse than zero-shot"
    print(f"\n=== Option C verdict: tuned pipeline {verdict_vs_zeroshot} on held-out folds ===")

    out = {
        "n": n, "mae_zeroshot": mae_zeroshot, "mae_w1_option_a": mae_w1,
        "fold_best_w": fold_best_w, "fold_heldout_mae_tuned": fold_heldout_mae,
        "fold_heldout_mae_w1": fold_heldout_mae_at_w1,
        "cv_mae_tuned": cv_mae_tuned, "cv_mae_w1": cv_mae_w1,
        "tuned_vs_zeroshot_pct": tuned_vs_zeroshot_pct, "tuned_vs_w1_pct": tuned_vs_w1_pct,
        "p_tuned_vs_w1_foldpaired": None if np.isnan(p_tuned_vs_w1) else float(p_tuned_vs_w1),
        "verdict_vs_zeroshot": verdict_vs_zeroshot,
    }
    out_path = BASE / "data" / f"{tag}_pipeline_weight_tuning.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
