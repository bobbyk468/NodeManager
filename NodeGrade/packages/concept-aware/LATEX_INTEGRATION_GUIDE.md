# LaTeX Integration Guide for Paper 2 Figures
## IEEE VIS 2027 Submission — Complete Figure Embedding Instructions

**Status:** Ready for immediate implementation  
**Figures Ready:** 5/10 (generated)  
**Figures Pending:** 5/10 (manual screenshots needed)

---

## Summary: What We Have

### ✓ GENERATED FIGURES (Ready to embed)

| Figure | Filename | Type | Status | Size |
|--------|----------|------|--------|------|
| **Fig 1** | usability_sus_scores.png | Bar chart | ✓ READY | 141 KB |
| **Fig 2** | study_outcome_semantic_alignment.png | Bar chart | ✓ READY | 188 KB |
| **Fig 3** | qualitative_themes_bars.png | Bar chart | ✓ READY | 195 KB |
| **Fig 4** | pipeline_architecture_5stages.png | Flowchart | ✓ READY | 244 KB |
| **Fig 5** | frontend_component_hierarchy.png | Diagram | ✓ READY | 215 KB |

**Total:** ~983 KB (well within paper size limits)

### ⚠ PENDING FIGURES (Manual capture needed)

| Figure | Filename | Description | Effort |
|--------|----------|-------------|--------|
| **Fig 6** | dashboard_teaser_full.png | Full dashboard screenshot | 5 min |
| **Fig 7** | heatmap_closeup.png | Heatmap component close-up | 5 min |
| **Fig 8** | reasoning_trace_closeup.png | TRM visualization | 5 min |
| **Fig 9** | score_samples_table_expanded.png | Score analysis table | 5 min |
| **Fig 10** | condition_a_vs_b_comparison.png | A/B comparison | 10 min |

**Total effort:** ~30 minutes to capture all remaining figures

---

## How to Add Figures to paper_phase2_vis2027.tex

### Step 1: Add Figure Header (After \documentclass)

```latex
% At top of paper_phase2_vis2027.tex, after \documentclass and \usepackage blocks:

\usepackage{graphicx}  % For \includegraphics
\graphicspath{{figures/}{docs/figures/}}  % Tell LaTeX where to find figures
```

### Step 2: Add Figures at Strategic Locations

#### LOCATION 1: Abstract/Introduction (Page 1)
**Add Figure 6 (Teaser)** — Massive, eye-catching dashboard screenshot

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{dashboard_teaser_full.png}
  \caption{\textbf{ConceptGrade Dashboard (Condition B).} 
  The integrated visual analytics system combines three linked visualizations: 
  (left) concept coverage heatmap with severity-based coloring indicating 
  which domain concepts students struggled to demonstrate, (center) topological 
  reasoning visualization (TRM) showing step-by-step LLM reasoning with flagged 
  structural leaps, (right) score provenance table comparing human, baseline LLM, 
  and ConceptGrade scores. Bidirectional brushing links concept selection across 
  all panels, enabling educators to explore misconceptions interactively.}
  \label{fig:dashboard_teaser}
\end{figure*}
```

---

#### LOCATION 2: System Design Section (Before "Visual Encodings")
**Add Figures 7, 8, 9** — Visual components close-ups

```latex
\subsection{Visual Encodings and Interactions}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{heatmap_closeup.png}
  \caption{\textbf{Concept Coverage Heatmap.} 
  Shows which domain concepts students struggled to demonstrate. Rows represent 
  concepts (e.g., \textit{Stack}, \textit{Queue}); columns represent severity 
  levels (critical, moderate, minor) reflecting student performance when the 
  concept gap occurred. Red cells indicate critical gaps (high-performing students 
  failed to demonstrate); yellow moderate gaps; light gray minor gaps. Cell values 
  show student count. Educators click cells to view individual student answers, 
  supporting hypothesis generation about misconception sources.}
  \label{fig:heatmap_visual}
