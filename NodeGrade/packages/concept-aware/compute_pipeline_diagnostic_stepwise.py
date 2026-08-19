#!/usr/bin/env python3
"""
compute_pipeline_diagnostic_stepwise.py -- systematic, step-by-step
diagnostic of which individual signals (and which combinations of them)
actually carry predictive value for human_score, on the cached
300-sample GPT-backbone dataset. Zero new API calls.

Motivation: compute_pipeline_learned_reweighting.py showed the full
7-feature model is WORSE than the single-feature recalibrated verifier
score. That result alone doesn't say WHY -- this script isolates each
signal individually and in small combinations, under the same fair
leave-one-question-out recalibration protocol, to find out which
components (if any) carry real incremental signal, and which are pure
noise or actively harmful.

Every "MAE" below is a LOQO-cross-validated, recalibrated (intercept +
scale via ridge, nested alpha selection) prediction -- never a raw score
and never in-sample -- so all numbers are fairly comparable to each
other and to the recalibrated zero-shot baseline.

Run:
    python3 compute_pipeline_diagnostic_stepwise.py --model gpt
"""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr, wilcoxon
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).parent
ALPHA_GRID = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]


def inner_select_alpha(X_train, y_train, groups_train) -> float:
    inner_qs = np.unique(groups_train)
    best_alpha, best_mae = ALPHA_GRID[0], float("inf")
    for alpha in ALPHA_GRID:
        errs = []
        for q in inner_qs:
            tr = groups_train != q
            te = groups_train == q
            if tr.sum() < 5 or te.sum() == 0:
                continue
            sc = StandardScaler().fit(X_train[tr])
            m = Ridge(alpha=alpha).fit(sc.transform(X_train[tr]), y_train[tr])
            p = m.predict(sc.transform(X_train[te]))
            errs.append(np.abs(y_train[te] - p))
        if errs:
            mae = np.concatenate(errs).mean()
            if mae < best_mae:
                best_mae, best_alpha = mae, alpha
    return best_alpha


def loqo_predict(X: np.ndarray, y: np.ndarray, qids: np.ndarray) -> np.ndarray:
    unique_qs = np.unique(qids)
    preds = np.zeros(len(y))
    for q in unique_qs:
        te = qids == q
        tr = ~te
        alpha = inner_select_alpha(X[tr], y[tr], qids[tr])
        sc = StandardScaler().fit(X[tr])
        m = Ridge(alpha=alpha).fit(sc.transform(X[tr]), y[tr])
        preds[te] = m.predict(sc.transform(X[te]))
    return np.clip(preds, 0.0, 5.0)


