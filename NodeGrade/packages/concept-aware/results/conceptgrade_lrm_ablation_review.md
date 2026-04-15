# ConceptGrade — LRM Ablation Study: Results & Review Request

**Prepared for:** Gemini AI Review  
**Date:** 2026-04-14  
**Context:** PhD research toward IEEE VIS 2027 VAST submission ("Visual Analytics for Explainable AI Grading")

---

## 1. System Overview

**ConceptGrade** is a 5-stage automated short-answer grading system that grounds scoring in a domain Knowledge Graph (KG) rather than relying solely on LLM judgment.

### 5-Stage Pipeline

| Stage | Name | Description |
|-------|------|-------------|
| 1 | Question Parsing | Extract expected concepts from rubric using Gemini 2.5 Flash |
| 2 | Concept Matching | Semantic matching of student answer against KG concepts (TF-IDF + embeddings) |
| 3a | LRM Verifier | Reasoning model (DeepSeek-R1 or Gemini 2.5 Flash w/ thinking) verifies domain logic validity |
| 3b | Trace Parser | Parses the verifier's chain-of-thought into structured steps (SUPPORTS / CONTRADICTS / UNCERTAIN) |
| 4 | Chain Coverage | % of expected KG relationship chain covered by student concepts |
| 5 | Score Aggregation | Weighted combination → final 0–5 score |

### Conditions Being Compared

- **C_LLM** — Pure LLM baseline (Gemini 2.5 Flash, no KG grounding)
- **C5** — Full 5-stage ConceptGrade pipeline (KG-grounded, no LRM trace adjustment)
- **LRM-adjusted** — C5 score ± scaled net_delta from the verifier's parsed reasoning trace

### Research Question

> Does integrating a reasoning model's chain-of-thought trace (Stage 3b) as a post-hoc score adjustment improve grading accuracy beyond the 5-stage KG pipeline alone?

---

## 2. Datasets

| Dataset | Domain | N answers | Score range | Source |
|---------|--------|-----------|-------------|--------|
| **Mohler** | Computer Science (Data Structures) | 120 | 0–5 | Mohler et al. 2011 |
| **DigiKlausur** | Neural Networks / Deep Learning | 300 (sampled) | 0–5 | In-house university exam data |

---

## 3. LRM Verifier Details

- **Primary model:** DeepSeek-R1 (`deepseek-reasoner`) via API — 119/120 Mohler, 295/300 DigiKlausur
- **Fill-in model:** Gemini 2.5 Flash with thinking (`include_thoughts=True, thinking_budget=8192`) — remaining samples
- **Prompt:** Domain + question + student answer + matched KG concepts + missing concepts + chain coverage %
- **Output:** `valid` (bool) + `reasoning` (1 sentence) + full chain-of-thought trace
- **Trace parsing:** Each sentence of reasoning → classified as SUPPORTS / CONTRADICTS / UNCERTAIN + `confidence_delta` (±0.05 to ±0.15)
- **net_delta:** Sum of all step confidence_deltas per answer
- **Score adjustment:** `lrm_adjusted = clip(c5_score + scale × net_delta, 0, 5)`

---

## 4. Ablation Results

### 4.1 Mohler Dataset (n=120, CS domain)

| Metric | C_LLM | C5 | LRM raw (scale=1.0) | LRM calibrated |
|--------|-------|----|---------------------|----------------|
| **MAE** | 2.2500 | 2.2500 | **2.0717** | **2.0717** |
| vs C_LLM | — | 0.0% | — | — |
| vs C5 | — | — | **+7.9%** | **+7.9%** |
| Optimal scale | — | — | 1.0 | 1.0 |

**Mohler LRM trace statistics:**
- Valid verdicts: 87/120 (72.5%)
- Avg reasoning steps: 19.9 per answer
- Step classification: SUPPORTS 38%, CONTRADICTS 37%, UNCERTAIN 25%
- Avg net_delta: −0.340 (range: −2.10 to +1.20)

**Finding:** C5 does not improve over C_LLM on Mohler, but LRM adjustment gives +7.9% MAE reduction.  
The verifier's reasoning trace carries useful signal that the KG pipeline alone misses.

### 4.2 DigiKlausur Dataset (n=300, Neural Networks domain)

| Metric | C_LLM | C5 | LRM raw (scale=1.0) | LRM calibrated |
|--------|-------|----|---------------------|----------------|
| **MAE** | 1.1867 | **1.0517** | 1.2617 | **1.0517** |
| vs C_LLM | — | **+11.4%** | — | — |
| vs C5 | — | — | −20.0% | 0.0% |
| Optimal scale | — | — | 1.0 → harmful | **0.0** |

**DigiKlausur LRM trace statistics:**
- Valid verdicts: 176/300 (58.7%)
- Avg reasoning steps: 19.6 per answer
- Step classification: SUPPORTS 34%, CONTRADICTS 38%, UNCERTAIN 28%
- Avg net_delta: −0.450 (range: −2.35 to +1.30)

