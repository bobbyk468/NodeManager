#!/usr/bin/env python3
"""
compute_main_results_ci.py -- Bootstrap 95% CIs for the headline MAE and
Pearson r figures in Table III (Main Evaluation), on the full real
n=1,262 Mohler sample.

Motivation
----------
Table III reports point estimates only (MAE, r, QWK, RMSE) for C_LLM and
C5_fix on the full real sample. A self-review pass noted that the
bootstrap machinery already used elsewhere in this paper
(compute_real_fixes.py, on the n=90 test split) was never applied to the
full n=1,262 sample the headline table itself reports. This closes that
gap using only the already-collected data/mohler_real_eval_results.json
-- zero new API calls.

Method
------
5,000 percentile-method bootstrap resamples (seed=42, matching the
Evaluation Metrics section's stated convention), resampling responses
with replacement, recomputing MAE and Pearson r for both systems on each
resample.

Run:
    python3 compute_main_results_ci.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr

BASE = Path(__file__).parent
N_RESAMPLES = 5000
SEED = 42


def main() -> int:
    with (BASE / "data" / "mohler_real_eval_results.json").open() as f:
        d = json.load(f)
    rows = d["results"]

    human = np.array([r["human_score"] for r in rows])
    cllm = np.array([r["cllm_score"] for r in rows])
    c5 = np.array([r["c5_score"] for r in rows])
    n = len(rows)
    print(f"n = {n}")

    rng = np.random.default_rng(SEED)
    boot_mae_cllm = np.empty(N_RESAMPLES)
    boot_mae_c5 = np.empty(N_RESAMPLES)
    boot_r_cllm = np.empty(N_RESAMPLES)
    boot_r_c5 = np.empty(N_RESAMPLES)

    for i in range(N_RESAMPLES):
        idx = rng.integers(0, n, size=n)
        h, cl, c5s = human[idx], cllm[idx], c5[idx]
        boot_mae_cllm[i] = np.mean(np.abs(h - cl))
        boot_mae_c5[i] = np.mean(np.abs(h - c5s))
        boot_r_cllm[i] = np.corrcoef(h, cl)[0, 1]
        boot_r_c5[i] = np.corrcoef(h, c5s)[0, 1]

    def ci(arr):
        return float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))

    result = {
        "n": n,
        "n_resamples": N_RESAMPLES,
        "seed": SEED,
        "mae_cllm": {"point": float(np.mean(np.abs(human - cllm))), "ci95": ci(boot_mae_cllm)},
        "mae_c5": {"point": float(np.mean(np.abs(human - c5))), "ci95": ci(boot_mae_c5)},
        "r_cllm": {"point": float(pearsonr(human, cllm)[0]), "ci95": ci(boot_r_cllm)},
        "r_c5": {"point": float(pearsonr(human, c5)[0]), "ci95": ci(boot_r_c5)},
    }

    for k, v in result.items():
        if isinstance(v, dict):
            print(f"{k}: point={v['point']:.4f}  95% CI=[{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]")

    out_path = BASE / "data" / "main_results_ci.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
