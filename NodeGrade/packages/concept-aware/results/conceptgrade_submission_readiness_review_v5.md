# ConceptGrade — Submission Readiness Review v5

**Date:** 2026-04-14  
**Context:** IEEE VIS 2027 VAST — final pre-pilot review  
**Prior reviews:** v1 (ablation), v2 (empirical follow-up), v3 (rubric tracking), v4 (semantic alignment + Click-to-Add)  
**This review:** Critical pre-submission blocker cleared (Mohler per-sample data); full system status

---

## 1. What Was Fixed Since v4

### 1.1 Mohler Critical Blocker — CLEARED

**Problem:** `mohler_eval_results.json` had correct aggregate metrics but `results: []` (empty per-sample list). `load_mohler_samples()` was falling through to a placeholder path that returned `cllm_score=0.0, c5_score=0.0` for all 120 samples — an impossible baseline that would signal data fabrication to a reviewer.

**Root cause:** The aggregate metrics were computed in an earlier session and saved to the summary file, but the per-sample scores were never written back to `mohler_eval_results.json`.

**Fix:** Reconstructed the full per-sample results by cross-referencing:
- `ablation_checkpoint_gemini_flash_latest.json` — 120 `C_LLM` and `C5_fix` scores from the full pipeline run
- `ablation_intermediates_fixed.json` — matched_concepts, chain_pct, SOLO, Bloom metadata for each sample

**Verified:** `load_mohler_samples()` now loads via Path 1 (real scores). MAEs match the stored summary exactly.

---

## 2. Confirmed Paper Numbers (All Three Datasets)

All three datasets now have **120/646/473 per-sample results** with real `cllm_score` and `c5_score`. No placeholder zeros remain.

| Dataset | N | C_LLM MAE | C5 MAE | Reduction | Wilcoxon p | Significant? |
|---------|---|-----------|--------|-----------|------------|-------------|
| Mohler 2011 (CS) | 120 | 0.3300 | 0.2229 | **+32.4%** | 0.0026 | ✓ p < 0.01 |
| DigiKlausur (NN) | 646 | 1.1842 | 1.1262 | **+4.9%** | 0.0489 | ✓ p < 0.05 |
| Kaggle ASAG (Science) | 473 | 1.2082 | 1.1797 | **+2.4%** | 0.340 | ✗ n.s. |
| **Fisher combined** | **1,239** | | | | **0.0027** | ✓ p < 0.01 |

**Key narrative:** 2/3 datasets significant individually; Fisher combined p=0.0027 across all 1,239 answers. The non-significance on Kaggle ASAG is explained by domain boundary mismatch (science KG vs. CS/NN domains where ConceptGrade was tuned).

### Additional Metrics (Mohler — strongest dataset)

| Metric | C_LLM | C5_fix |
|--------|-------|--------|
| MAE | 0.3300 | **0.2229** |
| RMSE | 0.4667 | **0.3315** |
| QWK | 0.9561 | **0.9748** |
| Pearson r | 0.9709 | **0.9820** |

---

## 3. Full System Architecture Status

### 3.1 Backend Pipeline (Python)

| Component | Status |
|-----------|--------|
| Stage 1: KG generation (`generate_auto_kg_prompt.py`) | ✓ All 3 datasets |
| Stage 2: Concept matching (`concept_matching.py`) | ✓ Embedding cache |
| Stage 3a: LRM Verifier (`lrm_verifier.py`) | ✓ Gemini 2.5 Flash, thinking_budget=8192 |
| Stage 3b: Trace parser (`trace_parser.py`) | ✓ Structured step output |
| Stage 4: C5 scoring | ✓ Per-sample results for all datasets |
| Multi-dataset ablation (`run_lrm_ablation.py`) | ✓ 3 conditions + Wilcoxon stats |
| Study log analyzer (`analyze_study_logs.py`) | ✓ Multi-window + semantic + hypergeometric |

### 3.2 Backend API (NestJS)

| Endpoint | Status |
|----------|--------|
| `GET /api/visualization/datasets` | ✓ Returns all 3 datasets |
| `GET /api/visualization/datasets/:dataset` | ✓ Returns 7 VisualizationSpecs |
| `GET /api/sample/:id/xai` | ✓ Returns trace + matched concepts |
| `POST /api/study/log` | ✗ **Not yet built** — localStorage fallback active |
| `GET /api/study/health` | ✓ Health probe for facilitator |

### 3.3 Frontend Dashboard (React)

| Feature | Status |
|---------|--------|
| 11 linked charts with bidirectional brushing | ✓ |
| Heatmap → StudentAnswerPanel → ConceptKGPanel | ✓ |
| LRM trace panel (VerifierReasoningPanel) | ✓ |
| CONTRADICTS step → KG node highlight | ✓ |
| Radar quartile → answer panel filter | ✓ |
| DashboardContext rolling 60-second window | ✓ |
| RubricEditorPanel (Cond A blank, Cond B with trace) | ✓ |
| Click-to-Add chips with pulse animation | ✓ |
| SUSQuestionnaire | ✓ |
| Study log export (localStorage) | ✓ |
| conceptAliases.ts (fuzzy + alias matching) | ✓ |

### 3.4 Study Log Analysis

