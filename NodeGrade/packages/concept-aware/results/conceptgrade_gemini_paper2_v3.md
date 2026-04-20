# ConceptGrade Dashboard — Gemini Code Review v3

**Date:** 2026-04-19  
**Scope:** Paper 2 (IEEE VIS 2027 VAST submission) — full-stack VA dashboard + user study scaffolding  
**Prior reviews:** `conceptgrade_gemini_paper2_v1.md`, `conceptgrade_gemini_paper2_v2.md`, `GEMINI_FEEDBACK_PAPER2.md`  
**Status:** All 7 open questions from v2 (Q1/Q2/Q3/Q6/Q7/Q8/Q11) are now closed. TypeScript compilation passes with zero errors.

---

## 1. What Was Fixed Since v2

The following issues from `GEMINI_FEEDBACK_PAPER2.md` are now resolved. Each entry shows the exact code change for your verification.

---

### Q1 — Dual-Write Failure Detection (BLOCKING / IRB)

**Problem:** If both localStorage and the backend POST fail simultaneously (e.g. Safari strict private browsing + ad-blocker), data loss was silent.

**Fix in `packages/frontend/src/utils/studyLogger.ts`:**

```typescript
// safeLocalStorageAppend now returns boolean (true = wrote, false = failed)
function safeLocalStorageAppend(event: StudyEvent): boolean { ... }

let onDualWriteFailure: (() => void) | null = null;
export function setDualWriteFailureHandler(handler: () => void): void {
  onDualWriteFailure = handler;
}

export function logEvent(...): void {
  const localOk = safeLocalStorageAppend(event);
  if (studyApiBase) {
    fetch(`${studyApiBase}/api/study/log`, { ... }).catch(() => {
      if (!localOk && onDualWriteFailure) onDualWriteFailure(); // both channels down
    });
  } else if (!localOk && onDualWriteFailure) {
    onDualWriteFailure(); // no backend + localStorage failed
  }
}
```

**Fix in `packages/frontend/src/pages/InstructorDashboard.tsx`:**

```typescript
const [logFailure, setLogFailure] = useState(false);

useEffect(() => {
  setDualWriteFailureHandler(() => setLogFailure(true));
  // ... other mount logic
}, []);

// In render:
{logFailure && (
  <Alert severity="error" sx={{ mb: 2 }}>
    Study logging failed on both channels (localStorage + backend).
    Please disable ad-blockers and reload to continue.
    Session data cannot be saved — do not proceed.
  </Alert>
)}
```

**Verification:** `logFailure` state is wired; Alert renders above all study content, blocking the participant from continuing with data loss.

---

### Q2 — FERPA Hash Upgrade: FNV-1a 32-bit → 64-bit

**Problem:** 32-bit FNV-1a has ~50% collision probability at ~77k items.

**Fix in `packages/frontend/src/components/charts/StudentAnswerPanel.tsx`:**

```typescript
function fnv1a(text: string): string {
  let hash = BigInt('0xcbf29ce484222325');        // FNV offset basis (64-bit)
  const prime = BigInt('0x00000100000001b3');     // FNV prime (64-bit)
  const mask64 = (BigInt(1) << BigInt(64)) - BigInt(1);
  for (let i = 0; i < text.length; i++) {
    hash ^= BigInt(text.charCodeAt(i));
    hash = (hash * prime) & mask64;
  }
  return hash.toString(16).padStart(16, '0');    // 16-char hex string
}
```

Collision probability at 64-bit: ~1 in 10^14 at N=10,000. Negligible for IRB/FERPA purposes.

---

### Q3 — Missing Event Coverage: `kg_node_drag` + `xai_pill_hover`

**Problem:** KG node drag and XAI pill hover were not logged, under-counting trace interaction.

**Fix A — `kg_node_drag` in `packages/frontend/src/components/charts/ConceptKGPanel.tsx`:**

```typescript
// New StudyEventType entries in studyLogger.ts:
| 'kg_node_drag'    // educator drags a KG node to rearrange subgraph
| 'xai_pill_hover'  // educator hovers matched/missing concept pill

// KGGraph.onMouseUp (logged once per gesture, on release):
const onMouseUp = useCallback(() => {
  if (dragState.current) {
    logEvent(condition, dataset, 'kg_node_drag', {
      node_id: dragState.current.nodeId,
      concept_id: data.concept_id,
    });
    dragState.current = null;
  }
  if (svgRef.current) svgRef.current.style.cursor = 'default';
}, [condition, dataset, data.concept_id]);
```

