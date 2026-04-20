# ConceptGrade Dashboard — Gemini Code Review v5

**Date:** 2026-04-19  
**Prior reviews:** v1 → v2 → v3 → v4 (GEMINI_FEEDBACK_PAPER2_V4.md) → this document  
**Input:** `GEMINI_FEEDBACK_PAPER2_V4.md` — answers to Q-A1 through Q-F  
**Status:** All 6 v4 questions resolved. `tsc --noEmit` — 0 errors. Analysis pipeline verified.

---

## 1. v4 Question Dispositions

| Q | Finding | Action taken |
|---|---------|-------------|
| Q-A1 | Heatmap severity labels confirmed confound | **Fixed** — Condition A gets aggregated "students affected" list (no severity) |
| Q-A2 | `total_misconceptions` scalar is acceptable | **No change** — kept in both conditions |
| Q-B | `min_edits=3` as primary = researcher DoF risk | **Fixed** — swapped back to `min_edits=1` primary; `_min3` demoted to sensitivity |
| Q-C | 500ms dwell — two strong citations provided | **Fixed** — citations added as code comments + paper language note |
| Q-D | Layout cache dataset-switch clearing | **No change** — `dataset::conceptId` key + LRU is sufficient |
| Q-E | Distinguish `beacon_sent` vs `beacon_ls_only` | **Fixed** — `getBeaconCaptureMethod()` exported; payload updated |
| Q-F | Python inner-function scoping confirmed safe | **No change** needed |

---

## 2. Implemented Fixes (v5)

### Fix B — H1 Primary Estimator Restored to Pre-Registered `min_edits=1`

**`analyze_study_logs.py`** — column renaming and comment update:

```python
# PRIMARY (pre-registered): all participants with ≥1 edit — exact estimator at pre-registration
'causal_attribution_rate_15s': participant_mean_ratio(rows, 'rubric_edits_within_15s'),
'causal_attribution_rate_30s': participant_mean_ratio(rows, 'rubric_edits_within_30s'),
'causal_attribution_rate_60s': participant_mean_ratio(rows, 'rubric_edits_within_60s'),

# Sensitivity & Robustness (Supplementary Material):
'causal_attribution_rate_15s_min3': participant_mean_ratio(rows, '...', min_edits=3),
'causal_attribution_rate_30s_min3': participant_mean_ratio(rows, '...', min_edits=3),
'causal_attribution_rate_60s_min3': participant_mean_ratio(rows, '...', min_edits=3),
'causal_attribution_rate_30s_weighted': participant_weighted_ratio(rows, '...'),
```

**Report output now shows:**
```
Attribution rate @ 30 s [PRIMARY H1]      0.000    0.800   ← min_edits=1 (pre-registered)
  ↳ high-engagement only (≥3 edits)       0.000    0.600   ← sensitivity
  ↳ edit-weighted mean                    0.000    0.667   ← robustness
```

**Paper language (per Gemini Q-B):**
> "To ensure our primary pre-registered findings were not skewed by high-variance outlier sessions (educators making only 1–2 total edits), we conducted a post-hoc sensitivity analysis restricted to high-engagement sessions (≥3 edits). The causal attribution trend held stable across both the primary (0.800) and high-engagement-only (0.600) estimators."

---

### Fix E — `capture_method` Distinguishes `beacon_sent` vs `beacon_ls_only`

**`studyLogger.ts`** — type updated + helper exported:

```typescript
// AnswerDwellPayload type
capture_method: 'beacon_sent' | 'beacon_ls_only' | 'cleanup' | null;
//              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
//              'beacon_sent'    = navigator.sendBeacon() queued (reliable)
//              'beacon_ls_only' = localStorage only, no backend (at-risk on tab close)
//              'cleanup'        = React cleanup during normal navigation (fetch-based)
//              null             = answer_view_start (end method not yet known)

// New export — call at payload-construction time:
export function getBeaconCaptureMethod(): 'beacon_sent' | 'beacon_ls_only' {
  return studyApiBase ? 'beacon_sent' : 'beacon_ls_only';
}
```

**`StudentAnswerPanel.tsx`** — call site updated:

