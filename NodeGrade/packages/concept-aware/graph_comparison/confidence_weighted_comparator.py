"""
Confidence-Weighted Knowledge Graph Comparator.

Research Extension 2 — ConceptGrade Enhancement.

Motivation
----------
Standard KG comparison treats concept presence as binary: a concept either
matched (weight = importance) or missed (weight = 0). This ignores extraction
confidence — a concept extracted with confidence=0.95 is much more reliable
evidence than one extracted with confidence=0.40.

This extension weights each matched concept's contribution by its extraction
confidence, producing a more accurate coverage score that:
  - Rewards high-confidence concept mentions
  - Softly penalizes low-confidence mentions (may be hallucinated)
  - Correlates better with human rater scores on noisy short answers

Algorithm
---------
Coverage score numerator:
  Σ (concept_importance_i × extraction_confidence_i)   for matched concepts

vs. standard:
  Σ (concept_importance_i)                              for matched concepts

Effect on downstream scoring
-----------------------------
  Higher precision → fewer false-positive matches → score better calibrated
  to student actual knowledge → higher Pearson r with human grades.
"""

from __future__ import annotations

import re
from typing import Optional

try:
    import networkx as nx
except ImportError:
    nx = None  # type: ignore

try:
    from graph_comparison.comparator import (
        KnowledgeGraphComparator,
        ComparisonResult,
        ConceptGap,
    )
    from knowledge_graph.domain_graph import DomainKnowledgeGraph
    from concept_extraction.extractor import StudentConceptGraph
except ImportError:
    from comparator import KnowledgeGraphComparator, ComparisonResult, ConceptGap
    from knowledge_graph.domain_graph import DomainKnowledgeGraph
    from concept_extraction.extractor import StudentConceptGraph


