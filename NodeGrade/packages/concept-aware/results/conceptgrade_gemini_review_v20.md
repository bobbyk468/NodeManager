# Gemini Review Request v20
**Date:** 2026-04-18  
**Paper:** IEEE VIS 2027 VAST — "ConceptGrade: Visual Co-Auditing of AI Reasoning to Externalize Educator Mental Models"  
**Prior rounds:** v1–v19 (all decisions locked)  
**This round:** Exception Handling Audit — full-stack review across Python pipeline, NestJS backend, and React frontend

---

## Context

Following the v13 code review of `AGENT_EVALUATION_GUIDE.md`, a systematic audit of exception handling across all three layers of the ConceptGrade stack was conducted. This review documents every unhandled or inadequately handled error path, organized by severity. Each finding includes the exact file, the code pattern in question, the failure scenario, and a proposed fix.

The three layers audited:
1. **Python pipeline** — `conceptgrade/pipeline.py`, `conceptgrade/verifier.py`, `run_batch_eval_api.py`, `conceptgrade/key_rotator.py`, `stability_analysis.py`
2. **TypeScript backend** — `packages/backend/src/visualization/visualization.service.ts`, `packages/backend/src/study/study.service.ts`
3. **TypeScript frontend** — `packages/frontend/src/utils/studyLogger.ts`

---

## Finding 1 — CRITICAL: `assess_class()` ThreadPoolExecutor swallows student-level exceptions

**File:** `packages/concept-aware/conceptgrade/pipeline.py`  
**Lines:** 479–484

**Current code:**
```python
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = {
        pool.submit(_assess, sid, ans): sid
        for sid, ans in student_items
    }
    for future in as_completed(futures):
        results.append(future.result())  # ← NO try-except
```

**Failure scenario:** If any single student's assessment raises an uncaught exception (e.g., a malformed answer triggers a `UnicodeDecodeError`, or the Groq API returns an unexpected schema change), `future.result()` re-raises that exception into the main thread — crashing the **entire class assessment** and losing results for all other students whose futures completed successfully.

**Why this matters for the paper:** The Mohler evaluation runs 120 assessments in a batch. If answer #73 triggers an API schema change mid-run, answers 1–72 are lost. The cached results on disk are from a prior run, so `run_batch_eval_api.py` has no way to detect that the current run was incomplete.

**Proposed fix:**
```python
for future in as_completed(futures):
    sid = futures[future]
    try:
        results.append(future.result())
    except Exception as e:
        err = str(e)
        # Re-raise rate-limit errors: they should abort the batch
        # so the caller can implement backoff at the orchestration level.
        if "429" in err or "529" in err or "rate_limit" in err.lower():
            raise
        # For all other failures: record a failed placeholder so the
        # batch result is complete (N outputs for N inputs) and the
        # analysis scripts can detect and skip failed entries.
        print(f"  [assess_class] Student {sid} FAILED: {type(e).__name__}: {e}")
        failed = StudentAssessment(student_id=sid, question=question, answer="")
        failed.concept_graph = {"error": str(e)}
        results.append(failed)
```

**Please answer:**
1. Is the proposed per-future try-except the right pattern, or should the orchestrator be responsible for retry logic?
2. Should failed assessments be re-tried once (with a fresh API key) before recording as failed, or recorded immediately?

---

## Finding 2 — CRITICAL: `loadJson()` in `visualization.service.ts` has no `SyntaxError` guard

**File:** `packages/backend/src/visualization/visualization.service.ts`  
**Lines:** 89–95

**Current code:**
```typescript
private async loadJson<T>(filePath: string): Promise<T> {
  if (!this.fileCache.has(filePath)) {
    const raw = await readFile(filePath, 'utf8');
    this.fileCache.set(filePath, JSON.parse(raw));  // ← throws SyntaxError if malformed
  }
  return this.fileCache.get(filePath) as T;
}
```

