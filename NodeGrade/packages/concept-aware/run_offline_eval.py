"""
ConceptGrade Offline End-to-End Evaluation — Zero API calls.

Loads all pre-saved scores from data/ and produces the full ablation table:

  C0       Cosine-Only Baseline        (from checkpoint)
  C_LLM    Pure LLM Zero-Shot          (from checkpoint)
  C1       ConceptGrade Baseline (KG)  (from checkpoint — broken kg_raw)
  C1_fix   KG-Evidence Concept Score   (concept_score from gemini_kg_dual_scores)
  C5_fix   KG-Evidence Holistic Score  (holistic_score from gemini_kg_dual_scores)

All data pre-saved from previous Gemini sessions — no API key required.

Usage:
    python3 run_offline_eval.py [--latex] [--save]

    --latex   : Also print LaTeX table
    --save    : Save results to data/offline_eval_results.json
"""

from __future__ import annotations

import json
import os
import sys
import numpy as np
from scipy.stats import pearsonr, wilcoxon

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data")

CHECKPOINT  = os.path.join(DATA_DIR, "ablation_checkpoint_gemini_flash_latest.json")
DUAL_SCORES = os.path.join(DATA_DIR, "gemini_kg_dual_scores.json")

SEP = "─" * 76


def load_data():
    with open(CHECKPOINT) as f:
        ckpt = json.load(f)
    with open(DUAL_SCORES) as f:
        dual = json.load(f)
    return ckpt, dual


def metrics(human: list, predicted: list) -> dict:
    h = np.array(human, dtype=float)
    p = np.array(predicted, dtype=float)
    mae  = float(np.mean(np.abs(h - p)))
    rmse = float(np.sqrt(np.mean((h - p) ** 2)))
    r, _  = pearsonr(h, p)

    from sklearn.metrics import cohen_kappa_score
    h_d = np.round(h * 2).astype(int)
    p_d = np.round(p * 2).astype(int)
    all_labels = list(range(0, 11))
    try:
        qwk = cohen_kappa_score(h_d, p_d, weights="quadratic", labels=all_labels)
    except Exception:
        qwk = float("nan")

    return {"mae": mae, "rmse": rmse, "r": r, "qwk": qwk}


def significance(human: list, scores_a: list, scores_b: list) -> dict:
    """One-sided Wilcoxon: does A have lower absolute error than B?"""
    h = np.array(human)
    ea = np.abs(h - np.array(scores_a))
    eb = np.abs(h - np.array(scores_b))
    diff = eb - ea
    try:
        stat, pval = wilcoxon(diff, alternative="greater", zero_method="wilcox")
    except Exception:
        stat, pval = float("nan"), float("nan")
    return {"statistic": float(stat), "p_value": float(pval), "significant": bool(pval < 0.05)}


def bootstrap_ci(human: list, predicted: list, n_boot: int = 2000, alpha: float = 0.05) -> dict:
    """Bootstrap 95% CIs for r and MAE."""
    rng = np.random.default_rng(42)
    h = np.array(human, dtype=float)
    p = np.array(predicted, dtype=float)
    n = len(h)
    rs, maes = [], []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        try:
            r, _ = pearsonr(h[idx], p[idx])
        except Exception:
            r = float("nan")
        rs.append(r)
        maes.append(float(np.mean(np.abs(h[idx] - p[idx]))))
    lo_r, hi_r   = np.nanpercentile(rs,   [alpha/2*100, (1-alpha/2)*100])
    lo_m, hi_m   = np.nanpercentile(maes, [alpha/2*100, (1-alpha/2)*100])
    return {"r_ci": (lo_r, hi_r), "mae_ci": (lo_m, hi_m)}


def format_row(cid, cname, m, base_m=None, markers=None):
    if markers is None:
        markers = {}
    if base_m is not None:
        dr  = m["r"]   - base_m["r"]
        dm  = m["mae"] - base_m["mae"]
        dr_s = f"{dr:>+8.4f}"
        dm_s = f"{dm:>+8.4f}"
    else:
        dr_s = "    —   "
        dm_s = "    —   "

    def b(val, fmt):
        s = fmt.format(val)
        return f"[{s}]" if markers.get("r") and fmt == "{:.4f}" and val == m["r"] else s

    r_s    = f"[{m['r']:.4f}]"    if markers.get("r")    else f"  {m['r']:.4f}  "
    mae_s  = f"[{m['mae']:.4f}]"  if markers.get("mae")  else f"  {m['mae']:.4f}  "
    rmse_s = f"[{m['rmse']:.4f}]" if markers.get("rmse") else f"  {m['rmse']:.4f}  "

    return (f"  {cid:<10}  {cname:<36}  {r_s}  {dr_s}  "
            f"{m['qwk']:>7.4f}  {rmse_s}  {mae_s}  {dm_s}")


