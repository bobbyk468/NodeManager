# ConceptGrade Paper 2 — End-to-End Code & Feature Review for Gemini

**Context:** This document is for an independent code review of the ConceptGrade IEEE VIS 2027 VAST Paper 2 system. Please review ALL numbered questions and flag any correctness, IRB validity, or publication-readiness issues.

The system is a full-stack Visual Analytics dashboard for AI-assisted grading, with a 2-condition (A/B) controlled user study baked in. Paper 2 claims:
- **H1 (temporal):** Educators who see CONTRADICTS trace signals are more likely to make rubric edits within 30 s of the interaction (primary window; 15 s / 60 s reported as sensitivity checks).
- **H2 (semantic):** Rubric edits that follow CONTRADICTS interactions align semantically with the flagged concept more than chance (hypergeometric null model, manual-edits only).

**Stack:** NestJS backend · React/MUI frontend · Python analysis pipeline (analyze_study_logs.py)

---

## Section 1 — Event Logging Architecture

### Q1: Is the dual-write (localStorage + POST) setup correct for IRB durability?

`studyLogger.ts` (the source of truth for all event data):

```typescript
// studyLogger.ts:179-211
export function logEvent<T extends Record<string, unknown>>(
  condition: string,
  dataset: string,
  event_type: StudyEventType,
  payload: T = {} as T,
): void {
  const event: StudyEvent = {
    session_id: SESSION_ID,
    condition: condition as StudyCondition,
    dataset,
    event_type,
    timestamp_ms: Date.now(),
    elapsed_ms: Date.now() - SESSION_START,
    payload,
  };

  safeLocalStorageAppend(event);   // primary: survives JS error

  if (studyApiBase) {
    fetch(`${studyApiBase}/api/study/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
    }).catch(() => {});            // backend: fire-and-forget, never throws
  }
}
```

`logBeacon` is used in React useEffect cleanup paths (answer_view_end during tab unload) to guarantee delivery via `navigator.sendBeacon()`:

```typescript
// studyLogger.ts:227-255
export function logBeacon<T extends Record<string, unknown>>(
  condition: string, dataset: string,
  event_type: StudyEventType, payload: T = {} as T,
): void {
  const event = { session_id: SESSION_ID, condition, dataset, event_type,
    timestamp_ms: Date.now(), elapsed_ms: Date.now() - SESSION_START, payload };
  safeLocalStorageAppend(event);
  if (studyApiBase) {
    const blob = new Blob([JSON.stringify(event)], { type: 'application/json' });
    navigator.sendBeacon(`${studyApiBase}/api/study/log`, blob);
  }
}
```

localStorage quota exhaustion is handled with 20%-trim fallback (studyLogger.ts:153-164). Backend write path (study.service.ts) uses per-session JSONL files, race-safe append.

**Question for Gemini:** Is the dual-write design sufficient for IRB data integrity? Any edge case where both writes can fail silently?

---

### Q2: FERPA compliance — is the FNV-1a hash adequate?

Raw student answer text is never included in any log event. Only a 32-bit FNV-1a hash is transmitted:

```typescript
// StudentAnswerPanel.tsx:49-57
function fnv1a(text: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, '0');
}
```

Used in answer_view_start and answer_view_end payloads as `answer_content_hash`. Raw text is never logged anywhere in the system.

**Question for Gemini:** Is FNV-1a 32-bit sufficient for FERPA fingerprinting? Are there collision risks that would undermine the IRB claim that "the same answer was shown consistently across participants"?

---

### Q3: Are ALL study-relevant event types logged?

Event types defined in `studyLogger.ts`:
- `page_view` — on mount (InstructorDashboard.tsx:286)
- `tab_change` — on dataset switch (InstructorDashboard.tsx:273)
- `task_start` — on first textarea focus (StudyTaskPanel handleFocus)
- `task_submit` — on main task submit, SUS submit, rubric review submit (3 subtypes: `main_task`, `sus_questionnaire`, `rubric_review`)
- `chart_hover` — on chart container mouse enter (all chart components)
- `chart_click` — on deliberate in-chart interactions (quartile select, row expand)
- `trace_interact` — on EVERY step click (SUPPORTS/CONTRADICTS/UNCERTAIN) in VerifierReasoningPanel
- `rubric_edit` — on every rubric concept add/remove/reweight in RubricEditorPanel
- `answer_view_start` / `answer_view_end` — on student answer select/deselect, via beacon

**Critical path verified:** `trace_interact` is logged in VerifierReasoningPanel.tsx for both step clicks and node pill clicks (both fixed in v27):

```typescript
// VerifierReasoningPanel.tsx:430-461
const handleSelectStep = useCallback(
  (stepId: number) => {
    const nextId = selectedStepId === stepId ? null : stepId;
    setSelectedStepId(nextId);
    if (nextId !== null) {
      const step = parsedSteps.find((s) => s.step_id === nextId);
      if (step) {
        logEvent(condition, dataset, 'trace_interact', {
          classification: step.classification,
          node_id: step.kg_nodes[0] ?? null,
          step_id: step.step_id,
        });
        if (step.classification === 'CONTRADICTS' && step.kg_nodes.length > 0) {
          pushContradicts(step.kg_nodes[0]);
        }
        if (onNodeClick && step.kg_nodes.length > 0) onNodeClick(step.kg_nodes[0]);
      }
    }
  },
  [selectedStepId, parsedSteps, onNodeClick, pushContradicts, condition, dataset],
);

