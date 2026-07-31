#!/usr/bin/env python3
"""
sample_kg_failure_cases.py — selects a sample of cases where the
pre-Verifier KG-grounded score (kg_score) diverges most from the human
score, for a subsequent inductive (not predetermined-category) failure
analysis. ZERO new API calls -- reuses cached Phase A extraction data
and the already-computed 3-condition ablation scores.

Sampling design (to avoid only looking at the most extreme, possibly
unrepresentative failures): top 60 cases by |kg_score - human_score|,
which is roughly the top 5% of the 1,262-sample real Mohler set, plus
full context (question, reference answer, student answer, extracted
concepts with confidence, matched/missing concepts, C_LLM's score on
the same case for comparison) needed to code each case's failure mode
without a preset taxonomy.

Run:
    python3 sample_kg_failure_cases.py
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).parent


def main() -> int:
    with (BASE / "data" / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = {r["sample_id"]: r for r in json.load(f)}
    with (BASE / "data" / "ablation_three_condition_real.json").open() as f:
        abl = json.load(f)["per_sample"]

    rows = []
    for r in abl:
        a = phase_a.get(r["id"])
        if a is None:
            continue
        kg_err = abs(r["kg_score"] - r["human_score"])
        cllm_err = abs(r["cllm_score"] - r["human_score"])
        rows.append({
            "id": r["id"], "qid": r["qid"],
            "human_score": r["human_score"], "kg_score": r["kg_score"],
            "cllm_score": r["cllm_score"], "c5_fix": r["c5_fix"],
            "kg_err": kg_err, "cllm_err": cllm_err,
            "question": a["question"], "reference_answer": a["reference_answer"],
            "student_answer": a["student_answer"],
            "concepts": a["concept_graph"].get("concepts", []),
            "unmapped_terms": a["concept_graph"].get("unmapped_terms", []),
            "domain_match_score": a["concept_graph"].get("domain_match_score"),
            "out_of_kg_domain": a["concept_graph"].get("out_of_kg_domain"),
            "matched_concepts": a["comparison_result"].get("analysis", {}).get("matched_concepts", []),
            "missing_concepts": a["comparison_result"].get("analysis", {}).get("missing_concepts", []),
            "scores": a["comparison_result"].get("scores", {}),
        })

    rows.sort(key=lambda r: -r["kg_err"])
    top60 = rows[:60]

    print(f"Total real samples: {len(rows)}")
    print(f"Top 60 by |kg_score - human_score|: range {top60[-1]['kg_err']:.3f} to {top60[0]['kg_err']:.3f}")
    print(f"For context, mean |kg_score - human| over all samples: "
          f"{sum(r['kg_err'] for r in rows)/len(rows):.3f}")
    n_cllm_also_wrong = sum(1 for r in top60 if r["cllm_err"] > 1.0)
    print(f"Of these 60, C_LLM also off by >1.0 on the same case: {n_cllm_also_wrong}/60 "
          f"(tells us whether these are 'hard cases generally' or 'kg-score-specific' failures)")

    out_path = BASE / "data" / "kg_failure_case_sample.json"
    out_path.write_text(json.dumps(top60, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
