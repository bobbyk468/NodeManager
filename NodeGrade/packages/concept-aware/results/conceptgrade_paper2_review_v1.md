# ConceptGrade — Paper 2 Code Review (IEEE VIS 2027 VAST)

## Paper Title (Working)
"ConceptGrade: A Visual Analytics System for Human-AI Co-Auditing of Knowledge Graph-Grounded Grading"

## Scope of This Review

Paper 2 claims three distinct contributions that map to code:

1. **Topological Reasoning Mapping (TRM)** — formal technique for mapping LRM reasoning chains onto a domain KG topology (Definitions 1–5).
2. **Bidirectional Co-Auditing Interface** — VA system with linking & brushing via `DashboardContext`, `VerifierReasoningPanel`, `ConceptKGPanel`, `RubricEditorPanel`.
3. **Controlled User Study** — Condition A/B telemetry pipeline (`studyLogger.ts` → `analyze_study_logs.py`) with pre-registered hypotheses H1 (temporal attribution) and H2 (semantic alignment).

This review covers each contribution area with questions about correctness, completeness, and paper-readiness.

---

## Section 1 — TRM Formal Definitions vs. Implementation

### TRM Formal Definitions (v11, locked):
- **Definition 1 (Step Mapping):** φ(sᵢ) = Nᵢ ⊆ V (node set only; no cᵢ in the formal box)
- **Definition 2 (Adjacency):** Nᵢ ∩ Nᵢ₊₁ ≠ ∅ (node-only continuity; no edge-type criterion)
- **Definition 3 (Structural Leap):** Nᵢ ≠ ∅ AND Nᵢ₊₁ ≠ ∅ AND Nᵢ ∩ Nᵢ₊₁ = ∅
- **Definition 4 (Leap Count):** integer count of structural leaps among consecutive grounded steps
- **Definition 5 (Grounding Density):** |{i : Nᵢ ≠ ∅}| / n ∈ [0, 1]

### Implementation in `DashboardContext.tsx`:

`lastTraceGapCount` (Def 4) and `lastGroundingDensity` (Def 5) are stored as state. Both are dispatched by `VerifierReasoningPanel` when `parsedSteps` changes (`SET_TRACE_GAP_COUNT`, `SET_GROUNDING_DENSITY`).

**Q1 — VerifierReasoningPanel: gap count computation — does it match Definition 3?**

`VerifierReasoningPanel` sets `lastTraceGapCount`. Definition 3 requires:
- Both Nᵢ and Nᵢ₊₁ are non-empty (both steps must be grounded)
- Nᵢ ∩ Nᵢ₊₁ = ∅ (no shared KG node between consecutive steps)

**Question:** Confirm the gap count computation in `VerifierReasoningPanel` checks both conditions. Specifically:
(a) Are ungrounded steps (empty `kg_nodes`) excluded from the leap count, or do they contribute a gap by default?
(b) Is the intersection check on `kg_nodes` arrays (step-level node IDs), or on a higher-level concept label?

If ungrounded steps are counted as gaps, the Leap Count inflates — a 20-step trace with 15 ungrounded steps becomes 15 "gaps" by default, which is not what Definition 3 formalises.

---

**Q2 — Grounding Density (Definition 5) denominator — all steps or only classified steps?**

Definition 5: `|{i : Nᵢ ≠ ∅}| / n` where n is the total number of steps in the trace.

**Question:** In `VerifierReasoningPanel`, is `n` the count of all `parsedSteps` (including UNCERTAIN), or only SUPPORTS + CONTRADICTS steps? If UNCERTAIN steps with empty `kg_nodes` are excluded from both numerator and denominator, the grounding density is artificially inflated. The paper claims to compare Gemini Flash vs DeepSeek-R1 on grounding density — a computation mismatch here invalidates the Stability Analysis comparison.

---

## Section 2 — Bidirectional Brushing & Linking

### Implemented brushing paths (from `DashboardContext.tsx`):
- **Heatmap cell click → StudentAnswerPanel:** `selectConcept(concept, severity)` → answer list filters to that concept/severity
- **Radar quartile click → StudentAnswerPanel filter:** `selectQuartile(index)` → answer list narrows to score range
- **StudentAnswerPanel row click → ConceptKGPanel node coloring:** `selectStudent(id, matchedConcepts)` → KG subgraph highlights matched concept nodes
- **VerifierReasoningPanel step click → ConceptKGPanel:** `onNodeClick` prop → KG panel opens for that node

**Q3 — Reverse brushing: ConceptKGPanel node click → VerifierReasoningPanel step filter — is it implemented?**

The VIS VAST requirement is *bidirectional* brushing. The `VerifierReasoningPanel` JSDoc states:
> "Click a KG node → filters the step list to show only steps that reference that node"