const handleNodePillClick = useCallback(
  (nodeId: string) => {
    onNodeClick?.(nodeId);
    const step = parsedSteps.find(s =>
      s.kg_nodes.includes(nodeId) && s.classification === 'CONTRADICTS');
    if (step) {
      logEvent(condition, dataset, 'trace_interact', {
        classification: 'CONTRADICTS',
        node_id: nodeId,
        step_id: step.step_id,
      });
      pushContradicts(nodeId);
    }
  },
  [onNodeClick, parsedSteps, pushContradicts, condition, dataset],
);
```

**Question for Gemini:** Are there any user interaction paths in the dashboard that should generate a study event but don't? E.g., KG node drag, concept pill hover in XAI provenance panel?

---

## Section 2 — H1 Temporal Causal Attribution

### Q4: Is the rolling contradicts window implemented correctly?

The CONTRADICTS interaction window is managed in `DashboardContext.tsx` using a reducer:

```typescript
// DashboardContext.tsx:156-165
case 'PUSH_CONTRADICTS': {
  const now = Date.now();
  const pruned = state.recentContradicts.filter(
    e => now - e.timestamp_ms < ROLLING_WINDOW_MS,  // ROLLING_WINDOW_MS = 60_000
  );
  return {
    ...state,
    recentContradicts: [...pruned, { nodeId: action.nodeId, timestamp_ms: now }],
  };
}
```

The rolling window (60 s) is pruned on every new push. RubricEditorPanel reads it and filters tighter windows at the moment of each edit:

```typescript
// RubricEditorPanel.tsx:156-160
const w60 = recentContradicts.filter(e => now - e.timestamp_ms <= 60_000);
const w30 = w60.filter(e => now - e.timestamp_ms <= 30_000);
const w15 = w30.filter(e => now - e.timestamp_ms <= 15_000);
```

The permanent session accumulator (`sessionContradictsNodes`) is maintained separately in InstructorDashboard.tsx using a ref to track already-seen timestamps and never re-add duplicates:

```typescript
// InstructorDashboard.tsx:220-230
const seenContradictTimestamps = React.useRef(new Set<number>());
React.useEffect(() => {
  for (const entry of recentContradicts) {
    if (!seenContradictTimestamps.current.has(entry.timestamp_ms)) {
      seenContradictTimestamps.current.add(entry.timestamp_ms);
      setSessionContradictsNodes(prev =>
        prev.includes(entry.nodeId) ? prev : [...prev, entry.nodeId],
      );
    }
  }
}, [recentContradicts]);
```

**Question for Gemini:** Is there a time-warp risk if `Date.now()` is called at different moments in the PUSH vs the filter? Could a rubric edit that arrives 1 ms after a push window expiry accidentally fall outside the 30 s window?

---

### Q5: Is H1 causal attribution rate computed correctly in the analysis?

`analyze_study_logs.py` — per-session metrics:

```python
# analyze_study_logs.py:282-285
n_within_15s = sum(1 for e in rubric_edits if e['within_15s'])
n_within_30s = sum(1 for e in rubric_edits if e['within_30s'])
n_within_60s = sum(1 for e in rubric_edits if e['within_60s'])
```

Condition-level aggregate (primary H1 metric) — **FIXED V8: participant-mean estimator**:

```python
# analyze_study_logs.py (aggregate_by_condition)
def participant_mean_ratio(window_key: str) -> Optional[float]:
    """Per-participant ratio: within-window edits / total edits; averaged across participants.
    Equal-weighting ensures no single high-volume participant dominates the H1 rate.
    Only includes participants who made at least one rubric edit (others have no signal)."""
    ratios = []
    for r in rows:
        n_edits = r.get('rubric_edits') or 0
        n_window = r.get(window_key) or 0
        if n_edits > 0:
            ratios.append(n_window / n_edits)
    return round(statistics.mean(ratios), 3) if ratios else None

