"""
Generate a SINGLE Gemini prompt that returns BOTH ablation scores at once.

More efficient than two separate prompts — one Gemini session, two score sets.

For each sample, Gemini grades TWICE:
  - concepts_only: using matched concepts + chain coverage (no SOLO/Bloom)
  - taxonomy_only: using SOLO + Bloom level (no concept lists)

Output: /tmp/ablation_dual_ALL.txt
        /tmp/ablation_dual_scores_response.json  (to be filled after Gemini run)
"""

import json, os

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
INTERMEDIATES = os.path.join(BASE_DIR, "data", "ablation_intermediates_gemini_flash_latest.json")

SYSTEM = """You are an expert Computer Science educator. For each student answer below,
you must provide TWO independent scores from 0.0 to 5.0 using 0.25 increments.

SCORING GUIDE (same for both scores):
- 5.0: ≥90% of reference content correctly explained
- 4.5: ≥80%, only minor omissions
- 4.0: ≥70%, one clear gap
- 3.5: ≥60% with reasonable depth
- 3.0: ~50%
- 2.5: 30–50%, substantial content missing
- 2.0: 1–2 key ideas correct, most missing
- 1.5: partial understanding of 1 concept, no mechanism
- 1.0: aware of topic, no accurate explanations
- 0.5: single marginally relevant statement
- 0.0: no relevant content

SCORE A — concepts_only:
  Use: question + reference + student answer + KG matched concepts + chain coverage
  Ignore: SOLO level, Bloom's level, misconceptions

SCORE B — taxonomy_only:
  Use: question + reference + student answer + SOLO cognitive level + Bloom's level
  Ignore: matched concepts, chain coverage, misconceptions

Return ONLY valid JSON (no markdown):
{
  "scores": {
    "<id>": {"concepts_only": X.X, "taxonomy_only": X.X},
    ...
  }
}"""


def build_sample(idx, entry):
    comp     = entry.get("comparison", {})
    analysis = comp.get("analysis", {})
    scores   = comp.get("scores", {})
    blooms   = entry.get("blooms") or {}
    solo     = entry.get("solo")   or {}

    matched  = analysis.get("matched_concepts", [])
    chain    = scores.get("chain_coverage", 0.0)

    covered  = ", ".join(matched[:12]) if matched else "none"
    chain_s  = f"{chain:.0%}" if chain else "0%"
    bl_lbl   = blooms.get("label", "Remember")
    bl_lv    = blooms.get("level", 1)
    sl_lbl   = solo.get("label", "Prestructural")
    sl_lv    = solo.get("level", 1)

    return (
        f"--- SAMPLE {idx} ---\n"
        f"QUESTION: {entry['question']}\n\n"
        f"REFERENCE: {entry['reference_answer']}\n\n"
        f"STUDENT: {entry['student_answer']}\n\n"
        f"[Score A evidence — concepts]  matched: {covered}  chain: {chain_s}\n"
        f"[Score B evidence — taxonomy]  SOLO: {sl_lbl} ({sl_lv}/5)  Bloom: {bl_lbl} ({bl_lv}/6)\n"
        f"  (SOLO: 1=Prestructural 2=Unistructural 3=Multistructural 4=Relational 5=Extended)"
    )


def main():
    with open(INTERMEDIATES) as f:
        ints = json.load(f)

    n = 120
    entries = [(i, ints[str(i)]) for i in range(n)]

    header = (
        f"{SYSTEM}\n\n"
        f"Grade the following {n} student answers (IDs 0–{n-1}).\n"
        f"For each: provide concepts_only score AND taxonomy_only score.\n\n"
        f"{'='*70}\n\n"
    )
    body = "\n\n".join(build_sample(idx, entry) for idx, entry in entries)
    footer = (
        f"\n\n{'='*70}\n"
        f"Grade all {n} samples. Return ONLY the JSON with both scores per sample."
    )

    content = header + body + footer
    out_path = "/tmp/ablation_dual_ALL.txt"
    with open(out_path, "w") as f:
        f.write(content)

    print(f"Dual ablation prompt: {out_path}  ({len(content):,} chars)")
    print(f"\nAfter Gemini Pro responds, save response as:")
    print(f"  /tmp/ablation_dual_response.json")
    print(f"\nThen run score_ablation_dual.py to compute all metrics.\n")

    # Write scorer
    scorer = '''"""Score dual ablation response from Gemini."""
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

    print("\\nKG COMPONENT ABLATION — DUAL SCORING")
    print("=" * 65)
    print(f"  {\'System\':<38} {\'MAE\':>7}  {\'r\':>7}  {\'ΔMAE vs C_LLM\'}")
    print(f"  {\'─\'*38} {\'─\'*7}  {\'─\'*7}  {\'─\'*15}")
    base_mae = float(np.mean(np.abs(h - cllm)))
    for name, scores in configs.items():
        mae = float(np.mean(np.abs(h - scores)))
        r, _ = pearsonr(h, scores)
        delta = mae - base_mae
        mark = " ← BEST" if mae == min(float(np.mean(np.abs(h-sc))) for sc in configs.values()) else ""
        print(f"  {name:<38} {mae:>7.4f}  {r:>7.4f}  {delta:>+15.4f}{mark}")

    mae_c = float(np.mean(np.abs(h - concepts_sc)))
    mae_t = float(np.mean(np.abs(h - taxonomy_sc)))
    print("\\n  INTERPRETATION:")
    if mae_t < mae_c:
        print(f"  → TAXONOMY-ONLY ({mae_t:.4f}) < CONCEPTS-ONLY ({mae_c:.4f})")
        print("    SOLO/Bloom taxonomy is the stronger KG driver.")
        print("    ConceptGrade\\'s cognitive depth analysis is more valuable than concept matching.")
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
    print(f"\\n  Results saved: {out}")

if __name__ == "__main__":
    main()
'''
    scorer_path = os.path.join(BASE_DIR, "score_ablation_dual.py")
    with open(scorer_path, "w") as f:
        f.write(scorer)
    print(f"Scorer: {scorer_path}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, BASE_DIR)
    main()
