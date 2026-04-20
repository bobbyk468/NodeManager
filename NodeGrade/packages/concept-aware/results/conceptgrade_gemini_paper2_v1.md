# ConceptGrade — Paper 2 Code Review for Gemini (IEEE VIS 2027 VAST)

## Context

This review audits the Paper 2 codebase against three claimed contributions:
1. **TRM formal definitions** (Defs 1–5, locked v11)
2. **Bidirectional co-auditing interface** (DashboardContext linking & brushing)
3. **User study telemetry** (H1 temporal, H2 semantic, H-MOD moderation)

Several questions from our internal Paper 2 analysis (conceptgrade_paper2_review_v1.md)
are pre-answered below from code inspection. New questions that require your review
are flagged with **[QUESTION]**.

---

## Q1 — VerifierReasoningPanel.tsx: gap count matches TRM Definition 3 — CONFIRMED

**File:** `packages/frontend/src/components/charts/VerifierReasoningPanel.tsx`

Definition 3 (locked v11): Nᵢ ≠ ∅ AND Nᵢ₊₁ ≠ ∅ AND Nᵢ ∩ Nᵢ₊₁ = ∅.

**Implementation:**
```typescript
function hasTopologicalGap(stepA: ParsedStep, stepB: ParsedStep): boolean {
  if (stepA.kg_nodes.length === 0 || stepB.kg_nodes.length === 0) return false;
  const nodesA = new Set(stepA.kg_nodes);
  return !stepB.kg_nodes.some(n => nodesA.has(n));
}

const topologicalGapCount = useMemo(() => {
  let count = 0;
  for (let i = 1; i < parsedSteps.length; i++) {
    if (hasTopologicalGap(parsedSteps[i - 1], parsedSteps[i])) count++;
  }
  return count;
}, [parsedSteps]);
```

Correct: ungrounded steps (`kg_nodes.length === 0`) return `false` — they are NOT
counted as gaps. The intersection is on `kg_nodes` string arrays. Matches Def 3 exactly.

**Status: No change required.**

---

## Q2 — VerifierReasoningPanel.tsx: grounding density matches TRM Definition 5 — CONFIRMED

**File:** `packages/frontend/src/components/charts/VerifierReasoningPanel.tsx`

Definition 5: `|{i : Nᵢ ≠ ∅}| / n ∈ [0, 1]` where n = total steps.

**Implementation:**
```typescript
const groundingDensity = useMemo(() => {
  if (parsedSteps.length === 0) return 0;
  const grounded = parsedSteps.filter(s => s.kg_nodes.length > 0).length;
  return grounded / parsedSteps.length;  // denominator = ALL steps including UNCERTAIN
}, [parsedSteps]);
```

Denominator is `parsedSteps.length` (all steps including UNCERTAIN). Matches Def 5.

**Status: No change required.**

---

## Q3 — VerifierReasoningPanel.tsx: reverse brushing (KG→Trace) — CONFIRMED IMPLEMENTED

**File:** `packages/frontend/src/components/charts/VerifierReasoningPanel.tsx`

**Implementation:**
```typescript
// When a KG node is highlighted externally (e.g. user clicked in ConceptKGPanel),
// dim steps that do NOT reference that node (bidirectional brushing receiving end).
const hasNodeFilter = Boolean(highlightedNode);
const filteredStepIds = hasNodeFilter
  ? new Set(parsedSteps.filter((s) => s.kg_nodes.includes(highlightedNode!))
      .map((s) => s.step_id))
  : null;
// ...
isFiltered={filteredStepIds !== null && !filteredStepIds.has(step.step_id)}
```

KG→Trace direction is live: clicking a node in ConceptKGPanel passes `highlightedNode`
to VerifierReasoningPanel, which dims all non-matching steps. The "bidirectional" VIS
claim is substantiated.

**Status: No change required.**

---

## Q4 — InstructorDashboard.tsx: sessionContradictsNodes is a permanent accumulator — CONFIRMED

**File:** `packages/frontend/src/pages/InstructorDashboard.tsx`

