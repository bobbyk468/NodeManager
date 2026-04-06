#!/usr/bin/env python3
"""
Evidence summary for "ConceptGrade (C5_fix) vs LLM-only (C_LLM)" using **stored JSON**.

What this can and cannot do
----------------------------
- **Can**: Recompute MAE / Wilcoxon from `results[]`, validate internal consistency, combine
  dataset-level p-values (exploratory), report **sample win rates** (|C5−h| < |C_LLM−h|).
- **Cannot**: Turn Kaggle into a win **without new LLM outputs**. Offline mixes of stored
  `c5_score` with `cllm_score` are **not** valid counterfactuals when those C5 scores were
  produced under prompts that always showed KG — the model never ran in "no KG" mode for
  those rows.

**Full proof (no caveats on Kaggle)** requires a confirmatory run:
  1. Regenerate prompts: `python3 generate_batch_scoring_prompts.py --dataset kaggle_asag`
  2. Re-score **only** C5_fix batches with a valid API key:
     `python3 run_full_pipeline.py --dataset kaggle_asag --skip-kg --only-system c5fix --force`
  3. `python3 score_batch_results.py --dataset kaggle_asag && python3 validate_stored_eval.py --check-batches`

Outputs `data/cross_dataset_evidence_summary.json`.

Usage:
  python3 prove_cross_dataset_evidence.py
"""

from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
from scipy.stats import chi2, wilcoxon

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")


def _load_json(name: str) -> dict:
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def compute_mae_wilcoxon(
    h: np.ndarray, cllm: np.ndarray, c5: np.ndarray
) -> tuple[float, float, float, float]:
    m_cllm = float(np.mean(np.abs(h - cllm)))
    m_c5 = float(np.mean(np.abs(h - c5)))
    try:
        _, p = wilcoxon(np.abs(c5 - h), np.abs(cllm - h))
        p = float(p)
    except Exception:
        p = 1.0
    red = (m_cllm - m_c5) / m_cllm * 100.0 if m_cllm > 0 else 0.0
    return m_cllm, m_c5, p, red


def error_delta(h: np.ndarray, cllm: np.ndarray, c5: np.ndarray) -> np.ndarray:
    """Positive => C_LLM had smaller absolute error (better)."""
    return np.abs(c5 - h) - np.abs(cllm - h)


def fisher_combine_p(pvals: list[float]) -> float:
    pv = [max(p, 1e-300) for p in pvals]
    stat = -2.0 * sum(math.log(p) for p in pv)
    df = 2 * len(pv)
    return float(1.0 - chi2.cdf(stat, df))


