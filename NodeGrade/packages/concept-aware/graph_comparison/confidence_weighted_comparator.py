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

from typing import Optional

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

            importance = concept.difficulty_level / 5.0
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
