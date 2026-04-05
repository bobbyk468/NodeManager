"""
Generate batch scoring prompts for new datasets (DigiKlausur, Kaggle ASAG).

Works WITHOUT a Gemini API key — generates text files that can be pasted into
Gemini web or submitted via API later.

Each batch prompt asks for BOTH C_LLM and C5_fix scores in one JSON response.
The KG evidence (concept matching, SOLO, Bloom, chain coverage) is precomputed
locally — no API calls needed for that step.

Outputs (per dataset, per batch):
  /tmp/batch_scoring/{dataset}_batch_{n:02d}.txt   — the prompt to send to Gemini
  /tmp/batch_scoring/{dataset}_precomputed.json    — precomputed KG features

Usage:
    python3 generate_batch_scoring_prompts.py --dataset digiklausur
    python3 generate_batch_scoring_prompts.py --dataset kaggle_asag
    python3 generate_batch_scoring_prompts.py --dataset all

After getting Gemini responses:
    python3 score_batch_results.py --dataset digiklausur
    python3 score_batch_results.py --dataset kaggle_asag
"""

from __future__ import annotations

import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR = "/tmp/batch_scoring"

BATCH_SIZE = 80  # samples per batch prompt

SCORING_GUIDE = """SCORING GUIDE — based on proportion of reference answer content correctly demonstrated:
- 5.0: Student correctly explains virtually all key ideas (≥90% of reference content)
- 4.5: Student correctly explains the great majority (≥80%); only very minor omissions
- 4.0: Student correctly explains most key ideas (≥70%); one clear gap
- 3.5: Student correctly explains a solid majority (≥60%) with reasonable depth
- 3.0: Student correctly explains about half the reference content (~50%)
- 2.5: Student correctly explains several key ideas (30–50%); substantial content missing
- 2.0: Student correctly explains 1–2 key ideas accurately; most reference content missing
- 1.5: Student shows partial understanding of 1 concept but cannot explain mechanisms
- 1.0: Student shows awareness of the topic but no accurate explanations
- 0.5: Single marginally relevant statement; no explanation
- 0.0: No relevant content

Score what the student got RIGHT. Missing vocabulary alone does not lower the score.
Use 0.25 increments only."""


def simple_concept_match(student_answer: str, kg_concepts: list[dict]) -> list[str]:
    """
    Match KG concepts against student answer using multi-strategy matching:
    1. Exact name/id words (>3 chars)
    2. Description keywords from the KG concept description
    3. Short meaningful words (>2 chars) from concept name
    4. Concept synonyms embedded in description text

    This is more robust than strict keyword matching, catching paraphrases
    like "good" → "helpful_microorganisms" (description: "helpful living things").
    """
    matched = []
    answer_lower = student_answer.lower()
    # Pre-tokenize answer for faster membership checks
    answer_words = set(answer_lower.replace(",", " ").replace(".", " ").split())

    for c in kg_concepts:
        cid = c["id"]
        name = c.get("name", cid).lower()
        desc = c.get("description", "").lower()

        # Strategy 1: words from concept name/id (>3 chars)
        name_words = [w for w in name.replace("_", " ").split() if len(w) > 3]
        id_words = [w for w in cid.replace("_", " ").split() if len(w) > 3]
        all_kw = set(name_words + id_words)

        if any(w in answer_lower for w in all_kw):
            matched.append(cid)
            continue

        # Strategy 2: short meaningful words from name (>2 chars, not stop words)
        stop = {"the", "and", "for", "are", "that", "this", "with", "from", "not"}
        short_words = [w for w in name.replace("_", " ").split()
                       if len(w) > 2 and w not in stop]
        if short_words and any(w in answer_lower for w in short_words):
            matched.append(cid)
            continue

        # Strategy 3: key words from KG description (>4 chars, not stop words)
        if desc:
            desc_words = [w for w in desc.split() if len(w) > 4 and w not in stop]
            # Require at least 2 description words to match (avoids false positives)
            desc_hits = sum(1 for w in desc_words if w in answer_lower)
            if desc_hits >= 2:
                matched.append(cid)
                continue

        # Strategy 4: full concept id appears as substring
        if cid.replace("_", " ") in answer_lower:
            matched.append(cid)

    return list(set(matched))


def classify_solo(matched: list[str], total_expected: int) -> str:
    ratio = len(matched) / max(total_expected, 1)
    if ratio == 0:
        return "Prestructural"
    elif ratio <= 0.25:
        return "Unistructural"
    elif ratio <= 0.60:
        return "Multistructural"
    elif ratio <= 0.85:
        return "Relational"
    else:
        return "Extended Abstract"


def classify_bloom(student_answer: str) -> str:
    a = student_answer.lower()
    if any(w in a for w in ["because", "therefore", "which means", "this causes", "as a result"]):
        return "Analyze"
    if any(w in a for w in ["explains", "describe", "how", "why", "process", "mechanism"]):
        return "Understand"
    return "Remember"


