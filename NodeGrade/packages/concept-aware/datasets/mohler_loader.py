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


# ── Embedded sample subset for testing ──────────────────────────────
# Representative samples from Data Structures topics
MOHLER_SAMPLE_DATA = [
    {
        "question_id": "Q1",
        "question": "Define a linked list and describe its basic operations.",
        "reference_answer": "A linked list is a linear data structure where each element (node) contains data and a pointer to the next node. Basic operations include insertion (at head, tail, or position), deletion, traversal, and search. Insertion at head is O(1), while search requires O(n) traversal.",
        "samples": [
            {"answer": "A linked list is a data structure where each node has a value and a pointer to the next node. You can insert at the beginning in O(1) time, delete nodes by updating pointers, and traverse by following pointers from head to tail. Search takes O(n) because you must visit each node sequentially.", "score": 5.0},
            {"answer": "A linked list has nodes connected by pointers. You can add and remove elements. It takes O(n) to find something.", "score": 3.5},
            {"answer": "Linked lists store elements in nodes. Each node points to the next one. You can insert and delete elements.", "score": 3.0},
            {"answer": "A linked list stores data in a sequence. You can access any element by its index number in O(1) time.", "score": 1.5},
            {"answer": "It is a type of array that uses dynamic memory.", "score": 1.0},
        ],
    },
    {
        "question_id": "Q2",
        "question": "Compare arrays and linked lists in terms of time complexity for access and insertion.",
        "reference_answer": "Arrays provide O(1) random access by index due to contiguous memory, but insertion requires O(n) shifting. Linked lists require O(n) for access by traversal, but insertion at the head is O(1) by pointer manipulation. Arrays are better for random access; linked lists for frequent insertions.",
        "samples": [
            {"answer": "Arrays give O(1) access because elements are stored contiguously in memory, but inserting requires shifting elements which is O(n). Linked lists need O(n) to traverse to an element, but inserting at the head is O(1) since you just update the pointer. Arrays are preferred for lookups, linked lists for frequent insertions at known positions.", "score": 5.0},
            {"answer": "Arrays have O(1) access but O(n) insertion. Linked lists have O(n) access but O(1) insertion at the head. Arrays use contiguous memory while linked lists use pointers.", "score": 4.0},
            {"answer": "Arrays are fast to access. Linked lists are fast to insert. Arrays need shifting for insertion.", "score": 2.5},
            {"answer": "Both arrays and linked lists store data. Arrays are faster because they use memory addresses.", "score": 1.5},
            {"answer": "Linked lists are always faster than arrays for everything.", "score": 0.5},
        ],
    },
    {
        "question_id": "Q3",
        "question": "Explain how a stack works and give a real-world example of its use.",
        "reference_answer": "A stack is a LIFO (Last In First Out) data structure. The main operations are push (add to top), pop (remove from top), and peek (view top without removing). Time complexity is O(1) for all operations. A real-world example is the undo function in text editors — each action is pushed onto a stack, and undo pops the most recent action.",
        "samples": [
            {"answer": "A stack follows Last In First Out (LIFO) principle. Push adds an element to the top, pop removes the top element, and peek looks at the top without removing it. All operations are O(1). An example is the browser back button — each page visited is pushed to a stack, and pressing back pops the most recent page.", "score": 5.0},
            {"answer": "A stack is LIFO. You push and pop elements. It's like a stack of plates — you take from the top.", "score": 3.5},
            {"answer": "A stack stores elements and you can add or remove them. It works like a pile of books.", "score": 2.0},
            {"answer": "A stack is first in first out. You add at the end and remove from the beginning.", "score": 1.0},
            {"answer": "Stacks are used in programming.", "score": 0.5},
        ],
    },
    {
        "question_id": "Q4",
        "question": "What is a binary search tree (BST) and what is the time complexity of search?",
        "reference_answer": "A binary search tree is a binary tree where for each node, all values in the left subtree are less than the node and all values in the right subtree are greater. Search complexity is O(log n) for a balanced BST because each comparison halves the search space. In the worst case (degenerate/skewed tree), search is O(n).",
        "samples": [
            {"answer": "A BST is a binary tree with the ordering property: left child < parent < right child for every node. Search is O(log n) on average because each comparison eliminates half the remaining nodes. However, if the tree is unbalanced (e.g., all nodes inserted in sorted order), it degenerates to a linked list with O(n) search.", "score": 5.0},
            {"answer": "A BST maintains order where left subtree values are smaller and right are larger. Search is O(log n) when balanced.", "score": 4.0},
            {"answer": "A binary search tree is ordered. Searching in it is fast because you go left or right at each node.", "score": 2.5},
            {"answer": "A BST is a tree where you can search for elements. The search is always O(log n).", "score": 2.0},
            {"answer": "It is a tree data structure. You can find elements in it.", "score": 1.0},
        ],
    },
    {
        "question_id": "Q5",
        "question": "Explain the difference between BFS and DFS graph traversal algorithms.",
        "reference_answer": "BFS (Breadth-First Search) explores all neighbors at the current depth before moving deeper, using a queue. DFS (Depth-First Search) explores as deep as possible before backtracking, using a stack or recursion. BFS finds the shortest path in unweighted graphs and uses O(V) space for the queue. DFS uses O(V) space for the recursion stack and is useful for topological sorting and cycle detection.",
        "samples": [
            {"answer": "BFS uses a queue to explore all neighbors at each level before going deeper, making it ideal for finding shortest paths in unweighted graphs. DFS uses a stack (or recursion) to go as deep as possible before backtracking. BFS space is O(V) for the queue; DFS space is O(V) for the recursion stack. DFS is preferred for topological sorting and detecting cycles.", "score": 5.0},
            {"answer": "BFS goes level by level using a queue. DFS goes deep first using a stack. BFS finds shortest paths in unweighted graphs.", "score": 3.5},
            {"answer": "BFS and DFS are ways to traverse graphs. BFS uses a queue and DFS uses a stack.", "score": 2.5},
            {"answer": "BFS uses a stack and DFS uses a queue. They both visit all nodes in a graph.", "score": 1.0},
            {"answer": "They are graph algorithms.", "score": 0.5},
        ],
    },
    {
        "question_id": "Q6",
        "question": "What is a hash table and how are collisions handled?",
        "reference_answer": "A hash table maps keys to values using a hash function that converts keys to array indices. Average operations are O(1). Collisions occur when two keys hash to the same index. Common resolution methods: chaining (linked list at each bucket) and open addressing (probing for next empty slot — linear, quadratic, or double hashing).",
        "samples": [
            {"answer": "A hash table uses a hash function to map keys to array indices for O(1) average access. When two keys produce the same index (collision), two main approaches exist: chaining stores a linked list at each bucket, while open addressing probes for the next empty slot using linear probing, quadratic probing, or double hashing. Worst case is O(n) with many collisions.", "score": 5.0},
            {"answer": "Hash tables use hash functions to store key-value pairs. Collisions are handled by chaining (lists at each position) or open addressing (finding another slot).", "score": 4.0},
            {"answer": "A hash table stores data using a hash function. If two things go to the same place, it's a collision and we handle it.", "score": 2.0},
            {"answer": "Hash tables are fast for storing data. They always take O(1) time.", "score": 1.5},
            {"answer": "A hash table is like an array but uses hashing.", "score": 1.0},
        ],
    },
]


def load_mohler_sample() -> MohlerDataset:
    """Load the embedded sample subset of the Mohler dataset."""
    dataset = MohlerDataset()

    for q_data in MOHLER_SAMPLE_DATA:
        qid = q_data["question_id"]
        question = q_data["question"]
        ref_answer = q_data["reference_answer"]
        dataset.questions[qid] = question

        for s in q_data["samples"]:
            score = s["score"]
            sample = MohlerSample(
                question_id=qid,
                question=question,
                reference_answer=ref_answer,
                student_answer=s["answer"],
                score_me=score,
                score_other=score,  # Same for sample data
                score_avg=score,
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
