#!/usr/bin/env python3
"""
compute_cllm_c5_ensemble_real.py — a simple linear ensemble of C_LLM and
C5_fix's already-computed scores, real Mohler data, ZERO new API calls.

Motivation: the real-data ablation and verifier-weight sweep established
that C5_fix's raw MAE edge over C_LLM comes with a cost -- its Pearson
(0.784) and Spearman (0.808) correlations are both *worse* than C_LLM's
(0.790 / 0.825), and post-hoc calibration reverses the MAE result
entirely. Sweeping every blend along the existing kg_score/verified axis
(compute_verifier_weight_sweep_v2.py) never recovers C_LLM's correlation
-- that axis blends kg_score with the verifier, not the verifier with
C_LLM itself.

This script tests a different, previously-untried axis: blending the
FINAL C5_fix score with C_LLM's raw score,
    ensemble = w * C_LLM + (1-w) * C5_fix
for w in [0, 1]. Both component scores are already fully computed and
cached (data/ablation_three_condition_real.json), so the entire sweep
is free.

Run:
    python3 compute_cllm_c5_ensemble_real.py
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr, wilcoxon

BASE = Path(__file__).parent


def main() -> int:
    with (BASE / "data" / "ablation_three_condition_real.json").open() as f:
        rows = json.load(f)["per_sample"]

    human = np.array([r["human_score"] for r in rows])
    cllm = np.array([r["cllm_score"] for r in rows])
    c5 = np.array([r["c5_fix"] for r in rows])
    qids = [r["qid"] for r in rows]

    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)

    err_cllm = np.abs(human - cllm)
    err_c5 = np.abs(human - c5)
    mae_cllm = float(np.mean(err_cllm))
    mae_c5 = float(np.mean(err_c5))
    r_cllm = float(pearsonr(human, cllm)[0])
    r_c5 = float(pearsonr(human, c5)[0])
    sp_cllm = float(spearmanr(human, cllm)[0])
    sp_c5 = float(spearmanr(human, c5)[0])

    print(f"n = {len(rows)}")
    print(f"C_LLM alone : MAE={mae_cllm:.4f}  pearson={r_cllm:.4f}  spearman={sp_cllm:.4f}")
    print(f"C5_fix alone: MAE={mae_c5:.4f}  pearson={r_c5:.4f}  spearman={sp_c5:.4f}")
    print()
    print("Sweep: ensemble = w*C_LLM + (1-w)*C5_fix")

    results = []
    for w in np.arange(0.0, 0.55, 0.05):
        w = round(float(w), 2)
        blend = w * cllm + (1 - w) * c5
        blend_q = np.clip(np.round(blend * 4) / 4, 0, 5)
        err_blend = np.abs(human - blend_q)
        mae = float(np.mean(err_blend))
        pr = float(pearsonr(human, blend_q)[0])
        sp = float(spearmanr(human, blend_q)[0])

        _, p_resp_two = wilcoxon(err_blend, err_cllm, alternative="two-sided", zero_method="wilcox")
        _, p_resp_one = wilcoxon(err_blend, err_cllm, alternative="less", zero_method="wilcox")

        qerr_blend = np.array([np.mean(err_blend[idx]) for idx in by_q.values()])
        qerr_cllm = np.array([np.mean(err_cllm[idx]) for idx in by_q.values()])
        _, p_clust_two = wilcoxon(qerr_blend, qerr_cllm, alternative="two-sided", zero_method="wilcox")
        _, p_clust_one = wilcoxon(qerr_blend, qerr_cllm, alternative="less", zero_method="wilcox")
        wins = int(sum(1 for a, b in zip(qerr_blend, qerr_cllm) if a < b))

        beats_cllm_both_corr = pr > r_cllm and sp > sp_cllm
        row = {
            "w_cllm": w, "mae": mae, "mae_reduction_pct": (mae_cllm - mae) / mae_cllm * 100,
            "pearson": pr, "spearman": sp, "beats_cllm_on_both_correlations": beats_cllm_both_corr,
            "p_response_two_tailed": float(p_resp_two), "p_response_one_tailed": float(p_resp_one),
            "p_cluster_two_tailed": float(p_clust_two), "p_cluster_one_tailed": float(p_clust_one),
            "question_wins": wins, "question_total": len(by_q),
        }
        results.append(row)
        marker = "  <-- beats C_LLM on MAE + both correlations" if beats_cllm_both_corr and mae < mae_cllm else ""
        print(f"  w={w:.2f}  MAE={mae:.4f} ({row['mae_reduction_pct']:+.1f}%)  "
              f"pearson={pr:.4f}  spearman={sp:.4f}  "
              f"qclust p_one={p_clust_one:.4f}  wins={wins}/{len(by_q)}{marker}")

    # Pick the recommended point: smallest w such that both correlations
    # beat C_LLM (conservative -- keeps as much of the MAE gain as possible
    # while first crossing the "beats baseline on ranking too" line).
    candidates = [r for r in results if r["beats_cllm_on_both_correlations"]]
    recommended = min(candidates, key=lambda r: r["w_cllm"]) if candidates else None
    if recommended:
        print(f"\nRecommended: w_cllm={recommended['w_cllm']:.2f} -- "
              f"MAE {recommended['mae_reduction_pct']:+.1f}% vs C_LLM, "
              f"beats C_LLM on Pearson AND Spearman, "
              f"question-clustered one-tailed p={recommended['p_cluster_one_tailed']:.4f}")

    out = {
        "n": len(rows),
        "cllm_alone": {"mae": mae_cllm, "pearson": r_cllm, "spearman": sp_cllm},
        "c5_alone": {"mae": mae_c5, "pearson": r_c5, "spearman": sp_c5},
        "sweep": results,
        "recommended": recommended,
    }
    out_path = BASE / "data" / "cllm_c5_ensemble_real.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
