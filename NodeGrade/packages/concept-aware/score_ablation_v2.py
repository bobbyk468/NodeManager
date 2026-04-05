"""
Score the v2 component ablation responses.

Expects:
  /tmp/ablation_concepts_v2_response.json   — {"scores": {"0": X.X, ...}}
  /tmp/ablation_taxonomy_v2_response.json   — {"scores": {"0": X.X, ...}}

Produces:
  data/ablation_component_results.json
  (also prints full comparison table and updates paper_latex_tables.tex)
"""

import json, os, sys
import numpy as np
from scipy.stats import pearsonr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA     = os.path.join(BASE_DIR, "data")


def load_scores(path, n=120):
    with open(path) as f:
        raw = json.load(f)
    sc = raw.get("scores", raw)
    return np.array([float(sc[str(i)]) for i in range(n)])


def metrics(h, pred):
    mae  = float(np.mean(np.abs(h - pred)))
    rmse = float(np.sqrt(np.mean((h - pred)**2)))
    r, _ = pearsonr(h, pred)
    bias = float(np.mean(pred - h))
    return dict(mae=mae, rmse=rmse, r=float(r), bias=bias, max_pred=float(pred.max()))


def main():
    # Load baseline data
    with open(os.path.join(DATA, "ablation_checkpoint_gemini_flash_latest.json")) as f:
        ckpt = json.load(f)
    with open(os.path.join(DATA, "gemini_kg_dual_scores.json")) as f:
        dual = json.load(f)

    n = 120
    h     = np.array(ckpt["human_scores"])
    cllm  = np.array(ckpt["scores"]["C_LLM"])
    c5fix = np.array([dual["holistic_scores"][str(i)] for i in range(n)])

    # Check which v2 files are available
    con_path = "/tmp/ablation_concepts_v2_response.json"
    tax_path = "/tmp/ablation_taxonomy_v2_response.json"

    missing = []
    if not os.path.exists(con_path):
        missing.append(con_path)
    if not os.path.exists(tax_path):
        missing.append(tax_path)
    if missing:
        print("Missing response files:")
        for m in missing:
            print(f"  {m}")
        print("\nRun Gemini with the prompts first, then save responses to those paths.")
        sys.exit(1)

    con_sc = load_scores(con_path, n)
    tax_sc = load_scores(tax_path, n)

    # Metrics
    m_cllm = metrics(h, cllm)
    m_con  = metrics(h, con_sc)
    m_tax  = metrics(h, tax_sc)
    m_c5   = metrics(h, c5fix)

    configs = [
        ("C5_fix (full KG + answer)",       m_c5),
        ("C_LLM (answer only, no KG)",       m_cllm),
        ("taxonomy_only (SOLO+Bloom+ans)",   m_tax),
        ("concepts_only (match+chain+ans)",  m_con),
    ]

    base_mae = m_cllm["mae"]
    base_r   = m_cllm["r"]

    print("\nKG COMPONENT ABLATION v2 — FIXED CALIBRATION")
    print("=" * 75)
    print(f"  {'System':<38} {'MAE':>7}  {'r':>7}  {'bias':>7}  {'ΔMAE':>8}")
    print(f"  {'─'*38} {'─'*7}  {'─'*7}  {'─'*7}  {'─'*8}")
    for name, m in configs:
        delta = m["mae"] - base_mae
        mark = " ← BEST" if m["mae"] == min(c["mae"] for _, c in configs) else ""
        print(f"  {name:<38} {m['mae']:>7.4f}  {m['r']:>7.4f}  {m['bias']:>+7.3f}  {delta:>+8.4f}{mark}")

    print()
    if m_tax["mae"] < m_con["mae"]:
        print(f"  → TAXONOMY-ONLY ({m_tax['mae']:.4f}) < CONCEPTS-ONLY ({m_con['mae']:.4f})")
        print("    SOLO/Bloom taxonomy is the stronger KG driver.")
        key = "taxonomy_stronger"
    else:
        print(f"  → CONCEPTS-ONLY ({m_con['mae']:.4f}) < TAXONOMY-ONLY ({m_tax['mae']:.4f})")
        print("    Concept coverage matching is the stronger KG driver.")
        key = "concepts_stronger"

    # Save results
    results = {
        "version": "v2_fixed",
        "n": n,
        "c5_fix":       m_c5,
        "c_llm":        m_cllm,
        "taxonomy_only": m_tax,
        "concepts_only": m_con,
        "key_finding":  key,
        "correlation_ladder": {
            "C5_fix":        m_c5["r"],
            "C_LLM":         m_cllm["r"],
            "taxonomy_only": m_tax["r"],
            "concepts_only": m_con["r"],
        },
        "interpretation": {
            "taxonomy_vs_concepts": f"taxonomy_only MAE={m_tax['mae']:.4f} r={m_tax['r']:.4f} vs concepts_only MAE={m_con['mae']:.4f} r={m_con['r']:.4f}",
            "partial_kg_effect": (
                "Both ablations fall below C_LLM performance — partial KG evidence disrupts calibration"
                if m_tax["r"] < m_cllm["r"] and m_con["r"] < m_cllm["r"]
                else "Component ablation beats or matches C_LLM baseline"
            ),
        }
    }

    out_path = os.path.join(DATA, "ablation_component_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {out_path}")

    # Generate LaTeX table for the component ablation
    latex = generate_latex(configs, base_mae, key, m_c5, m_cllm)
    tex_path = os.path.join(DATA, "paper_component_ablation.tex")
    with open(tex_path, "w") as f:
        f.write(latex)
    print(f"  LaTeX table:  {tex_path}")


