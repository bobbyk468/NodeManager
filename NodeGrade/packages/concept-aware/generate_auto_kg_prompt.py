"""
Stage 0: Automated KG Generation from Reference Answers.

For each unique question+reference_answer, prompts Gemini to generate
a local Knowledge Graph (concept nodes + typed edges) automatically.

This eliminates the need for hand-crafted KGs, enabling ConceptGrade to
scale to arbitrary domains and datasets.

Input:  data/kaggle_asag_dataset.json  OR  data/digiklausur_dataset.json
Output: /tmp/auto_kg_prompt_{dataset}.txt  (send to Gemini)
        data/{dataset}_auto_kg.json         (after Gemini responds)

Usage:
    python3 generate_auto_kg_prompt.py --dataset kaggle_asag
    python3 generate_auto_kg_prompt.py --dataset digiklausur
"""

from __future__ import annotations

import argparse
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

VALID_REL_TYPES = [
    "IS_A", "HAS_PART", "PREREQUISITE_FOR", "IMPLEMENTS",
    "USES", "VARIANT_OF", "HAS_PROPERTY", "HAS_COMPLEXITY",
    "OPERATES_ON", "PRODUCES", "CONTRASTS_WITH",
]

KG_SYSTEM_PROMPT = """You are an expert educator building a Knowledge Graph for automated answer grading.

For each question + reference answer pair below, extract:
1. CONCEPTS: The key domain concepts a student must understand (as snake_case IDs)
2. RELATIONSHIPS: Typed edges between concepts

Relationship types allowed:
  IS_A           — taxonomy (neural_network IS_A function_approximator)
  HAS_PART       — composition (brain HAS_PART neuron)
  PREREQUISITE_FOR — dependency (gradient PREREQUISITE_FOR backpropagation)
  IMPLEMENTS     — realization (perceptron IMPLEMENTS linear_classifier)
  USES           — usage (backpropagation USES chain_rule)
  VARIANT_OF     — variation (relu VARIANT_OF activation_function)
  HAS_PROPERTY   — attribute (neural_network HAS_PROPERTY parallel_processing)
  CONTRASTS_WITH — comparison (supervised_learning CONTRASTS_WITH unsupervised_learning)
  PRODUCES       — output (learning_algorithm PRODUCES weight_update)
  OPERATES_ON    — target (convolution OPERATES_ON feature_map)

Rules:
- Each concept ID must be snake_case, no spaces
- Include 4-10 concepts per question
- Include 3-8 relationships per question
- Concepts must be domain terms, not generic words (NOT: "process", "way", "thing")
- Focus on what the reference answer explicitly covers

Return a JSON object:
{
  "question_kgs": {
    "<question_id>": {
      "question": "<question text>",
      "concepts": [
        {"id": "concept_id", "name": "Human Readable Name", "description": "one line"}
      ],
      "relationships": [
        {"from": "concept_a", "to": "concept_b", "type": "RELATIONSHIP_TYPE", "weight": 0.9, "description": "why"}
      ],
      "expected_concepts": ["concept_id_1", "concept_id_2"]
    }
  }
}
"""


def main(dataset: str) -> None:
    in_path = os.path.join(DATA_DIR, f"{dataset}_dataset.json")
    prompt_path = f"/tmp/auto_kg_prompt_{dataset}.txt"

    with open(in_path) as f:
        records = json.load(f)

    # Collect unique questions (by question text)
    seen: dict[str, dict] = {}
    for r in records:
        q = r["question"].strip()
        if q not in seen:
            seen[q] = {
                "question_id": str(r.get("question_id", len(seen))),
                "question": q,
                "reference_answer": r["reference_answer"].strip(),
            }

    unique_qs = list(seen.values())
    print(f"Dataset: {dataset}")
    print(f"Total samples: {len(records)}, Unique questions: {len(unique_qs)}")

    # Build prompt — batch all questions in one call
    header = (
        f"{KG_SYSTEM_PROMPT}\n\n"
        f"Generate Knowledge Graphs for the following {len(unique_qs)} questions.\n"
        f"Use the QUESTION TEXT as the question_id key (use numeric index 0..{len(unique_qs)-1}).\n\n"
        f"{'='*70}\n\n"
    )

    body_parts = []
    for qi, q in enumerate(unique_qs):
        body_parts.append(
            f"--- QUESTION {qi} ---\n"
            f"QUESTION: {q['question']}\n\n"
            f"REFERENCE ANSWER:\n{q['reference_answer']}\n"
        )

    footer = (
        f"\n{'='*70}\n"
        f"Generate Knowledge Graphs for ALL {len(unique_qs)} questions above.\n"
        f"Return only the JSON object with question_kgs."
    )

    content = header + "\n\n".join(body_parts) + footer

    with open(prompt_path, "w") as f:
        f.write(content)

    print(f"Prompt written → {prompt_path}  ({len(content):,} chars, {len(unique_qs)} questions)")
    print()
    print("Next steps:")
    print(f"  1. Send {prompt_path} to Gemini")
    print(f"  2. Save response to /tmp/auto_kg_response_{dataset}.json")
    print(f"  3. Run: python3 run_new_dataset_eval.py --dataset {dataset}")

    # Also save the question index for later alignment
    idx_path = os.path.join(DATA_DIR, f"{dataset}_question_index.json")
    with open(idx_path, "w") as f:
        json.dump(unique_qs, f, indent=2)
    print(f"  Question index saved → {idx_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["kaggle_asag", "digiklausur"], required=True)
    args = parser.parse_args()
    main(args.dataset)