**Question:** Is the KG → Trace direction (clicking a node in `ConceptKGPanel` → filtering `VerifierReasoningPanel` steps to matching `kg_nodes`) actually wired in the current code? If this direction only exists in comments but not in the event flow, the co-auditing interface is unidirectional, which weakens the core VIS claim. Confirm the exact prop/callback that delivers the KG-selected node ID to `VerifierReasoningPanel` as `highlightedNode`.

---

**Q4 — `sessionContradictsNodes` accumulation — who owns the accumulation and across which scope?**

`RubricEditorPanel` receives `sessionContradictsNodes: string[]` as a prop (from `InstructorDashboard`). The `recentContradicts` rolling window is in `DashboardContext`. These are two separate stores:

- `sessionContradictsNodes` — all-time session accumulation (union across all answers viewed)
- `recentContradicts` — rolling 60-second window for causal attribution

**Question:** Who populates `sessionContradictsNodes` in `InstructorDashboard`? Is it derived from `recentContradicts` (wrong — that would be a 60s rolling subset), or maintained as a separate `useState` that accumulates every `CONTRADICTS` node across the session? If the two arrays can diverge (e.g., old CONTRADICTS nodes fall out of the rolling window but stay in `sessionContradictsNodes`), confirm that the semantic alignment check in `handleEdit()` uses `sessionContradictsNodes` (full session) and the causal attribution window check uses `recentContradicts` (rolling). The paper's H1 and H2 depend on this distinction being correct.

---

**Q5 — Click-to-Add chip availability — Condition A/B gating correctness**

`RubricEditorPanel` receives `sessionContradictsNodes` from the parent. For Condition A, the parent passes an empty array, so the CONTRADICTS chip strip is blank (correct per design). But the rubric concept list with edit buttons is visible in both conditions.

**Question:** In `InstructorDashboard.tsx`, is `sessionContradictsNodes` derived from `DashboardContext.recentContradicts` or from a separate accumulator? If it is derived from the rolling window, an educator in Condition B who spent > 60 seconds between their last trace interaction and opening the rubric panel would see a blank CONTRADICTS strip even though they are in Condition B — creating a condition assignment failure that would corrupt the study data.

---

## Section 3 — Study Logging (`studyLogger.ts`)

### Event taxonomy:
```typescript
'page_view' | 'tab_change' | 'task_start' | 'task_submit'
| 'chart_hover'     // mouse enters a chart container
| 'chart_click'     // deliberate click (quartile, row expand, heatmap cell)
| 'trace_interact'  // CONTRADICTS/SUPPORTS/UNCERTAIN step click
| 'rubric_edit'     // add/remove/increase_weight/decrease_weight
| 'answer_view_start' | 'answer_view_end'
```

**Q6 — `trace_interact` logging in `VerifierReasoningPanel` — is `pushContradicts` called?**

When an educator clicks a CONTRADICTS step, two things must happen atomically:
1. `logEvent(..., 'trace_interact', { classification, node_id, step_id })` — for the log record
2. `pushContradicts(nodeId)` — to update the rolling 60-second window in `DashboardContext`

If `pushContradicts` is called but `logEvent('trace_interact')` is not (or vice versa), the log and the causal window diverge, and the `within_30s` field in subsequent `rubric_edit` events will not match the logged `trace_interact` timeline.

**Question:** In `VerifierReasoningPanel`, confirm both calls are made in the same handler for CONTRADICTS steps. Are SUPPORTS and UNCERTAIN clicks also logged as `trace_interact`? If only CONTRADICTS is logged, the log loses the signal needed for the `trace_gap_count` moderation analysis.

---

**Q7 — `answer_view_end` beacon delivery — `studyApiBase` must be set**

`logBeacon()` in `studyLogger.ts` calls `navigator.sendBeacon()` only if `studyApiBase` is set:
```typescript
if (studyApiBase) {
  const blob = new Blob([JSON.stringify(event)], { type: 'application/json' });
  navigator.sendBeacon(`${studyApiBase}/api/study/log`, blob);
}
```

`setStudyApiBase()` must be called once on `InstructorDashboard` mount via `useEffect`. If it is not called, `answer_view_end` events are written to `localStorage` only, and tab-close events are lost — the `dwell_time_ms` field (populated by beacon) will be null for all participants who close the tab mid-session.

**Question:** Confirm `setStudyApiBase(apiBase)` is called in `InstructorDashboard`'s mount `useEffect`. Also confirm: does the backend `POST /api/study/log` endpoint (in `study.controller.ts`) write events to a durable file (not just respond 200)? If the backend is not running during the study, beacon events are silently dropped.

---

