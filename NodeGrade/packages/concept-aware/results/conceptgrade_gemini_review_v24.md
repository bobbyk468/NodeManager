# ConceptGrade — Code Review v24 for Gemini

## Context

This review covers the five fixes applied in response to v23 feedback (Q1, Q3, Q4, Q6, Q7).
Q2 and Q5 required no code changes (confirmed correct / silent exclusion accepted).
The questions below verify correctness of the applied fixes and raise three new issues
discovered during implementation.

---

## Q1 — analyze_study_logs.py: rubric_size capped at 15 at parse time — does this mask future schema changes?

**File:** `packages/concept-aware/analyze_study_logs.py`, rubric_edit parser block

The v23 fix caps `rubric_size` at 15 when reading from the payload:

```python
'rubric_size': min(payload.get('rubric_size', 0), 15),
```

And changes the legacy fallback from `max(m_flagged, 20)` to `max(m_flagged, 15)`.

The cap is motivated by the fact that `concept_frequency` shows at most 15 bars.
However, the cap is hardcoded as a magic number in two places. If the frontend is later
updated to show more concepts (e.g., top-20 via a UI change), the analyzer would
silently truncate correct `rubric_size` values from new logs without any warning,
producing a systematic undercount of N in the hypergeometric test.

**Question:** Should `15` be extracted as a named constant (e.g.,
`CONCEPT_FREQUENCY_MAX_BARS = 15`) at the top of the file alongside `_MAX_DWELL_MS`,
so both magic numbers are co-located and easy to update together?

---

## Q2 — analyze_study_logs.py: write_edits_csv() pipe-delimiter — empty lists serialize as empty string

**File:** `packages/concept-aware/analyze_study_logs.py`, `write_edits_csv()`

The fix serialises list fields as pipe-delimited strings:

```python
k: '|'.join(str(x) for x in v) if isinstance(v, list) else v
```

When `source_contradicts_nodes_60s` or `session_contradicts_nodes` is an empty list
`[]`, `'|'.join(...)` produces an empty string `""`. In R or pandas, an empty string
is read as a valid (non-missing) value, making it indistinguishable from a missing
field. An analyst filtering `source_contradicts_nodes_60s != ""` to find edits with
CONTRADICTS context would silently include zero-context edits.

**Question:** Should empty lists be serialised as `None` (which becomes an empty CSV
cell, read as `NA` in R and `NaN` in pandas) rather than `""`?

```python
k: ('|'.join(str(x) for x in v) if v else None) if isinstance(v, list) else v
```

---

## Q3 — analyze_study_logs.py: statistics.median() raises StatisticsError on empty list — two unguarded sites

**File:** `packages/concept-aware/analyze_study_logs.py`

`statistics.median()` raises `StatisticsError: no median for empty sequence` when
called on an empty list. After consolidating to a top-level import, two call sites
that were previously guarded by local try/except no longer have that protection:

1. **`aggregate_by_condition()`** — `seed_dwells` and `non_seed_dwells` are filtered
   from `all_dwells`. If no session in a condition has any `answer_view_end` events
   (e.g., Condition A participants who never opened the drill-down panel), both lists
   are empty and `statistics.median(non_seed_dwells)` in the `seed_dwell_ratio`
   computation raises.

   ```python
   seed_dwell_ratio = (
       round(statistics.median(seed_dwells) / statistics.median(non_seed_dwells), 3)
       if seed_dwells and non_seed_dwells else None   # ← this guard is correct
   )
   ```
   This site is already guarded — `seed_dwell_ratio` is only computed when both lists
   are non-empty. ✓

2. **`_median_dwell_by()`** — the comprehension filters `if vs` before calling median:

   ```python
   return {k: round(statistics.median(vs) / 1000, 2) for k, vs in grps.items() if vs}
   ```
   `if vs` is truthy only when the list is non-empty. ✓

3. **`print_report()`** — `statistics.median(b_hyper)` is called inside `if b_hyper:`
   which guards the empty case. ✓

All three sites appear correctly guarded. This question is a verification request.

**Question:** Please confirm that no additional `statistics.median()` or
`statistics.mean()` / `statistics.stdev()` call sites in the file are unguarded
against empty input, given that the local import-wrapping previously masked any
`StatisticsError` that would have been raised.

---

