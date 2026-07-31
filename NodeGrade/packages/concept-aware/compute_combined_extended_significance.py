#!/usr/bin/env python3
"""
compute_combined_extended_significance.py — full rigorous significance
suite on the COMBINED real Mohler dataset (2026-07-28): the original
frozen 46-question/1,262-response KG-aligned subset PLUS the 4-question/
109-response extension (data/mohler_real_extension_eval_results.json),
for a total of 50 questions / 1,371 responses.

This does NOT modify the original frozen files
(data/mohler_real_eval_results.json, data/mohler_real/mohler_real_kg_aligned.json)
which remain the reproducibility anchor for every number currently in
either paper. This script's output is a separate, clearly-labeled
combined-dataset analysis, held out of both papers until further
validated (per explicit instruction 2026-07-28: prove the model
robustly beats the baseline before touching paper text).

Reuses the exact methodology already established and checked in
verify_all_paper_claims.py sections 2b/4 (MAE, Pearson r, quadratic-
weighted kappa (QWK), RMSE, response-level Wilcoxon, question-clustered
Wilcoxon, LOOCV over question folds) so results are directly comparable
to the existing headline numbers.

Also evaluates the C_LLM/C5_fix linear ensemble
(compute_cllm_c5_ensemble_real.py's finding) on this same combined
dataset, sweeping w_cllm to find where every metric (MAE, Pearson,
Spearman, question-clustered significance) simultaneously beats C_LLM.

Run:
    python3 compute_combined_extended_significance.py
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


def full_suite(human, pred, qids, label):
    err = np.abs(human - pred)
    mae = float(np.mean(err))
    r = float(np.corrcoef(human, pred)[0, 1])
    rho = float(stats.spearmanr(human, pred)[0])
    q = qwk(human, pred)
    rmse = float(np.sqrt(np.mean((human - pred) ** 2)))

    by_q = collections.defaultdict(list)
    for i, qid in enumerate(qids):
        by_q[qid].append(i)
    n_q = len(by_q)

    out = {
        "label": label, "n": len(human), "n_questions": n_q,
        "mae": mae, "pearson_r": r, "spearman_r": rho, "qwk": q, "rmse": rmse,
        "human_mean": float(np.mean(human)), "pred_mean": float(np.mean(pred)),
    }
    return out, err, by_q


def paired_tests(err_a, err_b, by_q, label_a, label_b):
    """err_a is the 'new' system, err_b is the baseline being compared against."""
    diffs = err_b - err_a  # positive = a (new) has smaller error
    n_nonzero = int(np.sum(diffs != 0))
    d_z = float(diffs.mean() / diffs.std(ddof=1)) if diffs.std(ddof=1) > 0 else 0.0

    _, p_resp_two = stats.wilcoxon(err_a, err_b, alternative="two-sided", zero_method="wilcox")
    _, p_resp_one = stats.wilcoxon(err_a, err_b, alternative="less", zero_method="wilcox")

    qerr_a = np.array([np.mean(err_a[idx]) for idx in by_q.values()])
    qerr_b = np.array([np.mean(err_b[idx]) for idx in by_q.values()])
    _, p_clust_two = stats.wilcoxon(qerr_a, qerr_b, alternative="two-sided", zero_method="wilcox")
    _, p_clust_one = stats.wilcoxon(qerr_a, qerr_b, alternative="less", zero_method="wilcox")
    wins = int(sum(1 for x, y in zip(qerr_a, qerr_b) if x < y))
    n_q = len(qerr_a)

    n_sig_one = n_sig_two = 0
    for i in range(n_q):
        keep = [j for j in range(n_q) if j != i]
        _, p_t = stats.wilcoxon(qerr_a[keep], qerr_b[keep], alternative="two-sided", zero_method="wilcox")
        _, p_o = stats.wilcoxon(qerr_a[keep], qerr_b[keep], alternative="less", zero_method="wilcox")
        if p_o < 0.05:
            n_sig_one += 1
        if p_t < 0.05:
            n_sig_two += 1

    return {
        "comparison": f"{label_a}_vs_{label_b}",
        "n_nonzero_diffs": n_nonzero, "d_z": d_z,
        "p_response_two_tailed": float(p_resp_two), "p_response_one_tailed": float(p_resp_one),
        "p_cluster_two_tailed": float(p_clust_two), "p_cluster_one_tailed": float(p_clust_one),
        "question_wins": wins, "question_total": n_q,
        "loocv_one_tailed_significant_folds": n_sig_one,
        "loocv_two_tailed_significant_folds": n_sig_two,
    }


def main() -> int:
    orig = json.loads((BASE / "data" / "mohler_real_eval_results.json").read_text())["results"]
    ext = json.loads((BASE / "data" / "mohler_real_extension_eval_results.json").read_text())["results"]
    combined = orig + ext

    human = np.array([r["human_score"] for r in combined])
    cllm = np.array([r["cllm_score"] for r in combined])
    c5 = np.array([r["c5_score"] for r in combined])
    qids = [r["qid"] for r in combined]

    print(f"=== Combined dataset: n={len(combined)}, questions={len(set(qids))} ===")
    print(f"(original: n={len(orig)}/{len({r['qid'] for r in orig})}q, "
          f"extension: n={len(ext)}/{len({r['qid'] for r in ext})}q)\n")

    cllm_stats, err_cllm, by_q = full_suite(human, cllm, qids, "C_LLM")
    c5_stats, err_c5, _ = full_suite(human, c5, qids, "C5_fix")

    for st in (cllm_stats, c5_stats):
        print(f"{st['label']:8s}  MAE={st['mae']:.4f}  r={st['pearson_r']:.4f}  "
              f"rho={st['spearman_r']:.4f}  QWK={st['qwk']:.4f}  RMSE={st['rmse']:.4f}")

    c5_vs_cllm = paired_tests(err_c5, err_cllm, by_q, "C5_fix", "C_LLM")
    print(f"\nC5_fix vs C_LLM: MAE reduction {(cllm_stats['mae']-c5_stats['mae'])/cllm_stats['mae']*100:.2f}%, "
          f"d_z={c5_vs_cllm['d_z']:.4f}")
    print(f"  response: p_two={c5_vs_cllm['p_response_two_tailed']:.4f} "
          f"p_one={c5_vs_cllm['p_response_one_tailed']:.4f}")
    print(f"  cluster : p_two={c5_vs_cllm['p_cluster_two_tailed']:.4f} "
          f"p_one={c5_vs_cllm['p_cluster_one_tailed']:.4f} "
          f"wins={c5_vs_cllm['question_wins']}/{c5_vs_cllm['question_total']}")
    print(f"  LOOCV   : one-tail sig folds={c5_vs_cllm['loocv_one_tailed_significant_folds']}/{c5_vs_cllm['question_total']}, "
          f"two-tail sig folds={c5_vs_cllm['loocv_two_tailed_significant_folds']}/{c5_vs_cllm['question_total']}")

    # Ensemble sweep on the combined dataset
    print("\n=== C_LLM/C5_fix ensemble sweep on combined data ===")
    ensemble_results = []
    for w in np.arange(0.0, 0.65, 0.05):
        w = round(float(w), 2)
        blend = w * cllm + (1 - w) * c5
        blend_q = np.clip(np.round(blend * 4) / 4, 0, 5)
        blend_stats, err_blend, _ = full_suite(human, blend_q, qids, f"ensemble_w{w}")
        vs_cllm = paired_tests(err_blend, err_cllm, by_q, f"ensemble_w{w}", "C_LLM")
        beats_both_corr = blend_stats["pearson_r"] > cllm_stats["pearson_r"] and \
                           blend_stats["spearman_r"] > cllm_stats["spearman_r"]
        beats_mae = blend_stats["mae"] < cllm_stats["mae"]
        clust_sig_both = vs_cllm["p_cluster_one_tailed"] < 0.05 and vs_cllm["p_cluster_two_tailed"] < 0.05
        row = {"w_cllm": w, **blend_stats, **vs_cllm, "beats_cllm_on_both_correlations": beats_both_corr,
               "beats_cllm_on_mae": beats_mae, "cluster_significant_both_tails": clust_sig_both}
        ensemble_results.append(row)
        marker = ""
        if beats_both_corr and beats_mae and clust_sig_both:
            marker = "  <-- MAE+corr+cluster(2-tail) ALL beat C_LLM"
        print(f"  w={w:.2f}  MAE={blend_stats['mae']:.4f}  r={blend_stats['pearson_r']:.4f}  "
              f"rho={blend_stats['spearman_r']:.4f}  "
              f"clust_p1={vs_cllm['p_cluster_one_tailed']:.4f}  clust_p2={vs_cllm['p_cluster_two_tailed']:.4f}"
              f"{marker}")

    fully_winning = [r for r in ensemble_results
                      if r["beats_cllm_on_both_correlations"] and r["beats_cllm_on_mae"]
                      and r["cluster_significant_both_tails"]]
    # Among configs that fully win, prefer the smallest w_cllm (keeps the most MAE gain).
    recommended = min(fully_winning, key=lambda r: r["w_cllm"]) if fully_winning else None

    out = {
        "n": len(combined), "n_questions": len(set(qids)),
        "source": {"original_n": len(orig), "original_questions": len({r["qid"] for r in orig}),
                   "extension_n": len(ext), "extension_questions": len({r["qid"] for r in ext})},
        "cllm": cllm_stats, "c5_fix": c5_stats,
        "c5_vs_cllm": c5_vs_cllm,
        "ensemble_sweep": ensemble_results,
        "ensemble_recommended": recommended,
        "status": "NOT YET ADDED TO EITHER PAPER -- held pending further validation, "
                  "per explicit instruction 2026-07-28",
    }
    out_path = BASE / "data" / "combined_extended_significance.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    print("\nNOTE: this analysis has NOT been added to either paper (held pending further validation).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