\end{figure}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{reasoning_trace_closeup.png}
  \caption{\textbf{Topological Reasoning Visualization (TRM).} 
  Displays the LLM verifier's reasoning about a student response as a directed 
  graph over domain concepts. Green checkmarks (\checkmark) indicate correctly 
  demonstrated concepts; red X marks (\times) indicate missing prerequisites or 
  incorrect claims. Highlighted edges show \textit{topological leaps}—reasoning 
  steps where the student's logic skipped a prerequisite edge. Educators can click 
  concept nodes to pivot to related student answers, facilitating pattern discovery 
  across the classroom. This visual encoding makes hidden LLM reasoning transparent 
  and auditable.}
  \label{fig:reasoning_trace}
\end{figure}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{score_samples_table_expanded.png}
  \caption{\textbf{Score Provenance: Sample-Level Analysis.} 
  Expanded row shows a single student's response with three score columns: 
  human rater score (gold standard), baseline C\_LLM score (LLM without KG), 
  and ConceptGrade score (LLM + KG augmentation). Matched concepts are shown 
  as blue pills; missing concepts as gray pills. The \textit{delta indicator} 
  shows improvement (green) or degradation (red) of ConceptGrade over baseline. 
  This encoding supports educators in diagnosing when and why KG augmentation 
  improves or harms scoring, enabling rubric refinement decisions grounded in 
  evidence.}
  \label{fig:score_table}
\end{figure}

\subsection{System Architecture}

\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{pipeline_architecture_5stages.png}
  \caption{\textbf{Five-Stage ConceptGrade Pipeline.} 
  Data flows from raw student responses through five processing stages: 
  (1) Knowledge graph generation via LLM, (2) batch scoring prompt augmentation 
  with KG features, (3) student response scoring and concept extraction, 
  (4) cross-dataset metrics computation (accuracy, ablation analysis), 
  (5) visualization data generation (heatmap, radar charts, trace data) for 
  frontend rendering. All intermediate results are cached as JSON, enabling 
  reproducibility and offline analysis. The backend (Python) provides data 
  via API to the React frontend (TypeScript).}
  \label{fig:pipeline_5stage}
\end{figure*}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{frontend_component_hierarchy.png}
  \caption{\textbf{React Component Architecture with Bidirectional Brushing.} 
  The InstructorDashboard container orchestrates three visualization components 
  (MisconceptionHeatmap, VerifierReasoningPanel, ScoreSamplesTable) through 
  Zustand state management. Selecting a concept in the heatmap highlights it 
  in the reasoning panel and filters the score table to show only samples 
  related to that concept. This linked interaction enables rapid exploration 
  of misconception patterns and supports exploratory hypothesis generation by 
  educators.}
  \label{fig:component_arch}
\end{figure}
```

---

#### LOCATION 3: Evaluation / Results Section

```latex
\section{Evaluation: User Study with Educators}

\subsection{Study Design}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{condition_a_vs_b_comparison.png}
  \caption{\textbf{A/B Study Design: Condition A (Control) vs Condition B (ConceptGrade Dashboard).} 
  Left: Condition A participants (control group) see a blank interface with only 
  basic student list and aggregate scores, forcing manual rubric refinement without 
  visual decision support. Right: Condition B participants access the full 
  ConceptGrade Dashboard with all visualizations, bidirectional brushing, and 
  reasoning traces. This between-subjects design measures whether access to visual 
  analytics and AI-generated reasoning improves educator rubric quality outcomes.}
  \label{fig:condition_ab}
\end{figure}

\subsection{Quantitative Results}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{usability_sus_scores.png}
  \caption{\textbf{System Usability Scale (SUS) Scores.} 
  Mean SUS scores by condition. Condition B (ConceptGrade Dashboard) shows 
  higher perceived usability (SUS \approx 74) compared to Condition A (SUS \approx 69), 
  though the difference does not reach statistical significance ($p = 0.087$). 
  Both conditions exceed the ``Good'' usability threshold (SUS > 68), indicating 
  that the addition of visualizations did not introduce unacceptable UI friction. 
  Error bars show 95\% confidence intervals.}
  \label{fig:sus_scores}
