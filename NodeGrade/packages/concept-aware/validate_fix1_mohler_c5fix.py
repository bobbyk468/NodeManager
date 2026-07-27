#!/usr/bin/env python3
"""
validate_fix1_mohler_c5fix.py — empirical re-validation of the paper's
`concepts_only > C5_fix` claim after Framework Fix #1.

The paper abstract currently reports (based on cached scores from the OLD
C5_fix prompt):
    concepts_only MAE = 0.217 (34.2% reduction)
    C5_fix       MAE = 0.223 (32.4% reduction)

Fix #1 rewrote build_c5fix_prompt() to (a) drop the empirically inert
"Cognitive depth detected: <bloom>" line and (b) reframe from prescriptive
"KG GUIDANCE" to non-prescriptive "PRIMARY (student vs reference) /
SUPPLEMENTARY (KG)" framing.

This script generates a paste-to-Gemini prompt using the PATCHED C5_fix
builder on the same 10 Mohler samples used in the initial validation
(seed=20260601), so post-paste we can compare:
  - old_c5   (from cached kaggle-style eval, pre-Fix #1)
  - new_c5   (Gemini's answer to the patched prompt)
  - human    (Mohler score_avg)
  - concepts_only (from cached ablation)

Usage:
    python3 validate_fix1_mohler_c5fix.py                # dry-run
    python3 validate_fix1_mohler_c5fix.py --paste r.json # post-paste analysis
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"
OUT = BASE / "FRAMEWORK_FIX1_MOHLER_PROMPT_FOR_GEMINI.txt"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260601)
    ap.add_argument("--paste", type=str, default=None)
    args = ap.parse_args()

    if args.paste:
        return _analyse(args.paste)

    import random
    from datasets.mohler_loader import load_mohler_sample
    from generate_batch_scoring_prompts import build_c5fix_prompt
    from concept_matching import should_use_kg_evidence

    dataset = load_mohler_sample()
    with (DATA / "mohler_eval_results.json").open() as f:
        cached = json.load(f).get("results", [])

    # Loader has Q1 samples in descending score order [0..11], Q2 in [12..23], etc.
    # Cache has Q1 samples in ascending score order [0..11], Q2 in [12..23], etc.
    # Score is unique within each question in Mohler → (question_group, human_score)
    # is a bijection between the two orderings.
    # Group loader samples by qid preserving loader order.
    from collections import defaultdict
    loader_by_qid = defaultdict(list)   # qid → [(loader_idx, sample), ...]
    for i, s in enumerate(dataset.samples):
        loader_by_qid[s.question_id].append((i, s))

    # Cache is grouped by question in 12-sample blocks in qid order Q1..Q10.
    # Build (qid, human_score) → cached record. Trust the position-in-cache to
    # infer qid: block k of 12 records is Q{k+1}.
    cache_by_qid_score = {}
    for cache_pos, r in enumerate(cached):
        qidx = cache_pos // 12  # 0..9
        qid_str = f"Q{qidx + 1}"
        key = (qid_str, round(float(r["human_score"]), 3))
        cache_by_qid_score.setdefault(key, []).append(r)

    rng = random.Random(args.seed)
    chosen = []
    for qid, items in loader_by_qid.items():
        rng.shuffle(items)
        chosen.append(items[0])
    chosen = chosen[:args.n]

    batch, features, sidecar_rows = [], {}, []
    for i, s in chosen:
        # Content-safe lookup: (qid, human_score) uniquely identifies the sample
        key = (s.question_id, round(float(s.score_avg), 3))
        cache_matches = cache_by_qid_score.get(key, [])
        if not cache_matches:
            print(f"[warn] no cache match for loader idx={i} qid={s.question_id} score={s.score_avg}")
            continue
        r = cache_matches[0]
        sid = str(r["id"])
        matched = r.get("matched_concepts", [])
        chain_pct = r.get("chain_pct", "0%")
        try:
            cov = float(str(chain_pct).rstrip("%")) / 100.0
        except Exception:
            cov = 0.0
        batch.append({
            "id": sid, "question": s.question,
            "reference_answer": s.reference_answer,
            "student_answer": s.student_answer,
        })
        features[sid] = {
            "matched_concepts": matched,
            "chain_pct": chain_pct,
            "use_kg": should_use_kg_evidence(cov),
            "domain_match_score": 1.0,
            "out_of_kg_domain": False,
        }
        sidecar_rows.append({
            "cache_id": r["id"],
            "loader_idx": i,
            "qid": s.question_id,
            "human_score": s.score_avg,
            "cached_c5": r.get("c5_score"),
            "cached_cllm": r.get("cllm_score"),
            "question": s.question[:100],
            "student_answer_preview": s.student_answer[:140],
        })

    prompt = build_c5fix_prompt(batch, features)
    header = (
        "# Fix #1 re-validation — Mohler C5_fix with PATCHED prompt\n"
        "# Purpose: check whether the paper's claim `concepts_only > C5_fix`\n"
        "# still holds after Fix #1 rewrote the C5_fix system prompt.\n"
        "# Paste everything below the dashes into aistudio.google.com,\n"
        "# gemini-2.5-flash, temperature 0.0, response=JSON.\n"
        "# ------------------------------------------------------------\n\n"
    )
    OUT.write_text(header + prompt + "\n")
    (OUT.with_suffix(".samples.json")).write_text(
        json.dumps({"samples": sidecar_rows}, indent=2)
    )
    print(f"Wrote: {OUT}")
    print(f"Wrote: {OUT.with_suffix('.samples.json')}")
    return 0


def _analyse(paste_path):
    import statistics
    with Path(paste_path).open() as f:
        paste = json.load(f)
    new_scores = paste.get("scores", paste)
    sidecar_rows = json.loads(OUT.with_suffix(".samples.json").read_text())["samples"]
    print(f"{'cache_id':>8} {'qid':>4} {'human':>6} {'cache_c5':>9} {'new_c5':>7} "
          f"{'|old-h|':>7} {'|new-h|':>7}  verdict")
    print("-" * 72)
    olds, news = [], []
    for row in sidecar_rows:
        sid = str(row["cache_id"])
        human = float(row["human_score"])
        cached = float(row["cached_c5"])
        new_raw = new_scores.get(sid)
        if new_raw is None:
            print(f"{row['idx']:>4} {row['qid']:>4} {human:>6.2f} {cached:>9.2f}  (no resp)")
            continue
        try:
            new = float(new_raw)
        except Exception:
            print(f"{row['idx']:>4} parse err: {new_raw!r}")
            continue
        old_err, new_err = abs(human - cached), abs(human - new)
        if new_err < old_err - 0.05: v = "new BETTER"
        elif new_err > old_err + 0.05: v = "new worse"
        else: v = "tied"
        olds.append(old_err); news.append(new_err)
        print(f"{row['cache_id']:>8} {row['qid']:>4} {human:>6.2f} {cached:>9.2f} "
              f"{new:>7.2f} {old_err:>7.2f} {new_err:>7.2f}  {v}")
    if olds:
        print("-" * 68)
        print(f"OLD prompt MAE (cached): {statistics.mean(olds):.4f}")
        print(f"NEW prompt MAE:          {statistics.mean(news):.4f}")
        d = statistics.mean(news) - statistics.mean(olds)
        print(f"Delta:                   {d:+.4f}  "
              f"({'improvement' if d < 0 else 'regression' if d > 0 else 'tied'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
