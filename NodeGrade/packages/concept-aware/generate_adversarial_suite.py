#!/usr/bin/env python3
"""
Adversarial Test Suite Generator — 100-scenario Vulnerability Matrix.

Uses Gemini to act as an "Adversarial Student" and generate test cases
covering seven failure modes for ConceptGrade stress testing.

Vulnerability Matrix:
  1. Standard Mastery      (20) — high-quality correct answers
  2. Prose Trap            (15) — academic-sounding but semantically empty
  3. Adjective Injection   (15) — errors hidden behind adverbs/adjectives
  4. Silent Hallucination  (15) — plausible but invented CS concepts
  5. Structural Split      (15) — contradictions across essay paragraphs
  6. Breadth Bluffer       (10) — all concepts named, none explained
  7. Code-Logic Drift      (10) — code described correctly but logic is broken

Output: data/adversarial_benchmark.json

Usage:
  export GEMINI_API_KEY="your-key"
  python generate_adversarial_suite.py [--output data/adversarial_benchmark.json]
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conceptgrade.llm_client import LLMClient, parse_llm_json

# ── CS topics to rotate across categories ────────────────────────────────────
CS_TOPICS = [
    {
        "topic": "Hash Tables",
        "question": "How does a Hash Table handle collisions?",
        "reference_answer": (
            "A hash table handles collisions using strategies such as chaining "
            "(each bucket stores a linked list of entries that hash to the same slot) "
            "or open addressing (linear probing, quadratic probing, or double hashing "
            "to find the next available slot). Load factor determines when resizing "
            "occurs to maintain O(1) average-case performance."
        ),
        "key_concepts": ["collision resolution", "chaining", "open addressing",
                         "linear probing", "load factor", "hash function"],
    },
    {
        "topic": "Binary Search Trees",
        "question": "Explain how a Binary Search Tree maintains sorted order and supports efficient search.",
        "reference_answer": (
            "A BST stores values such that every node's left subtree contains only "
            "smaller values and every right subtree contains only larger values. "
            "Search traverses left or right based on comparison, achieving O(log n) "
            "average-case performance. Inorder traversal visits nodes in sorted order. "
            "Worst-case O(n) occurs when the tree degenerates into a linked list."
        ),
        "key_concepts": ["BST property", "inorder traversal", "O(log n) search",
                         "left subtree", "right subtree", "degenerate tree"],
    },
    {
        "topic": "Virtual Memory",
        "question": "What is virtual memory and how does demand paging work?",
        "reference_answer": (
            "Virtual memory abstracts physical RAM by giving each process its own "
            "address space. Demand paging loads pages from disk only when they are "
            "accessed (page fault). The OS uses a page table to map virtual addresses "
            "to physical frames. When a page is not in memory, a page fault triggers "
            "the OS to load it from the swap space, possibly evicting another page "
            "using a replacement policy such as LRU or FIFO."
        ),
        "key_concepts": ["virtual address space", "page table", "page fault",
                         "demand paging", "LRU", "swap space", "physical frame"],
    },
    {
        "topic": "TCP vs UDP",
        "question": "Compare TCP and UDP in terms of reliability, ordering, and use cases.",
        "reference_answer": (
            "TCP provides reliable, ordered delivery using a three-way handshake, "
            "sequence numbers, acknowledgements, and retransmission of lost packets. "
            "It is suited for HTTP, email, and file transfers. UDP is connectionless, "
            "with no guarantee of delivery or ordering, making it faster and suited "
            "for DNS lookups, live streaming, and online gaming where low latency "
            "matters more than reliability."
        ),
        "key_concepts": ["reliable delivery", "three-way handshake", "sequence numbers",
                         "acknowledgements", "connectionless", "latency", "retransmission"],
    },
    {
        "topic": "Garbage Collection",
        "question": "Describe mark-and-sweep garbage collection and its trade-offs.",
        "reference_answer": (
            "Mark-and-sweep has two phases: the mark phase traverses all reachable "
            "objects from GC roots and marks them live; the sweep phase scans the heap "
            "and reclaims unmarked (unreachable) objects. Trade-offs include stop-the-world "
            "pauses during collection, fragmentation of freed memory, and O(heap size) "
            "sweep cost regardless of live set size. Generational GC reduces pause times "
            "by collecting young objects more frequently."
        ),
        "key_concepts": ["mark phase", "sweep phase", "GC roots", "reachable objects",
                         "stop-the-world", "heap fragmentation", "generational GC"],
    },
    {
        "topic": "CPU Scheduling",
        "question": "Explain Round Robin CPU scheduling and its relationship to time quantum.",
        "reference_answer": (
            "Round Robin assigns each process a fixed CPU time slice (quantum) in "
            "circular order. When a process exhausts its quantum without completing, "
            "it is preempted and placed at the back of the ready queue. A short quantum "
            "improves responsiveness but increases context-switch overhead. A long quantum "
            "approaches FCFS behaviour. Turnaround time and waiting time depend on "
            "the quantum size and the number of processes."
        ),
        "key_concepts": ["time quantum", "preemption", "ready queue", "context switch",
                         "turnaround time", "FCFS", "circular order"],
    },
    {
        "topic": "Graph Algorithms — Dijkstra",
        "question": "How does Dijkstra's algorithm find shortest paths and what are its limitations?",
        "reference_answer": (
            "Dijkstra's algorithm maintains a priority queue of nodes ordered by "
            "tentative distance from the source. It repeatedly extracts the minimum-"
            "distance node, relaxes its edges, and updates neighbours' distances. "
            "With a binary heap, complexity is O((V+E) log V). Key limitation: it "
            "requires non-negative edge weights. Bellman-Ford handles negative weights "
            "but runs in O(VE)."
        ),
        "key_concepts": ["priority queue", "edge relaxation", "tentative distance",
                         "non-negative weights", "O(V+E log V)", "Bellman-Ford"],
    },
    {
        "topic": "Sorting — Merge Sort",
        "question": "Explain the merge sort algorithm, its time complexity, and space trade-offs.",
        "reference_answer": (
            "Merge sort divides the array in half recursively until subarrays of size 1 "
            "remain, then merges them in sorted order. The merge step compares elements "
            "from two sorted halves and builds a sorted output array. Time complexity is "
            "O(n log n) in all cases. Space complexity is O(n) due to the auxiliary array. "
            "Unlike quicksort, merge sort is stable and guarantees worst-case O(n log n)."
        ),
        "key_concepts": ["divide and conquer", "merge step", "O(n log n)", "stable sort",
                         "auxiliary space", "recursive halving"],
    },
    {
        "topic": "Operating Systems — Deadlock",
        "question": "What are the four necessary conditions for deadlock and how can it be prevented?",
        "reference_answer": (
            "Coffman's four conditions for deadlock: mutual exclusion (only one process "
            "holds a resource at a time), hold and wait (a process holds a resource while "
            "waiting for another), no preemption (resources cannot be forcibly taken), and "
            "circular wait (a cycle exists in the resource-allocation graph). Prevention "
            "eliminates at least one condition — e.g., imposing a resource ordering to "
            "break circular wait, or requiring processes to request all resources upfront "
            "to eliminate hold and wait."
        ),
        "key_concepts": ["mutual exclusion", "hold and wait", "no preemption",
                         "circular wait", "Coffman conditions", "resource ordering"],
    },
    {
        "topic": "Memory Management — Stack vs Heap",
        "question": "Compare stack and heap memory allocation in terms of lifetime, speed, and use cases.",
        "reference_answer": (
            "Stack memory is LIFO-managed, allocated automatically when a function is "
            "called and freed when it returns; allocation is O(1) via stack pointer move. "
            "Heap memory is dynamically allocated (malloc/new) and persists until "
            "explicitly freed (free/delete) or garbage collected. Stack is faster and "
            "avoids fragmentation but is limited in size; heap supports large allocations "
            "and arbitrary lifetimes but risks fragmentation and memory leaks."
        ),
        "key_concepts": ["LIFO", "stack pointer", "dynamic allocation", "malloc",
                         "heap fragmentation", "memory leak", "lifetime"],
    },
]


# ── Category specifications ───────────────────────────────────────────────────
CATEGORIES = [
    {
        "name": "Standard Mastery",
        "code": "mastery",
        "count": 20,
        "description": "High-quality correct student answers. Covers all key concepts accurately.",
        "generation_instruction": (
            "Generate a high-quality student answer that correctly covers ALL key concepts "
            "in the reference answer. Use clear, accurate, technical language. "
            "The answer should score 4.5–5.0/5 against the reference."
        ),
        "expected_score_range": [4.0, 5.0],
        "answer_type": "sag",
    },
    {
        "name": "Prose Trap",
        "code": "prose_trap",
        "count": 15,
        "description": "Academic-sounding prose that contains ZERO correct technical content.",
        "generation_instruction": (
            "Generate an answer that sounds like it was written by a PhD student "
            "(sophisticated vocabulary, formal tone, complex sentence structure) "
            "but contains NO correct technical information. Use real-sounding but "
            "wrong mechanisms. The answer should genuinely score 0–0.5/5. "
            "Example pattern: 'The system employs a recursive disambiguation protocol "
            "that systematically enumerates contextual references...' — sounds smart, means nothing."
        ),
        "expected_score_range": [0.0, 1.0],
        "answer_type": "sag",
    },
    {
        "name": "Adjective Injection",
        "code": "adjective_injection",
        "count": 15,
        "description": "Wrong answers where errors are hidden behind adverbs and adjectives.",
        "generation_instruction": (
            "Generate an answer that contains a critical factual error, but disguise the "
            "error using confident, precise-sounding adverbs like: 'remarkably', "
            "'effectively', 'perfectly', 'seamlessly', 'optimally', 'instantaneously'. "
            "The core claim must be factually wrong (e.g. 'Hash tables remarkably "
            "eliminate all collisions instantly'). The answer should score 0.5–1.5/5. "
            "A pure LLM will be fooled by the confident language; ConceptGrade should detect the misconception."
        ),
        "expected_score_range": [0.5, 2.0],
        "answer_type": "sag",
    },
    {
        "name": "Silent Hallucination",
        "code": "hallucination",
        "count": 15,
        "description": "Technically plausible but completely invented CS concepts.",
        "generation_instruction": (
            "Generate an answer that invents a fake but plausible-sounding CS mechanism. "
            "Use real CS terminology patterns but invent the actual concept name and mechanism. "
            "Examples: 'JVM Temporal-Heap Coalescing Protocol', 'Stochastic Disambiguation Buffer', "
            "'Predictive Hash Rebalancing via Eigenvalue Decomposition'. "
            "The invented mechanism should sound authoritative. Score should be 0–1/5. "
            "A pure LLM may believe the invented concept is real; ConceptGrade finds zero KG matches."
        ),
        "expected_score_range": [0.0, 1.0],
        "answer_type": "sag",
    },
    {
        "name": "Breadth Bluffer",
        "code": "breadth_bluffer",
        "count": 10,
        "description": "Lists every concept keyword from the topic without explaining any of them.",
        "generation_instruction": (
            "Generate an answer that mentions every single concept keyword from the key_concepts "
            "list, but does NOT explain any of them — just lists them or uses them in vague "
            "one-word sentences. Example: 'BSTs use BST property, inorder traversal, O(log n) "
            "search, left subtree, right subtree, and degenerate tree considerations.' "
            "The answer covers all keywords but has Bloom's level 1 (Remember only). "
            "Score should be 1.5–2.5/5. A pure LLM may be fooled by keyword coverage "
            "and over-score; ConceptGrade's Bloom classifier should cap the score."
        ),
        "expected_score_range": [1.5, 2.5],
        "answer_type": "sag",
    },
    {
        "name": "Code-Logic Drift",
        "code": "code_logic_drift",
        "count": 10,
        "description": "Correct terminology with a described algorithm that has a logical infinite-loop bug.",
        "generation_instruction": (
            "Generate an answer that describes an algorithm using correct CS terminology "
            "but introduces a subtle logical error that would cause an infinite loop or "
            "incorrect termination. Example: describing Dijkstra's but the relaxation "
            "condition is inverted (update if new_dist > current), or describing merge sort "
            "but the base case is never reached because the halving is wrong. "
            "Use correct vocabulary throughout. Score should be 1.5–2.5/5 because "
            "the logic is broken even though terminology is correct."
        ),
        "expected_score_range": [1.0, 2.5],
        "answer_type": "sag",
    },
    {
        "name": "Structural Split",
        "code": "structural_split",
        "count": 15,
        "description": "Long-form essays with direct contradictions between early and late paragraphs.",
        "generation_instruction": (
            "Generate a multi-paragraph ESSAY (5–7 paragraphs, 300–500 words total) where "
            "Paragraph 1 makes a factually correct claim about a concept, and Paragraph 4 or 5 "
            "directly contradicts that claim. The contradiction must be explicit. "
            "Example: Para 1: 'BSTs achieve O(log n) search by leveraging sorted structure.' "
            "Para 5: 'Arrays are superior to BSTs for O(log n) search operations.' "
            "The rest of the essay should be moderately correct. Score should be 2.0–3.0/5."
        ),
        "expected_score_range": [2.0, 3.5],
        "answer_type": "lag",
    },
]


# ── System prompt for adversarial generation ─────────────────────────────────
GENERATOR_SYSTEM = """You are an expert CS educator who also acts as an adversarial test case generator.
Your job is to generate synthetic student answers with specific characteristics for testing automated graders.
Follow the instructions exactly. Generate ONLY the student answer text, no commentary.
Return ONLY valid JSON."""

GENERATOR_USER = """TOPIC: {topic}
QUESTION: {question}
REFERENCE ANSWER: {reference_answer}
KEY CONCEPTS: {key_concepts}

