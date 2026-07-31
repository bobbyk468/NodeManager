#!/usr/bin/env python3
"""
compute_x7_mean_final_significance.py — formalizes MEAN aggregation (not
median) as the reference self-consistency design, with the full
significance suite (MAE, Pearson, Spearman, QWK, RMSE, response-level
and question-clustered Wilcoxon, LOOCV) on all three datasets, matching
the exact rigor already applied to the median version
(compute_verifier_x7_combined_significance.py). ZERO new API calls --
reuses the already-collected 7 attempts per sample, just aggregated
differently (mean instead of median).

This supersedes compute_verifier_x7_combined_significance.py as the
reference design, per compute_x7_aggregation_comparison.py's finding
that mean/trimmed-mean strictly dominates median on Mohler and
DigiKlausur (better correlation, comparable-or-better significance) and
is not worse on Kaggle ASAG (which remains null regardless of
aggregation, consistent with "no real signal to aggregate" there).

Run:
    python3 compute_x7_mean_final_significance.py
"""
from __future__ import annotations

import collections
import json
import statistics
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import cohen_kappa_score

BASE = Path(__file__).parent


def qwk(human, pred):
    hi = np.round(human * 4).astype(int)
    pi = np.round(np.clip(pred, 0, 5) * 4).astype(int)
    return float(cohen_kappa_score(hi, pi, weights="quadratic"))


def snap(x):
    return float(np.clip(round(x * 4) / 4, 0, 5))


def mean_agg(attempts):
    return snap(statistics.mean(attempts))


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
    diffs = qb - qa if False else (err_b - err_a)
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


def analyze(rows, attempts_key, single_key, cllm_key, human_key, qid_key, label):
    human = np.array([r[human_key] for r in rows])
    cllm = np.array([r[cllm_key] for r in rows])
    single = np.array([r[single_key] for r in rows])
    x7_mean = np.array([mean_agg(r[attempts_key]) for r in rows])
    qids = [r[qid_key] for r in rows]
    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)

    cllm_stats = suite(human, cllm)
    single_stats = suite(human, single)
    x7_stats = suite(human, x7_mean)

    print(f"\n=== {label} (n={len(rows)}, questions={len(by_q)}) ===")
    for name, st in [("C_LLM", cllm_stats), ("Single call", single_stats), ("x7-mean", x7_stats)]:
        print(f"  {name:12s} MAE={st['mae']:.4f}  r={st['pearson_r']:.4f}  rho={st['spearman_r']:.4f}  "
              f"QWK={st['qwk']:.4f}  RMSE={st['rmse']:.4f}")

    err_cllm = np.abs(human - cllm)
    err_single = np.abs(human - single)
    err_x7 = np.abs(human - x7_mean)

    x7_vs_cllm = paired(err_x7, err_cllm, by_q)
    x7_vs_single = paired(err_x7, err_single, by_q)

    print(f"  x7-mean vs C_LLM: MAE reduction {(cllm_stats['mae']-x7_stats['mae'])/cllm_stats['mae']*100:.2f}%, "
          f"d_z={x7_vs_cllm['d_z']:.4f}")
    print(f"    response: p_two={x7_vs_cllm['p_response_two_tailed']:.4f} p_one={x7_vs_cllm['p_response_one_tailed']:.4f}")
    print(f"    cluster : p_two={x7_vs_cllm['p_cluster_two_tailed']:.4f} p_one={x7_vs_cllm['p_cluster_one_tailed']:.4f} "
          f"wins={x7_vs_cllm['question_wins']}/{x7_vs_cllm['question_total']}")
    print(f"    LOOCV   : one-tail sig={x7_vs_cllm['loocv_one_tailed_significant_folds']}/{x7_vs_cllm['question_total']}, "
          f"two-tail sig={x7_vs_cllm['loocv_two_tailed_significant_folds']}/{x7_vs_cllm['question_total']}")
    print(f"  x7-mean vs single call: MAE reduction "
          f"{(single_stats['mae']-x7_stats['mae'])/single_stats['mae']*100:.2f}%, "
          f"response p_one={x7_vs_single['p_response_one_tailed']:.4f}")

    return {"cllm": cllm_stats, "single": single_stats, "x7_mean": x7_stats,
            "x7_mean_vs_cllm": x7_vs_cllm, "x7_mean_vs_single": x7_vs_single}


def main() -> int:
    orig = json.loads((BASE / "data" / "verifier_selfconsistency_real_results.json").read_text())["per_sample"]
    ext = json.loads((BASE / "data" / "verifier_selfconsistency_extension_results.json").read_text())["results"]
    mohler_combined = orig + ext
    mohler_result = analyze(mohler_combined, "verifier_x7_attempts", "c5_fix_single", "cllm_score",
                             "human_score", "qid", "Mohler combined (50q, 1371r)")

    dk = json.loads((BASE / "data" / "digiklausur_c5fix_selfconsistency_results.json").read_text())["per_sample"]
    dk_result = analyze(dk, "c5fix_x7_attempts", "c5_fix_single", "cllm_score",
                         "human_score", "qid", "DigiKlausur (17q, 646r)")

    ka = json.loads((BASE / "data" / "kaggle_c5fix_selfconsistency_results.json").read_text())["per_sample"]
    ka_result = analyze(ka, "c5fix_x7_attempts", "c5_fix_single", "cllm_score",
                         "human_score", "qid", "Kaggle ASAG deduped (150q, 368r)")

    out = {
        "note": "x7-mean (mean aggregation of 7 self-consistency attempts, temperature=0.7) "
                "supersedes x7-median as the reference design -- strictly better on Mohler "
                "and DigiKlausur, no worse on Kaggle ASAG (which remains null on this "
                "mechanism regardless of aggregation choice, consistent with no real "
                "KG signal to denoise there). Zero new API calls versus the median version "
                "-- same underlying data, different aggregation function.",
        "mohler_combined": mohler_result,
        "digiklausur": dk_result,
        "kaggle_asag_deduped": ka_result,
    }
    out_path = BASE / "data" / "x7_mean_final_significance.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
