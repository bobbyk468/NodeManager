#!/usr/bin/env python3
"""
compute_ablation_three_condition_real.py — 3-condition component ablation
on real Mohler data, ZERO new API calls.

Conditions:
  1. C_LLM        — baseline, no KG grounding at all (identical-model zero-shot)
  2. kg_score     — pipeline's internal KG-grounded score BEFORE the verifier
                     (kg_weight=0.05*KG-formula + holistic_weight=0.95*holistic
                     LLM score, exact pipeline.py formula), i.e. "+TRM, no verifier"
  3. C5_fix       — full pipeline including the verifier (kg_weight fully
                     discarded at verifier_weight=1.0, per the architectural
                     finding in compute_verifier_weight_sweep_v2.py)

All three conditions are recomputed from data already collected and cached:
  data/mohler_real_phaseA_signals.json  (concept extraction + comparison + misconceptions)
  data/mohler_real_eval_results.json    (C_LLM, C5_fix, blooms/solo levels)
  data/holistic_score_real.json         (pipeline's internal holistic LLM score)

This does NOT prove intermediate pipeline configurations were independently
re-run live -- kg_score is reconstructed post-hoc from already-cached
components using the exact pipeline.py arithmetic. That is a legitimate
ablation of the SCORE FORMULA's components, not a re-execution of the
pipeline in a different configuration. Documented as such in REPRODUCIBILITY.md.

Run:
    python3 compute_ablation_three_condition_real.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

BASE = Path(__file__).parent

KG_WEIGHT = 0.05
HOLISTIC_WEIGHT = 0.95


def compute_kg_formula_score(comparison_scores: dict, blooms_level: int, solo_level: int,
                               misconceptions: dict) -> float:
    """Exact port of conceptgrade/pipeline.py's _compute_overall_score()."""
    concept_coverage = comparison_scores.get("concept_coverage", 0)
    rel_accuracy = comparison_scores.get("relationship_accuracy", 0)
    integration = comparison_scores.get("integration_quality", 0)
    blooms_normalized = (blooms_level - 1) / 5
    solo_normalized = (solo_level - 1) / 4
    n_misc = misconceptions.get("total_misconceptions", 0)
    critical = misconceptions.get("critical_count", 0)
    misc_penalty = min(0.30, n_misc * 0.06 + critical * 0.10)
    knowledge = concept_coverage * 0.45 + rel_accuracy * 0.35 + integration * 0.20
    depth = blooms_normalized * 0.55 + solo_normalized * 0.45
    score = (knowledge * 0.60 + depth * 0.40) * (1.0 - misc_penalty)
    return min(1.0, max(0.0, score))


def mae(human, pred):
    return float(np.mean(np.abs(human - pred)))


def question_clustered_wilcoxon(rows, err_a, err_b):
    """Average error per question, then Wilcoxon on the 46 question-level pairs."""
    by_q: dict[str, list[tuple[float, float]]] = {}
    for r, ea, eb in zip(rows, err_a, err_b):
        by_q.setdefault(r["qid"], []).append((ea, eb))
    qa, qb = [], []
    for qid, pairs in by_q.items():
        a = np.mean([p[0] for p in pairs])
        b = np.mean([p[1] for p in pairs])
        qa.append(a)
        qb.append(b)
    qa, qb = np.array(qa), np.array(qb)
    n_q = len(qa)
    wins_b = int(np.sum(qb < qa))
    try:
        _, p_two = wilcoxon(qb, qa, alternative="two-sided", zero_method="wilcox")
        _, p_one = wilcoxon(qb, qa, alternative="less", zero_method="wilcox")
    except ValueError:
        p_two, p_one = float("nan"), float("nan")
    return {"n_questions": n_q, "wins_b_over_a": wins_b,
            "p_two_tailed": float(p_two), "p_one_tailed": float(p_one)}


