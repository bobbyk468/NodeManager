# ConceptGrade — Code Review v26 for Gemini

## Context

This review covers fixes applied from two sources:
(a) Remaining v25 questions (Q2, Q3, Q4, Q5).
(b) VIS 2027 code walkthrough action items (Action Plan items 1–6).

---

## Q1 — analyze_study_logs.py: write_edits_csv() — None → '' fix and DictWriter restval

**File:** `packages/concept-aware/analyze_study_logs.py`, `write_edits_csv()`

**Fix applied:** Empty lists now serialize as `''` (not `None`), and `DictWriter` is
instantiated with `restval=''`:

```python
k: ('|'.join(str(x) for x in v) if v else '') if isinstance(v, list) else v
# ...
writer = csv.DictWriter(f, fieldnames=fieldnames, restval='')
```

**Question:** The `restval=''` guard handles missing keys for rows where a new field was
added mid-study (e.g., if `rubric_size` was added in v21 and older sessions lack it).
Are there any fields in the `write_csv()` session-level CSV that also have the same
`None` vs `''` problem for list fields, or is the session-level CSV only scalar fields?

---

## Q2 — analyze_study_logs.py: 'ts' → 'timestamp_ms' rename — downstream consumers

**File:** `packages/concept-aware/analyze_study_logs.py`, `analyse_session()`

**Fix applied:** Both `trace_interactions` records and `rubric_edits` records now use
`'timestamp_ms'` instead of `'ts'` as the field name, matching the `StudyEvent`
schema in `studyLogger.ts`.

**Question:** The `trace_interactions` list is included in the session result dict as
`'trace_interactions': len(trace_interactions)` — only the count is exported, not
the raw dicts. Is the raw `trace_interactions` list (with `timestamp_ms`) also written
to any CSV or JSON output? If not, the rename is cosmetic for the current output, but
correct for any future per-interaction export. Please confirm no downstream consumer
of `trace_interactions` dicts reads `'ts'` as a key.

---

## Q3 — score_ablation_v2.py: sys.exit(2) convention — resolved

**File:** `packages/concept-aware/score_ablation_v2.py`

**Decision:** `sys.exit(2)` is retained. The distinction is documented in the inline
comment (`exit(2) = data integrity abort; exit(1) = missing-file / user error`) and
is not consumed by any downstream CI script. No change applied.

**Question:** None — this item is closed.

---

## Q4 — score_ablation_v2.py: BATCH_DIR sentinel mismatch — fixed

**Files:**
- `run_batch_eval_api.py` — writes sentinel `.flag` files
- `generate_batch_scoring_prompts.py` — writes batch prompt files
- `run_full_pipeline.py` — orchestrates both
- `score_batch_results.py` — reads batch response files
- `score_ablation_v2.py` — reads sentinel files for integrity check

**Critical bug fixed:** The sentinel writer (`run_batch_eval_api.py`) was writing
`.flag` files to `/tmp/batch_scoring/`, while the sentinel checker (`score_ablation_v2.py`)
was checking `data/batch_responses/`. The check always saw zero flags.

**Fix applied:** All five scripts now resolve `BATCH_DIR` via:

```python
BATCH_DIR = os.environ.get('CONCEPTGRADE_BATCH_DIR', os.path.join(BASE_DIR, 'data', 'tmp'))
```

`score_ablation_v2.py` uses the same env var for its sentinel check, so writer and
checker are guaranteed to use the same directory.

**Question:** `score_batch_results.py` has a `BACKUP_DIR = os.path.join(DATA_DIR, "batch_responses")`
that is used as a fallback when files are not found in `BATCH_DIR`. After this change,
`BACKUP_DIR` still points to `data/batch_responses/` (the old persistent store). Should
`BACKUP_DIR` also be made configurable via a second env var (e.g., `CONCEPTGRADE_BACKUP_DIR`),
or is the hardcoded `data/batch_responses/` fallback acceptable since it's a read-only
archive path that doesn't need to match the writer?

---

## Q5 — analyze_study_logs.py: std_of() dead code — confirmed live

**File:** `packages/concept-aware/analyze_study_logs.py`, `aggregate_by_condition()`

**Verification:** `std_of()` is consumed in the result dict on lines 448 and 450:
`'sus_sd': std_of('sus_score')` and `'time_to_answer_sd_s': std_of('time_to_answer_s')`.
These fields propagate into the session-level CSV via `write_csv()`. Not dead code.

**Question:** None — this item is closed.

---

## Q6 — VIS 2027: chart_hover vs chart_click disambiguation — fixed