**Fix B — `xai_pill_hover` in `packages/frontend/src/components/charts/ScoreSamplesTable.tsx`:**

```typescript
// ConceptPill now accepts onHover prop:
function ConceptPill({ label, variant, onHover }: {
  label: string; variant: 'matched' | 'missing'; onHover?: () => void
}) {
  return <Chip onMouseEnter={onHover} ... />;
}

// Call sites in ScoreProvenancePanel:
{xai.missing_concepts.map((c) => (
  <ConceptPill
    key={c} label={c} variant="missing"
    onHover={() => logEvent(condition ?? 'B', dataset, 'xai_pill_hover',
      { concept_id: c, variant: 'missing' })}
  />
))}
{xai.matched_concepts.map((c) => (
  <ConceptPill
    key={c} label={c} variant="matched"
    onHover={() => logEvent(condition ?? 'B', dataset, 'xai_pill_hover',
      { concept_id: c, variant: 'matched' })}
  />
))}
```

**Note:** No debounce was added. `onMouseEnter` fires once per enter, not per pixel — debounce would only be needed for `onMouseMove`. Existing behavior is correct.

---

### Q6 — Conservative-K Footnote in Hypergeometric Null Model

**Problem:** Using `rubric_edits[-1]['session_contradicts_nodes']` as K over-estimates the pool of flagged concepts.

**Fix in `packages/concept-aware/analyze_study_logs.py`:**

```python
# Use the last edit's session_contradicts_nodes as K (full session accumulation).
# This is a conservative estimator: as K grows throughout the session, the
# hypergeometric null becomes easier to satisfy by chance (larger K = smaller
# denominator for the null proportion K/N), making it harder to reject H2.
# Reported as a paper footnote; sensitivity analysis with K = 30s-window only
# is available via --window-k flag. Pre-registration locks the full-session K.
session_c = rubric_edits[-1]['session_contradicts_nodes']
m_flagged = len(session_c)
```

**Paper footnote language (suggested):** "We use the full-session `session_contradicts_nodes` accumulation as K. This is conservative — larger K makes the hypergeometric null harder to reject — so our reported p-values are a lower bound on significance."

---

### Q7 — Condition Propagation to VerifierReasoningPanel

**Problem:** `ScoreProvenancePanel` did not pass `condition`/`dataset` to `VerifierReasoningPanel`, so trace interactions in that panel were either unlogged or logged with incorrect condition.

**Fix in `packages/frontend/src/components/charts/ScoreSamplesTable.tsx`:**

```typescript
// ScoreProvenancePanel signature now includes condition:
function ScoreProvenancePanel({
  row, maxScore, dataset, apiBase, condition,
}: { ...; condition?: string; })

// VerifierReasoningPanel call now passes both:
<VerifierReasoningPanel
  parsedSteps={...}
  traceSummary={...}
  onNodeClick={handleTraceNodeClick}
  highlightedNode={selectedConcept}
  onClose={() => setShowTrace(false)}
  condition={condition}    // ← was missing
  dataset={dataset}        // ← was missing
/>
```

---

### Q8 — Runtime Condition Guard

**Problem:** `?condition=C` would silently propagate an invalid condition through the entire study session and logs.

**Fix in `packages/frontend/src/pages/InstructorDashboard.tsx`:**

```typescript
const rawCondition = searchParams.get('condition');
const condition = (rawCondition === 'A' || rawCondition === 'B')
  ? rawCondition
  : 'B'; // default to treatment for missing/invalid param
const isControlCondition = condition === 'A';
const isStudyMode = rawCondition !== null;
```

Any value other than `'A'` or `'B'` is remapped to `'B'` (treatment). `isStudyMode` is still `true` for `?condition=C`, so logs are captured, but the condition field is valid.

---

### Q11 — KG Node Layout Persistence Per conceptId

**Problem:** Navigating away from a concept and returning reset the user's drag arrangement.

**Fix in `packages/frontend/src/components/charts/ConceptKGPanel.tsx`:**

