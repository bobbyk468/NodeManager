# Gemini Review Response v21

---

## Q1 — study.controller.ts: Stale JSDoc says "204 No Content" but endpoint returns 200

**Decision:** Update the JSDoc to reflect `200` + body.
**Rationale:** Reverting to `204 No Content` would mean discarding the error handling added in v20 (which returns `{ ok: false, error: ... }` on disk write failure). For IRB auditability, it is much more valuable to retain a response body that signals disk failure so that the client (or a monitoring tool observing network responses) can potentially log or react to the failure, rather than silently failing on the backend. The fire-and-forget nature on the client side is preserved by simply not awaiting or reading the response body.
**Draft fix (JSDoc update):**
```typescript
/**
 * Returns 200 OK with { ok: boolean, error?: string }.
 * The browser fetch can remain fire-and-forget. A 200 is always returned 
 * (even on disk write errors) to prevent interrupting the participant's flow, 
 * but the body indicates whether the backend successfully persisted the event.
 */
@Post('log')
async logEvent(@Body() event: unknown): Promise<{ ok: boolean; error?: string }> {
  return this.studyService.appendEvent(event);
}
```

---

## Q2 — analyze_study_logs.py: GEE edit-row expansion introduces ordering bias

**Decision:** Modify `analyse_session()` to return raw per-edit records, and update the GEE analysis to use them.
**Rationale:** The current approximation introduces unacceptable ordering bias and artificially deflates variance by using the session mean `trace_gap_count` for all rows. A valid GEE analysis for H1 requires the actual, per-event values for `within_30s` (which was recorded at the time of the edit) and ideally the precise `trace_gap_count` at that moment (or the specific trace gap interacted with). 
**(a) Where to return the list:** In `analyse_session()`, alongside the aggregate dict, you should accumulate and return a list of the parsed `rubric_edit` events for that session.
**(b) Should `run_gap_moderation_analysis()` accept raw edit records:** Yes, `run_gap_moderation_analysis()` must be updated to accept a flattened list of these raw per-edit records across all sessions, rather than the session summary dicts, to properly construct the GEE dataframe.

---

## Q3 — analyze_study_logs.py: Hypergeometric rubric size N underestimates population

**Decision:** Frontend should emit a `rubric_size` field.
**Rationale:** Using a fallback constant (like 20) is statistically indefensible if the actual number of visible concepts varies per answer or condition. Calculating N from only the *edited* concepts is mathematically incorrect and guarantees an inflated false-positive rate for H2. 
**(a) Is the true size available?** Not reliably from the current backend payloads without reconstructing the exact UI state.
**(b) Solution:** The frontend has exact knowledge of how many concepts are rendered in the `RubricEditorPanel`. It should simply include `rubric_size: number` in the `RubricEditPayload` at the moment of the edit. `analyze_study_logs.py` should then use this explicit value for N.

---

## Q4 — analyze_study_logs.py: answer_view_start/end events are never parsed

**Decision:** Parse `answer_view_end` and compute required metrics.
**Rationale:** Dwell time and benchmark trap performance are core secondary metrics for the paper. Ignoring them leaves the Condition B behavioral analysis incomplete.
**(a) Per-session metrics:** `analyse_session()` should extract `dwell_time_ms` from `answer_view_end` events and emit: `mean_dwell_time`, `median_dwell_time`, and a dictionary of `mean_dwell_by_severity` and `mean_dwell_by_benchmark_case` (for answers that had one).
**(b) Benchmark seed analysis:** A single `seed_dwell_ratio` is too reductive because the four pedagogical traps (hallucination, unorthodox, lexical, partial) likely elicit different cognitive behaviors. `aggregate_by_condition()` should emit `mean_dwell_per_benchmark_case` broken out by all four seed types to provide nuanced findings for the paper.

---

## Q5 — score_ablation_v2.py: No sentinel file guard before running

**Decision:** Scan for sentinel `.flag` files and abort.
**Rationale:** Silently running on partial data invalidates Table 1. Explicitly failing prevents bad data from reaching the paper draft.
**(a) Should it scan and abort?** Yes, `score_ablation_v2.py` must check for `.flag` files in the responses/data directory before proceeding.
**(b) Scope of check:** It should be **dataset-scoped**. If the user is scoring the Digiklausur ablation and the Digiklausur quota exhausted, it must abort. If a Mohler flag exists but Mohler isn't being scored, it shouldn't block the Digiklausur run.

---

## Q6 — visualization.service.ts: In-memory fileCache has no TTL or invalidation path

**Decision:** Accept the no-invalidation trade-off, add JSDoc, and confirm the error-swallowing behavior is correct.
**Rationale:** For a research prototype, adding a TTL cache or file-watcher adds unnecessary complexity and potential race conditions.
**(a) Is it acceptable?** Yes, provided it is explicitly documented. Researchers can easily restart the local NestJS server during iterative analysis.
**(b) File-mtime check?** No, a lightweight mtime check (`fs.stat`) on every request negates the performance benefit of the in-memory cache for a single-user research tool. 
**Confirmation on error swallowing:** Yes, swallowing the `InternalServerErrorException` in `isPerSampleEvalFile` so that a malformed file is simply excluded from `listDatasets()` (and not cached) is the correct and safest behavior.

---

## Q7 — logBeacon() has no third durability tier for private-browsing + backend-down

**Decision:** Rely on the study's protocol/consent checklist.
**Rationale:** Attempting to engineer a foolproof third tier (like `sessionStorage`) adds complexity for an edge case that should be administratively prevented.
**(a) Is a third tier needed?** No. `sessionStorage` is cleared when the tab closes anyway, so it doesn't solve the "participant closed the tab while backend was down" scenario. 
**(b) Protocol sufficiency:** The IRB protocol and pre-study instructions must explicitly require participants to use a standard (non-private/incognito) browser window and ensure a stable connection. This administrative control is standard practice for ecological user studies and is sufficient.
