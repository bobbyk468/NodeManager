#!/usr/bin/env python3
"""
compute_pipeline_backbone_significance.py -- Option A pre-registered test:
does swapping ConceptGrade's backbone from Gemini to a frontier model
(GPT-5.6-terra) let the pipeline architecture beat that same model's own
zero-shot baseline? Compares run_frontier_pipeline_phaseB_batched.py's
output (full pipeline, GPT backbone) against run_frontier_baselines_batched.py's
output (GPT zero-shot), on the identical sample-ID subset only -- so the
"stronger backbone" is the only thing that differs between the two arms.

Pre-registered success criterion (set before running Phase B, per the
project's established discipline): the pipeline must beat GPT's own
zero-shot baseline at BOTH response-level AND question-clustered
Wilcoxon, p<0.05 two-tailed. Anything short of that is reported as a
negative/mixed result, not reframed post hoc.

Statistical method is identical to compute_frontier_baselines_significance.py's
paired_stats() (response-level + question-clustered Wilcoxon, paired
Cohen's d_z, bootstrap 95% CI on MAE reduction, 5,000 resamples, seed=42) --
reused verbatim, not reimplemented, to avoid any drift from the paper's
established convention.

Requires: data/{tag}_pipeline_eval_results.json (from
run_frontier_pipeline_phaseB_batched.py --model {tag}) and the existing
data/mohler_real_eval_results_{tag}.json zero-shot baseline. Zero new API
calls -- reads only cached files.

Run:
    python3 compute_pipeline_backbone_significance.py --model gpt
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, wilcoxon

BASE = Path(__file__).parent
N_RESAMPLES = 5000
SEED = 42


def paired_stats(name: str, human: np.ndarray, ref: np.ndarray, cand: np.ndarray,
                  qids: list[str]) -> dict:
    """ref = zero-shot baseline; cand = full pipeline (backbone-swapped).
    Positive MAE reduction = pipeline is better than the model's own zero-shot."""
    err_ref = np.abs(human - ref)
    err_cand = np.abs(human - cand)

    mae_ref = float(err_ref.mean())
    mae_cand = float(err_cand.mean())
    mae_reduction_pct = float((mae_ref - mae_cand) / mae_ref * 100)

    diff = err_ref - err_cand
    w_stat, p_two = wilcoxon(diff)
    p_one = p_two / 2 if diff.mean() > 0 else 1 - p_two / 2
    d_z = float(diff.mean() / diff.std(ddof=1))

    by_q_ref = defaultdict(list)
    by_q_cand = defaultdict(list)
    for q, er, ec in zip(qids, err_ref, err_cand):
        by_q_ref[q].append(er)
        by_q_cand[q].append(ec)
    q_ids = sorted(by_q_ref)
    q_err_ref = np.array([np.mean(by_q_ref[q]) for q in q_ids])
    q_err_cand = np.array([np.mean(by_q_cand[q]) for q in q_ids])
    q_diff = q_err_ref - q_err_cand
    qw_stat, qp_two = wilcoxon(q_diff)
    qp_one = qp_two / 2 if q_diff.mean() > 0 else 1 - qp_two / 2
    q_wins = int((q_diff > 0).sum())

    rng = np.random.default_rng(SEED)
    n = len(human)
    boot = np.empty(N_RESAMPLES)
    for i in range(N_RESAMPLES):
        idx = rng.integers(0, n, size=n)
        r = np.abs(human[idx] - ref[idx]).mean()
        c = np.abs(human[idx] - cand[idx]).mean()
        boot[i] = (r - c) / r * 100
    ci_lo, ci_hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))

    r_human_cand = float(pearsonr(human, cand)[0])
    r_human_ref = float(pearsonr(human, ref)[0])

    return {
        "comparison": name,
        "n": n,
        "mae_zeroshot": mae_ref, "mae_pipeline": mae_cand,
        "mae_reduction_pct": mae_reduction_pct,
        "mae_reduction_ci95": [ci_lo, ci_hi],
        "pearson_r_zeroshot": r_human_ref, "pearson_r_pipeline": r_human_cand,
        "response_level": {"p_two_tailed": float(p_two), "p_one_tailed": float(p_one), "d_z": d_z, "n": n},
        "question_clustered": {"p_two_tailed": float(qp_two), "p_one_tailed": float(qp_one),
                                "n_questions": len(q_ids), "wins": q_wins},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, choices=["claude", "gpt", "deepseek"])
    args = ap.parse_args()
    tag = args.model

    pipeline_path = BASE / "data" / f"{tag}_pipeline_eval_results.json"
    baseline_path = BASE / "data" / f"mohler_real_eval_results_{tag}.json"
    if not pipeline_path.exists():
        print(f"Missing {pipeline_path} -- run run_frontier_pipeline_phaseB_batched.py --model {tag} first.")
        return 1
    if not baseline_path.exists():
        print(f"Missing {baseline_path} -- run run_frontier_baselines_batched.py --model {tag} first.")
        return 1

    pipeline_raw = json.load(open(pipeline_path))
    pipeline = {r["id"]: {"qid": r["qid"], "human": r["human_score"], "score": r[f"{tag}_c5_score"]}
                for r in pipeline_raw["results"] if r[f"{tag}_c5_score"] is not None}
    baseline_raw = json.load(open(baseline_path))
    baseline = {r["id"]: {"qid": r["qid"], "human": r["human_score"], "score": r[f"{tag}_score"]}
                for r in baseline_raw["results"]}

    common = sorted(set(pipeline) & set(baseline))
    print(f"Pipeline rows: {len(pipeline)}  Baseline rows (full pool): {len(baseline)}  Common (subset): {len(common)}")
    if len(common) < len(pipeline):
        missing = set(pipeline) - set(baseline)
        print(f"  [warn] {len(missing)} pipeline sample IDs not found in the zero-shot baseline pool")

    human = np.array([pipeline[i]["human"] for i in common])
    qids = [pipeline[i]["qid"] for i in common]
    zeroshot_scores = np.array([baseline[i]["score"] for i in common])
    pipeline_scores = np.array([pipeline[i]["score"] for i in common])

    result = paired_stats(f"{tag}_pipeline_vs_{tag}_zeroshot", human, zeroshot_scores, pipeline_scores, qids)

    print(f"\n=== Option A: GPT-backbone pipeline vs GPT zero-shot (n={result['n']}) ===")
    print(f"  MAE {result['mae_zeroshot']:.4f} (zero-shot) -> {result['mae_pipeline']:.4f} (pipeline) "
          f"({result['mae_reduction_pct']:+.1f}%, CI {result['mae_reduction_ci95']})")
    print(f"  Pearson r: zero-shot={result['pearson_r_zeroshot']:.4f}  pipeline={result['pearson_r_pipeline']:.4f}")
    print(f"  Response-level:      p={result['response_level']['p_two_tailed']:.4g}  d_z={result['response_level']['d_z']:.4f}")
    print(f"  Question-clustered:  p={result['question_clustered']['p_two_tailed']:.4g}  "
          f"wins={result['question_clustered']['wins']}/{result['question_clustered']['n_questions']}")

    resp_sig = result["response_level"]["p_two_tailed"] < 0.05 and result["response_level"]["d_z"] > 0
    clus_sig = result["question_clustered"]["p_two_tailed"] < 0.05 and result["question_clustered"]["wins"] > result["question_clustered"]["n_questions"] / 2
    verdict = "PASS" if (resp_sig and clus_sig) else "FAIL"
    print(f"\n  Pre-registered criterion (beat zero-shot at BOTH response-level AND "
          f"question-clustered, p<0.05): {verdict}")

    out_path = BASE / "data" / f"{tag}_pipeline_backbone_significance.json"
    out_path.write_text(json.dumps({**result, "preregistered_verdict": verdict}, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
