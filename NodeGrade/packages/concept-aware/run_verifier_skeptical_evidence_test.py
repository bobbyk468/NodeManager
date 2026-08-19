#!/usr/bin/env python3
"""
run_verifier_skeptical_evidence_test.py -- follow-up to
run_verifier_evidence_ablation.py's finding that giving DeepSeek's
verifier KG evidence makes it significantly WORSE (24.3% higher MAE,
p=0.0005) than the same prompt with no evidence at all -- consistent
with "false authority" (the model trusting fallible KG evidence over its
own reading of the student answer).

Tests one targeted fix: the EXACT SAME evidence content as the full
verifier (reconstructed via the real, unmodified
conceptgrade.verifier.LLMVerifier.build_user_prompt(), not
reimplemented), with one added instruction telling the verifier the
evidence is fallible and must be checked against the actual student
answer before being trusted. Nothing else changes -- same evidence
fields, same scoring guide, same JSON schema. If this closes the gap,
it's a prompt fix, not a mechanism fix -- worth knowing either way.

conceptgrade/verifier.py itself is NOT modified by this script -- this
is a standalone test of a prompt variant before deciding whether to
adopt it in production.

Run:
    python3 run_verifier_skeptical_evidence_test.py --model deepseek --n 150
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
WORKERS = 8
RPM_CAP = 20

MODELS = {
    "claude":   "anthropic/claude-sonnet-5",
    "gpt":      "openai/gpt-5.6-terra",
    "deepseek": "deepseek/deepseek-chat-v3.1",
}

BLOOMS_LABELS = {1: "Remember", 2: "Understand", 3: "Apply", 4: "Analyze", 5: "Evaluate", 6: "Create"}
SOLO_LABELS = {1: "Prestructural", 2: "Unistructural", 3: "Multistructural", 4: "Relational", 5: "Extended Abstract"}

SKEPTICISM_INSTRUCTION = (
    "\n\nIMPORTANT — the KNOWLEDGE GRAPH EVIDENCE below was extracted "
    "automatically by a separate, imperfect system. It can be incomplete, "
    "wrong, or misleading (e.g. a listed \"covered concept\" may not "
    "actually reflect correct understanding; a \"missing\" concept may "
    "have been expressed in different words the extractor missed; a "
    "flagged \"misconception\" may be a false positive). Treat it as a "
    "second opinion, not ground truth: independently read the STUDENT "
    "ANSWER yourself first, form your own judgment of what the student "
    "actually demonstrated, and only use the KG evidence to double-check "
    "or catch something you may have missed — never let it override your "
    "own direct reading of the student's actual words.\n"
)


def _chunks(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield i // size, rows[i:i + size]


class _RateLimiter:
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
            messages = [{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}]
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
            print(f"    [retry] {tag} attempt {attempt+1}/3 failed ({type(e).__name__}: {e}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"{tag}: failed after 3 retries") from last_exc


def _resolve_scores(scores: dict, expected_ids: list[str]) -> dict:
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
    used_keys, used_ids = set(), set()
    for ratio, sid, k in pairs:
        if sid in used_ids or k in used_keys:
            continue
        out[sid] = scores[k]
        used_keys.add(k); used_ids.add(sid)
    return out


def _skeptical_chunk(client, model: str, verifier, batch_dir: Path, chunk_i: int,
                      chunk: list[dict], limiter: _RateLimiter) -> tuple[int, dict]:
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
        # Inject the skepticism instruction right before the KG evidence block.
        kg_marker = "KNOWLEDGE GRAPH EVIDENCE:"
        kpos = evidence.find(kg_marker)
        if kpos != -1:
            evidence = evidence[:kpos] + SKEPTICISM_INSTRUCTION.strip() + "\n\n" + evidence[kpos:]
        blocks.append(f"=== SAMPLE ID: {r['sample_id']} ===\n{evidence}")

    footer = (
        "\n\nFor EACH sample above, independently apply the scoring guide. "
        "Return ONLY valid JSON:\n"
        "{\n  \"scores\": {\n    \"<SAMPLE ID>\": {\n"
        "      \"verified_score\": <float 0.0-5.0 in 0.25 increments>\n"
        "    }, ...\n  }\n}"
    )
    prompt = "\n\n".join(blocks) + footer
    tag = f"skeptical_c{chunk_i}"
    limiter.acquire()
    result = _call_batched(client, model, system_prompt, prompt, batch_dir, tag)
    scores_raw = result["parsed"].get("scores", result["parsed"])
    scores = _resolve_scores(scores_raw, [r["sample_id"] for r in chunk])
    out = {}
    for r in chunk:
        v = scores.get(r["sample_id"])
        if v is None:
            print(f"    [warn] no skeptical-verifier score for {r['sample_id']} (chunk {chunk_i})")
            continue
        raw = float(v["verified_score"]) if isinstance(v, dict) and "verified_score" in v else (
            float(next(iter(v.values()))) if isinstance(v, dict) and len(v) == 1 else float(v)
        )
        out[r["sample_id"]] = max(0.0, min(5.0, round(raw * 4) / 4))
    print(f"  Skeptical-evidence chunk {chunk_i}: {len(chunk)} samples done")
    return chunk_i, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, choices=sorted(MODELS.keys()))
    ap.add_argument("--n", type=int, default=150)
    args = ap.parse_args()
    tag = args.model
    model_id = MODELS[tag]

    phase_a = {r["sample_id"]: r for r in json.loads((DATA / f"{tag}_pipeline_phaseA_signals.json").read_text())}
    phase_b = json.loads((DATA / f"{tag}_pipeline_eval_results.json").read_text())

    rows = []
    for r in phase_b["results"][:args.n]:
        sid = r["id"]
        if sid not in phase_a:
            continue
        pa = phase_a[sid]
        rows.append({
            "sample_id": sid, "question": pa["question"], "student_answer": pa["student_answer"],
            "reference_answer": pa["reference_answer"], "comparison_result": pa["comparison_result"],
            "misconceptions": pa["misconceptions"],
            "_depth": {"blooms": {"level": r["blooms_level"], "label": BLOOMS_LABELS[r["blooms_level"]]},
                       "solo": {"level": r["solo_level"], "label": SOLO_LABELS[r["solo_level"]]}},
        })
    print(f"n={len(rows)}  model={model_id}")

    batch_dir = DATA / f"{tag}_verifier_skeptical_batches"
    from conceptgrade.llm_client import LLMClient, load_openrouter_key
    from conceptgrade.verifier import LLMVerifier
    key = load_openrouter_key()
    client = LLMClient(api_key=key)
    verifier = LLMVerifier(api_key=key, model=model_id, verifier_weight=1.0)

    limiter = _RateLimiter(RPM_CAP)
    out = {}
    chunks = list(_chunks(rows, CHUNK_SIZE))
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(_skeptical_chunk, client, model_id, verifier, batch_dir, ci, c, limiter) for ci, c in chunks]
        for future in as_completed(futures):
            _, chunk_result = future.result()
            out.update(chunk_result)

    out_path = DATA / f"{tag}_verifier_skeptical_evidence.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Done: {len(out)}/{len(rows)} complete. Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
