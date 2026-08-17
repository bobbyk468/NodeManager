#!/usr/bin/env python3
"""
compute_frontier_baselines_significance.py -- Full statistical comparison
of the frontier-model zero-shot baselines (Claude, GPT, DeepSeek, run via
OpenRouter -- see run_frontier_baselines_batched.py) against both the
paper's existing Gemini C_LLM baseline and ConceptGrade's own C5_fix
pipeline, on the same real 1,262-sample Mohler set.

Matches the statistical rigor already used elsewhere in this paper:
response-level Wilcoxon (two-tailed + one-tailed), question-clustered
Wilcoxon (46 questions), paired Cohen's d_z, and bootstrap 95% CIs on
MAE (5,000 resamples, seed=42, same convention as
compute_main_results_ci.py). Zero new API calls -- reads only the
already-cached eval result files.

Run:
    python3 compute_frontier_baselines_significance.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, wilcoxon

BASE = Path(__file__).parent
N_RESAMPLES = 5000
SEED = 42


def load(path: str, score_key: str) -> dict:
    d = json.load(open(BASE / "data" / path))
    return {r["id"]: {"qid": r["qid"], "human": r["human_score"], "score": r[score_key]}
            for r in d["results"]}


def paired_stats(name: str, human: np.ndarray, ref: np.ndarray, cand: np.ndarray,
                  qids: list[str]) -> dict:
    """ref = the baseline being compared against (e.g. Gemini C_LLM or C5_fix);
    cand = the candidate model. Positive MAE reduction = cand is better."""
    err_ref = np.abs(human - ref)
    err_cand = np.abs(human - cand)

    mae_ref = float(err_ref.mean())
    mae_cand = float(err_cand.mean())
    mae_reduction_pct = float((mae_ref - mae_cand) / mae_ref * 100)

    diff = err_ref - err_cand  # positive = cand has lower error
    w_stat, p_two = wilcoxon(diff)
    p_one = p_two / 2 if diff.mean() > 0 else 1 - p_two / 2
    d_z = float(diff.mean() / diff.std(ddof=1))

    # Question-clustered: mean error per question, then paired Wilcoxon across questions
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

    # Bootstrap 95% CI on MAE reduction %
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

    return {
        "comparison": name,
        "mae_ref": mae_ref, "mae_cand": mae_cand,
        "mae_reduction_pct": mae_reduction_pct,
        "mae_reduction_ci95": [ci_lo, ci_hi],
        "pearson_r_cand": r_human_cand,
        "response_level": {"p_two_tailed": float(p_two), "p_one_tailed": float(p_one), "d_z": d_z, "n": n},
        "question_clustered": {"p_two_tailed": float(qp_two), "p_one_tailed": float(qp_one),
                                "n_questions": len(q_ids), "wins": q_wins},
    }


def main() -> int:
    gemini = load("mohler_real_eval_results.json", "cllm_score")
    c5fix_raw = json.load(open(BASE / "data" / "mohler_real_eval_results.json"))
    c5fix = {r["id"]: {"qid": r["qid"], "human": r["human_score"], "score": r["c5_score"]}
             for r in c5fix_raw["results"]}
    candidates = {
        "claude":   load("mohler_real_eval_results_claude.json", "claude_score"),
        "gpt":      load("mohler_real_eval_results_gpt.json", "gpt_score"),
        "deepseek": load("mohler_real_eval_results_deepseek.json", "deepseek_score"),
    }

    common = set(gemini) & set(c5fix)
    for c in candidates.values():
        common &= set(c)
    ids = sorted(common)
    print(f"n common samples: {len(ids)}")

    human = np.array([gemini[i]["human"] for i in ids])
    qids = [gemini[i]["qid"] for i in ids]
    gemini_scores = np.array([gemini[i]["score"] for i in ids])
    c5fix_scores = np.array([c5fix[i]["score"] for i in ids])

    all_results = {}
    for tag, data in candidates.items():
        cand_scores = np.array([data[i]["score"] for i in ids])

        vs_gemini = paired_stats(f"{tag}_vs_gemini_cllm", human, gemini_scores, cand_scores, qids)
        vs_c5fix = paired_stats(f"{tag}_vs_c5fix", human, c5fix_scores, cand_scores, qids)
        all_results[tag] = {"vs_gemini_cllm": vs_gemini, "vs_c5fix": vs_c5fix}

        print(f"\n=== {tag} ===")
        print(f"  vs Gemini C_LLM: MAE {vs_gemini['mae_ref']:.4f} -> {vs_gemini['mae_cand']:.4f} "
              f"({vs_gemini['mae_reduction_pct']:+.1f}%, CI {vs_gemini['mae_reduction_ci95']}), "
              f"response p={vs_gemini['response_level']['p_two_tailed']:.2e}, "
              f"cluster p={vs_gemini['question_clustered']['p_two_tailed']:.4f} "
              f"({vs_gemini['question_clustered']['wins']}/{vs_gemini['question_clustered']['n_questions']} questions)")
        print(f"  vs C5_fix:       MAE {vs_c5fix['mae_ref']:.4f} -> {vs_c5fix['mae_cand']:.4f} "
              f"({vs_c5fix['mae_reduction_pct']:+.1f}%, CI {vs_c5fix['mae_reduction_ci95']}), "
              f"response p={vs_c5fix['response_level']['p_two_tailed']:.2e}, "
              f"cluster p={vs_c5fix['question_clustered']['p_two_tailed']:.4f} "
              f"({vs_c5fix['question_clustered']['wins']}/{vs_c5fix['question_clustered']['n_questions']} questions)")

    out_path = BASE / "data" / "frontier_baselines_significance.json"
    out_path.write_text(json.dumps(all_results, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
