"""Score ablation responses from single-file Gemini runs."""
import json, os, numpy as np
from scipy.stats import pearsonr

DATA = os.path.join(os.path.dirname(__file__), "data")

def load(path):
    with open(path) as f:
        data = json.load(f)
    sc = data.get("scores", data)
    return {int(k): float(v["verified_score"] if isinstance(v,dict) else v) for k,v in sc.items()}

def main():
    with open(os.path.join(DATA, "ablation_checkpoint_gemini_flash_latest.json")) as f:
        ckpt = json.load(f)
    with open(os.path.join(DATA, "gemini_kg_dual_scores.json")) as f:
        dual = json.load(f)

    n = 120
    human = ckpt["human_scores"]
    h = np.array(human)

    baselines = {
        "C_LLM (no KG)": np.array(ckpt["scores"]["C_LLM"]),
        "C5_fix (full KG+answer)": np.array([dual["holistic_scores"][str(i)] for i in range(n)]),
    }

    ablations = {}
    for variant, label in [
        ("concepts_only", "Concepts-only KG (no taxonomy)"),
        ("taxonomy_only",  "Taxonomy-only KG (no concepts)"),
    ]:
        path = f"/tmp/ablation_{variant}_response.json"
        if os.path.exists(path):
            sc_map = load(path)
            if len(sc_map) == n:
                ablations[label] = np.array([sc_map[i] for i in range(n)])
                print(f"  Loaded {label}: {len(sc_map)} scores")
            else:
                print(f"  {label}: only {len(sc_map)} scores, expected {n}")
        else:
            print(f"  Missing: {path}")

    print("\nKG COMPONENT ABLATION RESULTS")
    print("=" * 65)
    print(f"  {'System':<38} {'MAE':>7}  {'r':>7}  {'ΔMAE vs C_LLM'}")
    print(f"  {'─'*38} {'─'*7}  {'─'*7}  {'─'*15}")

    all_configs = {**baselines, **ablations}
    baseline_mae = float(np.mean(np.abs(h - baselines["C_LLM (no KG)"])))
    for name, scores in all_configs.items():
        mae = float(np.mean(np.abs(h - scores)))
        r, _ = pearsonr(h, scores)
        delta = mae - baseline_mae
        marker = " ← BEST" if mae == min(float(np.mean(np.abs(h-sc))) for sc in all_configs.values()) else ""
        print(f"  {name:<38} {mae:>7.4f}  {r:>7.4f}  {delta:>+15.4f}{marker}")

    print("\n  INTERPRETATION:")
    if "Taxonomy-only KG (no concepts)" in ablations and "Concepts-only KG (no taxonomy)" in ablations:
        mae_t = float(np.mean(np.abs(h - ablations["Taxonomy-only KG (no concepts)"])))
        mae_c = float(np.mean(np.abs(h - ablations["Concepts-only KG (no taxonomy)"])))
        if mae_t < mae_c:
            print("  → SOLO/Bloom taxonomy is the stronger KG driver (lower MAE than concepts-only)")
            print("    This validates ConceptGrade\'s taxonomic design beyond simple keyword matching.")
        else:
            print("  → Concept coverage matching is the stronger KG driver")
            print("    KG concept lists provide more discriminating information than taxonomy alone.")

if __name__ == "__main__":
    main()
