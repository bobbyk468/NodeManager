#!/usr/bin/env python3
"""
run_verifier_evidence_ablation.py -- the causal ablation deliberately
deferred earlier this session: does KG-derived evidence-in-context
specifically (not just a longer/more-structured verifier prompt) cause
the verifier's edge over zero-shot? Isolates this by using the EXACT
SAME verifier system prompt and scoring instructions as the full
pipeline, with the "KNOWLEDGE GRAPH EVIDENCE:" block removed from the
user prompt -- everything else (question, reference answer, student
answer, scoring guide, JSON schema) held identical. This is different
from zero-shot (which uses a completely separate C_LLM prompt template)
and different from the full verifier (which includes the evidence
block) -- it's the missing middle condition needed to separate "evidence
content" from "prompt template" as the cause of any score difference.

Batched (chunk size 25), same pattern as run_frontier_pipeline_phaseB_batched.py.
Runs on the first N samples of each backbone's existing 300/298-sample
Phase A/B output, so the "full verifier" condition can be reused from
cache (zero extra cost) and compared directly against this script's new
"bare verifier" condition on the exact same samples.

Run:
    python3 run_verifier_evidence_ablation.py --model gpt --n 150
    python3 run_verifier_evidence_ablation.py --model deepseek --n 150
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

# Copied verbatim from conceptgrade/verifier.py's VERIFIER_SYSTEM -- must
# stay byte-identical to the full-verifier condition for this to be a
# valid ablation (only the evidence block in the user prompt differs).
VERIFIER_SYSTEM = """You are an expert Computer Science educator grading a student's short answer.

Your task: Compare the student answer to the reference answer and assign a score from 0.0 to 5.0.

SCORING GUIDE — based on proportion of reference answer content correctly demonstrated:
- 5.0: Student correctly explains virtually all key ideas (≥90% of reference content)
- 4.5: Student correctly explains the great majority (≥80%); only very minor omissions
- 4.0: Student correctly explains most key ideas (≥70%); one clear gap
- 3.5: Student correctly explains a solid majority (≥60%) with reasonable depth
- 3.0: Student correctly explains about half the reference content (~50%)
- 2.5: Student correctly explains several key ideas (30–50%); substantial content still missing
- 2.0: Student correctly explains 1–2 key ideas accurately; most reference content missing
- 1.5: Student shows partial understanding of 1 concept but cannot explain mechanisms
- 1.0: Student shows awareness of the topic but no accurate explanations of mechanisms
- 0.5: Single marginally relevant statement; no explanation
- 0.0: No relevant content

IMPORTANT:
- "Some correct content with major gaps" = 2.0–2.5 range, NOT 1.0.
- Score what the student got RIGHT; what is MISSING prevents reaching a higher band.
- Misconceptions about core mechanisms lower the score; missing vocabulary alone does not.
- Students often express correct understanding in different words — credit the understanding.
- Use 0.25 increments.

Return ONLY valid JSON."""

BARE_INSTRUCTION = (
    "First identify what the student correctly explained (this sets the base score). "
    "Then note what is missing (this caps the maximum score). A student who correctly "
    "explains 1–2 key concepts earns 2.0–2.5 even if many other concepts are absent. "
    "Score based on the proportion of reference content correctly demonstrated, not on "
    "the count of missing items."
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
    """Same fuzzy-match safety net as run_frontier_pipeline_phaseB_batched.py --
    tolerates the single-stray-character key corruption observed with some
    models, without ever fuzzy-matching against a key that's already an
    exact match for a DIFFERENT sample."""
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


def _bare_chunk(client, model: str, batch_dir: Path, chunk_i: int, chunk: list[dict],
                 limiter: _RateLimiter) -> tuple[int, dict]:
    blocks = []
    for r in chunk:
        block = (
            f"=== SAMPLE ID: {r['sample_id']} ===\n"
            f"QUESTION: {r['question']}\n\n"
            f"REFERENCE ANSWER (expert answer — defines 5.0):\n{r['reference_answer']}\n\n"
            f"STUDENT ANSWER:\n{r['student_answer']}\n\n"
            f"{BARE_INSTRUCTION}"
        )
        blocks.append(block)
    footer = (
        "\n\nFor EACH sample above, independently apply the scoring guide. "
        "Return ONLY valid JSON:\n"
        "{\n  \"scores\": {\n    \"<SAMPLE ID>\": {\n"
        "      \"verified_score\": <float 0.0-5.0 in 0.25 increments>\n"
        "    }, ...\n  }\n}"
    )
    prompt = "\n\n".join(blocks) + footer
    tag = f"bare_c{chunk_i}"
    limiter.acquire()
    result = _call_batched(client, model, VERIFIER_SYSTEM, prompt, batch_dir, tag)
    scores_raw = result["parsed"].get("scores", result["parsed"])
    scores = _resolve_scores(scores_raw, [r["sample_id"] for r in chunk])
    out = {}
    for r in chunk:
        v = scores.get(r["sample_id"])
        if v is None:
            print(f"    [warn] no bare-verifier score for {r['sample_id']} (chunk {chunk_i})")
            continue
        raw = float(v["verified_score"]) if isinstance(v, dict) and "verified_score" in v else (
            float(next(iter(v.values()))) if isinstance(v, dict) and len(v) == 1 else float(v)
        )
        out[r["sample_id"]] = max(0.0, min(5.0, round(raw * 4) / 4))
    print(f"  Bare-verifier chunk {chunk_i}: {len(chunk)} samples done")
    return chunk_i, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, choices=sorted(MODELS.keys()))
    ap.add_argument("--n", type=int, default=150)
    args = ap.parse_args()
    tag = args.model
    model_id = MODELS[tag]

    phase_a_path = DATA / f"{tag}_pipeline_phaseA_signals.json"
    if not phase_a_path.exists():
        print(f"Missing {phase_a_path}")
        return 1
    rows = json.loads(phase_a_path.read_text())[:args.n]
    print(f"n={len(rows)}  model={model_id}")

    batch_dir = DATA / f"{tag}_verifier_ablation_batches"
    from conceptgrade.llm_client import LLMClient, load_openrouter_key
    client = LLMClient(api_key=load_openrouter_key())

    limiter = _RateLimiter(RPM_CAP)
    out = {}
    chunks = list(_chunks(rows, CHUNK_SIZE))
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(_bare_chunk, client, model_id, batch_dir, ci, c, limiter) for ci, c in chunks]
        for future in as_completed(futures):
            _, chunk_result = future.result()
            out.update(chunk_result)

    out_path = DATA / f"{tag}_verifier_ablation_bare.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Done: {len(out)}/{len(rows)} complete. Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
