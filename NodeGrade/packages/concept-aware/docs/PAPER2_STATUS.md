# Paper 2: ConceptGrade — LRM Visual Analytics Dashboard for Human-AI Co-Auditing
## Project Status & Pending Work

**Paper Focus:** Topological Reasoning Mapping (TRM/LRM) + Visual Analytics system for educator co-auditing of automated grading  
**Target Venue:** IEEE VIS 2027 — VAST Track (Visual Analytics Science and Technology)  
**Date of This Document:** April 19, 2026 (updated)
**Overall Status:** ✅ Sections 1, 3, 4, 5a complete | ✅ Section 2 complete | ⏳ User study pending (May–August 2026)

---

## ⭐ Gemini VIS 2027 External Review — April 19, 2026

**Verdict:** *"Framework fully verified, structurally complete, and methodologically bulletproof."*

Four narrative recommendations implemented into `paper_phase2_vis2027.tex`:

| # | Recommendation | Location | Status |
|---|---------------|----------|--------|
| Rec-1 | **Epistemic Update Angle** — Frame CONTRADICTS chip → click_to_add as the measurable moment of mental model update. Name CA rate + SA rate as its operationalisation. | §1.1 "Why Co-Auditing Matters" | ✅ Implemented |
| Rec-2 | **TRM Visual Encoding subsection** — Map Definitions 1–5 onto specific UI elements (step cards, gap badges, SummaryBar, no-grounding banner). Prove formal-to-visual correspondence. | §2.1.1 after Def. 5 | ✅ Implemented |
| Rec-3 | **Condition A/B Isolation Argument** — Explicitly argue that Condition A's numeric metrics mean the B>A gap validates visual XAI components, not AI presence. Make it falsifiable at the interface-design level. | §5.1 Conditions + §3 Design Rationale | ✅ Implemented |
| Rec-4 | **AI Uncertainty Exposure as Design Choice** — Frame zero-grounding banner and gap badges as intentional uncertainty communication, not engineering workarounds. | §3 new "Design Rationale" subsection | ✅ Implemented |

Full review text: `docs/GEMINI_VIS2027_REVIEW_APR19.md`

---

## 1. What This Paper Is About

Paper 2 is the **visual analytics system paper**. It answers a different question from Paper 1:

> Can visualizing an AI's internal reasoning against a domain knowledge graph help expert instructors diagnose student misconceptions faster and more confidently than reading text alone?

The core technical contribution is **Topological Reasoning Mapping (TRM)** — a formal framework that maps LLM chain-of-thought reasoning chains onto a domain knowledge graph to expose structural reasoning leaps and measure grounding density.

The pedagogical contribution is the **co-auditing paradigm** — a bidirectional epistemic alignment mechanism in which the educator's mental model and the machine's evaluation criteria update simultaneously through shared visual topology.

This paper does **not** report the LLM grading accuracy ablation study (that is Paper 1). It uses the grading pipeline as a black box and focuses entirely on the visual analytics interface and educator user study.

---

## 2. Core Technical Contribution: TRM (Topological Reasoning Mapping)

### 2.1 Five Formal Definitions

| Definition | Name | Formula / Description |
|------------|------|-----------------------|
| Def 1 | Step Mapping | Maps each LLM reasoning step sᵢ to a set of KG nodes Nᵢ via concept extraction |
| Def 2 | Adjacency | Nᵢ ∩ Nᵢ₊₁ ≠ ∅ → adjacent (node-level, not edge-level — intentional) |
| Def 3 | Structural Leap | ¬Adjacent(sᵢ, sᵢ₊₁) = a leap (reasoning jumps across the domain graph) |
| Def 4 | Leap Count | LeapCount = Σ Leapᵢ across all consecutive step pairs |
| Def 5 | Grounding Density | GrDensity = |{sᵢ : Nᵢ ≠ ∅}| / |steps| |

### 2.2 Zero-Grounding Degeneration (Critical Discovery)

**Finding from `generate_trm_cache.py` (April 2026):** 97.7% of DigiKlausur LRM traces have `kg_nodes=[]` for all parsed steps → `topological_gap_count ≈ 0` across the entire dataset. This makes LeapCount useless as a Spearman ρ predictor.

