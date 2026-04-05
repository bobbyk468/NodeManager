"""
Score KG component ablation responses from Gemini.

After collecting Gemini responses for concepts_only and taxonomy_only batches,
run this script to compute MAE and compare all conditions.

Expected input files:
  /tmp/ablation_concepts_only_scores_1.json ... _5.json
  /tmp/ablation_taxonomy_only_scores_1.json ... _5.json

Usage:
    python3 score_ablation_responses.py
"""
import json, os, numpy as np
from scipy.stats import pearsonr

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_scores_from_files(prefix, n_batches=5):
    scores = {}
    for i in range(1, n_batches+1):
        path = f"/tmp/ablation_{prefix}_scores_{i}.json"
        if not os.path.exists(path):
            print(f"  Missing: {path}")
            continue
        with open(path) as f:
            data = json.load(f)
        batch_scores = data.get("scores", data)
        for k, v in batch_scores.items():
            if isinstance(v, dict):
                scores[int(k)] = float(v.get("verified_score", 0))
            else:
                scores[int(k)] = float(v)
    return scores

def main():
    with open(os.path.join(DATA_DIR, "ablation_checkpoint_gemini_flash_latest.json")) as f:
        ckpt = json.load(f)
    with open(os.path.join(DATA_DIR, "gemini_kg_dual_scores.json")) as f:
        dual = json.load(f)

    n = 120
    human = ckpt["human_scores"]
    cllm  = ckpt["scores"]["C_LLM"]
    c5fix = [dual["holistic_scores"][str(i)] for i in range(n)]

    h = np.array(human)

    configs = {
        "C_LLM (baseline)":        np.array(cllm),
        "C5_fix (full KG+answer)": np.array(c5fix),
    }

    # Load ablation scores
    for variant, label in [
        ("concepts_only", "Concepts-only ablation"),
        ("taxonomy_only",  "Taxonomy-only ablation"),
    ]:
        sc_map = load_scores_from_files(variant)
        if len(sc_map) == n:
            sc = np.array([sc_map[i] for i in range(n)])
            configs[label] = sc
        else:
            print(f"  {label}: only {len(sc_map)}/{n} scores found — skipping")

    print("\nKG Component Ablation Results")
    print("=" * 60)
    print(f"  {'System':<35} {'MAE':>7}  {'r':>7}  {'vs C_LLM'}")
    print(f"  {'─'*35} {'─'*7}  {'─'*7}  {'─'*10}")
    baseline_mae = float(np.mean(np.abs(h - np.array(cllm))))
    for name, scores in configs.items():
        mae = float(np.mean(np.abs(h - scores)))
        r, _ = pearsonr(h, scores)
        delta = mae - baseline_mae
        print(f"  {name:<35} {mae:>7.4f}  {r:>7.4f}  {delta:>+10.4f}")

if __name__ == "__main__":
    main()
