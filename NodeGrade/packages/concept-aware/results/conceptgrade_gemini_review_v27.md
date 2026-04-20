# ConceptGrade — Code Review v27 for Gemini

## Context

This review covers fixes applied from v26 questions Q1, Q4, Q6, Q7, Q8, Q9.
Q3 and Q5 were closed in v26 with no changes.

---

## Q1 — analyze_study_logs.py: write_csv() restval='' — applied

**File:** `packages/concept-aware/analyze_study_logs.py`, `write_csv()`

**Fix applied:** `DictWriter` now instantiated with `restval=''` in both `write_csv()`
and `write_edits_csv()`:

```python
writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore', restval='')
```

This ensures sessions logged before a new field was added (e.g., old sessions without
`rubric_size`) produce an empty cell rather than the string `"None"` in R/pandas.

**Question:** The `fieldnames` list is derived from `session_metrics[0].keys()`. If
the first session in the list is an old session that lacks a new field, that field will
be absent from `fieldnames` entirely — `restval=''` only helps when a key is present
in `fieldnames` but missing from a specific row. Should `fieldnames` be derived from
the union of all session keys rather than just the first session, to handle partial
schema migrations?

---

## Q2 — score_batch_results.py: BACKUP_DIR — decision

**File:** `packages/concept-aware/score_batch_results.py`

**Decision:** `BACKUP_DIR = os.path.join(DATA_DIR, "batch_responses")` is left
hardcoded. It is a read-only persistent archive and does not need to match the writer
path. The `pattern.replace(BATCH_DIR, BACKUP_DIR)` substitution is safe because
`BATCH_DIR` appears exactly once in each pattern.

**Question:** None — this item is closed.

---

## Q3 — MisconceptionHeatmap.tsx: cell click now logs chart_click

**File:** `packages/frontend/src/components/charts/MisconceptionHeatmap.tsx`, line 128

**Fix applied:** Cell `onClick` now emits `chart_click` before invoking `onCellClick`:

```tsx
onClick={() => {
  if (!isInteractive || count === 0) return;
  logEvent(condition, dataset, 'chart_click', { viz_id: spec.viz_id, concept, severity: sev });
  onCellClick!(concept, sev);
}}
```

The guard `count === 0` prevents logging phantom clicks on empty cells (matching
the visual `cursor: 'default'` when count is zero).

**Question:** The `concept` field logged is the raw `concept` ID (underscore-separated,
e.g., `"learning_rate"`). The `viz_id` is `spec.viz_id` (e.g., `"misconception_heatmap"`).
Is there any pre-registered analysis that joins this `chart_click` payload on the
rubric_edit payload by `concept_id`? If so, confirm the field name matches — the
rubric_edit payload uses `concept_id`, not `concept`.

---

## Q4 — CrossDatasetComparisonChart.tsx: placeholder text updated

**File:** `packages/frontend/src/components/charts/CrossDatasetComparisonChart.tsx`

**Fix applied:** Placeholder when fewer than 2 datasets are loaded now reads:

> "Cross-dataset comparison requires data from at least two datasets.
> Run the pipeline for additional datasets to populate this chart."

**Question:** During a real pilot (not a dev environment), the facilitator may not
know which pipeline command to run. Should the placeholder include the specific
command (`python3 run_full_pipeline.py --dataset <name>`) or link to documentation?
Or is the current text sufficient for the target audience (researcher-facilitators
who have the README)?

---

## Q5 — InstructorDashboard.tsx: No Matched Concepts MetricCard added (Q8)

**File:** `packages/frontend/src/pages/InstructorDashboard.tsx`

**Fix applied:** A seventh MetricCard is added to the summary row:

```tsx
<MetricCard
  label="No Matched Concepts"
  value={summaryData.total_misconceptions ?? 0}
  color="#f59e0b"
  tooltip="Answers where no KG concepts were matched — proxy for missed content coverage"
/>
```

This surfaces the `total_misconceptions` value (computed from `results.filter(r =>
(r.matched_concepts ?? []).length === 0).length` in `buildClassSummary`) with an
accurate, non-overstating label.

**Question:** With seven cards in the summary row, the `md={2}` width gives each card
exactly 2/12 columns on medium screens, which is 7×2=14 — overflowing the 12-column
grid. Should the new card use `md={2}` (allowing wrapping to a second row) or should
one of the existing cards be removed or merged to keep the row on a single line?

---

## Q6 — visualization.service.ts: getConceptStudentAnswers — filter both matched and missed (Q9)

**File:** `packages/backend/src/visualization/visualization.service.ts`,
`getConceptStudentAnswers()`

**Fix applied:** Both matched and missed cases are now filtered by question_id when
KG question_id data is available:

```typescript
// Was: only skipping missed cases from off-topic questions
if (!matched && qIdKnown && !questionIdsExpecting.has(row.question_id)) continue;

// Now: skip any sample (matched or missed) from questions that don't expect the concept
if (qIdKnown && !questionIdsExpecting.has(row.question_id)) continue;
```

**Question:** The `questionIdsExpecting` set is built by checking
`qdata.expected_concepts.includes(conceptId)` in the KG file. If the KG file uses
a different concept ID schema than `matched_concepts` in the eval results (e.g., KG
uses `"learning_rate"` but eval stores `"learning rate"` with a space), the set may
be empty even when the concept is expected — causing `qIdKnown` to be `false` and
falling back to showing all samples. Is the concept ID schema guaranteed to be
consistent between the KG file and the eval results file, or is normalization needed?

---

## Summary Table

| # | File | Severity | Category |
|---|------|----------|----------|
| Q1 | analyze_study_logs.py | Low | fieldnames from union of all session keys vs first session only |
| Q2 | score_batch_results.py | Closed | BACKUP_DIR hardcoded — acceptable as read-only archive |
| Q3 | MisconceptionHeatmap.tsx | Low | chart_click payload field: `concept` vs rubric_edit `concept_id` |
| Q4 | CrossDatasetComparisonChart.tsx | Low | Placeholder specificity — command vs prose |
| Q5 | InstructorDashboard.tsx | **Medium** | 7 MetricCards overflow 12-col grid at md={2} — layout fix needed |
| Q6 | visualization.service.ts | Low | Concept ID schema consistency between KG and eval results |

**Priority:** Q5 (grid overflow) is the most visible — seven md={2} cards sum to 14
columns, which will wrap on medium screens. Adjust widths or card count before
running the user study.
