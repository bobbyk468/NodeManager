# ConceptGrade — Code Review v21 for Gemini

## Context

This review covers seven issues identified after applying the v20 exception-handling fixes
and after completing `analyze_study_logs.py`. The questions span:

- A stale HTTP status comment in `study.controller.ts`
- Methodological weaknesses in the GEE approximation inside `analyze_study_logs.py`
- A hypergeometric rubric-size underestimate (H2 validity)
- Missing dwell-time and benchmark analysis for `answer_view` events
- Absent sentinel-file guard in `score_ablation_v2.py`
- In-memory file cache with no TTL in `visualization.service.ts`
- Durability gap when both localStorage and Beacon fail simultaneously

All questions assume the v20 fixes are already applied. Respond only on what is asked;
do not suggest refactors beyond the scope of each question.

---

## Q1 — study.controller.ts: Stale JSDoc says "204 No Content" but endpoint returns 200

**File:** `packages/backend/src/study/study.controller.ts`, line 22

The JSDoc comment was written when the endpoint returned `Promise<void>` with `@HttpCode(204)`.
After the v20 fix it now returns `Promise<{ ok: boolean; error?: string }>`, which NestJS
serialises as HTTP 200 with a JSON body.

```typescript
/**
 * Returns 204 No Content on success so the browser fetch stays fire-and-forget
 * without waiting for a response body.    ← stale
 */
@Post('log')
async logEvent(@Body() event: unknown): Promise<{ ok: boolean; error?: string }> {
  return this.studyService.appendEvent(event);
}
```

The callers in `studyLogger.ts` use `.catch(() => {})` only — they never read the response
body — so 200 vs 204 has no functional impact. However, the comment asserts 204, which
misleads future maintainers and auditors.

**Question:** Should the JSDoc be updated to reflect 200 + body, or should the endpoint
be reverted to HTTP 204 (return void, re-add `@HttpCode(204)`) to restore the fire-and-forget
contract? Which choice better preserves IRB auditability — the body that signals disk failure
(`ok: false`) or the simpler 204?

---

## Q2 — analyze_study_logs.py: GEE edit-row expansion introduces ordering bias

**File:** `packages/concept-aware/analyze_study_logs.py`, lines 472–480

The GEE analysis requires one row per rubric edit. Because only session-level summary counts
are stored (`rubric_edits_within_30s`, `rubric_edits`), the script expands sessions to edit
rows by arbitrarily assigning the first `n_within_30` rows the label `within_30s = 1` and
the rest `within_30s = 0`:

```python
for i in range(n_edits):
    rows.append({
        'session_id':      sid,
        'condition':       cond,
        'trace_gap_count': gap,            # session mean, same for all rows
        'within_30s':      1 if i < n_within_30 else 0,   # ← ordering assumption
    })
```

Two compounding biases:
1. **Ordering bias** — early edits are assumed to be the attributed ones. If educators
   typically interact with the trace mid-session (not at the start), this mislabels rows.
2. **Constant covariate** — `trace_gap_count` is the session mean, identical for every
   row of that session. GEE with an exchangeable correlation structure will treat all rows
   as exchangeable, which is correct structurally, but the constant covariate makes the
   within-cluster variance artificially zero, inflating the precision of `trace_gap_count`
   regression coefficients.

The comment on line 463 already acknowledges this:
> "Session-level approximation — re-derive from raw JSONL event logs for full study."

**Question:** For the paper's primary GEE analysis (H1 temporal, within_30s ~
condition * trace_gap_count | session_id), what is the minimum change to
`analyze_study_logs.py` that replaces the approximation with a correct per-edit expansion
from raw JSONL events? Specifically: (a) where in `analyse_session()` should the raw
per-edit list be returned alongside the aggregates, and (b) should `run_gap_moderation_analysis()`
accept raw edit records instead of session summary dicts?

---

## Q3 — analyze_study_logs.py: Hypergeometric rubric size N underestimates population