def build_feature_dict(pa_row: dict, blooms_level: int, solo_level: int,
                        verified: float, zeroshot: float) -> dict:
    scores = pa_row["comparison_result"].get("scores", {})
    misc = pa_row["misconceptions"]
    n_misc = misc.get("total_misconceptions", 0) if "error" not in misc else 0
    critical = misc.get("critical_count", 0) if "error" not in misc else 0
    misc_penalty = min(0.30, n_misc * 0.06 + critical * 0.10)
    knowledge = (scores.get("concept_coverage", 0) * 0.45 +
                 scores.get("relationship_accuracy", 0) * 0.35 +
                 scores.get("integration_quality", 0) * 0.20)
    depth = ((blooms_level - 1) / 5) * 0.55 + ((solo_level - 1) / 4) * 0.45
    kg_formula = min(1.0, max(0.0, (knowledge * 0.60 + depth * 0.40) * (1.0 - misc_penalty))) * 5.0
    return {
        "concept_coverage": scores.get("concept_coverage", 0),
        "relationship_accuracy": scores.get("relationship_accuracy", 0),
        "integration_quality": scores.get("integration_quality", 0),
        "blooms_normalized": (blooms_level - 1) / 5,
        "solo_normalized": (solo_level - 1) / 4,
        "n_misconceptions": n_misc,
        "misc_penalty": misc_penalty,
        "kg_formula_composite": kg_formula,
        "verified_score": verified,
        "zeroshot": zeroshot,
    }


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

    feats_list, y_list, qid_list = [], [], []
    for r in phase_b["results"]:
        sid = r["id"]
        if r[f"{tag}_c5_score"] is None or sid not in phase_a or sid not in baseline:
            continue
        feats_list.append(build_feature_dict(phase_a[sid], r["blooms_level"], r["solo_level"],
                                              r[f"{tag}_c5_score"], baseline[sid]))
        y_list.append(r["human_score"])
        qid_list.append(r["qid"])

    y = np.array(y_list)
    qids = np.array(qid_list)
    names = list(feats_list[0].keys())
    F = {name: np.array([f[name] for f in feats_list]) for name in names}
    n = len(y)
    print(f"n={n}  n_questions={len(np.unique(qids))}\n")

    # ---- Step 1: each signal alone, raw correlation with human_score ----
    print("=== Step 1: raw Pearson/Spearman correlation with human_score (no recalibration) ===")
    for name in names:
        r_p, _ = pearsonr(F[name], y)
        r_s, _ = spearmanr(F[name], y)
        print(f"  {name:24s}  Pearson r={r_p:+.4f}  Spearman rho={r_s:+.4f}")

    # ---- Step 2: each signal alone, recalibrated LOQO MAE ----
    print("\n=== Step 2: each signal alone, recalibrated (LOQO CV) MAE ===")
    single_preds = {}
    single_mae = {}
    for name in names:
        pred = loqo_predict(F[name].reshape(-1, 1), y, qids)
        single_preds[name] = pred
        single_mae[name] = float(np.abs(y - pred).mean())
        print(f"  {name:24s}  MAE={single_mae[name]:.4f}")

    zeroshot_recal_mae = single_mae["zeroshot"]
    zeroshot_recal_pred = single_preds["zeroshot"]

    # ---- Step 3: does each signal add value ON TOP of recalibrated zero-shot? ----
    print(f"\n=== Step 3: zero-shot + each other signal, recalibrated (vs zero-shot-alone MAE={zeroshot_recal_mae:.4f}) ===")
    pair_results = []
    for name in names:
        if name == "zeroshot":
            continue
        X = np.column_stack([F["zeroshot"], F[name]])
        pred = loqo_predict(X, y, qids)
        mae = float(np.abs(y - pred).mean())
        diff = np.abs(y - zeroshot_recal_pred) - np.abs(y - pred)
        try:
            _, p = wilcoxon(diff)
        except ValueError:
            p = float("nan")
        pct = (zeroshot_recal_mae - mae) / zeroshot_recal_mae * 100
        flag = "HELPS" if (mae < zeroshot_recal_mae and p < 0.05) else ("hurts" if mae > zeroshot_recal_mae else "~tie")
        pair_results.append((name, mae, pct, p, flag))
        print(f"  zeroshot + {name:24s} MAE={mae:.4f}  ({pct:+.1f}%, p={p:.3g})  [{flag}]")

    # ---- Step 4: best-looking combinations (zeroshot + verified_score + misconceptions) ----
    print(f"\n=== Step 4: targeted combinations ===")
    combos = {
        "zeroshot + verified_score": ["zeroshot", "verified_score"],
        "zeroshot + n_misconceptions": ["zeroshot", "n_misconceptions"],
        "zeroshot + verified_score + n_misconceptions": ["zeroshot", "verified_score", "n_misconceptions"],
        "verified_score + n_misconceptions": ["verified_score", "n_misconceptions"],
        "zeroshot + kg_formula_composite": ["zeroshot", "kg_formula_composite"],
        "all_10_features": names,
    }
    combo_results = {}
    for label, cols in combos.items():
        X = np.column_stack([F[c] for c in cols])
        pred = loqo_predict(X, y, qids)
        mae = float(np.abs(y - pred).mean())
        diff = np.abs(y - zeroshot_recal_pred) - np.abs(y - pred)
        try:
            _, p = wilcoxon(diff)
        except ValueError:
            p = float("nan")
        pct = (zeroshot_recal_mae - mae) / zeroshot_recal_mae * 100
        combo_results[label] = {"mae": mae, "pct_vs_zeroshot": pct, "p": None if np.isnan(p) else float(p)}
        flag = "HELPS" if (mae < zeroshot_recal_mae and p < 0.05) else ("hurts" if mae > zeroshot_recal_mae else "~tie")
        print(f"  {label:45s} MAE={mae:.4f}  ({pct:+.1f}% vs zero-shot, p={p:.3g})  [{flag}]")

    out = {
        "n": n, "n_questions": int(len(np.unique(qids))),
        "raw_correlations": {name: {"pearson_r": float(pearsonr(F[name], y)[0]),
                                     "spearman_rho": float(spearmanr(F[name], y)[0])} for name in names},
        "single_signal_recalibrated_mae": single_mae,
        "pair_vs_zeroshot": [{"signal": n_, "mae": m, "pct_vs_zeroshot": p_, "p": None if np.isnan(pv) else float(pv), "flag": f}
                              for n_, m, p_, pv, f in pair_results],
        "targeted_combinations": combo_results,
    }
    out_path = BASE / "data" / f"{tag}_pipeline_diagnostic_stepwise.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
