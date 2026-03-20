"""
ConceptGrade Unified Assessment Pipeline.

Orchestrates the complete 5-layer concept-aware assessment:
  Layer 1: Domain Knowledge Graph (expert reference)
  Layer 2: Concept Extraction + KG Comparison
  Layer 3: Bloom's Taxonomy Classification
  Layer 4: SOLO Taxonomy Classification + Misconception Detection
  Layer 5: V-NLI Analytics + Visualization

This module provides:
  - Single-student assessment (assess_student)
  - Batch assessment for entire class (assess_class)
  - Class-level analytics aggregation (analyze_class)
  - Query-driven analytics (query)

Paper 3: "ConceptGrade: An Integrated Framework for Concept-Understanding
Assessment with Visual Natural Language Interface for Educational Analytics"
"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from knowledge_graph.domain_graph import DomainKnowledgeGraph
from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
from concept_extraction.extractor import ConceptExtractor
from graph_comparison.comparator import KnowledgeGraphComparator
from cognitive_depth.blooms_classifier import BloomsClassifier
from cognitive_depth.solo_classifier import SOLOClassifier
from misconception_detection.detector import MisconceptionDetector
from nl_query_engine.parser import NLQueryParser, ParsedQuery, QueryType


@dataclass
class StudentAssessment:
    """Complete assessment result for a single student response."""
    student_id: str
    question: str
    answer: str
    timestamp: str = ""

    # Layer 2: Concept extraction + comparison
    concept_graph: dict = field(default_factory=dict)
    comparison: dict = field(default_factory=dict)

    # Layer 3: Bloom's classification
    blooms: dict = field(default_factory=dict)

    # Layer 4: SOLO classification + misconceptions
    solo: dict = field(default_factory=dict)
    misconceptions: dict = field(default_factory=dict)

    # Composite scores
    overall_score: float = 0.0
    depth_category: str = "surface"  # surface, moderate, deep, expert

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "question": self.question,
            "answer": self.answer,
            "timestamp": self.timestamp,
            "concept_graph": self.concept_graph,
            "comparison": self.comparison,
            "blooms": self.blooms,
            "solo": self.solo,
            "misconceptions": self.misconceptions,
            "overall_score": round(self.overall_score, 4),
            "depth_category": self.depth_category,
        }


@dataclass
class ClassAnalytics:
    """Aggregated analytics for an entire class."""
    num_students: int = 0
    question: str = ""
    timestamp: str = ""

    # Bloom's distribution
    blooms_distribution: dict = field(default_factory=dict)  # {level_label: count}
    blooms_average: float = 0.0

    # SOLO distribution
    solo_distribution: dict = field(default_factory=dict)  # {level_label: count}
    solo_average: float = 0.0

    # Concept analytics
    concept_coverage_avg: float = 0.0
    most_demonstrated_concepts: list = field(default_factory=list)  # [(concept_id, count)]
    most_missed_concepts: list = field(default_factory=list)  # [(concept_id, count)]
    concept_student_matrix: dict = field(default_factory=dict)  # {concept: {student: bool}}

    # Misconception analytics
    total_misconceptions: int = 0
    misconception_frequency: dict = field(default_factory=dict)  # {description: count}
    misconception_by_concept: dict = field(default_factory=dict)  # {concept: [misconceptions]}
    students_with_critical: list = field(default_factory=list)

    # Overall
    class_average_score: float = 0.0
    depth_distribution: dict = field(default_factory=dict)  # {category: count}

    def to_dict(self) -> dict:
        return {
            "num_students": self.num_students,
            "question": self.question,
            "timestamp": self.timestamp,
            "blooms": {
                "distribution": self.blooms_distribution,
                "average_level": round(self.blooms_average, 2),
            },
            "solo": {
                "distribution": self.solo_distribution,
                "average_level": round(self.solo_average, 2),
            },
            "concepts": {
                "coverage_average": round(self.concept_coverage_avg, 3),
                "most_demonstrated": self.most_demonstrated_concepts[:10],
                "most_missed": self.most_missed_concepts[:10],
            },
            "misconceptions": {
                "total": self.total_misconceptions,
                "frequency": self.misconception_frequency,
                "by_concept": self.misconception_by_concept,
                "students_with_critical": self.students_with_critical,
            },
            "overall": {
                "class_average_score": round(self.class_average_score, 3),
                "depth_distribution": self.depth_distribution,
            },
        }


class ConceptGradePipeline:
    """
    Unified ConceptGrade assessment pipeline.
    
    Orchestrates all 5 layers of the concept-aware assessment framework.
    """

    def __init__(
        self,
        api_key: str,
        domain_graph: Optional[DomainKnowledgeGraph] = None,
        model: str = "llama-3.3-70b-versatile",
        rate_limit_delay: float = 1.5,
    ):
        """
        Initialize the ConceptGrade pipeline.
        
        Args:
            api_key: Groq API key
            domain_graph: Expert knowledge graph (defaults to DS graph)
            model: LLM model name
            rate_limit_delay: Seconds between API calls for rate limiting
        """
        self.api_key = api_key
        self.model = model
        self.rate_limit_delay = rate_limit_delay

        # Layer 1: Domain Knowledge Graph
        self.domain_graph = domain_graph or build_data_structures_graph()

        # Layer 2: Concept Extraction + Comparison
        self.extractor = ConceptExtractor(
            domain_graph=self.domain_graph, api_key=api_key, model=model
        )
        self.comparator = KnowledgeGraphComparator(
            domain_graph=self.domain_graph
        )

        # Layer 3-4: Cognitive Depth + Misconceptions
        self.blooms_clf = BloomsClassifier(api_key=api_key, model=model)
        self.solo_clf = SOLOClassifier(api_key=api_key, model=model)
        self.misconception_det = MisconceptionDetector(api_key=api_key, model=model)

        # Layer 5: NL Query Parser
        self.query_parser = NLQueryParser(api_key=api_key, model=model)

    def assess_student(
        self,
        student_id: str,
        question: str,
        answer: str,
    ) -> StudentAssessment:
        """
        Run the full 5-layer assessment pipeline on a single student response.
        
        Args:
            student_id: Unique student identifier
            question: The assessment question
            answer: Student's free-text response
            
        Returns:
            StudentAssessment with all layers populated
        """
        result = StudentAssessment(
            student_id=student_id,
            question=question,
            answer=answer,
            timestamp=datetime.now().isoformat(),
        )

        # Layer 2: Concept Extraction
        try:
            concept_graph_obj = self.extractor.extract(
                question=question, student_answer=answer
            )
            result.concept_graph = concept_graph_obj.to_dict()
            time.sleep(self.rate_limit_delay)
        except Exception as e:
            result.concept_graph = {"error": str(e), "concepts": [], "relationships": []}
            concept_graph_obj = None

        # Layer 2: KG Comparison
        try:
            if concept_graph_obj:
                comparison_obj = self.comparator.compare(student_graph=concept_graph_obj)
                result.comparison = comparison_obj.to_dict()
            else:
                result.comparison = {"scores": {}, "analysis": {}, "diagnostic": {}}
        except Exception as e:
            result.comparison = {"error": str(e), "scores": {}, "analysis": {}, "diagnostic": {}}

        # Layer 3: Bloom's Classification
        try:
            blooms_result = self.blooms_clf.classify(
                question=question,
                student_answer=answer,
                concept_graph=result.concept_graph,
                comparison_result=result.comparison,
            )
            result.blooms = blooms_result.to_dict()
            time.sleep(self.rate_limit_delay)
        except Exception as e:
            result.blooms = {"error": str(e), "level": 1, "label": "Remember", "confidence": 0}

        # Layer 4: SOLO Classification
        try:
            solo_result = self.solo_clf.classify(
                question=question,
                student_answer=answer,
                concept_graph=result.concept_graph,
                comparison_result=result.comparison,
            )
            result.solo = solo_result.to_dict()
            time.sleep(self.rate_limit_delay)
        except Exception as e:
            result.solo = {"error": str(e), "level": 1, "label": "Prestructural", "confidence": 0}

        # Layer 4: Misconception Detection
        try:
            misc_result = self.misconception_det.detect(
                question=question,
                student_answer=answer,
                concept_graph=result.concept_graph,
                comparison_result=result.comparison,
            )
            result.misconceptions = misc_result.to_dict()
            time.sleep(self.rate_limit_delay)
        except Exception as e:
            result.misconceptions = {"error": str(e), "total_misconceptions": 0, "misconceptions": []}

        # Compute composite score
        result.overall_score = self._compute_overall_score(result)
        result.depth_category = self._categorize_depth(result)

        return result

    def assess_class(
        self,
        question: str,
        student_answers: dict[str, str],
    ) -> list[StudentAssessment]:
        """
        Assess an entire class of student responses.
        
        Args:
            question: The assessment question
            student_answers: {student_id: answer_text}
            
        Returns:
            List of StudentAssessment objects
        """
        results = []
        for student_id, answer in student_answers.items():
            assessment = self.assess_student(student_id, question, answer)
            results.append(assessment)
        return results

    def analyze_class(self, assessments: list[StudentAssessment]) -> ClassAnalytics:
        """
        Compute aggregated class-level analytics from individual assessments.
        
        Args:
            assessments: List of StudentAssessment objects
            
        Returns:
            ClassAnalytics with distributions, frequencies, and aggregations
        """
        analytics = ClassAnalytics(
            num_students=len(assessments),
            question=assessments[0].question if assessments else "",
            timestamp=datetime.now().isoformat(),
        )

        # Bloom's distribution
        blooms_levels = {
            "Remember": 0, "Understand": 0, "Apply": 0,
            "Analyze": 0, "Evaluate": 0, "Create": 0,
        }
        blooms_sum = 0

        # SOLO distribution
        solo_levels = {
            "Prestructural": 0, "Unistructural": 0, "Multistructural": 0,
            "Relational": 0, "Extended Abstract": 0,
        }
        solo_sum = 0

        # Concept tracking
        concept_counts = {}  # concept_id → count of students who demonstrated it
        missing_counts = {}  # concept_id → count of students who missed it
        concept_matrix = {}  # concept_id → {student_id: True/False}

        # Misconception tracking
        misc_freq = {}  # description → count
        misc_by_concept = {}  # concept → [misconception descriptions]
        critical_students = []

        # Depth distribution
        depth_dist = {"surface": 0, "moderate": 0, "deep": 0, "expert": 0}
        score_sum = 0

        for a in assessments:
            # Bloom's
            b_label = a.blooms.get("label", "Remember")
            if b_label in blooms_levels:
                blooms_levels[b_label] += 1
            blooms_sum += a.blooms.get("level", 1)

            # SOLO
            s_label = a.solo.get("label", "Prestructural")
            if s_label in solo_levels:
                solo_levels[s_label] += 1
            solo_sum += a.solo.get("level", 1)

            # Concepts
            cg = a.concept_graph
            student_concepts = set()
            for c in cg.get("concepts", []):
                cid = c.get("concept_id", c.get("id", "unknown"))
                student_concepts.add(cid)
                concept_counts[cid] = concept_counts.get(cid, 0) + 1
                if cid not in concept_matrix:
                    concept_matrix[cid] = {}
                concept_matrix[cid][a.student_id] = True

            # Missing concepts
            for mc in a.comparison.get("analysis", {}).get("missing_concepts", []):
                mid = mc.get("id", mc) if isinstance(mc, dict) else str(mc)
                missing_counts[mid] = missing_counts.get(mid, 0) + 1

            # Misconceptions
            misc = a.misconceptions
            for m in misc.get("misconceptions", []):
                desc = m.get("student_claim", m.get("explanation", "unknown"))[:80]
                misc_freq[desc] = misc_freq.get(desc, 0) + 1
                src = m.get("source_concept", "unknown")
                tgt = m.get("target_concept", "unknown")
                for concept in [src, tgt]:
                    if concept and concept != "unknown":
                        if concept not in misc_by_concept:
                            misc_by_concept[concept] = []
                        misc_by_concept[concept].append(desc)

            if misc.get("by_severity", {}).get("critical", 0) > 0:
                critical_students.append(a.student_id)

            # Depth
            depth_dist[a.depth_category] = depth_dist.get(a.depth_category, 0) + 1
            score_sum += a.overall_score

        n = len(assessments) or 1

        analytics.blooms_distribution = blooms_levels
        analytics.blooms_average = blooms_sum / n
        analytics.solo_distribution = solo_levels
        analytics.solo_average = solo_sum / n

        # Concept coverage average
        coverage_scores = [
            a.comparison.get("scores", {}).get("concept_coverage", 0)
            for a in assessments
        ]
        analytics.concept_coverage_avg = sum(coverage_scores) / n if coverage_scores else 0

        # Sort concepts by frequency
        analytics.most_demonstrated_concepts = sorted(
            concept_counts.items(), key=lambda x: -x[1]
        )[:10]
        analytics.most_missed_concepts = sorted(
            missing_counts.items(), key=lambda x: -x[1]
        )[:10]
        analytics.concept_student_matrix = concept_matrix

        # Misconception analytics
        analytics.total_misconceptions = sum(
            a.misconceptions.get("total_misconceptions", 0) for a in assessments
        )
        analytics.misconception_frequency = dict(
            sorted(misc_freq.items(), key=lambda x: -x[1])[:10]
        )
        analytics.misconception_by_concept = misc_by_concept
        analytics.students_with_critical = critical_students

        analytics.class_average_score = score_sum / n
        analytics.depth_distribution = depth_dist

        return analytics

    def query(
        self,
        nl_query: str,
        assessments: list[StudentAssessment],
        class_analytics: Optional[ClassAnalytics] = None,
    ) -> dict:
        """
        Process a natural language query against assessment data.
        
        Args:
            nl_query: Educator's natural language question
            assessments: List of student assessments
            class_analytics: Pre-computed class analytics (computed if None)
            
        Returns:
            Dict with parsed query, relevant data, and visualization spec
        """
        # Parse the query
        parsed = self.query_parser.parse(nl_query)

        # Compute class analytics if needed
        if class_analytics is None:
            class_analytics = self.analyze_class(assessments)

        # Execute the query
        data = self._execute_query(parsed, assessments, class_analytics)

        return {
            "query": parsed.to_dict(),
            "data": data,
            "visualization": self._build_viz_spec(parsed, data),
        }

    def _compute_overall_score(self, assessment: StudentAssessment) -> float:
        """Compute a composite score from all assessment dimensions."""
        scores = assessment.comparison.get("scores", {})
        concept_coverage = scores.get("concept_coverage", 0)
        rel_accuracy = scores.get("relationship_accuracy", 0)
        integration = scores.get("integration_quality", 0)

        blooms_normalized = (assessment.blooms.get("level", 1) - 1) / 5  # 0-1
        solo_normalized = (assessment.solo.get("level", 1) - 1) / 4  # 0-1
        accuracy = assessment.misconceptions.get("overall_accuracy", 1.0)

        # Weighted composite
        score = (
            concept_coverage * 0.15 +
            rel_accuracy * 0.15 +
            integration * 0.15 +
            blooms_normalized * 0.20 +
            solo_normalized * 0.20 +
            accuracy * 0.15
        )
        return min(1.0, max(0.0, score))

    def _categorize_depth(self, assessment: StudentAssessment) -> str:
        """Categorize overall depth of understanding."""
        blooms = assessment.blooms.get("level", 1)
        solo = assessment.solo.get("level", 1)
        misc = assessment.misconceptions.get("total_misconceptions", 0)
        critical = assessment.misconceptions.get("by_severity", {}).get("critical", 0)

        if blooms >= 5 and solo >= 4 and critical == 0:
            return "expert"
        elif blooms >= 4 and solo >= 3 and critical == 0:
            return "deep"
        elif blooms >= 2 and solo >= 2:
            return "moderate"
        else:
            return "surface"

    def _execute_query(
        self,
        parsed: ParsedQuery,
        assessments: list[StudentAssessment],
        analytics: ClassAnalytics,
    ) -> dict:
        """Execute a parsed query against assessment data."""
        qt = parsed.query_type

        if qt == QueryType.BLOOM_DISTRIBUTION:
            return {
                "distribution": analytics.blooms_distribution,
                "average": analytics.blooms_average,
                "students": [
                    {"id": a.student_id, "level": a.blooms.get("level", 0),
                     "label": a.blooms.get("label", "?")}
                    for a in assessments
                ],
            }

        elif qt == QueryType.SOLO_DISTRIBUTION:
            return {
                "distribution": analytics.solo_distribution,
                "average": analytics.solo_average,
                "students": [
                    {"id": a.student_id, "level": a.solo.get("level", 0),
                     "label": a.solo.get("label", "?")}
                    for a in assessments
                ],
            }

        elif qt == QueryType.MISCONCEPTION_ANALYSIS:
            return {
                "total": analytics.total_misconceptions,
                "frequency": analytics.misconception_frequency,
                "by_concept": analytics.misconception_by_concept,
                "students_with_critical": analytics.students_with_critical,
                "details": [
                    {"student": a.student_id,
                     "misconceptions": a.misconceptions.get("misconceptions", [])}
                    for a in assessments if a.misconceptions.get("total_misconceptions", 0) > 0
                ],
            }

        elif qt == QueryType.CONCEPT_ANALYSIS:
            return {
                "coverage_average": analytics.concept_coverage_avg,
                "most_demonstrated": analytics.most_demonstrated_concepts,
                "most_missed": analytics.most_missed_concepts,
                "per_student": [
                    {"id": a.student_id,
                     "concepts_count": len(a.concept_graph.get("concepts", [])),
                     "coverage": a.comparison.get("scores", {}).get("concept_coverage", 0)}
                    for a in assessments
                ],
            }

        elif qt == QueryType.CONCEPT_HEATMAP:
            return {
                "matrix": analytics.concept_student_matrix,
                "concepts": list(analytics.concept_student_matrix.keys()),
                "students": [a.student_id for a in assessments],
            }

        elif qt == QueryType.STUDENT_COMPARISON:
            # Find specific students if mentioned in filters
            target_students = parsed.filters.get("students", [])
            if not target_students:
                target_students = [a.student_id for a in assessments[:4]]
            return {
                "students": [
                    {
                        "id": a.student_id,
                        "blooms_level": a.blooms.get("level", 0),
                        "blooms_label": a.blooms.get("label", "?"),
                        "solo_level": a.solo.get("level", 0),
                        "solo_label": a.solo.get("label", "?"),
                        "concept_coverage": a.comparison.get("scores", {}).get("concept_coverage", 0),
                        "integration": a.comparison.get("scores", {}).get("integration_quality", 0),
                        "misconceptions": a.misconceptions.get("total_misconceptions", 0),
                        "overall_score": a.overall_score,
                        "depth": a.depth_category,
                    }
                    for a in assessments
                    if a.student_id in target_students or not target_students
                ],
            }

        else:  # CLASS_SUMMARY
            return {
                "num_students": analytics.num_students,
                "blooms_average": analytics.blooms_average,
                "solo_average": analytics.solo_average,
                "concept_coverage_avg": analytics.concept_coverage_avg,
                "total_misconceptions": analytics.total_misconceptions,
                "class_average_score": analytics.class_average_score,
                "depth_distribution": analytics.depth_distribution,
                "students_needing_attention": analytics.students_with_critical,
            }

    def _build_viz_spec(self, parsed: ParsedQuery, data: dict) -> dict:
        """Build a visualization specification for the frontend."""
        return {
            "type": parsed.visualization_type.value,
            "title": parsed.description or f"{parsed.query_type.value} visualization",
            "data_keys": list(data.keys()),
            "config": {
                "query_type": parsed.query_type.value,
                "focus": parsed.focus_entity,
                "filters": parsed.filters,
            },
        }
