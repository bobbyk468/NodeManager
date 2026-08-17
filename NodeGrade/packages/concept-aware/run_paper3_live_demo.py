#!/usr/bin/env python3
"""
run_paper3_live_demo.py — a single, fresh, interactive walkthrough of the
real LongAnswerPipeline. This example is NOT part of the audited n=8
pilot set (pilot_set_v1.json) and does not touch that data or its
results — it exists purely to demonstrate, live, what the pipeline
actually does end-to-end (segmentation -> extraction -> depth ->
misconceptions -> verification -> feedback).

Same fixed config as the pilot run for consistency:
  model=gemini-2.5-flash, use_sure=True, use_cross_para=True
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

QUESTION = (
    "Explain how a doubly linked list works and how it can be used to "
    "implement a deque (double-ended queue). Discuss the tradeoffs "
    "compared to a singly linked list."
)

STUDENT_ANSWER = (
    "A doubly linked list is a linked list where each node stores two "
    "pointers instead of one: a next pointer to the following node, and "
    "a prev pointer to the preceding node. This is different from a "
    "singly linked list, where each node only knows about the node that "
    "comes after it.\n\n"
    "Because each node stores a next and a prev pointer, a doubly "
    "linked list can be traversed in both directions -- forward from "
    "the head or backward from the tail. This is what makes it a "
    "natural fit for implementing a deque, since a deque needs to "
    "support efficient insertion and removal at both ends. By keeping "
    "references to both the head and tail nodes, pushing or popping "
    "from either end is an O(1) operation: you just update a couple of "
    "pointers, no traversal required.\n\n"
    "The main cost of a doubly linked list compared to a singly linked "
    "list is the extra memory needed for the second pointer in every "
    "node, and the small extra bookkeeping cost of maintaining two "
    "pointers correctly during insertion and deletion instead of one. "
    "In exchange, you get backward traversal and O(1) removal of a "
    "given node if you already have a reference to it, which a singly "
    "linked list can't do efficiently since you'd need to walk from the "
    "head to find the node before it.\n\n"
    "One more advantage worth mentioning: since a doubly linked list "
    "stores its nodes contiguously in memory the way an array does, "
    "iterating through it sequentially is just as cache-friendly as "
    "iterating through an array, so the extra pointer overhead doesn't "
    "really cost you anything in practice for large lists."
)


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY", file=sys.stderr)
        return 1

    from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
    from conceptgrade.lag_pipeline import LongAnswerPipeline

    domain_graph = build_data_structures_graph()

    def log(stage, detail):
        print(f"  [{stage}] {detail}")

    print("=" * 78)
    print("LIVE DEMO — real LongAnswerPipeline, fresh example (not in the audited pilot)")
    print("=" * 78)
    print(f"\nQuestion:\n  {QUESTION}\n")
    print(f"Student answer ({len(STUDENT_ANSWER.split())} words):\n{STUDENT_ANSWER}\n")
    print("-" * 78)
    print("Running pipeline (model=gemini-2.5-flash, use_sure=True, use_cross_para=True)...\n")

    pipeline = LongAnswerPipeline(
        api_key=api_key,
        model="gemini-2.5-flash",
        domain_graph=domain_graph,
        use_sure=True,
        use_cross_para=True,
        on_progress=log,
    )

    t0 = time.time()
    result = pipeline.assess(
        question=QUESTION,
        student_answer=STUDENT_ANSWER,
        student_id="live_demo_doubly_linked_list",
    )
    elapsed = time.time() - t0

    d = result.to_dict()

    print("\n" + "=" * 78)
    print("RESULT")
    print("=" * 78)
    print(json.dumps(d, indent=2, default=str))

    out_path = os.path.join(os.path.dirname(__file__), "data", "paper3_longanswer", "live_demo_result.json")
    with open(out_path, "w") as f:
        json.dump(d, f, indent=2, default=str)
    print(f"\nWrote {out_path}")
    print(f"Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
