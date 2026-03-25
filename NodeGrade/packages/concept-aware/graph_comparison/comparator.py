"""
Knowledge Graph Comparison Engine.

Compares student concept sub-graphs against the expert domain knowledge graph
to produce multi-dimensional assessment scores and diagnostic feedback.

Assessment dimensions:
1. Concept Coverage Score — what fraction of expected concepts did the student mention?
2. Relationship Accuracy Score — are the relationships between concepts correct?
3. Integration Quality Score — how well-connected is the student's knowledge?
4. Gap Analysis — what concepts and relationships are missing?
5. Misconception Detection — what incorrect relationships exist?
"""

import json
import math
from dataclasses import dataclass, field
from typing import Optional
import networkx as nx

try:
    from ..knowledge_graph.domain_graph import DomainKnowledgeGraph
    from ..knowledge_graph.ontology import Concept, RelationshipType
    from ..concept_extraction.extractor import (
        StudentConceptGraph, ExtractedConcept, ExtractedRelationship
    )
except ImportError:
    from knowledge_graph.domain_graph import DomainKnowledgeGraph
    from knowledge_graph.ontology import Concept, RelationshipType
    from concept_extraction.extractor import (
        StudentConceptGraph, ExtractedConcept, ExtractedRelationship
    )


@dataclass
class ConceptGap:
    """A concept the student was expected to mention but didn't."""
    concept_id: str
    concept_name: str
    importance: float  # How critical is this concept for the answer
    gap_type: str  # "missing", "incomplete", "superficial"
    description: str = ""


@dataclass
class MisconceptionReport:
    """A detected misconception in the student's understanding."""
    source_concept: str
    target_concept: str
    student_relation: str
    correct_relation: Optional[str]
    explanation: str
    severity: str  # "minor", "moderate", "critical"


@dataclass
class ComparisonResult:
    """
    Complete comparison result between student and expert knowledge graphs.
    """
    # Scores (0.0 to 1.0)
    concept_coverage_score: float = 0.0
    relationship_accuracy_score: float = 0.0
    integration_quality_score: float = 0.0
    overall_score: float = 0.0

    # Detailed analysis
    matched_concepts: list[str] = field(default_factory=list)
    missing_concepts: list[ConceptGap] = field(default_factory=list)
    extra_concepts: list[str] = field(default_factory=list)  # Concepts not in expected set
    correct_relationships: list[dict] = field(default_factory=list)
    incorrect_relationships: list[MisconceptionReport] = field(default_factory=list)
    missing_relationships: list[dict] = field(default_factory=list)

    # Diagnostic
    depth_assessment: str = "surface"  # surface, moderate, deep
    feedback_points: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    # Hierarchical KG scores (populated by compare_hierarchical / compare with use_hierarchical=True)
    primary_coverage_score: float = 0.0
    secondary_coverage_score: float = 0.0

    def to_dict(self) -> dict:
        scores: dict = {
            "concept_coverage": round(self.concept_coverage_score, 4),
            "relationship_accuracy": round(self.relationship_accuracy_score, 4),
            "integration_quality": round(self.integration_quality_score, 4),
            "overall": round(self.overall_score, 4),
        }
        if self.primary_coverage_score > 0.0 or self.secondary_coverage_score > 0.0:
            scores["primary_coverage"]   = round(self.primary_coverage_score, 4)
            scores["secondary_coverage"] = round(self.secondary_coverage_score, 4)
        return {
            "scores": scores,
            "analysis": {
                "matched_concepts": self.matched_concepts,
                "missing_concepts": [
                    {"id": g.concept_id, "name": g.concept_name,
                     "importance": g.importance, "type": g.gap_type}
                    for g in self.missing_concepts
                ],
                "extra_concepts": self.extra_concepts,
                "correct_relationships": self.correct_relationships,
                "incorrect_relationships": [
                    {"source": m.source_concept, "target": m.target_concept,
                     "student_relation": m.student_relation,
                     "correct_relation": m.correct_relation,
                     "explanation": m.explanation, "severity": m.severity}
                    for m in self.incorrect_relationships
                ],
                "missing_relationships": self.missing_relationships,
            },
            "diagnostic": {
                "depth_assessment": self.depth_assessment,
                "feedback_points": self.feedback_points,
                "strengths": self.strengths,
                "weaknesses": self.weaknesses,
            }
        }

    def summary(self) -> str:
        """Human-readable summary of the comparison."""
        lines = [
            "=== Concept-Aware Assessment Result ===",
            f"  Overall Score: {self.overall_score:.1%}",
            f"  Concept Coverage: {self.concept_coverage_score:.1%} "
            f"({len(self.matched_concepts)} matched, {len(self.missing_concepts)} missing)",
            f"  Relationship Accuracy: {self.relationship_accuracy_score:.1%}",
            f"  Integration Quality: {self.integration_quality_score:.1%}",
            f"  Depth: {self.depth_assessment}",
        ]
        if self.strengths:
            lines.append(f"  Strengths: {', '.join(self.strengths[:3])}")
        if self.weaknesses:
            lines.append(f"  Weaknesses: {', '.join(self.weaknesses[:3])}")
        if self.incorrect_relationships:
            lines.append(f"  Misconceptions: {len(self.incorrect_relationships)} detected")
        return "\n".join(lines)


