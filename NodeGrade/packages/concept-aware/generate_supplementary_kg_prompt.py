"""
Generate supplementary KG prompt for Kaggle ASAG questions 53-149
(the 97 questions not covered in the first KG response).

Output: /tmp/auto_kg_prompt_kaggle_asag_part2.txt

After Gemini responds:
  1. Save response to /tmp/auto_kg_response_kaggle_asag_part2.json
  2. Run: python3 merge_kaggle_kg.py
"""

from __future__ import annotations
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

KG_SYSTEM_PROMPT = """You are an expert educator building a Knowledge Graph for automated answer grading.

For each question + reference answer pair below, extract:
1. CONCEPTS: The key domain concepts a student must understand (as snake_case IDs)
2. RELATIONSHIPS: Typed edges between concepts

Relationship types allowed:
  IS_A, HAS_PART, PREREQUISITE_FOR, IMPLEMENTS, USES, VARIANT_OF,
  HAS_PROPERTY, CONTRASTS_WITH, PRODUCES, OPERATES_ON

Rules:
- Each concept ID must be snake_case, no spaces
- Include 4-8 concepts per question
- Include 3-6 relationships per question
- Focus on what the reference answer explicitly covers

Return ONLY this JSON (no other text):
{
  "question_kgs": {
    "<question_id>": {
      "question": "<question text>",
      "concepts": [{"id": "concept_id", "name": "Human Name", "description": "one line"}],
      "relationships": [{"from": "a", "to": "b", "type": "TYPE", "weight": 0.9, "description": "why"}],
      "expected_concepts": ["concept_id_1", "concept_id_2"]
    }
  }
}"""


def main():
    with open(os.path.join(DATA_DIR, "kaggle_asag_question_index.json")) as f:
        q_index = json.load(f)
    with open(os.path.join(DATA_DIR, "kaggle_asag_dataset.json")) as f:
        records = json.load(f)

    # Build question → reference answer map
    q_to_ref = {}
    for r in records:
        q = r["question"].strip()
        if q not in q_to_ref:
            q_to_ref[q] = r["reference_answer"].strip()

    # Questions 53-149 are missing
    missing_qs = q_index[53:]
    print(f"Generating KG prompt for {len(missing_qs)} questions (indices 53-149)")

    header = (
        f"{KG_SYSTEM_PROMPT}\n\n"
        f"Generate Knowledge Graphs for the following {len(missing_qs)} questions.\n"
        f"Use numeric indices 53 through {53 + len(missing_qs) - 1} as the question_id keys.\n\n"
        f"{'='*70}\n\n"
    )

    body_parts = []
    for offset, q_entry in enumerate(missing_qs):
        qi = 53 + offset
        q_text = q_entry["question"].strip()
        ref = q_to_ref.get(q_text, "")
        body_parts.append(
            f"--- QUESTION {qi} ---\n"
            f"QUESTION: {q_text}\n\n"
            f"REFERENCE ANSWER:\n{ref}\n"
        )

    footer = (
        f"\n{'='*70}\n"
        f"Generate Knowledge Graphs for ALL {len(missing_qs)} questions above (indices 53-{52+len(missing_qs)}).\n"
        f"Return only the JSON object with question_kgs."
    )

    content = header + "\n\n".join(body_parts) + footer
    out_path = "/tmp/auto_kg_prompt_kaggle_asag_part2.txt"
    with open(out_path, "w") as f:
        f.write(content)

    print(f"Prompt → {out_path}  ({len(content):,} chars)")
    print()
    print("Next steps:")
    print("  1. Send /tmp/auto_kg_prompt_kaggle_asag_part2.txt to Gemini")
    print("  2. Save response to /tmp/auto_kg_response_kaggle_asag_part2.json")
    print("  3. Run: python3 merge_kaggle_kg.py")


if __name__ == "__main__":
    main()