def generate_latex(configs, base_mae, key, m_c5, m_cllm):
    rows = []
    sys_names = {
        "C5_fix (full KG + answer)":       (r"$C_5^{*}$",   r"\textbf{ConceptGrade} (full KG + answer)"),
        "C_LLM (answer only, no KG)":       (r"$C_{\text{LLM}}$", r"Pure LLM (answer only, no KG)"),
        "taxonomy_only (SOLO+Bloom+ans)":   (r"$C_{\text{tax}}$", r"Taxonomy-only (SOLO + Bloom's + answer)"),
        "concepts_only (match+chain+ans)":  (r"$C_{\text{con}}$", r"Concepts-only (matched concepts + chain + answer)"),
    }
    for name, m in configs:
        sid, sdesc = sys_names.get(name, (name, name))
        delta = m["mae"] - base_mae
        bold_open  = r"\textbf{" if m["mae"] == min(c["mae"] for _, c in configs) else ""
        bold_close = "}" if bold_open else ""
        delta_s = f"{delta:+.4f}" if name != "C_LLM (answer only, no KG)" else "--"
        rows.append(
            f"{sid} & {sdesc} & {bold_open}{m['r']:.4f}{bold_close} & "
            f"{bold_open}{m['mae']:.4f}{bold_close} & {delta_s} & {m['bias']:+.4f} \\\\"
        )

    finding = (
        r"$C_{\text{tax}}$ (SOLO/Bloom) provides stronger rank signal ($r=%.4f$) "
        r"than $C_{\text{con}}$ (concept matching, $r=%.4f$)." % (
            next(m["r"] for n, m in configs if "taxonomy" in n),
            next(m["r"] for n, m in configs if "concepts" in n),
        )
    )

    return (
        "% Table: KG Component Ablation (v2 — fixed calibration)\n"
        r"\begin{table}[ht]\centering" + "\n"
        r"\caption{KG component ablation on Mohler et al.\ (2011) ($n=120$). " + "\n"
        r"$C_{\text{con}}$: LLM graded with student answer + KG matched concepts + chain coverage (no SOLO/Bloom). " + "\n"
        r"$C_{\text{tax}}$: LLM graded with student answer + SOLO cognitive level + Bloom's level (no concept lists). " + "\n"
        r"$C_5^{*}$: full ConceptGrade (all KG evidence). " + "\n"
        r"$\Delta$MAE relative to $C_{\text{LLM}}$. Bold = best.}" + "\n"
        r"\label{tab:component_ablation}" + "\n"
        r"\begin{tabular}{@{}llrrrr@{}}\toprule" + "\n"
        r"\textbf{ID} & \textbf{System} & \textbf{$r$} & \textbf{MAE} & \textbf{$\Delta$MAE} & \textbf{Bias} \\\midrule" + "\n"
        + "\n".join(rows) + "\n"
        r"\bottomrule" + "\n"
        r"\end{tabular}" + "\n"
        r"\end{table}"
    )


if __name__ == "__main__":
    sys.path.insert(0, BASE_DIR)
    main()