**Finding:** C5 clearly beats C_LLM (+11.4%). However, the LRM score adjustment is harmful on DigiKlausur regardless of scale — the grid search optimum is scale=0.0, meaning C5 alone is best here. The negative bias (avg delta = −0.45) systematically pushes scores down, hurting accuracy.

### 4.3 Cross-Dataset Summary

| Dataset | C5 vs C_LLM | LRM-cal vs C5 | Best system |
|---------|-------------|---------------|-------------|
| Mohler | 0.0% | **+7.9%** | LRM-adjusted |
| DigiKlausur | **+11.4%** | 0.0% | C5 alone |

---

## 5. Key Analytical Questions for Review

### Q1 — Interpretation of LRM scale=0.0 on DigiKlausur
The calibration grid search finds optimal LRM scale = 0.0 for DigiKlausur, meaning any non-zero LRM adjustment worsens MAE. Three possible explanations:

**(a) Net_delta bias:** The verifier systematically assigns more CONTRADICTS than SUPPORTS for neural network answers (38% vs 34%). This negative bias makes the adjustment always push scores below the already-accurate C5 baseline.

**(b) Domain mismatch:** DeepSeek-R1 was trained on broad internet data; its internal model of "neural network concepts" may not match the specific course rubric used in DigiKlausur. The KG (built from the actual course) is better calibrated.

**(c) Score ceiling effect:** DigiKlausur C5 MAE is already 1.05 (tight). Adjustments that help on harder problems (Mohler MAE 2.25) may overshoot on an already-accurate baseline.

**Question:** Which explanation do you find most plausible? What additional analysis would differentiate them?

### Q2 — Mohler C5 = C_LLM (no KG improvement)
On Mohler, C5 MAE equals C_LLM MAE (both 2.25). The LRM trace adjustment is the only thing that helps. Possible causes:

- The Mohler KG may be under-populated (auto-generated, not expert-curated)
- The concept matching stage may be noisy for CS terminology  
- LLM baseline may already be strong for well-structured CS questions

**Question:** Is this a KG quality problem or a fundamental limitation of concept-chain grading for CS data structures? How would you test this?

### Q3 — LRM as verification vs. adjustment
Current use: LRM net_delta → post-hoc score adjustment.  
Alternative hypothesis: LRM `valid` flag (72.5% Mohler, 58.7% DigiKlausur) should be used as a **binary veto** (if `valid=False`, reduce score by fixed penalty) rather than a continuous delta.

**Question:** Would a binary validity gate outperform the continuous delta adjustment? What design would you recommend for a pedagogically defensible scoring rule?

### Q4 — Consistency across reasoning models
Mohler traces: 119/120 from DeepSeek-R1.  
DigiKlausur traces: 295/300 from DeepSeek-R1, 5 from Gemini 2.5 Flash thinking.

**Question:** How would you control for inter-model variance in the traces when reporting ablation results? Is it methodologically sound to mix models across 5 samples in a 300-sample dataset?

### Q5 — Statistical significance
Current analysis uses MAE point estimates only.  
With n=120 (Mohler) and n=300 (DigiKlausur), are the observed MAE differences (7.9% on Mohler) statistically meaningful?

**Question:** What non-parametric test would you recommend for comparing paired MAE distributions? Is Wilcoxon signed-rank on per-sample absolute errors appropriate here?

---

## 6. Proposed Next Steps

1. **Binary validity gate:** Implement and compare `valid=False → score × 0.85` against current delta adjustment
2. **Separate-model ablation on DigiKlausur:** Re-run 30 samples with Gemini thinking only (already cached), compare to DeepSeek traces
3. **KG quality analysis:** Check Mohler KG node count per question; correlate with C5 improvement
4. **Wilcoxon signed-rank:** Add statistical test to `compute_ablation_mae` for per-sample error distributions
5. **User study:** Condition A (C5 scores + summary) vs Condition B (full dashboard with trace visualization) — infrastructure already built

---

## 7. System Architecture (for VIS Framing)

The IEEE VIS 2027 submission frames ConceptGrade as a **Visual Analytics system** for explainable AI grading, not an ML accuracy paper. Key VA contributions:

- **Linking & brushing:** Clicking a KG concept node highlights it across all 11 dashboard charts simultaneously
- **Verifier Reasoning Panel:** The parsed trace steps (SUPPORTS / CONTRADICTS / UNCERTAIN) are displayed inline with KG node references, letting instructors follow the model's reasoning  
- **Study conditions:** Condition A (summary card only) vs Condition B (full VA dashboard) for educator user study
- **SUS questionnaire:** Integrated post-task, gates on task completion

**Review question:** For VIS, the contribution must be the *visualization + interaction design*, not the ML accuracy. How would you frame the LRM trace visualization as a novel VA contribution distinct from existing explainable AI dashboards?

---

*Generated from:*  
- `data/mohler_lrm_traces.json` — 120 DeepSeek-R1 traces  
- `data/digiklausur_lrm_traces.json` — 300 mixed traces  
- `data/lrm_ablation_summary.json` — calibrated MAE summary
