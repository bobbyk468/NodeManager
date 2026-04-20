# ConceptGrade — Code Review v22 for Gemini

## Context

This review covers the changes applied in response to the v21 recommendations (Q1–Q7).
All six code fixes have been implemented; Q7 was resolved via protocol (no code change).
The questions below verify correctness of the fixes, probe edge cases introduced by the
new code, and raise one new issue discovered during implementation.

---

## Q1 — analyze_study_logs.py: _median_dwell_by() shadows outer `groups` variable

**File:** `packages/concept-aware/analyze_study_logs.py` (inside `aggregate_by_condition()`)

The new `_median_dwell_by()` helper is defined inside the `for cond, rows in sorted(groups.items()):` loop. It declares its own local `groups: dict[str, list[int]] = defaultdict(list)`, which shadows the outer `groups` variable from `aggregate_by_condition`. Python's LEGB scoping means the inner assignment creates a new local, so the outer `groups` is not mutated. However, static type checkers (pyright, mypy) will flag this as a shadow of an outer variable, which can be confusing for future readers.

Additionally, `_median_dwell_by` is re-defined on every iteration of the `for cond, rows` loop (once per condition), capturing `all_dwells` via closure. The closure capture is correct because the function is called immediately within the same loop body. But if it were ever extracted to a different call site, the closure would silently capture the last value of `all_dwells`.

```python
def _median_dwell_by(key: str) -> dict[str, float]:
    groups: dict[str, list[int]] = defaultdict(list)   # shadows outer groups
    for d in all_dwells:                               # captured via closure
        ...
```

**Question:** Should `_median_dwell_by` be (a) renamed to use an underscore-prefixed
variable internally (`grps` instead of `groups`) to avoid the shadow, and (b) extracted
as a module-level helper that takes `dwells` as an explicit parameter instead of relying
on closure? This would make the function unit-testable in isolation.

---

## Q2 — analyze_study_logs.py: GEE approximation note in docstring still references old approach

**File:** `packages/concept-aware/analyze_study_logs.py`, `run_gap_moderation_analysis()` docstring (around line 462)

The docstring still contains this line from the v20 implementation:
> "Session-level approximation — re-derive from raw JSONL event logs for full study."

After the v21 fix, `run_gap_moderation_analysis()` now uses exact per-edit rows from
`m['raw_edits']` — the approximation is gone. But the docstring has not been updated,
so it now contradicts the implementation.

**Question:** Please confirm the updated docstring text for `run_gap_moderation_analysis()`.
The key points to reflect: (a) each row is one rubric_edit event with its own
`trace_gap_count` and `within_30s` as captured at edit time; (b) the "session-level
approximation" warning should be removed; (c) the working correlation ρ note should be
retained as it is still valid.

---

## Q3 — score_ablation_v2.py: sentinel check uses `os.listdir` which can raise on permission error

**File:** `packages/concept-aware/score_ablation_v2.py`, new sentinel guard block

The sentinel check iterates `os.listdir(batch_dir)`:

```python
if os.path.isdir(batch_dir):
    flags = [f for f in os.listdir(batch_dir) if f.endswith(".flag")]
```

`os.listdir` raises `PermissionError` (or `OSError`) if the directory exists but is not
readable (e.g., on a shared filesystem where another process holds a lock). This would
crash the script before it even checks for missing input files, producing a confusing
traceback instead of a clear message.

