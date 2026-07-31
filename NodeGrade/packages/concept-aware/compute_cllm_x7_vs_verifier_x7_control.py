#!/usr/bin/env python3
"""
compute_cllm_x7_vs_verifier_x7_control.py — the critical control experiment
flagged in a reviewer-perspective audit of Paper 1: does self-consistency
alone (no KG evidence, no Verifier -- just resampling the plain C_LLM
zero-shot prompt) already capture most of the gain attributed to Verifier
self-consistency? If C_LLM x7 matches Verifier x7, the paper's claimed
contribution (a Verifier/KG-evidence-informed architecture) collapses to
"self-consistency helps any LLM grader," undermining the architectural
claim.

ZERO new API calls for this first pass: the call-budget-matched experiment
(run_budget_matched_real_batched.py) already collected 7 independent C_LLM
attempts per response at temperature=0.7 on the original 46-question Mohler
set -- just aggregated with median. This re-aggregates with MEAN (the
design used for Verifier x7) for a fair, apples-to-apples comparison on
identical underlying data.

Run:
    python3 compute_cllm_x7_vs_verifier_x7_control.py
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
    bm = json.loads((BASE / "data" / "budget_matched_real_results.json").read_text())["per_sample"]
    vx7 = {r["id"]: r for r in
           json.loads((BASE / "data" / "verifier_selfconsistency_real_results.json").read_text())["per_sample"]}

    rows = []
    for r in bm:
        v = vx7.get(r["id"])
        if v is None:
            continue
        rows.append({
            "id": r["id"], "qid": r["qid"], "human_score": r["human_score"],
            "cllm_1call": r["cllm_1call"],
            "cllm_x7_mean": snap(statistics.mean(r["cllm_x7_attempts"])),
            "c5_fix_single": r["c5_fix"],
            "verifier_x7_mean": snap(statistics.mean(v["verifier_x7_attempts"])),
        })

    human = np.array([r["human_score"] for r in rows])
    cllm1 = np.array([r["cllm_1call"] for r in rows])
    cllm_x7 = np.array([r["cllm_x7_mean"] for r in rows])
    c5_single = np.array([r["c5_fix_single"] for r in rows])
    verif_x7 = np.array([r["verifier_x7_mean"] for r in rows])
    qids = [r["qid"] for r in rows]
    by_q = collections.defaultdict(list)
    for i, q in enumerate(qids):
        by_q[q].append(i)

    print(f"n = {len(rows)}, questions = {len(by_q)}")
    print()
    for label, pred in [("C_LLM (1 call)", cllm1), ("C_LLM x7 (mean)", cllm_x7),
                         ("C5_fix (single Verifier call)", c5_single),
                         ("Verifier x7 (mean)", verif_x7)]:
        st = suite(human, pred)
        print(f"  {label:32s} MAE={st['mae']:.4f}  r={st['pearson_r']:.4f}  "
              f"rho={st['spearman_r']:.4f}  QWK={st['qwk']:.4f}")

    err_cllm1 = np.abs(human - cllm1)
    err_cllmx7 = np.abs(human - cllm_x7)
    err_c5single = np.abs(human - c5_single)
    err_verifx7 = np.abs(human - verif_x7)

    print("\n=== THE CRITICAL COMPARISON: C_LLM x7 vs Verifier x7 (same design, same data) ===")
    head_to_head = paired(err_verifx7, err_cllmx7, by_q)
    mae_cllmx7 = float(np.mean(err_cllmx7))
    mae_verifx7 = float(np.mean(err_verifx7))
    print(f"  Verifier x7 MAE={mae_verifx7:.4f}  vs  C_LLM x7 MAE={mae_cllmx7:.4f}  "
          f"({(mae_cllmx7-mae_verifx7)/mae_cllmx7*100:+.2f}% change)")
    print(f"  response: p_two={head_to_head['p_response_two_tailed']:.4f} "
          f"p_one={head_to_head['p_response_one_tailed']:.4f}")
    print(f"  cluster : p_two={head_to_head['p_cluster_two_tailed']:.4f} "
          f"p_one={head_to_head['p_cluster_one_tailed']:.4f} "
          f"wins={head_to_head['question_wins']}/{head_to_head['question_total']}")
    print(f"  LOOCV   : one-tail sig={head_to_head['loocv_one_tailed_significant_folds']}/{head_to_head['question_total']}, "
          f"two-tail sig={head_to_head['loocv_two_tailed_significant_folds']}/{head_to_head['question_total']}")

    print("\n=== Context: does self-consistency alone (C_LLM x7) already beat C_LLM x1? ===")
    cllmx7_vs_cllm1 = paired(err_cllmx7, err_cllm1, by_q)
    print(f"  C_LLM x7 MAE={mae_cllmx7:.4f} vs C_LLM x1 MAE={float(np.mean(err_cllm1)):.4f} "
          f"({(float(np.mean(err_cllm1))-mae_cllmx7)/float(np.mean(err_cllm1))*100:+.2f}%)")
    print(f"  response p_one={cllmx7_vs_cllm1['p_response_one_tailed']:.4f}, "
          f"cluster p_two={cllmx7_vs_cllm1['p_cluster_two_tailed']:.4f}")

    print("\n=== Context: Verifier x7 vs C_LLM x1 (already reported in paper) ===")
    verifx7_vs_cllm1 = paired(err_verifx7, err_cllm1, by_q)
    print(f"  Verifier x7 MAE={mae_verifx7:.4f} vs C_LLM x1 MAE={float(np.mean(err_cllm1)):.4f} "
          f"({(float(np.mean(err_cllm1))-mae_verifx7)/float(np.mean(err_cllm1))*100:+.2f}%)")
    print(f"  response p_one={verifx7_vs_cllm1['p_response_one_tailed']:.4f}, "
          f"cluster p_two={verifx7_vs_cllm1['p_cluster_two_tailed']:.4f}")

    verdict = ("Verifier x7 beats C_LLM x7 -- the architecture adds value beyond plain self-consistency"
               if mae_verifx7 < mae_cllmx7 and head_to_head["p_response_two_tailed"] < 0.05
               else "Verifier x7 does NOT clearly beat C_LLM x7 -- self-consistency alone may explain most of the gain")
    print(f"\nVERDICT: {verdict}")

    out = {
        "n": len(rows), "n_questions": len(by_q),
        "cllm_1call": suite(human, cllm1), "cllm_x7_mean": suite(human, cllm_x7),
        "c5_fix_single": suite(human, c5_single), "verifier_x7_mean": suite(human, verif_x7),
        "verifier_x7_vs_cllm_x7_head_to_head": head_to_head,
        "cllm_x7_vs_cllm_1call": cllmx7_vs_cllm1,
        "verifier_x7_vs_cllm_1call": verifx7_vs_cllm1,
        "verdict": verdict,
    }
    out_path = BASE / "data" / "cllm_x7_vs_verifier_x7_control.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