**Q8 — `answer_content_hash` FERPA compliance — is it computed at log time?**

`AnswerDwellPayload` includes:
```typescript
answer_content_hash?: string;  // FNV-1a hash of student answer text (32-bit, hex)
```
This field is described as a FERPA compliance measure — raw text is never logged, only the hash.

**Question:** Is `answer_content_hash` actually computed and populated in `StudentAnswerPanel` when `logEvent('answer_view_start', ...)` is called? If the field is defined in the TypeScript interface but never populated, the FERPA compliance claim in the paper is unfounded. If raw answer text appears anywhere in the log payload, it must be removed before the paper can claim IRB-grade data handling.

---

## Section 4 — Analysis Pipeline (`analyze_study_logs.py`)

### Pre-registered hypotheses:
- **H1 (temporal):** Condition B educators edit rubric concepts within 30 s of a CONTRADICTS interaction at a higher rate than chance. Primary window = 30 s; sensitivity checks at 15 s and 60 s.
- **H2 (semantic):** Edited concepts semantically align with session-level CONTRADICTS nodes at a rate exceeding hypergeometric null (N = rubric_size, K = contradicts_count, n = total_edits).
- **H-DT2 (dwell):** Condition B educators dwell longer on benchmark-seeded answers than non-seeded.
- **H-MOD (moderation):** `trace_gap_count` moderates H1 — gappier traces increase causal attribution probability.

**Q9 — GEE moderation model — `session_id` as cluster variable**

`run_gap_moderation_analysis()` builds rows with `session_id`, `condition`, `trace_gap_count`, `within_30s` (one row per rubric_edit). The GEE model formula (locked v9) is:
```
within_30s ~ condition * trace_gap_count | session_id
```

The `session_id` field in each `raw_edits` entry comes from the rubric_edit record dict. In `write_edits_csv()`, the canonical `m['session_id']` is used as the first key; the spread then excludes `k != 'session_id'` from the edit dict to prevent overwriting.

**Question:** In `run_gap_moderation_analysis()`, does the code read `session_id` from `m['session_id']` (the session-level key) or from `edit.get('session_id')` (the per-edit copy)? If it reads from the per-edit copy and any older logs lack this field, the cluster variable would silently be `None`, turning the GEE into a standard GLM with no random effects and inflated type-I error.

---

**Q10 — Hypergeometric null model (H2) — `n_semantic_aligned` vs `n_manual_edits`**

The hypergeometric p-value is computed as:
```python
hyper_p = _hypergeometric_p(
    k=n_semantic_aligned,   # successes observed (all edits, CTA + manual)
    N=max(n_rubric, m_flagged),
    K=m_flagged,
    n=n_edits,              # total draws
)
```

The paper states H2 PRIMARY = `semantic_alignment_rate_manual` (unprompted edits only), but the hypergeometric test uses `k=n_semantic_aligned` which includes Click-to-Add edits. Click-to-Add edits always align semantically by construction (the educator clicked a chip that IS a CONTRADICTS node), so including them artificially inflates `k` and deflates `hyper_p`.

**Question:** Should the hypergeometric test be computed twice — once for all edits (`k=n_semantic_aligned`, for the combined rate) and once for manual-only edits (`k=n_semantic_aligned_manual`, n=`n_manual_edits`, for the H2 primary test)? Reporting only the combined `hyper_p` as the H2 primary result overstates the unprompted alignment rate, which is the actual causal claim.

---

**Q11 — `fieldnames` union order in `write_csv()` — column ordering across mixed-schema logs**

After the v27 fix, `fieldnames` is built as an insertion-ordered dict union across all sessions:
```python
all_keys: dict[str, None] = {}
for m in session_metrics:
    for k in m.keys():
        if k not in _NON_SCALAR_KEYS:
            all_keys[k] = None
fieldnames = list(all_keys)
```

The column order depends on which session appears first. In a mixed-schema study (pilot sessions before full deployment, older logs lacking `rubric_size`), the column ordering will differ from a pure new-schema run — making the CSV non-reproducible if log files are processed in different orders.

**Question:** Should `fieldnames` be sorted (e.g., `sorted(all_keys)`) or follow a fixed canonical ordering (explicit list with `all_keys` as a fallback for unknown keys)? Sorted ordering ensures reproducible CSV structure regardless of session processing order, which matters for pre-registration reproducibility.

---

## Section 5 — Benchmark Seeds (`benchmarkSeeds.ts`)

### Seeded answers (DigiKlausur):
```
fluent_hallucination : IDs '0', '9'   (structural leap in LRM trace)
unorthodox_genius    : IDs '276', '269' (human=5.0, AI low)
lexical_bluffer      : IDs '484', '505' (AI overestimates; CONTRADICTS buried)
partial_credit_needle: IDs '32', '558'  (balanced trace; concept missing in KG)
```