'causal_attribution_rate_30s': participant_mean_ratio('rubric_edits_within_30s'),
```

**Verified:** Two-participant test (8 edits / 6 within-30s vs 2 edits / 1 within-30s):
- Old pooled: (6+1)/(8+2) = **0.700** — dominated by high-volume participant
- New participant-mean: mean(6/8, 1/2) = **0.625** — equal weighting ✅

**Status: RESOLVED (V8)**

---

## Section 3 — H2 Semantic Concept Alignment

### Q6: Is the hypergeometric null model split correctly (manual vs CTA)?

Click-to-Add (CTA) edits always align semantically by construction — the educator is clicking a chip that IS the CONTRADICTS node. Including CTA in k would inflate the alignment rate. The fix splits into `hyper_p_manual` (pre-registered primary) and `hyper_p_combined` (robustness):

```python
# analyze_study_logs.py:323-351
hyper_p_manual: Optional[float] = None    # H2 PRIMARY — manual edits only
hyper_p_combined: Optional[float] = None  # robustness — all edits incl. Click-to-Add
if n_edits > 0 and rubric_edits:
    session_c = rubric_edits[-1]['session_contradicts_nodes']
    m_flagged = len(session_c)
    rubric_sizes = [e['rubric_size'] for e in rubric_edits if e.get('rubric_size', 0) > 0]
    n_rubric = int(statistics.median(rubric_sizes)) if rubric_sizes else max(m_flagged, CONCEPT_FREQUENCY_MAX_BARS)
    N_eff = max(n_rubric, m_flagged)
    if m_flagged > 0 and n_rubric > 0:
        if n_manual_edits > 0:
            hyper_p_manual = _hypergeometric_p(
                k=n_semantic_aligned_manual,
                N=N_eff, K=m_flagged, n=n_manual_edits,
            )
        hyper_p_combined = _hypergeometric_p(
            k=n_semantic_aligned,
            N=N_eff, K=m_flagged, n=n_edits,
        )
```

The hypergeometric p-value function:

```python
# analyze_study_logs.py:75-100
def _hypergeometric_p(k: int, N: int, K: int, n: int) -> Optional[float]:
    # P(X >= k) where X ~ Hypergeometric(N, K, n)
    # N = effective rubric size, K = CONTRADICTS flagged concepts,
    # n = draws (edits), k = successes (aligned edits)
