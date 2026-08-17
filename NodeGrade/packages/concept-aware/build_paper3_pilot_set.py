#!/usr/bin/env python3
"""
build_paper3_pilot_set.py — constructs the Paper 3 (long-answer) pilot
test set with FULLY DISCLOSED provenance.

Every answer below is author-written (by the researcher running this
project), NOT collected from real students, NOT LLM-generated. Each is
tagged with an author-intended quality tier and target score BEFORE
running the pipeline.

Per external GPT review (docs/PAPER3_LONGANSWER_REVIEW_REQUEST.md), this
is framed as HYPOTHESIS-DRIVEN STRESS TESTING of a predicted failure mode
(the design doc's own §2.5 "misconception locality" concern), not a
representative evaluation — and as DEVELOPER-AUTHORED FUNCTIONAL
VALIDATION, since the same person designed the pipeline, wrote these
answers, and assigned the target scores. It does not claim inter-rater
reliability, real-student sampling, statistical power, or an estimate of
real-world grading performance, and should never be cited as such.

This directly replaces the retracted lag_benchmark.json (see
REPRODUCIBILITY.md, "CRITICAL: the LAG evaluation is retracted"): every
topic here is checked against data/ds_knowledge_graph.json to confirm KG
coverage before inclusion (unlike the retracted set, where 3/5 topics had
zero matching concepts).
"""
import json
from pathlib import Path

BASE = Path(__file__).parent