def precompute_features(records, q_to_kg):
    features = {}
    for r in records:
        q = r["question"].strip()
        kg = q_to_kg.get(q, {})
        concepts = kg.get("concepts", [])
        expected = kg.get("expected_concepts", [c["id"] for c in concepts])
        matched = simple_concept_match(r["student_answer"], concepts)
        chain_pct = f"{min(len(matched)/max(len(expected),1), 1.0):.0%}"
        solo_label = classify_solo(matched, len(expected))
        bloom_label = classify_bloom(r["student_answer"])
        features[str(r["id"])] = {
            "matched_concepts": matched,
            "chain_pct": chain_pct,
            "solo": solo_label,
            "bloom": bloom_label,
            "n_kg_concepts": len(concepts),
        }
    return features


def build_batch_prompt(batch: list[dict], features: dict) -> str:
    """Build a dual-score prompt: returns both cllm and c5fix per sample.
    NOTE: Kept for backward compatibility. Use build_cllm_prompt / build_c5fix_prompt
    for split mode (prevents anchoring where cllm==c5fix always).
    """
    system = f"""{SCORING_GUIDE}

You are an expert grader. For each student answer below, provide TWO scores:
1. cllm_score: Grade using ONLY the question, reference answer, and student answer.
2. c5fix_score: Grade using the question, reference answer, student answer, AND the KG evidence provided.

Return a JSON object:
{{
  "scores": {{
    "<id>": {{"cllm_score": X.X, "c5fix_score": X.X}},
    ...
  }}
}}

Grade all {len(batch)} samples below. Use 0.25 increments."""

    parts = []
    for r in batch:
        sid = str(r["id"])
        feat = features.get(sid, {})
        covered = ", ".join(feat.get("matched_concepts", [])) or "none identified"
        chain_pct = feat.get("chain_pct", "0%")
        solo = feat.get("solo", "Prestructural")
        bloom = feat.get("bloom", "Remember")

        parts.append(
            f"--- SAMPLE ID: {sid} ---\n"
            f"QUESTION: {r['question']}\n\n"
            f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
            f"KG EVIDENCE:\n"
            f"  Concepts demonstrated: {covered}\n"
            f"  Causal chain coverage: {chain_pct}\n"
            f"  Bloom's level: {bloom}\n"
            f"  SOLO level: {solo}\n\n"
            f"STUDENT ANSWER:\n{r['student_answer']}"
        )

    header = f"{system}\n\n{'='*70}\n\n"
    body = "\n\n".join(parts)
    footer = f"\n\n{'='*70}\nGrade all {len(batch)} samples. Return only the JSON object."
    return header + body + footer


def build_cllm_prompt(batch: list[dict]) -> str:
    """C_LLM batch prompt: grade using ONLY question + reference + student answer (no KG)."""
    system = f"""{SCORING_GUIDE}

You are an expert grader. Grade each student answer below using ONLY the question, reference answer, and student answer. Do NOT use any external knowledge graphs or structured evidence.

Return a JSON object:
{{
  "scores": {{
    "<id>": X.X,
    ...
  }}
}}

Grade all {len(batch)} samples. Use 0.25 increments."""

    parts = []
    for r in batch:
        parts.append(
            f"--- SAMPLE ID: {r['id']} ---\n"
            f"QUESTION: {r['question']}\n\n"
            f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
            f"STUDENT ANSWER:\n{r['student_answer']}"
        )

    header = f"{system}\n\n{'='*70}\n\n"
    body = "\n\n".join(parts)
    footer = f"\n\n{'='*70}\nGrade all {len(batch)} samples. Return only the JSON object."
    return header + body + footer


def build_c5fix_prompt(batch: list[dict], features: dict) -> str:
    """C5_fix batch prompt: grade using question + reference + student answer + KG evidence.

    The KG evidence is framed as a POSITIVE guide (key concepts expected) rather than
    a penalty (concepts not detected). This avoids systematic underscoring when
    keyword matching misses paraphrased correct answers.
    """
    system = f"""{SCORING_GUIDE}

You are an expert grader with access to a Knowledge Graph (KG) that identifies the key concepts expected in a complete answer. Use the KG as a conceptual checklist: does the student's answer address these concepts (even if not using exact terminology)? The KG guides what to look for; it does NOT mechanically penalize for missing keywords.

Important: A student who expresses a concept correctly in their own words should receive full credit for that concept, even if they don't use the technical term.

Return a JSON object:
{{
  "scores": {{
    "<id>": X.X,
    ...
  }}
}}

Grade all {len(batch)} samples. Use 0.25 increments."""

    parts = []
    for r in batch:
        sid = str(r["id"])
        feat = features.get(sid, {})
        covered = ", ".join(feat.get("matched_concepts", [])) or "assess from student text"
        chain_pct = feat.get("chain_pct", "0%")
        bloom = feat.get("bloom", "Remember")
        n_kg = feat.get("n_kg_concepts", 0)

        # Load KG concepts list for this question to show as positive guide
        # (Only show if we have KG data)
        kg_guide = f"Detected concept keywords: {covered}" if covered != "assess from student text" else "Use reference answer to identify key concepts"

        parts.append(
            f"--- SAMPLE ID: {sid} ---\n"
            f"QUESTION: {r['question']}\n\n"
            f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
            f"KG GUIDANCE (expected concepts: {n_kg} total):\n"
            f"  {kg_guide}\n"
            f"  Estimated chain coverage: {chain_pct}\n"
            f"  Cognitive depth detected: {bloom}\n\n"
            f"STUDENT ANSWER:\n{r['student_answer']}"
        )

    header = f"{system}\n\n{'='*70}\n\n"
    body = "\n\n".join(parts)
    footer = f"\n\n{'='*70}\nGrade all {len(batch)} samples. Use KG as a guide, not a rigid checklist. Return only the JSON object."
    return header + body + footer


