#!/usr/bin/env python3
"""
compute_verifier_x7_combined_significance.py — full significance suite
for the Verifier self-consistency (K=7, temperature=0.7, median) result
on the COMBINED 50-question/1,371-response real Mohler set (original 46q
+ 4q extension), following the exact same methodology as
compute_combined_extended_significance.py so results are directly
comparable to every other headline number this session.

Unlike the retracted C_LLM/C5_fix ensemble, this design has no tuned
hyperparameter (K=7, temperature=0.7 were fixed in advance, copying the
already-validated C_LLM x7 budget-matched experiment's design) -- so
there is no grid-search-on-the-same-data risk for cross-validation to
catch. This script reports the point estimate and full significance
suite, not a CV check.

Run:
    python3 compute_verifier_x7_combined_significance.py
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import cohen_kappa_score

BASE = Path(__file__).parent


def qwk(human, pred):
    hi = np.round(human * 4).astype(int)
    pi = np.round(np.clip(pred, 0, 5) * 4).astype(int)
    return float(cohen_kappa_score(hi, pi, weights="quadratic"))


def suite(human, pred):
    return {
        "mae": float(np.mean(np.abs(human - pred))),
        "pearson_r": float(np.corrcoef(human, pred)[0, 1]),
        "spearman_r": float(stats.spearmanr(human, pred)[0]),
        "qwk": qwk(human, pred),
        "rmse": float(np.sqrt(np.mean((human - pred) ** 2))),
    }


def paired(err_a, err_b, by_q):
    _, p_rt = stats.wilcoxon(err_a, err_b, alternative="two-sided", zero_method="wilcox")
    _, p_ro = stats.wilcoxon(err_a, err_b, alternative="less", zero_method="wilcox")
    qa = np.array([np.mean(err_a[idx]) for idx in by_q.values()])
    qb = np.array([np.mean(err_b[idx]) for idx in by_q.values()])
    _, p_ct = stats.wilcoxon(qa, qb, alternative="two-sided", zero_method="wilcox")
    _, p_co = stats.wilcoxon(qa, qb, alternative="less", zero_method="wilcox")
    wins = int(sum(1 for x, y in zip(qa, qb) if x < y))
    diffs = err_b - err_a
    d_z = float(diffs.mean() / diffs.std(ddof=1)) if diffs.std(ddof=1) > 0 else 0.0

    n_q = len(qa)
    n_sig_one = n_sig_two = 0
    for i in range(n_q):
        keep = [j for j in range(n_q) if j != i]
        _, p_t = stats.wilcoxon(qa[keep], qb[keep], alternative="two-sided", zero_method="wilcox")
        _, p_o = stats.wilcoxon(qa[keep], qb[keep], alternative="less", zero_method="wilcox")
        if p_o < 0.05:
            n_sig_one += 1
        if p_t < 0.05:
            n_sig_two += 1

    return {
        "d_z": d_z,
        "p_response_two_tailed": float(p_rt), "p_response_one_tailed": float(p_ro),
        "p_cluster_two_tailed": float(p_ct), "p_cluster_one_tailed": float(p_co),
        "question_wins": wins, "question_total": n_q,
        "loocv_one_tailed_significant_folds": n_sig_one,
        "loocv_two_tailed_significant_folds": n_sig_two,
    }


def main() -> int:
    orig = json.loads((BASE / "data" / "verifier_selfconsistency_real_results.json").read_text())["per_sample"]
    ext = json.loads((BASE / "data" / "verifier_selfconsistency_extension_results.json").read_text())["results"]
    combined = orig + ext

    human = np.array([r["human_score"] for r in combined])
    cllm = np.array([r["cllm_score"] for r in combined])
    c5_single = np.array([r["c5_fix_single"] for r in combined])
    verif_x7 = np.array([r["verifier_x7_median"] for r in combined])
    qids = [r["qid"] for r in combined]
    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)

    cllm_stats = suite(human, cllm)
    c5_stats = suite(human, c5_single)
    x7_stats = suite(human, verif_x7)

    print(f"=== Combined: n={len(combined)}, questions={len(set(qids))} ===\n")
    for label, st in [("C_LLM", cllm_stats), ("C5_fix (x1)", c5_stats), ("Verifier x7", x7_stats)]:
        print(f"{label:15s} MAE={st['mae']:.4f}  r={st['pearson_r']:.4f}  rho={st['spearman_r']:.4f}  "
              f"QWK={st['qwk']:.4f}  RMSE={st['rmse']:.4f}")

    err_cllm = np.abs(human - cllm)
    err_c5 = np.abs(human - c5_single)
    err_x7 = np.abs(human - verif_x7)

    x7_vs_cllm = paired(err_x7, err_cllm, by_q)
    x7_vs_c5 = paired(err_x7, err_c5, by_q)
    c5_vs_cllm = paired(err_c5, err_cllm, by_q)

    print(f"\nVerifier x7 vs C_LLM: MAE reduction {(cllm_stats['mae']-x7_stats['mae'])/cllm_stats['mae']*100:.2f}%, "
          f"d_z={x7_vs_cllm['d_z']:.4f}")
    print(f"  response: p_two={x7_vs_cllm['p_response_two_tailed']:.4f} p_one={x7_vs_cllm['p_response_one_tailed']:.4f}")
    print(f"  cluster : p_two={x7_vs_cllm['p_cluster_two_tailed']:.4f} p_one={x7_vs_cllm['p_cluster_one_tailed']:.4f} "
          f"wins={x7_vs_cllm['question_wins']}/{x7_vs_cllm['question_total']}")
    print(f"  LOOCV   : one-tail sig={x7_vs_cllm['loocv_one_tailed_significant_folds']}/{x7_vs_cllm['question_total']}, "
          f"two-tail sig={x7_vs_cllm['loocv_two_tailed_significant_folds']}/{x7_vs_cllm['question_total']}")

    print(f"\nVerifier x7 vs C5_fix(x1): MAE reduction "
          f"{(c5_stats['mae']-x7_stats['mae'])/c5_stats['mae']*100:.2f}%")
    print(f"  response: p_two={x7_vs_c5['p_response_two_tailed']:.4f} p_one={x7_vs_c5['p_response_one_tailed']:.4f}")

    print(f"\nFor reference, C5_fix(x1) vs C_LLM: cluster p_two={c5_vs_cllm['p_cluster_two_tailed']:.4f} "
          f"p_one={c5_vs_cllm['p_cluster_one_tailed']:.4f} wins={c5_vs_cllm['question_wins']}/{c5_vs_cllm['question_total']}")

    out = {
        "n": len(combined), "n_questions": len(set(qids)),
        "cllm": cllm_stats, "c5_fix_single": c5_stats, "verifier_x7": x7_stats,
        "verifier_x7_vs_cllm": x7_vs_cllm, "verifier_x7_vs_c5_single": x7_vs_c5,
        "c5_single_vs_cllm_reference": c5_vs_cllm,
        "note": "verifier_x7 design (K=7, temperature=0.7, median) was fixed in advance "
                "matching the already-validated C_LLM x7 budget-matched experiment -- no "
                "hyperparameter was tuned on this data, unlike the retracted ensemble.",
    }
    out_path = BASE / "data" / "verifier_x7_combined_significance.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
