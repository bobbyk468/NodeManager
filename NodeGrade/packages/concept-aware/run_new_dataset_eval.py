"""
Full ConceptGrade evaluation on a new dataset.

Pipeline for DigiKlausur or Kaggle ASAG:
  1. Loads dataset JSON + auto-generated KG from Gemini
  2. For each sample: extracts matched concepts, chain coverage, SOLO/Bloom via LLM
  3. Grades with C_LLM (baseline) and C5_fix (KG-augmented)
  4. Computes MAE, QWK, Pearson r, Spearman rho, bias
  5. Saves results to data/{dataset}_eval_results.json

Requires:
  data/{dataset}_dataset.json             — student answers + human scores
  /tmp/auto_kg_response_{dataset}.json    — Gemini KG response
  GEMINI_API_KEY in backend/.env          — for LLM grading calls

Usage:
    python3 run_new_dataset_eval.py --dataset digiklausur [--n 50]
    python3 run_new_dataset_eval.py --dataset kaggle_asag [--n 100]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from scipy.stats import pearsonr, spearmanr, wilcoxon
from sklearn.metrics import cohen_kappa_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
sys.path.insert(0, BASE_DIR)

from concept_matching import ConceptEmbeddingCache, unified_concept_match

BACKEND_ENV = os.path.join(BASE_DIR, "..", "backend", ".env")

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


def load_api_key() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    env_path = os.path.abspath(BACKEND_ENV)
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key
    raise RuntimeError("GEMINI_API_KEY not found")


def build_cllm_prompt(question: str, reference: str, student: str) -> str:
    return (
        f"{SCORING_GUIDE}\n\n"
        f"QUESTION: {question}\n\n"
        f"REFERENCE ANSWER:\n{reference}\n\n"
        f"STUDENT ANSWER:\n{student}\n\n"
        f'Return JSON: {{"holistic_score": X.X}}'
    )


def build_c5_prompt(
    question: str, reference: str, student: str,
    concepts: list[str], chain_pct: str,
    solo_label: str, bloom_label: str,
) -> str:
    covered = ", ".join(concepts) if concepts else "none identified"
    return (
        f"{SCORING_GUIDE}\n\n"
        f"QUESTION: {question}\n\n"
        f"REFERENCE ANSWER:\n{reference}\n\n"
        f"KG EVIDENCE:\n"
        f"- Concepts demonstrated: {covered}\n"
        f"- Causal chain coverage: {chain_pct}\n"
        f"- Bloom's level: {bloom_label}\n"
        f"- SOLO level: {solo_label}\n\n"
        f"STUDENT ANSWER:\n{student}\n\n"
        f'Return JSON: {{"holistic_score": X.X}}'
    )


def call_gemini(client, prompt: str, model: str = "gemini-2.0-flash") -> float:
    from conceptgrade.llm_client import parse_llm_json
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=64,
        json_mode=True,
    )
    raw = response.choices[0].message.content
    parsed = parse_llm_json(raw)
    return float(parsed.get("holistic_score", parsed.get("score", 0.0)))


def classify_solo(matched: list[str], total_expected: int) -> tuple[str, int]:
    ratio = len(matched) / max(total_expected, 1)
    if ratio == 0:
        return "Prestructural", 1
    elif ratio <= 0.25:
        return "Unistructural", 2
    elif ratio <= 0.60:
        return "Multistructural", 3
    elif ratio <= 0.85:
        return "Relational", 4
    else:
        return "Extended Abstract", 5


def classify_bloom(student_answer: str) -> tuple[str, int]:
    """Heuristic Bloom classification based on answer patterns."""
    a = student_answer.lower()
    if any(w in a for w in ["because", "therefore", "which means", "this causes", "as a result"]):
        return "Analyze", 4
    if any(w in a for w in ["explains", "describe", "how", "why", "process", "mechanism"]):
        return "Understand", 2
    return "Remember", 1


def main(dataset: str, n_samples: int | None, dry_run: bool = False) -> None:
    print(f"{'='*70}")
    print(f"ConceptGrade Evaluation on {dataset}")
    print(f"{'='*70}")

    # Load dataset
    data_path = os.path.join(DATA_DIR, f"{dataset}_dataset.json")
    with open(data_path) as f:
        records = json.load(f)

    # Load auto-generated KG
    kg_path = f"/tmp/auto_kg_response_{dataset}.json"
    if not os.path.exists(kg_path):
        print(f"ERROR: {kg_path} not found.")
        print(f"  1. Send /tmp/auto_kg_prompt_{dataset}.txt to Gemini")
        print(f"  2. Save response to {kg_path}")
        sys.exit(1)

    with open(kg_path) as f:
        kg_raw = json.load(f)
    question_kgs = kg_raw.get("question_kgs", kg_raw)

    # Build question → KG mapping by question text
    q_idx_path = os.path.join(DATA_DIR, f"{dataset}_question_index.json")
    with open(q_idx_path) as f:
        q_index = json.load(f)

    # Map question text → KG data (KG keyed by numeric index 0..N)
    q_to_kg: dict[str, dict] = {}
    for qi, q_entry in enumerate(q_index):
        kg_entry = question_kgs.get(str(qi), question_kgs.get(qi, {}))
        q_to_kg[q_entry["question"].strip()] = kg_entry

    # Limit samples
    if n_samples:
        records = records[:n_samples]

    print(f"Loaded {len(records)} samples, {len(q_to_kg)} KGs")

    embed_cache = ConceptEmbeddingCache(q_to_kg)

    if dry_run:
        print("DRY RUN — showing first 3 prompt pairs")
        for r in records[:3]:
            q = r["question"].strip()
            kg = q_to_kg.get(q, {})
            concepts = kg.get("concepts", [])
            matched = unified_concept_match(
                r["student_answer"], concepts, cache=embed_cache
            )
            solo_label, _ = classify_solo(matched, len(concepts))
            bloom_label, _ = classify_bloom(r["student_answer"])
            print(f"  ID {r['id']}: matched={matched}, solo={solo_label}, bloom={bloom_label}")
        return

    # Load Gemini client
    api_key = load_api_key()
    from conceptgrade.llm_client import LLMClient
    client = LLMClient(api_key=api_key)

    results = []
    errors = []

    for idx, r in enumerate(records):
        if idx % 10 == 0:
            print(f"  Processing {idx}/{len(records)}...")

        q = r["question"].strip()
        kg = q_to_kg.get(q, {})
        concepts = kg.get("concepts", [])
        expected = kg.get("expected_concepts", [c["id"] for c in concepts])
        matched = unified_concept_match(
            r["student_answer"], concepts, cache=embed_cache
        )
        chain_pct = f"{min(len(matched)/max(len(expected),1), 1.0):.0%}"
        solo_label, _ = classify_solo(matched, len(expected))
        bloom_label, _ = classify_bloom(r["student_answer"])

        try:
            # C_LLM: pure LLM, no KG
            score_cllm = call_gemini(
                client,
                build_cllm_prompt(q, r["reference_answer"], r["student_answer"]),
            )
            time.sleep(0.1)

            # C5_fix: full KG evidence
            score_c5 = call_gemini(
                client,
                build_c5_prompt(
                    q, r["reference_answer"], r["student_answer"],
                    matched, chain_pct, solo_label, bloom_label,
                ),
            )
            time.sleep(0.1)

            results.append({
                "id": r["id"],
                "human_score": r["human_score"],
                "cllm_score": score_cllm,
                "c5_score": score_c5,
                "matched_concepts": matched,
                "chain_pct": chain_pct,
                "solo": solo_label,
                "bloom": bloom_label,
            })

        except Exception as e:
            errors.append({"id": r["id"], "error": str(e)})
            print(f"    ERROR on ID {r['id']}: {e}")

    # Compute metrics
    human = np.array([r["human_score"] for r in results])
    cllm_scores = np.array([r["cllm_score"] for r in results])
    c5_scores = np.array([r["c5_score"] for r in results])

    def compute_metrics(pred):
        r, _ = pearsonr(human, pred)
        rho, _ = spearmanr(human, pred)
        mae = float(np.mean(np.abs(human - pred)))
        bias = float(np.mean(pred - human))
        hi = np.round(human * 4).astype(int)
        pi = np.round(pred * 4).astype(int)
        qwk = float(cohen_kappa_score(hi, pi, weights="quadratic"))
        return dict(mae=mae, r=r, rho=rho, qwk=qwk, bias=bias)

    m_cllm = compute_metrics(cllm_scores)
    m_c5 = compute_metrics(c5_scores)

    try:
        _, p_wil = wilcoxon(np.abs(c5_scores - human), np.abs(cllm_scores - human))
    except Exception:
        p_wil = 1.0

    print()
    print(f"{'='*70}")
    print(f"RESULTS — {dataset} (n={len(results)})")
    print(f"{'='*70}")
    print(f"  {'System':40} {'MAE':7} {'r':7} {'rho':7} {'QWK':7} {'Bias':7}")
    print("  " + "-" * 60)
    print(f"  {'C_LLM (no KG)':40} {m_cllm['mae']:.4f}  {m_cllm['r']:.4f}  {m_cllm['rho']:.4f}  {m_cllm['qwk']:.4f}  {m_cllm['bias']:+.4f}")
    print(f"  {'C5_fix / ConceptGrade':40} {m_c5['mae']:.4f}  {m_c5['r']:.4f}  {m_c5['rho']:.4f}  {m_c5['qwk']:.4f}  {m_c5['bias']:+.4f}")
    print(f"  Wilcoxon p (C5 vs C_LLM): {p_wil:.4f}")
    print(f"  MAE reduction: {(m_cllm['mae']-m_c5['mae'])/m_cllm['mae']*100:.1f}%")

    # Save
    out = {
        "dataset": dataset,
        "n": len(results),
        "n_errors": len(errors),
        "metrics": {"C_LLM": m_cllm, "C5_fix": m_c5},
        "wilcoxon_p": float(p_wil),
        "results": results,
        "errors": errors,
    }
    out_path = os.path.join(DATA_DIR, f"{dataset}_eval_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["digiklausur", "kaggle_asag"], required=True)
    parser.add_argument("--n", type=int, default=None, help="Limit to first N samples")
    parser.add_argument("--dry-run", action="store_true", help="Show prompts without calling API")
    args = parser.parse_args()
    main(args.dataset, args.n, args.dry_run)