Additionally, the sentinel check is global across all datasets — it will block even if
the `.flag` file belongs to a dataset unrelated to the ablation being computed. The v21
recommendation was dataset-scoped (only reject if the ablation dataset's flag exists),
but the implementation is currently global.

**Question:** (a) Should the `os.listdir` call be wrapped in a try/except OSError that
prints a warning and continues rather than aborting? (b) Should the flag file pattern be
narrowed to only match flags for the datasets used in this ablation (e.g., check for
`ablation_checkpoint_gemini_flash_latest` dataset name as a prefix)?

---

## Q4 — visualization.service.ts: stat() call on every request adds one syscall per file

**File:** `packages/backend/src/visualization/visualization.service.ts`, `loadJson()`

The v21 mtime fix adds a `stat()` call on every `loadJson()` invocation:

```typescript
private async loadJson<T>(filePath: string): Promise<T> {
  const fileStat = await stat(filePath);
  const currentMtime = fileStat.mtimeMs;
  const cached = this.fileCache.get(filePath);
  if (cached && cached.mtimeMs === currentMtime) {
    return cached.data as T;
  }
  // ...re-read file
}
```

For a dashboard request that loads 3 datasets with 2 extra files each (eval + extras),
this adds 6 stat() syscalls per page load. On a local dev machine this is negligible
(~0.1 ms each). However, `isPerSampleEvalFile()` also calls `loadJson()` inside
`listDatasets()`, which now also triggers a stat() for each candidate file. If DATA_DIR
contains many `*_eval_results.json` files, this multiplies.

Additionally: if `stat(filePath)` throws (e.g., the file is deleted between the
`existsSync()` check and the `stat()` call), the error propagates as an unhandled
rejection — currently no try/catch wraps the `stat()` call.

**Question:** (a) Is the stat()-per-request cost acceptable for a research tool where
data freshness is more important than microsecond latency? (b) Should the `stat()` call
be wrapped in a try/catch that falls back to serving the cached data (if any) rather than
throwing, to handle the TOCTOU race between `existsSync` and `stat`?

---

## Q5 — analyze_study_logs.py: answer_view_end fallback wall-clock delta can inflate dwell

**File:** `packages/concept-aware/analyze_study_logs.py`, new `answer_view_end` parser block

When `dwell_time_ms` is absent from the payload (e.g., old log format or capture_method
is null), the code falls back to computing dwell from the wall-clock delta between
`answer_view_start.timestamp_ms` and `answer_view_end.timestamp_ms`:

```python
elif aid in pending_views:
    computed = max(0, ts - pending_views[aid]['start_ts'])
```

This is correct for normal navigation, but will produce an inflated dwell if:
1. The educator switched browser tabs mid-review (Page Visibility API pauses dwell
   accumulation in the frontend, but the wall-clock delta ignores this).
2. The educator left a session open overnight and resumed the next day.

The payload also carries `capture_method: 'cleanup' | 'beacon' | null`, which can
distinguish reliable captures from potentially unreliable ones.

**Question:** Should the fallback wall-clock delta be capped at a maximum (e.g., 10
minutes) to prevent overnight-session outliers from distorting median dwell time?
And should events with `capture_method == null` (incomplete sessions) be excluded from
the dwell analysis or flagged separately?

---

## Q6 — RubricEditorPanel.tsx: rubric_size derived from extractConceptsFromSpecs may undercount

**File:** `packages/frontend/src/components/charts/RubricEditorPanel.tsx`, lines 72–90

The `rubric_size: concepts.length` field uses the `concepts` array derived from
`extractConceptsFromSpecs(specs)`:

```typescript
function extractConceptsFromSpecs(specs: VisualizationSpec[]): string[] {
  const concepts = new Set<string>();
  for (const spec of specs) {
    if (spec.viz_id === 'concept_frequency' || spec.viz_type === 'bar_chart') {
      const items = (spec.data as any)?.items ?? [];   // field name mismatch: data.bars not data.items
      ...
    }
    if (spec.insights) {
      // regex heuristic to extract PascalCase_snake concepts from insight strings
    }
  }
}
```

Two issues:
1. **Field name mismatch:** The `concept_frequency` spec stores concepts under
   `data.bars` (see `visualization.service.ts` `buildConceptFrequency`), not `data.items`.
   So `(spec.data as any)?.items ?? []` is always an empty array — the spec-based
   concept extraction never fires. The only concepts extracted come from the insight
   string regex heuristic.

2. **Insight regex is not the source of truth:** The regex `\b[A-Z][a-z]+(?:_[A-Z][a-z]+)+\b`
   matches PascalCase_snake identifiers in insight strings, which is unreliable.
   `rubric_size` is intended to represent the number of concepts the educator can edit,
   but this approach yields a count driven by what insights mention, not what is visible
   in the rubric panel's concept list.

The consequence: `rubric_size` in rubric_edit events is likely 0 or a small
undercount, making the v21 hypergeometric N fix partially ineffective (the
`rubric_sizes` fallback in `analyze_study_logs.py` will still use the legacy `max(m_flagged, 20)` path).

**Question:** (a) Should `extractConceptsFromSpecs` be fixed to read from `data.bars`
(not `data.items`) for the `concept_frequency` spec? (b) Is the concept_frequency bar
list the correct ground truth for rubric_size, or should the rubric panel receive the
full expected concept list from the KG (via a separate API field) to ensure rubric_size
reflects concepts the educator was actually shown?

---

## Q7 — New: analyze_study_logs.py write_csv() does not include raw_edits / answer_dwells columns

**File:** `packages/concept-aware/analyze_study_logs.py`, `write_csv()`

The `write_csv()` function uses `list(session_metrics[0].keys())` as fieldnames. After
the v21 changes, `session_metrics` now includes `raw_edits` (a list of dicts) and
`answer_dwells` (a list of dicts) as keys. `csv.DictWriter` will serialize these lists
as their Python repr strings (e.g., `[{'ts': 123, ...}]`), which are not parseable by
downstream tools (R, pandas).

```python
def write_csv(session_metrics: list[dict], out_path: Path) -> None:
    fieldnames = list(session_metrics[0].keys())   # now includes raw_edits, answer_dwells
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
```

**Question:** Should `write_csv()` explicitly exclude `raw_edits` and `answer_dwells`
from the CSV fieldnames (since they are nested lists, not scalars)? A separate
`write_edits_csv()` function could export the flattened per-edit records with
`session_id` and `condition` joined in for downstream GEE analysis in R.

---

## Summary Table

| # | File | Severity | Category |
|---|------|----------|----------|
| Q1 | analyze_study_logs.py | Low | `_median_dwell_by` shadow + closure coupling |
| Q2 | analyze_study_logs.py | Low | Stale docstring contradicts implementation |
| Q3 | score_ablation_v2.py | Medium | `os.listdir` unguarded + global (not dataset-scoped) sentinel |
| Q4 | visualization.service.ts | Low | stat() per request + TOCTOU race |
| Q5 | analyze_study_logs.py | Medium | Wall-clock dwell fallback may inflate on tab-switch / overnight |
| Q6 | RubricEditorPanel.tsx | **High** | `rubric_size` likely 0 due to `data.items` vs `data.bars` mismatch |
| Q7 | analyze_study_logs.py | Medium | `write_csv()` serializes list-typed columns as repr strings |

**Priority:** Fix Q6 first — without it the hypergeometric N remains broken despite
the v21 fix. Q3, Q5, Q7 are correctness issues that should be resolved before pilot.
Q1, Q2, Q4 are low-priority documentation/robustness issues.
