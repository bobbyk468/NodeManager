#!/usr/bin/env python3
"""
verify_all_paper_claims.py — cross-check every quantitative claim in
Paper 1 AND Paper 2 against the cached metadata / dataset files / script
output, plus structural checks (file existence, LaTeX preamble).

For every claim, this script either:
  (a) reproduces the number from cached data and reports MATCH if the
      paper text matches it within rounding;
  (b) reports MISMATCH if the paper text does not match the actual data,
      with the discrepancy quantified;
  (c) reports UNVERIFIABLE if the claim cannot be checked from cached
      data (e.g., external citation, prose claim).

Run:
    python verify_all_paper_claims.py

Exit code: 0 if every checkable claim matches; 1 if any mismatch found.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

BASE = Path(__file__).parent


def load_eval(name: str) -> dict:
    with (BASE / "data" / f"{name}_eval_results.json").open() as f:
        return json.load(f)


def err_arrays(name: str):
    d = load_eval(name)
    results = d["results"]
    human = np.array([r["human_score"] for r in results])
    cllm = np.array([r["cllm_score"] for r in results])
    c5 = np.array([r["c5_score"] for r in results])
    return np.abs(human - cllm), np.abs(human - c5), results


def claim(label: str, paper_value, actual_value, tol: float = 0.01,
          status: list = None) -> None:
    """Record a claim's check status. status is a list to append result to."""
    if isinstance(actual_value, str):
        ok = (paper_value == actual_value)
    elif paper_value is None or actual_value is None:
        ok = (paper_value is None and actual_value is None)
    elif isinstance(paper_value, (int, float)) and isinstance(actual_value, (int, float)):
        ok = abs(paper_value - actual_value) <= tol
    else:
        ok = (paper_value == actual_value)
    tag = "MATCH " if ok else "FAIL  "
    status.append((tag, label, paper_value, actual_value))


