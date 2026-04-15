# ConceptGrade — Project Status Document

**Date:** 2026-04-14  
**Venue Target:** IEEE VIS 2027 VAST (Visual Analytics Science and Technology)  
**Submission Deadline:** ~March 2027 (abstract ~February 2027)  
**Working Title:** *"ConceptGrade: A Visual Analytics System for Human-AI Co-Auditing of Knowledge Graph-Grounded Grading"*

---

## 1. What We Set Out to Build

### 1.1 The Problem

Automated short-answer grading (ASAG) systems have reached near-human accuracy on structured benchmarks. The real bottleneck is not performance — it is **accountability**. When a model downgrades a student's answer, the educator has no mechanism to inspect why. The system becomes an oracle to trust or ignore, not a collaborator to audit.

Existing XAI tools (LIME, SHAP, attention visualization) answer "what did the model look at?" — not "was the model's reasoning about the domain coherent?" The second question requires a structured domain representation.

### 1.2 The Core Idea

Build a system that:
1. Grounds LLM grading in a **domain Knowledge Graph (KG)** rather than relying on holistic language pattern matching.
2. Projects the LLM's **chain-of-thought reasoning** onto the KG topology, making gaps and jumps visible to educators.
3. Enables **co-auditing**: educators inspect AI reasoning, which forces them to surface and refine their own implicit mental models of the rubric — a bidirectional epistemic update.

### 1.3 Initial Plan (Papers)

Two publications planned:

| Paper | Venue | Focus |
|-------|-------|-------|
| Paper 1 | NLP/EdAI (ACL/EMNLP/LREC) | ML pipeline accuracy, KG-augmented grading vs LLM baseline, ablation |
| Paper 2 | IEEE VIS 2027 VAST | Visual analytics system design, TRM formalization, educator user study |

Both papers draw from the same underlying system. Paper 1 justifies that the pipeline is trustworthy; Paper 2 demonstrates that the visual interface makes it auditable.

---

## 2. How We Progressed

### Phase 1 — Five-Stage ML Pipeline (Completed)

Built a full grading pipeline in `packages/concept-aware/`:

```
Student Answer
     ↓
[Stage 1] KG Generation          generate_auto_kg_prompt.py
[Stage 2] Concept Matching        concept_matching.py
[Stage 3a] LRM Verifier           lrm_verifier.py  (Gemini Flash / DeepSeek-R1)
[Stage 3b] Trace Parser           trace_parser.py  → ParsedStep[]
[Stage 4]  C5 Scoring             c5_scorer.py
     ↓
Graded output + TRM trace
```

Three research extensions integrated:
- **C2** Self-Consistent Extractor — 3-run majority voting
- **C3** Confidence-Weighted Comparator — alpha=1.0 in production
- **C4** LLM-as-Verifier — the critical driver of accuracy gains

The Verifier (C4) is the most important ablation result: Δr=+0.092, RMSE −23%, p<0.0001 on n=30 LLM-mode ablation.

---

### Phase 2 — Ablation & Statistical Validation (Completed)

**Standard SAG Ablation (n=120, Mohler dataset, gemini-2.5-flash):**

| ID | System | r | MAE | QWK |
|----|--------|---|-----|-----|
| C0 | Cosine Baseline | 0.7319 | 1.7113 | 0.1854 |
| C_LLM | Pure LLM Zero-Shot | **0.9789** | **0.2250** | 0.9713 |
| C1 | CG Baseline | 0.8712 | 0.8076 | 0.7201 |
| C4 | CG + Verifier | 0.9631 | 0.3750 | 0.9469 |
| C5 | CG + All Ext | **0.9710** | 0.3167 | **0.9588** |

Key nuance: C5 r=0.9710 vs C_LLM r=0.9789 — 95% CIs overlap (Δr=0.008). ConceptGrade is **competitive** on standard SAG, not strictly better.

**Adversarial Benchmark (n=100):**
ConceptGrade wins 5/7 adversarial categories. +11.4% MAE reduction on the hardest inputs (hallucination, logic drift, structural split). This is the "CG beats LLM" claim.

**`C5_fix` Mohler Final (n=120):**

After KG edge fixes and targeted rescoring:
- MAE: **0.3300 → 0.2229** (−32.4%)
- Wilcoxon p = 0.0013
- 8/10 questions: C5_fix wins by point estimate
- 10/10 questions: non-inferior (one-sided Wilcoxon p_worse > 0.05 on all)

All LaTeX tables paper-ready in `data/paper_*.tex`.

---

### Phase 3 — Multi-Dataset Evaluation (Completed)

Extended evaluation to three datasets (1,239 total student answers):

