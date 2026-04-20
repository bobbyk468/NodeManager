# GitHub Commit Summary — LRM/TRM/User-Study Layer

**Date:** 2026-04-15  
**Repository:** https://github.com/bobbyk468/NodeManager  
**Branch:** main  
**Three commits pushed** (f420498, e6ba613, d7f1e26)

---

## Commit 1 — LRM Core Pipeline

**Hash:** `f420498`  
**Message:** `feat(concept-aware): LRM Verifier + TRM Trace Parser — Large Reasoning Model integration`

### Files Added (6)
- `packages/concept-aware/conceptgrade/lrm_verifier.py` ← **Gemini Flash / DeepSeek-R1 verifier**
- `packages/concept-aware/conceptgrade/trace_parser.py` ← **Parse LRM output to ParsedStep[]**
- `packages/concept-aware/run_lrm_ablation.py` ← **Ablation runner (cross-model comparison)**
- `packages/concept-aware/data/mohler_lrm_traces.json` ← **120 cached traces (Mohler)**
- `packages/concept-aware/data/digiklausur_lrm_traces.json` ← **646 cached traces (DigiKlausur)**
- `packages/concept-aware/data/lrm_ablation_summary.json` ← **Cross-model ablation results**

### Key Features
- Large Reasoning Model produces 20–40 step chain-of-thought per answer
- Each step parsed to: `step_id`, `kg_nodes: string[]`, `classification: SUPPORTS|CONTRADICTS|UNCERTAIN`
- Foundational for TRM Formal Definitions (§3.1 paper section)
- Enables VerifierReasoningPanel visualization
- All results cached — no API calls needed to reproduce

### How to Use
```bash
# Reproduce evaluation (uses cache):
python run_batch_eval_api.py --dataset mohler

# Run fresh ablation (requires GEMINI_API_KEY):
python run_lrm_ablation.py --datasets digiklausur --use-gemini --sample-n 646
```

---

## Commit 2 — Visual Analytics User Study Layer

**Hash:** `e6ba613`  
**Message:** `feat(frontend): TRM co-auditing UI + user study instrumentation layer`

### Files Added (11)

**Core State Management:**
- `packages/frontend/src/contexts/DashboardContext.tsx` ← **Global state machine**
  - Rolling 60-second CONTRADICTS window
  - `lastTraceGapCount` (structural leaps moderator)
  - `lastGroundingDensity` (grounding stability)
  - Bidirectional brushing (selectedConcept)

**Event Logging:**
- `packages/frontend/src/utils/studyLogger.ts` ← **Generic `logEvent<T>` function**
  - `RubricEditPayload`: 17 fields, multi-window attribution (15/30/60s)
  - `interaction_source`: 'manual' vs 'click_to_add' (H2 source split)
  - Fire-and-forget POST to `/api/study/log`

**Semantic Matching:**
- `packages/frontend/src/utils/conceptAliases.ts` ← **3-layer fuzzy matching**
  - Layer 1: exact normalized match
  - Layer 2: domain alias dictionary (CS + NN only)
  - Layer 3: Levenshtein ratio ≥ 0.80
  - Returns: `{matched: boolean, bestMatch: string, score: 0-1}`

**TRM Visualization:**
- `packages/frontend/src/components/charts/VerifierReasoningPanel.tsx` ← **Trace viewer with gap indicators**
  - Renders LRM trace (20–40 steps)
  - Node-only adjacency detection (Nᵢ ∩ Nᵢ₊₁ ≠ ∅)
  - Structural leap indicators (amber) + grounding density bar
  - Publishes gap count + density to context
  - Tooltips: "incomplete explanation: intermediate concept was skipped"

- `packages/frontend/src/components/charts/ConceptKGPanel.tsx` ← **KG ego-graph**
  - Shows concept neighborhood (PREREQUISITE, HAS_PART, PRODUCES edges)
  - Activated on concept selection (brushing)
  - Highlights leap-to-leap paths

**Co-Auditing Interface:**
- `packages/frontend/src/components/charts/RubricEditorPanel.tsx` ← **Rubric editor + Click-to-Add**
  - Multi-window causal attribution (w15, w30, w60)
  - CONTRADICTS chips pulse 3× on mount
  - Click-to-Add logs `interaction_source: 'click_to_add'`
  - Semantic alignment: fuzzy match via conceptAliases
  - `panelBeforeTrace`: captures rubric-first vs trace-first strategies
  - H2 split: `semantic_alignment_rate_manual` (primary) vs `_cta` (UI-assisted)

