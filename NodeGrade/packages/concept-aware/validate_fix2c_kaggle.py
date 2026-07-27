#!/usr/bin/env python3
"""
validate_fix2c_kaggle.py — empirical validation of Framework Fix #2c.

Fix #2c added an explicit [OUT_OF_KG_DOMAIN] marker to the C5_fix prompt
when the question is outside the CS-DS KG's coverage (Kaggle ASAG samples
about elementary science / biology). Before #2c the prompt silently emitted
empty KG evidence; the LLM had to infer from the absence of a KG block
whether the KG was inapplicable or the student just hadn't covered
concepts. The marker now tells the LLM explicitly.

This script generates a paste-to-Gemini prompt for n Kaggle samples using
the patched C5_fix prompt builder, then (after manual paste-back) compares
new vs cached old scores to test whether the marker measurably changes
Gemini's behaviour.

Usage:
    python3 validate_fix2c_kaggle.py                 # dry-run, n=10 → /tmp prompt
    python3 validate_fix2c_kaggle.py --n 20          # larger batch
    python3 validate_fix2c_kaggle.py --paste RESPONSE.json   # post-paste analysis
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

DATA = BASE / "data"
OUT = BASE / "FRAMEWORK_FIX2C_PROMPT_FOR_GEMINI.txt"


def load_kaggle():
    with (DATA / "kaggle_asag_dataset.json").open() as f:
        records = json.load(f)
    with (DATA / "kaggle_asag_eval_results.json").open() as f:
        ev = json.load(f).get("results", [])
    # Index eval by sample id for safe lookup
    ev_by_id = {r.get("id"): r for r in ev}
    return records, ev_by_id


def select_samples(records, n, seed):
    """Deterministically pick n samples. Skip whitespace-only student
    answers (they always score 0 and don't exercise the marker)."""
    rng = random.Random(seed)
    candidates = [r for r in records if str(r.get("student_answer", "")).strip()]
    rng.shuffle(candidates)
    return candidates[:n]


def build_prompt(samples):
    """Build the patched C5_fix prompt for the chosen Kaggle samples."""
    from generate_batch_scoring_prompts import (
        build_c5fix_prompt, SCORING_GUIDE_STRICT,
    )
    # Translate Kaggle records into the prompt-builder format
    batch = []
    features = {}
    for r in samples:
        sid = str(r["id"])
        batch.append({
            "id": sid,
            "question": r["question"],
            "reference_answer": r["reference_answer"],
            "student_answer": r["student_answer"],
        })
        # Kaggle questions are all OUT_OF_KG (CS-DS KG doesn't cover plant
        # respiration, magnetism, etc.) — domain_match_score is 0.0 for all.
        # Fix #2c reads this via precompute_features but we set it directly
        # here since we want to validate the marker behaviour explicitly.
        features[sid] = {
            "matched_concepts": [],
            "chain_pct": "0%",
            "use_kg": False,
            "domain_match_score": 0.0,
            "out_of_kg_domain": True,
        }
    return build_c5fix_prompt(batch, features, scoring_guide=SCORING_GUIDE_STRICT)


def write_paste_prompt(samples, prompt):
    """Write the prompt + a separator block listing the sample IDs the user
    will paste responses back for."""
    header = (
        "# Fix #2c validation — Kaggle ASAG with [OUT_OF_KG_DOMAIN] marker\n"
        "# ============================================================\n"
        "# 1. Open https://aistudio.google.com/\n"
        "# 2. Paste the entire block below (after the dashes) into the prompt input.\n"
        "# 3. Select model: gemini-2.5-flash. Temperature 0.0. Response: JSON.\n"
        "# 4. Send. Save the full response JSON.\n"
        "# 5. Re-run: python3 validate_fix2c_kaggle.py --paste <response.json>\n"
        "# ------------------------------------------------------------\n\n"
    )
    OUT.write_text(header + prompt + "\n")
    # Also dump expected ID list + human/cached scores for post-paste compare
    sidecar = OUT.with_suffix(".samples.json")
    rows = []
    for r in samples:
        rows.append({
            "id": r["id"],
            "human_score": r.get("human_score"),
            "question": r["question"][:100],
            "student_answer": r["student_answer"][:140],
        })
    sidecar.write_text(json.dumps({"samples": rows}, indent=2))
    return OUT, sidecar


def analyse_paste(paste_path):
    """Compare pasted Gemini scores against cached old C5_fix scores."""
    with Path(paste_path).open() as f:
        paste = json.load(f)
    new_scores = paste.get("scores", paste)
    # Load sidecar to recover the sample list
    sidecar_path = OUT.with_suffix(".samples.json")
    if not sidecar_path.exists():
        sys.exit(f"sidecar not found: {sidecar_path} — re-run without --paste first")
    sidecar = json.loads(sidecar_path.read_text())
    # Load cached eval for old C5 scores
    with (DATA / "kaggle_asag_eval_results.json").open() as f:
        cached = {str(r.get("id")): r for r in json.load(f).get("results", [])}

    print(f"{'id':>5}  {'human':>5}  {'old_C5':>6}  {'new_C5':>6}  "
          f"{'|old-h|':>7}  {'|new-h|':>7}  verdict")
    print("-" * 70)
    deltas = []
    for row in sidecar["samples"]:
        sid = str(row["id"])
        human = float(row["human_score"])
        old = float(cached.get(sid, {}).get("c5_score", 0))
        new_raw = new_scores.get(sid)
        if new_raw is None:
            print(f"{sid:>5}  {human:>5.1f}  {old:>6.2f}  {'--':>6}  (no response)")
            continue
        try:
            new = float(new_raw)
        except (ValueError, TypeError):
            print(f"{sid:>5}  parse error on response: {new_raw!r}")
            continue
        old_err, new_err = abs(human - old), abs(human - new)
        if new_err < old_err - 0.05:
            verdict = "new BETTER"
        elif new_err > old_err + 0.05:
            verdict = "new worse"
        else:
            verdict = "tied"
        deltas.append((old_err, new_err))
        print(f"{sid:>5}  {human:>5.1f}  {old:>6.2f}  {new:>6.2f}  "
              f"{old_err:>7.2f}  {new_err:>7.2f}  {verdict}")
    if deltas:
        import statistics
        mae_old = statistics.mean(o for o, _ in deltas)
        mae_new = statistics.mean(n for _, n in deltas)
        print("-" * 70)
        print(f"Aggregate over {len(deltas)} samples:")
        print(f"  OLD prompt MAE:  {mae_old:.4f}")
        print(f"  NEW prompt MAE:  {mae_new:.4f}")
        print(f"  Delta MAE:       {mae_new - mae_old:+.4f}  "
              f"({'IMPROVEMENT' if mae_new < mae_old else 'regression' if mae_new > mae_old else 'tied'})")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260615)
    ap.add_argument("--paste", type=str, default=None,
                    help="Path to the JSON response from Gemini after pasting")
    args = ap.parse_args()

    if args.paste:
        analyse_paste(args.paste)
        return 0

    records, _ = load_kaggle()
    samples = select_samples(records, args.n, args.seed)
    prompt = build_prompt(samples)
    out, sidecar = write_paste_prompt(samples, prompt)
    print(f"Wrote paste-to-Gemini prompt:")
    print(f"  {out}")
    print(f"Wrote sample sidecar (post-paste compare):")
    print(f"  {sidecar}")
    print(f"\nNext: paste the prompt content into AI Studio, save the JSON")
    print(f"response, then run:")
    print(f"  python3 validate_fix2c_kaggle.py --paste <response.json>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
