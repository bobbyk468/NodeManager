# ConceptGrade — Code Review v23 Feedback

This document provides feedback and answers to the questions raised in `conceptgrade_gemini_review_v23.md`.

## Q1 — `RubricEditorPanel.tsx`: `concept_frequency` vs `expected_concepts` for `rubric_size`
**(a)** Top-15 is an acceptable approximation. The educator's "opportunity" to edit a concept is bounded by what is presented to them in the UI. If they only see the top 15 concepts in the `concept_frequency` chart, their effective rubric size (the `N` in the hypergeometric null model) is 15. Requesting the full `expected_concepts` list would artificially inflate `N` with concepts the educator never saw and therefore could never have edited.
**(b)** Yes, to ensure consistency across old and new logs, capping the fallback `rubric_size` at 15 in `analyze_study_logs.py` (for logs that used the old extraction) is a good idea so the hypergeometric `N` remains consistent.

## Q2 — `score_ablation_v2.py`: `ABLATION_DATASET = 'mohler'`
**Confirmed.** `'mohler'` is the correct dataset name. The ablation checkpoint (`ablation_checkpoint_gemini_flash_latest.json`) and the LaTeX table generation in `score_ablation_v2.py` are specifically hardcoded for the Mohler dataset ($n=120$). If this script is later adapted to run across multiple datasets, parameterizing `ABLATION_DATASET` (e.g., via `argparse`) would be the right approach, but for now, the hardcoded constant is correct.

## Q3 — `analyze_study_logs.py`: `_MAX_DWELL_MS` cap applied to beacon dwell
**Agree with the suggested fix.** The beacon value is already corrected for tab visibility (using the Page Visibility API). Capping it at 10 minutes would artificially truncate legitimate, long dwell times. The 10-minute cap should *only* apply to the wall-clock fallback path to prevent overnight sessions from inflating the median. The suggested code snippet is correct:
```python
if isinstance(dwell_ms, (int, float)) and dwell_ms > 0:
    computed = int(dwell_ms)                                      # trust beacon
elif aid in pending_views:
    computed = min(max(0, ts - pending_views[aid]['start_ts']), _MAX_DWELL_MS)  # cap fallback only
```

## Q4 — `analyze_study_logs.py`: `write_edits_csv()` excludes list/dict fields
**(a)** Yes, `source_contradicts_nodes_60s` and `session_contradicts_nodes` should be serialized as pipe-delimited strings (e.g., `"nodeA|nodeB"`) in the edits CSV. This preserves the attribution context for analysts who want to re-derive H2 or inspect the exact nodes without needing to cross-reference the session-level CSV or the raw JSONL files.

## Q5 — `visualization.service.ts`: `loadJson` `NotFoundException` silent exclusion
**Silent exclusion is correct.** This mimics standard filesystem race condition handling. If a file is deleted between `readdir` and `stat` (a TOCTOU race), it effectively no longer exists and should not be included in the dataset list. Throwing or bubbling up the error would break the `/datasets` endpoint for all other valid datasets. Adding a `Logger.warn` could be useful for debugging, but silent exclusion is safe and expected here.

## Q6 — `analyze_study_logs.py`: `import statistics` scattered
**Yes**, `import statistics` should be moved to the top-level module imports (alongside `import json`, `import os`, etc.). While Python caches imports so there is no performance penalty, consolidating them at the top of the file is standard Python practice and improves stylistic consistency.

## Q7 — `score_ablation_v2.py`: `OSError` fallback prints WARNING to stdout
**Agree.** The warning should be printed to `sys.stderr` so it remains visible even if the researcher pipes the standard output (the ablation table) to a file. Including the exception class name is also a good practice for debugging.
Suggested fix:
```python
except OSError as e:
    print(f"WARNING: Could not read batch_responses/ directory: {type(e).__name__} - {e}", file=sys.stderr)
    print("  Proceeding without sentinel check — verify batch completeness manually.", file=sys.stderr)
    flags = []
```

---
**Summary of Next Steps:**
1. Implement the beacon dwell fix in `analyze_study_logs.py`.
2. Update `write_edits_csv()` to serialize list fields as pipe-delimited strings.
3. Move `import statistics` to the top of `analyze_study_logs.py`.
4. Update the `OSError` warning in `score_ablation_v2.py` to use `sys.stderr` and include the exception type.
5. Cap legacy `rubric_size` at 15 in `analyze_study_logs.py`.