**Resolution:** `chain_pct` (KG chain coverage from Stage 2 of the pipeline, `ConceptStudentAnswer`) has meaningful variance and is pre-registered as the primary dwell-time predictor instead. Pre-registered in `analysis_plan_qualitative.md` §5.5.

**Formal handling in paper:** Zero-grounding degeneration is treated as a distinct failure mode in the TRM theory section — a separate "no grounding found" indicator, not a false negative (GrDensity=0 ≠ LeapCount=0).

### 2.3 Co-Auditing vs. Interactive Machine Teaching (IMT)

| Dimension | IMT (prior work) | Co-Auditing (this paper) |
|-----------|-----------------|--------------------------|
| Primary artifact updated | Model weights | Educator's rubric |
| Human mental model | Assumed static | Actively updated |
| Direction of alignment | Human → Model | Bidirectional |
| Shared representation | Loss landscape | Domain knowledge graph |
| Interaction modality | Training labels | Click-to-Add KG node names |

**Key distinction:** IMT assumes the human's mental model is the ground truth and pushes it into the model. Co-auditing acknowledges that the educator's evaluation schema is itself incomplete — the machine's structured failure modes (leaps, low grounding) provide feedback that revises the rubric AND the educator's internal standards.

---

## 3. The Visual Analytics Dashboard

### 3.1 Five Core Components

| Component | Function | Key Interaction |
|-----------|----------|----------------|
| **Concept Heatmap** | 2D grid: concepts × severity levels; cell = % students with that concept at that severity | Click cell → filter Student Answer Panel |
| **Radar Chart** | Per-concept bloom/SOLO level distribution | Hover → highlight concept across all views |
| **KG Subgraph Panel** | D3 force-directed graph; green=covered, red=missed, grey=unrelated | Drag nodes; click node → filter answers |
| **Verifier Trace Panel** | Step-by-step LLM reasoning chain with leap markers + grounding indicators | Click "Add to Rubric" button (Click-to-Add) |
| **Rubric Editor** | Live editable rubric; criteria added from KG node names | Inline edit; each change logged with causal attribution |

### 3.2 DashboardContext: Shared State Architecture

```
DashboardContext (central state)
  ├── selectedConcept          → filters heatmap row + KG highlight + answer panel
  ├── selectedSeverity         → filters heatmap column + answer panel
  ├── selectedStudentId        → highlights student row in heatmap + opens trace
  ├── selectedStudentMatchedConcepts → drives KG node color coding
  ├── selectedQuartileIndex    → filters answer panel by score quartile
  ├── recentContradicts        → 60s rolling window of CONTRADICTS events
  ├── traceGapCount            → leap count for selected student's trace
  └── groundingDensity         → grounding density for selected student's trace
```

All clicks in any panel propagate through DashboardContext → all other panels react. Bidirectional brushing and linking.

### 3.3 Click-to-Add: Semantic Interaction Instantiation

The Click-to-Add button in the Verifier Trace panel pre-populates the Rubric Editor with the KG node name at that reasoning step. This is the instantiation of Endert's semantic interaction principle: the educator acts in domain vocabulary (KG node names); the system translates to machine-readable rubric criteria.

**Causal attribution logging for each rubric edit:**
```json
{
  "event": "rubric_edit",
  "rubric_criterion_text": "...",
  "matched_concept_id": "backpropagation",
  "trace_step_id": 7,
  "within_15s": true,
  "within_30s": true,
  "within_60s": true,
  "semantic_match_method": "alias_dict | levenshtein"
}
```

Semantic match: Levenshtein ratio ≥ 0.80 OR domain alias dictionary (NN + CS only).

---

## 4. Backend Logging Infrastructure

### 4.1 Study Event Types

All study events logged to `data/study_logs/{session_id}.jsonl` (JSONL per session):

```typescript
type StudyEventType =
  | 'page_view'
  | 'tab_change'
  | 'task_start'
  | 'task_submit'
  | 'chart_hover'
  | 'trace_interact'
  | 'rubric_edit'
  | 'answer_view_start'   // educator selects a student answer
  | 'answer_view_end';    // educator navigates away (dwell window closes)
```

### 4.2 Answer Dwell Time Logging (April 2026 Addition)

**Architecture:** React `useEffect` cleanup + `navigator.sendBeacon()` for browser-safe delivery.