def generate_latex(all_configs, metric_map, human, n) -> str:
    lines = [
        "% ConceptGrade Offline Ablation — Mohler (n={})".format(n),
        "\\begin{table}[h]\\centering",
        "\\caption{Ablation results on Mohler et al.\\ (2011) ($n=" + str(n) + "$). "
        "C\\textsubscript{LLM} = Pure LLM Zero-Shot; "
        "C\\textsubscript{1,fix} = KG Evidence $\\to$ Concept Score; "
        "C\\textsubscript{5,fix} = KG Evidence $\\to$ Holistic Score (ConceptGrade). "
        "$\\Delta$ vs.\\ C\\textsubscript{LLM}. Bold = best.}",
        "\\label{tab:offline_ablation}",
        "\\begin{tabular}{@{}llrrrrrr@{}}\\toprule",
        "\\textbf{ID} & \\textbf{System} & \\textbf{$r$} & \\textbf{$\\Delta r$} & "
        "\\textbf{QWK} & \\textbf{RMSE} & \\textbf{MAE} & \\textbf{$\\Delta$MAE} \\\\\\midrule",
    ]
    best_r    = max(m["r"]    for _, _, m, _ in all_configs)
    best_mae  = min(m["mae"]  for _, _, m, _ in all_configs)
    best_rmse = min(m["rmse"] for _, _, m, _ in all_configs)

    for cid, cname, m, baseline_id in all_configs:
        base_m = next((bm for bi, _, bm, _ in all_configs if bi == baseline_id), None)
        dr  = (m["r"]   - base_m["r"])   if base_m else None
        dm  = (m["mae"] - base_m["mae"]) if base_m else None
        dr_s = f"{dr:+.4f}" if dr is not None else "--"
        dm_s = f"{dm:+.4f}" if dm is not None else "--"

        def bfmt(val, best, fmt):
            s = fmt.format(val)
            return f"\\textbf{{{s}}}" if abs(val - best) < 1e-6 else s

        r_s    = bfmt(m["r"],    best_r,    "{:.4f}")
        mae_s  = bfmt(m["mae"],  best_mae,  "{:.4f}")
        rmse_s = bfmt(m["rmse"], best_rmse, "{:.4f}")

        if cid == "C1":
            lines.append("\\midrule")
        lines.append(
            f"{cid} & {cname} & {r_s} & {dr_s} & {m['qwk']:.4f} & {rmse_s} & {mae_s} & {dm_s} \\\\"
        )
    lines += ["\\bottomrule\\end{tabular}\\end{table}"]
    return "\n".join(lines)