## Q4 — score_ablation_v2.py: sys.stderr warning — sys is already imported?

**File:** `packages/concept-aware/score_ablation_v2.py`, line 13

The OSError warning now uses `file=sys.stderr`:

```python
print(f"WARNING: ...", file=sys.stderr)
```

The existing import line is:

```python
import json, os, sys
```

`sys` is already imported — the `file=sys.stderr` fix is safe. This is a verification
question.

**Question:** Confirm that `sys` is present in the import line and no additional import
is needed. Also: should the sentinel block's `sys.exit(1)` calls (which already exist
in the function) be updated to `sys.exit(2)` to distinguish a sentinel-detected abort
(data integrity error) from a missing-file abort (user error)? Exit code 1 is currently
used for both cases.

---

## Q5 — New: analyze_study_logs.py: aggregate_by_condition() references `statistics` but local import was removed — confirm no NameError

**File:** `packages/concept-aware/analyze_study_logs.py`, `aggregate_by_condition()`

Before the v23 fix, `aggregate_by_condition()` began with `import statistics` as a
local import, which guaranteed the name was bound inside the function scope. After the
fix, `statistics` is only imported at the module level (line 55). The function now
relies on the module-level binding.

The calls inside `aggregate_by_condition()` that use `statistics` are:

```python
def mean_of(key: str) -> Optional[float]:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(statistics.mean(vals), 2) if vals else None

def std_of(key: str) -> Optional[float]:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(statistics.stdev(vals), 2) if len(vals) >= 2 else None
```

These are nested functions defined inside `aggregate_by_condition()`. Python resolves
`statistics` via LEGB: Local → Enclosing → Global → Built-in. Since `statistics` is
not local or enclosing, it resolves to the module-level global — correct.

**Question:** This is a verification request. Confirm that the removal of the local
`import statistics` inside `aggregate_by_condition()` does not introduce a `NameError`
at runtime, given that `statistics` is now a module-level name resolved via the global
scope.

---

## Q6 — New: analyze_study_logs.py: write_edits_csv() — session_id field duplicated if edit dict already contains it

**File:** `packages/concept-aware/analyze_study_logs.py`, `write_edits_csv()`

Each rubric_edit record now includes a `session_id` key (added in the v21 rubric_edit
parser):

```python
rubric_edits.append({
    'ts':         ts,
    'session_id': session_id,   # ← added in v21
    ...
})
```

`write_edits_csv()` also prepends `session_id` from the session metric:

```python
rows.append({
    'session_id': m['session_id'],   # from session level
    'condition':  m['condition'],
    **{k: v ... for k, v in edit.items() ...},  # edit-level — also has session_id
})
```

When the `**edit` spread is applied, `session_id` from the edit dict overwrites the
one from `m['session_id']`. Both values should be identical (they are set from the
same source), so this does not produce wrong data. However, it is a latent bug: if
a JSONL file were ever corrupted such that `event.session_id` differs from the
filename-derived session key used to group events, the edit-level `session_id` would
silently overwrite the session-level one, producing inconsistent rows.

**Question:** Should the `**edit` spread explicitly exclude `session_id` (since it is
already set from the session metric) to make the precedence explicit and prevent the
silent overwrite?

```python
**{k: ... for k, v in edit.items() if k != 'session_id' and not isinstance(v, dict)},
```

---

## Summary Table

| # | File | Severity | Category |
|---|------|----------|----------|
| Q1 | analyze_study_logs.py | Low | Magic number `15` in two places — suggest named constant |
| Q2 | analyze_study_logs.py | Medium | Empty list → `""` in pipe-delimited CSV; should be `None` |
| Q3 | analyze_study_logs.py | Low | Verification: `statistics.median()` empty-list guards |
| Q4 | score_ablation_v2.py | Low | Verification: `sys` import + `sys.exit` code distinction |
| Q5 | analyze_study_logs.py | Low | Verification: module-level `statistics` resolves in nested functions |
| Q6 | analyze_study_logs.py | Medium | `session_id` duplicated in `write_edits_csv()` — silent overwrite |

**Priority:** Fix Q2 (empty list → None) and Q6 (session_id precedence) before pilot.
Q1 is a readability improvement. Q3, Q4, Q5 are verification-only — no code change
expected if confirmed correct.