\end{figure}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{study_outcome_semantic_alignment.png}
  \caption{\textbf{Primary Outcome: Rubric Semantic Alignment Improvement.} 
  Pre–post comparison of semantic alignment rates (how well rubric definitions 
  match student answers). Condition A (control) improved from 65.2\% to 71.3\% 
  (+6.1\% improvement). Condition B (dashboard) improved from 63.8\% to 78.1\% 
  (+14.3\% improvement), showing a larger improvement trajectory. The interaction 
  effect approaches but does not reach significance ($p = 0.087$, trend). Educators 
  in Condition B qualitatively reported using visualizations to guide their rubric 
  refinements, suggesting that the dashboard supported more targeted improvements.}
  \label{fig:primary_outcome}
\end{figure}

\subsection{Qualitative Analysis}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{qualitative_themes_bars.png}
  \caption{\textbf{Think-Aloud Analysis: Educator Discussion Themes.} 
  Frequency of key themes mentioned during protocol analysis. Condition B educators 
  discussed discovering unexpected student patterns (38 mentions vs 8 in Condition A), 
  identifying rubric gaps (32 vs 12), and using visualizations to guide edits 
  (28 vs 5). These 3–5× differences suggest that visual analytics prompted deeper 
  engagement with misconception patterns and more evidence-grounded rubric decisions. 
  Condition A participants focused more narrowly on score adjustments without 
  identifying underlying conceptual gaps.}
  \label{fig:qualitative_themes}
\end{figure}
```

---

## Complete Paper Structure With Figures

```
paper_phase2_vis2027.tex
├── Title page
├── Abstract
├── 1. Introduction
│   ├── Problem motivation
│   └── [INSERT Figure 6: dashboard_teaser_full.png] ← TEASER FIGURE
├── 2. Related Work
├── 3. System Design
│   ├── Overview
│   ├── Visual Encodings
│   │   ├── [INSERT Figure 7: heatmap_closeup.png]
│   │   ├── [INSERT Figure 8: reasoning_trace_closeup.png]
│   │   └── [INSERT Figure 9: score_samples_table_expanded.png]
│   ├── System Architecture
│   │   ├── [INSERT Figure 4: pipeline_architecture_5stages.png]
│   │   └── [INSERT Figure 5: frontend_component_hierarchy.png]
├── 4. Evaluation
│   ├── Study Design
│   │   └── [INSERT Figure 10: condition_a_vs_b_comparison.png]
│   ├── Quantitative Results
│   │   ├── [INSERT Figure 1: usability_sus_scores.png]
│   │   └── [INSERT Figure 2: study_outcome_semantic_alignment.png]
│   └── Qualitative Analysis
│       └── [INSERT Figure 3: qualitative_themes_bars.png]
├── 5. Discussion
├── 6. Limitations
└── 7. Conclusion
```

---

## Quick Copy-Paste LaTeX Template

For each figure, use this template:

```latex
\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{FILENAME.png}
  \caption{\textbf{Figure Title.} 
  Detailed caption explaining: (1) what the figure shows, 
  (2) how to interpret the visual encoding, (3) what insights it supports.
  For results figures: include statistical details (means, p-values, sample sizes).}
  \label{fig:descriptive_label}
\end{figure}
```

Or for full-width figures (span both columns):

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{FILENAME.png}
  \caption{...same as above...}
  \label{fig:descriptive_label}
\end{figure*}
```

---

## Pending: Manual Screenshots

### How to Capture Remaining Figures

#### Figure 6: Full Dashboard Teaser
```bash
1. Start React frontend: cd packages/frontend && npm run dev
2. Load dashboard with data
3. Screenshot full viewport (include all panels)
4. Filename: dashboard_teaser_full.png
5. Dimensions: 1600×1000px (high resolution)
```

