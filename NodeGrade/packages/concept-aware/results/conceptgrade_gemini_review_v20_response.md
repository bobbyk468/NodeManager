Here is the completed code review addressing the exception handling audit outlined in your v20 document. I have provided decisions, rationale, and draft fixes for all 10 findings, prioritizing the critical and high-severity issues as requested.

---

### Finding 1 — CRITICAL: `assess_class()` ThreadPoolExecutor swallows student-level exceptions

**1. Decision:** Approve fix
**2. Rationale:** The proposed per-future try-except is the correct pattern. The orchestrator should handle batch-level rate limits (which the fix re-raises), but student-level failures (like parsing errors) should be caught and recorded so that the batch doesn't fail completely. Recording them immediately is best; retries for non-transient errors (like malformed JSON) will just fail again and waste time.
**3. Draft fix:**
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
        # For all other failures: record a failed placeholder
        print(f"  [assess_class] Student {sid} FAILED: {type(e).__name__}: {e}")
        failed = StudentAssessment(student_id=sid, question=question, answer="")
        failed.concept_graph = {"error": str(e)}
        results.append(failed)
```

---

### Finding 2 — CRITICAL: `loadJson()` in `visualization.service.ts` has no `SyntaxError` guard

**1. Decision:** Modify
**2. Rationale:** A corrupted file should surface as a 500 (Internal Server Error) because it's a server-side state issue that the client cannot fix by retrying. A 503 implies a temporary overload. The corrupted dataset should hard-fail requests for that dataset so the researcher is explicitly aware it's broken, rather than silently hiding it from `listDatasets()`.
**3. Draft fix:**
```typescript
import { InternalServerErrorException } from '@nestjs/common';

private async loadJson<T>(filePath: string): Promise<T> {
  if (!this.fileCache.has(filePath)) {
    const raw = await readFile(filePath, 'utf8');
    try {
      this.fileCache.set(filePath, JSON.parse(raw));
    } catch (e) {
      throw new InternalServerErrorException(
        `Malformed JSON in eval results file '${path.basename(filePath)}': ${(e as Error).message}. ` +
        `Re-run run_batch_eval_api.py --dataset <name> to regenerate.`
      );
    }
  }
  return this.fileCache.get(filePath) as T;
}
```

---

### Finding 3 — CRITICAL: `study.service.ts` `appendFile` has no error handling

**1. Decision:** Approve fix
**2. Rationale:** Returning `200 OK` with `{ ok: false }` is essential for ecological validity; study participants shouldn't see backend infrastructure errors. Disk errors should absolutely trigger an alert (via `console.error` for server logs, which monitoring tools will pick up) so researchers know to intervene before the study completes.
**3. Draft fix:**
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
*(Controller change is approved as proposed in the request)*

---

### Finding 4 — HIGH: Bare `except Exception: pass` in `_tmp_comp` block silently loses errors

**1. Decision:** Approve fix
**2. Rationale:** There is no valid reason to swallow exceptions silently here. Silently degrading classification quality without logs makes debugging impossible. Logging the error ensures visibility while maintaining the fallback behavior.
**3. Draft fix:**
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

---

### Finding 5 — HIGH: `logEvent()` and `logBeacon()` bare `catch {}` conflates three distinct error types

**1. Decision:** Approve fix
**2. Rationale:** The "trim oldest 20%" approach is a practical tradeoff. Completely clearing the log risks losing recent, potentially unflushed events if the backend is temporarily unreachable. For the SyntaxError reset, a corrupted local log is unreadable anyway, so resetting is the only viable path forward to resume local caching.
**3. Draft fix:**
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

---

### Finding 6 — HIGH: `import traceback` inside except block in `verifier.py`

**1. Decision:** Approve fix
**2. Rationale:** Standard practice is to place imports at the top of the file. Moving it avoids potential issues in deeply restricted sandboxed environments where `import` could theoretically fail during an exception handler, and it improves code readability.
**3. Draft fix:** 
Move `import traceback` to the top of `packages/concept-aware/conceptgrade/verifier.py` alongside other standard library imports.

---

### Finding 7 — MEDIUM: `run_batch_eval_api.py` writes no partial-completion marker on quota exhaustion

**1. Decision:** Approve fix
**2. Rationale:** Writing a sentinel file is a robust way to signal incomplete runs. Downstream scripts like `score_ablation_v2.py` should ideally check for these sentinels and halt or warn the user, preventing silent partial results from polluting research tables.
**3. Draft fix:**
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

---

### Finding 8 — MEDIUM: `key_rotator.py` doesn't distinguish transient network errors from rate limits

**1. Decision:** Approve fix
**2. Rationale:** Rotating keys for transient network errors is inefficient and can prematurely exhaust keys. `ConnectionError` and `TimeoutError` do occur, especially in batch jobs running against remote APIs over several hours. Backing off on the same key is the correct strategy.
**3. Draft fix:**
```python
import socket
TRANSIENT_NETWORK_ERRORS = (
    ConnectionError,
    TimeoutError,
    socket.timeout,
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

---

### Finding 9 — LOW: `stability_analysis.py` `__main__` block has no file-not-found guard

**1. Decision:** Approve fix
**2. Rationale:** User-friendly error messages are crucial for a smooth research workflow. Adding basic validation for non-empty traces before computing correlations is a necessary step to prevent obscure math errors downstream.
**3. Draft fix:**
```python
if __name__ == '__main__':
    import sys, os
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
    
    if not flash_traces or not deepseek_traces:
        print(f"ERROR: Trace dictionaries are empty in {ablation_path}.")
        sys.exit(1)
        
    result = stability_analysis(flash_traces, deepseek_traces)
    print(json.dumps(result, indent=2))
    with open('data/stability_analysis_result.json', 'w') as f:
        json.dump(result, f, indent=2)
```

---

### Finding 10 — LOW: `readdirSync()` in `visualization.service.ts` is not guarded against post-startup permission errors

**1. Decision:** Approve fix
**2. Rationale:** Switching to async `readdir` prevents blocking the Node.js event loop and correctly handles post-startup permission issues. This is a best practice for I/O operations in high-throughput services.
**3. Draft fix:**
```typescript
import { readdir } from 'fs/promises';
import { InternalServerErrorException } from '@nestjs/common';

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
    throw new InternalServerErrorException(`Cannot read dataset directory '${DATA_DIR}': ${err.message}`);
  }
}
```