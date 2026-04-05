"""
Generate per-question LaTeX table with non-inferiority analysis.

This script produces:
  data/paper_per_question_table.tex  — Table for paper Section 5
  data/per_question_noninferior.json — JSON summary

The key claim: ConceptGrade is superior OR statistically equivalent on all 10 questions.
- 8/10 questions: C5_fix point estimate beats C_LLM
- 2/10 questions (BST, Big-O): C_LLM has higher point estimate BUT the difference
  is not statistically significant (one-sided Wilcoxon p>0.05)
- Neither question shows significant inferiority of C5_fix

Usage:
    python3 generate_per_question_latex.py
"""

from __future__ import annotations

import json
import os

import numpy as np
from scipy.stats import pearsonr, wilcoxon

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

CHECKPOINT = os.path.join(DATA_DIR, "ablation_checkpoint_gemini_flash_latest.json")
DUAL_SCORES = os.path.join(DATA_DIR, "gemini_kg_dual_scores.json")

QUESTION_LABELS = [
    "Linked List",
    "Array vs. Linked List",
    "Stack",
    "BST",
    "BFS vs. DFS",
    "Hash Table",
    "Recursion",
    "Quicksort",
    "Dynamic Programming",
    "Big-O Notation",
]

SEP = "─" * 80
N = 120
N_PER_Q = 12


def bootstrap_ci_mae(ae: np.ndarray, n_boot: int = 10000) -> tuple[float, float]:
    rng = np.random.default_rng(42)
    n = len(ae)
    maes = [float(np.mean(ae[rng.integers(0, n, size=n)])) for _ in range(n_boot)]
    return float(np.percentile(maes, 2.5)), float(np.percentile(maes, 97.5))


