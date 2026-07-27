#!/usr/bin/env python3
"""
recompute_kaggle_dedup_stats.py — recompute Paper 1 Kaggle numbers on the
dedupd sample set produced by Framework Fix #19.

Paper 1 (docs/paper_phase1_ieee.tex) currently reports Kaggle ASAG on the
full N=473 sample set. Fix #19 found 105 byte-identical duplicate records
(each pair had matching human_score) — treating them as independent
observations underestimates variance and biases significance downward.

This script recomputes the paired-test statistics on the 368 unique records
so the paper can either cite the corrected numbers or explicitly reference
both, with the sensitivity noted.

Reports (paired C5_fix vs C_LLM on |error|):
  - Sample count N
  - MAE for each system + MAE reduction %
  - Bootstrap 95% CI on the MAE reduction
  - Wilcoxon signed-rank (two-sided + one-sided) p-values
  - Paired t-test + Cohen's d_z
  - Number of ties (samples where c5 == cllm)

Usage:
    python3 recompute_kaggle_dedup_stats.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon, ttest_rel

BASE = Path(__file__).parent
DATA = BASE / "data"
sys.path.insert(0, str(BASE))

from datasets.dataset_dedupe import load_dedup_dataset, slice_eval_to_unique


def compute_stats(rows, label):
    """Compute paired-comparison stats between c5_score and cllm_score."""
    human = np.array([r["human_score"] for r in rows], dtype=float)
    cllm  = np.array([r["cllm_score"] for r in rows], dtype=float)
    c5    = np.array([r["c5_score"]   for r in rows], dtype=float)
    err_cllm = np.abs(human - cllm)
    err_c5   = np.abs(human - c5)
    mae_cllm = err_cllm.mean()
    mae_c5   = err_c5.mean()
    reduction_pct = 100.0 * (mae_cllm - mae_c5) / mae_cllm if mae_cllm > 0 else 0.0

    # Paired diff on absolute errors: negative = c5 better
    diffs = err_c5 - err_cllm
    n_ties  = int(np.sum(diffs == 0))
    n_c5_better  = int(np.sum(diffs < 0))
    n_cllm_better = int(np.sum(diffs > 0))

    # Wilcoxon signed-rank (drop zeros — scipy default)
    try:
        w_two = wilcoxon(err_c5, err_cllm, alternative="two-sided").pvalue
    except Exception:
        w_two = float("nan")
    try:
        w_one_less = wilcoxon(err_c5, err_cllm, alternative="less").pvalue  # c5 err < cllm err
    except Exception:
        w_one_less = float("nan")

    # Paired t-test + Cohen's d_z on the differences
    t = ttest_rel(err_c5, err_cllm)
    d_z = diffs.mean() / diffs.std(ddof=1) if diffs.std(ddof=1) > 0 else 0.0

    # Bootstrap CI on MAE reduction %
    rng = np.random.default_rng(20260616)
    B = 5000
    n = len(rows)
    boot_reductions = []
    for _ in range(B):
        idx = rng.integers(0, n, size=n)
        b_cllm = err_cllm[idx].mean()
        b_c5 = err_c5[idx].mean()
        if b_cllm > 0:
            boot_reductions.append(100.0 * (b_cllm - b_c5) / b_cllm)
    ci_lo, ci_hi = np.percentile(boot_reductions, [2.5, 97.5])

    print(f"\n=== {label}  (N = {n}) ===")
    print(f"  MAE C_LLM:      {mae_cllm:.4f}")
    print(f"  MAE C5_fix:     {mae_c5:.4f}")
    print(f"  MAE reduction:  {reduction_pct:+.2f}%   95% CI [{ci_lo:+.2f}%, {ci_hi:+.2f}%]")
    print(f"  Paired diffs:   c5_better={n_c5_better}  cllm_better={n_cllm_better}  ties={n_ties}")
    print(f"  Wilcoxon (two-sided) p = {w_two:.4f}")
    print(f"  Wilcoxon (one-sided, c5<cllm) p = {w_one_less:.4f}")
    print(f"  Paired t: t={t.statistic:.3f}, p={t.pvalue:.4f}")
    print(f"  Cohen's d_z:    {d_z:+.4f}")

    return {
        "label": label, "n": n,
        "mae_cllm": mae_cllm, "mae_c5": mae_c5,
        "reduction_pct": reduction_pct,
        "ci_low": ci_lo, "ci_high": ci_hi,
        "n_c5_better": n_c5_better, "n_cllm_better": n_cllm_better, "n_ties": n_ties,
        "p_wilcoxon_two": w_two, "p_wilcoxon_one_less": w_one_less,
        "p_paired_t": t.pvalue, "cohens_dz": d_z,
    }


def main():
    with (DATA / "kaggle_asag_eval_results.json").open() as f:
        cached_all = json.load(f).get("results", [])
    print(f"Loaded cached kaggle_asag_eval_results.json: {len(cached_all)} rows")

    # Baseline (paper): full N=473
    baseline = compute_stats(cached_all, "PAPER-CURRENT: N=473 (with 105 duplicates)")

    # Fix #19 sidecar: 368 unique records; slice eval by aligned indices
    unique_records, aligned_indices, dropped = load_dedup_dataset("kaggle_asag")
    print(f"\nFix #19 dedupe: {len(unique_records)} unique / {dropped} dropped duplicates")
    sliced_eval = slice_eval_to_unique(cached_all, aligned_indices)
    print(f"Sliced eval to dedupd index set: {len(sliced_eval)} rows")

    corrected = compute_stats(sliced_eval, "CORRECTED: N=368 (dedupd)")

    # Emit paper-ready text
    print("\n" + "=" * 70)
    print("PAPER TEXT REPLACEMENT (drop-in for the abstract + §5)")
    print("=" * 70)
    print(f"""
Kaggle ASAG (Elementary Science), N={corrected['n']} unique responses
(105 byte-identical duplicates dropped from source distribution):
Cohen's d_z = {corrected['cohens_dz']:+.3f},
Wilcoxon one-sided p = {corrected['p_wilcoxon_one_less']:.3f},
two-sided p = {corrected['p_wilcoxon_two']:.3f}.
MAE reduction {corrected['reduction_pct']:+.2f}%,
bootstrap 95% CI [{corrected['ci_low']:+.2f}%, {corrected['ci_high']:+.2f}%].
Ties: {corrected['n_ties']}/{corrected['n']}.
""")

    # Persist for downstream scripts / paper insertion
    out = {
        "baseline_n473": baseline,
        "corrected_n368": corrected,
    }
    (DATA / "kaggle_dedup_stats.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"[saved] data/kaggle_dedup_stats.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
