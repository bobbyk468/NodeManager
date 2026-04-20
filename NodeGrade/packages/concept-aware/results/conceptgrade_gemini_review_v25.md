# ConceptGrade — Code Review v25 for Gemini

## Context

This review covers the three code changes applied in response to v24 feedback
(Q1, Q2+Q6 combined, Q4). Q3 and Q5 were verification-only with no code changes.
The questions below verify the applied fixes and raise three new issues.

---

## Q1 — analyze_study_logs.py: CONCEPT_FREQUENCY_MAX_BARS used in two places — verify no third site

**File:** `packages/concept-aware/analyze_study_logs.py`

`CONCEPT_FREQUENCY_MAX_BARS = 15` now replaces the hardcoded `15` in two locations:

1. At rubric_edit parse time: `min(payload.get('rubric_size', 0), CONCEPT_FREQUENCY_MAX_BARS)`
2. At hypergeometric N fallback: `n_rubric = max(m_flagged, CONCEPT_FREQUENCY_MAX_BARS)`

**Question:** Confirm there is no third site that still uses the magic number `15` in
relation to rubric size or concept frequency in this file or in any related analysis
script (e.g., `stability_analysis.py`, `run_lrm_ablation.py`).

---

## Q2 — analyze_study_logs.py: write_edits_csv() None serialization — DictWriter behaviour

**File:** `packages/concept-aware/analyze_study_logs.py`, `write_edits_csv()`

The fix serialises empty lists as `None`:

```python
k: ('|'.join(str(x) for x in v) if v else None) if isinstance(v, list) else v
```

`csv.DictWriter` in Python serialises `None` as the string `"None"` by default, not as
an empty cell. An empty cell requires either `None` mapped to `''` via
`DictWriter(restval='')`, or an explicit `'' if v is None else ...` conversion.

```python
import csv
import io
w = csv.DictWriter(io.StringIO(), fieldnames=['x'])
w.writerow({'x': None})   # writes: "None\r\n"  ← NOT an empty cell
```

To produce an empty cell (read as `NA` in R), the value must be `''` (empty string),
not `None`.

**Question:** Should the serialisation be changed to `''` instead of `None` for empty
lists, and should `DictWriter` be instantiated with `restval=''` to ensure all missing
keys also produce empty cells rather than the string `"None"`?

---

## Q3 — score_ablation_v2.py: sys.exit(2) for sentinel abort — shell convention alignment

**File:** `packages/concept-aware/score_ablation_v2.py`

Exit code 2 is a POSIX convention for "misuse of shell built-ins" and is commonly
used by command-line tools (e.g., `grep`, `diff`) to signal usage errors.
Exit code 1 conventionally means "general error". Using `sys.exit(2)` for a
data-integrity sentinel abort is non-standard — most shell scripts and CI pipelines
treat any non-zero exit as failure and do not distinguish between 1 and 2.

The inline comment documents the intent:
```python
sys.exit(2)  # exit(2) = data integrity abort; exit(1) = missing-file / user error
```

**Question:** Is the distinction between exit code 1 and 2 actually consumed by any
downstream CI script or Makefile in this project? If not, `sys.exit(1)` with the
comment would serve the same practical purpose with less confusion for shell users
unfamiliar with the exit-code convention.

---

## Q4 — New: analyze_study_logs.py: write_edits_csv() — 'ts' field name collides with common R column name

**File:** `packages/concept-aware/analyze_study_logs.py`, rubric_edit records

Each rubric_edit record includes `'ts': ts` (Unix ms timestamp). In the edits CSV,
this becomes a column named `ts`. In R, `ts` is a built-in function (`time series`);
assigning `ts` as a column name in a `data.frame` is legal but will shadow the
built-in if the analyst does `attach(df)` — a common exploratory pattern.

Additionally, `ts` is an ambiguous abbreviation. The session-level events already use
`timestamp_ms` as the field name in `StudyEvent` (from `studyLogger.ts`).

**Question:** Should the `ts` field be renamed to `timestamp_ms` in the rubric_edit
records stored in `raw_edits` (in `analyse_session()`), so the edits CSV column name
matches the top-level `StudyEvent.timestamp_ms` schema and avoids the R built-in
shadow?

---

## Q5 — New: analyze_study_logs.py: aggregate_by_condition() — statistics.stdev() called with n=1 guard

**File:** `packages/concept-aware/analyze_study_logs.py`, `std_of()` inside
`aggregate_by_condition()`

```python
def std_of(key: str) -> Optional[float]:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(statistics.stdev(vals), 2) if len(vals) >= 2 else None
```

`statistics.stdev()` requires at least 2 values (it raises `StatisticsError` with n=1).
The guard `if len(vals) >= 2` correctly handles this. However, for a pilot study with
n=4 per condition (2 participants per arm), condition-level standard deviations will
have df=1 — extremely noisy but technically valid. The `print_report()` function
currently does not print standard deviations at all (only means), so `std_of()` is
computed but never displayed.

**Question:** Is `std_of()` used anywhere in `print_report()` or `write_csv()`? If it
is only computed but never consumed, it is dead code that adds computation overhead
and should be removed.

---

## Summary Table

| # | File | Severity | Category |
|---|------|----------|----------|
| Q1 | analyze_study_logs.py | Low | Verify no third magic-number `15` site |
| Q2 | analyze_study_logs.py | **High** | `None` → `"None"` in DictWriter; need `''` for empty CSV cell |
| Q3 | score_ablation_v2.py | Low | `sys.exit(2)` convention question — may revert to `exit(1)` |
| Q4 | analyze_study_logs.py | Low | `ts` field name shadows R built-in; suggest `timestamp_ms` |
| Q5 | analyze_study_logs.py | Low | `std_of()` may be dead code if never printed or written |

**Priority:** Fix Q2 immediately — it is a correctness bug where `None` becomes the
string `"None"` in the CSV, making the field non-missing in R/pandas. All other items
are low-risk and can be addressed in the next review cycle.