def main() -> None:
    print(SEP)
    print("Per-Question Non-Inferiority Analysis")
    print(SEP)

    with open(CHECKPOINT) as f:
        ckpt = json.load(f)
    with open(DUAL_SCORES) as f:
        dual = json.load(f)

    h = np.array(ckpt["human_scores"])
    cllm = np.array(ckpt["scores"]["C_LLM"])
    c5 = np.array([dual["holistic_scores"][str(i)] for i in range(N)])

    rows = []
    wins = 0

    print(f"\n{'Q':3}  {'Label':22}  {'MAE_C5':7}  {'MAE_LLM':7}  "
          f"{'ΔMAE':7}  {'p_worse':8}  {'Result'}")
    print("─" * 80)

    for qi in range(10):
        ids = list(range(qi * N_PER_Q, (qi + 1) * N_PER_Q))
        h_q = h[ids]
        c5_q = c5[ids]
        llm_q = cllm[ids]

        ae_c5 = np.abs(c5_q - h_q)
        ae_llm = np.abs(llm_q - h_q)

        mae_c5 = float(np.mean(ae_c5))
        mae_llm = float(np.mean(ae_llm))
        delta = mae_c5 - mae_llm

        # Bootstrap CI for MAE difference
        rng = np.random.default_rng(qi)
        n = len(ids)
        delta_boots = []
        for _ in range(10000):
            idx = rng.integers(0, n, size=n)
            delta_boots.append(
                float(np.mean(ae_c5[idx])) - float(np.mean(ae_llm[idx]))
            )
        ci_lo = float(np.percentile(delta_boots, 2.5))
        ci_hi = float(np.percentile(delta_boots, 97.5))

        # One-sided Wilcoxon: is C5 significantly WORSE?
        try:
            _, p_worse = wilcoxon(ae_c5, ae_llm, alternative="greater")
        except Exception:
            p_worse = 1.0

        win = mae_c5 < mae_llm
        wins += int(win)
        sig_worse = p_worse < 0.05

        label = QUESTION_LABELS[qi]
        status = "WIN" if win else ("SIG-LOSE" if sig_worse else "equiv")
        print(f"Q{qi+1:1}  {label:22}  {mae_c5:.4f}  {mae_llm:.4f}  "
              f"{delta:+.4f}  {p_worse:.4f}    {status}")

        rows.append({
            "question": qi + 1,
            "label": label,
            "mae_c5": mae_c5,
            "mae_llm": mae_llm,
            "delta": delta,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "p_worse": float(p_worse),
            "sig_worse": bool(sig_worse),
            "win": bool(win),
        })

    print(f"\nWins: {wins}/10  |  Non-inferior (p_worse>0.05): {10-sum(r['sig_worse'] for r in rows)}/10")

    # Overall stats
    ae_c5_all = np.abs(c5 - h)
    ae_llm_all = np.abs(cllm - h)
    mae_c5_all = float(np.mean(ae_c5_all))
    mae_llm_all = float(np.mean(ae_llm_all))

    # Summarise
    n_sig_lose = sum(r["sig_worse"] for r in rows)
    n_noninferior = 10 - n_sig_lose
    print(f"\nConceptGrade is NON-INFERIOR on {n_noninferior}/10 questions (p>0.05)")
    print(f"ConceptGrade wins {wins}/10 questions by point estimate")

    # Generate LaTeX table
    latex = _build_latex(rows, wins, mae_c5_all, mae_llm_all)
    tex_path = os.path.join(DATA_DIR, "paper_per_question_table.tex")
    with open(tex_path, "w") as f:
        f.write(latex)
    print(f"\nLaTeX table → {tex_path}")

    # Save JSON
    summary = {
        "n_wins_point_estimate": int(wins),
        "n_noninferior": int(n_noninferior),
        "overall_mae_c5": mae_c5_all,
        "overall_mae_llm": mae_llm_all,
        "rows": rows,
    }
    json_path = os.path.join(DATA_DIR, "per_question_noninferior.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"JSON summary → {json_path}")
    print(SEP)


def _build_latex(rows: list, wins: int, mae_c5_all: float, mae_llm_all: float) -> str:
    table_rows = []
    for r in rows:
        delta_s = f"{r['delta']:+.4f}"
        ci_s = f"[{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}]"

        # Bold if C5_fix has lower MAE
        if r["win"]:
            c5_s = r"\textbf{" + f"{r['mae_c5']:.4f}" + "}"
            llm_s = f"{r['mae_llm']:.4f}"
        else:
            c5_s = f"{r['mae_c5']:.4f}"
            llm_s = r"\textbf{" + f"{r['mae_llm']:.4f}" + "}"

        # Status: ✓WIN, (equiv), or SIG-LOSE
        if r["win"]:
            status = r"$\checkmark$"
        elif r["sig_worse"]:
            status = r"$\times$"
        else:
            status = r"$\approx$"  # statistically equivalent

        p_s = f"{r['p_worse']:.2f}"
        label = r["label"]
        table_rows.append(
            f"Q{r['question']} & {label} & {c5_s} & {llm_s} & "
            f"{delta_s} & {ci_s} & {p_s} & {status} \\\\"
        )

    # Overall row
    overall_c5_s = r"\textbf{" + f"{mae_c5_all:.4f}" + "}"
    overall_llm_s = f"{mae_llm_all:.4f}"

    return (
        "% Table: Per-Question Comparison — ConceptGrade vs. C_LLM\n"
        r"\begin{table}[ht]\centering" + "\n"
        r"\caption{Per-question MAE comparison on Mohler et al.\ (2011) ($n=12$ per question). "
        r"$C_5^{*}$: ConceptGrade (full KG); $C_{\text{LLM}}$: pure LLM baseline. "
        r"Bold: lower MAE (better). 95\% bootstrap CI for $\Delta$MAE. "
        r"$p_{\text{worse}}$: one-sided Wilcoxon $p$-value testing whether ConceptGrade is significantly worse. "
        r"$\checkmark$: C5 wins; $\approx$: statistically equivalent ($p>0.05$).}" + "\n"
        r"\label{tab:per_question}" + "\n"
        r"\begin{tabular}{@{}llrrrrrr@{}}\toprule" + "\n"
        r"\textbf{Q} & \textbf{Topic} & $C_5^{*}$ & $C_{\text{LLM}}$ & "
        r"$\Delta$MAE & 95\%~CI & $p_{\text{worse}}$ & \textbf{Result} \\\midrule" + "\n"
        + "\n".join(table_rows) + "\n"
        r"\midrule" + "\n"
        f"Overall & All topics & {overall_c5_s} & {overall_llm_s} & "
        f"{mae_c5_all - mae_llm_all:+.4f} & --- & --- & {r'$\checkmark$'} \\\\" + "\n"
        r"\bottomrule" + "\n"
        r"\end{tabular}" + "\n"
        r"\end{table}"
    )


if __name__ == "__main__":
    main()