```

Numeric validation: `_hypergeometric_p(k=3, N=15, K=5, n=4)` → 0.0769. Edge cases: `n=0` → 1.0, `k=0` → 1.0. ✓

**Question for Gemini:** Using `session_contradicts_nodes` from the LAST rubric edit's payload to define K — is this correct? Could earlier edits in the same session have had a different (smaller) set of session_contradicts_nodes, causing K to be over-estimated for those edits?

---

## Section 4 — Condition A/B Gating

### Q7: Is Condition A isolation correct?

Condition A (control) should see summary metrics only — no charts, no KG, no trace panel.

Dashboard gating (InstructorDashboard.tsx):
- `isControlCondition = condition === 'A'`
- Summary metric cards (7) render in BOTH conditions
- Charts section: `{!isControlCondition && (<> ... </>)}` — entire charts block is absent in A
- Study task panel: `{isStudyMode && ...}` — shown in both (it's the task, not the tool)
- Rubric editor + SUS: `{isStudyMode && taskSubmitted && ...}` — shown in both after task submit
- Log export button: `{isStudyMode && ...}` — shown in both

Benchmark seed filtering for Condition A (StudentAnswerPanel.tsx):

```typescript
// StudentAnswerPanel.tsx (answer_view_start payload)
benchmark_case: (() => {
  const bc = getBenchmarkCase(answer.id);
  if (!bc) return undefined;
  // Condition A: hide trace-only traps (fluent_hallucination, partial_credit_needle)
  // so A participants are not penalized for missing KG-panel signals they don't have.
  if (studyCondition === 'A' &&
      (bc === 'fluent_hallucination' || bc === 'partial_credit_needle')) {
    return undefined;
  }
  return bc;
})(),
```

**Question for Gemini:** In Condition A, the RubricEditorPanel is still shown after task submit. Condition A educators edit the rubric without having seen any trace — this is the "baseline" editing behavior we compare against. Is this experimental design sound? Could an educator in Condition A accidentally discover trace signals through the rubric editor UI itself (e.g., if the concept frequency chart or any summary signal hints at the same concepts the trace would flag)?

---

### Q8: Is the `condition` prop threaded correctly to all logging call sites?

Chain from URL param to event log:
1. `useSearchParams().get('condition')` → `condition: string` in InstructorDashboard
2. Passed to `<StudyTaskPanel condition={condition} ...>` → logEvent calls use it
3. Passed to all chart components via `condition={condition}` prop
4. Passed to `<ScoreSamplesTable condition={condition} ...>`
5. Threaded to `<ScoreProvenancePanel condition={condition} ...>` (fixed v27)
6. Threaded to `<VerifierReasoningPanel condition={condition} dataset={dataset} ...>` (fixed v27)
7. Passed to `<RubricEditorPanel condition={condition as 'A' | 'B'} ...>`

**Question for Gemini:** The `condition` string from URL is cast to `StudyCondition` as `condition as StudyCondition`. If a participant visits `/dashboard?condition=C` (typo), the cast silently accepts it and logs `condition: 'C'`. Should there be a runtime guard that coerces unknown condition values to 'B' (treatment) or throws an error?

---

## Section 5 — Bidirectional Brushing (Linking)

### Q9: What brushing interactions are implemented?

All brushing is mediated through `DashboardContext` (useReducer-based shared state):

| Interaction | Source | Target |
|-------------|--------|--------|
| Heatmap cell click | MisconceptionHeatmap | StudentAnswerPanel (filtered by concept + severity) |
| Radar quartile click | StudentRadarChart | StudentAnswerPanel (filtered by score quartile) |
| Answer row expand | ScoreSamplesTable | VerifierReasoningPanel (trace for that sample) |
| Step click in trace | VerifierReasoningPanel | ConceptKGPanel (highlight node via `selectedConcept`) |
| Node pill click | VerifierReasoningPanel | ConceptKGPanel (same path) |
| KG "Show KG" button | StudentAnswerPanel | ConceptKGPanel (mounted for selected concept) |
| Concept matched click | StudentAnswerPanel → XAI | DashboardContext.selectConcept → highlights heatmap cell |

StudentAnswerPanel receives `selectedQuartileIndex` from DashboardContext and filters its answer list:

```typescript
// StudentAnswerPanel — filter logic
const filtered = useMemo(() => {
  if (selectedQuartileIndex === null) return sortedAnswers;
  // quartile boundaries from StudentRadarChart spec
  return sortedAnswers.filter(a =>
    inQuartile(a.c5_score, selectedQuartileIndex, quartileBounds)
  );
}, [sortedAnswers, selectedQuartileIndex, quartileBounds]);
```

**FIXED V7:** AbortController integrated into the KG fetch `useEffect`:

```typescript
// ConceptKGPanel.tsx:278-286
useEffect(() => {
  setLoading(true); setError(null); setData(null);
  const abortController = new AbortController();
  fetch(`${apiBase}/api/visualization/datasets/${dataset}/kg/concept/${conceptId}`,
    { signal: abortController.signal })
    .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
    .then((d) => { setData(d); setLoading(false); })
    .catch((e: Error) => {
      if (e.name !== 'AbortError') { setError(e.message); setLoading(false); }
    });
  return () => abortController.abort();  // cancels in-flight request on conceptId change
}, [dataset, conceptId, apiBase]);
```

Rapid heatmap clicks no longer race — each `conceptId` change cancels the previous fetch before issuing a new one. `AbortError` is swallowed silently, preserving the loading state for the current request.

**Status: RESOLVED (V7)**

---

## Section 6 — Backend API Correctness

### Q10: Are all 9 visualization specs returned correctly?

API verified: `GET /api/visualization/datasets/digiklausur` returns:

```json
{
  "dataset": "digiklausur",
  "n": 646,
  "wilcoxon_p": 0.0489,
  "mae_reduction_pct": 4.9,
  "visualizations": [
    "class_summary", "blooms_dist", "solo_dist", "score_comparison",
    "concept_frequency", "chain_coverage_dist", "score_scatter",
    "student_radar", "misconception_heatmap"
  ]
}
```

`total_misconceptions` is in `visualizations[0].data.total_misconceptions` (class_summary spec), not at top-level. Frontend reads it via `summary?.data.total_misconceptions`. Verified: Mohler returns `total_misconceptions: 20` (answers with zero matched concepts).

### Q11: KG subgraph field names

API returns edges as `{ from, to, type, weight, description }`. Frontend types:

```typescript
// visualization.types.ts:81-85
export interface KGEdge {
  from: string;
  to: string;
  type: string;
  weight: number;
  description: string;
}
```

ConceptKGPanel renders `edge.from` / `edge.to` — field names match API. ✓

Node student-state overlay (matched/missing) is applied CLIENT-SIDE from DashboardContext, not from API response. API returns `is_expected` and `is_central` on nodes; the `matched` coloring comes from `matchedSet` (Set of concept IDs from the last selectStudent() call).

**Question for Gemini:** KG node positions are computed using a circular initial layout (initialLayout function, ConceptKGPanel.tsx). The layout is not persisted — every time ConceptKGPanel mounts (i.e., every concept selection), the graph resets. Should the layout be memoized per conceptId to preserve a user's drag rearrangements when they re-select the same concept?

---

## Section 7 — Analysis Pipeline Correctness

### Q12: Does `write_csv` produce consistent fieldnames across heterogeneous sessions?

`write_csv` uses an insertion-ordered dict union over all sessions, then sorted:

```python
# analyze_study_logs.py:813-820
all_keys: dict[str, None] = {}
for m in session_metrics:
    for k in m.keys():
        if k not in _NON_SCALAR_KEYS:
            all_keys[k] = None