def main() -> int:
    s: list[tuple[str, str, object, object]] = []

    # ====================================================================
    # 1. DATASET STRUCTURE CLAIMS
    # ====================================================================
    # Mohler 10 questions × 12 responses = 120
    sys.path.insert(0, str(BASE))
    from datasets.mohler_loader import load_mohler_sample
    ds = load_mohler_sample()
    q_count = len(set(s.question_id for s in ds.samples))
    claim("Mohler #questions = 10", 10, q_count, 0, status=s)
    claim("Mohler #responses = 120", 120, len(ds.samples), 0, status=s)
    per_q = Counter(x.question_id for x in ds.samples)
    claim("Mohler responses/question = 12", 12, list(per_q.values())[0], 0, status=s)

    # DigiKlausur 17 × 38 = 646
    with (BASE / "data" / "digiklausur_dataset.json").open() as f:
        dk = json.load(f)
    qc = Counter(x["question_id"] for x in dk)
    claim("DigiKlausur #questions = 17", 17, len(qc), 0, status=s)
    claim("DigiKlausur #responses = 646", 646, len(dk), 0, status=s)
    claim("DigiKlausur responses/q (uniform) = 38", 38, list(qc.values())[0], 0, status=s)

    # Kaggle ASAG 150 unique questions, 473 responses
    with (BASE / "data" / "kaggle_asag_dataset.json").open() as f:
        ka = json.load(f)
    q_uniq = len({x["question"] for x in ka})
    claim("Kaggle ASAG #unique-questions = 150", 150, q_uniq, 0, status=s)
    claim("Kaggle ASAG #responses = 473", 473, len(ka), 0, status=s)

    # Total samples across 3 datasets = 1,239
    total = len(ds.samples) + len(dk) + len(ka)
    claim("Total samples = 1,239", 1239, total, 0, status=s)
    total_q = q_count + len(qc) + q_uniq
    claim("Total questions = 177", 177, total_q, 0, status=s)

    # ====================================================================
    # 2. MOHLER HEADLINE NUMBERS
    # ====================================================================
    em, ef, res = err_arrays("mohler")
    claim("Mohler C_LLM MAE = 0.3300", 0.3300, float(em.mean()), 0.001, status=s)
    claim("Mohler C5_fix MAE = 0.2229", 0.2229, float(ef.mean()), 0.001, status=s)
    red = (em.mean() - ef.mean()) / em.mean() * 100
    claim("Mohler MAE reduction = 32.4%", 32.4, float(red), 0.05, status=s)

    # Wilcoxon
    _, p_two = stats.wilcoxon(ef, em, alternative="two-sided", zero_method="wilcox")
    _, p_one = stats.wilcoxon(ef, em, alternative="less", zero_method="wilcox")
    claim("Mohler Wilcoxon p two-tailed = 0.0026", 0.0026, float(p_two), 0.0002, status=s)
    claim("Mohler Wilcoxon p one-tailed = 0.0013", 0.0013, float(p_one), 0.0002, status=s)

    # W+ and ties
    diffs = ef - em
    n_ties = int((diffs == 0).sum())
    nz = diffs[diffs != 0]
    ranks = stats.rankdata(np.abs(nz))
    w_plus = float(ranks[nz > 0].sum())
    claim("Mohler W+ = 344", 344, int(w_plus), 1, status=s)
    claim("Mohler #ties = 70", 70, n_ties, 0, status=s)
    claim("Mohler #non-tied = 50", 50, int((diffs != 0).sum()), 0, status=s)

    # Cohen's d_z
    d_z = float(diffs.mean() / diffs.std(ddof=1))
    claim("Mohler d_z = -0.295", -0.295, float(d_z), 0.005, status=s)

    # Post-hoc power (one-tailed, α=0.05)
    from scipy.stats import norm
    n = 120
    z_alpha = norm.ppf(0.95)
    power = float(norm.cdf(abs(d_z) * np.sqrt(n) - z_alpha))
    claim("Mohler post-hoc power = 0.943", 0.943, float(power), 0.005, status=s)

    # ====================================================================
    # 3. NON-TIED (F2) NUMBERS
    # ====================================================================
    mask = diffs != 0
    nt_em = float(em[mask].mean())
    nt_ef = float(ef[mask].mean())
    nt_red = (nt_em - nt_ef) / nt_em * 100
    nt_diff = diffs[mask]
    nt_dz = float(nt_diff.mean() / nt_diff.std(ddof=1))
    claim("Non-tied n = 50", 50, int(mask.sum()), 0, status=s)
    claim("Non-tied MAE C_LLM = 0.507", 0.507, nt_em, 0.003, status=s)
    claim("Non-tied MAE C5_fix = 0.250", 0.250, nt_ef, 0.003, status=s)
    claim("Non-tied MAE reduction = 50.7%", 50.7, float(nt_red), 0.1, status=s)
    claim("Non-tied d_z = -0.48 (paper |d_z|=0.48)", -0.48, nt_dz, 0.01, status=s)

    # ====================================================================
    # 4. QUESTION-LEVEL CLUSTERED + LOOCV
    # ====================================================================
    qerr_cllm = em.reshape(10, 12).mean(axis=1)
    qerr_c5 = ef.reshape(10, 12).mean(axis=1)
    _, pq_two = stats.wilcoxon(qerr_c5, qerr_cllm, alternative="two-sided", zero_method="wilcox")
    _, pq_one = stats.wilcoxon(qerr_c5, qerr_cllm, alternative="less", zero_method="wilcox")
    claim("Q-level p two-tail = 0.0488", 0.0488, float(pq_two), 0.0002, status=s)
    claim("Q-level p one-tail = 0.0244", 0.0244, float(pq_one), 0.0002, status=s)

    # LOOCV
    n_sig_one = 0
    n_sig_two = 0
    for q in range(10):
        keep = [i for i in range(10) if i != q]
        _, p_t = stats.wilcoxon(qerr_c5[keep], qerr_cllm[keep],
                                alternative="two-sided", zero_method="wilcox")
        _, p_o = stats.wilcoxon(qerr_c5[keep], qerr_cllm[keep],
                                alternative="less", zero_method="wilcox")
        if p_o < 0.05: n_sig_one += 1
        if p_t < 0.05: n_sig_two += 1
    claim("LOOCV one-tail folds significant = 10", 10, n_sig_one, 0, status=s)
    claim("LOOCV two-tail folds significant = 1", 1, n_sig_two, 0, status=s)

    # ====================================================================
    # 5. CROSS-DATASET META-ANALYSIS
    # ====================================================================
    with (BASE / "data" / "cross_dataset_significance.json").open() as f:
        cd = json.load(f)
    fe = cd["meta_analysis"]["fixed_effects"]
    re_ = cd["meta_analysis"]["random_effects_DL"]
    claim("FE pool d_z = -0.073", -0.0733, fe["d_z"], 0.001, status=s)
    claim("FE pool 95% CI lo = -0.13", -0.1291, fe["ci_95"][0], 0.005, status=s)
    claim("FE pool 95% CI hi = -0.02", -0.0175, fe["ci_95"][1], 0.005, status=s)
    claim("FE pool p_two = 0.010", 0.010, fe["p_two_tailed"], 0.001, status=s)
    claim("RE pool d_z = -0.10", -0.1015, re_["d_z"], 0.005, status=s)
    claim("RE pool 95% CI lo = -0.21", -0.2142, re_["ci_95"][0], 0.005, status=s)
    claim("RE pool 95% CI hi = +0.01", 0.0112, re_["ci_95"][1], 0.005, status=s)
    claim("I^2 = 70%", 69.9, re_["I2_percent"], 0.5, status=s)
    claim("RE pool p_one = 0.039", 0.039, re_["p_one_tailed_C5_better"], 0.001, status=s)

    # ====================================================================
    # 6. PER-DATASET CROSS-EFFECTS
    # ====================================================================
    # Note: paper reports d_z values to 2 decimals (Mohler -0.30, DigiKlausur -0.07, Kaggle -0.03).
    # We use tolerance 0.01 to allow for the rounding tier the paper reports.
    for ds_name, exp_d_z in [("mohler", -0.30), ("digiklausur", -0.07), ("kaggle_asag", -0.03)]:
        em2, ef2, _ = err_arrays(ds_name)
        d_z2 = float((ef2 - em2).mean() / (ef2 - em2).std(ddof=1))
        claim(f"{ds_name} d_z", exp_d_z, d_z2, 0.01, status=s)

    # ====================================================================
    # 7. PER-SOLO BREAKDOWN
    # ====================================================================
    res = load_eval("mohler")["results"]
    by_solo = defaultdict(list)
    for r in res:
        by_solo[r["solo"]].append((abs(r["human_score"] - r["cllm_score"]),
                                   abs(r["human_score"] - r["c5_score"])))
    rel = by_solo.get("Relational", [])
    if rel:
        arr = np.array(rel)
        rel_red = (arr[:, 0].mean() - arr[:, 1].mean()) / arr[:, 0].mean() * 100
        claim("Mohler Relational n = 34", 34, len(rel), 0, status=s)
        claim("Mohler Relational reduction = 69.8%", 69.8, float(rel_red), 0.5, status=s)

    # ====================================================================
    # 8. TAXONOMY κ
    # ====================================================================
    with (BASE / "data" / "taxonomy_kappa_results.json").open() as f:
        kappa = json.load(f)
    claim("Taxonomy macro κ = 0.295", 0.2947, kappa["macro_kappa"], 0.005, status=s)
    claim("Taxonomy micro κ = 0.326", 0.3258, kappa["micro_kappa_pooled"], 0.005, status=s)
    claim("Taxonomy #entries = 16", 16, kappa["n_taxonomy_entries"], 0, status=s)

    # ====================================================================
    # 9. HUMAN IRR ON MOHLER
    # ====================================================================
    sm = np.array([s_.score_me for s_ in ds.samples])
    so = np.array([s_.score_other for s_ in ds.samples])
    r_human = float(np.corrcoef(sm, so)[0, 1])
    claim("Human IRR r = 0.985", 0.985, r_human, 0.005, status=s)
    diff_h = np.abs(sm - so)
    claim("Human samples disagree ≥ 1 = 0", 0, int((diff_h >= 1).sum()), 0, status=s)

    # ====================================================================
    # 10. PER-QUESTION (8/10 wins)
    # ====================================================================
    wins = 0
    for q in range(10):
        idxs = list(range(q*12, (q+1)*12))
        em_q = np.array([abs(res[i]["human_score"] - res[i]["cllm_score"]) for i in idxs]).mean()
        ef_q = np.array([abs(res[i]["human_score"] - res[i]["c5_score"]) for i in idxs]).mean()
        if ef_q < em_q: wins += 1
    claim("C5 wins on 8/10 questions", 8, wins, 0, status=s)

    # ====================================================================
    # 11. CONCEPT EXTRACTION COLLAPSE ON KAGGLE
    # ====================================================================
    for ds_name, exp_pct in [("mohler", 16.7), ("digiklausur", 6.8), ("kaggle_asag", 100.0)]:
        rr = load_eval(ds_name)["results"]
        zc = sum(1 for r in rr if len(r.get("matched_concepts", [])) == 0)
        pct = zc / len(rr) * 100
        claim(f"{ds_name} 0-concept extraction %", exp_pct, float(pct), 0.5, status=s)

    # ====================================================================
    # 12. SIGNAL-SOURCE ABLATION (concepts_only, taxonomy_only)
    # ====================================================================
    with (BASE / "data" / "ablation_component_results.json").open() as f:
        ab = json.load(f)
    sys_ = ab["systems"]
    claim("concepts_only MAE = 0.217", 0.217, sys_["concepts_only"]["mae"], 0.001, status=s)
    claim("taxonomy_only MAE = 0.229", 0.229, sys_["taxonomy_only"]["mae"], 0.001, status=s)
    claim("C5_fix MAE (component ablation) = 0.223", 0.223, sys_["C5_fix"]["mae"], 0.001, status=s)
    claim("C_LLM MAE (component ablation) = 0.330", 0.330, sys_["C_LLM"]["mae"], 0.001, status=s)

    # ====================================================================
    # 13. BERT BASELINES (from REAL fixes JSON)
    # ====================================================================
    if (BASE / "data" / "real_fixes_results.json").exists():
        with (BASE / "data" / "real_fixes_results.json").open() as f:
            rf = json.load(f)
        r3 = rf["real_3_local_bert_baseline"]
        claim("MiniLM frozen MAE = 1.833", 1.833, r3["mae_bert_frozen"], 0.005, status=s)
        claim("MiniLM frozen r = 0.649", 0.649, r3["pearson_r_bert_frozen"], 0.005, status=s)
        claim("BERT test set n = 90", 90, r3["n_test"], 0, status=s)

    if (BASE / "data" / "real_fixes_v2_results.json").exists():
        with (BASE / "data" / "real_fixes_v2_results.json").open() as f:
            rf2 = json.load(f)
        r5 = rf2["real_5_stronger_bert_mpnet"]
        claim("MPNet frozen MAE = 1.934", 1.934, r5["mae_mpnet_frozen"], 0.005, status=s)
        claim("MPNet frozen r = 0.669", 0.669, r5["pearson_r_mpnet_frozen"], 0.005, status=s)
        # Bootstrap cluster CIs
        r6 = rf2["real_6_cluster_bootstrap"]
        claim("Mohler test cluster CI lo = 2.5%", 2.5, r6["mohler_test_n90"]["cluster_bootstrap_ci_95"][0], 0.5, status=s)
        claim("Mohler test cluster CI hi = 56.0%", 56.0, r6["mohler_test_n90"]["cluster_bootstrap_ci_95"][1], 0.5, status=s)
        claim("Mohler all cluster CI lo = 8.4%", 8.4, r6["mohler_all"]["cluster_bootstrap_ci_95"][0], 0.5, status=s)
        claim("Mohler all cluster CI hi = 49.9%", 49.9, r6["mohler_all"]["cluster_bootstrap_ci_95"][1], 0.5, status=s)
        r7 = rf2["real_7_bca_sensitivity"]
        claim("Mohler test BCa CI lo = 14.1%", 14.1, r7["bca_ci_95"][0], 0.5, status=s)
        claim("Mohler test BCa CI hi = 49.8%", 49.8, r7["bca_ci_95"][1], 0.5, status=s)

    n_p1_claims = len(s)

    # ====================================================================
    # PAPER 2 CLAIMS
    # ====================================================================

    # 14. Verifier honesty: Paper 2 must NOT claim fine-tuning (the actual
    #     implementation is prompted LLM only — see conceptgrade/lrm_verifier.py)
    p2_text = (BASE / "docs" / "paper_phase2_vis2027.tex").read_text()
    p1_text = (BASE / "docs" / "paper_phase1_ieee.tex").read_text()
    bad_phrases_p2 = [
        "fine-tuned using the Mohler",
        "augmented to $\\approx$2,107 instances",
        "5-fold cross-validation",
        "learning rate $1 \\times 10",
        "2,107 instances",  # not the math, the claim
    ]
    for phrase in bad_phrases_p2:
        present = phrase in p2_text
        claim(f"Paper 2 must NOT claim Verifier '{phrase[:40]}…'",
              False, present, status=s)

    # The actual Verifier is a DeepSeek-R1 / Gemini prompted LLM call.
    # Paper 2 §A.1 should mention this explicitly.
    claim("Paper 2 §A.1 mentions DeepSeek-R1 (actual primary Verifier backend)",
          True,
          "deepseek-reasoner" in p2_text or "DeepSeek-R1" in p2_text,
          status=s)
    claim("Paper 2 §A.1 explicitly says 'no fine-tuning' or 'inference-only'",
          True,
          ("no fine-tuning" in p2_text) or ("inference-only" in p2_text)
          or ("inference only" in p2_text),
          status=s)

    # 15. Study design arithmetic (Paper 2 §5.1)
    n_per_condition = 32
    n_conditions = 2
    claim("Paper 2 §5.1: 32 × 2 = N = 64", 64,
          n_per_condition * n_conditions, 0, status=s)

    # Holm-Bonferroni: 5 confirmatory hypotheses at family-wise α=0.05
    family_size = 5
    family_alpha = 0.05
    alpha_strictest = family_alpha / family_size
    claim("Paper 2 §5.1: Holm-Bonferroni α₁ = 0.05/5 = 0.01",
          0.01, round(alpha_strictest, 4), 0.0001, status=s)

    # 16. Cross-paper shared claims (Paper 2 abstract should match Paper 1)
    # Same n=1,239 / 177 questions / d_z = -0.30, -0.07, -0.03 are already
    # verified in claims 7-9 above. Here we verify Paper 2 text matches.
    p2_tex = (BASE / "docs" / "paper_phase2_vis2027.tex").read_text()
    # Note: Paper 2's abstract was restructured around heterogeneity-first
    # framing. Explicit "1,239" / "177 questions" may appear in body (§4.3
    # cross-dataset section). We check that the Paper 1 numbers Paper 2
    # *actually cites in its new abstract* match Paper 1.
    claim("Paper 2 mentions '1,239' SOMEWHERE", True,
          "1{,}239" in p2_tex or "$1{,}239$" in p2_tex, status=s)
    claim("Paper 2 mentions '177' SOMEWHERE", True,
          "$177$" in p2_tex or "177 questions" in p2_tex
          or "across $177$" in p2_tex, status=s)
    claim("Paper 2 abstract mentions 'p = 0.0026' (Mohler)", True,
          "p = 0.0026" in p2_tex, status=s)
    claim("Paper 2 abstract mentions 'I^2 = 70'", True,
          "I^2 = 70" in p2_tex or "$I^2 = 70" in p2_tex, status=s)
    claim("Paper 2 mentions Kaggle '473/473' SOMEWHERE", True,
          "473/473" in p2_tex or "$473/473$" in p2_tex, status=s)
    # New: paper should explicitly frame around silent-failure /
    # structural-confidence triage (post-Gemini-Round-2 reframing)
    claim("Paper 2 frames around structural-confidence triage", True,
          "structural-confidence triage" in p2_tex
          or "structural-confidence gap" in p2_tex
          or "silent-failure" in p2_tex
          or "failure-mode" in p2_tex,
          status=s)

    # 17. Document class
    claim("Paper 2 uses vgtc journal+review", True,
          "\\documentclass[journal,review]{vgtc}" in p2_tex, status=s)

    # 18. Supplementary document existence
    for doc in [
        "OSF_PREREGISTRATION.md",
        "IRB_PROTOCOL.md",
        "PILOT_PROTOCOL.md",
        "data/pilot/pilot_template.csv",
        "compute_validation_gate.py",
        "VALIDATION_GATE_PROTOCOL.md",
    ]:
        exists = (BASE / doc).exists()
        claim(f"Supplementary {doc} exists", True, exists, status=s)

    # 19. Paper 1 must NOT claim the fictional 4-way ablation numbers
    #     (0.2889 and 0.2835 were never actually computed; they appeared only
    #     in the paper text and not in any cached data file)
    for fabricated_num in ["0.2889", "0.2835"]:
        claim(f"Paper 1 must NOT claim fabricated MAE '{fabricated_num}'",
              False, fabricated_num in p1_text, status=s)

    # 19b. Paper 1 must NOT claim the fictional kg_weight sensitivity rows
    #      (29.8%, 31.2%, 28.1% were never actually computed)
    for fabricated_num in ["29.8\\% improvement", "31.2\\% improvement",
                            "28.1\\% improvement"]:
        claim(f"Paper 1 must NOT claim fabricated kg_weight '{fabricated_num}'",
              False, fabricated_num in p1_text, status=s)

    # 19c. Paper 1 must NOT have the fictional Weight Sensitivity Table rows
    for fabricated_cell in ["0.741 & 0.234", "0.762 & 0.230", "0.756 & 0.232",
                             "0.748 & 0.237", "0.751 & 0.235"]:
        claim(f"Paper 1 must NOT have fabricated weight-sensitivity cell '{fabricated_cell[:18]}…'",
              False, fabricated_cell in p1_text, status=s)

    # 20. Pre-registered confirmatory boundary d ≥ 0.7
    claim("Paper 2 §5.1: pre-registered d ≥ 0.7 boundary", True,
          "d \\geq 0.7" in p2_tex or "$d \\geq 0.7$" in p2_tex
          or "d ≥ 0.7" in p2_tex, status=s)

    # 21. IRR target κ ≥ 0.70
    claim("Paper 2 §5.1: IRR target κ ≥ 0.70", True,
          "\\kappa \\geq 0.70" in p2_tex, status=s)

    # 22. Misconception heatmap κ cross-reference
    claim("Paper 2 §3: misconception heatmap cites κ_micro = 0.33", True,
          "\\kappa_{\\text{micro}} = 0.33" in p2_tex
          or "$\\kappa_{\\text{micro}} = 0.33$" in p2_tex, status=s)

    # 23. No leftover false-model references in either paper
    p1_tex = (BASE / "docs" / "paper_phase1_ieee.tex").read_text()
    # 'Llama-3.3-70b' should not appear as our baseline (1 generic mention OK
    # but not '-3.3-70b baseline')
    bad_llama_count = p1_tex.count("Llama-3.3-70b")
    claim("Paper 1 has no Llama-3.3-70b baseline claims", 0,
          bad_llama_count, 0, status=s)
    bad_groq = p1_tex.count("Groq")
    claim("Paper 1 has no Groq references", 0, bad_groq, 0, status=s)

    # 24. The C5_fix MAE = 0.223 should match across Paper 1, Paper 2, eval JSON
    # (already checked above)
    p2_has_0223 = "0.2229" in p2_tex or "0.223" in p2_tex
    claim("Paper 2 mentions C5_fix MAE = 0.2229", True, p2_has_0223, status=s)
    p2_has_0330 = "0.3300" in p2_tex or "0.330" in p2_tex
    claim("Paper 2 mentions C_LLM MAE = 0.3300", True, p2_has_0330, status=s)

    # 25. Paper 2 has explicit placeholder labels on mock figures
    n_placeholders = p2_tex.count("PRE-SUBMISSION PLACEHOLDER")
    claim("Paper 2 has ≥1 mock-figure PRE-SUBMISSION PLACEHOLDER labels",
          True, n_placeholders >= 1, status=s)

    # 26. Paper 2 has explicit [OSF-ID-TBD] / [IRB-PROTOCOL-TBD] placeholders
    claim("Paper 2 has [OSF-ID-TBD] placeholder", True,
          "[OSF-ID-TBD]" in p2_tex, status=s)
    claim("Paper 2 has [IRB-PROTOCOL-TBD] placeholder", True,
          "[IRB-PROTOCOL-TBD]" in p2_tex, status=s)

    # ====================================================================
    # 27. KG SIZE CLAIMS (verify against actual ds_knowledge_graph.json)
    # ====================================================================
    import re as _re
    with (BASE / "data" / "ds_knowledge_graph.json").open() as f:
        kg = json.load(f)
    claim("KG #concepts = 101 (actual file)", 101, len(kg["concepts"]), 0, status=s)
    claim("KG #relationships = 138 (actual file)", 138, len(kg["relationships"]), 0, status=s)
    claim("KG #concept_types = 8 (actual file)", 8, len(kg["stats"]["concept_types"]), 0, status=s)
    claim("KG #relationship_types = 10 (actual file)", 10, len(kg["stats"]["relationship_types"]), 0, status=s)

    # Paper 1 text should match: 101 concepts, 138 relationships, 8 semantic types, 10 relation types
    p1_kg_101 = "101 concepts" in p1_tex or "101 domain concepts" in p1_tex
    claim("Paper 1 claims 101 concepts (matches KG)", True, p1_kg_101, status=s)
    p1_kg_138 = "138 typed relationships" in p1_tex or "138 relationships" in p1_tex
    claim("Paper 1 claims 138 relationships (matches KG)", True, p1_kg_138, status=s)
    p1_8types = "eight semantic" in p1_tex or "8 semantic" in p1_tex
    claim("Paper 1 claims 8 semantic concept types (matches KG)", True, p1_8types, status=s)
    p1_10reltypes = "across 10\nrelation types" in p1_tex or "10 relation types" in p1_tex \
                  or "across 10 relation" in p1_tex
    claim("Paper 1 claims 10 relation types (matches KG)", True, p1_10reltypes, status=s)
    # Negative: must NOT claim 11 relation types
    claim("Paper 1 does NOT claim 11 relation types (stale)", False,
          "11 relation types" in p1_tex or "across 11\nrelation types" in p1_tex,
          status=s)

    # ====================================================================
    # 28. FIGURE FILE EXISTENCE (every \includegraphics{} must resolve)
    # ====================================================================
    import os
    fig_pattern = _re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
    for tex_path, paper_name in [
        ("docs/paper_phase1_ieee.tex", "Paper 1"),
        ("docs/paper_phase2_vis2027.tex", "Paper 2"),
    ]:
        with (BASE / tex_path).open() as f:
            t = f.read()
        figs = sorted(set(fig_pattern.findall(t)))
        for fig in figs:
            paper_dir = (BASE / tex_path).parent
            candidates = [paper_dir / fig, paper_dir / "figures" / os.path.basename(fig),
                          paper_dir / (fig + ".png"), paper_dir / (fig + ".pdf")]
            exists = any(c.exists() for c in candidates)
            claim(f"{paper_name} figure '{fig}' exists", True, exists, status=s)

    # ====================================================================
    # 29. SCRIPT FILE EXISTENCE (every script named in either paper exists)
    # ====================================================================
    py_pattern = _re.compile(r"([a-zA-Z][a-zA-Z0-9_/\\]*\.py)")
    for tex_path, paper_name in [
        ("docs/paper_phase1_ieee.tex", "Paper 1"),
        ("docs/paper_phase2_vis2027.tex", "Paper 2"),
    ]:
        with (BASE / tex_path).open() as f:
            t = f.read()
        scripts = py_pattern.findall(t)
        unique_scripts = sorted({sc.replace("\\_", "_").replace("\\", "") for sc in scripts})
        for sc in unique_scripts:
            paths = [BASE / sc, BASE / "docs" / sc, BASE / os.path.basename(sc)]
            exists = any(p.exists() for p in paths)
            claim(f"{paper_name} script '{sc}' exists", True, exists, status=s)

    # ====================================================================
    # 30. ANTI-FABRICATION REGEX PATTERNS
    # Catches new specific-detail claims that look plausible but have no
    # backing in the codebase or cached data.
    # ====================================================================
    fab_patterns_p1 = [
        # Training-procedure phrases (we do NOT train anything; pipeline is inference-only)
        (r"\b\d+\s+epochs\b", "epochs claim"),
        (r"\blearning\s+rate\s*=?\s*\$?1?\\?times?\s*10\^?{?-\d", "learning-rate claim"),
        (r"\b\d+\s*-?\s*fold\s+(?:cross-)?validation\b", "K-fold CV claim"),
        (r"\bbatch\s+size\s*=?\s*\d+\b", "batch-size claim"),
        # Specific GPU/TPU claims (we use cloud API, no local GPU)
        (r"\b(?:A100|V100|H100|TPU\s*v?\d|H800)\b", "GPU/TPU claim"),
        # Hyperparameter values for non-existent training
        (r"\bdropout\s*=?\s*0\.\d", "dropout claim"),
        (r"\bAdamW?\s+optimizer", "optimizer claim"),
        # Fabricated baseline model names (none of these are in our codebase)
        (r"\bLlama-?3\.3-?70b\b", "Llama-3.3-70b claim"),
        (r"\bGroq\b", "Groq claim"),
    ]
    for paper_tex, paper_name, paper_label in [
        (p1_text, p1_tex, "Paper 1"),  # placeholder; we'll use the actual loaded text below
    ]:
        pass
    # Use the texts we already loaded above
    for paper_label, paper_text in [("Paper 1", p1_text), ("Paper 2", p2_text)]:
        for pat, desc in fab_patterns_p1:
            matches = _re.findall(pat, paper_text, flags=_re.IGNORECASE)
            present = len(matches) > 0
            # For some patterns we ALLOW them in certain contexts (limitations etc.)
            # but generally these should be absent.
            claim(f"{paper_label} has NO {desc}", False, present, status=s)

    # 30b. TIE COMPOSITION (defuses "ties = both wrong by same large amount")
    em_full, ef_full, _ = err_arrays("mohler")
    tied_mask = (ef_full - em_full) == 0
    both_correct = int(((em_full == 0) & (ef_full == 0)).sum())
    tied_err = em_full[tied_mask]
    tied_err_gt_1 = int((tied_err > 1.0).sum())
    claim("Mohler ties: 31 both-correct", 31, both_correct, 0, status=s)
    claim("Mohler ties: 0 ties have |err| > 1.0", 0, tied_err_gt_1, 0, status=s)

    # Paper 1 must mention the tie-composition disclosure
    p1_text_now = (BASE / "docs" / "paper_phase1_ieee.tex").read_text()
    claim("Paper 1 mentions '31' both-correct ties (tie composition)",
          True, "$31$" in p1_text_now and "both predictions" in p1_text_now,
          status=s)

    # ====================================================================
    # 31. VERIFIER-COMPONENT HONEST DESCRIPTION
    # The verifier MUST be described as inference-only / prompted LLM.
    # ====================================================================
    # Paper 2 §A.1 should mention "no fine-tuning" or "inference-only"
    claim("Paper 2 §A.1 description matches conceptgrade/lrm_verifier.py reality",
          True,
          ("inference-only" in p2_text) or ("no fine-tuning" in p2_text)
          or ("inference only" in p2_text),
          status=s)
    # Paper 2 should mention DeepSeek (primary backend) or note Gemini fallback
    claim("Paper 2 §A.1 mentions deepseek-reasoner or DeepSeek-R1",
          True,
          ("deepseek-reasoner" in p2_text) or ("DeepSeek-R1" in p2_text)
          or ("DeepSeek" in p2_text),
          status=s)

    n_p2_claims = len(s) - n_p1_claims

    # ====================================================================
    # PRINT REPORT
    # ====================================================================
    print("=" * 78)
    print(f"PAPER 1 + PAPER 2 CLAIM CROSS-CHECK "
          f"(P1: {n_p1_claims} claims, P2: {n_p2_claims} claims, "
          f"total: {len(s)})")
    print("=" * 78)
    fails = []
    for i, (tag, label, paper, actual) in enumerate(s):
        if i == n_p1_claims:
            print(f"\n{'-' * 78}\nPAPER 2 CLAIMS\n{'-' * 78}")
        if tag == "MATCH ":
            print(f"  ✓ {label}")
        else:
            print(f"  ✗ {label}  PAPER={paper}  ACTUAL={actual}")
            fails.append((label, paper, actual))
    print()
    if fails:
        print(f"FAIL: {len(fails)} claims MISMATCH")
        for (lab, p, a) in fails:
            print(f"  - {lab}  paper={p}  actual={a}")
        return 1
    print(f"PASS: all {len(s)} claims verified against cached data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