**Implementation:**
```typescript
const [sessionContradictsNodes, setSessionContradictsNodes] = useState<string[]>([]);
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

`sessionContradictsNodes` is a permanent accumulator. It mirrors new entries from
the rolling `recentContradicts` window using `seenContradictTimestamps` to avoid
double-counting. Old entries falling out of the 60-second window do NOT remove from
`sessionContradictsNodes`. The two arrays are correctly separate:

- `recentContradicts` (rolling 60 s) → used by `RubricEditorPanel` for `within_15s/30s/60s`
- `sessionContradictsNodes` (permanent) → used for semantic alignment check + chip strip

Condition B race concern is not present: even if an educator goes > 60 s without
trace interaction, `sessionContradictsNodes` retains all prior nodes.

**Status: No change required.**

---

## Q5 — study.service.ts: per-session JSONL, race-safe — CONFIRMED

**File:** `packages/backend/src/study/study.service.ts`

**Implementation:**
```typescript
const safeName = sessionId.replace(/[^a-zA-Z0-9-_]/g, '_');
const logPath = path.join(LOGS_DIR, `${safeName}.jsonl`);
try {
  await appendFile(logPath, JSON.stringify(event) + '\n', 'utf8');
  return { ok: true };
} catch (e) {
  return { ok: false, error: msg };  // never throws 5xx to participant
}
```

Per-session JSONL confirmed. Each participant writes to their own `{session_id}.jsonl`
file — concurrent multi-participant writes are race-safe. Disk errors return
`ok: false` (not 5xx), so the participant session is never interrupted.

**Note:** No schema validation — any JSON body is accepted. A malformed event
(e.g., missing `session_id`) writes to `unknown.jsonl`. This is acceptable for a
controlled lab study but means `analyse_session()` must handle gracefully.

**Status: No change required.**

---

## Q6 — StudentAnswerPanel.tsx: FERPA hash confirmed, raw text absent — CONFIRMED

**File:** `packages/frontend/src/components/charts/StudentAnswerPanel.tsx`

```typescript
function fnv1a(text: string): string { /* 32-bit FNV-1a hash → 8-char hex */ }

// In answer_view_start payload:
answer_content_hash: fnv1a(answer.student_answer),
// Raw answer text is NEVER included in the log payload.
```

`fnv1a()` is defined inline and called at log time. The FERPA compliance claim is
substantiated: raw answer text never appears in any log field.

**Status: No change required.**

---

## Q7 — CRITICAL BUG: VerifierReasoningPanel.tsx: trace_interact events never logged

**File:** `packages/frontend/src/components/charts/VerifierReasoningPanel.tsx`

`analyze_study_logs.py` counts `trace_interactions` and `contradicts_interactions`
from `trace_interact` events in the JSONL log:

```python
elif etype == 'trace_interact':
    trace_interactions.append({
        'timestamp_ms': ts,
        'classification': payload.get('classification', ''),
        'node_id': payload.get('node_id', ''),
        'step_id': payload.get('step_id'),
    })
