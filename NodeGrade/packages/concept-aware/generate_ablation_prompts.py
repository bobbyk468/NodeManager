"""
Generate Gemini prompts for KG component ablation study.

Two ablation variants (both use student answer + partial KG evidence):

  Variant A — KG Concepts Only (no taxonomy):
    Evidence: matched concepts + missing concepts + chain coverage
    REMOVES: SOLO level, Bloom's level, misconception details
    Tests whether CONCEPT COVERAGE alone drives the gain.

  Variant B — KG Taxonomy Only (no concept lists):
    Evidence: SOLO level + Bloom's level
    REMOVES: matched concepts, missing concepts, chain coverage, misconceptions
    Tests whether COGNITIVE DEPTH TAXONOMY alone drives the gain.

Expected outcome (from offline correlation analysis):
  Full KG + answer (C5_fix): MAE=0.2229  [BEST]
  Taxonomy-only ablation:    MAE=?        [Expected ~0.25, taxonomy r=0.30]
  Concepts-only ablation:    MAE=?        [Expected ~0.27, concepts r=0.11]
  No KG (C_LLM):             MAE=0.3300

If taxonomy > concepts: SOLO/Bloom is the key KG driver (supports taxonomic design)
If concepts > taxonomy: coverage matching is the key driver

Usage:
    python3 generate_ablation_prompts.py

Output files (paste each into Gemini Pro, collect JSON response, save):
    /tmp/ablation_concepts_only_batch_N.txt  (5 files, 24 samples each)
    /tmp/ablation_taxonomy_only_batch_N.txt  (5 files, 24 samples each)
"""

from __future__ import annotations

import json
import os

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
INTERMEDIATES = os.path.join(BASE_DIR, "data", "ablation_intermediates_gemini_flash_latest.json")
CHECKPOINT    = os.path.join(BASE_DIR, "data", "ablation_checkpoint_gemini_flash_latest.json")

SYSTEM_PROMPT = """You are an expert Computer Science educator grading a student's short answer.

Your task: Compare the student answer to the reference answer and assign a score from 0.0 to 5.0.

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

IMPORTANT:
- Score what the student got RIGHT; what is MISSING prevents reaching a higher band.
- Misconceptions about core mechanisms lower the score; missing vocabulary alone does not.
- Students often express correct understanding in different words — credit the understanding.
- Use 0.25 increments.

Return ONLY valid JSON."""


def build_concepts_only_prompt(entry: dict) -> str:
    """KG evidence: matched concepts + chain coverage. No SOLO/Bloom/misconceptions."""
    comp     = entry.get("comparison", {})
    analysis = comp.get("analysis", {})
    scores   = comp.get("scores", {})

    matched  = analysis.get("matched_concepts", [])
    chain    = scores.get("chain_coverage", 0.0)

    covered_str  = ", ".join(matched[:12]) if matched else "none identified"
    chain_str    = f"{chain:.0%} of causal concept chains covered" if chain else "not computed"

    return (
        f"QUESTION: {entry['question']}\n\n"
        f"REFERENCE ANSWER (expert answer — defines 5.0):\n{entry['reference_answer']}\n\n"
        f"STUDENT ANSWER:\n{entry['student_answer']}\n\n"
        f"KNOWLEDGE GRAPH EVIDENCE (concept coverage only):\n"
        f"- Concepts the student demonstrated: {covered_str}\n"
        f"- Causal chain coverage: {chain_str}\n\n"
        f"Grade based on how well the student's concepts match the reference. "
        f"Return ONLY valid JSON:\n"
        f"{{\"verified_score\": <float 0.0-5.0 in 0.25 increments>}}"
    )


def build_taxonomy_only_prompt(entry: dict) -> str:
    """KG evidence: SOLO level + Bloom's level only. No concept lists."""
    blooms = entry.get("blooms") or {}
    solo   = entry.get("solo")   or {}

    bloom_label = blooms.get("label", "Remember")
    bloom_level = blooms.get("level", 1)
    solo_label  = solo.get("label", "Prestructural")
    solo_level  = solo.get("level", 1)

    return (
        f"QUESTION: {entry['question']}\n\n"
        f"REFERENCE ANSWER (expert answer — defines 5.0):\n{entry['reference_answer']}\n\n"
        f"STUDENT ANSWER:\n{entry['student_answer']}\n\n"
        f"COGNITIVE TAXONOMY EVIDENCE:\n"
        f"- Bloom's cognitive level: {bloom_label} (level {bloom_level}/6)\n"
        f"- SOLO structural level: {solo_label} (level {solo_level}/5)\n\n"
        f"SOLO taxonomy: 1=Prestructural (no relevant), 2=Unistructural (one concept), "
        f"3=Multistructural (several concepts), 4=Relational (integrated understanding), "
        f"5=Extended Abstract (generalises beyond task).\n\n"
        f"Grade based on the student's demonstrated cognitive depth. "
        f"Return ONLY valid JSON:\n"
        f"{{\"verified_score\": <float 0.0-5.0 in 0.25 increments>}}"
    )