PILOT_SET = [
    {
        "id": "recursion_excellent",
        "topic": "recursion",
        "question": "Explain how recursion works and discuss what is required for a recursive function to terminate correctly. Illustrate with an example.",
        "student_answer": (
            "Recursion is a technique where a function solves a problem by calling itself on a smaller "
            "version of the same problem, until the problem becomes trivial enough to solve directly. "
            "Every correct recursive function needs two things: a base case, which is the trivial "
            "condition that stops further recursive calls, and a recursive case, which breaks the "
            "problem down and calls the function again on a smaller input.\n\n"
            "A classic example is computing the factorial of a number. factorial(n) is defined as "
            "n * factorial(n-1) for n > 1, with the base case factorial(1) = 1. Each call reduces n by "
            "one, so the sequence of calls moves steadily toward the base case rather than looping "
            "forever. If the base case were missing or unreachable, the function would keep calling "
            "itself indefinitely, and each call would push a new stack frame onto the call stack until "
            "the program runs out of stack space and crashes with a stack overflow.\n\n"
            "It's worth noting that recursion and iteration are equivalent in terms of what they can "
            "compute, but they trade off differently: recursion often produces more readable code for "
            "problems with a naturally recursive structure, like tree traversal, but it costs more "
            "memory because of all the stack frames that accumulate while calls are pending. Tail "
            "recursion, where the recursive call is the very last operation performed, can sometimes be "
            "optimized by a compiler into an iterative loop to avoid this overhead, though this isn't "
            "guaranteed in every language."
        ),
        "author_intended_tier": "excellent",
        "author_intended_score_0to5": 4.75,
        "designed_misconception": None,
        "notes": "Comprehensive, correct, discusses base case, stack overflow, and recursion-vs-iteration tradeoff unprompted.",
    },
    {
        "id": "queue_good_shallow_depth",
        "topic": "queue",
        "question": "What is a queue and how does it order operations? Describe its main operations.",
        "student_answer": (
            "A queue is a linear data structure that follows First In First Out order, meaning FIFO. "
            "The first element added to the queue is the first one to be removed.\n\n"
            "The two main operations are enqueue, which adds an element to the back of the queue, and "
            "dequeue, which removes the element from the front of the queue. Both of these operations "
            "run in constant time, O(1), if the queue is implemented properly, for example using a "
            "linked list or a circular array.\n\n"
            "Queues are used in situations where things need to be processed in the order they arrive, "
            "such as a print queue or task scheduling in an operating system."
        ),
        "author_intended_tier": "good_but_shallow",
        "author_intended_score_0to5": 3.25,
        "designed_misconception": None,
        "notes": "Correct throughout, but stays mostly at definition/recall level; doesn't explain *why* FIFO order matters or connect to any deeper mechanism.",
    },
    {
        "id": "linked_list_surface_level",
        "topic": "linked_list",
        "question": "What is a linked list and how is it different from an array?",
        "student_answer": (
            "A linked list is a data structure made of nodes. Each node has a value and a pointer to "
            "the next node. It is different from an array because an array stores things next to each "
            "other in memory but a linked list does not.\n\n"
            "Linked lists are good when you need to insert or delete things a lot. Arrays are good when "
            "you need to access things quickly by index."
        ),
        "author_intended_tier": "shallow",
        "author_intended_score_0to5": 2.0,
        "designed_misconception": None,
        "notes": "Facts stated are correct but extremely thin — no explanation of *why* insertion is fast for linked lists or *why* array access is fast; no complexity discussion.",
    },
    {
        "id": "bst_tree_conflation",
        "topic": "binary_search_tree",
        "question": "What is a binary tree, and what additional property makes a binary tree a binary search tree?",
        "student_answer": (
            "A binary tree is a tree data structure where every node has at most two children, usually "
            "called the left child and the right child. Binary trees are used to represent hierarchical "
            "data efficiently, and many algorithms rely on their recursive structure — you can process "
            "the left subtree, process the right subtree, and combine the results.\n\n"
            "Because every binary tree already organizes data into a left side and a right side at "
            "every node, this ordering means that the left subtree always contains smaller values and "
            "the right subtree always contains larger values, which is what makes searching fast. This "
            "is why we can do binary search on any binary tree in O(log n) time in the average case, "
            "the same way we can do binary search on a sorted array.\n\n"
            "Common operations on binary trees include insertion, deletion, and traversal (in-order, "
            "pre-order, post-order). In-order traversal is especially useful because it visits nodes in "
            "ascending sorted order, which is a direct consequence of how binary trees are structured."
        ),
        "author_intended_tier": "flawed_by_critical_misconception",
        "author_intended_score_0to5": 2.25,
        "designed_misconception": "DS-TREE-01: assumes all binary trees are binary search trees (claims the left/right ordering property holds for every binary tree, not just BSTs)",
        "notes": "Fluent, well-organized, uses correct vocabulary (in-order traversal, O(log n)) — but the core claim is backwards: general binary trees have no ordering guarantee at all.",
    },
    {
        "id": "hash_table_complexity_misconception",
        "topic": "hash_table",
        "question": "Explain how a hash table works and discuss the time complexity of its main operations.",
        "student_answer": (
            "A hash table stores key-value pairs by using a hash function to convert a key into an "
            "index into an underlying array. When you want to insert, look up, or delete a value, the "
            "hash function computes the index directly, so the operation jumps straight to the right "
            "bucket instead of searching through the data.\n\n"
            "Because the hash function computes the index directly rather than searching, hash table "
            "operations — insertion, lookup, and deletion — are always O(1), regardless of how many "
            "elements are stored. This is what makes hash tables so much faster than data structures "
            "like linked lists or binary search trees for lookups, since those require traversing "
            "multiple nodes.\n\n"
            "One thing to be careful about is collisions, which happen when two different keys hash to "
            "the same index. Common ways to handle this are chaining, where each bucket holds a list of "
            "entries, and open addressing, where the table probes for the next free slot. A good hash "
            "function spreads keys evenly across the table to minimize how often collisions occur."
        ),
        "author_intended_tier": "flawed_by_moderate_misconception",
        "author_intended_score_0to5": 3.25,
        "designed_misconception": "DS-HASH-01: claims hash table operations are always O(1), ignoring worst-case O(n) with many collisions",
        "notes": "Otherwise strong (correctly explains collisions, chaining, open addressing) — the O(1)-always claim directly contradicts the collision discussion two paragraphs later, which the answer doesn't notice.",
    },
    {
        "id": "sorting_quicksort_mergesort_misconception",
        "topic": "sorting",
        "question": "Compare quicksort and merge sort in terms of how they work and their performance characteristics.",
        "student_answer": (
            "Both quicksort and merge sort are divide-and-conquer sorting algorithms, meaning they break "
            "the array into smaller pieces, sort the pieces, and then combine the results.\n\n"
            "Merge sort splits the array exactly in half at every step, recursively sorts each half, and "
            "then merges the two sorted halves back together in linear time. This gives merge sort a "
            "guaranteed O(n log n) running time no matter what the input looks like, but it needs extra "
            "memory for the merge step since it isn't done in place.\n\n"
            "Quicksort instead picks a pivot element, partitions the array so that smaller elements go "
            "before the pivot and larger elements go after, and then recursively sorts each partition. "
            "Because quicksort avoids the overhead of allocating extra arrays for merging and often has "
            "better cache performance, quicksort is always faster than merge sort in practice, which is "
            "why most standard library sort functions use quicksort as their default algorithm.\n\n"
            "The main tradeoff is memory: merge sort uses O(n) extra space while quicksort can sort "
            "in place using only O(log n) extra space for the recursion stack."
        ),
        "author_intended_tier": "flawed_by_moderate_misconception",
        "author_intended_score_0to5": 3.0,
        "designed_misconception": "DS-SORT-01: claims quicksort is always faster than merge sort, ignoring quicksort's O(n^2) worst case",
        "notes": "Otherwise accurate and well-structured (correct partition description, correct space tradeoff) — the 'always faster' claim is the flaw; worst-case behavior is never mentioned.",
    },
    {
        "id": "stack_queue_conflation_longform",
        "topic": "stack",
        "question": "Compare how a stack and a queue order their elements, and give an example of when you would use each.",
        "student_answer": (
            "Stacks and queues are both linear data structures that store a collection of elements, but "
            "they differ in the order elements are removed.\n\n"
            "A queue removes elements in the order they were added — the first element enqueued is the "
            "first one dequeued, which is called FIFO, First In First Out. A real-world analogy is a "
            "line of people waiting at a store: whoever got in line first gets served first.\n\n"
            "A stack works the same way, using FIFO ordering as well: the first element pushed onto the "
            "stack is the first one popped off. A good analogy is a stack of plates in a cafeteria — "
            "the plate that was placed on the stack first is the one a customer would take first, since "
            "it's been sitting there the longest and everyone takes from the bottom of the pile over "
            "time.\n\n"
            "Stacks are commonly used for function call management, where each function call pushes a "
            "new stack frame, and undo functionality in text editors, where each action is pushed and "
            "undoing pops the most recent one off. Queues are used for task scheduling and breadth-first "
            "search, where nodes need to be processed in the order they were discovered."
        ),
        "author_intended_tier": "flawed_by_critical_misconception_despite_fluency",
        "author_intended_score_0to5": 1.25,
        "designed_misconception": "DS-STACK-01: explicitly states stacks use FIFO order (should be LIFO) and invents an incorrect 'plates from the bottom' analogy to justify it",
        "notes": "The longer-form version of the same conflation tested in the short-answer demo — this time embedded in an otherwise fluent, well-organized four-paragraph essay with correct use-case examples for stacks (call stack, undo) that would normally signal understanding.",
    },
    {
        "id": "dynamic_array_excellent",
        "topic": "array",
        "question": "Explain how a dynamic array (like a Python list or Java ArrayList) achieves resizable storage, and discuss the time complexity of appending an element.",
        "student_answer": (
            "A dynamic array is built on top of a regular fixed-size array, but it manages resizing "
            "automatically so it appears to grow as needed. Internally, it keeps track of both the "
            "number of elements currently stored (the length) and the size of the underlying allocated "
            "array (the capacity), which is usually larger than the length to leave room to grow.\n\n"
            "When you append an element and there is spare capacity, the operation is simple: the new "
            "element is written to the next free slot and the length is incremented, which takes O(1) "
            "time. The interesting case is when the array is full. At that point, the dynamic array "
            "allocates a new, larger underlying array — typically double the current capacity — copies "
            "every existing element over, and then appends the new element. That single resize operation "
            "takes O(n) time because of the copy.\n\n"
            "Even though a single append can occasionally cost O(n), the amortized time complexity of "
            "append across a sequence of n appends is still O(1). This is because doubling the capacity "
            "means resizes become exponentially rarer as the array grows: resizes happen at sizes 1, 2, "
            "4, 8, 16, and so on, so the total cost of all the copying across n appends is bounded by "
            "roughly 2n, which averages out to O(1) per append even though individual operations vary.\n\n"
            "This is different from a plain fixed-size array, which cannot grow at all once allocated, "
            "and different from a linked list, which has O(1) worst-case insertion at the head but no "
            "O(1) random access by index."
        ),
        "author_intended_tier": "excellent",
        "author_intended_score_0to5": 4.75,
        "designed_misconception": None,
        "notes": "Correctly explains amortized analysis (the hardest concept here), contrasts with both array and linked list unprompted, uses correct terminology throughout.",
    },
]


