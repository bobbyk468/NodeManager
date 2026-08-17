#!/usr/bin/env python3
"""
validate_c5fix_prompt_fix.py — validate Framework Fix #1.

Generates the patched C5_fix prompt for a small Mohler sample, sends it
to gemini-2.5-flash, and prints the raw responses next to the cached
old-prompt C5_fix scores and the human ground truth. Lets you eyeball
whether the new prompt produces sensible, more answer-grounded grades
before committing to a full n=120 re-run.

Hard budget cap: $1. Default --n=10 samples. --dry-run prints prompt
only without API call.

Run:
    python validate_c5fix_prompt_fix.py                  # dry-run, 10 samples
    python validate_c5fix_prompt_fix.py --execute        # actually call
    python validate_c5fix_prompt_fix.py --execute --n 30 # 30 samples (~$0.10)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

ENV_PATH = BASE.parent / "backend" / ".env"
MAX_BUDGET_USD = 1.00
PRICE_IN_PER_1M = 0.30
PRICE_OUT_PER_1M = 2.50

# Realistic token estimate per sample for batch scoring
EST_IN_PER_SAMPLE = 350    # question + reference + student + KG block
EST_OUT_PER_SAMPLE = 12    # JSON {"id": X.X}


def load_gemini_key():
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            v = line.split("=", 1)[1].strip()
            if (v.startswith('"') and v.endswith('"')) or \
               (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            return v
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=10,
                        help="Number of Mohler samples to send (default 10)")
    parser.add_argument("--execute", action="store_true",
                        help="Actually call Gemini (default: dry-run prompt only)")
    parser.add_argument("--seed", type=int, default=20260601,
                        help="Random seed for sample selection")
    parser.add_argument("--show-prompt", action="store_true",
                        help="Print the full generated prompt to stdout")
    args = parser.parse_args()
    args.dry_run = not args.execute

    import random
    rng = random.Random(args.seed)

    # Load Mohler dataset + cached eval to grab features + cached C5_fix scores
    from datasets.mohler_loader import load_mohler_sample
    from concept_matching import should_use_kg_evidence

    dataset = load_mohler_sample()
    with (BASE / "archive" / "fabricated_fixtures" / "mohler_eval_results.json").open() as f:
        cached_eval = json.load(f)["results"]

    # Deterministically pick n samples spanning all 10 questions
    samples_by_q: dict[str, list] = {}
    for i, s in enumerate(dataset.samples):
        samples_by_q.setdefault(s.question_id, []).append((i, s))

    chosen: list[tuple[int, object]] = []
    per_q = max(1, args.n // len(samples_by_q))
    for qid, items in samples_by_q.items():
        rng.shuffle(items)
        chosen.extend(items[:per_q])
    chosen = chosen[: args.n]

    # Build the batch in the format generate_batch_scoring_prompts.py expects
    batch = []
    features = {}
    for i, s in chosen:
        sid = str(i)
        batch.append({
            "id": sid, "question": s.question,
            "reference_answer": s.reference_answer,
            "student_answer": s.student_answer,
        })
        r = cached_eval[i]
        matched = r.get("matched_concepts", [])
        chain_pct = r.get("chain_pct", "0%")
        # use_kg threshold check
        try:
            cov = float(str(chain_pct).rstrip("%")) / 100.0
        except Exception:
            cov = 0.0
        features[sid] = {
            "matched_concepts": matched,
            "chain_pct": chain_pct,
            "use_kg": should_use_kg_evidence(cov),
        }

    # Generate the PATCHED prompt
    from generate_batch_scoring_prompts import build_c5fix_prompt
    prompt = build_c5fix_prompt(batch, features)

    print("=" * 72)
    print(f"VALIDATION: Framework Fix #1 on {len(batch)} Mohler samples")
    print(f"           {'DRY RUN' if args.dry_run else 'EXECUTE'},  "
          f"budget cap ${MAX_BUDGET_USD}")
    print("=" * 72)

    if args.show_prompt or args.dry_run:
        print("\n--- PATCHED C5_FIX PROMPT ---")
        print(prompt)
        print("--- END PROMPT ---\n")

    est_in = EST_IN_PER_SAMPLE * len(batch)
    est_out = EST_OUT_PER_SAMPLE * len(batch)
    est_cost = (est_in / 1e6) * PRICE_IN_PER_1M + (est_out / 1e6) * PRICE_OUT_PER_1M
    print(f"Estimated tokens: {est_in + est_out:,}  Estimated cost: ${est_cost:.4f}")

    if args.dry_run:
        print("\nDry-run only. Re-run with --execute to send to Gemini.")
        return 0

    if est_cost > MAX_BUDGET_USD:
        print(f"ABORT: estimated cost ${est_cost:.4f} > cap ${MAX_BUDGET_USD}",
              file=sys.stderr)
        return 2

    key = load_gemini_key()
    if not key:
        print("ABORT: GEMINI_API_KEY not set", file=sys.stderr)
        return 2

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        os.system(f"{sys.executable} -m pip install google-genai")
        from google import genai
        from google.genai import types

    print(f"\n[gemini] sending {len(batch)}-sample batch to gemini-2.5-flash …",
          flush=True)
    client = genai.Client(api_key=key)
    t0 = time.time()
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=2000,
            response_mime_type="application/json",
        ),
    )
    latency_ms = round((time.time() - t0) * 1000, 1)
    raw_text = resp.text
    usage = resp.usage_metadata
    actual_in = getattr(usage, "prompt_token_count", 0)
    actual_out = getattr(usage, "candidates_token_count", 0)
    actual_cost = (actual_in / 1e6) * PRICE_IN_PER_1M + (actual_out / 1e6) * PRICE_OUT_PER_1M

    print(f"[gemini] response in {latency_ms}ms,  "
          f"in={actual_in} tok, out={actual_out} tok,  cost ${actual_cost:.4f}")

    if actual_cost > MAX_BUDGET_USD:
        print(f"\nWARNING: actual cost ${actual_cost:.4f} exceeded ${MAX_BUDGET_USD} cap"
              " (request already completed)", file=sys.stderr)

    # Parse the response
    try:
        parsed = json.loads(raw_text)
        scores_obj = parsed.get("scores", parsed)
    except Exception as e:
        print(f"\nWARNING: failed to parse Gemini JSON: {e}", file=sys.stderr)
        print(f"Raw response (first 500 chars):\n{raw_text[:500]}")
        return 1

    print("\n" + "=" * 72)
    print("PER-SAMPLE COMPARISON (cached old prompt vs new prompt)")
    print("=" * 72)
    print(f"{'idx':>4} {'qid':>4} {'human':>7} {'old_C5':>8} {'new_C5':>8} "
          f"{'|new-h|':>8} {'|old-h|':>8} {'verdict':>14}")
    print("-" * 72)

    new_errs = []
    old_errs = []
    for i, s in chosen:
        sid = str(i)
        human = s.score_avg
        old_score = cached_eval[i]["c5_score"]
        new_score = scores_obj.get(sid)
        if new_score is None:
            new_score_disp = "  --  "
            verdict = "no response"
        else:
            try:
                new_score_f = float(new_score)
            except Exception:
                new_score_f = float("nan")
                verdict = "parse err"
                new_score_disp = f"{new_score!r}"
            else:
                new_score_disp = f"{new_score_f:.2f}"
                old_err = abs(human - old_score)
                new_err = abs(human - new_score_f)
                if new_err < old_err - 0.05:
                    verdict = "new BETTER"
                elif new_err > old_err + 0.05:
                    verdict = "new worse"
                else:
                    verdict = "same"
                new_errs.append(new_err)
                old_errs.append(old_err)

        old_err_disp = f"{abs(human - old_score):.2f}"
        if isinstance(new_score, (int, float)):
            new_err_disp = f"{abs(human - new_score):.2f}"
        else:
            new_err_disp = "  --"
        print(f"{i:>4} {s.question_id:>4} {human:>7.2f} {old_score:>8.2f} "
              f"{new_score_disp:>8} {new_err_disp:>8} {old_err_disp:>8} "
              f"{verdict:>14}")

    if new_errs and old_errs:
        import statistics
        print("-" * 72)
        print(f"Aggregate over {len(new_errs)} samples that returned scores:")
        print(f"  Old prompt mean |error|: {statistics.mean(old_errs):.4f}")
        print(f"  New prompt mean |error|: {statistics.mean(new_errs):.4f}")
        delta = statistics.mean(new_errs) - statistics.mean(old_errs)
        print(f"  Delta MAE              : {delta:+.4f}  "
              f"({'improvement' if delta < 0 else 'regression' if delta > 0 else 'tied'})")

    # Save the full response + cost log
    out = {
        "fix_version": "framework_fix_1_c5fix_prompt",
        "n_samples": len(batch),
        "model": "gemini-2.5-flash",
        "latency_ms": latency_ms,
        "input_tokens": actual_in,
        "output_tokens": actual_out,
        "actual_cost_usd": round(actual_cost, 6),
        "raw_response": raw_text,
        "parsed_scores": scores_obj,
        "per_sample": [
            {
                "idx": i, "qid": s.question_id,
                "human": s.score_avg,
                "old_c5_score": cached_eval[i]["c5_score"],
                "new_c5_score": scores_obj.get(str(i)),
                "question": s.question[:120],
                "student_answer_preview": s.student_answer[:140],
            }
            for i, s in chosen
        ],
    }
    out_path = BASE / "data" / "framework_fix_1_validation.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    print("\nRaw response printed above so you can validate Gemini's scoring "
          "against your eye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