**Failure scenario:** If a `*_eval_results.json` file is corrupted (e.g., truncated by a disk-full condition during `run_batch_eval_api.py`'s `json.dump()` write), `JSON.parse()` throws a `SyntaxError`. NestJS catches this as an unhandled exception and returns a 500. The in-memory `fileCache` is NOT populated (the `set()` was never called), so every subsequent request also throws — the dataset is permanently broken for the lifetime of the server process.

**Proposed fix:**
```typescript
private async loadJson<T>(filePath: string): Promise<T> {
  if (!this.fileCache.has(filePath)) {
    const raw = await readFile(filePath, 'utf8');
    try {
      this.fileCache.set(filePath, JSON.parse(raw));
    } catch (e) {
      throw new Error(
        `Malformed JSON in eval results file '${path.basename(filePath)}': ${(e as Error).message}. ` +
        `Re-run run_batch_eval_api.py --dataset <name> to regenerate.`
      );
    }
  }
  return this.fileCache.get(filePath) as T;
}
```

**Please answer:**
1. Should the malformed-file error surface as a 500 (unrecoverable) or a 503 (retry after fix)? NestJS `HttpException` can be thrown with a specific status code.
2. Should a corrupted file cause the dataset to be excluded from `listDatasets()` results, or hard-fail requests for that dataset only?

---

## Finding 3 — CRITICAL: `study.service.ts` `appendFile` has no error handling

**File:** `packages/backend/src/study/study.service.ts`  
**Lines:** 32–33

**Current code:**
```typescript
await appendFile(logPath, JSON.stringify(event) + '\n', 'utf8');
// ← ENOSPC (disk full), EACCES (permission denied), or ENOENT
//   all become unhandled promise rejections
```

**Failure scenario:** During study execution, if the disk fills up (after accumulating many sessions' JSONL files), `appendFile` throws `ENOSPC`. This propagates as an unhandled promise rejection and causes the `POST /api/study/log` endpoint to return a 500. Study participants in Condition B see an error — which may break the ecological validity of the study if they notice.

**Proposed fix:**
```typescript
async appendEvent(event: unknown): Promise<{ ok: boolean; error?: string }> {
  // ... (mkdir guard unchanged) ...
  
  try {
    await appendFile(logPath, JSON.stringify(event) + '\n', 'utf8');
    return { ok: true };
  } catch (e) {
    const err = e as NodeJS.ErrnoException;
    const msg = `[StudyService] Failed to append event: ${err.code} — ${err.message}`;
    console.error(msg);
    // Return 200 OK to the frontend — log failure must never break participant flow.
    // The frontend's localStorage copy remains intact as the fallback.
    return { ok: false, error: msg };
  }
}
```

**Controller change:**
```typescript
@Post('log')
async logEvent(@Body() dto: StudyEventDto): Promise<{ ok: boolean }> {
  return this.studyService.appendEvent(dto);
  // Returns 200 with { ok: false, error: ... } on disk error
  // Frontend never sees a 5xx — study flow is uninterrupted
}
```

**Please answer:**
1. Is returning `200 { ok: false }` (instead of 500) the correct approach for preserving study ecological validity?
2. Should disk-error incidents trigger an email/Slack alert to the researcher (e.g., via a `console.error` that's captured by the server monitoring setup)?

---

## Finding 4 — HIGH: Bare `except Exception: pass` in `_tmp_comp` block silently loses errors

**File:** `packages/concept-aware/conceptgrade/pipeline.py`  
**Lines:** 303–309

**Current code:**
```python
try:
    if concept_graph_obj:
        _tmp_comp = KnowledgeGraphComparator(
            domain_graph=self.domain_graph
        ).compare(student_graph=concept_graph_obj).to_dict()
except Exception:
    pass  # ← no logging, no variable, no re-raise — completely silent
```

**Failure scenario:** If `KnowledgeGraphComparator.compare()` raises (e.g., a `KeyError` in the graph traversal, or a `TypeError` from an unexpected node format), the error is silently swallowed. The `_tmp_comp` dict remains `{}`, which means Bloom's and SOLO classifiers receive empty `comparison_result` context — silently degrading classification quality. There is no way to detect this happened from the output JSON.

**Proposed fix:**
```python
try:
    if concept_graph_obj:
        _tmp_comp = KnowledgeGraphComparator(
            domain_graph=self.domain_graph
        ).compare(student_graph=concept_graph_obj).to_dict()
except Exception as e:
    print(f"  [Pipeline] _tmp_comp failed ({type(e).__name__}: {e}) — Bloom/SOLO will use empty context")
    _tmp_comp = {}  # same fallback, but now visible in logs
```

**Please answer:** Is there any reason this exception should remain silent? If so, document the rationale.

---

## Finding 5 — HIGH: `logEvent()` and `logBeacon()` bare `catch {}` conflates three distinct error types

**File:** `packages/frontend/src/utils/studyLogger.ts`  
**Lines:** 156–162, 211–217

**Current code (both functions):**
```typescript
try {
  const existing: StudyEvent[] = JSON.parse(localStorage.getItem(LOG_KEY) ?? '[]');
  existing.push(event);
  localStorage.setItem(LOG_KEY, JSON.stringify(existing));
} catch {
  // localStorage unavailable — silently skip
}
```

**Three distinct failure modes conflated into a single silent catch:**

| Exception | Cause | Correct handling |
|-----------|-------|-----------------|
| `DOMException (SecurityError)` | Private browsing / cookies disabled | Silent skip — appropriate |
| `DOMException (QuotaExceededError)` | Storage full after many sessions | Log count to console; switch to server-only mode |
| `SyntaxError` from `JSON.parse` | `localStorage['ng-study-log']` corrupted | Reset the key and retry the write |

**Failure scenario:** A participant spends 45 minutes in Condition B. After ~30 minutes, `localStorage` fills up. Every subsequent event is silently dropped — including all the rubric edits the researcher needs for H1/H2 analysis. The backend server-side copy is still intact, but the participant's export (which they might do if the server is unreachable) is missing the second half of the session.

**Proposed fix:**
```typescript
function safeLocalStorageAppend(event: StudyEvent): void {
  try {
    const existing: StudyEvent[] = JSON.parse(localStorage.getItem(LOG_KEY) ?? '[]');
    existing.push(event);
    localStorage.setItem(LOG_KEY, JSON.stringify(existing));
  } catch (e) {
    if (e instanceof DOMException) {
      if (e.name === 'QuotaExceededError') {
        // Storage full: trim oldest 20% and retry once
        try {
          const existing: StudyEvent[] = JSON.parse(localStorage.getItem(LOG_KEY) ?? '[]');
          const trimmed = existing.slice(Math.floor(existing.length * 0.2));
          trimmed.push(event);
          localStorage.setItem(LOG_KEY, JSON.stringify(trimmed));
          if (import.meta.env.DEV) {
            console.warn('[StudyLog] localStorage quota hit — trimmed oldest 20% of events');
          }
        } catch {
          // Still full after trim — rely on backend flush only
        }
      }
      // SecurityError (private browsing) or other DOMException: silent skip
    } else if (e instanceof SyntaxError) {
      // Corrupted JSON: reset and retry
      localStorage.removeItem(LOG_KEY);
      try {
        localStorage.setItem(LOG_KEY, JSON.stringify([event]));
      } catch {
        // If reset also fails, rely on backend flush
      }
    }
  }
}
```

**Please answer:**
1. Is the "trim oldest 20%" approach the right tradeoff for QuotaExceededError — or should the log be cleared entirely (losing all local data, backend copy is canonical)?
2. For the SyntaxError reset: is there any scenario where resetting the localStorage key silently drops important events that hadn't been flushed to the backend yet?

---

## Finding 6 — HIGH: `import traceback` inside except block in `verifier.py`

**File:** `packages/concept-aware/conceptgrade/verifier.py`  
**Lines:** 393–402

**Current code:**
```python
except Exception as e:
    # Fallback: trust KG score
    import traceback          # ← import inside except block
    print(f"  [Verifier] FALLBACK triggered — {type(e).__name__}: {e}")
    traceback.print_exc()
    verified = kg_score
    ...
```

**Problem:** `import traceback` inside an except block is a minor but reviewable code smell:
1. In CPython it works (modules are cached after first import), but it creates a confusing pattern for agents reading the file.
2. If the exception is triggered before `traceback` has been imported in any other module, the `import` itself could fail in a deeply restricted environment (e.g., a sandboxed LLM execution environment).

**Proposed fix:** Move `import traceback` to the top of the file alongside other standard library imports.

**Please answer:** Is there a reason `traceback` was imported inside the except block (e.g., to avoid import-time cost in production runs where `verify()` succeeds)? If so, a `if __debug__: import traceback` guard would be more explicit.

---

## Finding 7 — MEDIUM: `run_batch_eval_api.py` writes no partial-completion marker on quota exhaustion

**File:** `packages/concept-aware/run_batch_eval_api.py`  
**Lines:** 134–137

**Current code:**
```python
elif "quota" in err_msg.lower():
    print(f"\n    QUOTA EXHAUSTED: {err_msg}")
    print("    Cannot continue. Remaining batches need manual submission.")
    return saved_paths  # ← returns partial list; no file written
```

**Failure scenario:** The researcher runs `--dataset digiklausur` with 15 batch files. After batch #8, quota exhausts. The script returns paths for batches 1–7. On the next run (same day, same quota), the script sees batches 1–7 as `already done` and batches 8–15 as unprocessed — correct behavior. However, if the researcher runs `score_ablation_v2.py` before re-running (e.g., forgetting the quota exhaustion), it silently scores only 7/15 batches, producing a partial Table 2 with no warning.

**Proposed fix:**
```python
elif "quota" in err_msg.lower():
    print(f"\n    QUOTA EXHAUSTED at batch {i}/{len(batch_files)}: {err_msg}")
    # Write a sentinel file so downstream scripts detect incomplete runs
    sentinel = os.path.join(BATCH_DIR, f"{dataset}_INCOMPLETE_{i}of{len(batch_files)}.flag")
    with open(sentinel, 'w') as f:
        f.write(json.dumps({
            'exhausted_at_batch': i,
            'total_batches': len(batch_files),
            'saved_paths': saved_paths,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }))
    print(f"    Sentinel written: {sentinel}")
    print("    Re-run after quota resets. Remaining batches will resume automatically.")
    return saved_paths
```

**Please answer:** Should `score_ablation_v2.py` check for these sentinel files before running, or is a print warning sufficient?

---

## Finding 8 — MEDIUM: `key_rotator.py` doesn't distinguish transient network errors from rate limits

**File:** `packages/concept-aware/conceptgrade/key_rotator.py`  
**Lines:** 135–145

**Current code:**
```python
except Exception as e:
    err_str = str(e)
    if "429" in err_str or "rate_limit" in err_str.lower():
        old = self._idx
        self.next_key()
        # ... retry
    else:
        last_error = e
        # falls through; eventually raises
```

**Problem:** `ConnectionError`, `TimeoutError`, and `SSLError` are non-rate-limit transient errors that the rotator should retry on the **same key** (not rotate). Rotating on a connection timeout wastes a key slot and shifts load unnecessarily.

**Proposed fix:**
```python
import socket
TRANSIENT_NETWORK_ERRORS = (
    ConnectionError,
    TimeoutError,
    socket.timeout,
    # Add: httpx.ConnectTimeout, requests.Timeout if those SDKs are in use
)

except Exception as e:
    err_str = str(e)
    if "429" in err_str or "rate_limit" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
        self.next_key()       # Rate limit: rotate key
    elif isinstance(e, TRANSIENT_NETWORK_ERRORS):
        time.sleep(2 ** attempt)  # Transient network: backoff, same key
    else:
        last_error = e        # Unrecognized error: propagate after retries
```

**Please answer:** Are `ConnectionError` / `TimeoutError` actually observed during batch evaluation runs, or is the current handling sufficient for the scale of this study?

---

## Finding 9 — LOW: `stability_analysis.py` `__main__` block has no file-not-found guard

**File:** `packages/concept-aware/stability_analysis.py` (as specified in AGENT_EVALUATION_GUIDE.md)  
**Current code:**
```python
if __name__ == '__main__':
    ablation = json.load(open('data/lrm_ablation_summary.json'))  # ← FileNotFoundError
    flash_traces = ablation['gemini_flash_traces']                 # ← KeyError
    deepseek_traces = ablation['deepseek_traces']                  # ← KeyError
```

**Failure scenario:** If the researcher runs `stability_analysis.py` before Task A1 (`run_lrm_ablation.py`) has completed, `FileNotFoundError` is thrown with a generic traceback. The error message gives no guidance on what to run first.

**Proposed fix:**
```python
if __name__ == '__main__':
    import sys
    ablation_path = 'data/lrm_ablation_summary.json'
    if not os.path.exists(ablation_path):
        print(f"ERROR: {ablation_path} not found.")
        print("Run `python run_lrm_ablation.py` first to generate ablation traces.")
        sys.exit(1)
    
    try:
        with open(ablation_path) as f:
            ablation = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: {ablation_path} is malformed JSON: {e}")
        print("Re-run `python run_lrm_ablation.py --force` to regenerate.")
        sys.exit(1)
    
    required_keys = ['gemini_flash_traces', 'deepseek_traces']
    for k in required_keys:
        if k not in ablation:
            print(f"ERROR: '{k}' not found in {ablation_path}. Keys present: {list(ablation.keys())}")
            sys.exit(1)
    
    flash_traces = ablation['gemini_flash_traces']
    deepseek_traces = ablation['deepseek_traces']
    result = stability_analysis(flash_traces, deepseek_traces)
    print(json.dumps(result, indent=2))
    with open('data/stability_analysis_result.json', 'w') as f:
        json.dump(result, f, indent=2)
```

**Please answer:** Should `stability_analysis.py` also validate that the traces dict is non-empty and that each answer's steps list is non-empty before computing correlations?

---

## Finding 10 — LOW: `readdirSync()` in `visualization.service.ts` is not guarded against post-startup permission errors

**File:** `packages/backend/src/visualization/visualization.service.ts`  
**Lines:** 97–107

**Current code:**
```typescript
async listDatasets(): Promise<string[]> {
  if (!existsSync(DATA_DIR)) return [];
  const files = readdirSync(DATA_DIR).filter(...);  // ← synchronous; throws if permissions change
  ...
}
```

**Problem:** `existsSync` guards against the directory not existing at request time, but `readdirSync` is synchronous and will throw `EACCES` or `EPERM` if the directory's permissions change after server startup (e.g., after a system administrator modifies file permissions during study execution). Since this is a synchronous call inside an async method, NestJS's async error handler may not catch it correctly in all versions.

**Proposed fix:**
```typescript
async listDatasets(): Promise<string[]> {
  try {
    const files = await readdir(DATA_DIR);  // Use async readdir, not sync
    const filtered = files.filter((f) => f.endsWith('_eval_results.json'));
    const checks = await Promise.all(
      filtered.map(async (f) => {
        const ok = await this.isPerSampleEvalFile(path.join(DATA_DIR, f));
        return ok ? f.replace('_eval_results.json', '') : null;
      }),
    );
    return checks.filter((x): x is string => x !== null);
  } catch (e) {
    const err = e as NodeJS.ErrnoException;
    if (err.code === 'ENOENT') return [];
    throw new Error(`Cannot read dataset directory '${DATA_DIR}': ${err.message}`);
  }
}
```

**Please answer:** Is `readdirSync` used elsewhere in the service that should also be migrated to the async `readdir`?

---

## Summary Table

| # | Severity | Layer | File | Pattern | Fix Required |
|---|----------|-------|------|---------|-------------|
| 1 | **CRITICAL** | Python | `pipeline.py` | `future.result()` without per-future try-except in `assess_class()` | Yes — per-future handler |
| 2 | **CRITICAL** | TS Backend | `visualization.service.ts` | `JSON.parse()` in `loadJson()` no SyntaxError catch | Yes — wrap with descriptive error |
| 3 | **CRITICAL** | TS Backend | `study.service.ts` | `appendFile()` unhandled promise rejection | Yes — return `{ ok: false }` on error |
| 4 | **HIGH** | Python | `pipeline.py` | `except Exception: pass` in `_tmp_comp` block | Yes — add print() |
| 5 | **HIGH** | TS Frontend | `studyLogger.ts` | Bare `catch {}` conflates QuotaExceededError / SyntaxError / SecurityError | Yes — discriminated handling |
| 6 | **HIGH** | Python | `verifier.py` | `import traceback` inside except block | Minor — move to top-level import |
| 7 | **MEDIUM** | Python | `run_batch_eval_api.py` | No sentinel file on quota exhaustion | Yes — write `.flag` file |
| 8 | **MEDIUM** | Python | `key_rotator.py` | All non-429 exceptions treated identically | Recommended — separate network errors |
| 9 | **LOW** | Python | `stability_analysis.py` | `__main__` block has no file-not-found / key validation | Yes — exit with helpful message |
| 10 | **LOW** | TS Backend | `visualization.service.ts` | `readdirSync()` synchronous; no EACCES guard | Recommended — switch to async `readdir` |

---

## Expected Output Format

For each finding:
1. **Decision** (approve fix / reject / modify)
2. **Rationale** (2–3 sentences — especially for any finding you want to reject or defer)
3. **Draft fix** (paste-ready code, if modification is recommended)

**Priority this round:** Findings 1, 2, 3 (all CRITICAL — must fix before study launch), then Finding 5 (HIGH — data integrity risk during multi-hour study sessions).

---

**End of Gemini Review v20**