**Additional Panels:**
- `packages/frontend/src/components/charts/SUSQuestionnaire.tsx` ← **System Usability Scale**
  - 10-item Likert scale (5 points each)
  - Post-task questionnaire (Condition B only)

- `packages/frontend/src/components/charts/CrossDatasetComparisonChart.tsx` ← **Domain comparison**
  - Side-by-side Bloom/SOLO distributions
  - Narrative: KG advantage scales with vocabulary specificity

- `packages/frontend/src/components/charts/StudentAnswerPanel.tsx` ← **Answer text viewer**
  - Context menu: "view student answer" from trace steps

**Updated Files:**
- `packages/frontend/src/components/charts/index.ts` ← **New component exports**
- `packages/frontend/src/pages/InstructorDashboard.tsx` ← **Condition A/B gating**

### Key Features
- **Node-only adjacency**: Nᵢ ∩ Nᵢ₊₁ ≠ ∅ (edge-type overlap NOT a criterion)
- **Grounding density**: secondary metric (not in GEE primary model)
- **Rolling window**: 60-second causal attribution window, re-filtered at edit time
- **Bidirectional brushing**: click concept → KG highlights; click KG → trace filters
- **H2 metric split**: manual vs UI-assisted separately (interaction_source flag)
- **Condition A/B**: URL param controls visibility; Condition A blank panel

### How to Use
```bash
cd packages/frontend && yarn dev
# Visit http://localhost:3000/dashboard?condition=B
# Click a CONTRADICTS step → KG subgraph highlights → rubric chip pulses
```

---

## Commit 3 — Study Analysis + Review Documents + Code Audit

**Hash:** `d7f1e26`  
**Message:** `feat(concept-aware): GEE study analysis + Gemini review documents v1-v12 + code audit`

### Files Added (22)

**Study Analysis:**
- `packages/concept-aware/analyze_study_logs.py` ← **GEE Binomial/Logit moderation analysis**
  ```
  Model: within_30s ~ condition * trace_gap_count | session_id
  Outcome: Binary (within 30-second window?)
  Family: Binomial(Logit link), Correlation: Exchangeable(ρ)
  H1: Condition B > H0 on within_30s (causal proximity)
  H2: semantic_alignment_rate_manual > hypergeometric null
  Moderation: trace_gap_count (exploratory, p < 0.10 = directional trend)
  ```
  - Session-level metrics: n_edits, n_within_30s, n_semantic_aligned_manual, n_semantic_aligned_cta
  - Mean trace gap count + grounding density per session
  - Per-session hypergeometric p-values for concept alignment null

- `packages/concept-aware/analyze_concept_matching_threshold.py` ← **Semantic threshold validation**
  - Tunes Levenshtein ratio threshold (currently 0.80) post-pilot
  - Evaluates false positive / false negative rates

**Gemini Review Documents (v1–v12):**

| Version | Focus | Locked Decisions |
|---------|-------|-----------------|
| v1–v5 | Ablation & contribution claims | KG discriminability; Kaggle = boundary condition |
| v6–v7 | Gap indicators; GEE upgrade | Rolling window; mixedlm → Binomial/Logit |
| v8 | Recruitment & IRB strategy | Sample 0 selected; TA criteria; Condition A requires amendment |
| v9 | Ablation & contribution refinement | Cross-model → Stability Analysis |
| v10 | Node-only adjacency | Nᵢ ∩ Nᵢ₊₁ only; "structural leap" terminology |
| v11 | Formal definitions + interpretation | cᵢ moved to prose; "implicit mental models" |
| v12 | Introduction draft (v1) + Q1–Q5 | 5 decisions on CoT, citations, placeholders, scope, length |

**Files Included:**
- `conceptgrade_code_review_v1.md` ← **6-layer instrumentation audit**
- `conceptgrade_code_review_v1_feedback.md` ← **Gemini's answers to code review Q1–Q5**
- `conceptgrade_project_status.md` ← **Complete project status (this document!)**
- `conceptgrade_introduction_draft_v12.md` ← **Introduction v1 (~1,050 words)**
- All other review docs (v6, v7, v8, v9, v10, v11) ← **Locked decision progression**