def main():
    do_latex = "--latex" in sys.argv
    do_save  = "--save"  in sys.argv

    print("=" * 76)
    print("  ConceptGrade Offline End-to-End Evaluation")
    print("  Data: ablation_checkpoint + gemini_kg_dual_scores (n=120)")
    print("  Zero API calls — all scores pre-saved.")
    print("=" * 76)

    ckpt, dual = load_data()

    human = ckpt["human_scores"]
    n = len(human)
    print(f"\n  Samples: {n}  |  Human score range: {min(human):.1f}–{max(human):.1f}")

    c0_scores       = ckpt["scores"]["C0"]
    cllm_scores     = ckpt["scores"]["C_LLM"]
    c1_scores       = ckpt["scores"]["C1"]
    concept_scores  = [dual["concept_scores"][str(i)]  for i in range(n)]
    holistic_scores = [dual["holistic_scores"][str(i)] for i in range(n)]

    # Compute metrics first so we can pass them tuples below
    m_c0   = metrics(human, c0_scores)
    m_clm  = metrics(human, cllm_scores)
    m_c1   = metrics(human, c1_scores)
    m_c1f  = metrics(human, concept_scores)
    m_c5f  = metrics(human, holistic_scores)

    all_configs = [
        ("C0",     "Cosine-Only Baseline",          m_c0,  None),
        ("C_LLM",  "Pure LLM Zero-Shot",             m_clm, None),
        ("C1",     "ConceptGrade KG Raw (broken)",   m_c1,  None),
        ("C1_fix", "KG Evidence → Concept Score",    m_c1f, "C_LLM"),
        ("C5_fix", "KG Evidence → Holistic Score",   m_c5f, "C_LLM"),
    ]
    metric_map = {cid: m for cid, _, m, _ in all_configs}
    scores_map = {
        "C0": c0_scores, "C_LLM": cllm_scores, "C1": c1_scores,
        "C1_fix": concept_scores, "C5_fix": holistic_scores,
    }

    best_r    = max(m["r"]    for _, _, m, _ in all_configs)
    best_mae  = min(m["mae"]  for _, _, m, _ in all_configs)
    best_rmse = min(m["rmse"] for _, _, m, _ in all_configs)

    # ── Print table ──────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    header = (f"  {'ID':<10}  {'System':<36}  {'r':>8}  {'Δr':>8}  "
              f"{'QWK':>7}  {'RMSE':>10}  {'MAE':>10}  {'ΔMAE':>8}")
    print(header)
    print(SEP)

    for cid, cname, m, baseline_id in all_configs:
        base_m = metric_map.get(baseline_id) if baseline_id else None
        markers = {
            "r":    abs(m["r"]    - best_r)    < 1e-6,
            "mae":  abs(m["mae"]  - best_mae)  < 1e-6,
            "rmse": abs(m["rmse"] - best_rmse) < 1e-6,
        }
        print(format_row(cid, cname, m, base_m, markers))
        if cid == "C1":
            print("  " + "·" * 72)
    print(SEP)
    print("  [ ] = best in column\n")

    # ── Bootstrap CIs ───────────────────────────────────────────────────────────
    print(f"{'='*76}")
    print("  95% BOOTSTRAP CONFIDENCE INTERVALS (n_boot=2000)")
    print(f"{'='*76}\n")
    for cid, sc in scores_map.items():
        ci = bootstrap_ci(human, sc)
        m = metric_map[cid]
        print(f"  {cid:<10}  r={m['r']:.4f} [{ci['r_ci'][0]:.4f}, {ci['r_ci'][1]:.4f}]  "
              f"MAE={m['mae']:.4f} [{ci['mae_ci'][0]:.4f}, {ci['mae_ci'][1]:.4f}]")

    # ── Core claim ───────────────────────────────────────────────────────────────
    print(f"\n{'='*76}")
    print("  CORE CLAIM: ConceptGrade (C5_fix) vs Pure LLM (C_LLM)")
    print(f"{'='*76}")

    delta_mae  = m_clm["mae"]  - m_c5f["mae"]
    delta_r    = m_c5f["r"]    - m_clm["r"]
    delta_rmse = m_clm["rmse"] - m_c5f["rmse"]
    pct_mae    = delta_mae  / m_clm["mae"]  * 100
    pct_r      = delta_r    / abs(m_clm["r"]) * 100

    print(f"\n  C_LLM    → MAE={m_clm['mae']:.4f}   r={m_clm['r']:.4f}   RMSE={m_clm['rmse']:.4f}")
    print(f"  C1_fix   → MAE={m_c1f['mae']:.4f}   r={m_c1f['r']:.4f}   RMSE={m_c1f['rmse']:.4f}")
    print(f"  C5_fix   → MAE={m_c5f['mae']:.4f}   r={m_c5f['r']:.4f}   RMSE={m_c5f['rmse']:.4f}")
    print(f"\n  ΔC5_fix − C_LLM:")
    print(f"    MAE  reduction: {delta_mae:+.4f}  ({pct_mae:+.1f}%)")
    print(f"    r    increase : {delta_r:+.4f}  ({pct_r:+.1f}%)")
    print(f"    RMSE reduction: {delta_rmse:+.4f}")

    # ── Statistical significance ─────────────────────────────────────────────────
    print(f"\n{'='*76}")
    print("  STATISTICAL SIGNIFICANCE (Wilcoxon one-sided, α=0.05)")
    print(f"{'='*76}\n")

    tests = [
        ("C1_fix vs C_LLM",  concept_scores,  cllm_scores),
        ("C5_fix vs C_LLM",  holistic_scores, cllm_scores),
        ("C5_fix vs C1",     holistic_scores, c1_scores),
        ("C5_fix vs C1_fix", holistic_scores, concept_scores),
    ]
    sig_results = {}
    for label, a, b in tests:
        sig = significance(human, a, b)
        mark = "✓ SIGNIFICANT" if sig["significant"] else "✗ n.s."
        print(f"  {label:<22}  W={sig['statistic']:.1f}   p={sig['p_value']:.4f}   {mark}")
        sig_results[label] = sig

    # ── Per-question breakdown ───────────────────────────────────────────────────
    print(f"\n{'='*76}")
    print("  PER-QUESTION BREAKDOWN (MAE per question, n=12 each)")
    print(f"{'='*76}")
    print(f"\n  {'Q':>4}  {'n':>4}  {'C_LLM':>8}  {'C1_fix':>8}  {'C5_fix':>8}  {'Winner':>8}")
    print(f"  {'─'*4}  {'─'*4}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}")

    q_size = 12
    n_q = n // q_size
    q_breakdown = []
    c5_wins = 0
    for qi in range(n_q):
        s = qi * q_size
        e = s + q_size
        h_q   = np.array(human[s:e])
        cl_q  = np.array(cllm_scores[s:e])
        c1f_q = np.array(concept_scores[s:e])
        c5f_q = np.array(holistic_scores[s:e])
        m_cl  = float(np.mean(np.abs(h_q - cl_q)))
        m_c1f = float(np.mean(np.abs(h_q - c1f_q)))
        m_c5f_q = float(np.mean(np.abs(h_q - c5f_q)))
        best = min(m_cl, m_c1f, m_c5f_q)
        winner = "C_LLM" if best == m_cl else ("C1_fix" if best == m_c1f else "C5_fix")
        if winner == "C5_fix":
            c5_wins += 1
        print(f"  Q{qi+1:>3}  {q_size:>4}  {m_cl:>8.4f}  {m_c1f:>8.4f}  {m_c5f_q:>8.4f}  {winner:>8}")
        q_breakdown.append({"q": qi+1, "c_llm": m_cl, "c1_fix": m_c1f, "c5_fix": m_c5f_q, "winner": winner})
    print(f"\n  C5_fix wins {c5_wins}/{n_q} questions")

    # ── LaTeX output ─────────────────────────────────────────────────────────────
    latex = generate_latex(all_configs, metric_map, human, n)
    if do_latex:
        print(f"\n{'='*76}")
        print("  LaTeX TABLE")
        print(f"{'='*76}\n")
        print(latex)

    # ── Save output ──────────────────────────────────────────────────────────────
    out_path = os.path.join(DATA_DIR, "offline_eval_results.json")
    result_data = {
        "n_samples": n,
        "configs": {
            cid: {"r": m["r"], "mae": m["mae"], "rmse": m["rmse"], "qwk": m["qwk"]}
            for cid, _, m, _ in all_configs
        },
        "core_claim": {
            "c5_fix_vs_c_llm_mae_delta": delta_mae,
            "c5_fix_vs_c_llm_mae_pct": pct_mae,
            "c5_fix_vs_c_llm_r_delta": delta_r,
            "c5_fix_vs_c_llm_rmse_delta": delta_rmse,
        },
        "significance": {label: sig for label, sig in sig_results.items()},
        "per_question": q_breakdown,
        "latex": latex,
    }
    with open(out_path, "w") as f:
        json.dump(result_data, f, indent=2)
    print(f"\n  Results saved → {out_path}")

    # ── Verdict ──────────────────────────────────────────────────────────────────
    print(f"\n{'='*76}")
    print("  VERDICT")
    print(f"{'='*76}\n")

    if m_c5f["mae"] < m_clm["mae"] and m_c5f["r"] > m_clm["r"]:
        print(f"  ✅ ConceptGrade (C5_fix) BEATS pure LLM baseline (C_LLM):")
        print(f"     MAE  {m_clm['mae']:.4f} → {m_c5f['mae']:.4f}  ({pct_mae:+.1f}% error reduction)")
        print(f"     r    {m_clm['r']:.4f} → {m_c5f['r']:.4f}  ({pct_r:+.1f}% correlation gain)")
        print(f"     Wilcoxon p={sig_results['C5_fix vs C_LLM']['p_value']:.4f}  "
              f"({'significant' if sig_results['C5_fix vs C_LLM']['significant'] else 'n.s.'})")
    else:
        print(f"  ⚠  ConceptGrade does NOT beat C_LLM on all metrics.")

    print(f"\n  Data sources:")
    print(f"    {CHECKPOINT}")
    print(f"    {DUAL_SCORES}\n")


if __name__ == "__main__":
    sys.path.insert(0, BASE_DIR)
    main()
