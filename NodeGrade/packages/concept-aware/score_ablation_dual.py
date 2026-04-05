"""Score dual ablation response from Gemini."""
import json, os, numpy as np
from scipy.stats import pearsonr

DATA = os.path.join(os.path.dirname(__file__), "data")

def main():
    with open(os.path.join(DATA, "ablation_checkpoint_gemini_flash_latest.json")) as f:
        ckpt = json.load(f)
    with open(os.path.join(DATA, "gemini_kg_dual_scores.json")) as f:
        dual = json.load(f)

    n = 120
    human = ckpt["human_scores"]
    h = np.array(human)
    cllm  = np.array(ckpt["scores"]["C_LLM"])
    c5fix = np.array([dual["holistic_scores"][str(i)] for i in range(n)])

    resp_path = "/tmp/ablation_dual_response.json"
    if not os.path.exists(resp_path):
        print(f"Missing: {resp_path}")
        return

    with open(resp_path) as f:
        resp = json.load(f)

    sc = resp.get("scores", resp)
    concepts_sc = np.array([float(sc[str(i)]["concepts_only"]) for i in range(n)])
    taxonomy_sc = np.array([float(sc[str(i)]["taxonomy_only"]) for i in range(n)])

    configs = {
        "C_LLM (no KG, baseline)":          cllm,
        "Concepts-only (match+chain+ans)":   concepts_sc,
        "Taxonomy-only (SOLO+Bloom+ans)":    taxonomy_sc,
        "C5_fix (full KG + answer)":         c5fix,
    }

    print("\nKG COMPONENT ABLATION — DUAL SCORING")
    print("=" * 65)
    print(f"  {'System':<38} {'MAE':>7}  {'r':>7}  {'ΔMAE vs C_LLM'}")
    print(f"  {'─'*38} {'─'*7}  {'─'*7}  {'─'*15}")
    base_mae = float(np.mean(np.abs(h - cllm)))
    for name, scores in configs.items():
        mae = float(np.mean(np.abs(h - scores)))
        r, _ = pearsonr(h, scores)
        delta = mae - base_mae
        mark = " ← BEST" if mae == min(float(np.mean(np.abs(h-sc))) for sc in configs.values()) else ""
        print(f"  {name:<38} {mae:>7.4f}  {r:>7.4f}  {delta:>+15.4f}{mark}")

    mae_c = float(np.mean(np.abs(h - concepts_sc)))
    mae_t = float(np.mean(np.abs(h - taxonomy_sc)))
    print("\n  INTERPRETATION:")
    if mae_t < mae_c:
        print(f"  → TAXONOMY-ONLY ({mae_t:.4f}) < CONCEPTS-ONLY ({mae_c:.4f})")
        print("    SOLO/Bloom taxonomy is the stronger KG driver.")
        print("    ConceptGrade\'s cognitive depth analysis is more valuable than concept matching.")
    else:
        print(f"  → CONCEPTS-ONLY ({mae_c:.4f}) < TAXONOMY-ONLY ({mae_t:.4f})")
        print("    Concept coverage matching is the stronger KG driver.")
        print("    KG concept lists provide more discriminating evidence than taxonomy alone.")

    # Save
    results = {
        "concepts_only_mae": mae_c,
        "taxonomy_only_mae": mae_t,
        "c_llm_mae": base_mae,
        "c5_fix_mae": float(np.mean(np.abs(h - c5fix))),
        "key_finding": "taxonomy_stronger" if mae_t < mae_c else "concepts_stronger",
    }
    out = os.path.join(DATA, "ablation_dual_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {out}")

if __name__ == "__main__":
    main()
