# ConceptGrade — Code Review v23 for Gemini

## Context

This review covers the seven fixes applied in response to v22 feedback. All items from
the v22 action plan have been implemented. The questions below verify correctness,
probe edge cases introduced by the new code, and raise two new issues discovered
during implementation.

---

## Q1 — RubricEditorPanel.tsx: extractConceptsFromSpecs now reads data.bars — is concept_frequency the right ground truth for rubric_size?

**File:** `packages/frontend/src/components/charts/RubricEditorPanel.tsx`, lines 72–96

The v22 fix corrected the field name from `data.items` to `data.bars` and narrowed the
spec filter to `viz_id === 'concept_frequency'` only:

```typescript
if (spec.viz_id === 'concept_frequency') {
  const bars = (spec.data as any)?.bars ?? [];
  for (const bar of bars) {
    if (bar?.concept) concepts.add(String(bar.concept));
  }
}
```

`concept_frequency` shows the **top 15 matched concepts** by frequency — concepts that
at least one student in the class mentioned. However, `rubric_size` for the
hypergeometric null model (H2) should represent the total number of concepts the
educator was shown and could theoretically edit, not just the 15 most common ones.

The full expected concept list per question lives in the KG
(`*_auto_kg.json → question_kgs[qId].expected_concepts`). On average a question has
8–12 expected concepts; concept_frequency truncates at 15 across the entire dataset.
For a dataset with 5 questions × 10 expected concepts, the true rubric could have up
to 50 unique concepts, while concept_frequency would show at most 15.

**Question:** (a) Should the frontend request the full expected concept list from
`GET /api/visualization/datasets/:dataset/sample/:sampleId/xai` (which returns
`expected_concepts`) and use its length as `rubric_size`, or is top-15 an acceptable
approximation given that educators are unlikely to edit concepts they never see?
(b) If top-15 is acceptable, should the `rubric_size` value be capped at 15 in
`analyze_study_logs.py` for logs that used the old (broken) extraction, so that the
hypergeometric N is consistent across old and new logs?

---

## Q2 — score_ablation_v2.py: ABLATION_DATASET = 'mohler' is hardcoded — needs verification

**File:** `packages/concept-aware/score_ablation_v2.py`, line 21

```python
ABLATION_DATASET = 'mohler'
```

This constant is used to scope the sentinel file check:

```python
flags = [
    f for f in os.listdir(batch_dir)
    if f.endswith(".flag") and f.startswith(ABLATION_DATASET + "_")
]
```

The ablation reads `data/ablation_checkpoint_gemini_flash_latest.json` and
`data/gemini_kg_dual_scores.json`. Neither filename contains a dataset prefix, so
`ABLATION_DATASET` was inferred from context.

**Question:** Please confirm that `'mohler'` is the correct dataset name for the
ablation checkpoint (i.e., that `ablation_checkpoint_gemini_flash_latest.json` was
produced from Mohler data). If the ablation spans multiple datasets, should
`ABLATION_DATASET` be a list and the sentinel check scan for flags matching any entry?

---

## Q3 — analyze_study_logs.py: _MAX_DWELL_MS cap applied to beacon dwell — is this correct?

**File:** `packages/concept-aware/analyze_study_logs.py`, answer_view_end parser block

The v22 fix caps both the beacon-delivered `dwell_time_ms` and the wall-clock fallback
at `_MAX_DWELL_MS = 600_000` (10 minutes):

```python
if isinstance(dwell_ms, (int, float)) and dwell_ms > 0:
    computed = int(min(dwell_ms, _MAX_DWELL_MS))   # ← beacon value also capped
elif aid in pending_views:
    computed = min(max(0, ts - pending_views[aid]['start_ts']), _MAX_DWELL_MS)
```

The beacon value is computed by the frontend using the Page Visibility API (pauses
accumulation on tab hide), so it is already corrected for tab switching. Capping a
legitimate beacon value at 10 minutes would truncate real dwell times for educators who
spend > 10 minutes carefully reading a complex answer — a plausible scenario for
`unorthodox_genius` benchmark seeds.

**Question:** Should the 10-minute cap apply only to the wall-clock fallback path
(where tab-switch inflation is possible) and not to the beacon-delivered value (which
is already Tab-Visibility-corrected)? Suggested fix:

```python
if isinstance(dwell_ms, (int, float)) and dwell_ms > 0:
    computed = int(dwell_ms)                                      # trust beacon
elif aid in pending_views:
    computed = min(max(0, ts - pending_views[aid]['start_ts']), _MAX_DWELL_MS)  # cap fallback only
```

---

## Q4 — analyze_study_logs.py: write_edits_csv() excludes list/dict fields silently

**File:** `packages/concept-aware/analyze_study_logs.py`, `write_edits_csv()`

```python
rows.append({
    'session_id': m['session_id'],
    'condition':  m['condition'],
    **{k: v for k, v in edit.items() if not isinstance(v, (list, dict))},
})
```