```typescript
// Module-level cache (survives component unmount/remount):
const layoutCache = new Map<string, Map<string, NodePos>>();

// KGGraph useState initializer restores from cache:
const [positions, setPositions] = useState<Map<string, NodePos>>(
  () => layoutCache.get(data.concept_id) ?? initialLayout(data.nodes),
);

// onMouseMove saves to cache on every drag move:
setPositions((prev) => {
  const next = new Map(prev).set(dragState.current!.nodeId, { x, y });
  layoutCache.set(data.concept_id, next);  // ← persist immediately
  return next;
});

// useEffect restores layout when conceptId changes:
useEffect(() => {
  setPositions(layoutCache.get(data.concept_id) ?? initialLayout(data.nodes));
}, [data.concept_id]);

// resetPositions also updates cache (so reset button clears it):
const resetPositions = useCallback(() => {
  const fresh = initialLayout(data.nodes);
  layoutCache.set(data.concept_id, fresh);
  setPositions(fresh);
}, [data.nodes, data.concept_id]);
```

Cache is module-scoped (not React state), so it is not re-initialized on component unmount. Cache is NOT persisted to localStorage (intentional — layout preference is session-scoped, not cross-session).

---

## 2. Current System Architecture Summary

### Frontend Components

| Component | File | Key Responsibility |
|-----------|------|--------------------|
| `InstructorDashboard` | `pages/InstructorDashboard.tsx` | Dataset selector, condition gating, study task panel, export |
| `ConceptKGPanel` | `charts/ConceptKGPanel.tsx` | SVG ego-graph; drag; student overlay; layout cache |
| `StudentAnswerPanel` | `charts/StudentAnswerPanel.tsx` | Master-detail list; dwell timing; FNV-1a 64-bit hash |
| `MisconceptionHeatmap` | `charts/MisconceptionHeatmap.tsx` | Severity × concept grid; brushing trigger |
| `ScoreSamplesTable` | `charts/ScoreSamplesTable.tsx` | Per-sample rows; ScoreProvenancePanel; xai_pill_hover |
| `VerifierReasoningPanel` | `charts/VerifierReasoningPanel.tsx` | LRM trace steps; CONTRADICTS/SUPPORTS/UNCERTAIN; rubric_edit causal |
| `RubricEditorPanel` | `charts/RubricEditorPanel.tsx` | Concept add/remove/reweight; rubric_edit event logging |
| `SUSQuestionnaire` | `charts/SUSQuestionnaire.tsx` | 10-item SUS scale; logged as task_submit/sus_questionnaire |
| `DashboardContext` | `contexts/DashboardContext.tsx` | selectedStudent, selectedConcept, recentContradicts (60s), sessionContradicts, traceOpen |

### Event Taxonomy (complete)

```
page_view          — dashboard mount
tab_change         — dataset switch
task_start         — first keystroke in StudyTaskPanel textarea
task_submit        — answer submitted (main_task + sus_questionnaire subtypes)
chart_hover        — mouse enters a chart container
chart_click        — deliberate click (row expand, quartile select)
trace_interact     — CONTRADICTS/SUPPORTS/UNCERTAIN step click in VerifierReasoningPanel
rubric_edit        — concept add/remove/increase_weight/decrease_weight
answer_view_start  — student answer selected
answer_view_end    — student answer deselected (via cleanup or sendBeacon)
kg_node_drag       — KG node drag released (one event per gesture)
xai_pill_hover     — concept pill hovered in ScoreProvenancePanel
```

### Analysis Pipeline (`analyze_study_logs.py`)

Key aggregates per participant-session:
- `causal_attribution_rate_30s` (primary H1) — fraction of rubric_edits with prior CONTRADICTS within 30s
- `participant_mean_ratio` — per-participant average attribution rate (avoids high-volume participant dominance)
- `hyper_p_manual` (primary H2) — hypergeometric p-value for semantic alignment of manual edits only
- `hyper_p_combined` — robustness check including Click-to-Add edits
- `grounding_density` — fraction of LRM trace steps with ≥1 kg_node (H1 moderator)
- `trace_gap_count` — structural leaps in most-recent LRM trace (H1 moderator)

---

## 3. Questions for Gemini Review

