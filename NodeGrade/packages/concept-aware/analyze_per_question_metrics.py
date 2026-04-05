"""
Per-Question Pearson r and Precision@0.5 analysis.

Computes for each of the 10 question types:
  - Pearson r (C_LLM vs human, C5_fix vs human)
  - Precision@0.5 (fraction of scores within 0.5 of human)
  - MAE
  - Winner (C5_fix or C_LLM)

Questions are groups of 12 consecutive samples:
  Q0: IDs 0-11, Q1: 12-23, ..., Q9: 108-119

Usage:
    python3 analyze_per_question_metrics.py
"""

from __future__ import annotations

import json
import os

import numpy as np
from scipy.stats import pearsonr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

CHECKPOINT = os.path.join(DATA_DIR, "ablation_checkpoint_gemini_flash_latest.json")

SEP = "─" * 80

QUESTION_LABELS = {
    0: "G0  Linked List",
    1: "G1  Array vs LL",
    2: "G2  Stack",
    3: "G3  BST",          # IDs 36-47 — failing Q
    4: "G4  BFS/DFS",
    5: "G5  Hash Table",
    6: "G6  Recursion",
    7: "G7  Quicksort",
    8: "G8  Dyn. Prog.",
    9: "G9  Big-O",        # IDs 108-119 — failing Q
}

# Questions from the diagnosis: Q3 = IDs 36-47 (group index 3), Q9 = IDs 108-119 (group index 9)
# Each group: 12 samples, so group k = IDs [k*12 ... k*12+11]


def precision_at_threshold(human: np.ndarray, predicted: np.ndarray, threshold: float = 0.5) -> float:
    """Fraction of predictions within `threshold` of human score."""
    return float(np.mean(np.abs(human - predicted) <= threshold))


def safe_pearsonr(h: np.ndarray, p: np.ndarray) -> float:
    if np.std(h) < 1e-9 or np.std(p) < 1e-9:
        return float("nan")
    r, _ = pearsonr(h, p)
    return float(r)


def main() -> None:
    with open(CHECKPOINT) as f:
        ckpt = json.load(f)

    human = np.array(ckpt["human_scores"], dtype=float)
    c5 = np.array(ckpt["scores"]["C5_fix"], dtype=float)
    cllm = np.array(ckpt["scores"]["C_LLM"], dtype=float)

    n = len(human)
    n_questions = n // 12  # 10 questions × 12 samples

    print(SEP)
    print("Per-Question Analysis: Pearson r, Precision@0.5, MAE")
    print(f"Total samples: {n}  |  Questions: {n_questions}  |  Samples/Q: 12")
    print(SEP)

    # Header
    print(
        f"{'Q':>2}  {'Label':22}  "
        f"{'r_LLM':>6}  {'r_C5':>6}  "
        f"{'P@0.5_LLM':>9}  {'P@0.5_C5':>8}  "
        f"{'MAE_LLM':>7}  {'MAE_C5':>7}  "
        f"{'MAE_Win':>8}  {'r_Win':>6}"
    )
    print(SEP)

    wins_mae_c5 = 0
    wins_r_c5 = 0
    wins_prec_c5 = 0

    for q in range(n_questions):
        start = q * 12
        end = start + 12
        h = human[start:end]
        c5q = c5[start:end]
        llmq = cllm[start:end]

        r_llm = safe_pearsonr(h, llmq)
        r_c5 = safe_pearsonr(h, c5q)
        prec_llm = precision_at_threshold(h, llmq)
        prec_c5 = precision_at_threshold(h, c5q)
        mae_llm = float(np.mean(np.abs(h - llmq)))
        mae_c5 = float(np.mean(np.abs(h - c5q)))

        mae_winner = "C5_fix" if mae_c5 <= mae_llm else "C_LLM "
        r_winner = "C5_fix" if (not np.isnan(r_c5) and not np.isnan(r_llm) and r_c5 >= r_llm) else "C_LLM "

        if mae_c5 <= mae_llm:
            wins_mae_c5 += 1
        if not np.isnan(r_c5) and not np.isnan(r_llm) and r_c5 >= r_llm:
            wins_r_c5 += 1
        if prec_c5 >= prec_llm:
            wins_prec_c5 += 1

        label = QUESTION_LABELS.get(q, f"Q{q+1:2d}")

        # Mark failing Qs
        flag = ""
        if q == 3 and mae_c5 > mae_llm:
            flag = " ← Q3 FAIL"
        if q == 9 and mae_c5 > mae_llm:
            flag = " ← Q9 FAIL"

        print(
            f"{q:>2}  {label:22}  "
            f"{r_llm:>6.3f}  {r_c5:>6.3f}  "
            f"{prec_llm:>9.3f}  {prec_c5:>8.3f}  "
            f"{mae_llm:>7.4f}  {mae_c5:>7.4f}  "
            f"{mae_winner:>8}  {r_winner:>6}{flag}"
        )

    print(SEP)
    print(f"C5_fix MAE wins: {wins_mae_c5}/{n_questions}")
    print(f"C5_fix Pearson r wins: {wins_r_c5}/{n_questions}")
    print(f"C5_fix Precision@0.5 wins: {wins_prec_c5}/{n_questions}")
    print(SEP)

    # Overall
    overall_mae_llm = float(np.mean(np.abs(human - cllm)))
    overall_mae_c5 = float(np.mean(np.abs(human - c5)))
    overall_r_llm = safe_pearsonr(human, cllm)
    overall_r_c5 = safe_pearsonr(human, c5)
    overall_prec_llm = precision_at_threshold(human, cllm)
    overall_prec_c5 = precision_at_threshold(human, c5)

    print(f"\nOVERALL (all {n} samples):")
    print(f"  C_LLM:   MAE={overall_mae_llm:.4f}  r={overall_r_llm:.4f}  Prec@0.5={overall_prec_llm:.3f}")
    print(f"  C5_fix:  MAE={overall_mae_c5:.4f}  r={overall_r_c5:.4f}  Prec@0.5={overall_prec_c5:.3f}")
    print()

    # Focus on Q3 (group 3, IDs 36-47) and Q9 (group 9, IDs 108-119)
    print("=== Q3 (BST, IDs 36-47) Detail ===")
    for i, sid in enumerate(range(36, 48)):
        h_i = human[sid]
        c5_i = c5[sid]
        llm_i = cllm[sid]
        err_c5 = abs(h_i - c5_i)
        err_llm = abs(h_i - llm_i)
        winner = "C5" if err_c5 <= err_llm else "LLM"
        print(f"  ID {sid}: human={h_i:.2f}  C5={c5_i:.2f}(err={err_c5:.2f})  LLM={llm_i:.2f}(err={err_llm:.2f})  win={winner}")

    print()
    print("=== Q9 (Big-O, IDs 108-119) Detail ===")
    for i, sid in enumerate(range(108, 120)):
        h_i = human[sid]
        c5_i = c5[sid]
        llm_i = cllm[sid]
        err_c5 = abs(h_i - c5_i)
        err_llm = abs(h_i - llm_i)
        winner = "C5" if err_c5 <= err_llm else "LLM"
        print(f"  ID {sid}: human={h_i:.2f}  C5={c5_i:.2f}(err={err_c5:.2f})  LLM={llm_i:.2f}(err={err_llm:.2f})  win={winner}")

    print(SEP)


if __name__ == "__main__":
    main()