| Dataset | n | C_LLM MAE | C5 MAE | Δ MAE | p-val | Sig? |
|---------|---|-----------|--------|-------|-------|------|
| Mohler 2011 (CS) | 120 | 0.3300 | 0.2229 | −32.4% | 0.0026 | ✓ |
| DigiKlausur (NN) | 646 | 1.1842 | 1.1262 | −4.9% | 0.049 | ✓ (marginal) |
| Kaggle ASAG (Sci) | 473 | 1.2082 | 1.1691 | −3.2% | 0.148 | ✗ directional |

- **Fisher combined p = 0.003** across all three (reported as exploratory)
- **Kaggle ASAG is not a failure** — it is a domain boundary condition: elementary science vocabulary lacks KG discriminability, so the KG provides no additional signal over holistic LLM scoring. This is documented and reported honestly as a finding, not hidden.

All results cached in `data/batch_responses/` and `data/*_eval_results.json`. No API calls needed to reproduce.

---

### Phase 4 — Visual Analytics Dashboard (Completed)

Built a full-stack React + NestJS dashboard (`packages/frontend/` + `packages/backend/`):

**14 implemented chart/panel components:**

| Component | Purpose |
|-----------|---------|
| `BloomsBarChart` | Bloom's taxonomy distribution per dataset |
| `SoloBarChart` | SOLO taxonomy distribution per dataset |
| `MisconceptionHeatmap` | Concept × question misconception matrix |
| `ConceptFrequencyChart` | Top-15 most cited KG concepts |
| `ScoreComparisonChart` | C_LLM vs C5 MAE by score bucket |
| `ChainCoverageChart` | KG chain coverage distribution |
| `StudentRadarChart` | Per-student multi-dimensional profile |
| `ScoreSamplesTable` | Raw per-sample score table |
| `CrossDatasetComparisonChart` | Side-by-side domain comparison |
| `ConceptKGPanel` | KG subgraph visualization (ego-graph per concept) |
| `StudentAnswerPanel` | Raw student answer text viewer |
| `VerifierReasoningPanel` | LRM trace viewer with TRM gap indicators |
| `RubricEditorPanel` | Educator rubric editing + Click-to-Add |
| `SUSQuestionnaire` | System Usability Scale (10 items) |

**DashboardContext** provides global state with bidirectional brushing:
- Selecting a concept in any panel highlights it across all linked views
- KG subgraph animates to show the selected concept's neighborhood
- CONTRADICTS steps in the trace panel push to the rolling attribution window

---

### Phase 5 — User Study Instrumentation (Completed, with recent fixes)

This is the most recently completed layer. It instruments the educator's interaction with the dashboard for the controlled study.

**Study Design:**
- 2 conditions: **Condition A** (blank rubric panel, no trace context) vs **Condition B** (full CONTRADICTS strip + LRM trace)
- N = 20 educators (CS + NN TAs/instructors who have actually graded student work)
- Primary hypothesis **H1**: causal attribution — do Condition B educators make rubric edits within 30 seconds of CONTRADICTS interactions?
- Primary hypothesis **H2**: semantic alignment — do Condition B rubric edits semantically match the KG concepts the LRM flagged?
- Moderator: `trace_gap_count` (number of structural leaps in the current trace)

**Implemented instrumentation:**

| Layer | File | What It Does |
|-------|------|-------------|
| State machine | `DashboardContext.tsx` | Manages `recentContradicts` rolling window, `lastTraceGapCount`, `lastGroundingDensity` |
| Gap detection | `VerifierReasoningPanel.tsx` | Node-only TRM adjacency; publishes gap count + density to context |
| Causal logger | `RubricEditorPanel.tsx` | Multi-window attribution (15/30/60 s) at edit time; Click-to-Add logging |
| Semantic match | `conceptAliases.ts` | 3-layer: exact → alias dict (CS + NN only) → Levenshtein ≥ 0.80 |
| Event schema | `studyLogger.ts` | Full `RubricEditPayload` with 17 fields; generic `logEvent<T>` |
| Analysis | `analyze_study_logs.py` | GEE Binomial/Logit + Exchangeable; H2 split by `interaction_source` |

**Key locked decisions (do not reopen):**
- Primary attribution window: **30 seconds**
- H2 primary metric: `semantic_alignment_rate_manual` (manual edits only; click_to_add reported separately)
- GEE model: `within_30s ~ condition * trace_gap_count | session_id`
- Grounding density: secondary metric (Stability Analysis §5a only; NOT in GEE — collinear with gap count)
- Node-only adjacency: two steps are topologically adjacent iff `Nᵢ ∩ Nᵢ₊₁ ≠ ∅`

---

