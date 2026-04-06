"""Lightweight checks for concept_matching (no sentence-transformers required)."""

from __future__ import annotations

import os

# Keyword path only in CI / dev without torch
os.environ.setdefault("CONCEPTGRADE_SEMANTIC", "0")

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concept_matching import (  # noqa: E402
    ConceptEmbeddingCache,
    coverage_ratio,
    should_use_kg_evidence,
    simple_concept_match,
    unified_concept_match,
)


def test_keyword_linked_list():
    concepts = [{"id": "linked_list", "name": "Linked List", "description": "nodes and pointers"}]
    m = simple_concept_match("The linked list connects nodes with pointers", concepts)
    assert "linked_list" in m


def test_coverage_and_threshold():
    assert coverage_ratio(["a", "b"], ["a", "b", "c"]) < 1.0
    assert should_use_kg_evidence(0.30) is True
    assert should_use_kg_evidence(0.10, min_coverage=0.25) is False


def test_unified_falls_back_without_embeddings():
    qkg = {"q1": {"concepts": [{"id": "x", "name": "photosynthesis", "description": ""}]}}
    cache = ConceptEmbeddingCache(qkg)
    m = unified_concept_match("photosynthesis makes food", qkg["q1"]["concepts"], cache=cache)
    assert "x" in m


if __name__ == "__main__":
    test_keyword_linked_list()
    test_coverage_and_threshold()
    test_unified_falls_back_without_embeddings()
    print("concept_matching tests: OK")