**Files:**
- `packages/frontend/src/utils/studyLogger.ts` — `'chart_click'` added to `StudyEventType` union
- `packages/frontend/src/components/charts/StudentRadarChart.tsx` line 72 — quartile click now emits `'chart_click'`
- `packages/frontend/src/components/charts/ScoreSamplesTable.tsx` line 315 — row expand now emits `'chart_click'`

**Question:** Are there any other `onMouseEnter` handlers in the chart components that
were also logging clicks (i.e., mouse-enter events from dragging or programmatic focus
that are not deliberate clicks)? Specifically, do `BloomsBarChart`, `SoloBarChart`,
`ConceptFrequencyChart`, `ScoreComparisonChart`, or `ChainCoverageChart` have any
click-like interactions (bar select, label click) that should be upgraded to
`'chart_click'` rather than `'chart_hover'`?

---

## Q7 — VIS 2027: CrossDatasetComparisonChart null return — fixed

**File:** `packages/frontend/src/components/charts/CrossDatasetComparisonChart.tsx`

**Fix applied:** `if (loading || error || points.length < 2) return null;` is split
into two guards:

```tsx
if (loading) return null;
if (error || points.length < 2) {
  return (
    <Box sx={{ p: 2, color: 'text.secondary', fontStyle: 'italic', fontSize: 13 }}>
      Cross-dataset comparison requires data from at least two datasets.
    </Box>
  );
}
```

**Question:** During a pilot study with only one dataset loaded, this placeholder
message will show in the `InstructorDashboard`. Is the placeholder text descriptive
enough for a facilitator running a pilot, or should it include a hint such as
"(Run the pipeline for additional datasets to populate this chart)"?

---

## Q8 — VIS 2027: total_misconceptions hardcoded 0 — fixed

**File:** `packages/backend/src/visualization/visualization.service.ts`, `buildClassSummary()`

**Fix applied:**

```typescript
// Was:
total_misconceptions: 0,

// Now:
total_misconceptions: results.filter((r) => (r.matched_concepts ?? []).length === 0).length,
```

**Question:** This proxy counts samples where *no* concepts were matched (zero-match
samples), which is a lower bound on misconceptions. The VIS 2027 walkthrough notes
that the actual misconception detector output is in the eval data. Does `EvalSample`
have a field (e.g., `r.misconceptions`, `r.has_misconception`) that should be used
instead of the zero-match proxy? If not, should the `InstructorDashboard` card label
be updated from "Total Misconceptions" to "Answers with No Matched Concepts" to
avoid overstating what the metric measures?

---

## Q9 — VIS 2027: getConceptStudentAnswers question_id filtering — fixed

**File:** `packages/backend/src/visualization/visualization.service.ts`,
`getConceptStudentAnswers()`

**Fix applied:** Missed cases (not matched) are now filtered to questions that expect
this concept when KG question_id data is available:

```typescript
const qIdKnown = questionIdsExpecting.size > 0;
// ...
if (!matched && qIdKnown && !questionIdsExpecting.has(row.question_id)) continue;
```

**Question:** The fix only skips missed cases from off-topic questions; matched cases
are still shown regardless of `question_id`. Is this the right behavior? An educator
browsing a concept drill-down might find it confusing if a student appears as "matched"
on a question that wasn't designed to test the concept. Should matched cases also be
filtered by `question_id` when `qIdKnown` is true, or is "matched anywhere" a
meaningful signal worth showing?

---

## Summary Table

| # | File | Severity | Category |
|---|------|----------|----------|
| Q1 | analyze_study_logs.py | Low | Verify write_csv() session-level CSV has no None list fields |
| Q2 | analyze_study_logs.py | Low | Confirm no downstream consumer of trace_interactions reads 'ts' |
| Q3 | score_ablation_v2.py | Closed | sys.exit(2) retained — no consumers distinguish 1 vs 2 |
| Q4 | score_batch_results.py | Low | Should BACKUP_DIR also be env-configurable? |
| Q5 | analyze_study_logs.py | Closed | std_of() is live code — consumed in aggregate result dict |
| Q6 | chart components | Low | Are there other click interactions mislabeled as chart_hover? |
| Q7 | CrossDatasetComparisonChart.tsx | Low | Placeholder text adequacy for pilot facilitators |
| Q8 | visualization.service.ts | **Medium** | Zero-match proxy vs actual misconception field; label accuracy |
| Q9 | visualization.service.ts | Low | Should matched cases also be filtered by question_id? |

**Priority:** Q8 is the most substantive open question — if `EvalSample` has a real
misconception field, the proxy should be replaced. All other items are low-risk.