### Key Features
- **GEE Binomial/Logit**: corrects Type I inflation from standard logistic regression on binary outcomes
- **H2 PRIMARY metric**: `semantic_alignment_rate_manual` (manual edits only)
- **H2 UI-ASSISTED**: `semantic_alignment_rate_cta` (Click-to-Add, reported separately)
- **Working correlation ρ**: Exchangeable, reported in paper Methods
- **Hypergeometric null**: Session-level H2 baseline (chance alignment)
- **12-round decision progression**: all locked after Gemini review (do not re-open)

### How to Use
```bash
# Analyze pilot/study data (post-study):
python analyze_study_logs.py --session-logs /path/to/study_logs.json

# Review design decisions:
cat results/conceptgrade_project_status.md
```

---

## What's Now on GitHub (Safely Backed Up)

### ✅ Backed Up & Pushed
- [x] LRM Verifier (lrm_verifier.py)
- [x] TRM Trace Parser (trace_parser.py)
- [x] LRM Ablation Runner (run_lrm_ablation.py)
- [x] All LRM trace data (cached)
- [x] DashboardContext state machine
- [x] VerifierReasoningPanel TRM viewer
- [x] RubricEditorPanel co-auditing UI
- [x] Semantic matching (conceptAliases.ts)
- [x] Event logging (studyLogger.ts)
- [x] GEE analysis (analyze_study_logs.py)
- [x] All Gemini review documents v1–v12
- [x] Code audit + feedback
- [x] Project status document

### ⚠️ Still Local Only (Untracked)
- `packages/backend/src/study/` — POST /api/study/log NestJS endpoint (planned, not yet built)
- `packages/concept-aware/docs/` — Various Word/docx files (secondary)
- Data backups: `*_backup.json`, `*_precomputed_*.json`
- Utility scripts: various `generate_*.py`, `convert_*.py`

**Action:** The critical code is now safe on GitHub. The backend study endpoint can be built later.

---

## Verification

### Local Status
```
On branch main
Your branch is up to date with 'origin/main'.

Last 3 commits:
d7f1e26 feat(concept-aware): GEE study analysis + Gemini review documents v1-v12 + code audit
e6ba613 feat(frontend): TRM co-auditing UI + user study instrumentation layer
f420498 feat(concept-aware): LRM Verifier + TRM Trace Parser — Large Reasoning Model integration
```

### GitHub Status
Pushed to: `https://github.com/bobbyk468/NodeManager/commits/main`

---

## Next Steps After Successful Push

1. **Continue on different account/machine?**
   - Clone: `git clone https://github.com/bobbyk468/NodeManager.git`
   - All LRM/TRM/study code is now in the repo
   - Memory files: `/memory/` directory in `.claude/projects/-Users-brahmajikatragadda-Desktop-PHD-NodeGrade/`

2. **Immediate priorities** (from conceptgrade_project_status.md §4.1):
   - [ ] File IRB amendment (Condition A blank panel change, expedited 48-72h)
   - [ ] Write Introduction v13 (apply 5 Gemini Q1-Q5 edits)
   - [ ] Run DigiKlausur Gemini Flash ablation (get Sample 0 figure trace)
   - [ ] Begin TA/instructor recruitment outreach (highest critical-path risk)

3. **Before pilot study**:
   - [ ] IRB amendment approved
   - [ ] Ablation complete (figure trace ready)
   - [ ] 2–3 pilot participants recruited
   - [ ] Confirmed: are CONTRADICTS chips clickable? (affordance test)

---

## Commit Message Style Reference

For future commits, use this three-part format:

```
feat(package): One-line summary of what feature adds

Longer explanation (1–3 paragraphs):
- Describe the problem it solves
- List key files/components
- Note any dependencies
- Add critical warnings if needed

## Related Issues / Paper Sections
- Issue #X or PR reference
- Paper section it enables (e.g., §3.1 TRM, §5b User Study)
```

Example from Commit 1:
```
feat(concept-aware): LRM Verifier + TRM Trace Parser — Large Reasoning Model integration

Adds chain-of-thought grading pipeline for IEEE VIS 2027 VAST submission:
[detailed explanation]
```

---

## GitHub Links to Review Commits

After push is complete, view commits at:
- Commit 1 (LRM): https://github.com/bobbyk468/NodeManager/commit/f420498
- Commit 2 (Frontend): https://github.com/bobbyk468/NodeManager/commit/e6ba613
- Commit 3 (Analysis): https://github.com/bobbyk468/NodeManager/commit/d7f1e26

All code is now safely backed up and available for cloning on any machine.
