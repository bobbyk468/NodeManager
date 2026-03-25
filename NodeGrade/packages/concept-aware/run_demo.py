#!/usr/bin/env python3
"""
End-to-End Demo: Concept-Aware Student Assessment Pipeline

1. Builds the Data Structures domain knowledge graph
2. Extracts concepts from sample student answers via Groq API
3. Compares student sub-graphs against expert graph
4. Produces multi-dimensional assessment scores

Usage: python -m concept-aware.run_demo
"""

import os
import sys
import json

# Add parent directory to path for relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from importlib import import_module

# Direct imports (avoid relative import issues when running as script)
from knowledge_graph.ontology import Concept, Relationship, ConceptType, RelationshipType
from knowledge_graph.domain_graph import DomainKnowledgeGraph
from knowledge_graph.ds_knowledge_graph import build_data_structures_graph, get_topic_questions
from concept_extraction.extractor import ConceptExtractor, StudentConceptGraph
from graph_comparison.comparator import KnowledgeGraphComparator, ComparisonResult


# Groq API Key
GROQ_API_KEY = os.environ.get(
    "GROQ_API_KEY",
    ""
)


# Sample student answers with varying quality levels
SAMPLE_QA = [
    {
        "question": "What is a linked list and how does it differ from an array?",
        "expected_concepts": [
            "linked_list", "array", "node", "pointer", "data_structure",
            "insertion", "deletion", "access", "dynamic_memory", "static_memory"
        ],
        "answers": {
            "excellent": (
                "A linked list is a linear data structure where each element (called a node) "
                "contains data and a pointer to the next node in the sequence. Unlike arrays, "
                "which store elements in contiguous memory locations allowing O(1) random access, "
                "linked lists use dynamic memory allocation where nodes can be scattered in memory. "
                "This makes insertion and deletion O(1) at the head, compared to O(n) for arrays "
                "which require shifting elements. However, linked lists sacrifice random access — "
                "you must traverse from the head to find the nth element, making access O(n). "
                "Arrays are better when you need fast access by index, while linked lists excel "
                "when frequent insertions and deletions are needed."
            ),
            "average": (
                "A linked list is made of nodes that are connected by pointers. Each node has "
                "data and a pointer to the next node. It's different from an array because arrays "
                "use contiguous memory but linked lists don't. You can add and remove elements "
                "more easily in a linked list."
            ),
            "poor": (
                "A linked list is a type of list that stores data. It is different from an array."
            ),
        }
    },
    {
        "question": "Explain how BFS and DFS work and when you would use each.",
        "expected_concepts": [
            "bfs", "dfs", "graph", "queue", "stack", "traversal",
            "shortest_path", "vertex", "edge"
        ],
        "answers": {
            "excellent": (
                "BFS (Breadth-First Search) explores a graph level by level, using a queue data "
                "structure. Starting from a source vertex, it visits all neighbors first before "
                "moving to the next level. This makes BFS ideal for finding the shortest path "
                "in unweighted graphs. DFS (Depth-First Search) explores as deep as possible "
                "along each branch before backtracking, using a stack (or recursion's call stack). "
                "DFS is useful for topological sorting, detecting cycles, and solving maze-like "
                "problems. Both have O(V+E) time complexity. BFS uses more memory (O(V) for the "
                "queue) while DFS can use O(V) stack space in the worst case."
            ),
            "average": (
                "BFS uses a queue and visits nodes level by level. DFS uses a stack and goes "
                "deep first. BFS is good for shortest path. DFS is good for exploring all paths."
            ),
            "poor": (
                "BFS and DFS are ways to search through a graph. BFS goes wide and DFS goes deep."
            ),
        }
    },
    {
        "question": "How does a hash table handle collisions?",
        "expected_concepts": [
            "hash_table", "hash_function", "collision", "chaining",
            "open_addressing", "linked_list", "load_factor"
        ],
        "answers": {
            "excellent": (
                "Hash collisions occur when two different keys map to the same index through "
                "the hash function. There are two main strategies: Separate chaining stores "
                "multiple elements at the same index using a linked list (or other collection). "
                "When a collision occurs, the new element is appended to the list at that bucket. "
                "Open addressing instead probes for the next available slot — linear probing "
                "checks consecutive slots, while quadratic probing uses a quadratic function. "
                "The load factor (n/m where n is elements and m is table size) affects performance — "
                "as it approaches 1.0, collisions increase and operations degrade from O(1) average "
                "to O(n) worst case. Resizing (rehashing) is triggered when the load factor exceeds "
                "a threshold, typically 0.75."
            ),
            "average": (
                "When two keys hash to the same index, that's a collision. Chaining uses linked "
                "lists to store multiple values at the same index. Open addressing finds another "
                "empty slot in the table."
            ),
            "poor": (
                "Collisions happen when two things go to the same place. You can use chaining."
            ),
        }
    },
]


