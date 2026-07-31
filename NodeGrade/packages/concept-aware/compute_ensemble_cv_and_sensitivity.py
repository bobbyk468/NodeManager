#!/usr/bin/env python3
"""
compute_ensemble_cv_and_sensitivity.py — closes the two offline-checkable
gaps flagged in REPRODUCIBILITY.md's 2026-07-28 "Dataset expansion +
ensemble" entry before it can be considered validated:

  (A) Cross-validated ensemble weight selection. The w_cllm=0.45 result
      was picked by sweeping a grid and reading off the best point on
      the SAME data being reported -- a garden-of-forking-paths risk.
      This script instead runs genuine leave-one-question-out CV: for
      each of the 50 questions, sweep w on the OTHER 49 questions only
      (selecting by training-fold MAE), then apply that fold-specific w
      to the held-out question's samples. The aggregated out-of-fold
      predictions across all 50 folds are then evaluated with the same
      full significance suite as compute_combined_extended_significance.py.
      This tests whether the ensemble benefit generalises, not just
      whether some w fits this exact sample.

  (B) Sensitivity check excluding the 2 out-of-domain extension
      questions (E08.Q06, E10.Q03 -- both flagged out_of_kg_domain=True
      by the pipeline itself). Re-runs the same CV procedure on the
      48-question set (46 original + E11.Q09 + E12.Q02 only) to check
      the result isn't being carried by two atypical, low-signal
      questions.

Zero new API calls -- reuses already-computed C_LLM/C5_fix scores.

Run:
    python3 compute_ensemble_cv_and_sensitivity.py
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import cohen_kappa_score

BASE = Path(__file__).parent

W_GRID = np.round(np.arange(0.0, 1.01, 0.05), 2)


def qwk(human, pred):
    hi = np.round(human * 4).astype(int)
    pi = np.round(np.clip(pred, 0, 5) * 4).astype(int)
    return float(cohen_kappa_score(hi, pi, weights="quadratic"))


def load_combined():
    orig = json.loads((BASE / "data" / "mohler_real_eval_results.json").read_text())["results"]
    ext = json.loads((BASE / "data" / "mohler_real_extension_eval_results.json").read_text())["results"]
    return orig + ext


def run_loocv_ensemble(rows: list[dict], label: str) -> dict:
    human = np.array([r["human_score"] for r in rows])
    cllm = np.array([r["cllm_score"] for r in rows])
    c5 = np.array([r["c5_score"] for r in rows])
    qids = np.array([r["qid"] for r in rows])
    unique_qids = sorted(set(qids))
    n_q = len(unique_qids)

    by_q_idx = {q: np.where(qids == q)[0] for q in unique_qids}

    oof_pred = np.zeros_like(human)
    chosen_w = {}

    for held_q in unique_qids:
        held_idx = by_q_idx[held_q]
        train_mask = np.ones(len(rows), dtype=bool)
        train_mask[held_idx] = False

        best_w, best_mae = None, np.inf
        for w in W_GRID:
            blend = w * cllm[train_mask] + (1 - w) * c5[train_mask]
            blend_q = np.clip(np.round(blend * 4) / 4, 0, 5)
            mae = float(np.mean(np.abs(human[train_mask] - blend_q)))
            if mae < best_mae:
                best_mae, best_w = mae, w
        chosen_w[held_q] = float(best_w)

        held_blend = best_w * cllm[held_idx] + (1 - best_w) * c5[held_idx]
        oof_pred[held_idx] = np.clip(np.round(held_blend * 4) / 4, 0, 5)

    # Full suite on the aggregated out-of-fold predictions
    err_oof = np.abs(human - oof_pred)
    err_cllm = np.abs(human - cllm)
    err_c5 = np.abs(human - c5)

    def suite(pred, err):
        return {
            "mae": float(np.mean(err)),
            "pearson_r": float(np.corrcoef(human, pred)[0, 1]),
            "spearman_r": float(stats.spearmanr(human, pred)[0]),
            "qwk": qwk(human, pred),
            "rmse": float(np.sqrt(np.mean((human - pred) ** 2))),
        }

    oof_stats = suite(oof_pred, err_oof)
    cllm_stats = suite(cllm, err_cllm)
    c5_stats = suite(c5, err_c5)

    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)

    def paired(err_a, err_b):
        _, p_resp_two = stats.wilcoxon(err_a, err_b, alternative="two-sided", zero_method="wilcox")
        _, p_resp_one = stats.wilcoxon(err_a, err_b, alternative="less", zero_method="wilcox")
        qerr_a = np.array([np.mean(err_a[idx]) for idx in by_q.values()])
        qerr_b = np.array([np.mean(err_b[idx]) for idx in by_q.values()])
        _, p_clust_two = stats.wilcoxon(qerr_a, qerr_b, alternative="two-sided", zero_method="wilcox")
        _, p_clust_one = stats.wilcoxon(qerr_a, qerr_b, alternative="less", zero_method="wilcox")
        wins = int(sum(1 for x, y in zip(qerr_a, qerr_b) if x < y))
        return {
            "p_response_two_tailed": float(p_resp_two), "p_response_one_tailed": float(p_resp_one),
            "p_cluster_two_tailed": float(p_clust_two), "p_cluster_one_tailed": float(p_clust_one),
            "question_wins": wins, "question_total": len(by_q),
        }

    oof_vs_cllm = paired(err_oof, err_cllm)
    beats_both_corr = oof_stats["pearson_r"] > cllm_stats["pearson_r"] and \
                       oof_stats["spearman_r"] > cllm_stats["spearman_r"]
    beats_mae = oof_stats["mae"] < cllm_stats["mae"]
    clust_sig_both = oof_vs_cllm["p_cluster_one_tailed"] < 0.05 and oof_vs_cllm["p_cluster_two_tailed"] < 0.05

    print(f"\n=== {label} (n={len(rows)}, questions={n_q}) ===")
    print(f"  C_LLM         : MAE={cllm_stats['mae']:.4f}  r={cllm_stats['pearson_r']:.4f}  "
          f"rho={cllm_stats['spearman_r']:.4f}  QWK={cllm_stats['qwk']:.4f}")
    print(f"  C5_fix        : MAE={c5_stats['mae']:.4f}  r={c5_stats['pearson_r']:.4f}  "
          f"rho={c5_stats['spearman_r']:.4f}  QWK={c5_stats['qwk']:.4f}")
    print(f"  OOF-CV ensemble: MAE={oof_stats['mae']:.4f}  r={oof_stats['pearson_r']:.4f}  "
          f"rho={oof_stats['spearman_r']:.4f}  QWK={oof_stats['qwk']:.4f}")
    print(f"  chosen w_cllm per fold: min={min(chosen_w.values()):.2f} "
          f"max={max(chosen_w.values()):.2f} mean={np.mean(list(chosen_w.values())):.3f} "
          f"median={np.median(list(chosen_w.values())):.2f}")
    print(f"  OOF vs C_LLM: response p_two={oof_vs_cllm['p_response_two_tailed']:.4f} "
          f"p_one={oof_vs_cllm['p_response_one_tailed']:.4f}")
    print(f"                cluster  p_two={oof_vs_cllm['p_cluster_two_tailed']:.4f} "
          f"p_one={oof_vs_cllm['p_cluster_one_tailed']:.4f} "
          f"wins={oof_vs_cllm['question_wins']}/{oof_vs_cllm['question_total']}")
    print(f"  Beats C_LLM on: MAE={beats_mae}  both correlations={beats_both_corr}  "
          f"cluster significant both tails={clust_sig_both}")

    return {
        "label": label, "n": len(rows), "n_questions": n_q,
        "cllm": cllm_stats, "c5_fix": c5_stats, "oof_cv_ensemble": oof_stats,
        "chosen_w_per_fold": chosen_w,
        "oof_vs_cllm": oof_vs_cllm,
        "beats_cllm_on_mae": beats_mae,
        "beats_cllm_on_both_correlations": beats_both_corr,
        "cluster_significant_both_tails": clust_sig_both,
    }


def main() -> int:
    combined = load_combined()

    # (A) Full 50-question cross-validated ensemble
    result_full = run_loocv_ensemble(combined, "Full 50-question combined set, OOF-CV ensemble")

    # (B) Sensitivity: exclude the 2 out-of-domain extension questions
    ext_all = json.loads((BASE / "data" / "mohler_real_extension_eval_results.json").read_text())["results"]
    ext_by_qid = collections.defaultdict(list)
    for r in ext_all:
        ext_by_qid[r["qid"]].append(r)
    out_of_domain_qids = {q for q, rows in ext_by_qid.items()
                           if all(r.get("out_of_kg_domain") for r in rows)}
    print(f"\nExcluding out-of-domain extension questions: {sorted(out_of_domain_qids)}")

    filtered = [r for r in combined if r["qid"] not in out_of_domain_qids]
    result_sensitivity = run_loocv_ensemble(filtered, "48-question set (out-of-domain pair excluded), OOF-CV ensemble")

    out = {
        "full_50_questions": result_full,
        "sensitivity_48_questions_excl_out_of_domain": result_sensitivity,
        "excluded_qids": sorted(out_of_domain_qids),
    }
    out_path = BASE / "data" / "ensemble_cv_and_sensitivity.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