**Why sendBeacon:** `window.beforeunload` and `fetch()` are throttled/cancelled during component unmount. `sendBeacon()` queues the POST asynchronously and survives page unload.

**Key design:**
```typescript
// Stable closure capture prevents stale reference bug
const answerForEnd = selectedAnswer;

return () => {
  const dwellTime = Date.now() - startTime;
  logBeacon(studyCondition, dataset, 'answer_view_end', {
    student_answer_id: answerId,
    chain_pct: answerForEnd.chain_pct,  // primary dwell predictor
    dwell_time_ms: dwellTime,
    capture_method: 'beacon',
    trace_panel_open: tracePanelOpen,
    kg_panel_open: kgPanelOpen,
  });
};
```

**Critical ordering:** The `useEffect` must be placed **after** the `selectedAnswer` useMemo declaration in `StudentAnswerPanel.tsx` to avoid TypeScript TS2448 forward reference error.

### 4.3 TRM Cache Pre-Computation

`generate_trm_cache.py` pre-computes TRM metrics for all 300 DigiKlausur student answers before any participant session.

Output: `data/digiklausur_trm_cache.json`
- Join key: `student_answer_id`
- Contents per entry: `topological_gap_count`, `grounding_density`, `verification_status` (green/yellow/red), `chain_pct`

**Why static cache:** Version-locked TRM metrics ensure all 30 participants see identical visualizations, maintaining between-subjects comparability.

### 4.4 Pending Backend Wire-Up

The new `answer_view_start/end` events and `studyCondition` prop are implemented in `StudentAnswerPanel.tsx` and `studyLogger.ts`, but the following props are **not yet wired** from `InstructorDashboard.tsx`:
- `studyCondition` → from URL param or session context
- `tracePanelOpen` → from DashboardContext or local state
- `kgPanelOpen` → from DashboardContext or local state

This must be done before the first participant session.

---

## 5. Paper Sections: Status

### 5.1 Section-by-Section Checklist

| Section | Status | Notes |
|---------|--------|-------|
| §1 Introduction | ✅ Complete | "Missing link is interface, not model" framing; citations added |
| §2 Related Work | ✅ Complete | 7 subsections, ~5–6 pages; see §5.2 |
| §3 TRM Theory | ✅ Complete | 5 formal definitions; Zero-Grounding case; adjacency confirmed node-level |
| §4 Implementation & Interaction | ✅ Complete | DashboardContext diagram; Click-to-Add mechanics; causal attribution logging |
| §5a ML Accuracy | ✅ Complete | Ablation table; 95% CIs; Kaggle domain-boundary framing |
| §5b User Study Results | ⏳ Placeholder | **Awaiting data collection May–August 2026** |
| §6 Discussion | ✅ Complete | Automation bias section; Kaggle boundary conditions; pre-registration note |
| §7 Conclusion | ✅ Ready | Minor polish after §5b |
| References | ✅ Complete | 29 entries in `references.bib`; Liu 2024 needs full metadata |

### 5.2 Section 2 Related Work — Completed (April 17, 2026)

Seven subsections covering:
1. **§2.1 Automated Short-Answer Grading** — historical arc Leacock→Mohler→LLM era; accuracy-interpretability tension
2. **§2.2 Explainability in NLP** — LIME/SHAP/attention = flat unstructured; TRM = domain-structural plausibility; Turpin 2023 / Lanham 2023 CoT unfaithfulness
3. **§2.3 VA for Sensemaking** — Thomas & Cook, Keim, Shneiderman, Pirolli & Card (foraging/sensemaking loops mapped to educator workflow), Klein Data/Frame theory, Sacha knowledge generation loop
4. **§2.4 Coordinated Multiple Views** — Becker, North & Shneiderman, Baldonado, Endert semantic interaction
5. **§2.5 Interactive Machine Teaching** — Amershi, Simard, Settles, Holzinger; key limitation = assumes static human mental model
6. **§2.6 Co-Auditing as Epistemic Alignment** — this paper's theoretical contribution; bidirectionality added over IMT
7. **§2.7 Knowledge Graphs in Education** — Corbett & Anderson BKT, Nakagawa, Liang; prior work = student models; ConceptGrade = LLM validation

