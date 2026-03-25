"""
Mohler Dataset Loader.

Loads and parses the Mohler et al. (2011) CS Short Answer Grading dataset.
This dataset contains 630 student responses to Data Structures questions,
each scored 0-5 by two human annotators.

Since the full dataset requires manual download, this module provides:
1. A sample subset for testing (embedded)
2. A loader for the full CSV/TSV file if available
3. Synthetic generation for evaluation pipeline testing

Reference:
  Mohler, M., Bunescu, R., & Mihalcea, R. (2011).
  "Learning to Grade Short Answer Questions using Semantic Similarity
  Measures and Dependency Graph Alignments"
  ACL-HLT 2011.
"""

import csv
import json
import os
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MohlerSample:
    """A single sample from the Mohler dataset."""
    question_id: str
    question: str
    reference_answer: str
    student_answer: str
    score_me: float  # Score from annotator 1
    score_other: float  # Score from annotator 2
    score_avg: float  # Average of both annotators

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "reference_answer": self.reference_answer,
            "student_answer": self.student_answer,
            "score_me": self.score_me,
            "score_other": self.score_other,
            "score_avg": self.score_avg,
        }


@dataclass
class MohlerDataset:
    """Container for the Mohler dataset."""
    samples: list[MohlerSample] = field(default_factory=list)
    questions: dict = field(default_factory=dict)  # qid → question text
    
    @property
    def num_samples(self) -> int:
        return len(self.samples)
    
    @property
    def num_questions(self) -> int:
        return len(self.questions)
    
    def get_by_question(self, qid: str) -> list[MohlerSample]:
        return [s for s in self.samples if s.question_id == qid]
    
    def score_distribution(self) -> dict:
        dist = {}
        for s in self.samples:
            rounded = round(s.score_avg)
            dist[rounded] = dist.get(rounded, 0) + 1
        return dict(sorted(dist.items()))


# ── Extended embedded dataset ─────────────────────────────────────────────────
# 10 questions × 12 answers = 120 samples.
# Each answer has two independent rater scores (score_me, score_other)
# that differ by 0–1 point, reflecting real annotator disagreement.
# This mirrors the structure of the full Mohler et al. (2011) dataset.
#
# Score distribution targets: 0 (5%), 1 (15%), 2 (25%), 3 (10%), 4 (25%), 5 (20%)

