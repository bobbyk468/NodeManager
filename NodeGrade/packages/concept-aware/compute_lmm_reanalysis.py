#!/usr/bin/env python3
"""
compute_lmm_reanalysis.py — re-tests the headline and fair-control
comparisons using a linear mixed-effects model (random intercept per
question) instead of the paired cluster-mean Wilcoxon test used
throughout this session. ZERO new API calls: reuses every prediction
already cached this session.

Motivation: the cluster-mean Wilcoxon approach collapses each question
to a single mean-error data point before testing, discarding
within-question sample size and variance information -- a real power
loss, especially at 17-50 question clusters. An LMM instead uses every
response-level data point while still modelling the non-independence of
responses within a question via a random intercept, which is the
standard, more appropriate way to handle this kind of nested data.

Model: abs_error ~ system + (1 | question_id)
  - Fixed effect: system (baseline vs. ConceptGrade/self-consistency variant)
  - Random intercept: question_id (captures per-question difficulty/bias)
  - Significance: both a likelihood-ratio test (full vs. system-free model,
    generally more robust for small numbers of clusters) and the model's
    own Wald z-test on the system coefficient are reported.

Honest caveat, stated once here rather than repeated per-result: with
only 17-50 clusters (questions), even the LRT's chi-squared reference
distribution is an asymptotic approximation and can be anti-conservative
at this cluster count; this is a genuine improvement in power over the
cluster-mean approach, not a perfect small-sample solution.

Run:
    python3 compute_lmm_reanalysis.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

BASE = Path(__file__).parent


def fit_lmm(df: pd.DataFrame, label: str) -> dict:
    """df must have columns: qid, system (categorical, 2 levels), abs_error."""
    df = df.copy()
    df["qid"] = df["qid"].astype(str)
    levels = sorted(df["system"].unique())
    assert len(levels) == 2, f"expected 2 systems, got {levels}"

    full = smf.mixedlm("abs_error ~ system", df, groups=df["qid"]).fit(reml=False)
    reduced = smf.mixedlm("abs_error ~ 1", df, groups=df["qid"]).fit(reml=False)

    lrt_stat = 2 * (full.llf - reduced.llf)
    from scipy.stats import chi2
    lrt_p = float(chi2.sf(lrt_stat, df=1))

    # Wald p-value on the system coefficient (non-intercept term)
    coef_name = [c for c in full.params.index if c.startswith("system[")][0]
    wald_p = float(full.pvalues[coef_name])
    coef = float(full.params[coef_name])

    n_q = df["qid"].nunique()
    n = len(df)
    print(f"\n=== {label} ===")
    print(f"  n={n}, questions={n_q}, levels={levels}")
    print(f"  fixed effect ({coef_name}): coef={coef:.4f}")
    print(f"  LRT (full vs.\\ no-system): chi2={lrt_stat:.3f}, p={lrt_p:.4f}")
    print(f"  Wald z-test on system coefficient: p={wald_p:.4f}")
    print(f"  Converged: full={full.converged}, reduced={reduced.converged}")

    return {
        "label": label, "n": n, "n_questions": n_q, "levels": levels,
        "coefficient": coef, "lrt_chi2": float(lrt_stat), "lrt_p": lrt_p, "wald_p": wald_p,
        "converged_full": bool(full.converged), "converged_reduced": bool(reduced.converged),
    }


def long_df(human, sys_a, sys_b, qids, name_a, name_b) -> pd.DataFrame:
    rows = []
    for h, a, b, q in zip(human, sys_a, sys_b, qids):
        rows.append({"qid": q, "system": name_a, "abs_error": abs(h - a)})
        rows.append({"qid": q, "system": name_b, "abs_error": abs(h - b)})
    return pd.DataFrame(rows)


def main() -> int:
    results = []

    # 1. Mohler 46q headline: C_LLM(x1) vs C5_fix(single)
    d = json.loads((BASE / "data" / "mohler_real_eval_results.json").read_text())["results"]
    human = [r["human_score"] for r in d]
    cllm = [r["cllm_score"] for r in d]
    c5 = [r["c5_score"] for r in d]
    qids = [r["qid"] for r in d]
    df1 = long_df(human, cllm, c5, qids, "C_LLM", "C5_fix")
    results.append(fit_lmm(df1, "Mohler 46q headline: C_LLM(x1) vs C5_fix(single)"))

    # 2. Mohler 46q fair control: C_LLM x7(mean) vs Verifier x7(mean)
    bm = json.loads((BASE / "data" / "budget_matched_real_results.json").read_text())["per_sample"]
    vx7 = {r["id"]: r for r in
           json.loads((BASE / "data" / "verifier_selfconsistency_real_results.json").read_text())["per_sample"]}
    human2, cllmk7, verifk7, qids2 = [], [], [], []
    for r in bm:
        v = vx7.get(r["id"])
        if v is None:
            continue
        human2.append(r["human_score"])
        cllmk7.append(round(statistics.mean(r["cllm_x7_attempts"]) * 4) / 4)
        verifk7.append(round(statistics.mean(v["verifier_x7_attempts"]) * 4) / 4)
        qids2.append(r["qid"])
    df2 = long_df(human2, cllmk7, verifk7, qids2, "C_LLM_x7", "Verifier_x7")
    results.append(fit_lmm(df2, "Mohler 46q FAIR CONTROL: C_LLM x7 vs Verifier x7"))

    # 3. Mohler combined 50q headline
    orig = json.loads((BASE / "data" / "mohler_real_eval_results.json").read_text())["results"]
    ext = json.loads((BASE / "data" / "mohler_real_extension_eval_results.json").read_text())["results"]
    combined = orig + ext
    human3 = [r["human_score"] for r in combined]
    cllm3 = [r["cllm_score"] for r in combined]
    c53 = [r["c5_score"] for r in combined]
    qids3 = [r["qid"] for r in combined]
    df3 = long_df(human3, cllm3, c53, qids3, "C_LLM", "C5_fix")
    results.append(fit_lmm(df3, "Mohler combined 50q headline: C_LLM(x1) vs C5_fix(single)"))

    # 4. DigiKlausur headline
    dk = json.loads((BASE / "data" / "digiklausur_eval_results.json").read_text())["results"]
    ds = json.loads((BASE / "data" / "digiklausur_dataset.json").read_text())
    id_to_qid = {r["id"]: r["question_id"] for r in ds}
    human4 = [r["human_score"] for r in dk]
    cllm4 = [r["cllm_score"] for r in dk]
    c54 = [r["c5_score"] for r in dk]
    qids4 = [id_to_qid[r["id"]] for r in dk]
    df4 = long_df(human4, cllm4, c54, qids4, "C_LLM", "C5fix")
    results.append(fit_lmm(df4, "DigiKlausur headline: C_LLM(x1) vs C5fix(single)"))

    # 5. DigiKlausur fair control: C_LLM x7(mean) vs C5fix x7(mean)
    dkc = json.loads((BASE / "data" / "digiklausur_cllm_selfconsistency_k7_results.json").read_text())["per_sample"]
    dk_c5x7 = {r["id"]: r for r in
               json.loads((BASE / "data" / "digiklausur_c5fix_selfconsistency_results.json").read_text())["per_sample"]}
    human5, cllmk7_5, c5x7_5, qids5 = [], [], [], []
    for r in dkc:
        if r["cllm_k7_mean"] is None:
            continue
        v = dk_c5x7[r["id"]]
        human5.append(r["human_score"])
        cllmk7_5.append(r["cllm_k7_mean"])
        c5x7_5.append(round(statistics.mean(v["c5fix_x7_attempts"]) * 4) / 4)
        qids5.append(r["qid"])
    df5 = long_df(human5, cllmk7_5, c5x7_5, qids5, "C_LLM_x7", "C5fix_x7")
    results.append(fit_lmm(df5, "DigiKlausur FAIR CONTROL: C_LLM x7 vs C5fix x7"))

    # 6. Kaggle ASAG headline (deduped)
    from datasets.dataset_dedupe import dedupe_records
    ka_raw = json.loads((BASE / "data" / "kaggle_asag_dataset.json").read_text())
    ka_ev = json.loads((BASE / "data" / "kaggle_asag_eval_results.json").read_text())["results"]
    _, aligned_idx, _ = dedupe_records(ka_raw)
    ka_ds = [ka_raw[i] for i in aligned_idx]
    ka_res = [ka_ev[i] for i in aligned_idx]
    q_to_id = {}
    qids6 = []
    for s in ka_ds:
        q = s.get("question", "")
        if q not in q_to_id:
            q_to_id[q] = f"KA{len(q_to_id)+1:03d}"
        qids6.append(q_to_id[q])
    human6 = [r["human_score"] for r in ka_res]
    cllm6 = [r["cllm_score"] for r in ka_res]
    c56 = [r["c5_score"] for r in ka_res]
    df6 = long_df(human6, cllm6, c56, qids6, "C_LLM", "C5fix")
    results.append(fit_lmm(df6, "Kaggle ASAG (deduped) headline: C_LLM(x1) vs C5fix(single)"))

    out_path = BASE / "data" / "lmm_reanalysis.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\n[saved] {out_path}")

    print("\n=== SUMMARY: LMM (LRT p-value) vs. prior cluster-mean Wilcoxon p-value ===")
    prior = {
        "Mohler 46q headline: C_LLM(x1) vs C5_fix(single)": 0.111,
        "Mohler 46q FAIR CONTROL: C_LLM x7 vs Verifier x7": 0.256,
        "Mohler combined 50q headline: C_LLM(x1) vs C5_fix(single)": 0.0657,
        "DigiKlausur headline: C_LLM(x1) vs C5fix(single)": 0.0489,
        "DigiKlausur FAIR CONTROL: C_LLM x7 vs C5fix x7": 0.089,
        "Kaggle ASAG (deduped) headline: C_LLM(x1) vs C5fix(single)": 0.702,
    }
    for r in results:
        old_p = prior.get(r["label"], float("nan"))
        print(f"  {r['label']}: LMM LRT p={r['lrt_p']:.4f}  (prior cluster-Wilcoxon p={old_p:.4f})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