### Phase 6 — Formal Theory & Paper Writing (In Progress)

The TRM formalization and Introduction have been drafted and reviewed through 12 rounds:

**Review Document Progression:**

| Doc | Focus | Key Decision |
|-----|-------|-------------|
| v1–v5 | Ablation, pipeline framing, contribution claims | Kaggle ASAG = boundary condition (not failure) |
| v6 | TRM gap indicators (first draft) | Rolling 60-s window, multi-window design |
| v7 | trace_gap_count wiring, GEE upgrade | GEE Binomial/Logit replaces mixedlm |
| v8 | Figure trace selection, IRB, recruitment | Sample 0 DigiKlausur selected as paper figure |
| v9 | Cross-model validation strategy | Fold into §5a Stability Analysis (no Section 5c) |
| v10 | Node-only adjacency, Structural Leap terminology | "Structural leap" not "hallucination"; node-only locked |
| v11 | §3.1 Formal Definition box + §3.2 Pedagogical Interpretation | cᵢ removed from Def 1; "implicit mental models" |
| v12 | Full §1 Introduction (~1,050 words) + 5 open questions | Writing order locked: §1 → §3 → §4 → §5a → §5b |
| Code Review v1 | 6-layer instrumentation audit + Gemini feedback | Synthetic ID bug fixed; logEvent made generic; H2 split |

**TRM Formal Definitions (v11, locked):**

- **Definition 1 (Step Mapping)**: φ(sᵢ) = Nᵢ — projection of step sᵢ to concept nodes. No cᵢ in the formal box.
- **Definition 2 (Topological Adjacency)**: Nᵢ ∩ Nᵢ₊₁ ≠ ∅ — steps share at least one KG node.
- **Definition 3 (Structural Leap)**: Both steps grounded (Nᵢ ≠ ∅, Nᵢ₊₁ ≠ ∅) and Nᵢ ∩ Nᵢ₊₁ = ∅.
- **Definition 4 (Leap Count)**: Integer count of structural leaps in a trace.
- **Definition 5 (Grounding Density)**: |{i : Nᵢ ≠ ∅}| / n ∈ [0,1].

cᵢ ∈ {SUPPORTS, CONTRADICTS, UNCERTAIN} is described in the prose after the box as an implementation artifact — not formally derived from G.

**Introduction Draft (v12) — 5 open Q1–Q5 answered by Gemini:**

| Q | Question | Decision |
|---|----------|----------|
| Q1 | CoT concession sentence? | Yes — add one sentence to para 2 acknowledging CoT can be domain-accurate; our claim is about topological visibility |
| Q2 | Cite Norman for "implicit mental models"? | No — cite Kulesza 2012 + Bansal 2019 (human-AI alignment literature) |
| Q3 | X/Y/Z placeholders in evaluation para? | Keep as [TODO] with power-analysis note for co-author draft |
| Q4 | "First approach" claim? | Narrow to "first visual analytics approach in the educational grading context" |
| Q5 | Introduction too long (~1,050 words)? | Cut to ~650 words: LIME/SHAP para → Related Work; strip p-values from preview para |

---

## 3. Where We Are Now

### 3.1 What Is Complete

**ML Pipeline:**
- [x] 5-stage pipeline fully implemented and validated
- [x] 3-extension ablation (C2 SC, C3 CW, C4 Verifier) with significance
- [x] 3-dataset evaluation (1,239 answers) with Fisher combined p = 0.003
- [x] Adversarial benchmark (5/7 wins, +11.4% MAE)
- [x] All LaTeX tables paper-ready in `data/paper_*.tex`
- [x] All results cached — no API calls needed

**Frontend Dashboard:**
- [x] 14 chart/panel components implemented
- [x] DashboardContext bidirectional brushing
- [x] KG subgraph visualization
- [x] LRM trace viewer (VerifierReasoningPanel) with TRM gap indicators
- [x] RubricEditorPanel with Click-to-Add (CONTRADICTS chips pulse 3×)
- [x] SUS Questionnaire
- [x] Condition A/B gating via URL param

**User Study Instrumentation:**
- [x] `studyLogger.ts` — generic `logEvent<T>`, full `RubricEditPayload` schema
- [x] `DashboardContext.tsx` — rolling window, gap count, grounding density state
- [x] `VerifierReasoningPanel.tsx` — node-only adjacency, structural leap indicators, grounding density
- [x] `RubricEditorPanel.tsx` — multi-window attribution, panelBeforeTrace, semantic matching
- [x] `conceptAliases.ts` — 3-layer semantic matching (CS + NN alias dict)
- [x] `analyze_study_logs.py` — GEE Binomial/Logit, H2 split by source, hypergeometric null