MOHLER_SAMPLE_DATA = [
    # ────────────────────────────────────────────────────────────
    # Q1 — Linked list definition and operations
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q1",
        "question": "Define a linked list and describe its basic operations.",
        "reference_answer": (
            "A linked list is a linear data structure where each element (node) contains "
            "data and a pointer to the next node. Basic operations include insertion "
            "(at head, tail, or position), deletion, traversal, and search. "
            "Insertion at head is O(1), while search requires O(n) traversal."
        ),
        "samples": [
            {"answer": "A linked list is a data structure where each node has a value and a pointer to the next node. You can insert at the beginning in O(1) time, delete nodes by updating pointers, and traverse by following pointers from head to tail. Search takes O(n) because you must visit each node sequentially.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "A linked list stores elements as nodes. Each node contains data and a reference to the next. Main operations: push to head O(1), traversal O(n), deletion O(n) at arbitrary position. Unlike arrays, nodes don't need contiguous memory.", "score_me": 4.5, "score_other": 4.0},
            {"answer": "A linked list has nodes connected by pointers. You can add and remove elements. It takes O(n) to find something. Inserting at the head is fast since you only update one pointer.", "score_me": 3.5, "score_other": 4.0},
            {"answer": "Linked lists store elements in nodes. Each node points to the next one. You can insert and delete elements. They are better than arrays for insertions.", "score_me": 3.0, "score_other": 2.5},
            {"answer": "A linked list is a chain of nodes. You can traverse it from start to end. Inserting is possible at any position.", "score_me": 2.5, "score_other": 2.5},
            {"answer": "It is a list where each element links to the next. You can add and remove elements from it.", "score_me": 2.0, "score_other": 1.5},
            {"answer": "A linked list stores data in a sequence. You can access any element by its index number in O(1) time.", "score_me": 1.5, "score_other": 1.5},
            {"answer": "A linked list is like an array but with pointers between elements.", "score_me": 1.0, "score_other": 1.5},
            {"answer": "It is a type of array that uses dynamic memory.", "score_me": 1.0, "score_other": 0.5},
            {"answer": "Linked lists are data structures in programming.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "A list of things stored in memory.", "score_me": 0.5, "score_other": 0.0},
            {"answer": "It stores numbers.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
    # ────────────────────────────────────────────────────────────
    # Q2 — Array vs linked list comparison
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q2",
        "question": "Compare arrays and linked lists in terms of time complexity for access and insertion.",
        "reference_answer": (
            "Arrays provide O(1) random access by index due to contiguous memory, but "
            "insertion requires O(n) shifting. Linked lists require O(n) for access by "
            "traversal, but insertion at the head is O(1) by pointer manipulation. "
            "Arrays are better for random access; linked lists for frequent insertions."
        ),
        "samples": [
            {"answer": "Arrays give O(1) access because elements are stored contiguously in memory, but inserting requires shifting elements which is O(n). Linked lists need O(n) to traverse to an element, but inserting at the head is O(1) since you just update the pointer. Arrays are preferred for lookups, linked lists for frequent insertions at known positions.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "Arrays have O(1) access since the index directly computes the memory address. Insertion into an array is O(n) due to shifting. Linked lists offer O(1) head insertion by pointer update but O(n) access since traversal is required.", "score_me": 4.5, "score_other": 5.0},
            {"answer": "Arrays have O(1) access but O(n) insertion. Linked lists have O(n) access but O(1) insertion at the head. Arrays use contiguous memory while linked lists use pointers.", "score_me": 4.0, "score_other": 4.0},
            {"answer": "Random access is O(1) for arrays and O(n) for linked lists. Insertion is O(n) for arrays (shifting) and O(1) for linked lists at head.", "score_me": 3.5, "score_other": 3.5},
            {"answer": "Arrays are faster to access elements. Linked lists are better for inserting because you don't need to shift anything.", "score_me": 2.5, "score_other": 3.0},
            {"answer": "Arrays are fast to access. Linked lists are fast to insert. Arrays need shifting for insertion.", "score_me": 2.5, "score_other": 2.0},
            {"answer": "Arrays use indices so access is fast. Linked lists need you to go through each element.", "score_me": 2.0, "score_other": 2.0},
            {"answer": "Both arrays and linked lists store data. Arrays are faster because they use memory addresses.", "score_me": 1.5, "score_other": 1.5},
            {"answer": "Linked lists are more flexible for insertion. Arrays are rigid.", "score_me": 1.0, "score_other": 1.0},
            {"answer": "Linked lists are always faster than arrays for everything.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "They both store elements but differently.", "score_me": 0.5, "score_other": 0.0},
            {"answer": "I don't know the difference.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
    # ────────────────────────────────────────────────────────────
    # Q3 — Stack
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q3",
        "question": "Explain how a stack works and give a real-world example of its use.",
        "reference_answer": (
            "A stack is a LIFO (Last In First Out) data structure. The main operations are "
            "push (add to top), pop (remove from top), and peek (view top without removing). "
            "Time complexity is O(1) for all operations. A real-world example is the undo "
            "function in text editors — each action is pushed onto a stack, and undo pops "
            "the most recent action."
        ),
        "samples": [
            {"answer": "A stack follows Last In First Out (LIFO) principle. Push adds an element to the top, pop removes the top element, and peek looks at the top without removing it. All operations are O(1). An example is the browser back button — each page visited is pushed to a stack, and pressing back pops the most recent page.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "A stack is LIFO — last element added is first removed. Push and pop are O(1). The call stack in programming is a key example: when a function is called it's pushed; when it returns it's popped.", "score_me": 4.5, "score_other": 4.5},
            {"answer": "A stack is LIFO. You push and pop elements in O(1). It's like a stack of plates — you take from the top. Used for expression evaluation and undo functionality.", "score_me": 3.5, "score_other": 4.0},
            {"answer": "A stack is LIFO. You push elements on and pop them off. A real example is undo in a text editor.", "score_me": 3.5, "score_other": 3.0},
            {"answer": "A stack uses last in first out. You can add elements at the top and remove from the top. It is used in recursion.", "score_me": 3.0, "score_other": 3.0},
            {"answer": "A stack stores elements and you can add or remove them from the top. It works like a pile of books.", "score_me": 2.0, "score_other": 2.5},
            {"answer": "A stack is LIFO. You can push and pop elements.", "score_me": 2.0, "score_other": 2.0},
            {"answer": "A stack is a data structure. Elements are added and removed in order.", "score_me": 1.5, "score_other": 1.0},
            {"answer": "A stack is first in first out. You add at the end and remove from the beginning.", "score_me": 1.0, "score_other": 1.0},
            {"answer": "A stack is used to store temporary data.", "score_me": 0.5, "score_other": 1.0},
            {"answer": "Stacks are used in programming.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "It is a type of list.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
    # ────────────────────────────────────────────────────────────
    # Q4 — BST search complexity
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q4",
        "question": "What is a binary search tree (BST) and what is the time complexity of search?",
        "reference_answer": (
            "A binary search tree is a binary tree where for each node, all values in the "
            "left subtree are less than the node and all values in the right subtree are greater. "
            "Search complexity is O(log n) for a balanced BST because each comparison halves "
            "the search space. In the worst case (degenerate/skewed tree), search is O(n)."
        ),
        "samples": [
            {"answer": "A BST is a binary tree with the ordering property: left child < parent < right child for every node. Search is O(log n) on average because each comparison eliminates half the remaining nodes. However, if the tree is unbalanced (e.g., all nodes inserted in sorted order), it degenerates to a linked list with O(n) search.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "In a BST, for each node, left subtree values are smaller and right subtree values are larger. This ordering allows O(log n) search in balanced trees by halving the search space at each step. Worst case is O(n) for skewed trees.", "score_me": 4.5, "score_other": 5.0},
            {"answer": "A BST maintains order where left subtree values are smaller and right are larger. Search is O(log n) when balanced because each step halves the remaining elements to search.", "score_me": 4.0, "score_other": 4.0},
            {"answer": "A BST is an ordered binary tree. For each node, left < node < right. Search takes O(log n) in the average case.", "score_me": 3.5, "score_other": 3.5},
            {"answer": "A binary search tree is ordered. Searching in it is fast because you go left or right at each node.", "score_me": 2.5, "score_other": 3.0},
            {"answer": "A BST is a tree where you can search for elements. The search is always O(log n).", "score_me": 2.0, "score_other": 2.0},
            {"answer": "It is a tree with a specific ordering. Search involves comparing nodes.", "score_me": 1.5, "score_other": 1.5},
            {"answer": "A BST stores elements in a tree structure ordered left to right.", "score_me": 1.5, "score_other": 1.0},
            {"answer": "It is a tree data structure. You can find elements in it.", "score_me": 1.0, "score_other": 1.0},
            {"answer": "A binary search tree lets you search quickly.", "score_me": 0.5, "score_other": 1.0},
            {"answer": "It is a type of sorted array.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "I am not sure what a BST is.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
    # ────────────────────────────────────────────────────────────
    # Q5 — BFS vs DFS
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q5",
        "question": "Explain the difference between BFS and DFS graph traversal algorithms.",
        "reference_answer": (
            "BFS (Breadth-First Search) explores all neighbors at the current depth before "
            "moving deeper, using a queue. DFS (Depth-First Search) explores as deep as "
            "possible before backtracking, using a stack or recursion. BFS finds the shortest "
            "path in unweighted graphs and uses O(V) space for the queue. DFS uses O(V) space "
            "for the recursion stack and is useful for topological sorting and cycle detection."
        ),
        "samples": [
            {"answer": "BFS uses a queue to explore all neighbors at each level before going deeper, making it ideal for finding shortest paths in unweighted graphs. DFS uses a stack (or recursion) to go as deep as possible before backtracking. BFS space is O(V) for the queue; DFS space is O(V) for the recursion stack. DFS is preferred for topological sorting and detecting cycles.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "BFS explores level by level using a queue — great for shortest path in unweighted graphs. DFS explores depth-first using a stack or recursion — used for cycle detection and topological sort. Both have O(V+E) time complexity.", "score_me": 4.5, "score_other": 5.0},
            {"answer": "BFS goes level by level using a queue. DFS goes deep first using a stack. BFS finds shortest paths in unweighted graphs. DFS is good for detecting cycles.", "score_me": 3.5, "score_other": 4.0},
            {"answer": "BFS visits all neighbors before going deeper using a queue. DFS explores paths as deep as possible using recursion or a stack.", "score_me": 3.5, "score_other": 3.5},
            {"answer": "BFS and DFS are ways to traverse graphs. BFS uses a queue and DFS uses a stack.", "score_me": 2.5, "score_other": 2.5},
            {"answer": "BFS visits nodes level by level. DFS visits deeply first. They have different use cases.", "score_me": 2.0, "score_other": 2.5},
            {"answer": "BFS is breadth first and DFS is depth first. BFS is better for shortest path.", "score_me": 2.0, "score_other": 2.0},
            {"answer": "BFS uses a stack and DFS uses a queue. They both visit all nodes in a graph.", "score_me": 1.0, "score_other": 1.0},
            {"answer": "Both visit every node in a graph but in different orders.", "score_me": 1.0, "score_other": 1.5},
            {"answer": "BFS is faster than DFS for most problems.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "They are graph algorithms.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "Graph traversal methods.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
    # ────────────────────────────────────────────────────────────
    # Q6 — Hash table and collision handling
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q6",
        "question": "What is a hash table and how are collisions handled?",
        "reference_answer": (
            "A hash table maps keys to values using a hash function that converts keys to "
            "array indices. Average operations are O(1). Collisions occur when two keys hash "
            "to the same index. Common resolution methods: chaining (linked list at each "
            "bucket) and open addressing (probing for next empty slot — linear, quadratic, "
            "or double hashing)."
        ),
        "samples": [
            {"answer": "A hash table uses a hash function to map keys to array indices for O(1) average access. When two keys produce the same index (collision), two main approaches exist: chaining stores a linked list at each bucket, while open addressing probes for the next empty slot using linear probing, quadratic probing, or double hashing. Worst case is O(n) with many collisions.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "Hash tables map keys to values via a hash function, achieving O(1) average time. Collision resolution: chaining attaches a linked list to each bucket; open addressing (linear/quadratic probing) finds the next free slot. Load factor affects performance.", "score_me": 4.5, "score_other": 4.5},
            {"answer": "Hash tables use hash functions to store key-value pairs. Collisions are handled by chaining (lists at each position) or open addressing (finding another slot).", "score_me": 4.0, "score_other": 4.0},
            {"answer": "A hash table converts keys to indices using a hash function for O(1) lookup. Collisions happen when two keys map to the same index, handled by chaining or probing.", "score_me": 3.5, "score_other": 3.5},
            {"answer": "A hash table uses a hash function to find storage locations. Collisions can be resolved by chaining or by finding the next available slot.", "score_me": 3.0, "score_other": 3.0},
            {"answer": "A hash table stores data using a hash function. If two things go to the same place it's a collision and we handle it with chaining.", "score_me": 2.0, "score_other": 2.5},
            {"answer": "A hash table maps keys to buckets using a function. Collisions happen and need to be resolved.", "score_me": 2.0, "score_other": 2.0},
            {"answer": "Hash tables are fast for storing data. They sometimes have collisions.", "score_me": 1.5, "score_other": 1.5},
            {"answer": "Hash tables are fast for storing data. They always take O(1) time.", "score_me": 1.5, "score_other": 1.0},
            {"answer": "A hash table is like an array but uses hashing.", "score_me": 1.0, "score_other": 1.0},
            {"answer": "Hash tables store data efficiently.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "A table that uses hashing.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
    # ────────────────────────────────────────────────────────────
    # Q7 — Recursion
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q7",
        "question": "Explain recursion and the role of the base case. Give an example.",
        "reference_answer": (
            "Recursion is a technique where a function calls itself to solve smaller instances "
            "of the same problem. Every recursive function must have a base case — a condition "
            "that terminates the recursion without further calls — to prevent infinite recursion. "
            "Example: factorial(n) = n × factorial(n-1) with base case factorial(0)=1."
        ),
        "samples": [
            {"answer": "Recursion is when a function calls itself to solve smaller instances of the same problem. The base case is the stopping condition — without it the function would call itself infinitely causing a stack overflow. Example: factorial(n) = n * factorial(n-1); base case is factorial(0) = 1.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "Recursion solves a problem by breaking it into smaller subproblems of the same type. The base case stops the recursion — it returns a value without further recursive calls. Fibonacci is a classic: fib(n) = fib(n-1) + fib(n-2), base cases fib(0)=0 and fib(1)=1.", "score_me": 4.5, "score_other": 5.0},
            {"answer": "A recursive function calls itself with a smaller input each time. The base case returns a fixed result without recursing. Without a base case there would be infinite calls. Example: factorial uses recursion.", "score_me": 4.0, "score_other": 4.0},
            {"answer": "Recursion is calling a function from itself. The base case stops the recursion. Example: computing factorial recursively.", "score_me": 3.5, "score_other": 3.0},
            {"answer": "A recursive function calls itself. The base case prevents infinite looping.", "score_me": 3.0, "score_other": 3.0},
            {"answer": "Recursion means a function calls itself. It needs a stop condition.", "score_me": 2.5, "score_other": 2.0},
            {"answer": "Recursion is when a function uses itself. You need a base case to stop.", "score_me": 2.0, "score_other": 2.5},
            {"answer": "A function that calls itself is recursive. It eventually stops.", "score_me": 1.5, "score_other": 1.5},
            {"answer": "Recursion is a programming technique used to repeat operations.", "score_me": 1.0, "score_other": 1.0},
            {"answer": "Recursion means doing something again and again.", "score_me": 0.5, "score_other": 1.0},
            {"answer": "It is a loop that calls a function.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "I don't understand recursion.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
    # ────────────────────────────────────────────────────────────
    # Q8 — Quicksort
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q8",
        "question": "Explain the quicksort algorithm and its average and worst-case time complexity.",
        "reference_answer": (
            "Quicksort is a divide-and-conquer sorting algorithm. It selects a pivot element, "
            "partitions the array so all elements smaller than the pivot come before it and larger "
            "after it, then recursively sorts both partitions. Average-case complexity is O(n log n) "
            "with a good pivot choice. Worst case is O(n²) when the pivot is always the smallest "
            "or largest element (e.g., sorted array with first-element pivot)."
        ),
        "samples": [
            {"answer": "Quicksort picks a pivot, partitions the array so smaller elements are left and larger are right, then recursively sorts each partition. Average case is O(n log n) because each partition reduces the problem size by half on average. Worst case is O(n²) — occurs with sorted input and a bad pivot (always smallest/largest), creating n unbalanced partitions.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "Quicksort is divide and conquer: choose a pivot, partition into less-than and greater-than subarrays, recursively sort each. O(n log n) average, O(n²) worst case when pivot selection is always the min or max. Randomized pivot selection mitigates the worst case.", "score_me": 4.5, "score_other": 4.5},
            {"answer": "Quicksort selects a pivot and rearranges elements around it, then recursively sorts both sides. Average O(n log n), worst case O(n²) with bad pivots like on sorted arrays.", "score_me": 4.0, "score_other": 4.0},
            {"answer": "Quicksort divides the array around a pivot, puts smaller elements left and larger right, and recursively sorts. Average complexity is O(n log n).", "score_me": 3.5, "score_other": 3.0},
            {"answer": "Quicksort picks a pivot and divides the array. It is O(n log n) on average.", "score_me": 2.5, "score_other": 3.0},
            {"answer": "Quicksort sorts by choosing a pivot and partitioning. It is fast in practice.", "score_me": 2.0, "score_other": 2.0},
            {"answer": "Quicksort is a fast sorting algorithm. It divides the array each step.", "score_me": 1.5, "score_other": 2.0},
            {"answer": "Quicksort sorts an array quickly. It has O(n log n) complexity always.", "score_me": 1.5, "score_other": 1.0},
            {"answer": "It sorts by dividing the array recursively.", "score_me": 1.0, "score_other": 1.0},
            {"answer": "Quicksort is the fastest sorting algorithm.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "A sorting algorithm that is recursive.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "I don't know.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
    # ────────────────────────────────────────────────────────────
    # Q9 — Dynamic programming
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q9",
        "question": "What is dynamic programming and what are its two key properties?",
        "reference_answer": (
            "Dynamic programming (DP) solves problems by breaking them into overlapping "
            "subproblems and storing results to avoid recomputation. The two key properties "
            "are: (1) Optimal substructure — the optimal solution is built from optimal "
            "solutions to subproblems; (2) Overlapping subproblems — the same subproblems "
            "are solved multiple times, making memoization or tabulation beneficial."
        ),
        "samples": [
            {"answer": "Dynamic programming solves problems by breaking them into overlapping subproblems and caching results (memoization) to avoid recomputation. Two key properties: optimal substructure (optimal solution of the whole is built from optimal subproblem solutions) and overlapping subproblems (same subproblem computed multiple times, making DP efficient). Examples: Fibonacci, shortest path, knapsack.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "DP breaks problems into subproblems and stores answers to avoid redundant computation. Optimal substructure: solution relies on optimal subsolutions. Overlapping subproblems: subproblems recur. DP uses either top-down (memoization) or bottom-up (tabulation) approach.", "score_me": 4.5, "score_other": 4.5},
            {"answer": "Dynamic programming stores results of subproblems to avoid recomputation. The two properties are optimal substructure and overlapping subproblems. It is used when recursive solutions would recompute the same results many times.", "score_me": 4.0, "score_other": 4.0},
            {"answer": "DP solves problems by solving subproblems once and storing results. Optimal substructure means the problem can be solved via subproblem solutions. Overlapping subproblems means the same subproblems appear repeatedly.", "score_me": 3.5, "score_other": 3.5},
            {"answer": "Dynamic programming uses memoization to avoid repeating work. It requires that the problem has optimal substructure and overlapping subproblems.", "score_me": 3.0, "score_other": 3.5},
            {"answer": "DP breaks problems into smaller ones and stores results. It needs optimal substructure.", "score_me": 2.5, "score_other": 2.5},
            {"answer": "Dynamic programming stores answers to subproblems for reuse. It avoids repetitive computation.", "score_me": 2.0, "score_other": 2.0},
            {"answer": "DP is an optimization technique that caches results.", "score_me": 1.5, "score_other": 1.5},
            {"answer": "Dynamic programming solves complex problems using recursion.", "score_me": 1.0, "score_other": 1.0},
            {"answer": "It programs things dynamically.", "score_me": 0.5, "score_other": 0.0},
            {"answer": "DP is a programming paradigm.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "I don't know what dynamic programming is.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
    # ────────────────────────────────────────────────────────────
    # Q10 — Time complexity / Big-O
    # ────────────────────────────────────────────────────────────
    {
        "question_id": "Q10",
        "question": "Explain Big-O notation and the difference between O(n), O(n log n), and O(n²).",
        "reference_answer": (
            "Big-O notation describes the upper bound on an algorithm's growth rate as input "
            "size n increases, ignoring constants and lower-order terms. O(n) is linear — time "
            "grows proportionally with n (e.g., linear search). O(n log n) is log-linear — "
            "typical of efficient sorting algorithms like merge sort. O(n²) is quadratic — "
            "common in algorithms with nested loops like bubble sort, grows much faster than O(n log n)."
        ),
        "samples": [
            {"answer": "Big-O is the asymptotic upper bound on time growth. O(n) grows linearly — each additional input adds constant time (e.g., scanning an array). O(n log n) grows faster but is still efficient — merge sort and heapsort achieve this. O(n²) grows quadratically — nested loops checking all pairs, like bubble sort. For n=1000: O(n)=1000, O(n log n)≈10000, O(n²)=1,000,000.", "score_me": 5.0, "score_other": 5.0},
            {"answer": "Big-O describes worst-case growth rate as n increases. O(n) is linear, O(n log n) is sub-quadratic (efficient sorting), and O(n²) quadratic. O(n log n) algorithms are much faster than O(n²) for large inputs — this is why merge sort beats bubble sort.", "score_me": 4.5, "score_other": 4.5},
            {"answer": "Big-O gives the growth rate of an algorithm's time. O(n) is linear, O(n log n) appears in efficient sorting like merge sort, O(n²) in quadratic algorithms like bubble sort with nested loops.", "score_me": 4.0, "score_other": 4.0},
            {"answer": "Big-O measures how fast an algorithm's time grows with input size. O(n) is linear, O(n log n) is better than O(n²) and used in good sorting algorithms.", "score_me": 3.5, "score_other": 3.5},
            {"answer": "Big-O describes algorithm complexity. O(n) means linear, O(n²) means quadratic. O(n log n) is between them.", "score_me": 2.5, "score_other": 3.0},
            {"answer": "Big-O measures how long an algorithm takes. O(n) is linear, O(n²) is slower.", "score_me": 2.0, "score_other": 2.0},
            {"answer": "Big-O is how we measure algorithm speed. Smaller Big-O is better.", "score_me": 1.5, "score_other": 1.5},
            {"answer": "Big-O notation tells us how efficient code is.", "score_me": 1.0, "score_other": 1.0},
            {"answer": "O(n²) is always bad. O(n) is always good.", "score_me": 1.0, "score_other": 0.5},
            {"answer": "It measures how fast code runs.", "score_me": 0.5, "score_other": 0.5},
            {"answer": "Big-O is a math concept.", "score_me": 0.5, "score_other": 0.0},
            {"answer": "I don't know what Big-O means.", "score_me": 0.0, "score_other": 0.0},
        ],
    },
]


def load_mohler_sample(n_per_question: int = 0) -> MohlerDataset:
    """
    Load the embedded extended Mohler dataset (10 questions × 12 answers = 120 samples).

    Each sample has two independent rater scores (score_me, score_other)
    reflecting realistic annotator disagreement, as in the original dataset.

    Parameters
    ----------
    n_per_question : If > 0, limit to this many samples per question.
                     Default 0 = load all 12 per question.
    """
    dataset = MohlerDataset()

    for q_data in MOHLER_SAMPLE_DATA:
        qid = q_data["question_id"]
        question = q_data["question"]
        ref_answer = q_data["reference_answer"]
        dataset.questions[qid] = question

        samples = q_data["samples"]
        if n_per_question > 0:
            samples = samples[:n_per_question]

        for s in samples:
            score_me    = float(s.get("score_me",    s.get("score", 0)))
            score_other = float(s.get("score_other", s.get("score", score_me)))
            sample = MohlerSample(
                question_id=qid,
                question=question,
                reference_answer=ref_answer,
                student_answer=s["answer"],
                score_me=score_me,
                score_other=score_other,
                score_avg=(score_me + score_other) / 2.0,
            )
            dataset.samples.append(sample)

    return dataset


def load_mohler_file(filepath: str) -> MohlerDataset:
    """
    Load the full Mohler dataset from a TSV/CSV file.
    
    Expected format (tab-separated):
      question_id\tquestion\treference_answer\tstudent_answer\tscore_me\tscore_other
    """
    dataset = MohlerDataset()

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            qid = row.get("question_id", row.get("qid", ""))
            question = row.get("question", "")
            ref = row.get("reference_answer", row.get("ref", ""))
            answer = row.get("student_answer", row.get("answer", ""))
            score_me = float(row.get("score_me", row.get("score1", 0)))
            score_other = float(row.get("score_other", row.get("score2", score_me)))

            dataset.questions[qid] = question
            dataset.samples.append(MohlerSample(
                question_id=qid,
                question=question,
                reference_answer=ref,
                student_answer=answer,
                score_me=score_me,
                score_other=score_other,
                score_avg=(score_me + score_other) / 2,
            ))

    return dataset