# ...
'trace_interactions':       len(trace_interactions),
'contradicts_interactions': sum(1 for t in trace_interactions if t['classification'] == 'CONTRADICTS'),
```

**The bug:** `handleSelectStep()` in `VerifierReasoningPanel` calls `pushContradicts()`
(updating the rolling window for causal attribution) but does NOT call `logEvent()`:

```typescript
const handleSelectStep = useCallback(
  (stepId: number) => {
    const nextId = selectedStepId === stepId ? null : stepId;
    setSelectedStepId(nextId);
    if (nextId !== null) {
      const step = parsedSteps.find((s) => s.step_id === nextId);
      if (step) {
        if (step.classification === 'CONTRADICTS' && step.kg_nodes.length > 0) {
          pushContradicts(step.kg_nodes[0]);  // ← rolling window updated
          // ← logEvent('trace_interact', ...) is MISSING
        }
        if (onNodeClick && step.kg_nodes.length > 0) {
          onNodeClick(step.kg_nodes[0]);
        }
      }
    }
  },
  [selectedStepId, parsedSteps, onNodeClick, pushContradicts],
);
```

**Consequence:** Every participant's JSONL log will have zero `trace_interact` events.
`analyze_study_logs.py` will output `trace_interactions: 0` and
`contradicts_interactions: 0` for all sessions, including Condition B educators
who actively engaged with the trace panel.

The `within_30s` causal window IS correctly computed (via `recentContradicts`), so
H1 results are unaffected. But the `trace_interactions` and `contradicts_interactions`
session-level metrics — which are supporting evidence for educator engagement —
will be unusable.

**[QUESTION Q7]:** Confirm the fix is to add `logEvent()` inside `handleSelectStep()`
for ALL classification types (SUPPORTS, CONTRADICTS, UNCERTAIN), not just CONTRADICTS,
so that the full trace engagement pattern is captured:

```typescript
if (step) {
  // Log ALL step clicks (SUPPORTS/CONTRADICTS/UNCERTAIN) for engagement analysis
  logEvent(condition, dataset, 'trace_interact', {
    classification: step.classification,
    node_id: step.kg_nodes[0] ?? null,
    step_id: step.step_id,
  });

  if (step.classification === 'CONTRADICTS' && step.kg_nodes.length > 0) {
    pushContradicts(step.kg_nodes[0]);
  }
  if (onNodeClick && step.kg_nodes.length > 0) {
    onNodeClick(step.kg_nodes[0]);
  }
}
```

Should `condition` and `dataset` be passed as props to `VerifierReasoningPanel`, or
is there a cleaner way to get them at the call site? Currently the component does not
receive these props.

---

## Q8 — CRITICAL BUG: analyze_study_logs.py: H2 hypergeometric k includes Click-to-Add

**File:** `packages/concept-aware/analyze_study_logs.py`, `analyse_session()`

The paper states: **H2 PRIMARY = `semantic_alignment_rate_manual`** (unprompted edits only).
Click-to-Add edits always align semantically by construction (the educator clicked
a chip that IS a CONTRADICTS node), so they must not inflate the H2 primary test.

**Current code:**
```python
n_semantic_aligned = sum(1 for e in rubric_edits if e['concept_in_contradicts_semantic'])
# ...
hyper_p = _hypergeometric_p(
    k=n_semantic_aligned,     # ← includes Click-to-Add successes
    N=max(n_rubric, m_flagged),
    K=m_flagged,
    n=n_edits,                # ← total draws (also includes Click-to-Add)
)
```

Click-to-Add edits have `interaction_source == 'click_to_add'` and
`concept_in_contradicts_semantic == True` by construction. Including them in `k`
while including them in `n` inflates the ratio `k/n` relative to the manual-only
rate, making the observed rate look closer to `K/N` (the null rate) and deflating
the p-value. But the inflation is asymmetric: a Click-to-Add session with 5 CTA
edits and 1 manual edit would have k=6, n=6 (ratio 1.0) vs manual-only k=1, n=1
— both happen to look identical here, but in a mixed session k=6, n=7 vs k=1, n=2
would give very different p-values.

**[QUESTION Q8]:** The fix is to compute `hyper_p` twice:

```python
# H2 PRIMARY — manual-only (pre-registered primary metric)
n_manual = n_manual_edits  # already computed above
n_semantic_aligned_manual = sum(
    1 for e in rubric_edits
    if e['concept_in_contradicts_semantic'] and e['interaction_source'] == 'manual'
)
if n_manual > 0 and m_flagged > 0 and n_rubric > 0:
    hyper_p_manual = _hypergeometric_p(
        k=n_semantic_aligned_manual,
        N=max(n_rubric, m_flagged),
        K=m_flagged,
        n=n_manual,
    )
else:
    hyper_p_manual = None

# H2 COMBINED — all edits (robustness check, not the primary claim)
hyper_p_combined = _hypergeometric_p(
    k=n_semantic_aligned,
    N=max(n_rubric, m_flagged),
    K=m_flagged,
    n=n_edits,
) if n_edits > 0 and m_flagged > 0 and n_rubric > 0 else None
```

Both should be returned in the session result dict and written to the CSV. The paper
reports `hyper_p_manual` as the primary H2 statistic; `hyper_p_combined` appears
in a robustness footnote.

Is there a reason the current code uses the combined `n_semantic_aligned`? Was the
manual-only split considered and deferred, or is this an oversight?

---

## Q9 — analyze_study_logs.py: write_csv() fieldnames order non-reproducible

**File:** `packages/concept-aware/analyze_study_logs.py`, `write_csv()`

After the v27 fix, `fieldnames` is built from an insertion-ordered dict union:

```python
all_keys: dict[str, None] = {}
for m in session_metrics:
    for k in m.keys():
        if k not in _NON_SCALAR_KEYS:
            all_keys[k] = None
