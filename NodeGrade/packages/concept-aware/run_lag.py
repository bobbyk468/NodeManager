#!/usr/bin/env python3
"""
ConceptGrade — Long Answer Grading (LAG) CLI

Grades a multi-paragraph student essay and prints results with live progress.

Usage
-----
  python -u run_lag.py --question "Q" --answer-file essay.txt [--model MODEL]
  python -u run_lag.py --question "Q" --answer "..." [--reference-file ref.txt]
  python -u run_lag.py --demo

Speed
-----
  Cache hit  : < 1s     (same essay graded before)
  First run  : ~15–25s  (wave-parallel: all segments scored simultaneously)

Wave parallelism breakdown (4-segment essay):
  Wave 1: Extract concepts — 4 calls in parallel    (~4s)
  Wave 2: Bloom's + Misconception — 8 calls parallel (~4s)
  Wave 3: KG comparison — no LLM                    (<0.1s)
  Wave 4: One verifier on full answer               (~4s)
  Wave 5: One feedback synthesis                    (~4s)
  Total : ~16–20s  (vs ~60–80s naive sequential)

Environment
-----------
  ANTHROPIC_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY  (matching the model)
"""

import argparse
import os
import sys
import time

# ── Detect API key ─────────────────────────────────────────────────────────────

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


# ── Progress callback ──────────────────────────────────────────────────────────

def make_progress_handler():
    stage_headers = {
        "segment":  "[ Segmentation ]",
        "wave1":    "[ Wave 1 — Concept Extraction ]",
        "wave2":    "[ Wave 2 — Depth + Misconceptions ]",
        "wave2b":   "[ Wave 2b — Cross-Paragraph Integration ]",
        "score":    "[ Segment Scores ]",
        "verify":   "[ Wave 4 — Holistic Verifier ]",
        "feedback": "[ Wave 5 — Feedback Synthesis ]",
        "cache":    "[ Cache ]",
    }
    last_stage = {"val": ""}

    def handler(stage: str, detail: str):
        if stage != last_stage["val"]:
            last_stage["val"] = stage
            header = stage_headers.get(stage, f"[ {stage} ]")
            print(f"\n{header}", flush=True)
        print(f"  {detail}", flush=True)

    return handler


# ── Output formatter ───────────────────────────────────────────────────────────

def print_header():
    print("=" * 65)
    print("  ConceptGrade — Long Answer Grading (LAG)")
    print("=" * 65)

