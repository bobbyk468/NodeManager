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
    semantic_concept_match,
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


def test_semantic_match_works_with_embedder(monkeypatch):
    import numpy as np
    import concept_matching as cm

    class FakeModel:
        def encode(self, texts, normalize_embeddings=True):  # noqa: ARG002
            # Encode by token counts across tiny vocabulary to produce deterministic cosine sims.
            vocab = ["photosynthesis", "respiration", "sunlight", "glucose"]
            arr = []
            for t in texts:
                low = t.lower()
                arr.append([float(low.count(tok)) for tok in vocab])
            return np.array(arr, dtype=np.float32)

    monkeypatch.setattr(cm, "_load_embedder", lambda: FakeModel())

    concepts = [
        {"id": "photosynthesis", "name": "Photosynthesis", "description": "sunlight glucose"},
        {"id": "respiration", "name": "Respiration", "description": "oxygen breakdown"},
    ]
    out = semantic_concept_match(
        "Plants use sunlight for photosynthesis to make glucose.",
        concepts,
        sim_threshold=0.1,
    )
    assert "photosynthesis" in out
    assert "respiration" not in out


if __name__ == "__main__":
    test_keyword_linked_list()
    test_coverage_and_threshold()
    test_unified_falls_back_without_embeddings()
    print("concept_matching tests: OK")
