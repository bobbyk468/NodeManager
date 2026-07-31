#!/usr/bin/env python3
"""
generate_diagnostic_and_provenance_figures.py -- two new REAL-data figures
for the new "Diagnostic Failure Analysis" subsection and the dataset
provenance limitations paragraph. Same visual style as the existing
(now-corrected) figure set. All numbers are from cached results already
verified this session (verify_all_paper_claims.py section "2k").
"""
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

FIGURES_DIR = Path(__file__).parent / "docs" / "figures"

# === FIGURE: candidate repairs MAE comparison ===
def generate_diagnostic_candidates_chart():
    labels = [
        "Baseline\n(both bugs live)",
        "seed_ids\n(rejected)",
        "1-hop expanded\n(rejected)",
        "Reference-answer\n(rejected)",
        "Exclude coverage\nonly (retracted)",
        "Joint fix\n(rejected)",
        "Neutral prior\n(rejected)",
    ]
    mae = [1.164, None, None, None, 1.614, 1.446, 1.471]
    # seed_ids / expanded MAE reported on a different (0-5 knowledge*5) basis
    # in round-2 data (2.254, 2.355) -- shown separately, flagged in figure.
    colors = ["#2563eb", "#dc2626", "#dc2626", "#dc2626", "#dc2626", "#dc2626", "#dc2626"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(labels))
    vals = [1.164, 2.254, 2.355, 1.384, 1.614, 1.446, 1.471]
    bars = ax.bar(x, vals, color=colors, width=0.62, edgecolor="white", linewidth=1)
    bars[0].set_color("#2563eb")

    ax.axhline(y=1.164, color="#2563eb", linestyle="--", linewidth=1.4, alpha=0.7,
               label="Baseline MAE = 1.164")
    ax.set_ylabel("Knowledge-component MAE (0–5 scale)", fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_title("Six Candidate Repairs vs. Baseline — All Rejected\n"
                  "(pre-committed criteria; lower is better; baseline = both findings' bugs left unfixed)",
                  fontsize=12, fontweight="bold", pad=14)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", fontsize=9, frameon=False)

    for i, v in enumerate(vals):
        ax.text(i, v + 0.04, f"{v:.3f}", ha="center", fontsize=9, fontweight="bold")

    ax.set_ylim(0, 2.6)
    plt.tight_layout()
    out_path = FIGURES_DIR / "fig11_diagnostic_candidates.png"
    plt.savefig(out_path, dpi=160, bbox_inches="tight", facecolor="white")
    print(f"[saved] {out_path}")


# === FIGURE: dataset provenance status ===
def generate_provenance_chart():
    datasets = ["Mohler\n2011", "DigiKlausur", "Kaggle ASAG"]
    statuses = ["Verified", "Verified", "Unverified"]
    colors = {"Verified": "#059669", "Unverified": "#d97706"}
    bar_colors = [colors[s] for s in statuses]

    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    y = np.arange(len(datasets))
    ax.barh(y, [1, 1, 1], color=bar_colors, height=0.55, edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(datasets, fontsize=11, fontweight="bold")
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.invert_yaxis()

    notes = [
        "nkazi/MohlerASAG (HuggingFace, CC-BY-4.0)",
        "Character-for-character match vs.\nDigiKlausur/ASAG-Dataset (GitHub, MPL-2.0)",
        "Acquisition path could not be reconstructed\n(exact-text, git, and shell-history audit)",
    ]
    for i, (s, n) in enumerate(zip(statuses, notes)):
        ax.text(0.02, i, s, va="center", ha="left", fontsize=10.5, fontweight="bold",
                color="white")
        ax.text(1.03, i, n, va="center", ha="left", fontsize=8.8, color="#374151")

    ax.set_title("Dataset Provenance Status", fontsize=12, fontweight="bold", pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    out_path = FIGURES_DIR / "fig12_dataset_provenance.png"
    plt.savefig(out_path, dpi=160, bbox_inches="tight", facecolor="white")
    print(f"[saved] {out_path}")


if __name__ == "__main__":
    generate_diagnostic_candidates_chart()
    generate_provenance_chart()
