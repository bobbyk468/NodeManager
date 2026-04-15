"""
Threshold sweep for semantic concept matching on Kaggle ASAG.

Loads the Kaggle ASAG dataset + KG, runs keyword-only and keyword+semantic
matching at multiple cosine thresholds, and reports coverage statistics.
Saves the best-threshold precomputed features to
  data/kaggle_asag_precomputed_semantic.json

No API calls required — all data is local.

Usage:
    python3 analyze_concept_matching_threshold.py [--save-threshold 0.45]
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

SEP = "=" * 72


def load_data() -> tuple[list[dict], dict]:
    with open(os.path.join(DATA_DIR, "kaggle_asag_dataset.json")) as f:
        dataset = json.load(f)
    with open(os.path.join(DATA_DIR, "kaggle_asag_auto_kg.json")) as f:
        kg_raw = json.load(f)
    # KG is nested under "question_kgs" keyed by question index string
    q_to_kg = kg_raw.get("question_kgs", kg_raw)
    return dataset, q_to_kg


def build_question_index(dataset: list[dict], q_to_kg: dict) -> dict[str, dict]:
    """Map each dataset question text to its KG (by q_to_kg key)."""
    # q_to_kg is keyed 0..N by question index; dataset rows have "question" text
    # Build a map: question_text -> kg
    q_to_index: dict[str, str] = {}
    for idx, qdata in q_to_kg.items():
        q_to_index[qdata.get("question", "").strip().lower()] = idx
    return q_to_index


def coverage_stats(coverages: list[float]) -> dict:
    arr = np.array(coverages)
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "zero_pct": float(np.mean(arr == 0) * 100),
        "low_pct": float(np.mean(arr < 0.25) * 100),
        "mid_pct": float(np.mean((arr >= 0.25) & (arr < 0.75)) * 100),
        "high_pct": float(np.mean(arr >= 0.75) * 100),
    }


def fmt_stats(stats: dict) -> str:
    return (
        f"mean={stats['mean']:.3f}  median={stats['median']:.3f}  "
        f"zero={stats['zero_pct']:.1f}%  low={stats['low_pct']:.1f}%  "
        f"mid={stats['mid_pct']:.1f}%  high={stats['high_pct']:.1f}%"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--save-threshold",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Save precomputed features at this threshold to "
             "data/kaggle_asag_precomputed_semantic.json (e.g. 0.45)",
    )
    parser.add_argument(
        "--thresholds",
        nargs="+",
        type=float,
        default=[0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70],
        metavar="F",
        help="Cosine thresholds to sweep",
    )
    args = parser.parse_args()

    dataset, q_to_kg = load_data()
    q_to_index = build_question_index(dataset, q_to_kg)

    # Import matching helpers
    from concept_matching import (
        ConceptEmbeddingCache,
        simple_concept_match,
        coverage_ratio,
        should_use_kg_evidence,
    )
    from concept_matching import _load_embedder  # noqa: F401 — trigger model load

    # Build embedding cache over all KG concepts
    print("Loading sentence-transformer model and encoding all concepts...")
    cache = ConceptEmbeddingCache(q_to_kg)
    if not cache.active:
        print("  ⚠ sentence-transformers not available; semantic sweep skipped")
        print("  Install: pip install sentence-transformers")
        return
    print(f"  Encoded {len(cache.ids)} unique KG concepts.")

    def get_kg_for_row(row: dict) -> tuple[list[dict], list[str]]:
        q_text = row.get("question", "").strip().lower()
        idx = q_to_index.get(q_text)
        if idx is None:
            return [], []
        kg_entry = q_to_kg[idx]
        concepts = kg_entry.get("concepts", [])
        expected = kg_entry.get("expected_concepts", [])
        return concepts, expected

    # ── Keyword-only baseline ──
    kw_coverages = []
    for row in dataset:
        concepts, expected = get_kg_for_row(row)
        if not concepts:
            kw_coverages.append(0.0)
            continue
        matched = simple_concept_match(row.get("student_answer", ""), concepts)
        kw_coverages.append(coverage_ratio(matched, expected))

    print()
    print(SEP)
    print("COVERAGE STATISTICS — Kaggle ASAG (n=473)")
    print(SEP)
    print(f"\n  Keyword-only (baseline):  {fmt_stats(coverage_stats(kw_coverages))}")

    # ── Semantic threshold sweep ──
    print()
    print(f"  {'Threshold':>10}  {'mean':>6}  {'median':>7}  "
          f"{'zero%':>6}  {'low%':>5}  {'mid%':>5}  {'high%':>6}  {'kg_used%':>8}")
    print("  " + "-" * 68)

    best_thr = None
    best_score = -1.0  # maximize mean coverage while minimizing zero%
    sweep_results: dict[float, list[float]] = {}

    for thr in sorted(args.thresholds):
        sem_coverages = []
        for row in dataset:
            concepts, expected = get_kg_for_row(row)
            if not concepts:
                sem_coverages.append(0.0)
                continue
            student_ans = row.get("student_answer", "")
            kw = set(simple_concept_match(student_ans, concepts))
            sem = set(cache.semantic_hits(student_ans, concepts, thr))
            matched = list(kw | sem)
            sem_coverages.append(coverage_ratio(matched, expected))
        sweep_results[thr] = sem_coverages
        stats = coverage_stats(sem_coverages)
        kg_used = sum(1 for c in sem_coverages if should_use_kg_evidence(c)) / len(sem_coverages) * 100
        print(f"  {thr:>10.2f}  {stats['mean']:>6.3f}  {stats['median']:>7.3f}  "
              f"{stats['zero_pct']:>6.1f}  {stats['low_pct']:>5.1f}  "
              f"{stats['mid_pct']:>5.1f}  {stats['high_pct']:>6.1f}  {kg_used:>8.1f}")
        # Score: maximize (mean + 0.5*high_pct/100) − 0.3*(zero_pct/100)
        composite = stats["mean"] + 0.5 * stats["high_pct"] / 100 - 0.3 * stats["zero_pct"] / 100
        if composite > best_score:
            best_score = composite
            best_thr = thr

    print()
    print(f"  Best threshold by composite score: {best_thr} (score={best_score:.4f})")

    # ── Save precomputed features at requested or best threshold ──
    save_thr = args.save_threshold if args.save_threshold is not None else best_thr
    if save_thr not in sweep_results:
        # Run it if not in sweep
        sem_coverages = []
        for row in dataset:
            concepts, expected = get_kg_for_row(row)
            if not concepts:
                sem_coverages.append(0.0)
                continue
            kw = set(simple_concept_match(row.get("student_answer", ""), concepts))
            sem = set(cache.semantic_hits(row.get("student_answer", ""), concepts, save_thr))
            matched = list(kw | sem)
            sem_coverages.append(coverage_ratio(matched, expected))
        sweep_results[save_thr] = sem_coverages

    # Build precomputed features dict (same schema as kaggle_asag_precomputed.json)
    from concept_matching import _DEFAULT_KG_MIN_COVERAGE
    precomputed: dict[str, dict] = {}
    for row, cov in zip(dataset, sweep_results[save_thr]):
        sid = str(row["id"])
        concepts, expected = get_kg_for_row(row)
        if not concepts:
            precomputed[sid] = {
                "matched_concepts": [], "chain_pct": "0%",
                "solo": "Prestructural", "bloom": "Remember",
                "n_kg_concepts": 0, "coverage_ratio": 0.0, "use_kg": False,
            }
            continue
        kw = set(simple_concept_match(row.get("student_answer", ""), concepts))
        sem = set(cache.semantic_hits(row.get("student_answer", ""), concepts, save_thr))
        matched = list(kw | sem)
        cov_ratio = coverage_ratio(matched, expected)
        chain_pct = f"{int(cov_ratio * 100)}%"

        # Derive SOLO heuristic from coverage
        if cov_ratio == 0:
            solo = "Prestructural"
        elif cov_ratio < 0.25:
            solo = "Unistructural"
        elif cov_ratio < 0.75:
            solo = "Multistructural"
        elif cov_ratio < 1.0:
            solo = "Relational"
        else:
            solo = "Extended Abstract"

        # Bloom heuristic: simple keyword-based
        ans_lower = row.get("student_answer", "").lower()
        if any(w in ans_lower for w in ["evaluate", "critique", "judge", "argue", "defend"]):
            bloom = "Evaluate"
        elif any(w in ans_lower for w in ["create", "design", "propose", "develop", "construct"]):
            bloom = "Create"
        elif any(w in ans_lower for w in ["analyze", "compare", "contrast", "distinguish", "examine"]):
            bloom = "Analyze"
        elif any(w in ans_lower for w in ["apply", "demonstrate", "use", "calculate", "solve"]):
            bloom = "Apply"
        elif any(w in ans_lower for w in ["explain", "describe", "summarize", "classify"]):
            bloom = "Understand"
        else:
            bloom = "Remember"

        precomputed[sid] = {
            "matched_concepts": matched,
            "chain_pct": chain_pct,
            "solo": solo,
            "bloom": bloom,
            "n_kg_concepts": len(concepts),
            "coverage_ratio": round(cov_ratio, 4),
            "use_kg": should_use_kg_evidence(cov_ratio),
        }

    out_path = os.path.join(DATA_DIR, "kaggle_asag_precomputed_semantic.json")
    with open(out_path, "w") as f:
        json.dump(precomputed, f, indent=2)

    # Summary comparison
    print(SEP)
    print(f"SAVED → {out_path}  (threshold={save_thr})")
    print()
    old_path = os.path.join(DATA_DIR, "kaggle_asag_precomputed.json")
    if os.path.exists(old_path):
        with open(old_path) as f:
            old_pre = json.load(f)
        old_covs = [v.get("coverage_ratio", 0.0) for v in old_pre.values()]
        new_covs = sweep_results[save_thr]
        print("  Comparison: current precomputed vs new semantic precomputed")
        print(f"  Current:   {fmt_stats(coverage_stats(old_covs))}")
        print(f"  New (t={save_thr:.2f}): {fmt_stats(coverage_stats(new_covs))}")
        delta_mean = np.mean(new_covs) - np.mean(old_covs)
        delta_zero = (np.mean(np.array(new_covs) == 0) - np.mean(np.array(old_covs) == 0)) * 100
        print(f"\n  Δ mean coverage: {delta_mean:+.3f}")
        print(f"  Δ zero coverage: {delta_zero:+.1f}pp")
        print()
        print("  NOTE: These precomputed features are ready for re-scoring.")
        print("  To re-score with new features (requires GEMINI_API_KEY):")
        print(f"    cp {out_path} {old_path}")
        print(f"    rm data/batch_responses/kaggle_asag_c5fix_batch_*_response.json")
        print(f"    python3 run_full_pipeline.py --dataset kaggle_asag --skip-kg")


if __name__ == "__main__":
    main()