fieldnames = list(all_keys)
```

Column order depends on which session's keys appear first. In a mixed pilot+full
study run (where pilot sessions have fewer fields), the CSV column order changes
depending on whether pilot files are loaded before or after full-schema files.

**[QUESTION Q9]:** Should `fieldnames` be sorted? A canonical sorted order ensures
reproducible CSV structure regardless of file loading order — important for
pre-registration reproducibility (reviewers expect identical column schemas in
replication attempts):

```python
fieldnames = sorted(all_keys)
```

Or is a canonical explicit ordering preferred, where known fields are listed first
and unknown fields appended sorted at the end? The latter is more readable for
analysts opening the CSV directly.

---

## Q10 — benchmarkSeeds.ts / benchmark_seeds.json: sync verified — CONFIRMED

**File:** `packages/frontend/src/utils/benchmarkSeeds.ts`
**File:** `packages/concept-aware/data/benchmark_seeds.json`

Both files contain the same 8 seed IDs (`'0'`, `'9'`, `'276'`, `'269'`, `'484'`,
`'505'`, `'32'`, `'558'`) with matching trap type assignments. `benchmark_seeds.json`
additionally contains `human_score`, `c5_score`, `topological_gap_count`, and
`selection_rationale` fields used by the Python analysis pipeline.

**Status: No change required.**

---

## Q11 — benchmarkSeeds.ts: benchmark_case injected for Condition A — design question

**File:** `packages/frontend/src/components/charts/StudentAnswerPanel.tsx`

```typescript
benchmark_case: getBenchmarkCase(answer.id),
```

`getBenchmarkCase()` is called regardless of `studyCondition`. Condition A educators
(no VerifierReasoningPanel, no CONTRADICTS chips) will have `benchmark_case` injected
into their `answer_view_start` logs when they click a seeded answer.

**[QUESTION Q11]:** Is this intentional?

The argument for injecting in Condition A: it enables post-hoc measurement of whether
Condition A educators dwell longer on `unorthodox_genius` answers (even without trace
context, they may sense something is off). This would be a meaningful between-condition
comparison.

The argument against: the `fluent_hallucination` and `partial_credit_needle` traps
are only detectable via the trace panel (Condition B only). Injecting these trap
labels for Condition A views would include rows where the trap was structurally
undetectable — potentially confounding the `dwell_by_benchmark` analysis.

Should `benchmark_case` be filtered to only the `unorthodox_genius` and
`lexical_bluffer` types for Condition A (the two traps visible from score alone),
while `fluent_hallucination` and `partial_credit_needle` are suppressed?

---

## Summary Table

| # | File | Severity | Status | Item |
|---|------|----------|--------|------|
| Q1 | VerifierReasoningPanel.tsx | — | ✅ Confirmed | TRM gap count excludes ungrounded steps — correct |
| Q2 | VerifierReasoningPanel.tsx | — | ✅ Confirmed | Grounding density denominator = all steps — correct |
| Q3 | VerifierReasoningPanel.tsx | — | ✅ Confirmed | KG→Trace reverse brushing implemented via `highlightedNode` |
| Q4 | InstructorDashboard.tsx | — | ✅ Confirmed | `sessionContradictsNodes` is a permanent accumulator — correct |
| Q5 | study.service.ts | — | ✅ Confirmed | Per-session JSONL, race-safe, ok:false on error |
| Q6 | StudentAnswerPanel.tsx | — | ✅ Confirmed | `fnv1a()` populated; raw text absent — FERPA compliant |
| **Q7** | VerifierReasoningPanel.tsx | **Critical** | ❌ Bug | `logEvent('trace_interact')` never called — `trace_interactions` always 0 in logs |
| **Q8** | analyze_study_logs.py | **High** | ❌ Bug | H2 hypergeometric `k` includes Click-to-Add — inflates H2 primary metric |
| Q9 | analyze_study_logs.py | Low | ❓ Open | `fieldnames` column order non-reproducible across session loading orders |
| Q10 | benchmarkSeeds.ts | — | ✅ Confirmed | `benchmark_seeds.json` in sync with TypeScript constants |
| **Q11** | StudentAnswerPanel.tsx | Medium | ❓ Open | Condition A gets `benchmark_case` for trace-only traps — intentional? |

**Priority:** Fix Q7 before any pilot participant session — zero `trace_interact` events
makes the engagement metrics (`trace_interactions`, `contradicts_interactions`) unusable.
Fix Q8 before running `analyze_study_logs.py` on real data — the current H2 primary
metric is computed incorrectly. Q9 and Q11 are design decisions, not bugs.
