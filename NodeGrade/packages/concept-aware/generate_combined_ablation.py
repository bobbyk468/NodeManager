"""
Generate combined single-file ablation prompts for Gemini Pro.

Produces ONE file per variant (all 120 samples) — easier to paste.
User pastes each file into Gemini Pro and gets JSON back.

Output:
    /tmp/ablation_concepts_only_ALL.txt   (~115KB)
    /tmp/ablation_taxonomy_only_ALL.txt   (~130KB)
"""

import json, os

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
INTERMEDIATES = os.path.join(BASE_DIR, "data", "ablation_intermediates_gemini_flash_latest.json")

SYSTEM = """You are an expert Computer Science educator grading student short answers.

SCORING GUIDE — based on proportion of reference answer content correctly demonstrated:
- 5.0: Student correctly explains virtually all key ideas (≥90% of reference content)
- 4.5: Student correctly explains the great majority (≥80%); only very minor omissions
- 4.0: Student correctly explains most key ideas (≥70%); one clear gap
- 3.5: Student correctly explains a solid majority (≥60%) with reasonable depth
- 3.0: Student correctly explains about half the reference content (~50%)
- 2.5: Student correctly explains several key ideas (30–50%); substantial content still missing
- 2.0: Student correctly explains 1–2 key ideas accurately; most reference content missing
- 1.5: Student shows partial understanding of 1 concept but cannot explain mechanisms
- 1.0: Student shows awareness of the topic but no accurate explanations of mechanisms
- 0.5: Single marginally relevant statement; no explanation
- 0.0: No relevant content

IMPORTANT RULES:
- Score what the student got RIGHT; what is MISSING prevents reaching a higher band.
- Misconceptions about core mechanisms lower the score; missing vocabulary alone does not.
- Students often express correct understanding in different words — credit the understanding.
- Use 0.25 increments only."""


def sample_concepts_only(idx, entry):
    comp     = entry.get("comparison", {})
    analysis = comp.get("analysis", {})
    scores   = comp.get("scores", {})
    matched  = analysis.get("matched_concepts", [])
    chain    = scores.get("chain_coverage", 0.0)
    covered  = ", ".join(matched[:12]) if matched else "none identified"
    chain_s  = f"{chain:.0%} of causal chains" if chain else "not computed"
    return (
        f"--- SAMPLE ID: {idx} ---\n"
        f"QUESTION: {entry['question']}\n\n"
        f"REFERENCE ANSWER (defines 5.0):\n{entry['reference_answer']}\n\n"
        f"KG EVIDENCE (concepts only):\n"
        f"- Concepts demonstrated: {covered}\n"
        f"- Chain coverage: {chain_s}\n\n"
        f"STUDENT ANSWER:\n{entry['student_answer']}"
    )


def sample_taxonomy_only(idx, entry):
    blooms = entry.get("blooms") or {}
    solo   = entry.get("solo")   or {}
    bl     = blooms.get("label", "Remember")
    blv    = blooms.get("level", 1)
    sl     = solo.get("label",   "Prestructural")
    slv    = solo.get("level",   1)
    return (
        f"--- SAMPLE ID: {idx} ---\n"
        f"QUESTION: {entry['question']}\n\n"
        f"REFERENCE ANSWER (defines 5.0):\n{entry['reference_answer']}\n\n"
        f"KG EVIDENCE (taxonomy only):\n"
        f"- Bloom's level: {bl} ({blv}/6)\n"
        f"- SOLO level: {sl} ({slv}/5)  [1=Prestructural, 2=Unistructural, 3=Multistructural, 4=Relational]\n\n"
        f"STUDENT ANSWER:\n{entry['student_answer']}"
    )


def build_combined(entries, sample_fn, variant_label):
    n = len(entries)
    first_id, last_id = entries[0][0], entries[-1][0]
    header = (
        f"{SYSTEM}\n\n"
        f"Grade the following {n} student answers (IDs {first_id}–{last_id}).\n\n"
        f"Return a single JSON object:\n"
        f'{{\n  "scores": {{\n'
        f'    "{first_id}": {{"verified_score": X.X, "reason": "one sentence"}}, ...\n'
        f"  }}\n}}\n\n"
        f"{'='*70}\n\n"
    )
    body = "\n\n".join(sample_fn(idx, entry) for idx, entry in entries)
    footer = (
        f"\n\n{'='*70}\n"
        f"Grade all {n} samples above. Use 0.25 increments. Return only the JSON."
    )
    return header + body + footer


def main():
    with open(INTERMEDIATES) as f:
        ints = json.load(f)

    n = 120
    entries = [(i, ints[str(i)]) for i in range(n)]

    for variant, sample_fn, label in [
        ("concepts_only", sample_concepts_only, "KG Concepts Only (no taxonomy)"),
        ("taxonomy_only",  sample_taxonomy_only, "KG Taxonomy Only (no concept lists)"),
    ]:
        content = build_combined(entries, sample_fn, label)
        path = f"/tmp/ablation_{variant}_ALL.txt"
        with open(path, "w") as f:
            f.write(content)
        print(f"  {label}: {path}  ({len(content):,} chars)")

    print(f"""
After Gemini Pro responds to each file, save responses as:
  /tmp/ablation_concepts_only_response.json
  /tmp/ablation_taxonomy_only_response.json

Then run:
  python3 score_ablation_single.py
""")

    # Also write the single-response scoring script
    _write_single_scorer()
    print("  Scoring script: score_ablation_single.py")


def _write_single_scorer():
    code = '''"""Score ablation responses from single-file Gemini runs."""
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

    print("\\nKG COMPONENT ABLATION RESULTS")
    print("=" * 65)
    print(f"  {\'System\':<38} {\'MAE\':>7}  {\'r\':>7}  {\'ΔMAE vs C_LLM\'}")
    print(f"  {\'─\'*38} {\'─\'*7}  {\'─\'*7}  {\'─\'*15}")

    all_configs = {**baselines, **ablations}
    baseline_mae = float(np.mean(np.abs(h - baselines["C_LLM (no KG)"])))
    for name, scores in all_configs.items():
        mae = float(np.mean(np.abs(h - scores)))
        r, _ = pearsonr(h, scores)
        delta = mae - baseline_mae
        marker = " ← BEST" if mae == min(float(np.mean(np.abs(h-sc))) for sc in all_configs.values()) else ""
        print(f"  {name:<38} {mae:>7.4f}  {r:>7.4f}  {delta:>+15.4f}{marker}")

    print("\\n  INTERPRETATION:")
    if "Taxonomy-only KG (no concepts)" in ablations and "Concepts-only KG (no taxonomy)" in ablations:
        mae_t = float(np.mean(np.abs(h - ablations["Taxonomy-only KG (no concepts)"])))
        mae_c = float(np.mean(np.abs(h - ablations["Concepts-only KG (no taxonomy)"])))
        if mae_t < mae_c:
            print("  → SOLO/Bloom taxonomy is the stronger KG driver (lower MAE than concepts-only)")
            print("    This validates ConceptGrade\\'s taxonomic design beyond simple keyword matching.")
        else:
            print("  → Concept coverage matching is the stronger KG driver")
            print("    KG concept lists provide more discriminating information than taxonomy alone.")

if __name__ == "__main__":
    main()
'''
    with open(os.path.join(os.path.dirname(__file__), "score_ablation_single.py"), "w") as f:
        f.write(code)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, BASE_DIR)
    main()
