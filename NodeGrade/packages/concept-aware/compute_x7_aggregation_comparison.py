#!/usr/bin/env python3
"""
compute_x7_aggregation_comparison.py — tests whether a different
aggregation of the already-collected 7 self-consistency attempts (mean,
trimmed mean, mode) does better than median, on all three datasets.
ZERO new API calls -- every attempt is already cached per-sample in the
verifier/c5fix self-consistency result files.

Also checks: does the number of rounds actually used (K=3, K=5 vs K=7)
matter, using SUBSETS of the already-collected 7 attempts? This tells us
whether fewer (cheaper) rounds would have gotten most of the benefit.

Run:
    python3 compute_x7_aggregation_comparison.py
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


def aggregate(attempts, method, k=None):
    a = attempts[:k] if k else attempts
    if method == "median":
        return snap(statistics.median(a))
    if method == "mean":
        return snap(statistics.mean(a))
    if method == "trimmed_mean":
        s = sorted(a)
        if len(s) >= 5:
            s = s[1:-1]  # drop min and max
        return snap(statistics.mean(s))
    if method == "mode":
        try:
            return snap(statistics.mode(a))
        except statistics.StatisticsError:
            return snap(statistics.median(a))
    raise ValueError(method)


def analyze(rows, attempts_key, single_key, cllm_key, human_key, qid_key, label):
    human = np.array([r[human_key] for r in rows])
    cllm = np.array([r[cllm_key] for r in rows])
    single = np.array([r[single_key] for r in rows])
    qids = [r[qid_key] for r in rows]
    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)

    err_cllm = np.abs(human - cllm)

    print(f"\n=== {label} (n={len(rows)}, questions={len(by_q)}) ===")
    print(f"  C_LLM        MAE={np.mean(err_cllm):.4f}  r={np.corrcoef(human,cllm)[0,1]:.4f}  "
          f"rho={stats.spearmanr(human,cllm)[0]:.4f}")
    print(f"  Single call  MAE={np.mean(np.abs(human-single)):.4f}  r={np.corrcoef(human,single)[0,1]:.4f}  "
          f"rho={stats.spearmanr(human,single)[0]:.4f}")

    results = {}
    for method in ["median", "mean", "trimmed_mean", "mode"]:
        pred = np.array([aggregate(r[attempts_key], method) for r in rows])
        err = np.abs(human - pred)
        mae = float(np.mean(err))
        r_p = float(np.corrcoef(human, pred)[0, 1])
        r_s = float(stats.spearmanr(human, pred)[0])
        q = qwk(human, pred)
        qerr = np.array([np.mean(err[idx]) for idx in by_q.values()])
        qerr_c = np.array([np.mean(err_cllm[idx]) for idx in by_q.values()])
        _, pc2 = stats.wilcoxon(qerr, qerr_c, alternative="two-sided", zero_method="wilcox")
        _, pc1 = stats.wilcoxon(qerr, qerr_c, alternative="less", zero_method="wilcox")
        wins = int(sum(1 for a, b in zip(qerr, qerr_c) if a < b))
        results[method] = {"mae": mae, "pearson_r": r_p, "spearman_r": r_s, "qwk": q,
                            "cluster_p_two": float(pc2), "cluster_p_one": float(pc1),
                            "wins": wins, "n_q": len(by_q)}
        print(f"  x7-{method:13s} MAE={mae:.4f}  r={r_p:.4f}  rho={r_s:.4f}  QWK={q:.4f}  "
              f"clust_p2={pc2:.4f}  wins={wins}/{len(by_q)}")

    # K-subset check: does K=3 or K=5 get most of the benefit?
    print(f"  --- K-subset check (median aggregation) ---")
    for k in [3, 5, 7]:
        pred = np.array([aggregate(r[attempts_key], "median", k=k) for r in rows])
        err = np.abs(human - pred)
        mae = float(np.mean(err))
        r_p = float(np.corrcoef(human, pred)[0, 1])
        qerr = np.array([np.mean(err[idx]) for idx in by_q.values()])
        qerr_c = np.array([np.mean(err_cllm[idx]) for idx in by_q.values()])
        _, pc2 = stats.wilcoxon(qerr, qerr_c, alternative="two-sided", zero_method="wilcox")
        print(f"    K={k}: MAE={mae:.4f}  r={r_p:.4f}  clust_p2={pc2:.4f}")

    return results


def main() -> int:
    orig = json.loads((BASE / "data" / "verifier_selfconsistency_real_results.json").read_text())["per_sample"]
    ext = json.loads((BASE / "data" / "verifier_selfconsistency_extension_results.json").read_text())["results"]
    mohler_combined = orig + ext
    for r in mohler_combined:
        if "c5_fix_single" not in r:
            r["c5_fix_single"] = r.get("c5_fix_single")

    mohler_results = analyze(mohler_combined, "verifier_x7_attempts", "c5_fix_single", "cllm_score",
                              "human_score", "qid", "Mohler combined (50q)")

    dk = json.loads((BASE / "data" / "digiklausur_c5fix_selfconsistency_results.json").read_text())["per_sample"]
    dk_results = analyze(dk, "c5fix_x7_attempts", "c5_fix_single", "cllm_score",
                          "human_score", "qid", "DigiKlausur")

    ka = json.loads((BASE / "data" / "kaggle_c5fix_selfconsistency_results.json").read_text())["per_sample"]
    ka_results = analyze(ka, "c5fix_x7_attempts", "c5_fix_single", "cllm_score",
                          "human_score", "qid", "Kaggle ASAG (deduped)")

    out = {"mohler": mohler_results, "digiklausur": dk_results, "kaggle_asag": ka_results}
    out_path = BASE / "data" / "x7_aggregation_comparison.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