def main() -> int:
    with (BASE / "data" / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = {r["sample_id"]: r for r in json.load(f)}
    with (BASE / "data" / "mohler_real_eval_results.json").open() as f:
        phase_b = json.load(f)["results"]
    with (BASE / "data" / "holistic_score_real.json").open() as f:
        holistic = json.load(f)

    rows = []
    skipped = 0
    for r in phase_b:
        a = phase_a.get(r["id"])
        h = holistic.get(r["id"])
        if a is None or h is None:
            skipped += 1
            continue
        kg_formula = compute_kg_formula_score(
            a["comparison_result"].get("scores", {}),
            r["blooms_level"], r["solo_level"], a["misconceptions"],
        )
        kg_score_01 = KG_WEIGHT * kg_formula + HOLISTIC_WEIGHT * h
        kg_score_5 = round(np.clip(kg_score_01 * 5.0, 0, 5) * 4) / 4
        rows.append({
            "id": r["id"], "qid": r["qid"], "human_score": r["human_score"],
            "cllm_score": r["cllm_score"], "kg_score": kg_score_5, "c5_fix": r["c5_score"],
        })

    print(f"n = {len(rows)} (skipped {skipped} without holistic/phaseA data)")

    human = np.array([r["human_score"] for r in rows])
    cllm = np.array([r["cllm_score"] for r in rows])
    kg = np.array([r["kg_score"] for r in rows])
    c5 = np.array([r["c5_fix"] for r in rows])

    mae_cllm, mae_kg, mae_c5 = mae(human, cllm), mae(human, kg), mae(human, c5)
    r_cllm = float(np.corrcoef(human, cllm)[0, 1])
    r_kg = float(np.corrcoef(human, kg)[0, 1])
    r_c5 = float(np.corrcoef(human, c5)[0, 1])

    err_cllm = np.abs(human - cllm)
    err_kg = np.abs(human - kg)
    err_c5 = np.abs(human - c5)

    _, p_kg_vs_cllm_2 = wilcoxon(err_kg, err_cllm, alternative="two-sided", zero_method="wilcox")
    _, p_kg_vs_cllm_1 = wilcoxon(err_kg, err_cllm, alternative="less", zero_method="wilcox")
    _, p_c5_vs_kg_2 = wilcoxon(err_c5, err_kg, alternative="two-sided", zero_method="wilcox")
    _, p_c5_vs_kg_1 = wilcoxon(err_c5, err_kg, alternative="less", zero_method="wilcox")
    _, p_c5_vs_cllm_2 = wilcoxon(err_c5, err_cllm, alternative="two-sided", zero_method="wilcox")
    _, p_c5_vs_cllm_1 = wilcoxon(err_c5, err_cllm, alternative="less", zero_method="wilcox")

    qc_kg_vs_cllm = question_clustered_wilcoxon(rows, err_cllm, err_kg)
    qc_c5_vs_kg = question_clustered_wilcoxon(rows, err_kg, err_c5)
    qc_c5_vs_cllm = question_clustered_wilcoxon(rows, err_cllm, err_c5)

    print(f"\n=== 3-condition ablation (n={len(rows)}) ===")
    print(f"  C_LLM (no KG)              MAE={mae_cllm:.4f}  r={r_cllm:.4f}")
    print(f"  kg_score (+TRM, no verif)  MAE={mae_kg:.4f}  r={r_kg:.4f}")
    print(f"  C5_fix (+TRM, +verifier)   MAE={mae_c5:.4f}  r={r_c5:.4f}")

    red_kg_vs_cllm = (mae_cllm - mae_kg) / mae_cllm * 100
    red_c5_vs_kg = (mae_kg - mae_c5) / mae_kg * 100
    red_c5_vs_cllm = (mae_cllm - mae_c5) / mae_cllm * 100

    print(f"\nkg_score vs C_LLM:  {red_kg_vs_cllm:+.1f}% MAE change  "
          f"(response-level p_two={p_kg_vs_cllm_2:.4f}, p_one={p_kg_vs_cllm_1:.4f})")
    print(f"  question-clustered: n_q={qc_kg_vs_cllm['n_questions']}, "
          f"wins={qc_kg_vs_cllm['wins_b_over_a']}, p_two={qc_kg_vs_cllm['p_two_tailed']:.4f}, "
          f"p_one={qc_kg_vs_cllm['p_one_tailed']:.4f}")

    print(f"\nC5_fix vs kg_score: {red_c5_vs_kg:+.1f}% MAE change  "
          f"(response-level p_two={p_c5_vs_kg_2:.4f}, p_one={p_c5_vs_kg_1:.4f})")
    print(f"  question-clustered: n_q={qc_c5_vs_kg['n_questions']}, "
          f"wins={qc_c5_vs_kg['wins_b_over_a']}, p_two={qc_c5_vs_kg['p_two_tailed']:.4f}, "
          f"p_one={qc_c5_vs_kg['p_one_tailed']:.4f}")

    print(f"\nC5_fix vs C_LLM:    {red_c5_vs_cllm:+.1f}% MAE change  "
          f"(response-level p_two={p_c5_vs_cllm_2:.4f}, p_one={p_c5_vs_cllm_1:.4f})")
    print(f"  question-clustered: n_q={qc_c5_vs_cllm['n_questions']}, "
          f"wins={qc_c5_vs_cllm['wins_b_over_a']}, p_two={qc_c5_vs_cllm['p_two_tailed']:.4f}, "
          f"p_one={qc_c5_vs_cllm['p_one_tailed']:.4f}")

    out = {
        "n": len(rows), "skipped": skipped,
        "conditions": {
            "cllm": {"mae": mae_cllm, "r": r_cllm},
            "kg_score": {"mae": mae_kg, "r": r_kg, "description": "kg_weight=0.05*KG-formula + holistic_weight=0.95*holistic LLM score, no verifier"},
            "c5_fix": {"mae": mae_c5, "r": r_c5},
        },
        "kg_vs_cllm": {
            "mae_reduction_pct": red_kg_vs_cllm,
            "response_level": {"p_two_tailed": float(p_kg_vs_cllm_2), "p_one_tailed": float(p_kg_vs_cllm_1)},
            "question_clustered": qc_kg_vs_cllm,
        },
        "c5_vs_kg": {
            "mae_reduction_pct": red_c5_vs_kg,
            "response_level": {"p_two_tailed": float(p_c5_vs_kg_2), "p_one_tailed": float(p_c5_vs_kg_1)},
            "question_clustered": qc_c5_vs_kg,
        },
        "c5_vs_cllm": {
            "mae_reduction_pct": red_c5_vs_cllm,
            "response_level": {"p_two_tailed": float(p_c5_vs_cllm_2), "p_one_tailed": float(p_c5_vs_cllm_1)},
            "question_clustered": qc_c5_vs_cllm,
        },
        "per_sample": rows,
    }
    out_path = BASE / "data" / "ablation_three_condition_real.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
