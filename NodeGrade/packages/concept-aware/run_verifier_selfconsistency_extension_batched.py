#!/usr/bin/env python3
"""
run_verifier_selfconsistency_extension_batched.py — extends the verifier
self-consistency (K=7, temperature=0.7, median-aggregated) experiment to
the 4-question/109-response extension set, so the combined 50-question
result can be evaluated.

Mirrors run_verifier_selfconsistency_real_batched.py exactly, but reads
the extension's Phase A signals + eval results and writes to a separate
output file.

Run:
    python3 run_verifier_selfconsistency_extension_batched.py
    python3 run_verifier_selfconsistency_extension_batched.py --status
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"
BATCH_DIR = DATA / "verifier_selfconsistency_extension_batches"
OUT_PATH = DATA / "verifier_selfconsistency_extension_results.json"
CHUNK_SIZE = 25
N_ROUNDS = 7
LIVE_MODEL = "gemini-2.5-flash"

BLOOMS_LABELS = {1: "Remember", 2: "Understand", 3: "Apply", 4: "Analyze", 5: "Evaluate", 6: "Create"}
SOLO_LABELS = {1: "Prestructural", 2: "Unistructural", 3: "Multistructural", 4: "Relational", 5: "Extended Abstract"}


def _load_gemini_key() -> str:
    env_path = BASE.parent / "backend" / ".env"
    with env_path.open() as f:
        for line in f:
            m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
            if m:
                return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def _call_batched(client, system_prompt: str, user_prompt: str, tag: str, temperature: float) -> dict:
    from conceptgrade.llm_client import parse_llm_json

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = BATCH_DIR / f"{tag}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    last_exc = None
    for attempt in range(3):
        try:
            messages = [{"role": "user", "content": user_prompt}]
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            resp = client.chat.completions.create(
                model=LIVE_MODEL, messages=messages, temperature=temperature, max_tokens=8192,
            )
            raw_text = resp.choices[0].message.content
            parsed = parse_llm_json(raw_text)
            cache_path.write_text(json.dumps({"raw_text": raw_text, "parsed": parsed}, indent=2))
            return {"raw_text": raw_text, "parsed": parsed}
        except Exception as e:
            last_exc = e
            wait = 3 * (2 ** attempt)
            print(f"    [retry] {tag} attempt {attempt+1}/3 failed ({type(e).__name__}: {e}); "
                  f"retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"{tag}: failed after 3 retries") from last_exc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    with (DATA / "mohler_real_extension_phaseA_signals.json").open() as f:
        phase_a = {r["sample_id"]: r for r in json.load(f)}
    with (DATA / "mohler_real_extension_eval_results.json").open() as f:
        cached = {r["id"]: r for r in json.load(f)["results"]}

    sample_ids = list(cached.keys())
    n_chunks = (len(sample_ids) + CHUNK_SIZE - 1) // CHUNK_SIZE
    total_batches = N_ROUNDS * n_chunks

    if args.status:
        done = len(list(BATCH_DIR.glob("verifsc_ext_r*_c*.json"))) if BATCH_DIR.exists() else 0
        print(f"Verifier self-consistency (extension) batches: {done}/{total_batches}")
        return 0

    from conceptgrade.llm_client import LLMClient
    from conceptgrade.verifier import LLMVerifier

    key = _load_gemini_key()
    client = LLMClient(api_key=key)
    verifier = LLMVerifier(api_key=key, model=LIVE_MODEL, verifier_weight=1.0)

    def build_batch_prompt(chunk_ids: list[str]) -> tuple[str, str]:
        blocks = []
        system_prompt = None
        for sid in chunk_ids:
            a = phase_a[sid]
            c = cached[sid]
            blooms = {"level": c["blooms_level"], "label": BLOOMS_LABELS[c["blooms_level"]]}
            solo = {"level": c["solo_level"], "label": SOLO_LABELS[c["solo_level"]]}
            sys_p, user_p, _ = verifier.build_user_prompt(
                question=a["question"], student_answer=a["student_answer"],
                comparison_result=a["comparison_result"],
                blooms=blooms, solo=solo, misconceptions=a["misconceptions"],
                reference_answer=a["reference_answer"], mode="sag",
            )
            system_prompt = sys_p
            marker = "\nReturn ONLY valid JSON:"
            idx = user_p.rfind(marker)
            evidence = user_p[:idx] if idx != -1 else user_p
            blocks.append(f"=== SAMPLE ID: {sid} ===\n{evidence}")

        footer = (
            "\n\nFor EACH sample above, independently apply the scoring guide as if you "
            "were one of several graders reaching your own holistic judgment without "
            "seeing the others'. Return ONLY valid JSON:\n"
            "{\n  \"scores\": {\n    \"<SAMPLE ID>\": {\n"
            "      \"verified_score\": <float 0.0-5.0 in 0.25 increments>\n"
            "    }, ...\n  }\n}"
        )
        return system_prompt, "\n\n".join(blocks) + footer

    attempts: dict[str, list[float]] = {sid: [] for sid in sample_ids}
    t_start = time.time()
    batch_num = 0
    for round_i in range(N_ROUNDS):
        for chunk_i in range(n_chunks):
            batch_num += 1
            chunk_ids = sample_ids[chunk_i * CHUNK_SIZE: (chunk_i + 1) * CHUNK_SIZE]
            tag = f"verifsc_ext_r{round_i}_c{chunk_i}"
            cache_path = BATCH_DIR / f"{tag}.json"
            if not cache_path.exists():
                system_prompt, prompt = build_batch_prompt(chunk_ids)
                _call_batched(client, system_prompt, prompt, tag, temperature=0.7)

            result = json.loads(cache_path.read_text())
            scores = result["parsed"].get("scores", result["parsed"])
            for sid in chunk_ids:
                v = scores.get(sid)
                if v is None:
                    print(f"    [warn] no score for {sid} in {tag}", flush=True)
                    continue
                raw = float(v["verified_score"]) if isinstance(v, dict) else float(v)
                attempts[sid].append(max(0.0, min(5.0, raw)))

            elapsed = time.time() - t_start
            print(f"[{batch_num}/{total_batches}] round {round_i+1}/{N_ROUNDS} "
                  f"batch {chunk_i+1}/{n_chunks} done -- elapsed {elapsed:.0f}s", flush=True)

    import statistics

    results = []
    for sid in sample_ids:
        atts = attempts[sid]
        median_score = round(statistics.median(atts) * 4) / 4 if atts else None
        c = cached[sid]
        results.append({
            "id": sid, "qid": c["qid"], "human_score": c["human_score"],
            "cllm_score": c["cllm_score"], "c5_fix_single": c["c5_score"],
            "verifier_x7_attempts": atts, "verifier_x7_median": median_score,
            "out_of_kg_domain": c.get("out_of_kg_domain", False),
        })

    n_complete = sum(1 for r in results if r["verifier_x7_median"] is not None)
    OUT_PATH.write_text(json.dumps({
        "dataset": "mohler_real_kg_extension", "n": len(results),
        "n_complete": n_complete, "results": results,
    }, indent=2))
    print(f"\nDone: {n_complete}/{len(results)} complete. Wrote {OUT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
