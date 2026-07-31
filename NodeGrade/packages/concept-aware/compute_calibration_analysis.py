#!/usr/bin/env python3
"""
compute_calibration_analysis.py — Post-hoc recalibration of C_LLM and
C5_fix against the real Mohler human scores.

Motivation
----------
The real-data re-evaluation (2026-07-28, see REPRODUCIBILITY.md) found
both systems systematically under-predict relative to real human graders
(human mean 4.24/5 vs. C_LLM 2.99, C5_fix 3.09) -- real course grading is
markedly more lenient than either LLM-based grader. This raises the
question of how much of the raw MAE is *scale/bias* error (fixable by a
monotonic recalibration fit on already-collected data, no new LLM calls)
versus genuine *ranking* error (which recalibration cannot fix).

Method
------
5-fold cross-validated isotonic regression (and, for comparison, linear
regression) mapping raw predicted score -> calibrated score, fit on 4
folds and applied out-of-fold to the 5th, repeated across all 5 folds so
every sample gets a genuinely held-out calibrated prediction (no
train/test leakage). This uses only the already-collected
data/mohler_real_eval_results.json -- zero new API calls.

Run:
    python3 compute_calibration_analysis.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold

BASE = Path(__file__).parent


def cv_calibrate(raw: np.ndarray, human: np.ndarray, method: str, seed: int = 42) -> np.ndarray:
    """5-fold CV calibration: each sample's calibrated prediction comes
    from a model fit on the OTHER 4 folds only."""
    kf = KFold(n_splits=5, shuffle=True, random_state=seed)
    out = np.zeros_like(raw)
    for train_idx, test_idx in kf.split(raw):
        if method == "isotonic":
            model = IsotonicRegression(out_of_bounds="clip").fit(raw[train_idx], human[train_idx])
            out[test_idx] = model.predict(raw[test_idx])
        elif method == "linear":
            model = LinearRegression().fit(raw[train_idx].reshape(-1, 1), human[train_idx])
            out[test_idx] = model.predict(raw[test_idx].reshape(-1, 1))
        else:
            raise ValueError(method)
    return np.clip(out, 0, 5)


def main() -> int:
    with (BASE / "data" / "mohler_real_eval_results.json").open() as f:
        d = json.load(f)
    results = d["results"]
    human = np.array([r["human_score"] for r in results])
    c5 = np.array([r["c5_score"] for r in results])
    cllm = np.array([r["cllm_score"] for r in results])

    def mae(pred):
        return float(np.mean(np.abs(human - pred)))

    print(f"n = {len(results)}")
    print(f"\nRAW (uncalibrated):")
    print(f"  C_LLM  MAE = {mae(cllm):.4f}")
    print(f"  C5_fix MAE = {mae(c5):.4f}")

    out = {"n": len(results), "raw": {"mae_cllm": mae(cllm), "mae_c5": mae(c5)}}

    for method in ["linear", "isotonic"]:
        cllm_cal = cv_calibrate(cllm, human, method)
        c5_cal = cv_calibrate(c5, human, method)
        mae_cllm_cal = mae(cllm_cal)
        mae_c5_cal = mae(c5_cal)
        print(f"\n{method.upper()} recalibration (5-fold CV, out-of-fold predictions):")
        print(f"  C_LLM  MAE = {mae_cllm_cal:.4f}  ({(mae(cllm)-mae_cllm_cal)/mae(cllm)*100:+.1f}% vs raw)")
        print(f"  C5_fix MAE = {mae_c5_cal:.4f}  ({(mae(c5)-mae_c5_cal)/mae(c5)*100:+.1f}% vs raw)")

        err_cllm_cal = np.abs(human - cllm_cal)
        err_c5_cal = np.abs(human - c5_cal)
        _, p_two = wilcoxon(err_c5_cal, err_cllm_cal, alternative="two-sided", zero_method="wilcox")
        _, p_one_cllm_better = wilcoxon(err_cllm_cal, err_c5_cal, alternative="less", zero_method="wilcox")
        diffs = err_c5_cal - err_cllm_cal
        d_z = float(diffs.mean() / diffs.std(ddof=1))
        winner = "C_LLM" if mae_cllm_cal < mae_c5_cal else "C5_fix"
        print(f"  Post-calibration comparison: {winner} has lower MAE; "
              f"two-tailed p={p_two:.4f}, one-tailed p(C_LLM better)={p_one_cllm_better:.4f}, d_z={d_z:.4f}")

        out[method] = {
            "mae_cllm_calibrated": mae_cllm_cal,
            "mae_c5_calibrated": mae_c5_cal,
            "pct_improvement_cllm": (mae(cllm) - mae_cllm_cal) / mae(cllm) * 100,
            "pct_improvement_c5": (mae(c5) - mae_c5_cal) / mae(c5) * 100,
            "wilcoxon_p_two_tailed": float(p_two),
            "wilcoxon_p_one_tailed_cllm_better": float(p_one_cllm_better),
            "d_z_c5_minus_cllm": d_z,
            "winner": winner,
        }

    out_path = BASE / "data" / "calibration_analysis.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
