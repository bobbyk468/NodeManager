# ConceptGrade — Code Review v26 Feedback

This document provides feedback and answers to the questions raised in `conceptgrade_gemini_review_v26.md`.

## Q1 — `analyze_study_logs.py`: `write_edits_csv()` `None` → `''` fix and `DictWriter` `restval`
**Confirmed.** The session-level CSV (`write_csv()`) explicitly excludes non-scalar fields (like `raw_edits` and `answer_dwells`) via the `_NON_SCALAR_KEYS` filter. Therefore, it only writes scalar values (ints, floats, strings, booleans). The `None` vs `''` problem for list serialization is isolated to the edits CSV (`write_edits_csv()`), which has now been fixed. The `restval=''` guard is a good defensive measure for backward compatibility with older logs.

## Q2 — `analyze_study_logs.py`: `'ts'` → `'timestamp_ms'` rename
**Confirmed.** The raw `trace_interactions` list is currently only used internally to compute the aggregate count (`len(trace_interactions)`) and the `contradicts_interactions` count. It is not exported to any CSV or JSON output. Therefore, renaming `'ts'` to `'timestamp_ms'` to match the `studyLogger.ts` schema is perfectly safe and will not break any downstream consumers.

## Q3 — `score_ablation_v2.py`: `sys.exit(2)` convention
**Closed.** No action needed.

## Q4 — `score_batch_results.py`: `BACKUP_DIR` sentinel mismatch
**Keep hardcoded fallback.** `BACKUP_DIR` pointing to `data/batch_responses/` is acceptable as a hardcoded fallback. It serves as a read-only archive path for previously completed batches. Since it is only used as a fallback when the primary `BATCH_DIR` (which is now correctly synchronized via the `CONCEPTGRADE_BATCH_DIR` environment variable) doesn't contain the files, it doesn't need the same dynamic configurability.

## Q5 — `analyze_study_logs.py`: `std_of()` dead code
**Closed.** Confirmed live.

## Q6 — VIS 2027: `chart_hover` vs `chart_click` disambiguation
**Confirmed.** The other chart components (`BloomsBarChart`, `SoloBarChart`, `ConceptFrequencyChart`, `ScoreComparisonChart`, `ChainCoverageChart`) use Recharts' standard `onMouseEnter` for tooltips, which correctly maps to `chart_hover`. They do not currently have custom `onClick` handlers (like the radar quartile click or the table row expand) that would require upgrading to `chart_click`. The disambiguation applied in v26 covers the necessary interactive elements.

## Q7 — VIS 2027: `CrossDatasetComparisonChart` null return
**Placeholder is adequate.** The current placeholder text ("Cross-dataset comparison requires data from at least two datasets.") is clear and descriptive enough for a facilitator running a pilot study. It explicitly states the requirement without cluttering the UI with technical instructions about running pipelines.

## Q8 — VIS 2027: `total_misconceptions` hardcoded 0 (Medium Priority)
**Action Required.** The zero-match proxy is indeed a poor substitute for actual misconceptions. 
If the `EvalSample` interface and the underlying JSON data do not currently expose a dedicated misconception count field (e.g., `n_misconceptions` or `has_misconception`), the UI label should be updated to accurately reflect the data.
**Recommendation:** Change the label in `buildClassSummary()` (and the corresponding frontend component if hardcoded there) from "Total Misconceptions" to "Answers with Zero Concepts Matched" or "Zero-Match Answers". This prevents overclaiming the metric's capability in a VIS 2027 context. If the backend *does* have access to misconception data in the future, this can be reverted.

## Q9 — VIS 2027: `getConceptStudentAnswers` `question_id` filtering
**Filter matched cases too.** Yes, matched cases should also be filtered by `question_id` when `qIdKnown` is true. If a student mentions a concept in an answer to a question that *doesn't* test that concept, it is likely noise (or an accidental keyword match) rather than a meaningful signal of mastery for the intended learning objective. 
**Recommendation:** Update the logic to skip *both* matched and missed cases if they belong to a question that doesn't expect the concept:
```typescript
if (qIdKnown && !questionIdsExpecting.has(row.question_id)) continue;
```
This ensures the drill-down view remains strictly focused on the relevant context.

---
**Summary of Next Steps:**
1. **Q8:** Update the UI label for the zero-match proxy to accurately reflect what it measures (e.g., "Zero-Match Answers"), or implement actual misconception counting if the data is available.
2. **Q9:** Update `getConceptStudentAnswers` to filter *both* matched and missed cases by `question_id` when `qIdKnown` is true.