def print_result(result):
    from conceptgrade.lag_pipeline import LongAnswerResult
    agg = result.aggregated
    fb  = result.feedback

    print()
    print("=" * 65)
    print("  RESULTS")
    print("=" * 65)

    # Per-segment breakdown
    if result.segment_scores:
        print()
        print("  Segment Breakdown:")
        print(f"  {'#':<4} {'Label':<28} {'Score':>6}  {'Blooms':<12} {'Misc':>4}")
        print("  " + "-" * 58)
        for ss in result.segment_scores:
            s5   = round(ss.kg_score * 5, 2)
            blm  = ss.blooms.get("label", "?")
            misc = ss.misconceptions.get("total_misconceptions", 0)
            peak = " ← ceiling" if ss.blooms.get("level", 1) == agg.ceiling_bloom_level else ""
            print(f"  {ss.segment.index:<4} {ss.segment.label:<28} {s5:>5.1f}/5  {blm:<12} {misc:>4}{peak}")

    # Depth profile
    print()
    bloom_arrow = " → ".join(
        f"S{i+1}:{l}" for i, l in
        zip(range(len(agg.bloom_sequence)),
            [f"L{b}" for b in agg.bloom_sequence])
    )
    print(f"  Depth Map   :  {bloom_arrow}")
    print(f"  Modal       :  {agg.modal_bloom_label} (Level {agg.modal_bloom_level}/6)")
    print(f"  Ceiling     :  {agg.ceiling_bloom_label} (Level {agg.ceiling_bloom_level}/6)")
    print(f"  Trajectory  :  {agg.depth_trajectory.capitalize()}")
    print(f"  Consistency :  {agg.consistency_index:.2f}  "
          f"({'disciplined' if agg.consistency_index >= 0.8 else 'variable'})")

    # Concepts
    print()
    print(f"  Concepts    :  {len(agg.covered_concepts)} covered", end="")
    if agg.missing_concepts:
        print(f" | Missing: {', '.join(agg.missing_concepts[:4])}")
    else:
        print()

    # Misconceptions
    if agg.misconceptions:
        print()
        print("  Misconceptions:")
        for m in agg.misconceptions[:3]:
            sev   = m.get("severity", "isolated").upper()
            desc  = m.get("description", m.get("concept", ""))[:70]
            print(f"    [{sev}] {desc}")

    # Cross-paragraph integration
    if getattr(agg, "integration", None):
        intg = agg.integration
        level    = intg.get("integration_level", "n/a")
        sem_cnt  = intg.get("semantic_bridge_count", 0)
        lex_cnt  = intg.get("lexical_bridge_count", 0)
        sem_str  = f"{sem_cnt} semantic bridge{'s' if sem_cnt != 1 else ''}"
        lex_str  = f"{lex_cnt} lexical bridge{'s' if lex_cnt != 1 else ''}"
        print(f"\n  Integration :  {level} ({sem_str}, {lex_str})")

    # Inter-chunk variance
    if agg.inter_chunk_variance > 0:
        variance_label = (
            "Low — consistent quality"
            if agg.inter_chunk_variance < 0.3 else
            "Moderate — some strong sections"
            if agg.inter_chunk_variance < 1.0 else
            "High — islands of brilliance"
        )
        print(f"\n  Variance    :  {agg.inter_chunk_variance:.3f} ({variance_label})")

    # SURE review flag
    if getattr(agg, "requires_human_review", False):
        sure_scores = getattr(agg, "sure_scores", [])
        spread_5 = (max(sure_scores) - min(sure_scores)) * 5 if sure_scores else 0.0
        scores_fmt = " / ".join(f"{s * 5:.1f}" for s in sure_scores)
        print()
        print(f"  ⚠  SURE REVIEW FLAG: Score spread = {spread_5:.2f}/5 — recommend human review")
        print(f"  SURE scores (Meticulous/Standard/Lenient): {scores_fmt}")

    # Final score
    print()
    print("─" * 65)
    print(f"  FINAL SCORE :  {agg.final_score:.1f} / 5.0")
    print("─" * 65)

    # Feedback
    print()
    print("  Feedback:")
    full_fb = fb.full_text()
    # Word-wrap at 65 chars
    words = full_fb.split()
    line  = "  "
    for word in words:
        if len(line) + len(word) + 1 > 65:
            print(line)
            line = "  " + word
        else:
            line += (" " if line.strip() else "") + word
    if line.strip():
        print(line)

    print()
    print(f"  Time: {result.elapsed_seconds:.1f}s", end="")
    if result.elapsed_seconds < 1.0:
        print("  ← cache hit")
    else:
        print()
    print("=" * 65)


# ── Demo data ──────────────────────────────────────────────────────────────────

DEMO_QUESTION = (
    "Discuss the memory management implications of using a Stack versus a Heap "
    "in a systems programming context. Include examples and compare their tradeoffs."
)

DEMO_ANSWER = """
A stack is a region of memory that operates in a last-in, first-out manner. When a
function is called, a stack frame is pushed containing local variables and the return
address. Memory allocation on the stack is extremely fast — it is simply a pointer
decrement. Stack memory is automatically reclaimed when the function returns, so there
is no risk of forgetting to free it.

The heap is used for dynamic memory allocation when the size of data is not known at
compile time. In C, malloc() reserves a block of memory on the heap and returns a
pointer to it. The programmer is responsible for calling free() to release it. Failure
to do so causes memory leaks, where memory is reserved but never returned to the
allocator. The heap is slower than the stack because the allocator must find a
suitably-sized free block, which takes O(log n) time in common implementations.

Unlike arrays stored on the stack, linked lists benefit from heap allocation because
nodes can be created dynamically at runtime without knowing the size in advance. There
is a trade-off, however: heap-allocated nodes incur pointer overhead and can cause
external fragmentation over time, where free memory is split into many small non-
contiguous blocks. This reduces cache efficiency compared to contiguous array storage,
which benefits from spatial locality. For latency-critical systems, stack allocation
or memory pools are preferred precisely because they avoid fragmentation.
""".strip()

