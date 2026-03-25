"""
SOLO Taxonomy Classifier — First Automated Implementation.

Classifies student responses along the Structure of the Observed
Learning Outcome (SOLO) taxonomy (Biggs & Collis, 1982).

This is a NOVEL CONTRIBUTION — no existing system in the literature
performs automated SOLO classification from free-text student responses.

Our approach uses knowledge graph structural features from Paper 1:
- Concept count maps to SOLO's "capacity" dimension
- Integration quality maps to SOLO's "relating operation" dimension
- Graph connectivity patterns distinguish SOLO levels

Based on Fernandez & Guzon (2025) rubric methodology, automated
via LLM + knowledge graph features.

SOLO Levels:
  1. Prestructural — No relevant understanding; misses the point
  2. Unistructural — One relevant concept addressed
  3. Multistructural — Multiple relevant concepts, but unconnected
  4. Relational — Concepts integrated into a coherent whole
  5. Extended Abstract — Generalizes beyond the given context
"""

import json
import math
import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional
from conceptgrade.llm_client import LLMClient as Groq


class SOLOLevel(IntEnum):
    """SOLO Taxonomy levels."""
    PRESTRUCTURAL = 1
    UNISTRUCTURAL = 2
    MULTISTRUCTURAL = 3
    RELATIONAL = 4
    EXTENDED_ABSTRACT = 5

    @property
    def label(self) -> str:
        labels = {
            1: "Prestructural",
            2: "Unistructural",
            3: "Multistructural",
            4: "Relational",
            5: "Extended Abstract"
        }
        return labels[self.value]

    @property
    def description(self) -> str:
        descriptions = {
            1: "No understanding; misses the point entirely or provides irrelevant information",
            2: "Addresses one relevant aspect; focuses on a single concept correctly",
            3: "Addresses several relevant aspects independently; concepts listed but not connected",
            4: "Integrates multiple aspects into a coherent whole; shows how concepts relate",
            5: "Generalizes to new domains; extends beyond the immediate question; shows abstract thinking"
        }
        return descriptions[self.value]

    @property
    def capacity_label(self) -> str:
        """SOLO's quantitative capacity dimension."""
        return {1: "none", 2: "one", 3: "several", 4: "many (integrated)", 5: "many (generalized)"}[self.value]

    @property
    def relating_operation(self) -> str:
        """SOLO's qualitative relating operation dimension."""
        return {
            1: "none — no relevant concepts",
            2: "identify — single concept in isolation",
            3: "enumerate — list multiple concepts without connecting",
            4: "relate — integrate concepts into coherent structure",
            5: "generalize — extend relationships beyond given context"
        }[self.value]


# Thresholds derived from Fernandez & Guzon (2025) rubric methodology
SOLO_RULES = {
    # (min_concepts, min_integration, min_relationships) → SOLO level
    "prestructural": {"max_concepts": 0, "max_integration": 0.1},
    "unistructural": {"min_concepts": 1, "max_concepts": 1, "max_integration": 0.4},
    "multistructural": {"min_concepts": 2, "max_integration": 0.5},
    "relational": {"min_concepts": 3, "min_integration": 0.5, "min_relationships": 2},
    "extended_abstract": {"min_concepts": 5, "min_integration": 0.7, "min_relationships": 4},
}


SOLO_COT_SYSTEM = """You are an expert educational researcher specializing in the SOLO Taxonomy (Structure of the Observed Learning Outcome) by Biggs & Collis (1982).

Your task is to classify a student's response along the SOLO taxonomy using their concept graph evidence.

SOLO TAXONOMY LEVELS:
1. PRESTRUCTURAL — The student shows no relevant understanding. Response is empty, irrelevant, or completely wrong. No relevant concepts demonstrated.

2. UNISTRUCTURAL — The student addresses ONE relevant aspect of the topic. They correctly identify or define a single concept but go no further. Example: "A linked list stores data in nodes" (correct but limited to one idea).

3. MULTISTRUCTURAL — The student addresses SEVERAL relevant aspects but treats them independently without showing connections. Multiple correct concepts listed/described, but not integrated. Example: "A linked list has nodes and pointers. Arrays use contiguous memory."

4. RELATIONAL — The student INTEGRATES concepts into a coherent whole. Shows how concepts relate to each other, explains cause-and-effect, compares and contrasts. The response forms a structured, connected argument. Example: "A linked list uses pointers to connect nodes, making insertion O(1) at the head, unlike arrays which require O(n) shifting because of contiguous storage."

5. EXTENDED ABSTRACT — The student GENERALIZES beyond the immediate topic. Applies the concepts to novel situations, proposes improvements, connects to broader principles, or demonstrates transfer. Example: "While linked lists excel at dynamic insertion, the cache-unfriendly access pattern makes them slower on modern hardware despite theoretically better complexity — this is why libraries like Java's ArrayList use dynamic arrays by default."

KEY DISTINCTION between levels:
- Prestructural → Unistructural: FROM no understanding TO one correct concept
- Unistructural → Multistructural: FROM one concept TO multiple concepts (but listed, not connected)
- Multistructural → Relational: FROM listing concepts TO explaining how they RELATE (this is the critical transition)
- Relational → Extended Abstract: FROM relating concepts TO generalizing/extending beyond the question

Use the concept graph evidence to make your classification. The number of concepts indicates CAPACITY, the integration quality indicates RELATING OPERATION."""