def run(dataset: str, mode: str = "split") -> None:
    """Generate batch prompts. mode='split' generates separate cllm/c5fix batches (recommended).
    mode='dual' generates combined dual-score batches (legacy, causes anchoring).
    """
    os.makedirs(OUT_DIR, exist_ok=True)

    data_path = os.path.join(DATA_DIR, f"{dataset}_dataset.json")
    kg_path = f"/tmp/auto_kg_response_{dataset}.json"
    q_idx_path = os.path.join(DATA_DIR, f"{dataset}_question_index.json")

    with open(data_path) as f:
        records = json.load(f)
    with open(q_idx_path) as f:
        q_index = json.load(f)

    # Build KG map
    if os.path.exists(kg_path):
        with open(kg_path) as f:
            kg_raw = json.load(f)
        question_kgs = kg_raw.get("question_kgs", kg_raw)
    else:
        print(f"WARNING: No KG file at {kg_path} — running with empty KG features")
        question_kgs = {}

    q_to_kg: dict[str, dict] = {}
    for qi, q_entry in enumerate(q_index):
        kg_entry = question_kgs.get(str(qi), question_kgs.get(qi, {}))
        q_to_kg[q_entry["question"].strip()] = kg_entry

    # Precompute KG features
    features = precompute_features(records, q_to_kg)
    feat_path = os.path.join(OUT_DIR, f"{dataset}_precomputed.json")
    with open(feat_path, "w") as f:
        json.dump(features, f, indent=2)
    print(f"Precomputed KG features → {feat_path}")

    n_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE
    total_chars = 0

    if mode == "split":
        # Generate separate cllm and c5fix batch files (prevents anchoring)
        for b in range(n_batches):
            batch = records[b * BATCH_SIZE: (b + 1) * BATCH_SIZE]

            cllm_prompt = build_cllm_prompt(batch)
            cllm_path = os.path.join(OUT_DIR, f"{dataset}_cllm_batch_{b+1:02d}.txt")
            with open(cllm_path, "w") as f:
                f.write(cllm_prompt)

            c5fix_prompt = build_c5fix_prompt(batch, features)
            c5fix_path = os.path.join(OUT_DIR, f"{dataset}_c5fix_batch_{b+1:02d}.txt")
            with open(c5fix_path, "w") as f:
                f.write(c5fix_prompt)

            total_chars += len(cllm_prompt) + len(c5fix_prompt)
            print(f"  Batch {b+1:2d}/{n_batches}: {len(batch):3d} samples, "
                  f"cllm={len(cllm_prompt):,} chars, c5fix={len(c5fix_prompt):,} chars")

        print(f"\nTotal: {n_batches} split batch pairs ({n_batches*2} files), {total_chars:,} chars")
        print(f"\nNext steps:")
        print(f"  python3 run_full_pipeline.py --dataset {dataset} --skip-kg")

    else:  # dual (legacy)
        for b in range(n_batches):
            batch = records[b * BATCH_SIZE: (b + 1) * BATCH_SIZE]
            prompt = build_batch_prompt(batch, features)
            out_path = os.path.join(OUT_DIR, f"{dataset}_batch_{b+1:02d}.txt")
            with open(out_path, "w") as f:
                f.write(prompt)
            total_chars += len(prompt)
            print(f"  Batch {b+1:2d}/{n_batches}: {len(batch):3d} samples, "
                  f"{len(prompt):,} chars → {out_path}")

        print(f"\nTotal: {n_batches} batch prompts, {total_chars:,} chars")
        print(f"\nNext steps:")
        print(f"  1. Send each batch_{dataset}_XX.txt to Gemini")
        print(f"  2. Save responses as: /tmp/batch_scoring/{dataset}_batch_XX_response.json")
        print(f"  3. Run: python3 score_batch_results.py --dataset {dataset}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["digiklausur", "kaggle_asag", "all"], required=True)
    parser.add_argument("--mode", choices=["split", "dual"], default="split",
                        help="split=separate cllm/c5fix batches (recommended); dual=combined (legacy)")
    args = parser.parse_args()

    if args.dataset == "all":
        for ds in ["digiklausur", "kaggle_asag"]:
            print(f"\n{'='*60}")
            print(f"Dataset: {ds}")
            print(f"{'='*60}")
            run(ds, mode=args.mode)
    else:
        run(args.dataset, mode=args.mode)


if __name__ == "__main__":
    main()
