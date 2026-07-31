#!/usr/bin/env python3
"""
compute_verifier_weight_cv.py — cross-validates the DEPLOYED
verifier_weight=1.0 default, zero new API calls.

Every prior verifier_weight sweep this session
(compute_verifier_weight_sweep.py, _v2.py) picked w=1.0 as best by
sweeping the full [0,1] grid and reading off the minimum-MAE point on
the SAME real Mohler data being reported -- exactly the same
in-sample-selection risk that got the C_LLM/C5_fix ensemble idea
retracted after cross-validation. This script closes that gap for the
verifier_weight parameter specifically: genuine leave-one-question-out
CV, selecting w on the other 45 questions only, applied to the held-out
question, aggregated out-of-fold.

final_score(w) = (1-w) * kg_score + w * c5_fix   [c5_fix IS the
                 verified score, since the deployed pipeline already
                 runs at w=1.0 -- see REPRODUCIBILITY.md]

Run:
    python3 compute_verifier_weight_cv.py
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


def main() -> int:
    rows = json.loads((BASE / "data" / "ablation_three_condition_real.json").read_text())["per_sample"]

    human = np.array([r["human_score"] for r in rows])
    cllm = np.array([r["cllm_score"] for r in rows])
    kg = np.array([r["kg_score"] for r in rows])
    c5 = np.array([r["c5_fix"] for r in rows])
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
            blend = (1 - w) * kg[train_mask] + w * c5[train_mask]
            blend_q = np.clip(np.round(blend * 4) / 4, 0, 5)
            mae = float(np.mean(np.abs(human[train_mask] - blend_q)))
            if mae < best_mae:
                best_mae, best_w = mae, w
        chosen_w[held_q] = float(best_w)

        held_blend = (1 - best_w) * kg[held_idx] + best_w * c5[held_idx]
        oof_pred[held_idx] = np.clip(np.round(held_blend * 4) / 4, 0, 5)

    err_oof = np.abs(human - oof_pred)
    err_cllm = np.abs(human - cllm)
    err_c5 = np.abs(human - c5)

    def suite(pred, err):
        return {
            "mae": float(np.mean(err)), "pearson_r": float(np.corrcoef(human, pred)[0, 1]),
            "spearman_r": float(stats.spearmanr(human, pred)[0]), "qwk": qwk(human, pred),
        }

    oof_stats = suite(oof_pred, err_oof)
    cllm_stats = suite(cllm, err_cllm)
    c5_stats = suite(c5, err_c5)

    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)

    def paired(err_a, err_b):
        _, p_rt = stats.wilcoxon(err_a, err_b, alternative="two-sided", zero_method="wilcox")
        _, p_ro = stats.wilcoxon(err_a, err_b, alternative="less", zero_method="wilcox")
        qa = np.array([np.mean(err_a[idx]) for idx in by_q.values()])
        qb = np.array([np.mean(err_b[idx]) for idx in by_q.values()])
        _, p_ct = stats.wilcoxon(qa, qb, alternative="two-sided", zero_method="wilcox")
        _, p_co = stats.wilcoxon(qa, qb, alternative="less", zero_method="wilcox")
        wins = int(sum(1 for x, y in zip(qa, qb) if x < y))
        return {"p_resp_two": float(p_rt), "p_resp_one": float(p_ro),
                "p_clust_two": float(p_ct), "p_clust_one": float(p_co),
                "wins": wins, "n_q": len(by_q)}

    oof_vs_cllm = paired(err_oof, err_cllm)
    c5_vs_cllm = paired(err_c5, err_cllm)

    print(f"n={len(rows)}, questions={n_q}")
    print(f"\nC_LLM         : MAE={cllm_stats['mae']:.4f} r={cllm_stats['pearson_r']:.4f} "
          f"rho={cllm_stats['spearman_r']:.4f} QWK={cllm_stats['qwk']:.4f}")
    print(f"C5_fix (w=1.0, deployed, in-sample): MAE={c5_stats['mae']:.4f} r={c5_stats['pearson_r']:.4f} "
          f"rho={c5_stats['spearman_r']:.4f} QWK={c5_stats['qwk']:.4f}")
    print(f"  vs C_LLM: cluster p_two={c5_vs_cllm['p_clust_two']:.4f} p_one={c5_vs_cllm['p_clust_one']:.4f} "
          f"wins={c5_vs_cllm['wins']}/{c5_vs_cllm['n_q']}")
    print(f"\nOOF-CV verifier_weight: MAE={oof_stats['mae']:.4f} r={oof_stats['pearson_r']:.4f} "
          f"rho={oof_stats['spearman_r']:.4f} QWK={oof_stats['qwk']:.4f}")
    print(f"  chosen w per fold: min={min(chosen_w.values()):.2f} max={max(chosen_w.values()):.2f} "
          f"mean={np.mean(list(chosen_w.values())):.3f} median={np.median(list(chosen_w.values())):.2f}")
    print(f"  folds choosing w=1.0 (matches deployed default): "
          f"{sum(1 for v in chosen_w.values() if v == 1.0)}/{n_q}")
    print(f"  vs C_LLM: cluster p_two={oof_vs_cllm['p_clust_two']:.4f} p_one={oof_vs_cllm['p_clust_one']:.4f} "
          f"wins={oof_vs_cllm['wins']}/{oof_vs_cllm['n_q']}")

    verdict = ("CV CONFIRMS the deployed w=1.0 default (CV picks w=1.0 on essentially every fold)"
               if sum(1 for v in chosen_w.values() if v == 1.0) >= n_q * 0.8
               else "CV does NOT confirm the deployed w=1.0 default -- folds disagree with it")
    print(f"\nVerdict: {verdict}")

    out = {
        "n": len(rows), "n_questions": n_q,
        "cllm": cllm_stats, "c5_fix_deployed_insample": c5_stats,
        "oof_cv": oof_stats, "chosen_w_per_fold": chosen_w,
        "oof_vs_cllm": oof_vs_cllm, "c5_vs_cllm_insample": c5_vs_cllm,
        "verdict": verdict,
    }
    out_path = BASE / "data" / "verifier_weight_cv.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
