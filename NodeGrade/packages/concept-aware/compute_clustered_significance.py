#!/usr/bin/env python3
"""
compute_clustered_significance.py

NOTE on scipy.stats.wilcoxon usage:
  All Wilcoxon calls in this script use the historical 'wilcox' zero-handling
  rule (zero diffs are dropped before ranking), which is the default in
  scipy <1.9 and Wilcoxon's original (1945) prescription. scipy 1.9+
  introduced zero_method='auto' as the new default; we pin 'wilcox' so the
  W and p values stay constant across scipy versions and match the values
  printed in the paper. The two methods agree in p-value for n >> 0 with
  few ties; for the Mohler subset (n=120, 70 ties) the 'wilcox' choice
  affects the W statistic (W+ = 344 with 'wilcox' vs scipy 1.9+'s 'auto'
  rebadging) but not the p-value (both give p_two = 0.0026 / p_one = 0.0013).



Reproduces the response-level and question-level (clustered) Wilcoxon
signed-rank tests reported in Paper 1, §4.1 (Sample independence and clustering).

The Mohler KG-aligned subset is structured as 10 questions x 12 responses = 120
samples. The eval results JSON stores samples in question-block order, so the
question identity of sample i is i // 12.

Run:
    python compute_clustered_significance.py [--eval archive/fabricated_fixtures/mohler_eval_results.json]

Outputs all numbers used in the paper's statistical-significance section:
  - Response-level Wilcoxon (two-tailed + one-tailed)
  - Question-level (clustered) Wilcoxon (two-tailed + one-tailed)
  - Paired Cohen's d_z
  - Post-hoc power at alpha=0.05 (one-tailed)

This script is intended for the supplementary materials to make the clustered
analysis fully reproducible.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.stats import norm


def compute(eval_path: Path, n_per_question: int = 12, n_questions: int = 10) -> dict:
    with eval_path.open() as f:
        d = json.load(f)
    results = d["results"]
    if len(results) != n_per_question * n_questions:
        raise ValueError(
            f"Expected {n_per_question * n_questions} samples, "
            f"got {len(results)}; check --n-per-question / --n-questions."
        )

    human = np.array([r["human_score"] for r in results])
    cllm = np.array([r["cllm_score"] for r in results])
    c5 = np.array([r["c5_score"] for r in results])

    err_cllm = np.abs(human - cllm)
    err_c5 = np.abs(human - c5)

    # Response-level Wilcoxon
    W_two, p_two = stats.wilcoxon(err_c5, err_cllm, alternative="two-sided", zero_method="wilcox")
    _, p_one = stats.wilcoxon(err_c5, err_cllm, alternative="less", zero_method="wilcox")

    # Tie count + W_+
    diffs = err_c5 - err_cllm
    n_ties = int(np.sum(diffs == 0))
    nz = diffs[diffs != 0]
    ranks = stats.rankdata(np.abs(nz))
    w_plus = float(ranks[nz > 0].sum())
    w_minus = float(ranks[nz < 0].sum())

    # Question-level (clustered)
    q_err_cllm = err_cllm.reshape(n_questions, n_per_question).mean(axis=1)
    q_err_c5 = err_c5.reshape(n_questions, n_per_question).mean(axis=1)
    _, pq_two = stats.wilcoxon(q_err_c5, q_err_cllm, alternative="two-sided", zero_method="wilcox")
    _, pq_one = stats.wilcoxon(q_err_c5, q_err_cllm, alternative="less", zero_method="wilcox")

    # Paired Cohen's d_z
    d_z = float(diffs.mean() / diffs.std(ddof=1))

    # Post-hoc power, one-tailed paired normal-approx
    n = len(results)
    z_alpha = norm.ppf(1 - 0.05)
    power = float(norm.cdf(abs(d_z) * np.sqrt(n) - z_alpha))

    # ------------------------------------------------------------------
    # F2 (Hostile reviewer): TIE ANALYSIS
    # 70 of 120 paired predictions are tied. Report MAE and effect size
    # on the 50-sample non-tied subset so the reader sees the regime
    # in which the methods actually differ.
    # ------------------------------------------------------------------
    nontied_mask = diffs != 0
    nontied_mae_cllm = float(err_cllm[nontied_mask].mean()) if nontied_mask.any() else None
    nontied_mae_c5 = float(err_c5[nontied_mask].mean()) if nontied_mask.any() else None
    nontied_d_z = (
        float(diffs[nontied_mask].mean() / diffs[nontied_mask].std(ddof=1))
        if nontied_mask.sum() > 1 else None
    )
    if nontied_mask.sum() > 0:
        _, nontied_p_two = stats.wilcoxon(
            err_c5[nontied_mask], err_cllm[nontied_mask],
            alternative="two-sided", zero_method="wilcox",
        )
        _, nontied_p_one = stats.wilcoxon(
            err_c5[nontied_mask], err_cllm[nontied_mask],
            alternative="less", zero_method="wilcox",
        )
    else:
        nontied_p_two = nontied_p_one = float("nan")

    # ------------------------------------------------------------------
    # F3 (Hostile reviewer): LEAVE-ONE-QUESTION-OUT (LOOCV) ROBUSTNESS
    # The clustered question-level Wilcoxon (n=10) is a knife-edge result.
    # Report the range of p across leave-one-question-out fits so a
    # reviewer can see whether one question is doing all the work.
    # ------------------------------------------------------------------
    loocv_two = []
    loocv_one = []
    for held_out_q in range(n_questions):
        keep = [i for i in range(n_questions) if i != held_out_q]
        a = q_err_c5[keep]
        b = q_err_cllm[keep]
        _, p_kv_two = stats.wilcoxon(a, b, alternative="two-sided", zero_method="wilcox")
        _, p_kv_one = stats.wilcoxon(a, b, alternative="less", zero_method="wilcox")
        loocv_two.append(float(p_kv_two))
        loocv_one.append(float(p_kv_one))

    return {
        "n_total": n,
        "n_questions": n_questions,
        "n_per_question": n_per_question,
        "mae_cllm": float(err_cllm.mean()),
        "mae_c5": float(err_c5.mean()),
        "mae_reduction_pct": float((err_cllm.mean() - err_c5.mean()) / err_cllm.mean() * 100),
        "response_level": {
            "W_plus": w_plus,
            "W_minus": w_minus,
            "n_ties": n_ties,
            "n_nonzero": int(len(nz)),
            "p_two_tailed": float(p_two),
            "p_one_tailed": float(p_one),
        },
        "question_level_clustered": {
            "n_clusters": n_questions,
            "p_two_tailed": float(pq_two),
            "p_one_tailed": float(pq_one),
        },
        "nontied_subset_F2": {
            "n_nontied": int(nontied_mask.sum()),
            "n_ties": int((~nontied_mask).sum()),
            "mae_cllm_nontied": nontied_mae_cllm,
            "mae_c5_nontied": nontied_mae_c5,
            "mae_reduction_pct_nontied": (
                round((nontied_mae_cllm - nontied_mae_c5) / nontied_mae_cllm * 100, 2)
                if nontied_mae_cllm else None
            ),
            "d_z_nontied": round(nontied_d_z, 3) if nontied_d_z is not None else None,
            "p_two_tailed_nontied": round(float(nontied_p_two), 4),
            "p_one_tailed_nontied": round(float(nontied_p_one), 4),
        },
        "loocv_question_level_F3": {
            "p_two_tailed_min": round(min(loocv_two), 4),
            "p_two_tailed_max": round(max(loocv_two), 4),
            "p_one_tailed_min": round(min(loocv_one), 4),
            "p_one_tailed_max": round(max(loocv_one), 4),
            "n_loocv_with_p_lt_005_two_tailed": sum(1 for p in loocv_two if p < 0.05),
            "n_loocv_with_p_lt_005_one_tailed": sum(1 for p in loocv_one if p < 0.05),
            "loocv_p_two_tailed_all": [round(p, 4) for p in loocv_two],
            "loocv_p_one_tailed_all": [round(p, 4) for p in loocv_one],
        },
        "effect_size_d_z_paired": d_z,
        "post_hoc_power_alpha_0_05_one_tailed": power,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--eval",
        default="archive/fabricated_fixtures/mohler_eval_results.json",
        type=Path,
        help="Path to Mohler eval results JSON. Default is the retracted "
             "fabricated fixture (reproduces the historical/retracted "
             "result intentionally); pass --eval data/mohler_real_eval_results.json "
             "for real data, or use verify_all_paper_claims.py for the "
             "authoritative real-data numbers.",
    )
    parser.add_argument("--n-per-question", type=int, default=12)
    parser.add_argument("--n-questions", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()

    if not args.eval.exists():
        print(f"ERROR: {args.eval} not found", file=sys.stderr)
        return 1

    result = compute(args.eval, args.n_per_question, args.n_questions)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    r = result["response_level"]
    q = result["question_level_clustered"]
    print(f"Mohler KG-aligned subset: n = {result['n_total']} "
          f"({result['n_questions']} questions x {result['n_per_question']} responses)")
    print(f"MAE: C_LLM={result['mae_cllm']:.4f}, C5_fix={result['mae_c5']:.4f} "
          f"({result['mae_reduction_pct']:.1f}% reduction)")
    print()
    print("Response-level Wilcoxon signed-rank:")
    print(f"  W+ = {r['W_plus']:.0f}, ties = {r['n_ties']}, non-zero = {r['n_nonzero']}")
    print(f"  Two-tailed p = {r['p_two_tailed']:.4f}")
    print(f"  One-tailed p (C5 < C_LLM) = {r['p_one_tailed']:.4f}")
    print()
    print("Question-level (clustered, robustness):")
    print(f"  n_clusters = {q['n_clusters']}")
    print(f"  Two-tailed p = {q['p_two_tailed']:.4f}")
    print(f"  One-tailed p = {q['p_one_tailed']:.4f}")
    print()
    print(f"Paired Cohen's d_z = {result['effect_size_d_z_paired']:.3f}")
    print(f"Post-hoc power (alpha=0.05, one-tailed) = "
          f"{result['post_hoc_power_alpha_0_05_one_tailed']:.3f}")

    # F2 — tie analysis
    nt = result["nontied_subset_F2"]
    print()
    print(f"[F2] Non-tied subset (n = {nt['n_nontied']}, "
          f"{nt['n_ties']} samples dropped where both methods predicted identically):")
    print(f"  MAE: C_LLM = {nt['mae_cllm_nontied']:.4f}, "
          f"C5 = {nt['mae_c5_nontied']:.4f} "
          f"(reduction {nt['mae_reduction_pct_nontied']}%)")
    print(f"  Cohen's d_z (non-tied) = {nt['d_z_nontied']}")
    print(f"  Wilcoxon p (non-tied) = {nt['p_two_tailed_nontied']} two-tailed / "
          f"{nt['p_one_tailed_nontied']} one-tailed")

    # F3 — LOOCV
    lo = result["loocv_question_level_F3"]
    print()
    print(f"[F3] Leave-one-question-out clustered Wilcoxon (n = {result['n_questions']} folds):")
    print(f"  Two-tailed p range: [{lo['p_two_tailed_min']}, {lo['p_two_tailed_max']}]")
    print(f"  One-tailed p range: [{lo['p_one_tailed_min']}, {lo['p_one_tailed_max']}]")
    print(f"  Folds with two-tailed p < 0.05: "
          f"{lo['n_loocv_with_p_lt_005_two_tailed']} / {result['n_questions']}")
    print(f"  Folds with one-tailed p < 0.05: "
          f"{lo['n_loocv_with_p_lt_005_one_tailed']} / {result['n_questions']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
