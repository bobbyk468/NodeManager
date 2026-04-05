"""
Generate Gemini re-scoring prompt for the 7 failing samples.

Samples: IDs 37, 42 (Q3/BST) and 112, 113, 116, 117, 118 (Q9/Big-O).

Uses the FULL C5_fix holistic format: student answer + SOLO/Bloom +
matched concepts + chain coverage + misconceptions — but with the UPDATED
chain coverage from data/ablation_intermediates_fixed.json.

Output: /tmp/rescore_targeted_7.txt

Usage:
    python3 generate_targeted_rescore.py
"""

from __future__ import annotations

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

FIXED_INTERMEDIATES = os.path.join(DATA_DIR, "ablation_intermediates_fixed.json")
CHECKPOINT = os.path.join(DATA_DIR, "ablation_checkpoint_gemini_flash_latest.json")
OUTPUT_PATH = "/tmp/rescore_targeted_7.txt"

FAILING_IDS = [37, 42, 112, 113, 114, 116, 117, 118]

SEP = "─" * 72

SYSTEM_PROMPT = """You are an expert Computer Science educator grading student short answers.

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
- Use 0.25 increments only.
- The KG evidence (matched concepts, chain coverage, SOLO/Bloom) reflects an expert
  knowledge graph analysis — use it alongside the student answer text."""


def build_holistic_sample(idx: int, entry: dict) -> str:
    """Build a full C5_fix holistic prompt for one sample."""
    comp = entry.get("comparison", {})
    analysis = comp.get("analysis", {})
    scores = comp.get("scores", {})
    blooms = entry.get("blooms") or {}
    solo = entry.get("solo") or {}
    misc = entry.get("misconceptions") or {}

    matched = analysis.get("matched_concepts", [])
    chain = scores.get("chain_coverage", 0.0)

    covered_str = ", ".join(matched) if matched else "none identified"
    chain_pct = f"{chain:.0%}"

    bloom_label = blooms.get("label", "Remember")
    bloom_level = blooms.get("level", 1)
    solo_label = solo.get("label", "Prestructural")
    solo_level = solo.get("level", 1)

    # Misconception summary
    if isinstance(misc, dict):
        misc_list = misc.get("misconceptions", []) or misc.get("detected", [])
    elif isinstance(misc, list):
        misc_list = misc
    else:
        misc_list = []
    misc_str = "; ".join(
        (m.get("description", "") or m.get("misconception", "") or str(m))
        for m in misc_list[:3]
    ) if misc_list else "none detected"

    return (
        f"--- SAMPLE ID: {idx} ---\n"
        f"QUESTION: {entry['question']}\n\n"
        f"REFERENCE ANSWER (expert — defines 5.0):\n{entry['reference_answer']}\n\n"
        f"FULL KG EVIDENCE:\n"
        f"- Concepts demonstrated: {covered_str}\n"
        f"- Causal chain coverage: {chain_pct} of concept chains covered\n"
        f"- Bloom's cognitive level: {bloom_label} ({bloom_level}/6)\n"
        f"- SOLO structural level: {solo_label} ({solo_level}/5)  "
        f"[1=Prestructural, 2=Unistructural, 3=Multistructural, 4=Relational, 5=Extended Abstract]\n"
        f"- Misconceptions: {misc_str}\n\n"
        f"STUDENT ANSWER:\n{entry['student_answer']}"
    )


def main() -> None:
    print(SEP)
    print("Generating Targeted Re-scoring Prompt for 7 Failing Samples")
    print(SEP)

    # Load fixed intermediates
    try:
        with open(FIXED_INTERMEDIATES) as f:
            ints = json.load(f)
        print(f"Loaded fixed intermediates: {FIXED_INTERMEDIATES}")
    except FileNotFoundError:
        print(f"WARNING: {FIXED_INTERMEDIATES} not found — falling back to augmented.")
        aug = os.path.join(DATA_DIR, "ablation_intermediates_augmented.json")
        try:
            with open(aug) as f:
                ints = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Neither fixed nor augmented intermediates found. Run augment_kg_concepts.py first.")
            return

    # Load current scores for context
    with open(CHECKPOINT) as f:
        ckpt = json.load(f)
    human_scores = ckpt["human_scores"]
    c5_scores = ckpt["scores"]["C5_fix"]
    cllm_scores = ckpt["scores"]["C_LLM"]

    print(f"\nFailing samples context:")
    print(f"{'ID':>4}  {'Q':3}  {'Human':6}  {'C5_fix':6}  {'C_LLM':6}  {'Concepts'}")
    print("─" * 72)
    for sid in FAILING_IDS:
        q_tag = "Q3" if sid < 100 else "Q9"
        entry = ints.get(str(sid), {})
        comp = entry.get("comparison", {})
        analysis = comp.get("analysis", {})
        matched = analysis.get("matched_concepts", [])
        scores = comp.get("scores", {})
        chain = scores.get("chain_coverage", 0.0)
        print(
            f"{sid:>4}  {q_tag:3}  {human_scores[sid]:6.2f}  "
            f"{c5_scores[sid]:6.2f}  {cllm_scores[sid]:6.2f}  "
            f"chain={chain:.0%} concepts={matched}"
        )

    # Build prompt
    entries = [(sid, ints[str(sid)]) for sid in FAILING_IDS if str(sid) in ints]
    n = len(entries)

    header = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Re-score the following {n} student answers (IDs: {', '.join(str(s) for s in FAILING_IDS)}).\n"
        f"These samples use UPDATED knowledge graph evidence (augmented concept matching\n"
        f"and fixed chain coverage from the expert KG).\n\n"
        f"Return a single JSON object:\n"
        f'{{\n  "scores": {{\n'
        f'    "{FAILING_IDS[0]}": {{"holistic_score": X.X, "reason": "one sentence"}},\n'
        f"    ...\n"
        f"  }}\n}}\n\n"
        f"{'='*70}\n\n"
    )
    body = "\n\n".join(build_holistic_sample(idx, entry) for idx, entry in entries)
    footer = (
        f"\n\n{'='*70}\n"
        f"Re-score all {n} samples using the full KG evidence above.\n"
        f"Use 0.25 increments. Return only the JSON with holistic_score per sample."
    )

    content = header + body + footer

    with open(OUTPUT_PATH, "w") as f:
        f.write(content)

    print(f"\nTargeted re-scoring prompt written → {OUTPUT_PATH}")
    print(f"Prompt length: {len(content):,} chars")
    print(SEP)
    print("\nAfter Gemini responds, compare holistic_score to human and C_LLM.")
    print("If |human - holistic| < |human - C_LLM|, C5_fix wins on those samples.")
    print(SEP)


if __name__ == "__main__":
    main()
