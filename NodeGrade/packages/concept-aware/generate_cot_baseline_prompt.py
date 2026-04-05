"""
Generate Chain-of-Thought (CoT) baseline prompt for Mohler 2011 (n=120).

The CoT prompt asks the LLM to:
  1. List CS concepts covered in the student answer
  2. Assess the cognitive depth (surface recall vs. integrated understanding)
  3. Identify misconceptions
  4. Assign a holistic score 0-5

This is the critical missing baseline: if CoT prompting alone matches C5_fix,
the KG provides no additional value. If C5_fix beats CoT, the KG is essential.

Output: /tmp/cot_baseline_prompt.txt

Usage:
    python3 generate_cot_baseline_prompt.py
    [send to Gemini, save response to /tmp/cot_baseline_response.json]
    python3 score_cot_baseline.py
"""

from __future__ import annotations

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

INPUT_FILE = os.path.join(DATA_DIR, "ablation_intermediates_gemini_flash_latest.json")
CHECKPOINT = os.path.join(DATA_DIR, "ablation_checkpoint_gemini_flash_latest.json")
OUTPUT_PATH = "/tmp/cot_baseline_prompt.txt"

COT_SYSTEM = """You are an expert Computer Science educator grading student short answers.

Use the following step-by-step process for EACH answer:

STEP 1 — CONCEPT COVERAGE:
  List the specific CS concepts the student correctly covers.
  Example: ["binary_search_tree", "o_log_n", "tree_traversal"]

STEP 2 — COGNITIVE DEPTH:
  Classify the student's level of understanding:
  - Surface (recall): Student restates definitions without explanation
  - Functional (understand): Student explains how/why mechanisms work
  - Integrated (analyze): Student connects multiple concepts with relationships
  - Expert (evaluate/create): Student compares, critiques, or synthesizes

STEP 3 — MISCONCEPTIONS:
  List any factual errors or conceptual confusions.
  If none, write "none".

STEP 4 — HOLISTIC SCORE (0–5 scale, 0.25 increments):
  Based on STEPS 1-3, assign a score:
  - 5.0: Virtually all key ideas, correct mechanisms, no misconceptions
  - 4.0–4.5: Most key ideas with minor gaps
  - 3.0–3.5: About half the reference content
  - 2.0–2.5: 1-2 key ideas correct, most content missing
  - 1.0–1.5: Awareness but no accurate explanations
  - 0.0–0.5: No relevant or incorrect content

IMPORTANT: Score what the student got RIGHT. Missing vocabulary alone does not
lower the score. Credit correct understanding expressed in any words.

Return a JSON object:
{
  "scores": {
    "0": {
      "concepts_identified": ["concept1", "concept2"],
      "cognitive_depth": "Functional",
      "misconceptions": "none",
      "holistic_score": X.X
    },
    ...
  }
}"""


def main() -> None:
    with open(INPUT_FILE) as f:
        data = json.load(f)
    with open(CHECKPOINT) as f:
        ckpt = json.load(f)

    n = 120
    samples = []
    for i in range(n):
        entry = data[str(i)]
        samples.append(
            f"--- SAMPLE ID: {i} ---\n"
            f"QUESTION: {entry['question']}\n\n"
            f"REFERENCE ANSWER (expert — defines 5.0):\n{entry['reference_answer']}\n\n"
            f"STUDENT ANSWER:\n{entry['student_answer']}"
        )

    header = (
        f"{COT_SYSTEM}\n\n"
        f"Grade all {n} student answers below using the step-by-step process.\n"
        f"Return a single JSON with scores for IDs 0 through {n-1}.\n\n"
        f"{'='*70}\n\n"
    )
    body = "\n\n".join(samples)
    footer = (
        f"\n\n{'='*70}\n"
        f"Grade all {n} samples using the 4-step CoT process above.\n"
        f"Return only the JSON object."
    )

    content = header + body + footer
    with open(OUTPUT_PATH, "w") as f:
        f.write(content)

    print(f"CoT baseline prompt → {OUTPUT_PATH}")
    print(f"  {n} samples, {len(content):,} chars")
    print()
    print("Next: Send to Gemini, save response to /tmp/cot_baseline_response.json")
    print("Then: python3 score_cot_baseline.py")


if __name__ == "__main__":
    main()
