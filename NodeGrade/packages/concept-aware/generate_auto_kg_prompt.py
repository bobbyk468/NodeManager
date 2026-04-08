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

    # After getting Gemini response:
    python3 generate_auto_kg_prompt.py --dataset kaggle_asag \\
        --process-response /tmp/auto_kg_response_kaggle_asag.json
"""

from __future__ import annotations

import argparse
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

VALID_REL_TYPES = [
    "IS_A", "HAS_PART", "PREREQUISITE_FOR", "IMPLEMENTS",
    "USES", "VARIANT_OF", "HAS_PROPERTY", "HAS_COMPLEXITY",
    "OPERATES_ON", "PRODUCES", "CONTRASTS_WITH",
]

# Map non-standard relationship types Gemini sometimes produces → canonical types
REL_TYPE_REMAP: dict[str, str] = {
    "STORES":          "HAS_PART",
    "RESEMBLES":       "VARIANT_OF",
    "LEADS_TO":        "PRODUCES",
    "ENABLES":         "PREREQUISITE_FOR",
    "PART_OF":         "HAS_PART",
    "RELATED_TO":      "CONTRASTS_WITH",
    "DEPENDS_ON":      "PREREQUISITE_FOR",
    "CONTAINS":        "HAS_PART",
    "EXTENDS":         "VARIANT_OF",
    "DERIVES_FROM":    "VARIANT_OF",
    "SUPPORTS":        "IMPLEMENTS",
    "APPLIED_TO":      "OPERATES_ON",
    "RESULTS_IN":      "PRODUCES",
    "DEFINES":         "HAS_PROPERTY",
    "CONSISTS_OF":     "HAS_PART",
    "REQUIRES":        "PREREQUISITE_FOR",
    "CREATES":         "PRODUCES",
    "MODIFIES":        "OPERATES_ON",
    "TRIGGERS":        "PRODUCES",
    "INCLUDES":        "HAS_PART",
}

# Generic terms that are not domain concepts — remove from KG
GENERIC_CONCEPT_STOPLIST: set[str] = {
    "process", "way", "thing", "method", "approach", "technique",
    "concept", "idea", "mechanism", "system", "aspect", "factor",
    "property", "result", "output", "input", "example", "type",
    "form", "kind", "part", "step", "stage", "element", "component",
    "feature", "function", "role", "use", "purpose", "reason",
    "information", "data", "value", "set", "list", "group", "term",
    "definition", "description", "structure", "model", "entity",
}

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


def _is_generic(concept_id: str) -> bool:
    """Return True if concept_id is a generic stop-word (not a domain term)."""
    normalized = concept_id.lower().replace("_", "")
    for stop in GENERIC_CONCEPT_STOPLIST:
        if normalized == stop.replace("_", ""):
            return True
    return False


def _fix_concept_id(raw_id: str) -> str:
    """Normalize concept ID to snake_case."""
    return re.sub(r"[^a-z0-9]+", "_", raw_id.lower().strip()).strip("_")


def validate_and_clean_kg(raw_kg: dict) -> tuple[dict, list[str]]:
    """
    Validate and clean a question_kgs dict returned by Gemini.

    Fixes:
    - Concept IDs with spaces → snake_case
    - Removes generic stop-word concepts
    - Remaps non-standard relationship types to canonical types
    - Drops relationships that can't be remapped
    - Flags entries with <4 valid concepts for retry
    - Prunes expected_concepts to surviving concept IDs

    Returns:
        (cleaned_kg, warnings)  where warnings is a list of human-readable strings.
    """
    warnings: list[str] = []
    cleaned_kgs: dict = {}

    for qid, entry in raw_kg.get("question_kgs", {}).items():
        concepts_raw = entry.get("concepts", [])
        relationships_raw = entry.get("relationships", [])
        expected_raw = entry.get("expected_concepts", [])

        # --- Step 1: Fix and filter concepts ---
        cleaned_concepts = []
        removed_ids: set[str] = set()
        id_remap: dict[str, str] = {}  # old_id → new_id (for space fixes)

        for c in concepts_raw:
            old_id = c.get("id", "")
            new_id = _fix_concept_id(old_id)

            if old_id != new_id:
                warnings.append(f"Q{qid}: fixed concept id '{old_id}' → '{new_id}'")
                id_remap[old_id] = new_id

            if _is_generic(new_id):
                warnings.append(f"Q{qid}: removed generic concept '{new_id}'")
                removed_ids.add(old_id)
                removed_ids.add(new_id)
                continue

            cleaned_concepts.append({**c, "id": new_id})

        surviving_ids = {c["id"] for c in cleaned_concepts}

        # --- Step 2: Remap and filter relationships ---
        cleaned_rels = []
        for rel in relationships_raw:
            rel_type = rel.get("type", "").upper()
            from_id = id_remap.get(rel.get("from", ""), rel.get("from", ""))
            to_id = id_remap.get(rel.get("to", ""), rel.get("to", ""))

            # Skip relationships involving removed concepts
            if from_id in removed_ids or to_id in removed_ids:
                continue
            if from_id not in surviving_ids or to_id not in surviving_ids:
                continue

            if rel_type in VALID_REL_TYPES:
                cleaned_rels.append({**rel, "from": from_id, "to": to_id, "type": rel_type})
            elif rel_type in REL_TYPE_REMAP:
                canonical = REL_TYPE_REMAP[rel_type]
                warnings.append(
                    f"Q{qid}: remapped relationship '{rel_type}' → '{canonical}' "
                    f"on '{from_id}' → '{to_id}'"
                )
                cleaned_rels.append({**rel, "from": from_id, "to": to_id, "type": canonical})
            else:
                warnings.append(
                    f"Q{qid}: dropped unknown relationship type '{rel_type}' "
                    f"on '{from_id}' → '{to_id}'"
                )

        # --- Step 3: Fix expected_concepts ---
        cleaned_expected = []
        for eid in expected_raw:
            fixed_eid = id_remap.get(eid, eid)
            if fixed_eid in surviving_ids:
                cleaned_expected.append(fixed_eid)

        # --- Step 4: Flag for retry if too few concepts ---
        needs_retry = len(cleaned_concepts) < 4
        if needs_retry:
            warnings.append(
                f"Q{qid}: only {len(cleaned_concepts)} concept(s) survived — flagged for retry"
            )

        cleaned_kgs[qid] = {
            "question": entry.get("question", ""),
            "concepts": cleaned_concepts,
            "relationships": cleaned_rels,
            "expected_concepts": cleaned_expected,
        }
        if needs_retry:
            cleaned_kgs[qid]["_needs_retry"] = True

    return {"question_kgs": cleaned_kgs}, warnings


def build_retry_prompt(questions_needing_retry: list[dict]) -> str:
    """
    Build a focused Gemini prompt for questions that returned <4 concepts.
    Uses the same system prompt header but with an explicit retry instruction.
    """
    n = len(questions_needing_retry)
    header = (
        f"{KG_SYSTEM_PROMPT}\n\n"
        "IMPORTANT RETRY INSTRUCTION: The following questions previously returned "
        "fewer than 4 valid domain concepts, or had too many generic/invalid concepts. "
        "Please regenerate them with richer, more specific concept extraction. "
        "Aim for 6-8 well-defined domain concepts per question.\n\n"
        f"Generate Knowledge Graphs for the following {n} questions.\n"
        f"{'='*70}\n\n"
    )

    body_parts = []
    for qi, q in enumerate(questions_needing_retry):
        body_parts.append(
            f"--- QUESTION {qi} ---\n"
            f"QUESTION: {q['question']}\n\n"
            f"REFERENCE ANSWER:\n{q.get('reference_answer', q.get('original_reference', ''))}\n"
        )

    footer = (
        f"\n{'='*70}\n"
        f"Generate Knowledge Graphs for ALL {n} questions above.\n"
        f"Return only the JSON object with question_kgs."
    )

    return header + "\n\n".join(body_parts) + footer


def process_response(dataset: str, response_path: str, max_retries: int = 1) -> None:
    """
    Load a Gemini KG response, validate/clean it, and save the result.
    If any questions need retry, writes a retry prompt to /tmp/.
    """
    print(f"\n=== Processing KG response for '{dataset}' ===")
    print(f"Input: {response_path}")

    with open(response_path) as f:
        raw = json.load(f)

    # Gemini sometimes wraps in {"candidates": [...]} — unwrap if needed
    if "question_kgs" not in raw and "candidates" in raw:
        print("  (unwrapping Gemini candidates envelope)")
        text = raw["candidates"][0]["content"]["parts"][0]["text"]
        # Strip markdown code fences if present
        text = re.sub(r"^```json\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text.strip())
        raw = json.loads(text)

    cleaned, warnings = validate_and_clean_kg(raw)

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ! {w}")
    else:
        print("  No warnings — KG is clean.")

    # Count concepts and rels
    total_concepts = sum(len(e["concepts"]) for e in cleaned["question_kgs"].values())
    total_rels = sum(len(e["relationships"]) for e in cleaned["question_kgs"].values())
    n_questions = len(cleaned["question_kgs"])
    needs_retry = [
        {"question": e["question"]}
        for e in cleaned["question_kgs"].values()
        if e.get("_needs_retry")
    ]

    print(f"\n  Questions: {n_questions}")
    print(f"  Concepts:  {total_concepts} total, avg {total_concepts/max(n_questions,1):.1f}/question")
    print(f"  Relations: {total_rels} total, avg {total_rels/max(n_questions,1):.1f}/question")
    print(f"  Need retry: {len(needs_retry)}")

    # Save cleaned KG (excluding _needs_retry flags in final output)
    out_path = os.path.join(DATA_DIR, f"{dataset}_auto_kg.json")
    final_kg = {
        "question_kgs": {
            qid: {k: v for k, v in entry.items() if k != "_needs_retry"}
            for qid, entry in cleaned["question_kgs"].items()
            if not entry.get("_needs_retry")
        }
    }
    with open(out_path, "w") as f:
        json.dump(final_kg, f, indent=2)
    print(f"\n  Cleaned KG saved → {out_path}")
    print(f"  ({len(final_kg['question_kgs'])} valid questions)")

    # If retries needed and quota allows, write retry prompt
    if needs_retry and max_retries > 0:
        # Load question index to get reference answers for retry questions
        idx_path = os.path.join(DATA_DIR, f"{dataset}_question_index.json")
        if os.path.exists(idx_path):
            with open(idx_path) as f:
                question_index = json.load(f)
            q_by_text = {q["question"]: q for q in question_index}
            retry_questions = []
            for nr in needs_retry:
                match = q_by_text.get(nr["question"])
                if match:
                    retry_questions.append(match)
                else:
                    retry_questions.append(nr)
        else:
            retry_questions = needs_retry

        retry_prompt = build_retry_prompt(retry_questions)
        retry_path = f"/tmp/auto_kg_retry_{dataset}.txt"
        with open(retry_path, "w") as f:
            f.write(retry_prompt)
        print(f"\n  Retry prompt written → {retry_path}")
        print(f"  Send it to Gemini, save response, then run:")
        print(f"    python3 generate_auto_kg_prompt.py --dataset {dataset} \\")
        print(f"        --process-response /tmp/auto_kg_retry_response_{dataset}.json \\")
        print(f"        --max-retries {max_retries - 1}")
    elif needs_retry:
        print(f"\n  {len(needs_retry)} questions still need retry but max_retries=0; skipping.")


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
    print(f"  3. Run:")
    print(f"     python3 generate_auto_kg_prompt.py --dataset {dataset} \\")
    print(f"         --process-response /tmp/auto_kg_response_{dataset}.json")

    # Also save the question index for later alignment
    idx_path = os.path.join(DATA_DIR, f"{dataset}_question_index.json")
    with open(idx_path, "w") as f:
        json.dump(unique_qs, f, indent=2)
    print(f"  Question index saved → {idx_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stage 0: Auto-generate Knowledge Graphs for a dataset."
    )
    parser.add_argument(
        "--dataset",
        choices=["kaggle_asag", "digiklausur"],
        required=True,
        help="Dataset to generate KGs for.",
    )
    parser.add_argument(
        "--process-response",
        metavar="PATH",
        help=(
            "Path to a Gemini JSON response file. When provided, validates and cleans the KG "
            "and saves the result to data/{dataset}_auto_kg.json."
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Number of retry passes for questions with <4 valid concepts (default: 1).",
    )
    args = parser.parse_args()

    if args.process_response:
        process_response(args.dataset, args.process_response, max_retries=args.max_retries)
    else:
        main(args.dataset)