**Recent Bug Fixes (code review v1):**
- [x] Synthetic node ID bug: CONTRADICTS steps with `kg_nodes = []` no longer push `step_3` IDs to rolling window
- [x] `logEvent` is now generic `<T extends Record<string, unknown>>` — double-cast removed from RubricEditorPanel
- [x] `semantic_alignment_rate` split into `_manual` (H2 PRIMARY) and `_cta` (UI-assisted, reported separately)
- [x] `within_30s` flagging confirmed correct (single-loop inline assignment — no bug)
- [x] Layer 2 alias ordering confirmed logically sound — no change needed

**Paper Writing:**
- [x] §3.1 Formal Definition box (TRM, 5 definitions) — locked
- [x] §3.2 Pedagogical Interpretation draft
- [x] §1 Introduction v12 draft (~1,050 words) with 5 open questions resolved
- [x] 12 Gemini review rounds completed; all major decisions locked in memory

---

### 3.2 What Is Partially Done

| Item | State | Blocker |
|------|-------|---------|
| §1 Introduction v13 | 5 editorial decisions made; not yet applied to the text | Manual editing needed |
| DigiKlausur Gemini Flash ablation | Command documented; not run | Needs `GEMINI_API_KEY` env var |
| Sample 0 figure trace (Gemini Flash) | Selected in review; trace exists but CONTRADICTS kg_nodes may be empty | Needs ablation run above |
| `POST /api/study/log` NestJS endpoint | Planned; not built | Post-pilot (scheduled) |
| §4 System Architecture draft | Not started | Depends on pipeline figure (Option C: flowchart + annotated screenshot) |

---

### 3.3 Known Open Issues (Non-Critical)

| Priority | Issue | Location |
|----------|-------|----------|
| 🟡 | `panel_focus_ms` field name is a timestamp, not a duration | `studyLogger.ts` line 60 — rename to `panel_mount_timestamp_ms` before full study |
| 🟢 | Negative ρ fallback not specified | `analyze_study_logs.py` — add Independence working correlation fallback if ρ < 0 in real study |
| 🟢 | Hyphen not normalized to space in `normalizeConceptId` | `conceptAliases.ts` — works by accident (Levenshtein catches it); document as intentional |
| 🟢 | `aliasLookup` rebuilt on every call | `conceptAliases.ts` — acceptable at N=20; comment if ever used in render loop |

---

## 4. What Needs to Be Done

### 4.1 Immediate (Before Pilot Study)

**IRB Amendment (BLOCKER)**
- The Condition A blank panel change is a protocol deviation from the original IRB.
- File expedited amendment using the hybrid framing: "strengthens experimental control AND adds epistemic agency delta metric."
- Expected turnaround: 48–72 hours.
- **Do not run pilot until amendment is approved.**

**Introduction v13 (Writing)**
Apply the five Gemini v12 Q1–Q5 decisions to the Introduction draft:
1. Add CoT concession sentence to para 2
2. Replace Norman citation with Kulesza 2012 + Bansal 2019
3. Mark N/Y/Z as explicit [TODO: fill from pilot] placeholders
4. Narrow "first approach" to "first visual analytics approach in the educational grading context"
5. Cut ~350 words: move LIME/SHAP para to §2 Related Work; strip p-value details from para 5 (keep 32.4% MAE and p < 0.05 only); target 650 words