SOLO_COT_USER = """Classify this student response using the SOLO Taxonomy.

QUESTION: {question}

STUDENT ANSWER: {student_answer}

KNOWLEDGE GRAPH EVIDENCE:
- Concepts found: {num_concepts} ({concept_list})
- Relationships demonstrated: {num_relationships}
- Integration quality score: {integration_score}
- Isolated concepts (mentioned but unconnected): {isolated_concepts}
- Concept coverage of expected: {coverage_score}
- Depth from KG comparison: {kg_depth}

Think step-by-step:
1. CAPACITY: How many relevant concepts does the student demonstrate?
2. RELATING: Does the student just list concepts, or show how they connect?
3. INTEGRATION: Is there a coherent structure, or isolated fragments?
4. EXTENSION: Does the student go beyond what was asked?

Return ONLY valid JSON:
{{
  "reasoning_steps": [
    "Step 1 (Capacity): ...",
    "Step 2 (Relating): ...",
    "Step 3 (Integration): ...",
    "Step 4 (Extension): ..."
  ],
  "solo_level": 1-5,
  "solo_label": "Prestructural|Unistructural|Multistructural|Relational|Extended Abstract",
  "capacity": "none|one|several|many",
  "relating_operation": "none|identify|enumerate|relate|generalize",
  "confidence": 0.0-1.0,
  "justification": "Brief explanation of classification"
}}"""


@dataclass
class SOLOClassification:
    """Result of SOLO taxonomy classification."""
    level: SOLOLevel
    confidence: float
    justification: str
    reasoning_steps: list[str]
    capacity: str
    relating_operation: str

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "label": self.level.label,
            "description": self.level.description,
            "confidence": round(self.confidence, 3),
            "justification": self.justification,
            "reasoning_steps": self.reasoning_steps,
            "capacity": self.capacity,
            "relating_operation": self.relating_operation,
        }