def win_rate_c5(h: np.ndarray, cllm: np.ndarray, c5: np.ndarray) -> float:
    return float(np.mean(np.abs(c5 - h) < np.abs(cllm - h)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    off = _load_json("offline_eval_results.json")
    mohler_p = float(off["significance"]["C5_fix vs C_LLM"]["p_value"])
    mohler_cfg = off["configs"]
    m_cllm_m = float(mohler_cfg["C_LLM"]["mae"])
    m_c5_m = float(mohler_cfg["C5_fix"]["mae"])

    dk = _load_json("digiklausur_eval_results.json")
    kg = _load_json("kaggle_asag_eval_results.json")

    h_d = np.array([r["human_score"] for r in dk["results"]])
    cllm_d = np.array([r["cllm_score"] for r in dk["results"]])
    c5_d = np.array([r["c5_score"] for r in dk["results"]])
    m0d, m5d, pd, redd = compute_mae_wilcoxon(h_d, cllm_d, c5_d)
    wr_d = win_rate_c5(h_d, cllm_d, c5_d)

    h_k = np.array([r["human_score"] for r in kg["results"]])
    cllm_k = np.array([r["cllm_score"] for r in kg["results"]])
    c5_k = np.array([r["c5_score"] for r in kg["results"]])
    m0k, m5k, pk, redk = compute_mae_wilcoxon(h_k, cllm_k, c5_k)
    wr_k = win_rate_c5(h_k, cllm_k, c5_k)

    # Pooled absolute-error comparison: Digi + Kaggle only (same 0–5-ish scale)
    pooled = np.concatenate(
        [error_delta(h_d, cllm_d, c5_d), error_delta(h_k, cllm_k, c5_k)]
    )
    try:
        _, p_pooled = wilcoxon(pooled, alternative="less", zero_method="wilcox")
        p_pooled = float(p_pooled)
    except Exception:
        p_pooled = 1.0

    p_fisher = fisher_combine_p([mohler_p, pd, pk])

    print("=" * 72)
    print("CONCEPTGRADE vs C_LLM — EVIDENCE FROM STORED JSON")
    print("=" * 72)
    print()
    print("Mohler 2011 (offline_eval_results.json, n=120)")
    print(f"  MAE: C_LLM={m_cllm_m:.4f}  C5_fix={m_c5_m:.4f}  (C5 better)")
    print(f"  Wilcoxon p (file, C5 vs C_LLM): {mohler_p:.6f}")
    print()
    print("DigiKlausur (n=646)")
    print(f"  MAE: C_LLM={m0d:.4f}  C5_fix={m5d:.4f}  ΔMAE {redd:+.2f}%  p={pd:.6f}")
    print(f"  Win rate (|C5−h| < |C_LLM−h|): {wr_d:.1%}")
    print()
    print("Kaggle ASAG (n=473)")
    print(f"  MAE: C_LLM={m0k:.4f}  C5_fix={m5k:.4f}  ΔMAE {redk:+.2f}%  p={pk:.6f}")
    print(f"  Win rate (|C5−h| < |C_LLM−h|): {wr_k:.1%}")
    print()
    print("Pooled paired-error test (Digi + Kaggle only, n=1119)")
    print(f"  Mean (|C5−h|−|C_LLM−h|): {pooled.mean():+.5f}  (negative favors C5)")
    print(f"  Wilcoxon one-sided p (median < 0): {p_pooled:.6f}")
    print()
    print("Fisher combination of three dataset-level Wilcoxon p-values")
    print(f"  p_Fisher = {p_fisher:.2e}  (datasets not independent — exploratory only)")
    print()
    print("─" * 72)
    print("BOTTOM LINE")
    print("─" * 72)
    all_three_mae = (m_c5_m < m_cllm_m) and (m5d < m0d) and (m5k < m0k)
    all_three_p = (mohler_p < 0.05) and (pd < 0.05) and (pk < 0.05)
    print(
        f"  Strict claim 'C5 beats C_LLM on every benchmark (MAE + p<0.05 each)': "
        f"{'YES' if all_three_mae and all_three_p else 'NO — Kaggle fails on stored run'}"
    )
    print(
        "  To remove that limitation: re-score Kaggle C5_fix batches after prompt/KGE tuning "
        "(API), then re-run validate_stored_eval.py."
    )

    out = {
        "mohler": {
            "n": 120,
            "mae_cllm": m_cllm_m,
            "mae_c5": m_c5_m,
            "wilcoxon_p": mohler_p,
            "c5_better_mae": m_c5_m < m_cllm_m,
            "significant_005": mohler_p < 0.05,
        },
        "digiklausur": {
            "n": len(h_d),
            "mae_cllm": m0d,
            "mae_c5": m5d,
            "mae_reduction_pct": redd,
            "wilcoxon_p": pd,
            "win_rate_c5_smaller_error": wr_d,
            "c5_better_mae": m5d < m0d,
            "significant_005": pd < 0.05,
        },
        "kaggle_asag": {
            "n": len(h_k),
            "mae_cllm": m0k,
            "mae_c5": m5k,
            "mae_reduction_pct": redk,
            "wilcoxon_p": pk,
            "win_rate_c5_smaller_error": wr_k,
            "c5_better_mae": m5k < m0k,
            "significant_005": pk < 0.05,
        },
        "pooled_digi_kaggle": {
            "n": int(len(pooled)),
            "mean_abs_error_diff_c5_minus_cllm": float(pooled.mean()),
            "wilcoxon_one_sided_p": p_pooled,
        },
        "fisher_combined_p_three_datasets": p_fisher,
        "strict_all_three_beat": bool(all_three_mae and all_three_p),
        "notes": [
            "Fisher assumes independence across datasets.",
            "Pooled test ignores clustering by dataset (exploratory).",
            "No offline score mixing can substitute for a fresh Kaggle C5_fix API run.",
        ],
    }
    path = os.path.join(DATA, "cross_dataset_evidence_summary.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print()
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
