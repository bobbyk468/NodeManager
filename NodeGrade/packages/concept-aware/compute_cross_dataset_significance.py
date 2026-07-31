#!/usr/bin/env python3
"""
compute_cross_dataset_significance.py

Reproduces the cross-dataset significance analysis reported in Paper 1
§4 (Cross-Dataset Generalization) using the *same* sensitivity machinery
applied to Mohler in `compute_clustered_significance.py`:

  * Response-level Wilcoxon (two-tailed + one-tailed)
  * Question-level (clustered) Wilcoxon
  * Leave-one-question-out (LOOCV) on the clustered test
  * Tie analysis on the non-tied sample subset
  * Paired Cohen's d_z and post-hoc power

Datasets, samples, and cluster structure (all real, all cached):
  - Mohler:        n =  120 samples,  10 questions ×  12 responses
  - DigiKlausur:   n =  646 samples,  17 questions ×  38 responses
  - Kaggle ASAG:   n =  368 samples (deduplicated from 473; see Fix #19),
                   150 questions × ~2.5 responses (variable)
  ------------------------------------------------------------------
  Total:           n = 1,134 samples, 177 questions

Also computes a fixed-effects pooled cross-dataset effect via meta-analysis
of paired Cohen's d_z (inverse-variance weighted).

Run:
    python compute_cross_dataset_significance.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy import stats
from scipy.stats import norm

BASE = Path(__file__).parent


# ---------------------------------------------------------------------------
# 1. Cluster-structure recovery
# ---------------------------------------------------------------------------
def load_dataset_with_clusters(name: str) -> dict:
    """
    Return:
        {
          'name': str,
          'human': np.ndarray,
          'cllm': np.ndarray,
          'c5': np.ndarray,
          'qid': list[str]     # one question_id per sample, length n
        }
    """
    # 2026-07-28 correction: data/mohler_eval_results.json was computed on
    # a fabricated 120-sample fixture (see REPRODUCIBILITY.md's "CRITICAL"
    # section). Mohler now loads from the real, KG-aligned re-evaluation
    # (data/mohler_real_eval_results.json, 46 questions, 1,262 responses,
    # each row already carrying its real qid -- no need to derive one from
    # a fixed 12-per-question index assumption, which was never true of
    # the real, variably-sized dataset).
    if name == "mohler":
        eval_path = BASE / "data" / "mohler_real_eval_results.json"
        with eval_path.open() as f:
            ev = json.load(f)
        results = ev["results"]
        qids = [r["qid"] for r in results]
        return {
            "name": name,
            "human": np.array([r["human_score"] for r in results], dtype=float),
            "cllm": np.array([r["cllm_score"] for r in results], dtype=float),
            "c5": np.array([r["c5_score"] for r in results], dtype=float),
            "qid": qids,
        }

    eval_path = BASE / "data" / f"{name}_eval_results.json"
    with eval_path.open() as f:
        ev = json.load(f)
    results = ev["results"]

    if name == "digiklausur":
        ds_path = BASE / "data" / "digiklausur_dataset.json"
        with ds_path.open() as f:
            ds = json.load(f)
        assert len(ds) == len(results), f"DigiKlausur length mismatch: {len(ds)} vs {len(results)}"
        qids = [str(s["question_id"]) for s in ds]
    elif name == "kaggle_asag":
        ds_path = BASE / "data" / "kaggle_asag_dataset.json"
        with ds_path.open() as f:
            ds = json.load(f)
        assert len(ds) == len(results), f"Kaggle length mismatch: {len(ds)} vs {len(results)}"

        # Framework Fix #19 (2026-06-15): the raw Kaggle ASAG source
        # contains 105 byte-identical duplicate (question, reference,
        # student_answer) records (473 -> 368 unique). Counting them
        # twice inflates the effective N and biases variance/significance
        # estimates in the cross-dataset pool. Filter both `ds` and
        # `results` to the deduplicated index set before proceeding.
        sys.path.insert(0, str(BASE))
        from datasets.dataset_dedupe import dedupe_records
        _, aligned_indices, dropped = dedupe_records(ds)
        print(f"[cross-dataset] Kaggle ASAG dedup: {len(ds)} -> {len(aligned_indices)} "
              f"unique ({dropped} duplicates removed)")
        ds = [ds[i] for i in aligned_indices]
        results = [results[i] for i in aligned_indices]

        # Derive question_id by deterministic ordering of unique question text
        q_to_id: dict[str, str] = {}
        qids = []
        for s in ds:
            q = s.get("question", "")
            if q not in q_to_id:
                q_to_id[q] = f"KA{len(q_to_id)+1:03d}"
            qids.append(q_to_id[q])
    else:
        raise ValueError(f"Unknown dataset: {name}")

    return {
        "name": name,
        "human": np.array([r["human_score"] for r in results], dtype=float),
        "cllm": np.array([r["cllm_score"] for r in results], dtype=float),
        "c5": np.array([r["c5_score"] for r in results], dtype=float),
        "qid": qids,
    }


# ---------------------------------------------------------------------------
# 2. Sensitivity machinery (mirrors compute_clustered_significance.py)
# ---------------------------------------------------------------------------
def analyse(ds: dict) -> dict:
    name = ds["name"]
    n = len(ds["human"])
    err_cllm = np.abs(ds["human"] - ds["cllm"])
    err_c5 = np.abs(ds["human"] - ds["c5"])
    diffs = err_c5 - err_cllm  # negative = C5 better

    # Response-level Wilcoxon (handle all-zero case)
    if np.all(diffs == 0):
        p_two = p_one = float("nan")
        w_plus = 0.0
    else:
        _, p_two = stats.wilcoxon(err_c5, err_cllm, alternative="two-sided",
                                  zero_method="wilcox")
        _, p_one = stats.wilcoxon(err_c5, err_cllm, alternative="less",
                                  zero_method="wilcox")
        nz = diffs[diffs != 0]
        ranks = stats.rankdata(np.abs(nz))
        w_plus = float(ranks[nz > 0].sum())

    n_ties = int(np.sum(diffs == 0))
    n_nontied = int(np.sum(diffs != 0))

    # MAE + effect size + power on all samples
    mae_cllm = float(err_cllm.mean())
    mae_c5 = float(err_c5.mean())
    mae_red = (mae_cllm - mae_c5) / mae_cllm * 100 if mae_cllm > 0 else 0.0
    if diffs.std(ddof=1) > 0:
        d_z = float(diffs.mean() / diffs.std(ddof=1))
    else:
        d_z = 0.0
    power = float(norm.cdf(abs(d_z) * np.sqrt(n) - norm.ppf(0.95)))

    # F2 — non-tied subset
    nontied_mask = diffs != 0
    nontied_mae_cllm = float(err_cllm[nontied_mask].mean()) if nontied_mask.any() else None
    nontied_mae_c5 = float(err_c5[nontied_mask].mean()) if nontied_mask.any() else None
    if nontied_mask.sum() > 1:
        nontied_d_z = float(diffs[nontied_mask].mean() / diffs[nontied_mask].std(ddof=1))
        _, nontied_p_two = stats.wilcoxon(err_c5[nontied_mask], err_cllm[nontied_mask],
                                          alternative="two-sided", zero_method="wilcox")
        _, nontied_p_one = stats.wilcoxon(err_c5[nontied_mask], err_cllm[nontied_mask],
                                          alternative="less", zero_method="wilcox")
    else:
        nontied_d_z = None
        nontied_p_two = nontied_p_one = float("nan")

    # Question-level clustering
    qid_to_idx: dict[str, list[int]] = defaultdict(list)
    for i, q in enumerate(ds["qid"]):
        qid_to_idx[q].append(i)
    q_err_cllm = np.array([err_cllm[idxs].mean() for idxs in qid_to_idx.values()])
    q_err_c5 = np.array([err_c5[idxs].mean() for idxs in qid_to_idx.values()])
    n_q = len(q_err_cllm)

    if np.all(q_err_c5 == q_err_cllm):
        pq_two = pq_one = float("nan")
    else:
        _, pq_two = stats.wilcoxon(q_err_c5, q_err_cllm, alternative="two-sided",
                                   zero_method="wilcox")
        _, pq_one = stats.wilcoxon(q_err_c5, q_err_cllm, alternative="less",
                                   zero_method="wilcox")

    # F3 — LOOCV across questions
    # (Kaggle has 150 questions; reporting min/max/n_sig is the useful summary.)
    loocv_two = []
    loocv_one = []
    for held_out in range(n_q):
        keep = [i for i in range(n_q) if i != held_out]
        a = q_err_c5[keep]
        b = q_err_cllm[keep]
        if np.all(a == b):
            loocv_two.append(1.0)
            loocv_one.append(1.0)
            continue
        try:
            _, p_kv_two = stats.wilcoxon(a, b, alternative="two-sided",
                                         zero_method="wilcox")
            _, p_kv_one = stats.wilcoxon(a, b, alternative="less",
                                         zero_method="wilcox")
            loocv_two.append(float(p_kv_two))
            loocv_one.append(float(p_kv_one))
        except ValueError:
            # Degenerate cases; skip
            loocv_two.append(1.0)
            loocv_one.append(1.0)

    return {
        "name": name,
        "n_total": n,
        "n_questions": n_q,
        "n_ties": n_ties,
        "n_nontied": n_nontied,
        "mae_cllm": round(mae_cllm, 4),
        "mae_c5": round(mae_c5, 4),
        "mae_reduction_pct": round(mae_red, 2),
        "W_plus": w_plus,
        "p_two_tailed": round(float(p_two), 4) if not np.isnan(p_two) else None,
        "p_one_tailed": round(float(p_one), 4) if not np.isnan(p_one) else None,
        "d_z": round(d_z, 3),
        "post_hoc_power": round(power, 3),
        "F2_nontied": {
            "n_nontied": int(nontied_mask.sum()),
            "n_ties": int(n - nontied_mask.sum()),
            "mae_cllm_nontied": round(nontied_mae_cllm, 4) if nontied_mae_cllm is not None else None,
            "mae_c5_nontied": round(nontied_mae_c5, 4) if nontied_mae_c5 is not None else None,
            "mae_reduction_pct_nontied": (
                round((nontied_mae_cllm - nontied_mae_c5) / nontied_mae_cllm * 100, 2)
                if nontied_mae_cllm else None
            ),
            "d_z_nontied": round(nontied_d_z, 3) if nontied_d_z is not None else None,
            "p_two_tailed_nontied": round(float(nontied_p_two), 4) if not np.isnan(nontied_p_two) else None,
            "p_one_tailed_nontied": round(float(nontied_p_one), 4) if not np.isnan(nontied_p_one) else None,
        },
        "F3_LOOCV_question_level": {
            "n_clusters": n_q,
            "p_two_tailed_clustered": round(float(pq_two), 4) if not np.isnan(pq_two) else None,
            "p_one_tailed_clustered": round(float(pq_one), 4) if not np.isnan(pq_one) else None,
            "loocv_p_two_min": round(min(loocv_two), 4) if loocv_two else None,
            "loocv_p_two_max": round(max(loocv_two), 4) if loocv_two else None,
            "loocv_p_one_min": round(min(loocv_one), 4) if loocv_one else None,
            "loocv_p_one_max": round(max(loocv_one), 4) if loocv_one else None,
            "n_loocv_two_sig_005": sum(1 for p in loocv_two if p < 0.05),
            "n_loocv_one_sig_005": sum(1 for p in loocv_one if p < 0.05),
        },
    }


# ---------------------------------------------------------------------------
# 3. Cross-dataset meta-analysis
# ---------------------------------------------------------------------------
def meta_analysis(per_ds: Sequence[dict]) -> dict:
    """
    Fixed-effects + DerSimonian-Laird random-effects meta-analysis on
    paired Cohen's d_z. Approximate variance of d_z: var ~ 1/n + d_z^2 / (2n).
    """
    ds_list = list(per_ds)
    d_list = np.array([d["d_z"] for d in ds_list], dtype=float)
    n_list = np.array([d["n_total"] for d in ds_list], dtype=float)
    var_list = 1.0 / n_list + (d_list ** 2) / (2 * n_list)
    w = 1.0 / var_list

    # Fixed effects
    d_fe = float((w * d_list).sum() / w.sum())
    se_fe = float(np.sqrt(1.0 / w.sum()))
    z_fe = d_fe / se_fe
    p_fe_two = float(2 * (1 - norm.cdf(abs(z_fe))))
    p_fe_one = float(1 - norm.cdf(-z_fe))  # one-tailed: C5 better (d_z < 0)
    ci_fe_lo = d_fe - 1.96 * se_fe
    ci_fe_hi = d_fe + 1.96 * se_fe

    # DerSimonian-Laird random effects
    q_stat = float((w * (d_list - d_fe) ** 2).sum())
    df = len(d_list) - 1
    c = float(w.sum() - (w ** 2).sum() / w.sum())
    tau2 = max(0.0, (q_stat - df) / c) if c > 0 else 0.0
    w_re = 1.0 / (var_list + tau2)
    d_re = float((w_re * d_list).sum() / w_re.sum())
    se_re = float(np.sqrt(1.0 / w_re.sum()))
    z_re = d_re / se_re
    p_re_two = float(2 * (1 - norm.cdf(abs(z_re))))
    p_re_one = float(1 - norm.cdf(-z_re))
    ci_re_lo = d_re - 1.96 * se_re
    ci_re_hi = d_re + 1.96 * se_re

    i2 = max(0.0, (q_stat - df) / q_stat) * 100 if q_stat > 0 else 0.0

    return {
        "per_dataset_d_z": d_list.tolist(),
        "per_dataset_n": n_list.tolist(),
        "fixed_effects": {
            "d_z": round(d_fe, 4),
            "se": round(se_fe, 4),
            "ci_95": [round(ci_fe_lo, 4), round(ci_fe_hi, 4)],
            "z": round(z_fe, 3),
            "p_two_tailed": round(p_fe_two, 6),
            "p_one_tailed_C5_better": round(p_fe_one, 6),
        },
        "random_effects_DL": {
            "d_z": round(d_re, 4),
            "se": round(se_re, 4),
            "ci_95": [round(ci_re_lo, 4), round(ci_re_hi, 4)],
            "tau2": round(tau2, 4),
            "I2_percent": round(i2, 1),
            "z": round(z_re, 3),
            "p_two_tailed": round(p_re_two, 6),
            "p_one_tailed_C5_better": round(p_re_one, 6),
        },
        "Q_statistic": round(q_stat, 3),
        "df": df,
    }


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
def main() -> int:
    datasets = ["mohler", "digiklausur", "kaggle_asag"]
    out = {"per_dataset": [], "totals": {}, "meta_analysis": {}}

    print("=" * 72)
    print("CROSS-DATASET SENSITIVITY (Mohler + DigiKlausur + Kaggle ASAG)")
    print("=" * 72)

    for name in datasets:
        ds = load_dataset_with_clusters(name)
        result = analyse(ds)
        out["per_dataset"].append(result)
        print(f"\n--- {name.upper()} ---")
        print(f"  n_total          : {result['n_total']}")
        print(f"  n_questions      : {result['n_questions']} clusters")
        print(f"  n_ties / n_nontied: {result['n_ties']} / {result['n_nontied']}")
        print(f"  MAE C_LLM → C5    : {result['mae_cllm']} → {result['mae_c5']} "
              f"({result['mae_reduction_pct']}% reduction)")
        print(f"  Cohen's d_z       : {result['d_z']}  (post-hoc power = {result['post_hoc_power']})")
        print(f"  Wilcoxon two-tail : p = {result['p_two_tailed']}")
        print(f"  Wilcoxon one-tail : p = {result['p_one_tailed']}")
        f2 = result["F2_nontied"]
        if f2["mae_reduction_pct_nontied"] is not None:
            print(f"  [F2 non-tied]     : MAE red = {f2['mae_reduction_pct_nontied']}%, "
                  f"d_z = {f2['d_z_nontied']}, p = {f2['p_two_tailed_nontied']} two / "
                  f"{f2['p_one_tailed_nontied']} one")
        f3 = result["F3_LOOCV_question_level"]
        print(f"  [F3 LOOCV]        : clustered p = {f3['p_two_tailed_clustered']} two / "
              f"{f3['p_one_tailed_clustered']} one")
        print(f"                       LOOCV one-tail range "
              f"[{f3['loocv_p_one_min']}, {f3['loocv_p_one_max']}], "
              f"{f3['n_loocv_one_sig_005']}/{f3['n_clusters']} folds sig.")

    # Pooled totals
    total_n = sum(d["n_total"] for d in out["per_dataset"])
    total_q = sum(d["n_questions"] for d in out["per_dataset"])
    total_ties = sum(d["n_ties"] for d in out["per_dataset"])
    total_nontied = sum(d["n_nontied"] for d in out["per_dataset"])
    out["totals"] = {
        "total_n": total_n,
        "total_questions": total_q,
        "total_ties": total_ties,
        "total_nontied": total_nontied,
    }

    # Cross-dataset meta-analysis
    out["meta_analysis"] = meta_analysis(out["per_dataset"])
    print("\n" + "=" * 72)
    print("CROSS-DATASET META-ANALYSIS (paired d_z, inverse-variance weighted)")
    print("=" * 72)
    print(f"  Total samples       : n = {total_n} across {total_q} questions, "
          f"3 datasets")
    fe = out["meta_analysis"]["fixed_effects"]
    re = out["meta_analysis"]["random_effects_DL"]
    print(f"\n  Fixed-effects pool  : d_z = {fe['d_z']}  "
          f"95% CI [{fe['ci_95'][0]}, {fe['ci_95'][1]}]")
    print(f"                       : z = {fe['z']}, "
          f"p (two-tail) = {fe['p_two_tailed']}, "
          f"p (one-tail, C5 better) = {fe['p_one_tailed_C5_better']}")
    print(f"\n  Random-effects (DL) : d_z = {re['d_z']}  "
          f"95% CI [{re['ci_95'][0]}, {re['ci_95'][1]}]")
    print(f"                       : tau^2 = {re['tau2']}, "
          f"I^2 = {re['I2_percent']}%, Q = {out['meta_analysis']['Q_statistic']}")
    print(f"                       : z = {re['z']}, "
          f"p (two-tail) = {re['p_two_tailed']}, "
          f"p (one-tail, C5 better) = {re['p_one_tailed_C5_better']}")

    out_path = BASE / "data" / "cross_dataset_significance.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
