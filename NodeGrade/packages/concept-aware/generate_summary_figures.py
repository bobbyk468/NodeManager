#!/usr/bin/env python3
"""
generate_summary_figures.py -- two new summary visuals for the main body,
built from numbers already reported in Table V (cross-dataset boundary,
Section V-D) and Table X (real-data 3-condition ablation, Section VI).
No new computation: every value here is copied verbatim from the paper's
own tables. Styled with the same validated palette used across all other
figures in this paper (docs/figures/*.png).
"""
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

FIGURES_DIR = Path(__file__).parent / "docs" / "figures"

BLUE = "#2a78d6"      # hero / ConceptGrade / in-domain
ORANGE = "#eb6834"    # baseline / marginal domain
MUTED = "#898781"     # null-effect / weakest
CRITICAL = "#d03b3b"  # far worse than baseline
GRID = "#e1e0d9"
INK = "#0b0b0b"
SECONDARY_INK = "#52514e"


def fig_cross_dataset_boundary():
    """Table V, Section V-D: MAE reduction (%) across the three datasets,
    with paired Cohen's d_z, coloured by how in-domain the dataset is."""
    datasets = ["Mohler 2011\n(CS Data Structures)", "DigiKlausur\n(Neural Networks)",
                "Kaggle ASAG\n(Elementary Science)"]
    mae_reduction = [8.2, 4.9, 0.6]
    dz = [-0.154, -0.067, -0.007]
    n = [1262, 646, 368]
    q = [46, 17, 150]
    sig = ["response-level\n$p<0.0001$", "response-level\n$p=0.049$", "n.s.\n$p=0.702$"]
    colors = [BLUE, ORANGE, MUTED]

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    x = np.arange(3)
    bars = ax.bar(x, mae_reduction, color=colors, width=0.55, edgecolor="white", linewidth=1.5, zorder=3)

    for i, (v, d, s) in enumerate(zip(mae_reduction, dz, sig)):
        ax.text(i, v + 0.35, f"{v:.1f}%", ha="center", fontsize=15, fontweight="bold", color=INK)
        ax.text(i, v + 1.5, f"$d_z={d:.3f}$", ha="center", fontsize=10.5, color=SECONDARY_INK)
        ax.text(i, -1.15, s, ha="center", fontsize=9, color=SECONDARY_INK, linespacing=1.4)

    ax.set_xticks(x)
    ax.set_xticklabels(datasets, fontsize=10.5)
    ax.set_ylabel("MAE reduction over identical-model LLM baseline (%)", fontsize=11, fontweight="bold", color=INK)
    ax.set_title("Cross-Dataset Boundary: the Effect Shrinks as Domain Vocabulary\nMoves Away From the Knowledge Graph",
                 fontsize=12.5, fontweight="bold", pad=14, color=INK)
    ax.axhline(0, color="#c3c2b7", linewidth=1, zorder=2)
    ax.grid(axis="y", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#c3c2b7")
    ax.set_ylim(-2.2, 10.5)
    ax.tick_params(colors=SECONDARY_INK)

    # small n/Q footnote
    footnote = "  |  ".join(f"{ds.split(chr(10))[0]}: n={nn:,}, Q={qq}" for ds, nn, qq in
                             zip(["Mohler", "DigiKlausur", "Kaggle ASAG"], n, q))
    ax.text(0.5, -0.24, footnote, transform=ax.transAxes, ha="center", fontsize=8.3, color=SECONDARY_INK)

    plt.tight_layout()
    out = FIGURES_DIR / "fig13_cross_dataset_boundary.png"
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"[saved] {out}")


def fig_ablation_decomposition():
    """Table X, Section VI: real-data 3-condition ablation on Mohler --
    shows the deterministic KG-formula score alone is far worse than the
    zero-shot baseline, and the verifier is what makes the full pipeline work."""
    labels = ["C_LLM\n(no KG)", "kg_score\n(KG, no verifier)", "C5_fix\n(full pipeline)"]
    mae = [1.282, 2.397, 1.177]
    colors = [ORANGE, CRITICAL, BLUE]

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    x = np.arange(3)
    bars = ax.bar(x, mae, color=colors, width=0.5, edgecolor="white", linewidth=1.5, zorder=3)

    for i, v in enumerate(mae):
        ax.text(i, v + 0.05, f"{v:.3f}", ha="center", fontsize=14, fontweight="bold", color=INK)

    ax.annotate("", xy=(1, 2.2), xytext=(0, 2.2),
                arrowprops=dict(arrowstyle="-", color=SECONDARY_INK, linewidth=1))
    ax.text(0.5, 2.27, "$-86.9\\%$ worse", ha="center", fontsize=9.5, color=CRITICAL, fontweight="bold")

    ax.annotate("", xy=(2, 2.55), xytext=(1, 2.55),
                arrowprops=dict(arrowstyle="-", color=SECONDARY_INK, linewidth=1))
    ax.text(1.5, 2.62, "verifier recovers it", ha="center", fontsize=9.5, color=BLUE, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("MAE on real Mohler sample ($n=1{,}262$, lower is better)", fontsize=11, fontweight="bold", color=INK)
    ax.set_title("Where the Gain Actually Comes From: the Verifier, Not the\nKnowledge-Graph Score Alone",
                 fontsize=12.5, fontweight="bold", pad=14, color=INK)
    ax.grid(axis="y", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#c3c2b7")
    ax.set_ylim(0, 2.9)
    ax.tick_params(colors=SECONDARY_INK)

    plt.tight_layout()
    out = FIGURES_DIR / "fig14_ablation_decomposition.png"
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"[saved] {out}")


if __name__ == "__main__":
    fig_cross_dataset_boundary()
    fig_ablation_decomposition()
