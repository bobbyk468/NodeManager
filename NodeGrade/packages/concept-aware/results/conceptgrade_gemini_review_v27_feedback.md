# ConceptGrade — Code Review v27 Feedback

This document provides feedback and answers to the questions raised in `conceptgrade_gemini_review_v27.md`.

## Q1 — `analyze_study_logs.py`: `write_csv()` fieldnames union
**Action Required.** Yes, `fieldnames` should definitely be derived from the union of all session keys rather than just the first session. If the first session in the list is an older log that lacks newly added fields (like `rubric_size`), those fields will be completely dropped from the CSV output for *all* sessions. 
**Recommendation:** Update the fieldnames extraction to iterate over all sessions and collect a unique set of keys (excluding `_NON_SCALAR_KEYS`), then sort them or enforce a specific order.

## Q2 — `score_batch_results.py`: `BACKUP_DIR`
**Closed.** No action needed.

## Q3 — `MisconceptionHeatmap.tsx`: `chart_click` payload field name
**Action Required.** To ensure clean data for pre-registered analyses and easy joins, the payload schema should be consistent across all events. Since `rubric_edit` uses `concept_id`, the `chart_click` event should also use `concept_id` instead of `concept`.
**Recommendation:** Change the payload in `MisconceptionHeatmap.tsx` to:
`logEvent(condition, dataset, 'chart_click', { viz_id: spec.viz_id, concept_id: concept, severity: sev });`

## Q4 — `CrossDatasetComparisonChart.tsx`: Placeholder specificity
**Current text is sufficient.** For the target audience of researcher-facilitators, the current prose ("Run the pipeline for additional datasets...") is adequate. Hardcoding the specific Python command in the React frontend risks the UI becoming outdated if the CLI arguments or script names change in the future.

## Q5 — `InstructorDashboard.tsx`: 7-card grid overflow (Medium Priority)
**Action Required.** Adding the 7th card with `md={2}` results in a total width of 14 columns, which breaks the 12-column MUI Grid and forces an awkward wrap on medium/large screens.
**Recommendation:** Since 7 does not divide evenly into 12, using strict integer grid columns will always leave empty space or force a wrap. The best layout fixes are:
1. **Use Flexbox Auto-Sizing:** Change the `Grid` items for the metric cards to use `xs="auto"` or `flex: 1` (e.g., `<Grid item xs={12} sm={6} md={true} ...>`) so they automatically share the available row width equally without relying on the 12-column constraints.
2. **Consolidate Cards:** Combine "Baseline MAE" and "C5 MAE" into a single "MAE Comparison" card, reducing the total number of cards back to 6, which perfectly fits `md={2}`.

Option 1 is the least destructive to the current data presentation and is highly recommended before the user study.

## Q6 — `visualization.service.ts`: Concept ID schema consistency
**No immediate action required, but monitor.** The concept IDs are normalized to underscore-separated strings (e.g., `"learning_rate"`) during the KG generation phase (specifically in `generate_auto_kg_prompt.py` which cleans concept IDs). As long as the evaluation pipeline strictly uses these cleaned IDs, they will match the `matched_concepts` array. However, if any manual edits or older datasets introduce spaces, it could cause `qIdKnown` to falsely evaluate to `false`. If this becomes an issue, adding a defensive `.replace(/ /g, '_')` normalization during the set lookup would be a safe fallback.

---
**Summary of Next Steps:**
1. **Q1:** Update `analyze_study_logs.py` to build `fieldnames` from the union of all session keys.
2. **Q3:** Rename `concept` to `concept_id` in the `MisconceptionHeatmap.tsx` `chart_click` payload.
3. **Q5 (Medium):** Fix the 7-card grid overflow in `InstructorDashboard.tsx` by using auto-sizing grid items (`md={true}`) or consolidating two cards into one.