def main() -> int:
    kg = json.loads((BASE / "data" / "ds_knowledge_graph.json").read_text())
    kg_ids = {c["id"] for c in kg["concepts"]}

    for item in PILOT_SET:
        item["word_count"] = len(item["student_answer"].split())
        # Sanity-check: topic must have at least one matching KG concept id
        # (directly, or as a substring match) — this is the check that the
        # retracted lag_benchmark.json's 3/5 topics would have failed.
        topic_tokens = item["topic"].split("_")
        match = any(
            all(tok in cid for tok in topic_tokens) or item["topic"] == cid
            for cid in kg_ids
        )
        item["kg_topic_coverage_verified"] = match
        if not match:
            raise SystemExit(f"REFUSING to include '{item['id']}': topic '{item['topic']}' has no KG match")

    out = {
        "meta": {
            "name": "Paper 3 pilot long-answer set",
            "provenance": "Author-written (this project), NOT real students, NOT LLM-generated. "
                           "Author-intended tier/score assigned before running the pipeline. "
                           "Same person designed the pipeline, wrote these answers, and set the "
                           "targets — read as developer-authored functional validation, not an "
                           "estimate of real-world grading performance.",
            "purpose": "Hypothesis-driven stress test of a predicted failure mode (design doc "
                       "Section 2.5, 'misconception locality'), NOT a representative evaluation "
                       "and NOT a psychometric validation study. No claim of inter-rater "
                       "reliability, statistical power, or generalization beyond this set. "
                       "Per external GPT review, docs/PAPER3_LONGANSWER_REVIEW_REQUEST.md.",
            "replaces": "data/lag_benchmark.json (retracted — see REPRODUCIBILITY.md)",
            "n_samples": len(PILOT_SET),
            "topics": sorted({x["topic"] for x in PILOT_SET}),
            "kg_source": "data/ds_knowledge_graph.json (101 concepts)",
        },
        "samples": PILOT_SET,
    }

    out_path = BASE / "data" / "paper3_longanswer" / "pilot_set_v1.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {out_path} — {len(PILOT_SET)} samples, all KG-coverage verified")
    for item in PILOT_SET:
        print(f"  {item['id']:40s} {item['word_count']:4d}w  target={item['author_intended_score_0to5']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