fieldnames = sorted(all_keys)
writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore', restval='')
```

`restval=''` fills in empty string (not `None`) for sessions that lack a field (e.g., sessions with no rubric edits will have `concept_alignment_hyper_p = ''` rather than `"None"`). ✓

### Q13: Is the `write_edits_csv` per-edit row correctly joined with session metadata?

```python
# analyze_study_logs.py:834-842
for m in session_metrics:
    for edit in m.get('raw_edits', []):
        rows.append({
            'session_id': m['session_id'],
            'condition':  m['condition'],
            **{
                k: ('|'.join(str(x) for x in v) if v else '') if isinstance(v, list) else v
                for k, v in edit.items()
                if k != 'session_id' and not isinstance(v, dict)
            },
        })
```

List fields (e.g., `session_contradicts_nodes`, `source_contradicts_nodes_60s`) are pipe-delimited strings in the CSV — compatible with R's `strsplit()` / Python `str.split('|')` for downstream GEE analysis.

**FIXED V6:** `write_edits_csv` now iterates all rows to compute the union of fieldnames:

```python
# analyze_study_logs.py:842-846
all_keys: dict[str, None] = {}
for r in rows:
    for k in r.keys():
        all_keys[k] = None
fieldnames = list(all_keys.keys())
writer = csv.DictWriter(f, fieldnames=fieldnames, restval='')
```

**Verified:** 10-row edits CSV — `semantic_match_node` and `semantic_match_score` both appear in header even when absent from the first edit row. ✓

**Status: RESOLVED (V6)**

---

## Section 8 — Known Issues: Resolution Status

| # | Severity | File | Issue | Status |
|---|----------|------|-------|--------|
| V1 | CONFIRMED OK | analyze_study_logs.py | SUS event_subtype `'sus_questionnaire'` matches component | ✓ |
| V2 | CONFIRMED OK | ConceptKGPanel.tsx | Edge `from`/`to` fields match API response | ✓ |
| V3 | CONFIRMED OK | analyze_study_logs.py | `hyper_p_manual` / `hyper_p_combined` split correct | ✓ |
| V4 | CONFIRMED OK | VerifierReasoningPanel.tsx | `trace_interact` logged for all step and node pill clicks | ✓ |
| V5 | CONFIRMED OK | ScoreSamplesTable.tsx | `condition` threaded through ScoreProvenancePanel → VerifierReasoningPanel | ✓ |
| V6 | **RESOLVED** | write_edits_csv | Fieldnames now union of all rows — no column misalignment | ✅ Fixed |
| V7 | **RESOLVED** | ConceptKGPanel.tsx | AbortController added — stale fetches cancelled on conceptId change | ✅ Fixed |
| V8 | **RESOLVED** | analyze_study_logs.py | H1 rate now participant-mean (not edit-pooled) via `participant_mean_ratio` | ✅ Fixed |

**Note:** V8 fix also required adding the missing `participant_mean_ratio` function definition (referenced but undefined in the user's initial fix — would have caused NameError at runtime). Added as local closure alongside `mean_of` / `std_of` in `aggregate_by_condition`.

---

## What We Need Gemini to Review (Updated)

**Priority 1 (still open — blocking for IRB/publication):**
- Q6: K over-estimation from last-edit's `session_contradicts_nodes` for earlier edits?
- Q7: Condition A RubricEditorPanel — could concept frequency chart leak trace signals?

**Priority 2 (still open — data quality):**
- Q1: Dual-write failure mode — any scenario where both localStorage and POST fail silently?
- Q3: Missing event coverage — unlogged interaction paths (KG node drag, XAI pill hover)?

**Priority 3 (still open — UX / publication polish):**
- Q2: FNV-1a 32-bit — collision risk for FERPA claim?
- Q8: Condition validation — silent accept of invalid condition strings (e.g., `?condition=C`)?
- Q11: KG layout persistence per conceptId across re-selections?

**Resolved since v2 document:**
- ✅ V6 (Q13): `write_edits_csv` fieldnames union
- ✅ V7 (Q9): AbortController on KG fetch
- ✅ V8 (Q5): Participant-mean H1 estimator

---

*Document updated: 2026-04-19. System version: v28 (V6/V7/V8 fixes applied and verified). Servers running: backend localhost:5001, frontend localhost:5173.*
