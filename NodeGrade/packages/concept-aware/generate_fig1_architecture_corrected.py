#!/usr/bin/env python3
"""
generate_fig1_architecture_corrected.py -- regenerates fig1_architecture.png
with the REAL system description. The prior version of this figure stated
the wrong LLM ("Llama-3.3-70b" -- the paper's own text and
verify_all_paper_claims.py explicitly confirm the real model is
gemini-2.5-flash) and a stale/incorrect Layer 5 formula
("0.25*coverage + 0.20*depth + 0.20*SOLO + 0.15*accuracy" -- the real,
extensively-verified formula is
knowledge = 0.45*cov + 0.35*acc + 0.20*int,
depth = 0.55*blooms + 0.45*solo,
s_kg = (0.60*knowledge + 0.40*depth)*(1 - misc_penalty),
final = (1-w)*s_kg + w*verified, deployed w=1.0).
Same visual style as the original (box-and-arrow 5-layer diagram),
factually corrected content only.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

FIGURES_DIR = Path(__file__).parent / "docs" / "figures"

LAYER_COLORS = [
    ("#2563eb", "#eff6ff"),  # Layer 1 - blue
    ("#059669", "#ecfdf5"),  # Layer 2 - green
    ("#7c3aed", "#f5f3ff"),  # Layer 3 - purple
    ("#ea580c", "#fff7ed"),  # Layer 4 - orange
    ("#dc2626", "#fef2f2"),  # Layer 5 - red
]

LAYERS = [
    ("Layer 1", "Concept Extraction",
     "LLM (gemini-2.5-flash) with $3\\times$ self-consistency\n"
     "extracts concepts, relationships, depth from student answer"),
    ("Layer 2", "Knowledge Graph\nComparison",
     "Deterministic, LLM-free matcher: coverage, relationship\n"
     "accuracy, integration vs. expert domain KG"),
    ("Layer 3", "Cognitive Depth\nAssessment",
     "Bloom's Taxonomy (L1-L6)\n"
     "SOLO Taxonomy (L1-L5), LLM classifier"),
    ("Layer 4", "Misconception\nDetection",
     "16-entry taxonomy (DS-STACK-01, DS-TREE-01...)\n"
     "severity + remediation hints"),
    ("Layer 5", "Score Synthesis\n+ Verification",
     "knowledge = 0.45cov + 0.35acc + 0.20int\n"
     "$s_{kg}$ = (0.60knowledge + 0.40depth)(1-misc); Verifier blends at $w{=}1.0$"),
]

fig, ax = plt.subplots(figsize=(13, 8))
ax.set_xlim(0, 13)
ax.set_ylim(-0.4, 7.5)
ax.axis("off")

ax.text(6.5, 7.15, "ConceptGrade — 5-Layer Concept-Aware Assessment Architecture",
        fontsize=17, fontweight="bold", ha="center")
ax.text(6.5, 6.75, "INPUT: Question + Student Answer",
        fontsize=11, style="italic", color="#6b7280", ha="center")

box_h = 1.05
gap = 0.15
top = 6.35
for i, ((edge, face), (layer, title, desc)) in enumerate(zip(LAYER_COLORS, LAYERS)):
    y = top - i * (box_h + gap) - box_h
    rect = mpatches.FancyBboxPatch(
        (0.3, y), 12.4, box_h,
        boxstyle="round,pad=0.02,rounding_size=0.06",
        linewidth=2.2, edgecolor=edge, facecolor=face,
    )
    ax.add_patch(rect)
    ax.text(0.65, y + box_h / 2 + 0.12, layer, fontsize=12, fontweight="bold",
            color=edge, va="center")
    ax.text(0.65, y + box_h / 2 - 0.22, title, fontsize=13, fontweight="bold",
            color="#111827", va="center")
    ax.text(4.7, y + box_h / 2, desc, fontsize=10.5, color="#374151", va="center",
            linespacing=1.6)
    if i < len(LAYERS) - 1:
        ax.text(6.5, y - gap / 2, "▾", fontsize=13, color="#9ca3af", ha="center", va="center")

bottom = top - len(LAYERS) * (box_h + gap) + gap
ax.text(6.5, bottom - 0.35,
        "OUTPUT: Score [0-5] + Feedback + Bloom's Level + SOLO Level + Misconceptions",
        fontsize=11, style="italic", color="#6b7280", ha="center")

plt.tight_layout()
out_path = FIGURES_DIR / "fig1_architecture.png"
plt.savefig(out_path, dpi=160, bbox_inches="tight", facecolor="white")
print(f"[saved] {out_path}")