**Q12 — Benchmark seed discovery path — does the educator have to find them naturally?**

The benchmark seeds are designed to be discovered *naturally* via the Concept Heatmap (foraging task). The `benchmark_case` flag is injected into `answer_view_start` / `answer_view_end` payloads silently, preserving ecological validity.

**Question:** If an educator in Condition A (no trace panel) clicks on a seeded answer, will `getBenchmarkCase(studentAnswerId)` still return the benchmark trap type and inject it into the log? Condition A lacks the VerifierReasoningPanel, so the `fluent_hallucination` trap (which requires reading the structural leap in the trace) is invisible to Condition A participants. Should `answer_view_start` payloads for Condition A still inject `benchmark_case`, or should this be filtered out to avoid confounding the post-hoc trap analysis with Condition A views?

---

**Q13 — `data/benchmark_seeds.json` synchronisation — is it in sync with `benchmarkSeeds.ts`?**

`benchmarkSeeds.ts` documents:
> "Sync this file with packages/concept-aware/data/benchmark_seeds.json whenever seeds change."

**Question:** Does `data/benchmark_seeds.json` currently exist in the repo, and does it contain the same 8 seed IDs with the same trap type assignments as `benchmarkSeeds.ts`? If the file is missing or out of sync, the Python analysis pipeline (`analyze_study_logs.py`) cannot validate seed IDs server-side, and any per-study seed assignment verification would rely solely on the TypeScript frontend constants.

---

## Section 6 — Backend Study Durability (`study.controller.ts`)

**Q14 — `POST /api/study/log` — file write durability and IRB compliance**

`studyLogger.ts` JSDoc states the backend is used for "IRB-grade durability" — a tab crash loses all `localStorage` data, so the backend must persist every event to disk.

**Question:** In `study.controller.ts`, does the `POST /api/study/log` handler:
(a) Append the event to a per-session JSONL file (one file per `session_id`)?
(b) Return `{ ok: false, error: string }` (not 5xx) on disk write failures?
(c) Validate the incoming payload against `StudyEvent` schema before writing?

If events from different sessions are written to a single shared file, concurrent writes during a multi-participant pilot would produce a corrupted JSONL file (race condition). Per-session files (`{session_id}.jsonl`) eliminate this risk.

---

## Summary Table

| # | Area | File | Severity | Question |
|---|------|------|----------|----------|
| Q1 | TRM | VerifierReasoningPanel.tsx | **High** | Gap count excludes ungrounded steps per Def. 3? |
| Q2 | TRM | VerifierReasoningPanel.tsx | **High** | Grounding density denominator — all steps or classified only? |
| Q3 | Brushing | ConceptKGPanel.tsx | **High** | KG→Trace reverse brushing — wired or comments only? |
| Q4 | Brushing | InstructorDashboard.tsx | **High** | `sessionContradictsNodes` vs `recentContradicts` — owner and scope |
| Q5 | Study | InstructorDashboard.tsx | **High** | Condition B CONTRADICTS strip blanks after 60 s gap — race condition? |
| Q6 | Logging | VerifierReasoningPanel.tsx | **High** | `pushContradicts` + `logEvent('trace_interact')` called atomically? |
| Q7 | Logging | InstructorDashboard.tsx | Medium | `setStudyApiBase()` called on mount? Backend durable? |
| Q8 | Logging | StudentAnswerPanel.tsx | Medium | `answer_content_hash` populated (FERPA)? Raw text absent? |
| Q9 | Analysis | analyze_study_logs.py | **High** | GEE cluster reads `m['session_id']` or `edit.get('session_id')`? |
| Q10 | Analysis | analyze_study_logs.py | **High** | Hypergeometric H2 should use manual-only `k`, not combined |
| Q11 | Analysis | analyze_study_logs.py | Low | `fieldnames` column order non-reproducible across log orderings |
| Q12 | Seeds | benchmarkSeeds.ts | Medium | Condition A logs `benchmark_case` — appropriate or confound? |
| Q13 | Seeds | benchmarkSeeds.ts | Medium | `benchmark_seeds.json` in sync with TypeScript constants? |
| Q14 | Backend | study.controller.ts | **High** | Per-session JSONL? Race-safe concurrent writes? Schema validation? |

**Priority order:** Q10 (H2 primary metric inflated by CTA) and Q1 (TRM gap count correctness) are the two items most likely to draw VIS reviewer rejection. Q3 (reverse brushing) and Q14 (backend durability) are mandatory for the "IRB-grade" and "bidirectional" claims respectively. Fix all High items before the pilot study begins.