```typescript
import { AnswerDwellPayload, getBeaconCaptureMethod, logBeacon, logEvent } from '../../utils/studyLogger';

// In useEffect cleanup:
const endPayload: AnswerDwellPayload = {
  ...
  capture_method: getBeaconCaptureMethod(),  // ← was hardcoded 'beacon'
  ...
};
```

**Post-study audit query (Python):**
```python
# Flag sessions with only ls_only end events — potential data loss on tab close
at_risk = [
    s for s in sessions
    if all(e['payload'].get('capture_method') == 'beacon_ls_only'
           for e in s['events'] if e['event_type'] == 'answer_view_end')
]
```

---

### Fix C — 500ms Dwell Citations Added to Code

**`ScoreSamplesTable.tsx`:**

```typescript
// Minimum hover duration before an xai_pill_hover event is logged.
// 500ms calibrated against established cognitive reading thresholds:
//   Just & Carpenter (1980) — eye-mind fixations for semantic processing: 250–500ms+.
//   Chen et al. (2001) — mouse hover correlates with visual attention on web UIs.
// Paper: "We applied a 500ms dwell-time gate to xai_pill_hover events to filter
// incidental cursor transits, capturing only intentional semantic processing in
// alignment with established eye-mind thresholds (Just & Carpenter, 1980; Chen et al., 2001)."
const PILL_DWELL_THRESHOLD_MS = 500;
```

---

## 3. Full Cumulative Change Inventory (all sessions)

| Session | File | Change |
|---------|------|--------|
| v3 | `studyLogger.ts` | Dual-write failure handler; `kg_node_drag` + `xai_pill_hover` event types |
| v3 | `StudentAnswerPanel.tsx` | FNV-1a 64-bit FERPA hash |
| v3 | `ScoreSamplesTable.tsx` | Q7 `condition`/`dataset` passed to VerifierReasoningPanel |
| v3 | `InstructorDashboard.tsx` | Runtime condition guard; fatal Alert overlay |
| v3 | `analyze_study_logs.py` | Conservative-K footnote |
| v3 | `ConceptKGPanel.tsx` | `kg_node_drag` logging; module-level layout cache |
| v4 | `ConceptFrequencyChart.tsx` | Condition A neutral color; stripped subtitle |
| v4 | `ConceptKGPanel.tsx` | `dataset::conceptId` cache key; LRU eviction at 50 |
| v4 | `ScoreSamplesTable.tsx` | 500ms dwell gate on `xai_pill_hover`; `dwell_ms` payload |
| v4 | `analyze_study_logs.py` | Explicit `cond_rows` params; `_min3`/`_weighted` sensitivity columns |
| v4 | `StudentAnswerPanel.tsx` | React 18 Strict Mode 50ms guard on `logBeacon` |
| v5 | `MisconceptionHeatmap.tsx` | Condition A aggregated view (no severity breakdown) |
| v5 | `analyze_study_logs.py` | Swap primary to `min_edits=1`; rename columns to `_min3` |
| v5 | `studyLogger.ts` | `getBeaconCaptureMethod()`; `capture_method` type union updated |
| v5 | `StudentAnswerPanel.tsx` | `capture_method: getBeaconCaptureMethod()` |
| v5 | `ScoreSamplesTable.tsx` | Citations in dwell-threshold comment |

---

## 4. Verification

```
tsc --noEmit:     0 errors ✓
Python H1 report:
  30s PRIMARY [min_edits=1]:   B=0.800  A=0.000  ✓
  30s sensitivity [min_edits=3]: B=0.600  A=0.000  ✓
  30s weighted:                B=0.667  A=0.000  ✓
Condition A heatmap:           aggregated list, no severity labels ✓
Condition A frequency chart:   uniform blue, neutral subtitle ✓
capture_method type:           'beacon_sent'|'beacon_ls_only'|'cleanup'|null ✓
```

---

## 5. Remaining Open Design Questions for Gemini

### 5.1 Condition A `StudentAnswerPanel` — Answer Severity Labels

The `StudentAnswerPanel` shows each student row with a severity `Chip` label (`Critical miss`, `Moderate miss`, `Minor miss`, `Covered`). These severity values come from the same KG matching logic as the heatmap. Condition A participants who drill into the answer panel will see the same severity signal that was removed from the heatmap.

**Q-G:** Should the severity `Chip` labels in `StudentAnswerPanel` be replaced with neutral labels in Condition A (e.g., "Not reviewed" or a score-based quartile label)? Or is the heatmap-to-answer drill-down interaction gated in Condition A in a way that prevents this view?