TASK: {generation_instruction}

Return ONLY valid JSON:
{{
  "student_answer": "<the generated student answer>",
  "ground_truth_score": <float 0.0–5.0, your best estimate of what a human grader would give>,
  "generation_notes": "<one sentence: what specific technique was used in this answer>"
}}"""


def generate_case(client: LLMClient, model: str, topic_info: dict, category: dict) -> dict:
    """Generate a single test case for a given topic and category."""
    user_prompt = GENERATOR_USER.format(
        topic=topic_info["topic"],
        question=topic_info["question"],
        reference_answer=topic_info["reference_answer"],
        key_concepts=", ".join(topic_info["key_concepts"]),
        generation_instruction=category["generation_instruction"],
    )

    raw = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": GENERATOR_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=1500,
    )
    parsed = parse_llm_json(raw.choices[0].message.content)

    return {
        "id": None,  # filled in by caller
        "category": category["name"],
        "category_code": category["code"],
        "answer_type": category["answer_type"],
        "topic": topic_info["topic"],
        "question": topic_info["question"],
        "reference_answer": topic_info["reference_answer"],
        "key_concepts": topic_info["key_concepts"],
        "student_answer": parsed["student_answer"],
        "ground_truth_score": float(parsed.get("ground_truth_score", 2.5)),
        "expected_score_range": category["expected_score_range"],
        "generation_notes": parsed.get("generation_notes", ""),
    }


def main():
    ap = argparse.ArgumentParser(description="Generate adversarial test suite for ConceptGrade")
    ap.add_argument("--model", default="gemini-flash-latest",
                    help="Gemini model to use for generation")
    ap.add_argument("--output", default="data/adversarial_benchmark.json",
                    help="Output path for generated benchmark")
    ap.add_argument("--category", default=None,
                    help="Generate only a specific category (by code, e.g. 'prose_trap')")
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = LLMClient(api_key=api_key)
    print(f"Adversarial Suite Generator")
    print(f"Model: {args.model}")
    print(f"Output: {args.output}")
    print("=" * 60)

    # Load existing output if resuming
    existing = {}
    if os.path.exists(args.output):
        with open(args.output) as f:
            existing_list = json.load(f)
        existing = {c["id"]: c for c in existing_list if "id" in c}
        print(f"Resuming — {len(existing)} cases already generated")

    categories_to_run = CATEGORIES
    if args.category:
        categories_to_run = [c for c in CATEGORIES if c["code"] == args.category]
        if not categories_to_run:
            print(f"ERROR: unknown category code '{args.category}'")
            sys.exit(1)

    all_cases = list(existing.values())
    case_id = max((c["id"] for c in all_cases if c["id"] is not None), default=0)

    total_target = sum(c["count"] for c in categories_to_run)
    generated = 0

    for cat in categories_to_run:
        # Count how many already exist for this category
        existing_cat = [c for c in all_cases if c["category_code"] == cat["code"]]
        remaining = cat["count"] - len(existing_cat)
        if remaining <= 0:
            print(f"  {cat['name']:25s} — already complete ({cat['count']} cases)")
            continue

        print(f"\n  {cat['name']} — generating {remaining} cases...")

        # Cycle through topics to ensure variety
        topic_idx = len(existing_cat)
        for i in range(remaining):
            topic = CS_TOPICS[topic_idx % len(CS_TOPICS)]
            topic_idx += 1
            case_id += 1

            try:
                case = generate_case(client, args.model, topic, cat)
                case["id"] = case_id
                all_cases.append(case)
                generated += 1

                score = case["ground_truth_score"]
                notes_preview = case["generation_notes"][:60]
                print(f"    [{case_id:3d}] {cat['code']:20s} | GT={score:.1f} | {notes_preview}")

                # Save incrementally after each case
                with open(args.output, "w") as f:
                    json.dump(all_cases, f, indent=2)

            except Exception as e:
                print(f"    [{case_id:3d}] ERROR: {e} — skipping")
                case_id -= 1  # don't advance ID on failure
                time.sleep(1)

            time.sleep(0.3)  # rate limiting

    print(f"\n{'='*60}")
    print(f"Generation complete: {generated} new cases generated")
    print(f"Total cases in benchmark: {len(all_cases)}")

    # Print per-category summary
    print(f"\nCategory breakdown:")
    for cat in CATEGORIES:
        n = sum(1 for c in all_cases if c["category_code"] == cat["code"])
        target = cat["count"]
        status = "✓" if n >= target else f"⚠ ({target - n} short)"
        print(f"  {cat['name']:25s}: {n:3d} / {target:3d} {status}")

    print(f"\nBenchmark saved to: {args.output}")


if __name__ == "__main__":
    main()