class ConfidenceWeightedComparator(KnowledgeGraphComparator):
    """
    KG Comparator that weights concept coverage by extraction confidence.

    Parameters
    ----------
    domain_graph  : Expert knowledge graph
    alpha         : Confidence blending factor (0 = ignore confidence,
                    1 = full confidence weighting). Default 1.0.
    """

    def __init__(self, domain_graph: DomainKnowledgeGraph, alpha: float = 1.0):
        super().__init__(domain_graph=domain_graph)
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be in [0, 1]")
        self.alpha = alpha

    # ── Override coverage computation ────────────────────────────────────────

    def compare(
        self,
        student_graph: StudentConceptGraph,
        expected_concepts: Optional[list[str]] = None,
        weights: Optional[dict[str, float]] = None,
        question: Optional[str] = None,
    ) -> ComparisonResult:
        """
        Run comparison with confidence-weighted coverage scoring.

        All other dimensions (relationship accuracy, integration quality)
        are inherited unchanged from KnowledgeGraphComparator.
        """
        if weights is None:
            weights = {"coverage": 0.4, "accuracy": 0.3, "integration": 0.3}

        result = ComparisonResult()

        # Determine expected concepts
        if expected_concepts:
            expected_set = set(expected_concepts)
        else:
            expected_set = student_graph.concept_ids

        student_concept_ids = student_graph.concept_ids

        # Build confidence lookup: concept_id → extraction_confidence
        confidence_map: dict[str, float] = {
            c.concept_id: c.confidence for c in student_graph.concepts
        }

        # 1. Confidence-weighted concept coverage
        result.concept_coverage_score, result.matched_concepts, result.missing_concepts = (
            self._weighted_coverage(student_concept_ids, expected_set, confidence_map)
        )

        result.extra_concepts = list(student_concept_ids - expected_set)

        # 2-3. Accuracy + integration unchanged
        result.relationship_accuracy_score, result.correct_relationships, result.incorrect_relationships = (
            self._compute_relationship_accuracy(student_graph)
        )

        result.integration_quality_score, result.missing_relationships = (
            self._compute_integration_quality(student_graph, expected_set)
        )

        # 4. Overall
        result.overall_score = (
            weights["coverage"] * result.concept_coverage_score +
            weights["accuracy"] * result.relationship_accuracy_score +
            weights["integration"] * result.integration_quality_score
        )

        result.depth_assessment = self._assess_depth(student_graph, result)
        result.strengths, result.weaknesses, result.feedback_points = (
            self._generate_feedback(result, student_graph)
        )

        # 5. Topological features (Anchor-Conductance)
        result.anchor_ratio, result.clustering_coefficient, result.graph_diameter, result.topological_summary = (
            self._compute_topological(result.matched_concepts, student_concept_ids)
        )

        # 6. Epistemic uncertainty ρ (question/KG keyword overlap)
        if question:
            result.kg_relevance_score = self._compute_kg_relevance(question)

        return result

    # ── Internal ─────────────────────────────────────────────────────────────

    def _weighted_coverage(
        self,
        student_concepts: set[str],
        expected_concepts: set[str],
        confidence_map: dict[str, float],
    ) -> tuple[float, list[str], list[ConceptGap]]:
        """
        Confidence-weighted coverage score.

        For each matched concept:
            contribution = importance × (alpha × confidence + (1 - alpha) × 1.0)

        When alpha=0 this reduces to the standard binary coverage.
        When alpha=1 a concept with confidence 0.5 contributes half as much.
        """
        if not expected_concepts:
            return 1.0, list(student_concepts), []

        matched = []
        missing = []
        total_weight = 0.0
        matched_weight = 0.0

        for concept_id in expected_concepts:
            concept = self.domain_graph.get_concept(concept_id)
            if not concept:
                continue

            # Saliency: primary concepts are core — secondary are fringe detail.
            # Missing a fringe concept should not heavily penalise a mastery answer.
            saliency = 1.0 if concept.is_primary else 0.35

            importance = saliency * concept.difficulty_level / 5.0
            if concept_id in self.domain_graph.graph:
                degree = self.domain_graph.graph.degree(concept_id)
                importance *= (1.0 + min(degree / 10.0, 1.0))

            total_weight += importance

            if concept_id in student_concepts:
                matched.append(concept_id)
                conf = confidence_map.get(concept_id, 1.0)
                # Blend: alpha controls how much confidence matters
                effective_conf = self.alpha * conf + (1.0 - self.alpha) * 1.0
                matched_weight += importance * effective_conf
            else:
                gap = ConceptGap(
                    concept_id=concept_id,
                    concept_name=concept.name,
                    importance=importance,
                    gap_type=self._classify_gap(concept_id, student_concepts),
                    description=f"Expected concept '{concept.name}' not found in student response",
                )
                missing.append(gap)

        score = matched_weight / total_weight if total_weight > 0 else 0.0
        return min(score, 1.0), matched, missing

    # ── Topological features ─────────────────────────────────────────────────

    def _compute_topological(
        self,
        matched_concepts: list[str],
        student_concept_ids: set[str],
    ) -> tuple[float, float, int, str]:
        """
        Compute Anchor-Conductance topological features.

        Returns
        -------
        (anchor_ratio, clustering_coefficient, graph_diameter, topological_summary)

        anchor_ratio
            len(matched) / len(student_concepts) — proportion of student concepts
            that are grounded in the domain KG. Low values signal hallucination /
            invented vocabulary.

        clustering_coefficient
            Average clustering of the matched concept subgraph. High value means
            the student's matched concepts form tightly-knit clusters (depth);
            low value means isolated mentions (breadth bluffing).

        graph_diameter
            Longest shortest path in the matched subgraph. A longer diameter
            suggests the student connects distant parts of the KG (integration).
        """
        n_student = len(student_concept_ids)
        n_matched = len(matched_concepts)

        anchor_ratio = n_matched / max(1, n_student)

        clustering_coeff = 0.0
        diameter = 0

        if nx is not None and n_matched >= 2:
            subgraph = self.domain_graph.graph.subgraph(matched_concepts)
            if subgraph.number_of_nodes() >= 2:
                # Undirected view for clustering coefficient
                ug = subgraph.to_undirected() if subgraph.is_directed() else subgraph
                try:
                    clustering_coeff = nx.average_clustering(ug)
                except Exception:
                    clustering_coeff = 0.0

                # Diameter — only for connected components (take the largest)
                try:
                    components = list(nx.connected_components(ug))
                    largest = max(components, key=len)
                    if len(largest) >= 2:
                        sub = ug.subgraph(largest)
                        diameter = nx.diameter(sub)
                except Exception:
                    diameter = 0

        # Build human-readable summary
        parts: list[str] = []

        if anchor_ratio < 0.40:
            parts.append(
                f"Anchor Ratio {anchor_ratio:.0%}: very low — "
                "many student concepts are not in the domain KG; "
                "evaluate carefully for hallucination or invented terminology."
            )
        elif anchor_ratio < 0.65:
            parts.append(
                f"Anchor Ratio {anchor_ratio:.0%}: moderate — "
                "some student concepts fall outside the KG vocabulary."
            )
        else:
            parts.append(f"Anchor Ratio {anchor_ratio:.0%}: high — student concepts are well-grounded in KG.")

        if n_matched >= 2:
            parts.append(
                f"Clustering {clustering_coeff:.2f} "
                f"(0=isolated mentions, 1=tightly connected); "
                f"Diameter {diameter} (path length across matched KG subgraph)."
            )

        summary = " ".join(parts)
        return anchor_ratio, clustering_coeff, diameter, summary

    # ── Epistemic uncertainty ρ ───────────────────────────────────────────────

    def _compute_kg_relevance(self, question: str) -> float:
        """
        Compute ρ = question/KG keyword overlap.

        Tokenise the question into content words, then count how many appear
        in the KG concept names or aliases. ρ close to 1.0 means the question
        is well-covered by the KG; ρ close to 0.0 means the KG is off-topic.

        When ρ is low, the verifier should rely more on holistic LLM judgment
        and treat KG coverage scores with lower weight.
        """
        # Collect all KG vocabulary (concept names + aliases, lowercased)
        kg_vocab: set[str] = set()
        for concept in self.domain_graph._concepts.values():
            for token in re.split(r'[\s_\-/]+', concept.name.lower()):
                if len(token) > 2:
                    kg_vocab.add(token)
            for alias in getattr(concept, "aliases", []):
                for token in re.split(r'[\s_\-/]+', alias.lower()):
                    if len(token) > 2:
                        kg_vocab.add(token)

        # Tokenise question — ignore stopwords and short tokens
        _STOPWORDS = {
            "what", "how", "why", "when", "where", "which", "who",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "can", "could", "should", "may", "might", "shall",
            "in", "on", "at", "to", "for", "of", "with", "by", "from",
            "and", "or", "but", "not", "if", "that", "this", "these", "those",
            "explain", "describe", "define", "discuss", "compare", "contrast",
        }
        q_tokens = [
            t for t in re.split(r'[^a-z]+', question.lower())
            if len(t) > 2 and t not in _STOPWORDS
        ]

        if not q_tokens:
            return 1.0  # No content words — assume KG is relevant

        matched = sum(1 for t in q_tokens if t in kg_vocab)
        return min(1.0, matched / len(q_tokens))