**DigiKlausur Gemini Flash Ablation (Figure Prerequisite)**
```bash
export GEMINI_API_KEY=<billing-enabled key>
python run_lrm_ablation.py --datasets digiklausur --use-gemini --sample-n 646
```
This is needed to confirm that Sample 0 produces CONTRADICTS steps with populated `kg_nodes` under Gemini Flash (DeepSeek-R1 leaves kg_nodes empty on judgment steps — that's why Sample 0 gaps have no node labels in the current trace).

**Participant Recruitment Outreach**
- Target: CS/NN TAs and instructors who have *actually graded student work*
- 20–30 participants for 45-minute sessions
- Compensation: $30–50 Amazon gift card
- Do NOT recruit from LinkedIn, Reddit, or crowdsourcing platforms
- **This is the highest-risk item on the critical path — begin outreach now, before pilot software is finalized.**

---

### 4.2 Short-Term (After Pilot Study)

**Run Pilot (2–3 Participants)**
Primary observation target: do educators notice the CONTRADICTS chips are clickable (CSS pulse + AddCircleOutlineIcon)?
- If >50% of Condition B educators edit only before the trace, add stronger visual affordance.
- Validate event log format — confirm all 17 `RubricEditPayload` fields are present and correctly typed.
- Confirm GEE model runs end-to-end on real data (not dummy).

**Build `POST /api/study/log` NestJS Endpoint**
```
POST /api/study/log
Body: StudyEvent JSON
Response: { received: true }
```
Fire-and-forget from `studyLogger.ts`. Provides IRB-grade durability against browser tab crashes. Build AFTER pilot confirms the event schema is stable.

**§4 System Architecture Draft**
- Figure 1: high-level TRM flowchart (KG → trace → structural leap visualization) — place in §3
- Figure 2: annotated screenshot of actual system (all 11 panels) — place in §4
- Figure 2 requires Gemini Flash trace for Sample 0 (depends on ablation above)
- Writing pipeline: describe the 5-stage ML pipeline, then the 3-panel co-auditing interface, then the bidirectional brushing interactions

**`panel_focus_ms` Rename**
Before full study, rename `panel_focus_ms` → `panel_mount_timestamp_ms` in `studyLogger.ts` and `analyze_study_logs.py`. Minor but important for data interpretability.

---

### 4.3 Medium-Term (Full Study + Paper Completion)

**Run Full Study (N=20)**
- Two conditions, balanced assignment
- 45-minute sessions (task + rubric review + SUS)
- Export study logs from localStorage + backend
- Run `analyze_study_logs.py` — GEE results will determine whether H1 and H2 are reportable or need re-framing

**§5b User Study Section**
- Method skeleton can be written now (before data)
- Fill H1 and H2 results after study data is available
- Pre-registered exploratory: p < 0.10 for trace_gap_count moderator = "directional trend" in Discussion

**§5a ML Accuracy Section**
This is the only section that is data-ready NOW. Write first after §4:
- Table 1: 3-dataset results (Mohler / DigiKlausur / Kaggle ASAG)
- Stability Analysis subsection: cross-model validation (Gemini Flash vs DeepSeek-R1) — grounding density + gap count distribution. Claim: TRM is invariant to model verbosity.
- Kaggle ASAG boundary condition framing: do not hide, explain as a domain-boundary finding.

**§2 Related Work**
Can be written at any time (no data dependency). Four areas:
1. XAI for NLP (LIME, SHAP, attention) — move LIME/SHAP para from Introduction here
2. Educational Analytics dashboards (aggregate stats, not reasoning-trace explainability)
3. Interactive Machine Teaching (IMT) — distinguish from co-auditing
4. Knowledge-grounded NLG evaluation [Ji 2023], trace faithfulness [Lanham 2023], concept map viz [Novak 1984]

**§6 Discussion + §7 Conclusion**
After all other sections are complete:
- §6: domain boundary mismatch (Kaggle ASAG); panel-before-trace strategy; limitations (alias dict covers only CS+NN; n=20 power)
- §7: TRM generalizability beyond grading (any domain where a KG exists and reasoning chains are auditable)

---

### 4.4 Remaining Open Questions (For Next Gemini Review)

| Q | Question |
|---|----------|
| A | §4 pipeline diagram: Option A (flowchart), B (annotated screenshot), or C (both)? Recommendation is C. |
| B | GEE working correlation ρ negative in dummy test (ρ = −0.308). If ρ < 0 in real data, switch to Independence working correlation? |
| C | Alias dictionary scope: CS + NN only (locked). But should we report the Kaggle ASAG semantic alignment rate using exact-only matching to be methodologically consistent? |
| D | H2 hypergeometric null: `N=max(n_rubric, m_flagged, 20)` uses 20 as a prior for unknown rubric size. Is this defensible in §5b Methods? Should we estimate N from the DigiKlausur KG node count instead? |
| E | SUS: is 10-item SUS sufficient for VIS 2027, or should we add NASA-TLX for cognitive load? |

---

## 5. Critical Path Summary

```
[NOW]
  ↓
File IRB amendment (expedited, 48-72h) ────────────────────────────────────────┐
Begin TA/instructor recruitment outreach                                         │
Write Introduction v13 (5 editorial cuts)                                        │
Run DigiKlausur Gemini Flash ablation (needs API key)                           │
                                                                                 │
[IRB APPROVED]                                                                   │
  ↓                                                                              │
Run pilot study (2-3 participants)                                               │
  → Fix affordance if click rate low                                             │
Build POST /api/study/log NestJS endpoint                                        │
Write §4 System Architecture (after figure is taken from system screenshot)     │
Write §5a ML Accuracy (data ready now)                                          │
                                                                                 │
[~N PARTICIPANTS RECRUITED] ──────────────────────────────────────────────┘     │
  ↓                                                                              │
Run full study (N=20, 45-min sessions)                                          │
Analyze logs → GEE → H1/H2 results                                             │
Write §5b User Study                                                            │
Write §2 Related Work (can be done in parallel)                                │
Write §6 Discussion + §7 Conclusion                                             │
  ↓                                                                             │
[~6 months before VIS 2027 abstract deadline]                                  │
  ↓                                                                             │
Full paper draft → co-author review → revision → submission                    │
```

**Highest risk:** Participant recruitment (CS/NN educators who have graded) — begin immediately.  
**Second highest risk:** ⚠️ LRM/user-study code has never been committed to GitHub — if this machine is lost, the entire Phase 5 + Phase 6 work is gone. Commit immediately (see §8).  
**Third highest risk:** Gemini Flash ablation for Sample 0 figure — needs API key now.  
**Everything else** (writing, code, analysis) is in-hand and manageable.

---

## 6. Paper Section Status

| Section | Status | Blocker |
|---------|--------|---------|
| §1 Introduction | v12 draft; v13 edits pending | 5 editorial changes (apply from Q1–Q5 decisions) |
| §2 Related Work | Not started | None — data-free; can write now |
| §3.1 TRM Formal Definitions | **Complete (locked)** | None |
| §3.2 Pedagogical Interpretation | Draft complete | Minor polish needed |
| §3.3 System Architecture Overview | Not started | Needs pipeline figure |
| §4 Implementation | Not started | Needs system screenshot (Gemini Flash trace) |
| §5a ML Accuracy | Not started — data ready | Write now; no new data needed |
| §5b User Study | Skeleton only | User study data (post-full-study) |
| §6 Discussion | Not started | Needs §5a + §5b results |
| §7 Conclusion | Not started | Needs full paper draft |

**Locked writing order:** §1 → §3.1 → §3.2 → §4 → §5a → §5b → §2 → §6 → §7 → §1 polish

---

## 7. Technical Debt & Configuration

### API Keys
- `GEMINI_API_KEY`: required for DigiKlausur Gemini Flash ablation. Current key in `packages/backend/.env` is `AIzaSyAYFB2h53KITX2OL-9P5vljNQRUE__op9Q` (may have quota limits; a billing-enabled key is needed for batch ablation).
- `DEEPSEEK_API_KEY`: not set. DeepSeek-R1 traces are available from earlier cached runs.

### Reproducibility
All ML results are cached. To reproduce any dataset evaluation:
```bash
python run_batch_eval_api.py --dataset mohler     # uses cache by default
python run_batch_eval_api.py --dataset digiklausur
python run_batch_eval_api.py --dataset kaggle_asag
```
No API calls will be made if `data/batch_responses/` already has the response files (12 files for Kaggle ASAG: 6 cllm + 6 c5fix).

### GEE Requirements
`statsmodels >= 0.14` and `pandas` required for `analyze_study_logs.py`. Install:
```bash
pip install statsmodels pandas
```

### Frontend Dev Server
```bash
cd packages/frontend && yarn dev
# Dashboard at http://localhost:3000/dashboard
# Condition A: /dashboard?condition=A
# Condition B: /dashboard?condition=B
```

---

## 8. GitHub Repositories & Version Control

### 8.1 Two Remotes

The local repository has two GitHub remotes tracking different scopes of the work:

| Remote | URL | Purpose |
|--------|-----|---------|
| `origin` | `https://github.com/bobbyk468/NodeManager` | Full monorepo — NodeGrade platform + ConceptGrade. **In sync with local HEAD.** |
| `conceptgrade` | `https://github.com/bobbyk468/ConceptGrade.git` | Older dedicated ConceptGrade repo — LLM-era code only. 66 commits behind local. |

---

### 8.2 LLM Era vs LRM Era — What Each Repo Contains

The project evolved in two distinct phases:

**LLM Era** (what `conceptgrade` remote and early `origin` commits contain):
- Standard LLM-as-grader (`C_LLM` baseline) using Gemini as a holistic scorer
- KG-augmented grading pipeline (C1–C5) with LLM as a verifier
- The "verifier" here is an LLM that receives concept evidence and produces a calibrated score
- Three datasets evaluated (Mohler, DigiKlausur, Kaggle ASAG)
- Dashboard with 9 charts (Bloom, SOLO, heatmap, radar, score comparison)
- This version is what the early `origin` commit `46eb12e` (ConceptGrade visualization dashboard) captures

**LRM Era** (local only — never committed):
- The LLM grader is replaced / augmented with a **Large Reasoning Model** (Gemini Flash, DeepSeek-R1) that produces a full **chain-of-thought trace** per student answer
- Each trace step is parsed into `ParsedStep` objects with `kg_nodes`, `classification`, and `step_id`
- **Topological Reasoning Mapping (TRM)** projects these trace steps onto the KG, detecting structural leaps
- New dashboard panels: `VerifierReasoningPanel` (TRM trace viewer) + `RubricEditorPanel` (co-auditing interface)
- Full user study instrumentation: causal attribution windows, semantic alignment rate, GEE analysis
- Formal TRM definitions in the paper (Definitions 1–5)

---

### 8.3 How to Clone and Run Each Version

**To get the LLM-era codebase (the stable, committed version):**
```bash
# Clone the full monorepo (recommended — most complete LLM-era state)
git clone https://github.com/bobbyk468/NodeManager.git
cd NodeManager/NodeGrade

# Or clone the older dedicated ConceptGrade repo (earlier LLM-era state)
git clone https://github.com/bobbyk468/ConceptGrade.git
```

**To run the LLM-era pipeline (after cloning NodeManager):**
```bash
cd packages/concept-aware

# Install Python dependencies
pip install -r requirements-concept-aware.txt
pip install statsmodels pandas

# Reproduce ML results from cache (no API key needed)
python run_batch_eval_api.py --dataset mohler
python run_batch_eval_api.py --dataset digiklausur
python run_batch_eval_api.py --dataset kaggle_asag

# Start the full stack
cd ../backend && npm install && npm run start:dev &
cd ../frontend && yarn install && yarn dev
# Dashboard: http://localhost:3000/dashboard
```

**To get the LRM-era codebase (current full state including TRM and user study):**

⚠️ This currently exists **only on the local machine**. It has never been pushed. After the commit described in §8.4, clone from origin:
```bash
git clone https://github.com/bobbyk468/NodeManager.git
cd NodeManager/NodeGrade
# The LRM layer will be present after the commit described below
```

---

### 8.4 ⚠️ Critical: LRM Work Is Not Backed Up

**The following files exist only locally — they have never been committed to any git remote:**

| File | What It Is |
|------|-----------|
| `packages/concept-aware/conceptgrade/lrm_verifier.py` | LRM Verifier — the engine that produces chain-of-thought traces |
| `packages/concept-aware/conceptgrade/trace_parser.py` | TRM Trace Parser — converts raw LRM output to `ParsedStep[]` |
| `packages/concept-aware/analyze_study_logs.py` | GEE moderation analysis for user study H1/H2 |
| `packages/concept-aware/run_lrm_ablation.py` | LRM ablation runner (Gemini Flash vs DeepSeek-R1) |
| `packages/frontend/src/components/charts/VerifierReasoningPanel.tsx` | TRM trace viewer with structural leap indicators |
| `packages/frontend/src/components/charts/RubricEditorPanel.tsx` | Co-auditing rubric editor + Click-to-Add |
| `packages/frontend/src/components/charts/ConceptKGPanel.tsx` | KG subgraph visualization |
| `packages/frontend/src/components/charts/CrossDatasetComparisonChart.tsx` | Cross-dataset comparison chart |
| `packages/frontend/src/components/charts/SUSQuestionnaire.tsx` | System Usability Scale panel |
| `packages/frontend/src/components/charts/StudentAnswerPanel.tsx` | Student answer text viewer |
| `packages/frontend/src/contexts/DashboardContext.tsx` | Global state (rolling window, gap count, density) |
| `packages/frontend/src/utils/conceptAliases.ts` | 3-layer semantic matching (alias dict + Levenshtein) |
| `packages/concept-aware/results/` | All Gemini review documents v1–v12, code review, status doc |
| `packages/concept-aware/data/mohler_lrm_traces.json` | LRM trace data for Mohler dataset |
| `packages/concept-aware/data/digiklausur_lrm_traces.json` | LRM trace data for DigiKlausur |
| `packages/backend/src/study/` | Study backend (planned NestJS endpoint) |

**Additionally modified (tracked, but changes not staged):**

| File | Change |
|------|--------|
| `packages/frontend/src/utils/studyLogger.ts` | Made `logEvent` generic; `RubricEditPayload` schema |
| `packages/frontend/src/pages/InstructorDashboard.tsx` | Study condition gating, study panel integration |
| `packages/frontend/src/components/charts/index.ts` | New component exports |
| `packages/backend/src/visualization/visualization.service.ts` | Service hardening, placeholder specs |
| Various `data/*.json` files | Eval results, LRM ablation summary |

---

### 8.5 Recommended Commit Strategy

Commit the LRM work in three logical units so the history remains readable:

**Commit 1 — LRM Core Pipeline**
```bash
git add packages/concept-aware/conceptgrade/lrm_verifier.py
git add packages/concept-aware/conceptgrade/trace_parser.py
git add packages/concept-aware/run_lrm_ablation.py
git add packages/concept-aware/data/mohler_lrm_traces.json
git add packages/concept-aware/data/digiklausur_lrm_traces.json
git add packages/concept-aware/data/lrm_ablation_summary.json
git commit -m "feat(concept-aware): LRM Verifier + TRM Trace Parser — chain-of-thought grading pipeline

Adds Large Reasoning Model integration:
- lrm_verifier.py: Gemini Flash / DeepSeek-R1 chain-of-thought grader
- trace_parser.py: converts raw LRM output to ParsedStep[] with kg_nodes + classification
- run_lrm_ablation.py: cross-model ablation runner (Gemini Flash vs DeepSeek-R1)
- Cached LRM traces for Mohler and DigiKlausur datasets"
```

**Commit 2 — Visual Analytics User Study Layer**
```bash
git add packages/frontend/src/contexts/DashboardContext.tsx
git add packages/frontend/src/components/charts/VerifierReasoningPanel.tsx
git add packages/frontend/src/components/charts/RubricEditorPanel.tsx
git add packages/frontend/src/components/charts/ConceptKGPanel.tsx
git add packages/frontend/src/components/charts/CrossDatasetComparisonChart.tsx
git add packages/frontend/src/components/charts/SUSQuestionnaire.tsx
git add packages/frontend/src/components/charts/StudentAnswerPanel.tsx
git add packages/frontend/src/utils/conceptAliases.ts
git add packages/frontend/src/utils/studyLogger.ts    # modified
git add packages/frontend/src/components/charts/index.ts
git add packages/frontend/src/pages/InstructorDashboard.tsx
git commit -m "feat(frontend): TRM co-auditing UI — VerifierReasoningPanel, RubricEditorPanel, user study instrumentation

Implements the IEEE VIS 2027 user study layer:
- VerifierReasoningPanel: TRM trace viewer with structural leap indicators (node-only adjacency)
- RubricEditorPanel: co-auditing rubric editor with Click-to-Add CONTRADICTS chips
- DashboardContext: rolling 60-s CONTRADICTS window, gap count + grounding density state
- conceptAliases.ts: 3-layer semantic matching (exact → alias dict → Levenshtein ≥ 0.80)
- studyLogger.ts: generic logEvent<T>, full RubricEditPayload schema (17 fields)
- Condition A/B gating, SUS questionnaire, KG subgraph + cross-dataset comparison panels"
```

**Commit 3 — Study Analysis + Review Documents**
```bash
git add packages/concept-aware/analyze_study_logs.py
git add packages/concept-aware/analyze_concept_matching_threshold.py
git add packages/concept-aware/results/
git add packages/concept-aware/docs/LRM_INTEGRATION.md
git commit -m "feat(concept-aware): GEE study analysis + Gemini review documents v1-v12

- analyze_study_logs.py: GEE Binomial/Logit moderation analysis (H1/H2)
  Outcome: within_30s ~ condition * trace_gap_count | session_id
  H2 split: semantic_alignment_rate_manual (primary) vs _cta (UI-assisted)
- results/: all Gemini review documents tracking TRM formalization decisions
  v7: trace_gap_count wiring | v8: recruitment | v9: ablation | v10: node-only adjacency
  v11: formal definition box | v12: Introduction draft | code_review_v1: instrumentation audit"
```

---

### 8.6 What the LLM → LRM Transition Means for the Showcase

If you want to **demo or present the LLM-era version** (simpler, no chain-of-thought):
```bash
# Use the committed origin/main state (checkout the dashboard commit)
git checkout 46eb12e   # feat: ConceptGrade visualization dashboard — full implementation
cd packages/frontend && yarn dev
# Shows: 9-chart dashboard (Bloom, SOLO, heatmap, score comparison, etc.)
# Does NOT show: TRM trace panel, RubricEditorPanel, structural leap indicators
```

If you want to **demo the full LRM/TRM version** (current local state):
```bash
# Stay on current main branch (after committing per §8.5)
cd packages/frontend && yarn dev
# Navigate to /dashboard?condition=B
# Shows: all 14 panels including VerifierReasoningPanel + RubricEditorPanel
# Click a CONTRADICTS step → KG subgraph highlights → rubric chip pulses
```

The key difference to explain to an audience:
- **LLM era**: the grader produces a *verdict* ("score: 3.5"). You see the score and the concept evidence, but not how the model arrived at it.
- **LRM era**: the grader produces a *chain-of-thought trace* (20–40 reasoning steps). TRM maps each step to KG nodes. Structural leaps between disconnected KG regions become visible. Educators can inspect, question, and act on the reasoning — not just the verdict.

This is the core of the co-auditing paradigm and the primary IEEE VIS 2027 contribution.
