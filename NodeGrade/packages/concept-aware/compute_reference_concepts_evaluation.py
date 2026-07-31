#!/usr/bin/env python3
"""
compute_reference_concepts_evaluation.py — evaluates reference-answer-
derived concepts as the `expected_concepts` candidate for Finding 3
(concept_coverage vacuity), using the same criteria as the round-2
seed_ids/expanded-subgraph experiment (compute_expected_concepts_candidates.py)
plus GPT's round-3 additions: expected-set-size comparison and a
hard-case check (does reference coverage help specifically where C_LLM,
the independent KG-free baseline, is also wrong?).

ZERO new API calls beyond the 42 already spent on
run_reference_answer_extraction.py -- this script only recomputes
ConfidenceWeightedComparator's real coverage formula against cached,
unchanged student extractions.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent
W_COV, W_ACC, W_INT = 0.45, 0.35, 0.20


def weighted_coverage(student_concepts: set[str], expected: set[str], confidence_map: dict[str, float]) -> float:
    if not expected:
        return 0.0
    matched_weight = 0.0
    total_weight = 0.0
    for cid in expected:
        total_weight += 1.0
        if cid in student_concepts:
            matched_weight += confidence_map.get(cid, 1.0)
    return min(1.0, matched_weight / total_weight) if total_weight > 0 else 0.0


def main() -> int:
    ref_concepts = {r["question_id"]: {c["concept_id"] for c in r["concepts"]}
                     for r in json.loads((BASE / "data" / "reference_concepts_mohler.json").read_text())}

    phase_a = json.loads((BASE / "data" / "mohler_real_phaseA_signals.json").read_text())
    abl = {r["id"]: r for r in json.loads((BASE / "data" / "ablation_three_condition_real.json").read_text())["per_sample"]}

    rows = []
    n_empty_ref = 0
    for r in phase_a:
        cg = r["concept_graph"]
        if cg.get("out_of_kg_domain"):
            continue
        qid = r["question_id"]
        expected = ref_concepts.get(qid, set())
        if not expected:
            n_empty_ref += 1

        student_ids = {c["concept_id"] for c in cg["concepts"]}
        confidence_map = {c["concept_id"]: c["confidence"] for c in cg["concepts"]}

        scores = r["comparison_result"]["scores"]
        acc = scores["relationship_accuracy"]
        integ = scores["integration_quality"]
        cov_current = scores["concept_coverage"]
        cov_ref = weighted_coverage(student_ids, expected, confidence_map)

        cllm_err = abs(abl[r["sample_id"]]["cllm_score"] - r["human_score"]) if r["sample_id"] in abl else None

        rows.append({
            "id": r["sample_id"], "qid": qid, "human": r["human_score"],
            "n_expected": len(expected), "cov_current": cov_current, "cov_ref": cov_ref,
            "acc": acc, "integ": integ, "cllm_err": cllm_err,
        })

    print(f"In-domain samples analyzed: {len(rows)}")
    print(f"Questions with empty reference-concept set (extractor found nothing, e.g. 'by reference'): {n_empty_ref} samples affected")

    n_expected_sizes = {"current(self-ref, dynamic)": None, "reference": [r["n_expected"] for r in rows]}
    print(f"\nMean |expected_concepts| under reference candidate: {statistics.mean(n_expected_sizes['reference']):.2f}")
    print(f"(for comparison, round-2 found: current(self-ref) varies per-sample by definition; "
          f"seed_ids and expanded were much larger, driving the 100% FPR)")

    human = np.array([r["human"] for r in rows])

    def knowledge_scores(cov_key: str) -> np.ndarray:
        return np.array([r[cov_key] * W_COV + r["acc"] * W_ACC + r["integ"] * W_INT for r in rows])

    print("\n=== Downstream 'knowledge' component (0-1 scale) ===")
    results = {}
    for label, key in [("current (self-referential)", "cov_current"), ("reference-answer", "cov_ref")]:
        know = knowledge_scores(key)
        know_5 = know * 5.0
        mae = float(np.mean(np.abs(know_5 - human)))
        r_val = float(np.corrcoef(know_5, human)[0, 1])
        cov_arr = np.array([r[key] for r in rows])
        high_q_mask = human >= 4.0
        fpr = float(np.mean(cov_arr[high_q_mask] < 0.5)) if high_q_mask.sum() else float("nan")
        low_q_vacuous_mask = (human <= 2.0) & (np.array([r["cov_current"] for r in rows]) == 1.0)
        n_low_q_vacuous = int(low_q_vacuous_mask.sum())
        corrected = float(np.mean(cov_arr[low_q_vacuous_mask] < 1.0)) if n_low_q_vacuous else float("nan")
        results[label] = {"mae": mae, "pearson_r": r_val, "fpr": fpr,
                           "low_quality_correction_rate": corrected, "n_low_quality_vacuous": n_low_q_vacuous}
        print(f"\n  [{label}]")
        print(f"    knowledge*5 MAE vs human: {mae:.3f}   Pearson r: {r_val:.4f}")
        print(f"    False Penalty Rate (human>=4.0 & new_cov<0.5): {fpr:.4f} ({int(high_q_mask.sum())} samples)")
        print(f"    Low-quality-vacuous correction rate (of {n_low_q_vacuous} known cases): {corrected:.4f}")

    print("\n=== Coverage distribution ===")
    for label, key in [("current", "cov_current"), ("reference", "cov_ref")]:
        arr = np.array([r[key] for r in rows])
        n_at_1 = int(np.sum(arr >= 0.999))
        n_at_0 = int(np.sum(arr <= 0.001))
        print(f"  {label:10s}: mean={arr.mean():.3f} std={arr.std():.3f} "
              f"at_1.0={n_at_1}/{len(arr)} ({100*n_at_1/len(arr):.1f}%) at_0.0={n_at_0}/{len(arr)} ({100*n_at_0/len(arr):.1f}%)")

    # Hard-case check (GPT's round-3 Q4 validation): does reference coverage
    # move in the right direction specifically where C_LLM itself is wrong?
    hard = [r for r in rows if r["cllm_err"] is not None and r["cllm_err"] > 1.0]
    easy = [r for r in rows if r["cllm_err"] is not None and r["cllm_err"] <= 1.0]
    print(f"\n=== Hard-case check (C_LLM err > 1.0): n={len(hard)} vs easy n={len(easy)} ===")
    for label, subset in [("hard (C_LLM wrong)", hard), ("easy (C_LLM right)", easy)]:
        if not subset:
            continue
        h = np.array([r["human"] for r in subset])
        know_cur = np.array([r["cov_current"] * W_COV + r["acc"] * W_ACC + r["integ"] * W_INT for r in subset]) * 5.0
        know_ref = np.array([r["cov_ref"] * W_COV + r["acc"] * W_ACC + r["integ"] * W_INT for r in subset]) * 5.0
        mae_cur = float(np.mean(np.abs(know_cur - h)))
        mae_ref = float(np.mean(np.abs(know_ref - h)))
        print(f"  {label}: n={len(subset)}  current MAE={mae_cur:.3f}  reference MAE={mae_ref:.3f}  "
              f"({'reference better' if mae_ref < mae_cur else 'current better'})")

    out_path = BASE / "data" / "reference_concepts_evaluation.json"
    out_path.write_text(json.dumps({
        "n_samples": len(rows), "n_empty_ref_samples": n_empty_ref,
        "mean_expected_size": statistics.mean(n_expected_sizes["reference"]),
        "results": results,
        "hard_case_n": len(hard), "easy_case_n": len(easy),
    }, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