DEMO_REFERENCE = (
    "Stack: LIFO region, fixed size, automatic deallocation, O(1) allocation. "
    "Heap: dynamic size, manual malloc/free, risk of leaks and fragmentation. "
    "Key tradeoffs: speed (stack) vs flexibility (heap); "
    "cache locality (stack/arrays) vs pointer overhead (heap/linked lists). "
    "Advanced: slab allocation, memory pools, NUMA effects."
)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ConceptGrade Long Answer Grading — multi-paragraph essays"
    )
    parser.add_argument("--question",        help="Assessment question text")
    parser.add_argument("--answer",          help="Student answer text (inline)")
    parser.add_argument("--answer-file",     help="Path to file containing the student answer")
    parser.add_argument("--reference",       default="", help="Reference answer text")
    parser.add_argument("--reference-file",  help="Path to reference answer file")
    parser.add_argument("--model",           default="claude-haiku-4-5-20251001",
                        help="LLM model name (auto-detects provider)")
    parser.add_argument("--segmenter-model", default=None,
                        help="Cheaper model for segmentation only (optional)")
    parser.add_argument("--feedback-model",  default=None,
                        help="Stronger model for feedback prose only (optional)")
    parser.add_argument("--student-id",      default="student")
    parser.add_argument("--demo",            action="store_true",
                        help="Run built-in 3-paragraph demo example")
    parser.add_argument("--sure",            action="store_true",
                        help="Enable SURE (3-persona ensemble) verification")
    parser.add_argument("--cross-para",      action="store_true",
                        help="Enable cross-paragraph integration detection (Wave 2b)")
    args = parser.parse_args()

    if args.demo:
        args.question  = DEMO_QUESTION
        args.answer    = DEMO_ANSWER
        args.reference = DEMO_REFERENCE

    if not args.question:
        parser.error("--question is required (or use --demo)")

    if args.answer_file:
        with open(args.answer_file) as f:
            answer = f.read().strip()
    elif args.answer:
        answer = args.answer
    else:
        parser.error("--answer or --answer-file is required (or use --demo)")

    if args.reference_file:
        with open(args.reference_file) as f:
            reference = f.read().strip()
    else:
        reference = args.reference

    api_key = get_api_key(args.model)

    print_header()
    print(f"\n  Question : {args.question[:80]}")
    wc = len(answer.split())
    print(f"  Answer   : {wc} words")
    print(f"  Model    : {args.model}")
    if args.segmenter_model:
        print(f"  Segmenter: {args.segmenter_model}")
    if args.feedback_model:
        print(f"  Feedback : {args.feedback_model}")
    if args.sure:
        print(f"  Verifier : SURE (3-persona ensemble)")
    if args.cross_para:
        print(f"  Cross-Para: integration detection enabled")

    from conceptgrade.lag_pipeline import LongAnswerPipeline

    progress = make_progress_handler()
    pipeline = LongAnswerPipeline(
        api_key=api_key,
        model=args.model,
        segmenter_model=args.segmenter_model,
        feedback_model=args.feedback_model,
        max_workers=8,
        on_progress=progress,
        use_sure=args.sure,
        use_cross_para=args.cross_para,
    )

    result = pipeline.assess(
        question=args.question,
        student_answer=answer,
        reference_answer=reference,
        student_id=args.student_id,
    )

    print_result(result)


if __name__ == "__main__":
    main()
