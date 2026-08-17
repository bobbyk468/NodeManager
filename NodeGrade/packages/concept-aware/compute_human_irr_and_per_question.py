#!/usr/bin/env python3
"""
compute_human_irr_and_per_question.py — two cached-data sanity checks
that resist common hostile-reviewer attacks:

  1. Inter-rater agreement between the TWO HUMAN ANNOTATORS in the
     Mohler dataset. Defuses the ``your ground truth is noise''
     attack by quantifying the ceiling.
  2. Per-question MAE breakdown showing the result is not driven by
     1-2 questions. Reports the fraction of questions on which C5
     beats C_LLM.

Run:
    python compute_human_irr_and_per_question.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from datasets.mohler_loader import load_mohler_sample  # noqa: E402
from sklearn.metrics import cohen_kappa_score  # noqa: E402


def main() -> int:
    ds = load_mohler_sample()
    sm = np.array([s.score_me for s in ds.samples])
    so = np.array([s.score_other for s in ds.samples])
    diff = np.abs(sm - so)

    sm_int = (sm * 2).round().astype(int)
    so_int = (so * 2).round().astype(int)
    qwk = float(cohen_kappa_score(sm_int, so_int, weights="quadratic"))
    ck = float(cohen_kappa_score(sm_int, so_int))

    human = {
        "n": int(len(diff)),
        "pearson_r": round(float(np.corrcoef(sm, so)[0, 1]), 4),
        "mean_abs_diff": round(float(diff.mean()), 4),
        "max_abs_diff": float(diff.max()),
        "samples_exactly_agree": int((diff == 0).sum()),
        "samples_disagree_ge_1": int((diff >= 1).sum()),
        "samples_disagree_ge_2": int((diff >= 2).sum()),
        "qwk_quadratic": round(qwk, 4),
        "cohen_kappa": round(ck, 4),
    }

    with (BASE / "archive" / "fabricated_fixtures" / "mohler_eval_results.json").open() as f:
        ev = json.load(f)
    res = ev["results"]
    per_q = []
    for q in range(10):
        idxs = list(range(q * 12, (q + 1) * 12))
        h = np.array([res[i]["human_score"] for i in idxs])
        c = np.array([res[i]["cllm_score"] for i in idxs])
        f5 = np.array([res[i]["c5_score"] for i in idxs])
        em = float(np.abs(h - c).mean())
        ef = float(np.abs(h - f5).mean())
        per_q.append({
            "question": f"Q{q+1}",
            "n": len(idxs),
            "mae_cllm": round(em, 4),
            "mae_c5": round(ef, 4),
            "delta_mae": round(em - ef, 4),
            "reduction_pct": round((em - ef) / em * 100, 1) if em else 0.0,
            "c5_wins": ef < em,
        })

    out = {
        "human_inter_rater": human,
        "per_question": per_q,
        "c5_wins_count": sum(1 for x in per_q if x["c5_wins"]),
        "c5_wins_questions": [x["question"] for x in per_q if x["c5_wins"]],
        "cllm_wins_questions": [x["question"] for x in per_q if not x["c5_wins"]],
    }

    print("=== Human inter-rater agreement (Mohler 2 raters, n=120) ===")
    print(f"  r={human['pearson_r']}  mean|diff|={human['mean_abs_diff']}  "
          f"max|diff|={human['max_abs_diff']}")
    print(f"  exact agreement: {human['samples_exactly_agree']}/120")
    print(f"  disagree ≥1: {human['samples_disagree_ge_1']}/120  "
          f"disagree ≥2: {human['samples_disagree_ge_2']}/120")
    print(f"  QWK: {human['qwk_quadratic']}  Cohen κ: {human['cohen_kappa']}")

    print("\n=== Per-question MAE breakdown ===")
    print(f"  {'Q':<5}{'n':<4}{'MAE_C_LLM':<12}{'MAE_C5':<10}"
          f"{'Δ':<10}{'reduce':<10}{'winner':<8}")
    for x in per_q:
        winner = "C5" if x["c5_wins"] else "C_LLM"
        sign = "+" if x["delta_mae"] >= 0 else ""
        print(f"  {x['question']:<5}{x['n']:<4}{x['mae_cllm']:<12}"
              f"{x['mae_c5']:<10}{sign+format(x['delta_mae'],'.4f'):<10}"
              f"{x['reduction_pct']:<10}{winner:<8}")
    print(f"  C5 wins {out['c5_wins_count']}/10 questions "
          f"({out['c5_wins_questions']})")

    (BASE / "data" / "human_irr_per_question.json").write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
