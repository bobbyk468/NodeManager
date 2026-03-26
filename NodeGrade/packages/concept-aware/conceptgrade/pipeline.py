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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from knowledge_graph.domain_graph import DomainKnowledgeGraph
from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
from concept_extraction.extractor import ConceptExtractor, StudentConceptGraph
from concept_extraction.self_consistent_extractor import SelfConsistentExtractor
from graph_comparison.comparator import KnowledgeGraphComparator
from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
from cognitive_depth.cognitive_depth_classifier import CognitiveDepthClassifier
from misconception_detection.detector import MisconceptionDetector
from nl_query_engine.parser import NLQueryParser, ParsedQuery, QueryType
from conceptgrade.cache import ResponseCache
from conceptgrade.verifier import LLMVerifier


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

    # Extension 3: LLM Verifier (optional)
    verifier: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
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
        if self.verifier:
            d["verifier"] = self.verifier
        return d


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
        model: str = "claude-haiku-4-5-20251001",
        rate_limit_delay: float = 0.1,
        # ── Research Extensions ───────────────────────────────────────────
        use_self_consistency: bool = False,
        use_confidence_weighting: bool = True,
        use_llm_verifier: bool = False,
        use_sure_verifier: bool = False,
        verifier_weight: float = 0.25,
        sc_n_runs: int = 3,
        sc_min_votes: int = 2,
        sc_inter_run_delay: float = 0.0,
        # ── Hierarchical KG ──────────────────────────────────────────────
        use_hierarchical_kg: bool = False,
    ):
        """
        Initialize the ConceptGrade pipeline.

        Args:
            api_key                : Groq API key
            domain_graph           : Expert knowledge graph (defaults to DS graph)
            model                  : LLM model name
            rate_limit_delay       : Seconds between API calls for rate limiting
            use_self_consistency   : Ext-1 — majority-vote extraction (3 LLM calls)
            use_confidence_weighting: Ext-2 — weight coverage by extraction confidence
            use_llm_verifier       : Ext-3 — LLM judge post-scoring
            verifier_weight        : Blend weight for verifier (0=KG only, 1=LLM only)
            sc_n_runs              : Number of self-consistency runs
            sc_min_votes           : Minimum votes to accept a concept
            use_hierarchical_kg    : Split domain KG into primary/secondary tiers and
                                     score as: min(1.0, p_cov*0.80 + s_cov*0.20)
        """
        self.api_key = api_key
        self.model = model
        self.rate_limit_delay = rate_limit_delay

        # Store extension flags for ablation studies
        self.use_self_consistency    = use_self_consistency
        self.use_confidence_weighting = use_confidence_weighting
        self.use_llm_verifier        = use_llm_verifier
        self.use_sure_verifier       = use_sure_verifier
        self.use_hierarchical_kg     = use_hierarchical_kg

        # Layer 1: Domain Knowledge Graph
        self.domain_graph = domain_graph or build_data_structures_graph()

        # Layer 2: Concept Extraction + Comparison
        # Extension 1: Self-Consistent Extractor (3 LLM calls with majority vote)
        if use_self_consistency:
            self.extractor = SelfConsistentExtractor(
                domain_graph=self.domain_graph,
                api_key=api_key,
                model=model,
                n_runs=sc_n_runs,
                min_votes=sc_min_votes,
                inter_run_delay=sc_inter_run_delay,
            )
        else:
            self.extractor = ConceptExtractor(
                domain_graph=self.domain_graph, api_key=api_key, model=model
            )

        # Extension 2: Confidence-Weighted Comparator
        if use_confidence_weighting:
            self.comparator = ConfidenceWeightedComparator(domain_graph=self.domain_graph)
        else:
            self.comparator = KnowledgeGraphComparator(domain_graph=self.domain_graph)

        # Layer 3-4: Cognitive Depth (combined 1 call) + Misconceptions
        self.cognitive_depth_clf = CognitiveDepthClassifier(api_key=api_key, model=model)
        self.misconception_det = MisconceptionDetector(api_key=api_key, model=model)

        # Extension 3: LLM Verifier
        self.verifier = LLMVerifier(
            api_key=api_key, model=model, verifier_weight=verifier_weight
        ) if use_llm_verifier else None

        # Layer 5: NL Query Parser
        self.query_parser = NLQueryParser(api_key=api_key, model=model)

        # Response cache — keyed by (question, answer) hash
        self.cache = ResponseCache()

    def assess_student(
        self,
        student_id: str,
        question: str,
        answer: str,
        reference_answer: str = "",
    ) -> StudentAssessment:
        """
        Run the full 5-layer assessment pipeline on a single student response.

        Cache strategy (token-efficient for ablation studies):
          - LLM cache  keyed by `sc` flag only — extraction, cognitive depth, and
            misconception outputs are reused across CW/verifier variants.
          - Comparison always re-run with the current comparator (CW or standard).
            This is purely algorithmic (no tokens), so it's cheap.
          - Verifier cache  keyed by `sc + cw` — only runs when enabled.
          Result: C3 reuses C1's LLM cache; C5 reuses C2's, cutting ~60% of tokens.
        """
        result = StudentAssessment(
            student_id=student_id,
            question=question,
            answer=answer,
            timestamp=datetime.now().isoformat(),
        )

        # ── LLM cache (extraction + cognitive depth + misconceptions) ───────
        # Keyed by `sc` only: CW is algorithmic, verifier is a separate step.
        llm_key = self.cache.key(
            f"llm_sc{int(self.use_self_consistency)}", self.model, question, answer
        )
        concept_graph_obj = None

        if llm_key in self.cache:
            cached = self.cache.get(llm_key)
            print(f"  [LLM-Cache HIT] student={student_id}")
            result.concept_graph  = cached["concept_graph"]
            result.blooms         = cached["blooms"]
            result.solo           = cached["solo"]
            result.misconceptions = cached["misconceptions"]
            # Reconstruct graph object so we can re-run comparison
            try:
                concept_graph_obj = StudentConceptGraph.from_dict(result.concept_graph)
            except Exception as e:
                print(f"  [Cache] Warning: Failed to reconstruct concept graph: {e}")
                concept_graph_obj = None

        else:
            # Layer 2: Concept Extraction  (LLM call 1 — or 3 parallel with SC)
            try:
                concept_graph_obj = self.extractor.extract(
                    question=question, student_answer=answer
                )
                result.concept_graph = concept_graph_obj.to_dict()
            except Exception as e:
                err = str(e)
                if "429" in err or "529" in err or "rate_limit" in err.lower() or "overloaded" in err.lower():
                    raise
                result.concept_graph = {"error": err, "concepts": [], "relationships": []}

            # Temporary algorithmic comparison — gives Bloom's/misconception prompts
            # coverage/accuracy signals at zero token cost.
            _tmp_comp: dict = {}
            try:
                if concept_graph_obj:
                    _tmp_comp = KnowledgeGraphComparator(
                        domain_graph=self.domain_graph
                    ).compare(student_graph=concept_graph_obj).to_dict()
            except Exception:
                pass

            # Layer 3+4 and Layer 4: Bloom's+SOLO and Misconception in PARALLEL
            # Both are independent of each other — fire them simultaneously.
            def _run_depth():
                return self.cognitive_depth_clf.classify(
                    question=question,
                    student_answer=answer,
                    concept_graph=result.concept_graph,
                    comparison_result=_tmp_comp,
                )

            def _run_misc():
                return self.misconception_det.detect(
                    question=question,
                    student_answer=answer,
                    concept_graph=result.concept_graph,
                    comparison_result=_tmp_comp,
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                f_depth = pool.submit(_run_depth)
                f_misc  = pool.submit(_run_misc)

                try:
                    depth_result = f_depth.result()
                    result.blooms = depth_result.to_blooms_dict()
                    result.solo   = depth_result.to_solo_dict()
                except Exception as e:
                    err = str(e)
                    if "429" in err or "529" in err or "rate_limit" in err.lower() or "overloaded" in err.lower():
                        raise
                    result.blooms = {"error": err, "level": 1, "label": "Remember",      "confidence": 0}
                    result.solo   = {"error": err, "level": 1, "label": "Prestructural", "confidence": 0}

                try:
                    misc_result = f_misc.result()
                    result.misconceptions = misc_result.to_dict()
                except Exception as e:
                    err = str(e)
                    if "429" in err or "529" in err or "rate_limit" in err.lower() or "overloaded" in err.lower():
                        raise
                    result.misconceptions = {"error": err, "total_misconceptions": 0, "misconceptions": []}

            # Persist LLM outputs to cache
            self.cache.set(llm_key, {
                "concept_graph":  result.concept_graph,
                "blooms":         result.blooms,
                "solo":           result.solo,
                "misconceptions": result.misconceptions,
            })

        # ── KG Comparison — ALWAYS re-run with the current comparator ───────
        # Algorithmic only (no LLM, zero token cost). This is what differentiates
        # C1 (standard) from C3 (confidence-weighted) correctly.
        try:
            if concept_graph_obj:
                if self.use_hierarchical_kg and hasattr(self.comparator, "compare_hierarchical"):
                    comparison_obj = self.comparator.compare_hierarchical(
                        student_graph=concept_graph_obj,
                        question=question,
                    )
                else:
                    comparison_obj = self.comparator.compare(
                        student_graph=concept_graph_obj,
                        question=question,
                    )
                result.comparison = comparison_obj.to_dict()
            else:
                result.comparison = {"scores": {}, "analysis": {}, "diagnostic": {}}
        except Exception as e:
            result.comparison = {"error": str(e), "scores": {}, "analysis": {}, "diagnostic": {}}

        # Composite score (recomputed from fresh comparison every time)
        result.overall_score  = self._compute_overall_score(result)
        result.depth_category = self._categorize_depth(result)

        # ── Extension 3: LLM Verifier  (LLM call 4, cached separately) ─────
        if self.verifier is not None:
            ver_key = self.cache.key(
                f"verifier_sc{int(self.use_self_consistency)}"
                f"_cw{int(self.use_confidence_weighting)}",
                self.model, question, answer,
            )
            if ver_key in self.cache:
                result.verifier = self.cache.get(ver_key)
                result.overall_score = result.verifier.get("final_score", result.overall_score)
            else:
                try:
                    if self.use_sure_verifier:
                        ver = self.verifier.verify_sure(
                            question=question,
                            student_answer=answer,
                            kg_score=result.overall_score,
                            comparison_result=result.comparison,
                            blooms=result.blooms,
                            solo=result.solo,
                            misconceptions=result.misconceptions,
                            reference_answer=reference_answer,
                        )
                    else:
                        ver = self.verifier.verify(
                            question=question,
                            student_answer=answer,
                            kg_score=result.overall_score,
                            comparison_result=result.comparison,
                            blooms=result.blooms,
                            solo=result.solo,
                            misconceptions=result.misconceptions,
                            reference_answer=reference_answer,
                        )
                    result.verifier = ver.to_dict()
                    result.overall_score = ver.final_score
                    self.cache.set(ver_key, result.verifier)
                except Exception as e:
                    err = str(e)
                    if "429" in err or "529" in err or "rate_limit" in err.lower() or "overloaded" in err.lower():
                        raise
                    result.verifier = {"error": err}

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
        # Run student assessments in parallel.
        # max_workers=3 keeps us inside Groq's rate limits while still
        # being ~3x faster than sequential for a typical class of 30.
        results: list[StudentAssessment] = []
        student_items = list(student_answers.items())

        def _assess(sid: str, ans: str) -> StudentAssessment:
            return self.assess_student(sid, question, ans)

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(_assess, sid, ans): sid
                for sid, ans in student_items
            }
            for future in as_completed(futures):
                results.append(future.result())

        # Re-sort to match original insertion order
        order = {sid: i for i, (sid, _) in enumerate(student_items)}
        results.sort(key=lambda a: order.get(a.student_id, 0))
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
        """Compute a composite score from all assessment dimensions.

        Design principles:
        - KG signals (coverage, accuracy, integration) are the PRIMARY driver.
          A student who mentions no relevant concepts scores near 0 — no floor.
        - Cognitive depth (Bloom's + SOLO) is a secondary amplifier.
        - Misconceptions apply a multiplicative penalty, capped at 30 %.

        When use_hierarchical_kg is True, the KG knowledge score is replaced by:
            min(1.0, primary_coverage * 0.80 + secondary_coverage * 0.20)
        This forces students to cover both core and advanced concepts for 5/5.
        """
        scores = assessment.comparison.get("scores", {})
        concept_coverage = scores.get("concept_coverage", 0)
        rel_accuracy     = scores.get("relationship_accuracy", 0)
        integration      = scores.get("integration_quality", 0)

        blooms_normalized = (assessment.blooms.get("level", 1) - 1) / 5  # 0–1
        solo_normalized   = (assessment.solo.get("level", 1)   - 1) / 4  # 0–1

        # Misconception penalty — each misconception proportionally caps the score
        if "error" in assessment.misconceptions:
            misc_penalty = 0.0
        else:
            n_misc   = assessment.misconceptions.get("total_misconceptions", 0)
            critical = assessment.misconceptions.get("by_severity", {}).get("critical", 0)
            misc_penalty = min(0.30, n_misc * 0.06 + critical * 0.10)

        # ── Hierarchical KG scoring ──────────────────────────────────────────
        if self.use_hierarchical_kg:
            p_cov = scores.get("primary_coverage",
                               scores.get("concept_coverage", 0))
            s_cov = scores.get("secondary_coverage", 0)
            # Fall back to standard if hierarchical scores are unavailable
            if p_cov > 0 or s_cov > 0:
                concept_coverage = min(1.0, p_cov * 0.80 + s_cov * 0.20)

        # Knowledge: primary signal, spans true 0–1
        knowledge = (
            concept_coverage * 0.45 +
            rel_accuracy     * 0.35 +
            integration      * 0.20
        )

        # Depth: secondary amplifier
        depth = blooms_normalized * 0.55 + solo_normalized * 0.45

        # Composite: knowledge dominates (60 %), depth secondary (40 %),
        # multiplicatively penalised by misconceptions — no additive floor.
        score = (knowledge * 0.60 + depth * 0.40) * (1.0 - misc_penalty)
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

        elif qt == QueryType.LEARNING_TRAJECTORY:
            # Longitudinal view: sort assessments by timestamp and return score progression
            sorted_assessments = sorted(
                assessments,
                key=lambda a: a.timestamp or "",
            )
            return {
                "note": "Longitudinal data requires multiple assessment sessions per student.",
                "trajectory": [
                    {
                        "student_id": a.student_id,
                        "timestamp": a.timestamp,
                        "overall_score": a.overall_score,
                        "blooms_level": a.blooms.get("level", 0),
                        "solo_level": a.solo.get("level", 0),
                        "depth": a.depth_category,
                    }
                    for a in sorted_assessments
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