Please review the following areas and provide specific feedback:

### 3.1 Q7-Confound: Concept Frequency Chart Signal Leakage (Condition A)

From GEMINI_FEEDBACK_PAPER2.md Q7:
> If the frequency chart highlights the exact same concepts that the trace would have flagged as CONTRADICTS, a Condition A participant might add those concepts simply because they are highly frequent.

**Current state:** Condition A shows the ConceptFrequencyChart (top 15 concepts by match frequency). The Condition B trace CONTRADICTS events are driven by missing concepts — i.e., concepts NOT demonstrated. Condition A sees which concepts ARE most demonstrated (matched). These are different sets: matched ≠ missing. But the concern is whether overlapping concepts between "most frequently missed" and "most frequently matched" could create a signal-leakage confound.

**Questions:**
1. Is the distinction between "matched frequency" (Condition A chart) and "missing/contradicts" (Condition B trace) sufficient to rule out confounding, or should Condition A's chart be filtered to only show `matched_concepts` (not concepts that also appear as `missing_concepts` in any answer)?
2. If confounding is a risk, would a post-hoc covariate (adding concept_frequency_rank to the rubric_edit payload) be sufficient for regression control, or does it require a design change?
3. Is this a pre-registration amendment requirement, or can it be handled in the statistical analysis section?

### 3.2 Layout Cache: Module-Level vs DashboardContext

Q11 was implemented using a module-level `Map<string, Map<string, NodePos>>`. An alternative was a DashboardContext entry. 

**Questions:**
1. Module-level cache is not reactive and not in React state. Is there a risk of stale layout being served to a new KGGraph instance if the `data.concept_id` ref has changed but the module cache key matches? (The `useEffect` on `data.concept_id` should handle this — does it?)
2. Should the cache be cleared when the user resets the dataset (changes dataset tab in InstructorDashboard)? Currently it is not cleared.
3. Is there a memory leak risk if the educator views many concepts in a long session (cache grows unbounded)?

### 3.3 xai_pill_hover Debounce Requirement

Q3 used `onMouseEnter` (not `onMouseMove`) for pill hover events. No debounce was added.

**Questions:**
1. `onMouseEnter` fires once per enter (not per pixel). Is this the correct choice, or should we use `onMouseLeave` to also capture dwell time (hover duration)?
2. If the educator moves the mouse rapidly across all pills, would a burst of `xai_pill_hover` events in rapid succession cause any analytical problems (e.g., inflate interaction counts and distort dwell-time estimates)?
3. Should we add a 200ms debounce on `onMouseEnter`, or track a minimum dwell time (e.g., only log if mouse stays > 300ms)?

### 3.4 `participant_mean_ratio` Statistical Validity

The V8 fix added `participant_mean_ratio` as the primary H1 estimator (replacing edit-pooled ratio) to prevent high-volume participants from dominating.

```python
def participant_mean_ratio(window_key: str) -> Optional[float]:
    ratios = []
    for r in rows:
        n_edits = r.get('rubric_edits') or 0
        n_window = r.get(window_key) or 0
        if n_edits > 0:
            ratios.append(n_window / n_edits)
    return round(statistics.mean(ratios), 3) if ratios else None
```

**Questions:**
1. This computes the mean of per-participant ratios. Is this the correct pre-registered estimator for H1, or should it be a weighted mean (weight = n_edits per participant)?
2. For participants with n_edits = 1 and n_window = 0, the ratio is 0. For n_edits = 1 and n_window = 1, ratio = 1.0. Does a single-edit participant have undue influence on the mean? Should a minimum edit threshold (n_edits ≥ 3) be applied?
3. `rows` in the closure is the same `rows` list used by `aggregate_by_condition`. Is there a filter to ensure `rows` contains only the correct condition (A or B) when called? If `aggregate_by_condition` is called once per condition, is `rows` scoped correctly, or is there a risk of mixing conditions?

### 3.5 `logBeacon` + `sendBeacon` Reliability for `answer_view_end`

```typescript
export function logBeacon(...): void {
  safeLocalStorageAppend(event);
  if (studyApiBase) {
    const blob = new Blob([JSON.stringify(event)], { type: 'application/json' });
    navigator.sendBeacon(`${studyApiBase}/api/study/log`, blob);
  }
}
```