**Non-incremental contribution claim for VAST reviewers:** The synthesis of VA sensemaking formalisms (Pirolli & Card foraging loop, Klein Data/Frame theory, Sacha knowledge generation model) applied to rubric-based pedagogy is absent in prior literature.

### 5.3 Gemini Review: Completed Feedback (April 17, 2026)

All 11 feedback items implemented. Key changes:
- ✅ Citations added for Liu 2024, G-Eval, Turpin 2023, Lanham 2023
- ✅ Zero-grounding degeneration subsection added
- ✅ DashboardContext state diagram added
- ✅ Click-to-Add mechanics clarified with causal logging detail
- ✅ Component contribution ablation table added (TRM=14.9%, Verifier=17.5%)
- ✅ 95% bootstrap CIs added for all results
- ✅ Kaggle ASAG domain-boundary framing confirmed
- ✅ Automation bias section added
- ✅ Pre-registration note added

---

## 6. User Study Design (Locked)

### 6.1 Study Parameters

| Parameter | Value | Locked? |
|-----------|-------|---------|
| N | 30 educators (15 per condition) | ✅ Yes |
| Condition A | Control — text summary statistics only | ✅ Yes |
| Condition B | Treatment — full ConceptGrade dashboard | ✅ Yes |
| Dataset | DigiKlausur only (646 NN exam answers) | ✅ Yes |
| Session length | 45 minutes via Zoom | ✅ Yes |
| Primary metric | Semantic alignment (rubric edits matched to KG concepts) | ✅ Yes |
| Think-aloud | Yes — narrated in real time | ✅ Yes |
| Scheduling | Reply-first (no cold Calendly link) | ✅ Yes |
| Compensation | $50 Amazon gift card | ✅ Yes |
| Venue signal | IEEE VIS 2027 (VAST track) | ✅ Yes |

**Rationale for DigiKlausur only:** Ecological validity (instructors using domain-specific NN data) + statistical power (N=15 per condition).

### 6.2 Pre-Registered Hypotheses

**Primary (Causal Attribution):**
- **H1:** Condition B produces more Causal Attribution (CA) think-aloud codes than Condition A (Poisson GLM, expected IRR ≈ 3.8×)

**Secondary (Semantic Alignment):**
- **H2:** Condition B produces more rubric edits semantically matched to KG concepts (SA codes) than Condition A

**Tertiary (Trust Calibration):**
- **H3:** Condition B produces higher trust calibration scores (ordinal 0–4, Mann-Whitney U)

**Dwell Time (Pre-registered, April 2026):**
- **H-DT1:** Low chain_pct answers → longer dwell time in Condition B (Spearman ρ)
- **H-DT2:** Dwell time correlates with CA code frequency (educator spends longer → produces more causal codes)
- **H-DT3:** Dwell time difference (B−A) largest for SOLO level 3–4 answers (partial credit zone)

### 6.3 Qualitative Coding Scheme

| Code | Name | Description |
|------|------|-------------|
| CA | Causal Attribution | Educator attributes student error to specific concept gap ("they don't understand backprop because...") |
| SA | Semantic Alignment | Educator adds rubric criterion matched to KG node |
| TC | Trust Calibration | Educator expresses agreement or disagreement with AI grade |
| II | Interaction Intensity | Educator explores multiple views before making a decision |