*Current state:* `StudentAnswerPanel` is rendered for both conditions; its `defaultSeverity` prop is set from the heatmap cell click. If the Condition A heatmap no longer has clickable severity cells (the new aggregated view doesn't call `onCellClick`), the `StudentAnswerPanel` may be unreachable in Condition A via the heatmap path. Confirm whether this interaction path is still open in Condition A.

### 5.2 `answer_view_start` `capture_method` Field

The `answer_view_start` event currently sets `capture_method: null`. This is documented as "end method not yet determined." The matching `answer_view_end` sets `capture_method: getBeaconCaptureMethod()`.

**Q-H:** For the post-study join between `answer_view_start` and `answer_view_end` events, the analyst uses `student_answer_id + session_id` as the join key. Is `capture_method: null` on the start event sufficient to distinguish start from end events, or should the start event use a dedicated value (e.g., `capture_method: 'start'`) to make the join query unambiguous?

### 5.3 `causal_attribution_rate_*` — Condition A Interpretation

The primary estimator `causal_attribution_rate_30s` is now `min_edits=1` for both conditions. In Condition A, there are no CONTRADICTS interactions (the VerifierReasoningPanel is not shown), so the rate should always be 0.

**Q-I:** In the paper's Table 3, should the Condition A `causal_attribution_rate_30s` column be reported as 0.000 or as "N/A" with a footnote explaining that Condition A has no trace panel? Reporting 0.000 is technically correct but could mislead reviewers into thinking Condition A participants actively chose not to make temporally-aligned edits (which requires CONTRADICTS interaction first).

### 5.4 MisconceptionHeatmap Condition A — Interaction Path Audit

The new Condition A heatmap view is a static list (no `onCellClick`). But `InstructorDashboard` passes `onCellClick` to the heatmap, and the heatmap fires it internally only in the full severity-grid path.

**Q-J:** Please confirm: in the new Condition A code path (`isConditionA === true`), the early-return renders a static Box with no `onCellClick` calls — meaning `selectedConcept`, `selectedSeverity`, and `StudentAnswerPanel` are NOT updated from the heatmap in Condition A. Is this the intended isolation, or should Condition A still be able to select a concept (and see the StudentAnswerPanel) via the aggregated list rows?

### 5.5 Paper Methods Section — Condition Isolation Statement

The isolation decisions across 4 components (frequency chart, heatmap, answer panel severity, MetricCard) need a unified 2-3 sentence statement for the paper's Methods section.

**Q-K:** Please draft a concise Methods paragraph (≤100 words) that covers: (1) what Condition A sees vs. doesn't see; (2) the rationale (prevent H2 confounding); (3) that Condition A still has full rubric editing capability. This will go directly into Section 4.2 "Study Conditions" of the paper.

---

## 6. File Reference Map (current)

```
packages/frontend/src/
  components/charts/
    ConceptFrequencyChart.tsx    ← Condition A: uniform blue, neutral subtitle (v4)
    MisconceptionHeatmap.tsx     ← Condition A: aggregated list, no severity (v5)
    StudentAnswerPanel.tsx       ← FNV-1a 64-bit; Strict Mode guard; beacon method (v3/v4/v5)
    ScoreSamplesTable.tsx        ← dwell gate; citations; condition/dataset to VRP (v4/v5)
    ConceptKGPanel.tsx           ← dataset::conceptId cache; LRU; kg_node_drag (v3/v4)
    VerifierReasoningPanel.tsx   ← condition/dataset received from ScoreProvenancePanel (v3)
    RubricEditorPanel.tsx        ← rubric_edit; semantic alignment (unchanged)
    SUSQuestionnaire.tsx         ← SUS logging (unchanged)
  pages/InstructorDashboard.tsx  ← condition guard; dual-write handler (v3)
  contexts/DashboardContext.tsx  ← brushing state (unchanged)
  utils/studyLogger.ts           ← getBeaconCaptureMethod; capture_method type (v5)

packages/concept-aware/
  analyze_study_logs.py          ← primary=min_edits=1; _min3/_weighted sensitivity (v5)
  results/
    conceptgrade_gemini_paper2_v5.md  ← this document
```