class SOLOClassifier:
    """
    First automated SOLO taxonomy classifier for free-text student responses.
    
    Uses a hybrid approach:
    1. Rule-based classification from knowledge graph structural features
    2. LLM-based Chain-of-Thought for nuanced classification
    3. Ensemble: combine both signals for final classification
    """

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def _call_llm(self, system: str, user: str, max_tokens: int = 512) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _parse_json(self, text: str) -> dict:
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return json.loads(text[start:end + 1])
        raise ValueError(f"Could not parse JSON: {text[:200]}")

    def classify_rule_based(
        self,
        num_concepts: int,
        num_relationships: int,
        integration_score: float,
        num_isolated: int,
    ) -> SOLOLevel:
        """
        Rule-based SOLO classification from knowledge graph features.
        
        Maps directly from SOLO's two dimensions:
        - Capacity (quantitative) → concept count
        - Relating operation (qualitative) → integration quality
        """
        if num_concepts == 0:
            return SOLOLevel.PRESTRUCTURAL
        
        if num_concepts == 1:
            return SOLOLevel.UNISTRUCTURAL
        
        # Multiple concepts — check integration
        if integration_score >= 0.7 and num_relationships >= 4 and num_concepts >= 5:
            return SOLOLevel.EXTENDED_ABSTRACT
        
        if integration_score >= 0.5 and num_relationships >= 2 and num_concepts >= 3:
            return SOLOLevel.RELATIONAL
        
        if num_concepts >= 2:
            # Check if mostly isolated (multi but not relational)
            if num_isolated > num_concepts * 0.5 or integration_score < 0.4:
                return SOLOLevel.MULTISTRUCTURAL
            # Borderline — lean relational if decent integration
            if integration_score >= 0.4 and num_relationships >= 2:
                return SOLOLevel.RELATIONAL
            return SOLOLevel.MULTISTRUCTURAL
        
        return SOLOLevel.UNISTRUCTURAL

    def classify(
        self,
        question: str,
        student_answer: str,
        concept_graph: Optional[dict] = None,
        comparison_result: Optional[dict] = None,
    ) -> SOLOClassification:
        """
        Classify a student response on the SOLO taxonomy.
        
        Uses ensemble of rule-based (KG features) + LLM (CoT reasoning).
        """
        # Extract features from concept graph and comparison
        num_concepts = 0
        concept_list = "none"
        num_rels = 0
        integration_score = 0.0
        coverage_score = 0.0
        kg_depth = "not assessed"
        isolated = 0

        if concept_graph:
            concepts = concept_graph.get("concepts", [])
            num_concepts = len(concepts)
            concept_list = ", ".join(
                c.get("concept_id", c.get("id", "?")) for c in concepts[:15]
            )
            rels = concept_graph.get("relationships", [])
            num_rels = len(rels)
            kg_depth = concept_graph.get("overall_depth", "not assessed")

            # Count isolated concepts (in concepts but not in any relationship)
            connected = set()
            for r in rels:
                connected.add(r.get("source_id", r.get("source", "")))
                connected.add(r.get("target_id", r.get("target", "")))
            concept_ids = {c.get("concept_id", c.get("id", "")) for c in concepts}
            isolated = len(concept_ids - connected)

        if comparison_result:
            scores = comparison_result.get("scores", {})
            integration_score = scores.get("integration_quality", 0.0)
            coverage_score = scores.get("concept_coverage", 0.0)

        # 1. Rule-based classification
        rule_level = self.classify_rule_based(
            num_concepts, num_rels, integration_score, isolated
        )

        # 2. LLM-based classification
        # When no concept_graph is provided, avoid polluting the prompt with
        # misleading "0 concepts" evidence — tell the LLM to classify from text.
        if concept_graph is None:
            kg_evidence_str = "Not available — classify from text content only."
            user_prompt = SOLO_COT_USER.format(
                question=question,
                student_answer=student_answer,
                num_concepts="N/A",
                concept_list="N/A",
                num_relationships="N/A",
                integration_score="N/A",
                isolated_concepts="N/A",
                coverage_score="N/A",
                kg_depth="N/A",
            )
        else:
            user_prompt = SOLO_COT_USER.format(
                question=question,
                student_answer=student_answer,
                num_concepts=num_concepts,
                concept_list=concept_list,
                num_relationships=num_rels,
                integration_score=f"{integration_score:.0%}",
                isolated_concepts=isolated,
                coverage_score=f"{coverage_score:.0%}",
                kg_depth=kg_depth,
            )

        try:
            raw = self._call_llm(SOLO_COT_SYSTEM, user_prompt)
            parsed = self._parse_json(raw)

            llm_level_val = int(parsed.get("solo_level", rule_level.value))
            llm_level_val = max(1, min(5, llm_level_val))
            llm_level = SOLOLevel(llm_level_val)
            llm_confidence = float(parsed.get("confidence", 0.5))

            # 3. Ensemble: weighted combination
            # When no concept graph is available, rule-based defaults to
            # PRESTRUCTURAL (no KG evidence) — trust LLM fully in that case.
            if concept_graph is None:
                final_level = llm_level
                confidence = llm_confidence
            # If LLM and rules agree → high confidence
            elif llm_level == rule_level:
                final_level = llm_level
                confidence = min(llm_confidence + 0.15, 1.0)
            elif abs(llm_level.value - rule_level.value) <= 1:
                final_level = llm_level  # Trust LLM for close calls
                confidence = llm_confidence * 0.9
            else:
                # Large disagreement — average and use structural evidence.
                # Use explicit round-half-up (math.ceil of x - 0.5) instead of
                # Python's banker's rounding to avoid unexpected floor-rounding
                # at midpoints (e.g. 2.5 → 2 under banker's, but should be 3).
                avg = (llm_level.value + rule_level.value) / 2
                final_level = SOLOLevel(math.floor(avg + 0.5))  # round-half-up
                confidence = min(llm_confidence, 0.5)

            return SOLOClassification(
                level=final_level,
                confidence=round(confidence, 3),
                justification=parsed.get("justification", ""),
                reasoning_steps=parsed.get("reasoning_steps", []),
                capacity=parsed.get("capacity", final_level.capacity_label),
                relating_operation=parsed.get(
                    "relating_operation", final_level.relating_operation
                ),
            )

        except Exception as e:
            # Fallback to rule-based only
            return SOLOClassification(
                level=rule_level,
                confidence=0.4,
                justification=f"Rule-based classification (LLM failed: {e})",
                reasoning_steps=[
                    f"Concept count: {num_concepts}",
                    f"Relationship count: {num_rels}",
                    f"Integration score: {integration_score:.2f}",
                    f"Isolated concepts: {isolated}",
                ],
                capacity=rule_level.capacity_label,
                relating_operation=rule_level.relating_operation,
            )