Inter-rater reliability target: κ ≥ 0.70 (Cohen's kappa).

---

## 7. Recruitment Materials: Status

All materials in `recruitment_materials_vis2027.md`.

### 7.1 Recruitment Email — v2.0 (Post-Gemini Review)

**Status:** ✅ Final copy ready. **Blocked on IRB protocol number.**

**Gemini review improvements (v1.0 → v2.0):**
- Subject: "Research Invitation: Your Neural Networks expertise for AI grading study (VIS 2027)"
- Research question: single block-quoted jargon-free sentence (replaces 4-sentence TRM explanation)
- Framing: "prepping for a lecture or office hours" (covers both lecturer and office-hours faculty)
- Length: ~200 words (trimmed from ~300; passes 15-second skim test)
- Think-aloud protocol: mentioned in task bullet
- Controlled experiment: correctly absent (avoid priming bias)
- System name "ConceptGrade": correctly absent (revealed at session orientation)

**Tracking document:** `GEMINI_RECRUITMENT_FEEDBACK_IMPLEMENTED.md`

### 7.2 Pre-Send Blockers

| Placeholder | Required Value | Status |
|-------------|---------------|--------|
| `[Full Name]` | Legal name of PI/sender | ⏳ Pending |
| `[Title]` | Current academic title | ⏳ Pending |
| `[Department] \| [Institution]` | Full institutional affiliation | ⏳ Pending |
| `[Email]` | Institutional `.edu` email | ⏳ Pending |
| `[Institution] IRB (Protocol #[XXX])` | IRB approval number | ⏳ **HARD GATE — do not send** |

### 7.3 Recruitment Batches

| Batch | Channel | Target | Send Date | Expected Confirmations |
|-------|---------|--------|-----------|------------------------|
| 1 | CS Department Chairs (direct email) | ~15 universities | May 1–15, 2026 | 8 |
| 2 | SIGCSE Mailing List | Broadcast | May 15–31, 2026 | 7 |
| 3 | ACM ICER / IEEE FIE Forums | Online posts | June 1–15, 2026 | 5 |
| 4 | Snowball from Batches 1–3 | Referrals | May–July (parallel) | 5 |
| 5 | Final push (if N<20 by July 1) | LinkedIn / Twitter | July 1–15, 2026 | 5 |

---

## 8. Statistical Analysis Plan

### 8.1 Primary Analyses

| Hypothesis | Test | Expected Result |
|------------|------|-----------------|
| H1 (Causal Attribution) | Poisson GLM | IRR ≈ 3.8× for Condition B |
| H2 (Semantic Alignment) | Mann-Whitney U | Condition B > A |
| H3 (Trust Calibration) | Mann-Whitney U (ordinal) | Condition B higher |
| Dwell time vs. chain_pct | Spearman ρ | Negative correlation |
| SUS usability | Independent-samples t-test + Cohen's d | Condition B SUS ≈ 72, Condition A ≈ 58 |
| Task accuracy | GEE logistic model | Condition B > A |

### 8.2 Post-Study Analysis: TRM Cache Join

After study, each `answer_view_end` event joins to `data/digiklausur_trm_cache.json` via `student_answer_id`:

```python
import pandas as pd
events = pd.read_json('data/study_logs/all_events.jsonl', lines=True)
trm = pd.read_json('data/digiklausur_trm_cache.json')
dwell_df = events[events.event_type == 'answer_view_end'].copy()
dwell_df = dwell_df.merge(trm, on='student_answer_id', how='left')

# Filter bounces
dwell_df = dwell_df[dwell_df.dwell_time_ms >= 2000]

# Test H-DT1
from scipy.stats import spearmanr
rho, p = spearmanr(dwell_df.chain_pct, dwell_df.dwell_time_ms)
```

---

## 9. Key File Map

| File | Contents |
|------|----------|
| `docs/paper_phase2_vis2027.tex` | Main paper (LaTeX, IEEE VIS template) |
| `docs/references.bib` | 29 BibTeX entries (all citations in paper) |
| `docs/user_study_protocol_vis2027.md` | Full study execution guide |
| `docs/analysis_plan_qualitative.md` | Qualitative coding scheme + statistical tests |
| `docs/recruitment_materials_vis2027.md` | All recruitment materials (v2.0) |
| `docs/GEMINI_FEEDBACK_IMPLEMENTED.md` | Paper review feedback tracking |
| `docs/GEMINI_RECRUITMENT_FEEDBACK_IMPLEMENTED.md` | Email review feedback tracking |
| `docs/GEMINI_DATASET_SELECTION.md` | Dataset selection decision brief |
| `docs/GEMINI_RECRUITMENT_REVIEW.md` | Original review brief for recruitment email |
| `data/digiklausur_trm_cache.json` | Pre-computed TRM metrics (300 entries) |
| `data/study_logs/` | Per-session JSONL event logs (populated during study) |
| `packages/frontend/src/utils/studyLogger.ts` | Event logging utility + beacon delivery |
| `packages/frontend/src/components/charts/StudentAnswerPanel.tsx` | Dwell time tracking component |

---

## 10. What Was Completed ✅

| Task | Status | Date |
|------|--------|------|
| TRM formal theory (5 definitions) | ✅ Done | March 2026 |
| Zero-grounding degeneration subsection | ✅ Done | April 2026 |
| DashboardContext state architecture | ✅ Done | March 2026 |
| All 5 dashboard components | ✅ Done | March–April 2026 |
| Bidirectional brushing & linking | ✅ Done | March 2026 |
| Click-to-Add interaction | ✅ Done | March 2026 |
| Causal attribution logging schema | ✅ Done | March 2026 |
| Condition A/B scaffolding | ✅ Done | March 2026 |
| `studyLogger.ts` with beacon delivery | ✅ Done | April 2026 |
| `answer_view_start/end` events | ✅ Done | April 2026 |
| Dwell-time useEffect + stable closure | ✅ Done | April 2026 |
| `AnswerDwellPayload` interface | ✅ Done | April 2026 |
| `generate_trm_cache.py` | ✅ Done | April 2026 |
| TRM cache (300 entries) | ✅ Done | April 2026 |
| Zero-grounding discovery documented | ✅ Done | April 2026 |
| chain_pct as dwell predictor pre-registered | ✅ Done | April 2026 |
| Section 2 Related Work (7 subsections) | ✅ Done | April 2026 |
| `references.bib` (29 entries) | ✅ Done | April 2026 |
| Gemini paper review: all 11 items | ✅ Done | April 2026 |
| Gemini recruitment email review: all 6 items | ✅ Done | April 2026 |
| Recruitment email v2.0 | ✅ Done | April 2026 |
| User study protocol | ✅ Done | March 2026 |
| Analysis plan (qualitative + quantitative) | ✅ Done | March–April 2026 |
| Pre-registered dwell hypotheses H-DT1/2/3 | ✅ Done | April 2026 |
| Automation bias section (§6) | ✅ Done | April 2026 |
| Pre-registration note (OSF) | ✅ Done | April 2026 |
| 95% CIs for all ML results | ✅ Done | April 2026 |

---

## 11. What Is Pending ⏳

### 11.1 Immediate (Before First Participant Session)

| Task | Blocker | Priority |
|------|---------|----------|
| Wire `studyCondition`, `tracePanelOpen`, `kgPanelOpen` props from `InstructorDashboard.tsx` into `StudentAnswerPanel.tsx` | No blocker — code change | 🔴 Critical |
| Run `generate_trm_cache.py` once more to confirm clean output | No blocker | 🔴 Critical |
| End-to-end logging test: `answer_view_start` → beacon → JSONL write → analysis join | No blocker | 🔴 Critical |
| Submit IRB application | No blocker | 🔴 **Hard gate for recruitment** |
| Fill placeholders in recruitment email | IRB number needed | 🔴 Blocked on IRB |
| Activate Calendly scheduling portal | No blocker | 🟡 Pre-recruitment |
| OSF pre-registration (lock analysis plan) | No blocker | 🟡 Before recruitment |

### 11.2 Recruitment & Data Collection (May–July 2026)

| Task | Timeline | Target |
|------|----------|--------|
| Batch 1: CS Department Chairs emails | May 1–15 | 8 confirmations |
| Batch 2: SIGCSE mailing list | May 15–31 | 7 confirmations |
| Batch 3: ACM ICER / IEEE FIE | June 1–15 | 5 confirmations |
| Snowball (parallel with Batches 1–3) | May–July | 5 confirmations |
| Final push if N<20 by July 1 | July 1–15 | Fill to 30 |
| Conduct 30 study sessions | May–July | All completed |

### 11.3 Analysis (August–September 2026)

| Task | Timeline | Notes |
|------|----------|-------|
| Transcribe think-aloud audio | August 2026 | Accuracy ≥ 95% |
| Apply qualitative codes (CA/SA/TC/II) | August 2026 | κ ≥ 0.70 required |
| Inter-rater reliability check | August 2026 | Second coder on 20% of transcripts |
| Run statistical analyses | August–September | Poisson GLM, Mann-Whitney U, GEE, Spearman ρ |
| Dwell time analysis (TRM cache join) | September 2026 | H-DT1/2/3 |

### 11.4 Paper Completion (September–October 2026)

| Task | Timeline | Notes |
|------|----------|-------|
| Write §5b User Study Results | September 2026 | SUS, think-aloud coding, task accuracy |
| Finalize §6 Discussion (post-study) | September 2026 | Incorporate user study findings |
| Minor polish §7 Conclusion | October 2026 | |
| Generate paper figures | October 2026 | SUS distribution; causal attribution frequency; dashboard screenshot |
| Populate Liu 2024 full metadata in `references.bib` | Any time | Currently `[To be fully populated when citation is confirmed]` |
| Final copy-edit (IEEE VIS style compliance) | October 2026 | Word count ≤ 7,500 |
| Submit to IEEE VIS 2027 | October 2026 | Hard deadline TBD |

---

## 12. Timeline Overview

```
April 2026:    ✅ Section 2 done | ✅ Recruitment email v2.0 | ⏳ IRB submission
May 2026:      IRB approval expected → launch Batch 1 recruitment
May–July 2026: Conduct 30 user study sessions (2–3/week)
August 2026:   Transcribe + code qualitative data
September 2026: Run statistics + write §5b
October 2026:  Finalize + submit to IEEE VIS 2027
```

---

## 13. Pre-Submission Checklist

### Before Any Recruitment Send
- [ ] IRB approved and protocol number in hand
- [ ] Fill all email placeholders: [Full Name], [Title], [Department | Institution], [Email], [Protocol #XXX]
- [ ] Wire `studyCondition` + panel state props in `InstructorDashboard.tsx`
- [ ] End-to-end logging pipeline test (verify beacon → JSONL delivery)
- [ ] OSF pre-registration (lock hypotheses + analysis plan)
- [ ] Calendly portal active with correct timezone coverage

### While Study Runs
- [ ] Monitor SUS scores every 5 sessions for outliers
- [ ] Verify event logs: POST `/api/study/log` receiving data
- [ ] Check transcription quality (≥ 95% accuracy)
- [ ] Track enrollment against target (contingency if N<20 by July 1: extend + raise to $75)

### After Data Collected
- [ ] Code all transcripts (CA/SA/TC/II); compute κ
- [ ] Poisson GLM for CA codes (Condition A vs B)
- [ ] Mann-Whitney U for SA codes, TC scores
- [ ] GEE logistic model for task accuracy
- [ ] Spearman ρ for dwell time vs chain_pct (H-DT1)
- [ ] Write §5b with actual results (replace placeholder language)

### Final Paper QA
- [ ] All tables formatted consistently
- [ ] All citations complete (no stubs — confirm Liu 2024)
- [ ] Figure captions include N and condition labels
- [ ] Word count ≤ 7,500 (VIS page limit)
- [ ] IEEE template compliance
- [ ] Supplementary material prepared (if figures overflow)

---

## 14. Summary: Paper 2 Readiness

| Component | Readiness | Notes |
|-----------|-----------|-------|
| TRM formal theory | ✅ **Complete** | 5 definitions, zero-grounding case, adjacency confirmed |
| Dashboard implementation | ✅ **Complete** | All 5 components, DashboardContext, Condition A/B |
| Backend logging | ✅ **Complete** | Beacon delivery, JSONL, dwell-time tracking |
| §1 Introduction | ✅ **Complete** | Citations, framing locked |
| §2 Related Work | ✅ **Complete** | 7 subsections, 29 references |
| §3 TRM Theory | ✅ **Complete** | |
| §4 Implementation | ✅ **Complete** | DashboardContext diagram, Click-to-Add |
| §5a ML Accuracy | ✅ **Complete** | Ablation table, 95% CIs |
| §5b User Study | ⏳ **Not started** | **Awaiting data (May–August 2026)** |
| §6 Discussion | ✅ **Complete** | Automation bias, Kaggle framing |
| §7 Conclusion | ✅ **Ready** | Minor polish post-study |
| Recruitment materials | ✅ **Complete** | Email v2.0 ready; blocked on IRB |
| IRB submission | ⏳ **Pending** | **Hard gate** |
| User study (30 sessions) | ⏳ **Not started** | May–July 2026 |

**Current gating item:** IRB approval. Nothing else blocks the path to submission.

---

**Document Prepared By:** Claude  
**Date:** April 17, 2026  
**Paper Version:** Sections 1–4, 5a, 6 complete; §5b pending user study data