**File:** `packages/concept-aware/analyze_study_logs.py`, lines 274–276

The hypergeometric null model (H2, semantic alignment) uses the number of distinct edited
concepts as the rubric size N:

```python
n_rubric = len({e['concept_id'] for e in rubric_edits})  # proxy for rubric size
```

If an educator can edit 20 rubric concepts but only edits 5, `N = 5` instead of 20.
This makes the draw denominator smaller than the true population, which inflates the
precision of the hypergeometric test and can produce spuriously small p-values.

The correct N is the total number of concepts in the rubric that the educator was shown,
not just the concepts they happened to edit.

**Question:** (a) Is the true rubric size available from `session_contradicts_nodes`
or from another field in the rubric_edit payload? (b) If not available client-side,
should the frontend emit a `rubric_size` field in each rubric_edit payload (total
concepts visible in the RubricEditorPanel at the moment of the edit), or is there
a defensible fallback constant (e.g., 20 as currently used in the `max()` guard)?

---

## Q4 — analyze_study_logs.py: answer_view_start/end events are never parsed

**Files:**
- `packages/frontend/src/utils/studyLogger.ts` — defines `AnswerDwellPayload` with
  `dwell_time_ms`, `trace_panel_open`, `kg_panel_open`, `benchmark_case`, `severity`, etc.
- `packages/concept-aware/analyze_study_logs.py` — `analyse_session()` handles
  `page_view`, `task_start`, `task_submit`, `chart_hover`, `tab_change`, `trace_interact`,
  `rubric_edit` — but not `answer_view_start` or `answer_view_end`.

This creates two gaps:

1. **Dwell time per answer is never computed.** The `answer_view_end` event carries
   `dwell_time_ms` (ms the educator spent reading that answer). This is listed in the
   AGENT_EVALUATION_GUIDE.md Phase 4 analysis plan as a secondary behavioral metric for
   Condition B but is currently ignored by the analyzer.

2. **Benchmark seed performance is never measured.** `AnswerDwellPayload.benchmark_case`
   is injected for seeded answers (`fluent_hallucination`, `unorthodox_genius`,
   `lexical_bluffer`, `partial_credit_needle`). The study's pre-registered goal is to
   measure whether Condition B educators dwell longer on seeded trap answers than
   Condition A educators. Without parsing `answer_view_end`, this analysis cannot run.

**Question:** (a) What per-session metrics should `analyse_session()` emit for dwell
time (mean, median per condition? per severity level? per benchmark_case?)
(b) For benchmark seed analysis, should `aggregate_by_condition()` emit
`mean_dwell_per_benchmark_case` broken out by all four seed types, or is a single
`seed_dwell_ratio` (seed dwell / non-seed dwell) sufficient to test the hypothesis?

---

## Q5 — score_ablation_v2.py: No sentinel file guard before running

**File:** `packages/concept-aware/score_ablation_v2.py`, lines 48–62

The script loads ablation response files from `/tmp/` and baseline data from `data/`:

```python
con_path = "/tmp/ablation_concepts_v2_response.json"
tax_path = "/tmp/ablation_taxonomy_v2_response.json"

missing = []
if not os.path.exists(con_path):
    missing.append(con_path)
```

The batch evaluation pipeline (`run_batch_eval_api.py`) writes sentinel `.flag` files when
a quota is exhausted mid-batch:

```python
sentinel = os.path.join(BATCH_DIR, f"{dataset}_INCOMPLETE_{i}of{len(batch_files)}.flag")
```

`score_ablation_v2.py` never checks for these sentinels. If the batch was interrupted,
the ablation response files are partial, but the script runs silently and produces
misleading ablation metrics that feed directly into Table 1 of the paper.

