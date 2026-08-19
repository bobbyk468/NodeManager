#!/usr/bin/env python3
"""
compute_pipeline_learned_reweighting.py -- Option B (genuinely distinct
mechanism, not a 6th binary include/exclude patch): fit a regularized
linear model (ridge regression) predicting human_score directly from the
pipeline's sub-scores, instead of the fixed hand-set formula weights
(0.45/0.35/0.20 knowledge; 0.60/0.40 knowledge/depth; verifier_weight).

This differs in kind from the five already-rejected fixes in
REPRODUCIBILITY.md's Finding 2/3 investigation (all of which excluded or
degraded individual dimensions within the fixed-weight formula): here
every dimension stays in, and a supervised model learns what combination
of them actually predicts human_score, including possibly discovering
that concept_coverage/relationship_accuracy deserve near-zero weight
(which would itself corroborate, not contradict, Findings 2/3).

IMPORTANT CONFOUND, CAUGHT AND CONTROLLED FOR: an early version of this
script compared the learned multi-feature model against the RAW,
uncalibrated zero-shot baseline (MAE 0.92) and found an apparent 47%
improvement. That comparison was invalid -- recalibrating the RAW
verified_score ALONE (intercept + scale, zero extra features) already
drops MAE to 0.385, and recalibrating the RAW zero-shot baseline THE SAME
WAY drops it to 0.431. Nearly the entire "improvement" was a generic
affine-recalibration artifact available to any raw 0-5 LLM score, not
evidence the pipeline's architecture adds value. This script now reports
the fair comparison: recalibrated pipeline vs. recalibrated zero-shot,
both under identical treatment, plus the full multi-feature model against
that same fair baseline.

Zero new API calls -- every feature is already cached from Phase A/B.

Validation: leave-one-question-out cross-validation (11 questions in this
300-sample GPT-backbone subset) -- the SAME method that caught this
project's own earlier retracted ensemble-blend-weight overfitting
(REPRODUCIBILITY.md). Ridge alpha (and, for the recalibration-only
baselines, the same nested selection) is chosen via inner CV on the
training questions only, never touching the held-out question.

Run:
    python3 compute_pipeline_learned_reweighting.py --model gpt
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from scipy.stats import wilcoxon

BASE = Path(__file__).parent
ALPHA_GRID = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]
FEATURE_NAMES = ["concept_coverage", "relationship_accuracy", "integration_quality",
                  "blooms_normalized", "solo_normalized", "misc_penalty", "verified_score"]


def build_features(pa_row: dict, blooms_level: int, solo_level: int, verified: float) -> np.ndarray:
    scores = pa_row["comparison_result"].get("scores", {})
    misc = pa_row["misconceptions"]
    n_misc = misc.get("total_misconceptions", 0) if "error" not in misc else 0
    critical = misc.get("critical_count", 0) if "error" not in misc else 0
    misc_penalty = min(0.30, n_misc * 0.06 + critical * 0.10)
    return np.array([
        scores.get("concept_coverage", 0),
        scores.get("relationship_accuracy", 0),
        scores.get("integration_quality", 0),
        (blooms_level - 1) / 5,
        (solo_level - 1) / 4,
        misc_penalty,
        verified,
    ])


def loqo_predict(X: np.ndarray, y: np.ndarray, qids: np.ndarray) -> np.ndarray:
    """Leave-one-question-out CV predictions for an arbitrary feature matrix
    (1 column = pure recalibration baseline; 7 columns = full learned model),
    with nested alpha selection on training questions only."""
    unique_qs = np.unique(qids)
    preds = np.zeros(len(y))
    for q in unique_qs:
        test_mask = qids == q
        train_mask = ~test_mask
        alpha = inner_select_alpha(X[train_mask], y[train_mask], qids[train_mask])
        scaler = StandardScaler().fit(X[train_mask])
        model = Ridge(alpha=alpha).fit(scaler.transform(X[train_mask]), y[train_mask])
        preds[test_mask] = model.predict(scaler.transform(X[test_mask]))
    return np.clip(preds, 0.0, 5.0)


def inner_select_alpha(X_train: np.ndarray, y_train: np.ndarray, groups_train: np.ndarray) -> float:
    """Nested leave-one-question-out CV on the training questions only."""
    inner_qs = np.unique(groups_train)
    best_alpha, best_mae = ALPHA_GRID[0], float("inf")
    for alpha in ALPHA_GRID:
        errs = []
        for q in inner_qs:
            tr_mask = groups_train != q
            te_mask = groups_train == q
            if tr_mask.sum() < 5 or te_mask.sum() == 0:
                continue
            scaler = StandardScaler().fit(X_train[tr_mask])
            model = Ridge(alpha=alpha).fit(scaler.transform(X_train[tr_mask]), y_train[tr_mask])
            pred = model.predict(scaler.transform(X_train[te_mask]))
            errs.append(np.abs(y_train[te_mask] - pred))
        if errs:
            mae = np.concatenate(errs).mean()
            if mae < best_mae:
                best_mae, best_alpha = mae, alpha
    return best_alpha


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

    X, y, qids, zeroshot = [], [], [], []
    for r in phase_b["results"]:
        sid = r["id"]
        if r[f"{tag}_c5_score"] is None or sid not in phase_a or sid not in baseline:
            continue
        feats = build_features(phase_a[sid], r["blooms_level"], r["solo_level"], r[f"{tag}_c5_score"])
        X.append(feats)
        y.append(r["human_score"])
        qids.append(r["qid"])
        zeroshot.append(baseline[sid])
    X = np.array(X)
    y = np.array(y)
    qids = np.array(qids)
    zeroshot = np.array(zeroshot)
    n = len(y)
    unique_qs = np.unique(qids)
    print(f"n={n}  n_questions={len(unique_qs)}  features={FEATURE_NAMES}")

    mae_zeroshot_raw = float(np.abs(y - zeroshot).mean())
    w1_scores = X[:, FEATURE_NAMES.index("verified_score")]
    mae_w1_raw = float(np.abs(y - w1_scores).mean())
    print(f"Raw zero-shot MAE (no recalibration):        {mae_zeroshot_raw:.4f}")
    print(f"Raw verified_score MAE (Option A/C, w=1.0):  {mae_w1_raw:.4f}")

    # Fair baselines: recalibrate (intercept+scale only, LOQO CV) BOTH sides
    # identically, isolating any real architecture signal from generic
    # affine-recalibration gains available to any raw 0-5 LLM score.
    pred_zeroshot_recal = loqo_predict(zeroshot.reshape(-1, 1), y, qids)
    pred_w1_recal = loqo_predict(w1_scores.reshape(-1, 1), y, qids)
    mae_zeroshot_recal = float(np.abs(y - pred_zeroshot_recal).mean())
    mae_w1_recal = float(np.abs(y - pred_w1_recal).mean())
    print(f"\nRecalibrated zero-shot MAE:      {mae_zeroshot_recal:.4f}")
    print(f"Recalibrated verified_score MAE: {mae_w1_recal:.4f}  <- fair comparison point")

    # Full multi-feature learned model
    unique_qs_list = list(unique_qs)
    fold_alphas = []
    fold_coefs = []
    preds = np.zeros(n)
    for q in unique_qs_list:
        test_mask = qids == q
        train_mask = ~test_mask
        alpha = inner_select_alpha(X[train_mask], y[train_mask], qids[train_mask])
        fold_alphas.append(alpha)
        scaler = StandardScaler().fit(X[train_mask])
        model = Ridge(alpha=alpha).fit(scaler.transform(X[train_mask]), y[train_mask])
        preds[test_mask] = model.predict(scaler.transform(X[test_mask]))
        fold_coefs.append(model.coef_)
    preds = np.clip(preds, 0.0, 5.0)
    mae_learned = float(np.abs(y - preds).mean())

    avg_coefs = np.mean(fold_coefs, axis=0)
    std_coefs = np.std(fold_coefs, axis=0)
    print(f"\nFull 7-feature learned model MAE: {mae_learned:.4f}")
    print("Average standardized coefficient per feature (across 11 folds, mean +/- std):")
    for name, m, s in zip(FEATURE_NAMES, avg_coefs, std_coefs):
        print(f"  {name:24s}  {m:+.4f}  (+/-{s:.4f})")

    # THE fair comparison: recalibrated pipeline vs recalibrated zero-shot
    diff_fair = np.abs(y - pred_zeroshot_recal) - np.abs(y - pred_w1_recal)
    w_stat, p_fair = wilcoxon(diff_fair)
    pct_fair = (mae_zeroshot_recal - mae_w1_recal) / mae_zeroshot_recal * 100
    print(f"\n=== FAIR comparison: recalibrated pipeline vs recalibrated zero-shot ===")
    print(f"  {pct_fair:+.1f}% MAE change (response-level p={p_fair:.4g})")

    # Does adding the raw KG sub-scores on top of recalibration help further?
    diff_multi_vs_recal = np.abs(y - pred_w1_recal) - np.abs(y - preds)
    w_stat2, p_multi = wilcoxon(diff_multi_vs_recal)
    pct_multi = (mae_w1_recal - mae_learned) / mae_w1_recal * 100
    print(f"\n=== Does adding raw KG sub-scores beyond recalibration help? ===")
    print(f"  {pct_multi:+.1f}% MAE change vs recalibration-only (p={p_multi:.4g}) "
          f"{'[WORSE, not better]' if pct_multi < 0 else ''}")

    verdict = ("recalibrated pipeline beats recalibrated zero-shot" if (mae_w1_recal < mae_zeroshot_recal and p_fair < 0.05)
               else "recalibrated pipeline does NOT beat recalibrated zero-shot")
    kg_verdict = ("raw KG sub-scores add value beyond recalibration" if (mae_learned < mae_w1_recal and p_multi < 0.05)
                  else "raw KG sub-scores add NO value beyond recalibration (confirms Findings 2/3)")
    print(f"\n=== Option B verdict: {verdict}; {kg_verdict} ===")

    out = {
        "n": n, "n_questions": len(unique_qs),
        "mae_zeroshot_raw": mae_zeroshot_raw, "mae_w1_raw": mae_w1_raw,
        "mae_zeroshot_recalibrated": mae_zeroshot_recal, "mae_w1_recalibrated": mae_w1_recal,
        "mae_full_learned_model": mae_learned,
        "pct_fair_pipeline_vs_zeroshot": pct_fair, "p_fair": float(p_fair),
        "pct_kg_subscores_vs_recal_only": pct_multi, "p_kg_subscores": float(p_multi),
        "fold_alphas": fold_alphas,
        "avg_coefficients": {name: float(m) for name, m in zip(FEATURE_NAMES, avg_coefs)},
        "std_coefficients": {name: float(s) for name, s in zip(FEATURE_NAMES, std_coefs)},
        "verdict": verdict, "kg_subscore_verdict": kg_verdict,
    }
    out_path = BASE / "data" / f"{tag}_pipeline_learned_reweighting.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