| Metric | Status |
|--------|--------|
| Multi-window attribution (15s/30s/60s) | ✓ |
| Exact concept alignment rate | ✓ |
| Semantic concept alignment rate [PRIMARY] | ✓ |
| Hypergeometric p-value (per session) | ✓ |
| Panel-before-trace ordering | ✓ |
| Click-to-Add vs manual interaction source | ✓ |
| CSV export | ✓ |

---

## 4. Remaining Items Before Submission

### Critical
| Item | Blocker for | Notes |
|------|------------|-------|
| `POST /api/study/log` backend endpoint | IRB-grade data durability | localStorage alone = risk if browser closes |
| 2–3 person pilot study | UX validation | Key question: do educators click the CONTRADICTS chips? |
| Cued Retrospective Think-Aloud interviews | Qualitative triangulation | Need quotes for the VIS narrative |
| IRB protocol update | Ethics | Condition A now gets blank rubric panel (new) |

### Important (Pre-Final Study)
| Item | Notes |
|------|-------|
| CONTRADICTS chip discoverability measurement | Watch click rate in pilot; add affordance if needed |
| Full Mohler LRM ablation (with Gemini Flash) | Per-sample LRM traces for the co-auditing XAI display |
| SUS analysis baseline | Need 10+ participants per condition for power |

---

## 5. Paper Outline — "Topological Reasoning Mapping" (IEEE VIS 2027 VAST)

Proposed structure for feedback:

### Abstract (target)
> ConceptGrade is a visual analytics system that bridges the epistemic gap between LLM grading rationale and structured domain knowledge. We introduce **Topological Reasoning Mapping**: a technique that projects a large reasoning model's chain-of-thought onto a Knowledge Graph topology, enabling educators to co-audit both machine reasoning and student knowledge gaps. A user study (N=X, two conditions) demonstrates that educators exposed to the reasoning trace make rubric edits with a semantic alignment rate of Y% (hypergeometric p<0.05), compared to a null baseline of Z%.

### Sections
1. **Introduction** — educational grading as a testbed for HCAI; gap between LLM opaqueness and educator accountability
2. **Related Work** — XAI for NLP, educational analytics, VA systems for sensemaking
3. **System Design** — 5-stage pipeline; Topological Reasoning Mapping; co-auditing interaction model
4. **Implementation** — 3-tier architecture; bidirectional brushing; DashboardContext rolling window
5. **Evaluation** — (a) Accuracy: 32.4% MAE reduction on Mohler, Fisher p=0.0027; (b) User study: causal attribution rate, semantic alignment rate, SUS
6. **Discussion** — domain boundary mismatch as KG quality signal; panel-before-trace reasoning strategy; limitations
7. **Conclusion** — generalizability of Topological Reasoning Mapping beyond grading

---

## 6. Questions for This Review

### Q1 — The Non-Significant Kaggle ASAG Dataset
The paper will show 2/3 datasets significant. Kaggle ASAG (p=0.340) is included in the Fisher combined p but fails individually. 

**How should we handle this in the paper?** Options:
- (a) Report all 3 datasets honestly; explain n.s. via domain boundary mismatch (defensible)
- (b) Frame Kaggle ASAG as a "transfer to unseen domain" test; n.s. is expected without domain-specific KG tuning
- (c) Drop Kaggle ASAG from the main accuracy claim; include in supplementary as a generalizability discussion

Which framing would reviewers find most credible?

### Q2 — Effect Size Adequacy for the User Study Claim
With N=10–15 per condition and the following hypothetical results:
- Semantic alignment rate: 60% (Condition B) vs 25% null baseline (hypergeometric)
- Causal attribution rate @ 30s: 50% (Condition B) vs 0% (Condition A)

Is this effect size large enough for a VAST submission, or do reviewers expect larger N? With N=10, we get ~30 rubric edits. If 60% are semantically aligned vs. null of 25%, Cohen's h ≈ 0.77 — a large effect. Does VAST typically accept large-effect small-N user studies?

### Q3 — The "Co-Auditing" Framing vs. "Assistive Grading"
Gemini's prior reviews suggested pivoting from "automated grading tool" to "co-auditing interface." The paper's central claim would be:

> *"The system enables educators and AI to mutually refine rubrics and reasoning through visual inspection — not just verify outputs, but influence each other's mental models."*

**Is this framing novel enough for VIS 2027?** Is there prior VAST work on human-AI co-auditing that we need to distinguish from? What is the closest prior work that reviewers will cite?

### Q4 — Topological Reasoning Mapping — Definition Sharpness
The term "Topological Reasoning Mapping" needs a formal definition to anchor the contribution claim:

> *"TRM maps each step si in a linear reasoning chain R = {s1, ..., sn} to a set of nodes Ni ⊆ G in a domain KG G = (V, E), where each mapping is classified as SUPPORTS, CONTRADICTS, or UNCERTAIN based on the alignment between si's propositional content and the structural neighborhood of Ni."*

**Is this definition sufficient?** What formal properties would VAST reviewers expect to be proven or demonstrated empirically?

### Q5 — Submission Timeline Feasibility
Target: IEEE VIS 2027 (submission ~March 2027, ~11 months away).

Current critical path:
- Pilot study (April 2026)
- Full study with 20–30 participants (May–June 2026)  
- Analysis + paper writing (July–September 2026)
- Internal review + revisions (October–December 2026)
- Submission (March 2027)

**Is this timeline realistic for a VAST submission?** What is the single highest-risk item on this critical path?