**Question:** (a) Should `score_ablation_v2.py` scan `data/batch_responses/` for any
`*.flag` file before loading scores and abort with an explicit error message if found?
(b) Should the check be dataset-scoped (only reject if the ablation dataset's flag exists)
or global (reject if any flag exists, regardless of dataset)?

---

## Q6 — visualization.service.ts: In-memory fileCache has no TTL or invalidation path

**File:** `packages/backend/src/visualization/visualization.service.ts`, lines 86–101

The service caches parsed JSON in a `Map<string, unknown>` that lives for the NestJS
server process lifetime:

```typescript
private readonly fileCache = new Map<string, unknown>();

private async loadJson<T>(filePath: string): Promise<T> {
  if (!this.fileCache.has(filePath)) {
    const raw = await readFile(filePath, 'utf8');
    // ...parse and store...
  }
  return this.fileCache.get(filePath) as T;
}
```

During a live study session, a researcher might re-run `run_batch_eval_api.py` to update
results for a dataset. Without a server restart, the cached (pre-update) data continues
to be served to the dashboard. This is unlikely during an active participant session but
is a correctness hazard during iterative analysis.

A secondary concern: `isPerSampleEvalFile()` calls `loadJson` in a `try/catch { return false }`.
If `loadJson` throws `InternalServerErrorException` for a malformed file, the error is
swallowed by `isPerSampleEvalFile`, the file is excluded from `listDatasets()`, and the
cache entry is never set. If the file is later fixed on disk, the cache miss correctly
re-reads it — this is correct behaviour, but only because `loadJson` never caches on
parse failure. Confirm this is intentional.

**Question:** (a) For a research tool (not production), is the no-invalidation trade-off
acceptable as long as it is documented (e.g., a JSDoc note saying "restart server to pick
up new eval files")? (b) Alternatively, is a lightweight file-mtime check on each request
more appropriate — and if so, where should `fs.stat` be inserted relative to the
`fileCache.has()` guard?

---

## Q7 — logBeacon() has no third durability tier for private-browsing + backend-down

**File:** `packages/frontend/src/utils/studyLogger.ts`, lines 221–249

`logBeacon()` provides two durability tiers:
1. `safeLocalStorageAppend()` — best-effort localStorage
2. `navigator.sendBeacon()` — reliable delivery during page unload (requires `studyApiBase`)

If a participant uses private/incognito browsing AND the backend is unreachable, both
tiers fail silently. The `safeLocalStorageAppend` path catches `SecurityError` (private
browsing) and skips, and `sendBeacon` is a no-op when `studyApiBase` is null.

IRB data-loss risk: `answer_view_end` events for the last few answers a participant views
before closing the tab are captured only via `logBeacon`. If the participant uses a
browser that rejects localStorage (Safari ITP, Firefox private mode) and the backend is
unreachable, these events are lost with no researcher notification.

Note: `logEvent()` (fetch-based) has the same two-tier structure. But logEvent is used
for non-unload events where a fetch() completes normally; the risk is lower there.

**Question:** (a) Is a third tier needed for IRB compliance, e.g., storing a session
summary to `sessionStorage` (not blocked by ITP) before each page unload? (b) Or is
the study's consent form + protocol checklist (backend must be reachable, standard browser
required) sufficient to exclude this scenario by design, making a third tier unnecessary?

---

## Summary Table

| # | File | Severity | Category |
|---|------|----------|----------|
| Q1 | study.controller.ts | Low | Stale comment / HTTP contract |
| Q2 | analyze_study_logs.py | **Critical** | GEE ordering bias → H1 validity |
| Q3 | analyze_study_logs.py | **High** | Hypergeometric N underestimate → H2 validity |
| Q4 | analyze_study_logs.py | **High** | Missing answer_view + benchmark analysis |
| Q5 | score_ablation_v2.py | **High** | Silent partial-data ablation → Table 1 error |
| Q6 | visualization.service.ts | Low | Cache TTL / mtime correctness |
| Q7 | studyLogger.ts | Medium | Durability gap in private browsing |

**Priority for pilot:** Fix Q2, Q3, Q4, Q5 before running any participant sessions.
Q1 and Q6 are documentation/tooling issues with no user-facing impact.
Q7 requires a protocol decision (IRB consent vs. code fix).
