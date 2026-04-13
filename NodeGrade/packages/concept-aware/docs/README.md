# ConceptGrade System Overview Documentation

## Overview

This directory contains the ConceptGrade System Overview Word document and the Python script that generates it.

## Files

- **`build_word_doc.py`** — Main script that generates `ConceptGrade_System_Overview.docx`
- **`ConceptGrade_System_Overview.docx`** — Final Word document (auto-generated)
- **`ConceptGrade_System_Overview.md`** — Markdown version of the document content

## Running the Script

```bash
cd packages/concept-aware/docs
python3 build_word_doc.py
```

This will:
1. Generate 5 matplotlib diagrams as PNG images
2. Assemble a formatted Word document with proper heading hierarchy
3. Embed diagrams with captions
4. Add tables and evaluation summaries
5. Save as `ConceptGrade_System_Overview.docx`

The script cleans up temporary diagram files after assembly.

## Document Contents

The generated Word document includes:

1. **Architecture Diagram** (Figure 1)
   - Three-tier system: Python Pipeline → NestJS Backend → React Frontend
   - Data flow between layers (JSON files, HTTP/REST)

2. **Knowledge Graph Example** (Figure 2)
   - Ego-graph showing relationships around "Backpropagation"
   - 6 nodes colour-coded by category
   - 5 relationships with labelled edges
   - Legend explaining node categories

3. **Bidirectional Brushing Flow** (Figure 4)
   - Two independent interaction flows shown in separate coloured bands:
     - **Flow 1** (blue): Heatmap drill-down → Answer Panel filter → Student click → KG update
     - **Flow 2** (purple): Radar quartile select → Answer Panel re-filter
   - Clarifies that flows are independent (no connection between Flow 1 step 4 and Flow 2 step 1)

4. **Five-Stage Pipeline** (Figure 3)
   - Sequential grading pipeline: Self-Consistent Extractor → Confidence-Weighted Comparator → LLM-as-Verifier → Chain Coverage Scorer → Final Score + Explanation
   - Each stage receives prior stage's output for iterative refinement

5. **Study Conditions** (Figure 5)
   - Side-by-side comparison of Condition A (summary only) vs Condition B (full dashboard)

6. **Evaluation Tables & Metrics**
   - Results across three datasets (DigiKlausur, Kaggle ASAG, Mohler)
   - Statistical significance (Wilcoxon p-values)
   - MAE improvements with ablation analysis

## Design Principles

### Diagram Visibility at Document Scale

Diagrams are sized for clarity when embedded at 5.8" width in Word (54% scale from 150 DPI source):

- **Box spacing:** Generous gaps (e.g. gap = 1.0 unit in pipeline) ensure arrows remain visible
- **Arrow styling:** `lw=3.5, mutation_scale=28` for prominent arrows even at reduced scale
- **Font sizes:** Increased to compensate for document scale-down (e.g. 10–11pt → ~5.5pt at 54%)
- **Node layouts:** Spread to corners to minimize label overlaps (e.g. KG nodes at x ∈ {1.8, 5.0, 8.2})

### Knowledge Graph Node Positioning

```
     Gradient        Neural
     Descent         Network
    (1.8,5.5)       (8.2,5.5)
         \             /
          \           /
      Backpropagation
         (5.0,3.5)
          /           \
         /             \
   Learning         Weight
    Rate            Update
   (1.8,1.5)       (8.2,1.5)
         \             /
          \           /
           Chain Rule
          (5.0,1.0)
```

- Central "Backpropagation" node (blue) at figure centre
- Supporting nodes pushed to corners → maximum spacing
- Perimeter-based arrows (via numpy unit vectors) prevent clipping through nodes
- Edge labels placed at midpoints with white background for contrast

### Brushing Flow Independence

Figure 4 uses a two-band design to clearly separate two interaction flows:

```
┌─────────── Flow 1: Main Drill-Down ──────────────┐  (blue band)
│  [Click Heatmap] → [Filter Panel] → [Click Student] → [Update KG]  │
└──────────────────────────────────────────────────┘

        ↕ These flows are independent ↕

┌────────── Flow 2: Radar Filter (independent) ─────────┐  (purple band)
│  [Click Radar Quartile] → [Re-filter Panel]           │
└──────────────────────────────────────────────────────┘
```

**Why this design?**
- Visually separates two independent user interactions
- Clarifies that both flows ultimately update the Answer Panel
- Prevents confusion: there is NO arrow from Flow 1 box 4 to Flow 2 box 1
- Coloured bands (blue/purple) reinforce independence

## Spacing & Alignment

- **Image width:** 5.8" (fits on A4 with 1" margins)
- **Figure margins:**
  - Before: 10pt (breathing room from prior section)
  - After caption: 14pt (separation from next section)
- **Heading hierarchy:** H1 (document title) → H2 (main sections) → H3 (subsections)
- **Table styling:** Coloured headers, alternating row shading for readability

## Dependencies

- `matplotlib` (150 DPI for diagram generation)
- `python-docx` (Word document assembly)
- `numpy` (perimeter-based arrow calculations in KG diagram)

## Troubleshooting

**Diagrams appear pixelated or text too small?**
- Check figure DPI (set to 150 in `save_fig()`)
- Verify font sizes in diagram functions (e.g. 10pt title, 8.5pt body)

**Arrows invisible in Word?**
- Ensure `lw=3.5, mutation_scale=28` in ARROW dict
- Check box spacing: gap should be ≥ 1.0 unit for lw=3.5 to be visible at document scale
- Verify image width in `add_image()` call (5.8" recommended)

**Legend overlapping nodes in KG diagram?**
- Legend is positioned at `loc='lower center', ncol=2` to avoid node overlaps
- If still overlapping, reduce figure height or move nodes further apart

**Labels overlapping boxes in brushing flow?**
- Flow band heights are 3.2 units to provide clearance
- Labels positioned 0.3 units below band top (0.7 units above box tops)
- If overlap persists, increase figure height or move labels higher

## Future Enhancements

- [ ] Generate diagrams dynamically based on live evaluation data
- [ ] Add interactive PDF version with bookmarks
- [ ] Export diagrams as standalone SVG for presentation use
- [ ] Implement dark mode version for slides
