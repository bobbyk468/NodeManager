#!/usr/bin/env python3
"""
run_frontier_pipeline_phaseB_batched.py -- Phase B of the full-pipeline
frontier-model comparison (Option A). Directly adapted from
run_real_eval_phaseB_batched.py's run_depth_batch()/run_verifier_batch()
(same prompt-batching logic, same chunk size, same parsing/clamping),
just pointed at an OpenRouter model instead of Gemini and reading
Phase A input from run_frontier_pipeline_phaseA_batched.py's output
instead of mohler_real_phaseA_signals.json.

Requires: data/{tag}_pipeline_phaseA_signals.json (from
run_frontier_pipeline_phaseA_batched.py --model {tag}).

Output: data/{tag}_pipeline_eval_results.json, same shape as
mohler_real_eval_results.json (id, qid, human_score, c5_score, ...)
modulo the score field being named "{tag}_c5_score".

Run:
    python3 run_frontier_pipeline_phaseB_batched.py --model gpt
    python3 run_frontier_pipeline_phaseB_batched.py --model gpt --status
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"

CHUNK_SIZE = 25

# Depth and verifier chunks are independent of each other (different sample
# subsets within each stage); dispatched concurrently, same pattern and
# same conservative default as Phase A's extraction parallelization.
PHASE_B_WORKERS = 8
PHASE_B_RPM_CAP = 20

MODELS = {
    "claude":   "anthropic/claude-sonnet-5",
    "gpt":      "openai/gpt-5.6-terra",
    "deepseek": "deepseek/deepseek-chat-v3.1",
}


class _RateLimiter:
    """Thread-safe sliding-window rate limiter: blocks callers so that no
    more than `max_per_minute` acquire() calls succeed in any 60s window."""

    def __init__(self, max_per_minute: int):
        import threading
        from collections import deque
        self._max = max_per_minute
        self._lock = threading.Lock()
        self._timestamps = deque()

    def acquire(self):
        while True:
            with self._lock:
                now = time.time()
                while self._timestamps and now - self._timestamps[0] > 60:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._max:
                    self._timestamps.append(now)
                    return
            time.sleep(0.5)


def _call_batched(client, model: str, system_prompt: str, user_prompt: str,
                   batch_dir: Path, tag: str) -> dict:
    from conceptgrade.llm_client import parse_llm_json

    batch_dir.mkdir(parents=True, exist_ok=True)
    cache_path = batch_dir / f"{tag}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    last_exc = None
    for attempt in range(3):
        try:
            messages = [{"role": "user", "content": user_prompt}]
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            resp = client.chat.completions.create(
                model=model, messages=messages, temperature=0.0, max_tokens=8192,
            )
            raw_text = resp.choices[0].message.content
            parsed = parse_llm_json(raw_text)
            cache_path.write_text(json.dumps({"raw_text": raw_text, "parsed": parsed}, indent=2))
            return {"raw_text": raw_text, "parsed": parsed}
        except Exception as e:
            last_exc = e
            wait = 3 * (2 ** attempt)
            print(f"    [retry] {tag} attempt {attempt+1}/3 failed ({type(e).__name__}: {e}); "
                  f"retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"{tag}: failed after 3 retries") from last_exc


def _resolve_scores(scores: dict, expected_ids: list[str]) -> dict:
    """Maps each expected sample_id to its entry in `scores`, tolerating a
    corruption pattern observed with DeepSeek: a short run of characters in
    a JSON key (either the sample-ID key or, separately, the inner
    "verified_score" field name) gets collapsed into a single stray
    non-ASCII character, e.g. "E03.Q06.A08" -> "E03.Q06.A极" (2 chars ->
    1) or "E03.Q06.A11" -> "E极3.Q06.A11" (1 char -> 1, but elsewhere in
    the string). Lengths of the corrupted key can differ from the
    original, so a strict equal-length single-substitution check misses
    cases like the first example.

    Safety against false matches: exact matches are claimed FIRST, so a
    genuinely different, correctly-keyed sample (e.g. real "...A09" when
    resolving missing "...A08") is never a fuzzy-match candidate -- only
    keys left over after every exact match is removed can be fuzzy-matched,
    and only against sample_ids that are themselves still unresolved.
    Fuzzy candidates are ranked by difflib similarity, highest first, each
    key used at most once."""
    import difflib

    out = {sid: scores[sid] for sid in expected_ids if sid in scores}
    leftover_ids = [sid for sid in expected_ids if sid not in out]
    leftover_keys = [k for k in scores if k not in out]
    if not leftover_ids or not leftover_keys:
        return out

    pairs = []
    for sid in leftover_ids:
        for k in leftover_keys:
            ratio = difflib.SequenceMatcher(None, k, sid).ratio()
            if ratio >= 0.85:
                pairs.append((ratio, sid, k))
    pairs.sort(reverse=True)
    used_keys = set()
    used_ids = set()
    for ratio, sid, k in pairs:
        if sid in used_ids or k in used_keys:
            continue
        out[sid] = scores[k]
        used_keys.add(k)
        used_ids.add(sid)
    return out


def _chunks(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield i // size, rows[i:i + size]


def _depth_one_chunk(client, model: str, depth_classifier, batch_dir: Path,
                      chunk_i: int, chunk: list[dict], limiter: _RateLimiter) -> tuple[int, dict]:
    blocks = []
    system_prompt = None
    for r in chunk:
        sys_p, user_p, _ = depth_classifier.build_user_prompt(
            question=r["question"], student_answer=r["student_answer"],
            concept_graph=r["concept_graph"], comparison_result=r["comparison_result"],
        )
        system_prompt = sys_p
        marker = "\nReturn ONLY valid JSON"
        idx = user_p.find(marker)
        evidence = user_p[:idx] if idx != -1 else user_p
        blocks.append(f"=== SAMPLE ID: {r['sample_id']} ===\n{evidence}")

    footer = (
        "\n\nFor EACH sample above, independently classify Bloom's and SOLO levels. "
        "Return ONLY valid JSON:\n"
        "{\n  \"scores\": {\n    \"<SAMPLE ID>\": {\n"
        "      \"blooms_level\": <1-6>, \"blooms_label\": \"...\",\n"
        "      \"solo_level\": <1-5>, \"solo_label\": \"...\"\n"
        "    }, ...\n  }\n}"
    )
    prompt = "\n\n".join(blocks) + footer
    tag = f"depth_c{chunk_i}"
    limiter.acquire()
    result = _call_batched(client, model, system_prompt, prompt, batch_dir, tag)
    scores_raw = result["parsed"].get("scores", result["parsed"])
    scores = _resolve_scores(scores_raw, [r["sample_id"] for r in chunk])
    out = {}
    for r in chunk:
        v = scores.get(r["sample_id"])
        if v is None:
            print(f"    [warn] no depth result for {r['sample_id']} (chunk {chunk_i})")
            continue
        b_level = max(1, min(6, int(v.get("blooms_level", 1))))
        s_level = max(1, min(5, int(v.get("solo_level", 1))))
        out[r["sample_id"]] = {
            "blooms": {"level": b_level, "label": v.get("blooms_label", "Remember")},
            "solo": {"level": s_level, "label": v.get("solo_label", "Prestructural")},
        }
    print(f"  Depth chunk {chunk_i}: {len(chunk)} samples done")
    return chunk_i, out


def run_depth_batch(rows: list[dict], client, model: str, depth_classifier, batch_dir: Path) -> dict:
    """Returns {sample_id: {"blooms": {...}, "solo": {...}}}. Chunks dispatched
    concurrently (independent of each other), same pattern as Phase A's
    extraction parallelization."""
    out = {}
    limiter = _RateLimiter(PHASE_B_RPM_CAP)
    chunks = list(_chunks(rows, CHUNK_SIZE))
    with ThreadPoolExecutor(max_workers=PHASE_B_WORKERS) as pool:
        futures = [pool.submit(_depth_one_chunk, client, model, depth_classifier, batch_dir, chunk_i, chunk, limiter)
                   for chunk_i, chunk in chunks]
        for future in as_completed(futures):
            _, chunk_result = future.result()
            out.update(chunk_result)
    return out


def _verifier_one_chunk(client, model: str, verifier, batch_dir: Path,
                         chunk_i: int, chunk: list[dict], limiter: _RateLimiter) -> tuple[int, dict]:
    blocks = []
    system_prompt = None
    for r in chunk:
        depth = r["_depth"]
        sys_p, user_p, _ = verifier.build_user_prompt(
            question=r["question"], student_answer=r["student_answer"],
            comparison_result=r["comparison_result"],
            blooms=depth["blooms"], solo=depth["solo"],
            misconceptions=r["misconceptions"],
            reference_answer=r["reference_answer"], mode="sag",
        )
        system_prompt = sys_p
        marker = "\nReturn ONLY valid JSON:"
        idx = user_p.rfind(marker)
        evidence = user_p[:idx] if idx != -1 else user_p
        blocks.append(f"=== SAMPLE ID: {r['sample_id']} ===\n{evidence}")

    footer = (
        "\n\nFor EACH sample above, independently apply the scoring guide. "
        "Return ONLY valid JSON:\n"
        "{\n  \"scores\": {\n    \"<SAMPLE ID>\": {\n"
        "      \"verified_score\": <float 0.0-5.0 in 0.25 increments>\n"
        "    }, ...\n  }\n}"
    )
    prompt = "\n\n".join(blocks) + footer
    tag = f"verifier_c{chunk_i}"
    limiter.acquire()
    result = _call_batched(client, model, system_prompt, prompt, batch_dir, tag)
    scores_raw = result["parsed"].get("scores", result["parsed"])
    scores = _resolve_scores(scores_raw, [r["sample_id"] for r in chunk])
    out = {}
    for r in chunk:
        v = scores.get(r["sample_id"])
        if v is None:
            print(f"    [warn] no verifier score for {r['sample_id']} (chunk {chunk_i})")
            continue
        if isinstance(v, dict):
            if "verified_score" in v:
                raw = float(v["verified_score"])
            else:
                # Some models (observed with DeepSeek) occasionally inject a
                # stray character into the key name (e.g. "verified极_score"
                # or "极verified_score") -- the value itself is still a
                # clean float. Recover it: single-key dict -> that value;
                # multi-key -> the one key containing "score"; else give up.
                score_keys = [k for k in v if "score" in k]
                if len(v) == 1:
                    raw = float(next(iter(v.values())))
                elif len(score_keys) == 1:
                    raw = float(v[score_keys[0]])
                else:
                    print(f"    [warn] malformed verifier entry for {r['sample_id']} "
                          f"(chunk {chunk_i}): {v!r} -- skipping")
                    continue
                print(f"    [recovered] {r['sample_id']} (chunk {chunk_i}): "
                      f"corrupted key {list(v.keys())!r} -> {raw}")
        else:
            raw = float(v)
        out[r["sample_id"]] = max(0.0, min(5.0, round(raw * 4) / 4))
    print(f"  Verifier chunk {chunk_i}: {len(chunk)} samples done")
    return chunk_i, out


def run_verifier_batch(rows: list[dict], client, model: str, verifier, batch_dir: Path) -> dict:
    """Returns {sample_id: verified_score}. Chunks dispatched concurrently."""
    out = {}
    limiter = _RateLimiter(PHASE_B_RPM_CAP)
    chunks = list(_chunks(rows, CHUNK_SIZE))
    with ThreadPoolExecutor(max_workers=PHASE_B_WORKERS) as pool:
        futures = [pool.submit(_verifier_one_chunk, client, model, verifier, batch_dir, chunk_i, chunk, limiter)
                   for chunk_i, chunk in chunks]
        for future in as_completed(futures):
            _, chunk_result = future.result()
            out.update(chunk_result)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, choices=sorted(MODELS.keys()))
    ap.add_argument("--pilot", type=int, default=0, help="limit to first N rows (0 = all)")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    tag = args.model
    model_id = MODELS[tag]
    phase_a_path = DATA / f"{tag}_pipeline_phaseA_signals.json"
    # Pilot runs get a separate batch cache dir: chunk boundaries shift with
    # row count, and unlike Phase A this script has no cache-mismatch check,
    # so a pilot's partial chunk_0 would silently poison the full run's cache.
    suffix = f"_pilot{args.pilot}" if args.pilot else ""
    batch_dir = DATA / f"{tag}_pipeline_phaseB_batches{suffix}"
    out_path = DATA / f"{tag}_pipeline_eval_results{suffix}.json"

    if not phase_a_path.exists():
        print(f"Missing {phase_a_path} -- run run_frontier_pipeline_phaseA_batched.py --model {tag} first.")
        return 1
    rows = json.loads(phase_a_path.read_text())
    if args.pilot:
        rows = rows[:args.pilot]
    print(f"Phase A rows available: {len(rows)}")
    print(f"Model: {model_id} (tag={tag})")

    if args.status:
        n_depth = len(list(batch_dir.glob("depth_c*.json"))) if batch_dir.exists() else 0
        n_verifier = len(list(batch_dir.glob("verifier_c*.json"))) if batch_dir.exists() else 0
        n_expected = (len(rows) + CHUNK_SIZE - 1) // CHUNK_SIZE
        print(f"Depth chunks: {n_depth}/{n_expected}  Verifier chunks: {n_verifier}/{n_expected}")
        if out_path.exists():
            done = json.loads(out_path.read_text())
            print(f"Output written: {done['n_complete']}/{done['n']} complete")
        return 0

    from conceptgrade.llm_client import LLMClient, load_openrouter_key
    from conceptgrade.verifier import LLMVerifier
    from cognitive_depth.cognitive_depth_classifier import CognitiveDepthClassifier

    key = load_openrouter_key()
    client = LLMClient(api_key=key)
    verifier = LLMVerifier(api_key=key, model=model_id, verifier_weight=1.0)
    depth_classifier = CognitiveDepthClassifier(api_key=key, model=model_id)

    print("\n[1/2] Cognitive depth (batched)...")
    depth_results = run_depth_batch(rows, client, model_id, depth_classifier, batch_dir)
    for r in rows:
        r["_depth"] = depth_results.get(r["sample_id"], {"blooms": {"level": 1, "label": "Remember"},
                                                            "solo": {"level": 1, "label": "Prestructural"}})

    print("\n[2/2] Verifier / final score (batched)...")
    verified_scores = run_verifier_batch(rows, client, model_id, verifier, batch_dir)

    results = []
    for r in rows:
        results.append({
            "id": r["sample_id"], "qid": r["question_id"],
            "human_score": r["human_score"],
            f"{tag}_c5_score": verified_scores.get(r["sample_id"]),
            "blooms_level": r["_depth"]["blooms"]["level"],
            "solo_level": r["_depth"]["solo"]["level"],
            "total_misconceptions": r["misconceptions"]["total_misconceptions"],
            "concept_coverage": r["comparison_result"].get("scores", {}).get("concept_coverage"),
        })

    n_complete = sum(1 for r in results if r[f"{tag}_c5_score"] is not None)
    out_path.write_text(json.dumps({
        "dataset": "mohler_real_kg_aligned", "model": model_id,
        "n": len(results), "n_complete": n_complete, "results": results,
    }, indent=2))
    print(f"\nDone: {n_complete}/{len(results)} complete. Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