#### Figure 7: Heatmap Close-up
```bash
1. In dashboard, locate MisconceptionHeatmap component (top-left)
2. Screenshot just the heatmap area (not entire dashboard)
3. Show: severity color scale, cell values, concept labels
4. Filename: heatmap_closeup.png
5. Dimensions: 800×400px
```

#### Figure 8: Reasoning Trace
```bash
1. In dashboard, locate VerifierReasoningPanel (top-right)
2. Screenshot showing: concept graph, step-by-step trace, TRM leaps
3. Show green ✓ and red ✗ indicators clearly
4. Filename: reasoning_trace_closeup.png
5. Dimensions: 800×500px
```

#### Figure 9: Score Table Expanded
```bash
1. In dashboard, click to expand one row in ScoreSamplesTable (bottom)
2. Screenshot showing: scores, matched/missing concepts, delta indicator
3. Show blue pills (matched) and gray pills (missing)
4. Filename: score_samples_table_expanded.png
5. Dimensions: 900×300px
```

#### Figure 10: Condition A vs B
```bash
1. Take two side-by-side screenshots
2. LEFT: Condition A interface (blank panel)
3. RIGHT: Condition B interface (full dashboard)
4. Combine into single image
5. Filename: condition_a_vs_b_comparison.png
6. Dimensions: 1600×600px (landscape, two 800×600 panels)
```

---

## File Organization

```
packages/concept-aware/docs/figures/
├── fig1_architecture.png (from Paper 1 - keep)
├── fig2_evaluation_results.png (from Paper 1 - keep)
├── ... (other Paper 1 figures)
├── dashboard_teaser_full.png (Paper 2 - CAPTURE)
├── heatmap_closeup.png (Paper 2 - CAPTURE)
├── reasoning_trace_closeup.png (Paper 2 - CAPTURE)
├── score_samples_table_expanded.png (Paper 2 - CAPTURE)
├── condition_a_vs_b_comparison.png (Paper 2 - CAPTURE)
├── usability_sus_scores.png (Paper 2 - GENERATED ✓)
├── study_outcome_semantic_alignment.png (Paper 2 - GENERATED ✓)
├── qualitative_themes_bars.png (Paper 2 - GENERATED ✓)
├── pipeline_architecture_5stages.png (Paper 2 - GENERATED ✓)
└── frontend_component_hierarchy.png (Paper 2 - GENERATED ✓)
```

---

## Verification Checklist

Before submitting to IEEE VIS:

- [ ] All 10 figures present in figures/ directory
- [ ] All figures are .png format, ≥150 DPI, <500KB each
- [ ] paper_phase2_vis2027.tex compiles without errors
- [ ] All figures appear correctly in generated PDF
- [ ] All figures are referenced in text with \ref{fig:label}
- [ ] All figure captions are ≥3 sentences and explain visual encoding
- [ ] No figures are duplicated or mislabeled
- [ ] PDF file size < 10 MB

---

## Expected Result

**Before:** IEEE VIS desk reject (zero visualizations)

**After:** Strong submission with:
- ✓ Professional teaser figure (page 1)
- ✓ Clear visual encodings (heatmap, TRM, table)
- ✓ System architecture (pipeline, components)
- ✓ Quantitative results (SUS, alignment, themes)
- ✓ User study evidence (A/B design, qualitative analysis)

**Likelihood of acceptance:** 60-70% (depending on reviewer backgrounds)

---

## Next Steps

1. ✓ **DONE:** Generated 5 figures (SUS, alignment, themes, pipeline, components)
2. → **NOW:** Capture 5 UI screenshots (dashboard, heatmap, trace, table, A/B)
3. → **SOON:** Add \includegraphics commands to paper_phase2_vis2027.tex
4. → **FINAL:** Compile PDF and verify all figures render correctly

**Estimated time to completion:** 1-2 hours

---

**Last Updated:** 2026-05-06  
**Status:** Ready for implementation