def run_demo():
    """Run the full concept-aware assessment demo."""
    print("=" * 70)
    print("  CONCEPT-AWARE STUDENT ASSESSMENT — End-to-End Demo")
    print("=" * 70)
    
    # Step 1: Build Domain Knowledge Graph
    print("\n[Step 1] Building Data Structures domain knowledge graph...")
    domain_graph = build_data_structures_graph()
    print(domain_graph.summary())
    
    # Save the graph
    output_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)
    graph_path = os.path.join(output_dir, "ds_knowledge_graph.json")
    domain_graph.save(graph_path)
    print(f"  Saved to: {graph_path}")

    # Step 2: Initialize extractors
    print("\n[Step 2] Initializing concept extractor (Groq API + Llama-3.3-70B)...")
    extractor = ConceptExtractor(
        domain_graph=domain_graph,
        api_key=GROQ_API_KEY,
        model="claude-haiku-4-5-20251001"
    )
    comparator = KnowledgeGraphComparator(domain_graph)

    # Step 3: Process sample answers
    all_results = []
    
    for qa_set in SAMPLE_QA:
        question = qa_set["question"]
        expected = qa_set["expected_concepts"]
        
        print(f"\n{'=' * 70}")
        print(f"  QUESTION: {question}")
        print(f"  Expected concepts: {len(expected)}")
        print(f"{'=' * 70}")
        
        for quality, answer in qa_set["answers"].items():
            print(f"\n  --- {quality.upper()} Answer ---")
            print(f"  {answer[:120]}...")
            
            # Extract concepts
            print(f"  [Extracting concepts...]")
            student_graph = extractor.extract(question, answer)
            print(f"  Found: {student_graph.num_concepts} concepts, "
                  f"{student_graph.num_relationships} relationships")
            
            # Compare against expert graph
            result = comparator.compare(
                student_graph,
                expected_concepts=expected
            )
            
            print(f"\n{result.summary()}")
            
            if result.incorrect_relationships:
                for m in result.incorrect_relationships[:2]:
                    print(f"  ⚠ Misconception: {m.source_concept} → {m.target_concept}: {m.explanation}")
            
            all_results.append({
                "question": question,
                "quality": quality,
                "answer": answer,
                "extraction": student_graph.to_dict(),
                "comparison": result.to_dict()
            })

    # Save all results
    results_path = os.path.join(output_dir, "demo_results.json")
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n\nAll results saved to: {results_path}")
    
    # Print summary table
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"{'Question':<40} {'Quality':<12} {'Coverage':>10} {'Accuracy':>10} {'Integration':>12} {'Overall':>10}")
    print("-" * 94)
    for r in all_results:
        q_short = r["question"][:38]
        scores = r["comparison"]["scores"]
        print(f"{q_short:<40} {r['quality']:<12} "
              f"{scores['concept_coverage']:>9.1%} "
              f"{scores['relationship_accuracy']:>9.1%} "
              f"{scores['integration_quality']:>11.1%} "
              f"{scores['overall']:>9.1%}")

    print(f"\nDemo complete. Processed {len(all_results)} student answer assessments.")
    return all_results


if __name__ == "__main__":
    run_demo()