Each rubric_edit record contains two list-typed fields:
- `source_contradicts_nodes_60s: list[str]` — CONTRADICTS node IDs in 60 s window
- `session_contradicts_nodes: list[str]` — all CONTRADICTS nodes this session

These are silently dropped from the edits CSV. For the GEE analysis in R, only scalar
columns are needed (`within_30s`, `trace_gap_count`, `condition`, `session_id`), so
dropping lists is correct. However, `session_contradicts_nodes` is also used to compute
the hypergeometric p-value in `analyse_session()` — if an analyst re-derives H2 from
the edits CSV rather than the session-level CSV, they lose this field.

**Question:** (a) Should `source_contradicts_nodes_60s` and `session_contradicts_nodes`
be serialised as pipe-delimited strings (e.g., `"nodeA|nodeB"`) in the edits CSV rather
than silently dropped, so analysts can recover the attribution context?
(b) Or is the session-level CSV (`study_analysis.csv`) the canonical source for those
fields, making the edits CSV exclusively for GEE scalar inputs?

---

## Q5 — visualization.service.ts: loadJson NotFoundException import now used — confirm no regression

**File:** `packages/backend/src/visualization/visualization.service.ts`, line 1

The v22 TOCTOU fix added a `NotFoundException` throw inside `loadJson()` when `stat()`
fails and no cache is available:

```typescript
throw new NotFoundException(`File not found or removed: ${path.basename(filePath)}`);
```

`NotFoundException` was already imported at line 1:

```typescript
import { Injectable, InternalServerErrorException, NotFoundException } from '@nestjs/common';
```

`loadJson()` is also called from `isPerSampleEvalFile()`, which wraps the call in
`try { ... } catch { return false; }`. If `stat()` throws for a malformed path passed
from `listDatasets()`, `isPerSampleEvalFile()` catches the NotFoundException and returns
`false` — the file is silently excluded from the dataset list. This is the same
behaviour as before the mtime fix.

**Question:** Is this silent exclusion the correct behaviour, or should `listDatasets()`
log a warning when `isPerSampleEvalFile()` returns false due to a stat failure (vs.
returning false because the file lacks per-sample scores)?

---

## Q6 — New: analyze_study_logs.py: _median_dwell_by imports statistics on every call

**File:** `packages/concept-aware/analyze_study_logs.py`, `_median_dwell_by()`

The module-level helper imports `statistics` on every invocation:

```python
def _median_dwell_by(dwells: list[dict], key: str) -> dict[str, float]:
    import statistics as _st
    ...
```

`statistics` is already imported inside `aggregate_by_condition()` (`import statistics`)
and inside `print_report()` (`import statistics as _st`). Python caches module imports
after the first load (`sys.modules`), so subsequent `import` statements are O(1) dict
lookups — there is no performance penalty. However, three separate local imports of the
same module are stylistically inconsistent.

**Question:** Should `import statistics` be moved to the top-level module imports
(alongside `import json`, `import os`, etc.) to consolidate all stdlib imports in one
place and eliminate the three scattered local imports?

---

## Q7 — New: score_ablation_v2.py: OSError fallback prints WARNING but continues — is this safe?

**File:** `packages/concept-aware/score_ablation_v2.py`, sentinel guard block

```python
except OSError as e:
    print(f"WARNING: Could not read batch_responses/ directory: {e}")
    print("  Proceeding without sentinel check — verify batch completeness manually.")
    flags = []
```

If `os.listdir` raises `PermissionError` (a subclass of `OSError`) on a shared
filesystem where another process holds a lock, the script proceeds without any sentinel
check. If the batch is genuinely incomplete at that moment (another process is writing),
the ablation produces corrupt results silently.

The warning is printed to stdout, which is mixed with the ablation table output and
may be missed by a researcher piping output to a file.

**Question:** Should the OSError warning be printed to `sys.stderr` instead of stdout
so it is visible even when stdout is redirected? And should the warning message include
the full exception class name (e.g., `PermissionError`) to help diagnose the root cause?

---

## Summary Table

| # | File | Severity | Category |
|---|------|----------|----------|
| Q1 | RubricEditorPanel.tsx | **High** | rubric_size = top-15 may undercount true rubric N |
| Q2 | score_ablation_v2.py | **High** | ABLATION_DATASET='mohler' needs confirmation |
| Q3 | analyze_study_logs.py | Medium | Beacon dwell should not be capped — only wall-clock fallback |
| Q4 | analyze_study_logs.py | Medium | List fields dropped silently from edits CSV |
| Q5 | visualization.service.ts | Low | Silent exclusion on stat failure in isPerSampleEvalFile |
| Q6 | analyze_study_logs.py | Low | `import statistics` scattered across 3 local sites |
| Q7 | score_ablation_v2.py | Low | OSError warning to stdout may be missed when piping |

**Priority before pilot:** Confirm Q2 (correct dataset name), fix Q3 (beacon cap),
decide Q1 (rubric_size ground truth). Q4–Q7 are low-risk and can be deferred.