class KnowledgeGraphComparator:
    """
    Compares student concept sub-graphs against expert domain knowledge graphs.
    
    Produces multi-dimensional scores and detailed diagnostic feedback
    that goes beyond surface-level similarity matching.
    """

    def __init__(self, domain_graph: DomainKnowledgeGraph):
        self.domain_graph = domain_graph

    def compare_hierarchical(
        self,
        student_graph: StudentConceptGraph,
        expected_concepts: Optional[list[str]] = None,
        weights: Optional[dict[str, float]] = None,
    ) -> ComparisonResult:
        """Run standard comparison then layer on hierarchical primary/secondary scores.

        Primary coverage: fraction of expected *primary* concepts matched.
        Secondary coverage: fraction of expected *secondary* concepts matched.

        Falls back to standard scoring if the expected set contains no primary
        concepts (e.g. a custom expected_concepts list that has no is_primary tags).
        """
        result = self.compare(
            student_graph=student_graph,
            expected_concepts=expected_concepts,
            weights=weights,
        )

        # Determine expected concept set (same logic as compare())
        if expected_concepts:
            expected_set = set(expected_concepts)
        else:
            expected_set = student_graph.concept_ids

        student_concept_ids = student_graph.concept_ids

        # Split expected concepts into primary / secondary
        primary_expected:   list[str] = []
        secondary_expected: list[str] = []

        for cid in expected_set:
            concept = self.domain_graph.get_concept(cid)
            if concept is None:
                continue
            # Default to primary if is_primary field is missing
            if getattr(concept, "is_primary", True):
                primary_expected.append(cid)
            else:
                secondary_expected.append(cid)

        # Fall back to standard if no primary concepts found
        if not primary_expected:
            return result

        # Primary coverage
        primary_matched = [cid for cid in primary_expected if cid in student_concept_ids]
        result.primary_coverage_score = len(primary_matched) / len(primary_expected)

        # Secondary coverage
        if secondary_expected:
            secondary_matched = [cid for cid in secondary_expected if cid in student_concept_ids]
            result.secondary_coverage_score = len(secondary_matched) / len(secondary_expected)
        else:
            result.secondary_coverage_score = 0.0

        return result

    def compare(
        self,
        student_graph: StudentConceptGraph,
        expected_concepts: Optional[list[str]] = None,
        weights: Optional[dict[str, float]] = None,
    ) -> ComparisonResult:
        """
        Compare a student's concept graph against the expert knowledge graph.
        
        Args:
            student_graph: The student's extracted concept sub-graph
            expected_concepts: Optional list of concept IDs expected for this question.
                             If not provided, uses all concepts the student mentioned.
            weights: Optional scoring weights dict with keys:
                     coverage, accuracy, integration (must sum to 1.0)
        
        Returns:
            ComparisonResult with scores and detailed analysis
        """
        if weights is None:
            weights = {"coverage": 0.4, "accuracy": 0.3, "integration": 0.3}

        result = ComparisonResult()

        # Determine expected concepts
        if expected_concepts:
            expected_set = set(expected_concepts)
        else:
            # Use the question-relevant subgraph
            expected_set = student_graph.concept_ids

        student_concept_ids = student_graph.concept_ids

        # 1. Concept Coverage Analysis
        result.concept_coverage_score, result.matched_concepts, result.missing_concepts = (
            self._compute_concept_coverage(student_concept_ids, expected_set)
        )

        # Extra concepts (student mentioned but not in expected set)
        result.extra_concepts = list(student_concept_ids - expected_set)

        # 2. Relationship Accuracy
        result.relationship_accuracy_score, result.correct_relationships, result.incorrect_relationships = (
            self._compute_relationship_accuracy(student_graph)
        )

        # 3. Integration Quality
        result.integration_quality_score, result.missing_relationships = (
            self._compute_integration_quality(student_graph, expected_set)
        )

        # 4. Overall Score (weighted combination)
        result.overall_score = (
            weights["coverage"] * result.concept_coverage_score +
            weights["accuracy"] * result.relationship_accuracy_score +
            weights["integration"] * result.integration_quality_score
        )

        # 5. Depth assessment
        result.depth_assessment = self._assess_depth(student_graph, result)

        # 6. Generate feedback
        result.strengths, result.weaknesses, result.feedback_points = (
            self._generate_feedback(result, student_graph)
        )

        return result

    def _compute_concept_coverage(
        self,
        student_concepts: set[str],
        expected_concepts: set[str]
    ) -> tuple[float, list[str], list[ConceptGap]]:
        """
        Compute concept coverage score.
        
        Uses weighted matching where more important concepts 
        contribute more to the score.
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

            # Weight by difficulty level (higher = more important to mention)
            importance = concept.difficulty_level / 5.0
            # Also weight by connectivity (more connected = more central)
            if concept_id in self.domain_graph.graph:
                degree = self.domain_graph.graph.degree(concept_id)
                importance *= (1.0 + min(degree / 10.0, 1.0))  # Normalize

            total_weight += importance

            if concept_id in student_concepts:
                matched.append(concept_id)
                matched_weight += importance
            else:
                gap = ConceptGap(
                    concept_id=concept_id,
                    concept_name=concept.name,
                    importance=importance,
                    gap_type=self._classify_gap(concept_id, student_concepts),
                    description=f"Expected concept '{concept.name}' not found in student response"
                )
                missing.append(gap)

        score = matched_weight / total_weight if total_weight > 0 else 0.0
        return min(score, 1.0), matched, missing

    def _classify_gap(self, concept_id: str, student_concepts: set[str]) -> str:
        """Classify the type of gap for a missing concept."""
        # Check if related concepts are present (partial understanding)
        neighbors = self.domain_graph.get_neighbors(concept_id)
        has_related = any(
            n_id in student_concepts 
            for n_id, _, _ in neighbors
        )
        
        if has_related:
            return "incomplete"  # Student knows related concepts but missed this one
        
        # Check if this is a prerequisite concept
        concept = self.domain_graph.get_concept(concept_id)
        if concept and concept.difficulty_level <= 2:
            return "missing"  # Basic concept completely absent
        
        return "superficial"  # Advanced concept not reached

    def _compute_relationship_accuracy(
        self, student_graph: StudentConceptGraph
    ) -> tuple[float, list[dict], list[MisconceptionReport]]:
        """
        Check if the relationships the student expressed are correct
        according to the expert knowledge graph.
        """
        correct = []
        incorrect = []

        if not student_graph.relationships:
            return 1.0, [], []

        for rel in student_graph.relationships:
            if not rel.is_correct:
                # LLM already flagged this as incorrect
                misconception = MisconceptionReport(
                    source_concept=rel.source_id,
                    target_concept=rel.target_id,
                    student_relation=rel.relation_type,
                    correct_relation=self._find_correct_relation(
                        rel.source_id, rel.target_id
                    ),
                    explanation=rel.misconception_note,
                    severity=self._assess_severity(rel)
                )
                incorrect.append(misconception)
                continue

            # Verify against expert graph
            is_valid = self._verify_relationship(
                rel.source_id, rel.target_id, rel.relation_type
            )
            
            if is_valid:
                correct.append({
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "type": rel.relation_type,
                    "confidence": rel.confidence
                })
            else:
                # Student stated a relationship that doesn't exist in expert graph
                correct_rel = self._find_correct_relation(
                    rel.source_id, rel.target_id
                )
                if correct_rel:
                    # Wrong relationship type
                    misconception = MisconceptionReport(
                        source_concept=rel.source_id,
                        target_concept=rel.target_id,
                        student_relation=rel.relation_type,
                        correct_relation=correct_rel,
                        explanation=f"Student used '{rel.relation_type}' but the correct relationship is '{correct_rel}'",
                        severity="moderate"
                    )
                    incorrect.append(misconception)
                else:
                    # No known relationship between these concepts
                    # This might be an insightful connection or a misconception
                    correct.append({
                        "source": rel.source_id,
                        "target": rel.target_id,
                        "type": rel.relation_type,
                        "confidence": rel.confidence * 0.7,  # Penalize slightly
                        "note": "Not in expert graph but plausible"
                    })

        total = len(student_graph.relationships)
        accuracy = len(correct) / total if total > 0 else 1.0
        return accuracy, correct, incorrect

    def _verify_relationship(
        self, source_id: str, target_id: str, relation_type: str
    ) -> bool:
        """Check if a specific relationship exists in the expert graph.

        Uses the authoritative _relationships list instead of the NetworkX
        graph to handle concepts with multiple edge types to the same target
        (e.g. binary_search→array exists as both USES and OPERATES_ON).
        """
        for rel in self.domain_graph.get_all_relationships():
            if rel.relation_type.value != relation_type:
                continue
            # Forward direction
            if rel.source_id == source_id and rel.target_id == target_id:
                return True
            # Reverse direction (also valid for symmetric contrasts_with)
            if rel.source_id == target_id and rel.target_id == source_id:
                return True
        return False

    def _find_correct_relation(
        self, source_id: str, target_id: str
    ) -> Optional[str]:
        """Find the correct relationship type(s) between two concepts.

        Returns the first match from the authoritative _relationships list.
        """
        for rel in self.domain_graph.get_all_relationships():
            if (rel.source_id == source_id and rel.target_id == target_id) or \
               (rel.source_id == target_id and rel.target_id == source_id):
                return rel.relation_type.value
        return None

    def _assess_severity(self, rel: ExtractedRelationship) -> str:
        """Assess the severity of a misconception."""
        if rel.confidence > 0.8:
            return "critical"  # Student is very confident in wrong info
        elif rel.confidence > 0.5:
            return "moderate"
        return "minor"

    def _compute_integration_quality(
        self,
        student_graph: StudentConceptGraph,
        expected_concepts: set[str]
    ) -> tuple[float, list[dict]]:
        """
        Assess how well-connected the student's knowledge is.
        
        High integration = concepts are linked together showing understanding
        of how they relate. Low integration = isolated concepts mentioned
        without connections (surface recall).
        """
        student_concepts = student_graph.concept_ids
        if len(student_concepts) <= 1:
            return 0.5 if student_concepts else 0.0, []

        # Build student's subgraph
        student_nx = nx.Graph()
        for c in student_graph.concepts:
            student_nx.add_node(c.concept_id)
        for r in student_graph.relationships:
            if r.source_id in student_concepts and r.target_id in student_concepts:
                student_nx.add_edge(r.source_id, r.target_id)

        # Metrics
        # 1. Connectivity ratio (edges / max_possible_edges)
        n = len(student_concepts)
        max_edges = n * (n - 1) / 2
        actual_edges = student_nx.number_of_edges()
        connectivity = actual_edges / max_edges if max_edges > 0 else 0

        # 2. Check for isolated nodes (mentioned but not connected)
        isolated = list(nx.isolates(student_nx))
        isolation_penalty = len(isolated) / n if n > 0 else 0

        # 3. Compare against expected relationships from expert graph
        missing_rels = []
        expected_rels_count = 0
        found_rels_count = 0

        for concept_id in student_concepts:
            expert_rels = self.domain_graph.get_relationships_for_concept(concept_id)
            for rel in expert_rels:
                other = rel.target_id if rel.source_id == concept_id else rel.source_id
                if other in student_concepts:
                    expected_rels_count += 1
                    # Check if student has this relationship
                    has_it = any(
                        (r.source_id == concept_id and r.target_id == other) or
                        (r.source_id == other and r.target_id == concept_id)
                        for r in student_graph.relationships
                    )
                    if has_it:
                        found_rels_count += 1
                    else:
                        missing_rels.append({
                            "source": rel.source_id,
                            "target": rel.target_id,
                            "type": rel.relation_type.value,
                            "note": "Expected connection not demonstrated"
                        })

        # Avoid double-counting (each edge counted from both directions).
        # Use ceil so odd counts round up rather than losing a relationship.
        expected_rels_count = max(math.ceil(expected_rels_count / 2), 1)
        found_rels_count = math.ceil(found_rels_count / 2)

        rel_coverage = found_rels_count / expected_rels_count if expected_rels_count > 0 else 0

        # Weighted integration score
        integration = (
            0.3 * min(connectivity * 3, 1.0) +  # Normalize connectivity
            0.3 * (1.0 - isolation_penalty) +
            0.4 * rel_coverage
        )

        return min(integration, 1.0), missing_rels[:10]  # Top 10 missing rels

    def _assess_depth(
        self, student_graph: StudentConceptGraph, result: ComparisonResult
    ) -> str:
        """Classify the depth of student understanding."""
        # Deep: many concepts, correct relationships, good integration
        if (result.concept_coverage_score > 0.7 and
            result.relationship_accuracy_score > 0.8 and
            result.integration_quality_score > 0.6):
            return "deep"
        
        # Moderate: decent coverage, some relationships
        if (result.concept_coverage_score > 0.4 and
            student_graph.num_relationships >= 2):
            return "moderate"
        
        # Surface: few concepts, isolated mentions
        return "surface"

    def _generate_feedback(
        self,
        result: ComparisonResult,
        student_graph: StudentConceptGraph
    ) -> tuple[list[str], list[str], list[str]]:
        """Generate diagnostic feedback for the student."""
        strengths = []
        weaknesses = []
        feedback = []

        # Strengths
        if result.concept_coverage_score > 0.7:
            strengths.append("Good concept coverage")
        if result.relationship_accuracy_score > 0.8:
            strengths.append("Accurate understanding of concept relationships")
        if result.integration_quality_score > 0.6:
            strengths.append("Well-integrated knowledge showing connections between concepts")
        if len(result.matched_concepts) > 3:
            strengths.append(f"Identified {len(result.matched_concepts)} relevant concepts")

        # Weaknesses
        if result.missing_concepts:
            critical = [g for g in result.missing_concepts if g.importance > 1.0]
            if critical:
                names = ", ".join(g.concept_name for g in critical[:3])
                weaknesses.append(f"Missing key concepts: {names}")
        
        if result.incorrect_relationships:
            weaknesses.append(
                f"{len(result.incorrect_relationships)} misconception(s) detected"
            )
        
        if result.integration_quality_score < 0.4:
            weaknesses.append("Concepts mentioned in isolation without showing connections")

        # Specific feedback points
        for gap in result.missing_concepts[:3]:
            feedback.append(
                f"Consider discussing '{gap.concept_name}' — "
                f"it's important for a complete answer"
            )
        
        for misconception in result.incorrect_relationships[:3]:
            feedback.append(
                f"Review the relationship between "
                f"'{misconception.source_concept}' and '{misconception.target_concept}': "
                f"{misconception.explanation}"
            )

        if result.depth_assessment == "surface":
            feedback.append(
                "Try to explain HOW concepts relate to each other, "
                "not just listing them"
            )

        return strengths, weaknesses, feedback
