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
import shutil
import sys

from concept_matching import (
    ConceptEmbeddingCache,
    coverage_ratio,
    should_use_kg_evidence,
    unified_concept_match,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR = os.environ.get('CONCEPTGRADE_BATCH_DIR', os.path.join(BASE_DIR, 'data', 'tmp'))

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

SCORING_GUIDE_STRICT = """SCORING GUIDE — based on proportion of reference answer content correctly demonstrated:
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

CALIBRATION NOTE: These are short elementary-level science answers. Most students earn 1–3 out of 5.
A student who only names the topic without explaining the mechanism scores 1.0 or less.
A student who gives a vague or partially correct answer scores 2.0–2.5.
Reserve 4.0–5.0 for answers that correctly explain the mechanism or process.
Score what the student got RIGHT. Missing vocabulary alone does not lower the score.
Use integer scores (0, 1, 2, 3, 4, 5) only — no decimals."""


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


def precompute_features(
    records,
    q_to_kg: dict,
    embed_cache: ConceptEmbeddingCache | None = None,
):
    features = {}
    for r in records:
        q = r["question"].strip()
        kg = q_to_kg.get(q, {})
        concepts = kg.get("concepts", [])
        expected = kg.get("expected_concepts", [c["id"] for c in concepts])
        # Framework Fix #2c (2026-06-15): explicit out-of-KG-domain signal.
        # When the question itself has no KG entry (Kaggle science questions
        # against the CS-DS KG), low coverage downstream does not mean
        # "student failed" — it means "KG cannot help here". The C5_fix
        # prompt uses this to tell the LLM not to penalise the student for
        # not using KG terminology. Mirror of the upstream
        # StudentConceptGraph.domain_match_score signal added in Fix #2b.
        in_q_to_kg = q in q_to_kg
        domain_match_score = 1.0 if (in_q_to_kg and concepts) else 0.0
        matched = unified_concept_match(
            r["student_answer"], concepts, cache=embed_cache
        )
        cov = coverage_ratio(matched, expected)
        use_kg = should_use_kg_evidence(cov)
        chain_pct = f"{min(len(matched) / max(len(expected), 1), 1.0):.0%}"
        solo_label = classify_solo(matched, len(expected))
        bloom_label = classify_bloom(r["student_answer"])
        features[str(r["id"])] = {
            "matched_concepts": matched,
            "chain_pct": chain_pct,
            "solo": solo_label,
            "bloom": bloom_label,
            "n_kg_concepts": len(concepts),
            "coverage_ratio": round(cov, 4),
            "use_kg": use_kg,
            "domain_match_score": domain_match_score,
            "out_of_kg_domain": domain_match_score < 0.05,
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


def build_cllm_prompt(batch: list[dict], scoring_guide: str | None = None) -> str:
    """C_LLM batch prompt: grade using ONLY question + reference + student answer (no KG)."""
    guide = scoring_guide if scoring_guide is not None else SCORING_GUIDE
    increment_note = "Use integer scores (0, 1, 2, 3, 4, 5) only." if scoring_guide == SCORING_GUIDE_STRICT else "Use 0.25 increments."
    system = f"""{guide}

You are an expert grader. Grade each student answer below using ONLY the question, reference answer, and student answer. Do NOT use any external knowledge graphs or structured evidence.

Return a JSON object:
{{
  "scores": {{
    "<id>": X.X,
    ...
  }}
}}

Grade all {len(batch)} samples. {increment_note}"""

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


def build_c5fix_prompt(batch: list[dict], features: dict, scoring_guide: str | None = None) -> str:
    """C5_fix batch prompt: grade using question + reference + student answer + KG evidence.

    The KG evidence is framed as a POSITIVE guide (key concepts expected) rather than
    a penalty (concepts not detected). This avoids systematic underscoring when
    keyword matching misses paraphrased correct answers.

    When automatic concept coverage is below KG_MIN_COVERAGE, the sample is graded
    like C_LLM (no KG block) so weak extractions do not mislead the model.
    """
    guide = scoring_guide if scoring_guide is not None else SCORING_GUIDE
    increment_note = "Use integer scores (0, 1, 2, 3, 4, 5) only." if scoring_guide == SCORING_GUIDE_STRICT else "Use 0.25 increments."
    # Framework Fix #1 (2026-05-31): two surgical changes vs the previous
    # build_c5fix_prompt that empirically lost to v2-concepts_only on Mohler:
    #   Diff #1: removed "Cognitive depth detected: <bloom>" line. The Bloom
    #            label is empirically inert (does not discriminate silent
    #            failures, p=0.46 on DigiKlausur) and primed the model to
    #            under-weight student-answer content.
    #   Diff #2: replaced prescriptive "KG GUIDANCE" framing with
    #            "PRIMARY (student vs reference) / SUPPLEMENTARY (KG)"
    #            framing copied from v2-concepts_only (which achieved
    #            MAE 0.217 vs C5_fix 0.223).
    system = f"""{guide}

You are an expert grader.

PRIMARY evidence (always): compare the student's answer against the reference answer. Ask: what key concepts from the reference did the student cover? What is missing?

SUPPLEMENTARY evidence (when present): KG matched concepts and chain coverage percentage. These confirm which knowledge-graph concepts were detected in the answer. IMPORTANT: if matched concepts = "none" or chain coverage = 0%, do NOT automatically give 0 -- read the student answer and score based on what you see.

When a sample has NO KG SUPPLEMENTARY EVIDENCE section, grade using ONLY the question, reference answer, and student answer.

When a sample is marked [OUT_OF_KG_DOMAIN], the question is outside the knowledge graph's coverage. The absence of KG matches is a property of the system, NOT a property of the student's answer. Grade student-vs-reference only and do not penalise the student for the missing KG evidence.

Return a JSON object:
{{
  "scores": {{
    "<id>": X.X,
    ...
  }}
}}

Grade all {len(batch)} samples. {increment_note}"""

    parts = []
    for r in batch:
        sid = str(r["id"])
        feat = features.get(sid, {})
        use_kg = feat.get("use_kg", True)
        out_of_kg = feat.get("out_of_kg_domain", False)

        if out_of_kg:
            parts.append(
                f"--- SAMPLE ID: {sid} ---  [OUT_OF_KG_DOMAIN]\n"
                f"QUESTION: {r['question']}\n\n"
                f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
                f"STUDENT ANSWER:\n{r['student_answer']}"
            )
            continue

        if not use_kg:
            parts.append(
                f"--- SAMPLE ID: {sid} ---\n"
                f"QUESTION: {r['question']}\n\n"
                f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
                f"STUDENT ANSWER:\n{r['student_answer']}"
            )
            continue

        covered = ", ".join(feat.get("matched_concepts", [])) or "none"
        chain_pct = feat.get("chain_pct", "0%")

        parts.append(
            f"--- SAMPLE ID: {sid} ---\n"
            f"QUESTION: {r['question']}\n\n"
            f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
            f"KG SUPPLEMENTARY EVIDENCE:\n"
            f"  Matched concepts: {covered}\n"
            f"  Chain coverage: {chain_pct}\n\n"
            f"STUDENT ANSWER:\n{r['student_answer']}"
        )

    header = f"{system}\n\n{'='*70}\n\n"
    body = "\n\n".join(parts)
    footer = f"\n\n{'='*70}\nGrade all {len(batch)} samples. PRIMARY evidence is student-vs-reference; KG is supplementary. Return only the JSON object."
    return header + body + footer


def build_c5fix_judge_prompt(batch: list[dict], features: dict, q_to_kg: dict) -> str:
    """LLM-as-Judge C5_fix prompt (Gemini's recommended fix for Kaggle ASAG).

    Instead of feeding pre-matched concept names (which inflates scores via
    keyword presence), this prompt shows ALL expected KG concepts and asks the
    model to explicitly verify correctness of each BEFORE scoring.

    Step 1: For each expected concept, judge TRUE (correctly demonstrated) or
            FALSE (mentioned incorrectly, missed, or vague).
    Step 2: Score based ONLY on TRUE concepts.

    This prevents the 'bag-of-words confidence boost' where correct-sounding
    but wrong answers (e.g., 'plants take in oxygen') get inflated scores.
    """
    system = f"""{SCORING_GUIDE}

You are an expert grader using a two-step process:

STEP 1 — Concept Verification: For each expected concept listed, determine:
  TRUE = student correctly demonstrated this idea (even in their own words)
  FALSE = student missed it, mentioned it vaguely, or used it incorrectly

CRITICAL: A student who MENTIONS a concept word but explains it INCORRECTLY must be marked FALSE for that concept. Keyword presence alone does not count — correct meaning matters.

STEP 2 — Score: Based ONLY on the TRUE concepts, assign a score using the scoring guide above.

When no concept list is provided, grade using the reference answer only.

Return a single JSON object with only scores (no reasoning in output):
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
        use_kg = feat.get("use_kg", True)
        q = r["question"].strip()
        kg = q_to_kg.get(q, {})
        concepts = kg.get("concepts", [])
        expected_ids = kg.get("expected_concepts", [c["id"] for c in concepts])
        expected_concepts = [c for c in concepts if c["id"] in expected_ids]

        if not use_kg or not expected_concepts:
            parts.append(
                f"--- SAMPLE ID: {sid} ---\n"
                f"QUESTION: {r['question']}\n\n"
                f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
                f"STUDENT ANSWER:\n{r['student_answer']}"
            )
            continue

        concept_list = "\n".join(
            f"  {i+1}. {c.get('name', c['id'])}: {c.get('description', '')}"
            for i, c in enumerate(expected_concepts)
        )

        parts.append(
            f"--- SAMPLE ID: {sid} ---\n"
            f"QUESTION: {r['question']}\n\n"
            f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
            f"EXPECTED CONCEPTS (verify each TRUE/FALSE in student answer):\n"
            f"{concept_list}\n\n"
            f"STUDENT ANSWER:\n{r['student_answer']}"
        )

    header = f"{system}\n\n{'='*70}\n\n"
    body = "\n\n".join(parts)
    footer = f"\n\n{'='*70}\nGrade all {len(batch)} samples. Verify concept correctness first, then score. Return only the JSON object."
    return header + body + footer


def build_c5fix_coverage_prompt(batch: list[dict], features: dict) -> str:
    """C5_fix variant using coverage-ratio framing instead of concept lists.

    Instead of listing detected concept names (which inflates scores via keyword
    presence), this variant shows only the numeric coverage ratio and emphasises
    that a concept mention is only credited when the student explains it CORRECTLY.
    Designed for short-answer datasets (Kaggle ASAG) where concept-name leakage
    causes systematic over-scoring in the standard c5fix prompt.
    """
    system = f"""{SCORING_GUIDE}

You are an expert grader. Some samples include a KG COVERAGE SIGNAL — an automated estimate of how much of the expected conceptual content the student's answer covers. Use this signal as a rough guide only:

- Coverage ≥ 70%: student likely addressed most key ideas; verify this in the answer before scoring high
- Coverage 30–70%: partial coverage; score based on what is actually correct in the answer
- Coverage < 30%: few key ideas addressed; likely scores 0–2

IMPORTANT: Coverage is keyword-based and can be wrong. A student who MENTIONS a concept but explains it INCORRECTLY should NOT receive credit for it. Always verify against the reference answer.

When NO KG COVERAGE SIGNAL is shown, grade using only the question, reference answer, and student answer.

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
        use_kg = feat.get("use_kg", True)
        cov = feat.get("coverage_ratio", 0.0)

        if not use_kg:
            parts.append(
                f"--- SAMPLE ID: {sid} ---\n"
                f"QUESTION: {r['question']}\n\n"
                f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
                f"STUDENT ANSWER:\n{r['student_answer']}"
            )
            continue

        cov_pct = int(round(cov * 100))
        cov_label = "High" if cov >= 0.7 else ("Medium" if cov >= 0.3 else "Low")

        parts.append(
            f"--- SAMPLE ID: {sid} ---\n"
            f"QUESTION: {r['question']}\n\n"
            f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
            f"KG COVERAGE SIGNAL: {cov_pct}% ({cov_label}) — verify correctness in answer\n\n"
            f"STUDENT ANSWER:\n{r['student_answer']}"
        )

    header = f"{system}\n\n{'='*70}\n\n"
    body = "\n\n".join(parts)
    footer = f"\n\n{'='*70}\nGrade all {len(batch)} samples. Coverage is a guide — always verify against the reference. Return only the JSON object."
    return header + body + footer


def run(dataset: str, mode: str = "split") -> None:
    """Generate batch prompts. mode='split' generates separate cllm/c5fix batches (recommended).
    mode='dual' generates combined dual-score batches (legacy, causes anchoring).
    """
    os.makedirs(OUT_DIR, exist_ok=True)

    data_path = os.path.join(DATA_DIR, f"{dataset}_dataset.json")
    kg_path = f"/tmp/auto_kg_response_{dataset}.json"
    persistent_kg = os.path.join(DATA_DIR, f"{dataset}_auto_kg.json")
    q_idx_path = os.path.join(DATA_DIR, f"{dataset}_question_index.json")

    with open(data_path) as f:
        records = json.load(f)
    with open(q_idx_path) as f:
        q_index = json.load(f)

    # Build KG map (/tmp first, else copy from data/)
    if os.path.exists(kg_path):
        with open(kg_path) as f:
            kg_raw = json.load(f)
        question_kgs = kg_raw.get("question_kgs", kg_raw)
    elif os.path.exists(persistent_kg):
        with open(persistent_kg) as f:
            kg_raw = json.load(f)
        question_kgs = kg_raw.get("question_kgs", kg_raw)
        os.makedirs(os.path.dirname(kg_path) or ".", exist_ok=True)
        shutil.copy2(persistent_kg, kg_path)
        print(f"  Restored KG from {persistent_kg} → {kg_path}")
    else:
        print(f"WARNING: No KG file at {kg_path} or {persistent_kg} — empty KG features")
        question_kgs = {}

    q_to_kg: dict[str, dict] = {}
    for qi, q_entry in enumerate(q_index):
        kg_entry = question_kgs.get(str(qi), question_kgs.get(qi, {}))
        q_to_kg[q_entry["question"].strip()] = kg_entry

    embed_cache = ConceptEmbeddingCache(q_to_kg)
    if embed_cache.active:
        print(
            f"  Semantic: sentence-transformers ON ({len(embed_cache.ids)} unique concepts)"
        )
    else:
        print(
            "  Semantic: TF-IDF (sklearn) + keywords "
            "(optional: pip install sentence-transformers for embeddings)"
        )

    # Precompute KG features
    features = precompute_features(records, q_to_kg, embed_cache=embed_cache)
    feat_path = os.path.join(OUT_DIR, f"{dataset}_precomputed.json")
    with open(feat_path, "w") as f:
        json.dump(features, f, indent=2)
    persist_pre = os.path.join(DATA_DIR, f"{dataset}_precomputed.json")
    shutil.copy2(feat_path, persist_pre)
    print(f"Precomputed KG features → {feat_path} (+ {persist_pre})")

    n_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE
    total_chars = 0

    # Standard scoring guide for all datasets
    scoring_guide = None

    if mode == "split":
        # Generate separate cllm and c5fix batch files (prevents anchoring)
        for b in range(n_batches):
            batch = records[b * BATCH_SIZE: (b + 1) * BATCH_SIZE]

            cllm_prompt = build_cllm_prompt(batch, scoring_guide=scoring_guide)
            cllm_path = os.path.join(OUT_DIR, f"{dataset}_cllm_batch_{b+1:02d}.txt")
            with open(cllm_path, "w") as f:
                f.write(cllm_prompt)

            # Kaggle ASAG: LLM-as-Judge — verify each concept's correctness before scoring
            if dataset == "kaggle_asag":
                c5fix_prompt = build_c5fix_judge_prompt(batch, features, q_to_kg)
            else:
                c5fix_prompt = build_c5fix_prompt(batch, features, scoring_guide=scoring_guide)
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
