#!/usr/bin/env python3
"""
ConceptGrade — Short Answer Grading (SAG) CLI

Grades a single short student answer and prints results immediately.

Usage
-----
  python -u run_sag.py --question "Q" --answer "A" [--model MODEL]
  python -u run_sag.py --question "Q" --answer-file ans.txt [--reference "R"]
  python -u run_sag.py --demo

Speed
-----
  Cache hit  : < 1s  (same answer scored before)
  First run  : ~10–15s  (3–4 parallel-optimised LLM calls)

Environment
-----------
  ANTHROPIC_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY  (matching the model)
"""

import argparse
import os
import sys
import time

# ── Detect API key from environment ──────────────────────────────────────────

def get_api_key(model: str) -> str:
    from conceptgrade.llm_client import detect_provider
    provider = detect_provider(model)
    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "google":    "GEMINI_API_KEY",
        "openai":    "OPENAI_API_KEY",
    }
    env_var = key_map.get(provider, "ANTHROPIC_API_KEY")
    key = os.environ.get(env_var, "")
    if not key:
        print(f"ERROR: Set {env_var} for model '{model}'", file=sys.stderr)
        sys.exit(1)
    return key


# ── Pretty output ─────────────────────────────────────────────────────────────

def print_header():
    print("=" * 60)
    print("  ConceptGrade — Short Answer Grading (SAG)")
    print("=" * 60)

def print_result(assessment, elapsed: float, hierarchical: bool = False):
    score_5 = round(assessment.overall_score * 5.0, 2)
    scores  = assessment.comparison.get("scores", {})
    cov     = scores.get("concept_coverage", 0.0)
    acc     = scores.get("relationship_accuracy", 0.0)
    intg    = scores.get("integration_quality", 0.0)

    bloom_lbl = assessment.blooms.get("label", "?")
    bloom_lvl = assessment.blooms.get("level", 1)
    solo_lbl  = assessment.solo.get("label", "?")
    solo_lvl  = assessment.solo.get("level", 1)
    n_misc    = assessment.misconceptions.get("total_misconceptions", 0)

    print()
    print(f"  Score       :  {score_5:.1f} / 5.0")
    if hierarchical and "primary_coverage" in scores:
        p_cov    = scores.get("primary_coverage", 0.0)
        s_cov    = scores.get("secondary_coverage", 0.0)
        hier_raw = min(1.0, p_cov * 0.80 + s_cov * 0.20)
        hier_5   = hier_raw * 5.0
        print(f"  KG Coverage :  Primary {p_cov:.0%}  Secondary {s_cov:.0%}  →  Score {hier_5:.1f}/5")
    else:
        print(f"  KG Coverage :  {cov:.0%}  (accuracy {acc:.0%}, integration {intg:.0%})")
    print(f"  Bloom's     :  {bloom_lbl} (Level {bloom_lvl}/6)")
    print(f"  SOLO        :  {solo_lbl} (Level {solo_lvl}/5)")
    print(f"  Misconceptions: {n_misc}")
    print(f"  Depth       :  {assessment.depth_category}")

    if assessment.verifier:
        ver = assessment.verifier
        print()
        print(f"  Verifier    :  KG {ver.get('kg_score',0)*5:.1f}/5 → "
              f"LLM {ver.get('verified_score',0)*5:.0f}/5 "
              f"({ver.get('adjustment_direction','?')}) → "
              f"Final {ver.get('final_score',0)*5:.2f}/5")

    # Misconception details
    miscs = assessment.misconceptions.get("misconceptions", [])
    if miscs:
        print()
        print("  Misconceptions detected:")
        for m in miscs[:3]:
            sev   = m.get("severity", "minor")
            claim = m.get("student_claim", m.get("explanation", ""))[:80]
            print(f"    [{sev.upper()}] {claim}")

    # Missing concepts
    missing = assessment.comparison.get("analysis", {}).get("missing_concepts", [])
    if missing:
        ids = [mc.get("id", mc) if isinstance(mc, dict) else str(mc)
               for mc in missing[:5]]
        print(f"\n  Missing concepts: {', '.join(ids)}")

    print()
    print(f"  Time: {elapsed:.1f}s", end="")
    if elapsed < 1.0:
        print("  ← cache hit")
    else:
        print()
    print("=" * 60)


# ── Demo data ─────────────────────────────────────────────────────────────────

DEMO_QUESTION = "What is a linked list and how does insertion at the head work?"
DEMO_ANSWER   = (
    "A linked list is a linear data structure where each element is a node "
    "containing data and a pointer to the next node. The first node is called "
    "the head. Insertion at the head works by creating a new node, setting its "
    "next pointer to the current head, and then updating the head pointer to "
    "the new node. This takes O(1) time since we don't need to traverse the list."
)
DEMO_REFERENCE = (
    "A linked list is a sequence of nodes where each node stores data and a "
    "pointer to the next node. The head pointer references the first node. "
    "To insert at the head: create a new node, set new_node.next = head, "
    "then set head = new_node. This is O(1) time complexity."
)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ConceptGrade Short Answer Grading — single answer, instant output"
    )
    parser.add_argument("--question",     help="Assessment question text")
    parser.add_argument("--answer",       help="Student answer text")
    parser.add_argument("--answer-file",  help="Path to file containing the student answer")
    parser.add_argument("--reference",    default="", help="Reference/model answer (optional)")
    parser.add_argument("--model",        default="claude-haiku-4-5-20251001",
                        help="LLM model name (auto-detects provider)")
    parser.add_argument("--student-id",   default="student", help="Student identifier")
    parser.add_argument("--demo",         action="store_true", help="Run built-in demo example")
    parser.add_argument("--hierarchical", action="store_true",
                        help="Use hierarchical KG scoring (primary 80%% + secondary 20%%)")
    args = parser.parse_args()

    # Demo mode
    if args.demo:
        args.question  = DEMO_QUESTION
        args.answer    = DEMO_ANSWER
        args.reference = DEMO_REFERENCE

    if not args.question:
        parser.error("--question is required (or use --demo)")
    if not args.answer and not args.answer_file:
        parser.error("--answer or --answer-file is required (or use --demo)")

    if args.answer_file:
        with open(args.answer_file) as f:
            answer = f.read().strip()
    else:
        answer = args.answer

    api_key = get_api_key(args.model)

    print_header()
    print(f"\n  Question : {args.question[:80]}")
    print(f"  Answer   : {answer[:80]}{'...' if len(answer) > 80 else ''}")
    print(f"  Model    : {args.model}")
    print()
    print("  Grading...", flush=True)

    from conceptgrade.pipeline import ConceptGradePipeline

    t0 = time.time()
    pipeline = ConceptGradePipeline(
        api_key=api_key,
        model=args.model,
        rate_limit_delay=0.3,
        use_self_consistency=False,
        use_confidence_weighting=True,
        use_llm_verifier=True,
        verifier_weight=1.0,
        use_hierarchical_kg=args.hierarchical,
    )
    assessment = pipeline.assess_student(
        student_id=args.student_id,
        question=args.question,
        answer=answer,
        reference_answer=args.reference,
    )
    elapsed = time.time() - t0

    print_result(assessment, elapsed, hierarchical=args.hierarchical)


if __name__ == "__main__":
    main()