def generate_batch(
    entries: list[tuple[int, dict]],
    prompt_builder,
    variant_name: str,
    batch_num: int,
    total_batches: int,
) -> str:
    """Build a single batch prompt with all samples in it."""
    lines = [
        SYSTEM_PROMPT,
        "",
        f"Grade the following {len(entries)} student answers (IDs {entries[0][0]}–{entries[-1][0]}).",
        "",
        f"Return a single JSON object:",
        "{",
        f'  "scores": {{',
        f'    "{entries[0][0]}": {{"verified_score": X.X}}, ...',
        "  }",
        "}",
        "",
        "=" * 70,
        "",
    ]
    for idx, entry in entries:
        lines.append(f"--- SAMPLE ID: {idx} ---")
        lines.append(build_concepts_only_prompt(entry) if variant_name == "concepts_only"
                     else build_taxonomy_only_prompt(entry))
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Grade all {len(entries)} samples above. Use 0.25 increments. Return only the JSON.")
    return "\n".join(lines)


def main():
    with open(INTERMEDIATES) as f:
        ints = json.load(f)
    with open(CHECKPOINT) as f:
        ckpt = json.load(f)

    n = 120
    entries = [(i, ints[str(i)]) for i in range(n)]

    batch_size = 24
    batches = [entries[i:i+batch_size] for i in range(0, n, batch_size)]
    n_batches = len(batches)

    print(f"Generating KG component ablation prompts...")
    print(f"  Samples: {n}")
    print(f"  Batches: {n_batches} × {batch_size} samples each")

    for variant in ["concepts_only", "taxonomy_only"]:
        print(f"\n  Variant: {variant}")
        for bi, batch in enumerate(batches):
            prompt = generate_batch(batch, None, variant, bi+1, n_batches)
            out_path = f"/tmp/ablation_{variant}_batch_{bi+1}_of_{n_batches}.txt"
            with open(out_path, "w") as f:
                f.write(prompt)
            print(f"    Batch {bi+1}/{n_batches}: {out_path}  ({len(prompt):,} chars)")

    print(f"""
  ─────────────────────────────────────────────────────────────────────
  NEXT STEPS:
  1. Paste each /tmp/ablation_concepts_only_batch_N.txt into Gemini Pro
  2. Save the JSON response to /tmp/ablation_concepts_only_scores_N.json
  3. Do the same for taxonomy_only batches
  4. Run: python3 score_ablation_responses.py
     to compute MAE and compare all conditions

  EXPECTED RESULTS (from offline correlation analysis):
    Full KG + answer (C5_fix):  MAE = 0.2229  [current best]
    Taxonomy-only + answer:     MAE ≈ 0.25?   [SOLO r=0.30 predicts this]
    Concepts-only + answer:     MAE ≈ 0.27?   [n_matched r=0.11 → less impact]
    No KG (C_LLM baseline):     MAE = 0.3300

  INTERPRETATION:
    If taxonomy-only MAE < concepts-only MAE:
      → SOLO/Bloom's taxonomy is the key KG driver (not keyword matching)
      → Supports ConceptGrade's multi-layer design philosophy
    If concepts-only MAE < taxonomy-only MAE:
      → Concept coverage is the key driver (taxonomy adds less)
  ─────────────────────────────────────────────────────────────────────
""")

    # Also generate the scoring script for when responses come in
    _generate_scoring_script()
    print("  Scoring script: score_ablation_responses.py")


def _generate_scoring_script():
    script = '''"""
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

    print("\\nKG Component Ablation Results")
    print("=" * 60)
    print(f"  {\'System\':<35} {\'MAE\':>7}  {\'r\':>7}  {\'vs C_LLM\'}")
    print(f"  {\'─\'*35} {\'─\'*7}  {\'─\'*7}  {\'─\'*10}")
    baseline_mae = float(np.mean(np.abs(h - np.array(cllm))))
    for name, scores in configs.items():
        mae = float(np.mean(np.abs(h - scores)))
        r, _ = pearsonr(h, scores)
        delta = mae - baseline_mae
        print(f"  {name:<35} {mae:>7.4f}  {r:>7.4f}  {delta:>+10.4f}")

if __name__ == "__main__":
    main()
'''
    with open(os.path.join(os.path.dirname(__file__), "score_ablation_responses.py"), "w") as f:
        f.write(script)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, BASE_DIR)
    main()
