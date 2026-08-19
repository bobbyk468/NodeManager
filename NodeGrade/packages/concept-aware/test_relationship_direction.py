"""
test_relationship_direction.py -- regression tests for the directed-edge
fix in graph_comparison/comparator.py (2026-08-19, external review,
REPRODUCIBILITY.md Finding 6).

Bug: KnowledgeGraphComparator._verify_relationship() previously accepted
BOTH directions for EVERY relation type, even though only CONTRASTS_WITH
is genuinely symmetric. A student claiming "array prerequisite_for
hash_table" when the expert graph actually says "hash_table
prerequisite_for array" (the reverse claim) was scored as correct.

No API key or network access required -- builds a small, self-contained
knowledge graph and exercises the comparator directly.

Run from packages/concept-aware/:
    python3 test_relationship_direction.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import conceptgrade  # noqa: F401 -- warms sys.modules to avoid a pre-existing
                      # circular import when graph_comparison.comparator is
                      # imported directly (before conceptgrade.pipeline has
                      # populated its own module chain).

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def _build_test_graph():
    from knowledge_graph.domain_graph import DomainKnowledgeGraph
    from knowledge_graph.ontology import Concept, ConceptType, Relationship, RelationshipType

    kg = DomainKnowledgeGraph(domain="test", version="test-1.0")
    for cid in ("array", "hash_table", "bfs", "dfs"):
        kg.add_concept(Concept(id=cid, name=cid, concept_type=ConceptType.DATA_STRUCTURE))

    # Directed: array is a real prerequisite for hash_table, not the reverse.
    kg.add_relationship(Relationship(
        source_id="array", target_id="hash_table",
        relation_type=RelationshipType.PREREQUISITE_FOR,
    ))
    # Symmetric: BFS contrasts_with DFS should hold in either stated order.
    kg.add_relationship(Relationship(
        source_id="bfs", target_id="dfs",
        relation_type=RelationshipType.CONTRASTS_WITH,
    ))
    return kg


def test_directed_relation_rejects_reverse():
    print("\n=== Directed relation type (prerequisite_for) ===")
    from graph_comparison.comparator import KnowledgeGraphComparator

    kg = _build_test_graph()
    comparator = KnowledgeGraphComparator(kg)

    check(
        "forward direction (array prerequisite_for hash_table) verifies as True",
        comparator._verify_relationship("array", "hash_table", "prerequisite_for") is True,
    )
    check(
        "reverse direction (hash_table prerequisite_for array) is REJECTED "
        "(this is the bug: it used to return True)",
        comparator._verify_relationship("hash_table", "array", "prerequisite_for") is False,
    )
    check(
        "_find_correct_relation on the reverse pair does NOT offer the "
        "reversed claim as if it were the same fact",
        comparator._find_correct_relation("hash_table", "array") is None,
    )
    check(
        "_find_correct_relation on the forward pair correctly identifies it",
        comparator._find_correct_relation("array", "hash_table") == "prerequisite_for",
    )


def test_symmetric_relation_accepts_both_directions():
    print("\n=== Symmetric relation type (contrasts_with) ===")
    from graph_comparison.comparator import KnowledgeGraphComparator

    kg = _build_test_graph()
    comparator = KnowledgeGraphComparator(kg)

    check(
        "forward direction (bfs contrasts_with dfs) verifies as True",
        comparator._verify_relationship("bfs", "dfs", "contrasts_with") is True,
    )
    check(
        "reverse direction (dfs contrasts_with bfs) ALSO verifies as True "
        "(contrasts_with is genuinely symmetric, this direction should stay valid)",
        comparator._verify_relationship("dfs", "bfs", "contrasts_with") is True,
    )
    check(
        "_find_correct_relation finds the symmetric relation from either order",
        comparator._find_correct_relation("dfs", "bfs") == "contrasts_with"
        and comparator._find_correct_relation("bfs", "dfs") == "contrasts_with",
    )


def test_end_to_end_relationship_accuracy_scoring():
    print("\n=== End-to-end: _compute_relationship_accuracy scores the reversed claim as wrong ===")
    from graph_comparison.comparator import KnowledgeGraphComparator
    from concept_extraction.extractor import StudentConceptGraph, ExtractedRelationship

    kg = _build_test_graph()
    comparator = KnowledgeGraphComparator(kg)

    # Student states the REVERSED (incorrect) direction of a directed relation.
    student_graph = StudentConceptGraph(
        question="test", student_answer="test",
        relationships=[ExtractedRelationship(
            source_id="hash_table", target_id="array",
            relation_type="prerequisite_for", confidence=0.9, evidence="test",
            is_correct=True,  # LLM extractor didn't flag it -- comparator must catch it
        )],
    )
    accuracy, correct, incorrect = comparator._compute_relationship_accuracy(student_graph)
    check(
        "reversed directed claim is NOT counted as correct",
        accuracy == 0.0 and len(correct) == 0 and len(incorrect) == 1,
        f"accuracy={accuracy}, correct={len(correct)}, incorrect={len(incorrect)}",
    )


def main() -> int:
    test_directed_relation_rejects_reverse()
    test_symmetric_relation_accepts_both_directions()
    test_end_to_end_relationship_accuracy_scoring()

    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed: {FAILURES}")
        return 1
    print("PASS: all relationship-direction regression checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