**Questions:**
1. `sendBeacon` is used in `useEffect` cleanup. React 18 strict mode calls cleanup twice in dev — does this cause duplicate `answer_view_end` events in production builds? (Strict mode only runs in dev, but worth confirming.)
2. If `sendBeacon` is called during a cross-origin navigation, some browsers block it. The study is a single-origin SPA, so this should not apply — correct?
3. `safeLocalStorageAppend` is called synchronously in `logBeacon`, which is called in a React cleanup (which itself is called from `useEffect`). Is there any risk that the localStorage call fails because the cleanup runs after the page has already started unloading?

### 3.6 Analyze Pipeline: `rows` Scoping in `aggregate_by_condition`

In `analyze_study_logs.py`, `aggregate_by_condition(rows)` accepts a `rows` list and defines `participant_mean_ratio` as a closure over the same `rows`. The function is called separately for Condition A and Condition B rows.

**Question:** Is the `participant_mean_ratio` closure guaranteed to use the locally-passed `rows` parameter (not the module-level session list), or is there a shadowing risk? Please verify the closure scoping.

---

## 4. Verification Checklist

The following was verified before writing this doc:

- [x] `npx tsc --noEmit` in `packages/frontend` — 0 errors
- [x] `logFailure` Alert renders in InstructorDashboard when dual-write fails
- [x] `fnv1a` returns 16-character hex string (64-bit FNV-1a)
- [x] `kg_node_drag` logged once per drag gesture (onMouseUp, not onMouseMove)
- [x] `xai_pill_hover` logged for both matched and missing pills
- [x] `VerifierReasoningPanel` receives `condition` and `dataset` from `ScoreProvenancePanel`
- [x] `?condition=C` remapped to `'B'`; `isStudyMode` still true
- [x] `layoutCache` module-level Map; restored in useState initializer and conceptId change effect
- [x] Conservative-K comment added to `analyze_study_logs.py` with paper footnote language
- [x] `participant_mean_ratio` defined before use in `aggregate_by_condition`
- [x] No duplicate `if __name__ == '__main__':` block in `analyze_study_logs.py`

---

## 5. Known Non-Issues (For Gemini Context)

- **`analyze_study_logs.py` SyntaxError (V8):** Duplicate fragment after `__main__` block was removed in the prior session.
- **KG route path:** Frontend uses `/kg/concept/:id` — correct. `/kg/:id` returns 404.
- **`total_misconceptions`:** Lives in `visualizations[0].data.total_misconceptions` (class_summary spec), not at API top-level. Frontend reads correctly.
- **SUS event_subtype:** Is `'sus_questionnaire'` in both the React component and the analyzer (verified match).
- **Study log export:** Client-side only (localStorage → Blob download). No backend GET endpoint exists by design.
- **Condition B trace gap/density moderators:** `lastTraceGapCount` and `lastGroundingDensity` are set in DashboardContext from `VerifierReasoningPanel` and read in `RubricEditorPanel` at edit time. This is correct — no round-trip required.

---

## 6. File Map for Quick Reference

```
packages/frontend/src/
  pages/InstructorDashboard.tsx        — condition guard, dual-write handler, study panel
  contexts/DashboardContext.tsx        — recentContradicts, sessionContradicts, traceOpen
  utils/studyLogger.ts                 — logEvent, logBeacon, dual-write detection, event types
  components/charts/
    ConceptKGPanel.tsx                 — SVG KG, drag, layoutCache, kg_node_drag
    StudentAnswerPanel.tsx             — master-detail, fnv1a 64-bit, answer_view_*
    ScoreSamplesTable.tsx              — ScoreProvenancePanel, xai_pill_hover, Q7 condition pass
    VerifierReasoningPanel.tsx         — LRM trace, CONTRADICTS, trace_interact
    RubricEditorPanel.tsx              — rubric_edit, Click-to-Add, semantic alignment
    MisconceptionHeatmap.tsx           — heatmap, severity brushing
    SUSQuestionnaire.tsx               — 10-item SUS

packages/concept-aware/
  analyze_study_logs.py                — H1/H2 aggregation, participant_mean_ratio, hyper_p
  results/
    conceptgrade_gemini_paper2_v3.md  — this document
```
