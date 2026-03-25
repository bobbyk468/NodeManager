"""
Bloom's Revised Taxonomy Classifier.

Classifies student responses along Bloom's cognitive levels using
Chain-of-Thought (CoT) prompting with concept graph evidence.

Following the methodology of Cohn et al. (2024) for automated
Bloom's classification, enhanced with knowledge graph features
from Paper 1 of our framework.

Levels (low → high):
  1. Remember — Recall facts, definitions, terms
  2. Understand — Explain ideas, paraphrase, summarize
  3. Apply — Use knowledge in new situations
  4. Analyze — Break information into parts, identify patterns
  5. Evaluate — Justify decisions, critique, assess
  6. Create — Generate new ideas, design solutions, synthesize
"""

import json
import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional
from conceptgrade.llm_client import LLMClient as Groq


class BloomsLevel(IntEnum):
    """Bloom's Revised Taxonomy levels."""
    REMEMBER = 1
    UNDERSTAND = 2
    APPLY = 3
    ANALYZE = 4
    EVALUATE = 5
    CREATE = 6

    @property
    def label(self) -> str:
        return self.name.capitalize()

    @property
    def description(self) -> str:
        descriptions = {
            1: "Recall facts, definitions, and basic terminology",
            2: "Explain ideas, paraphrase, interpret, or summarize",
            3: "Use knowledge in new situations, solve problems",
            4: "Break information into parts, identify relationships and patterns",
            5: "Justify decisions, critique, compare approaches, assess trade-offs",
            6: "Generate new ideas, design novel solutions, synthesize across domains"
        }
        return descriptions[self.value]


BLOOMS_COT_SYSTEM = """You are an expert educational assessment researcher specializing in Bloom's Revised Taxonomy classification.

Your task is to classify the cognitive depth of a student's response using Chain-of-Thought reasoning.

BLOOM'S REVISED TAXONOMY LEVELS:
1. REMEMBER — Retrieving relevant knowledge from long-term memory (define, list, recall, identify, name)
2. UNDERSTAND — Constructing meaning from instructional messages (explain, describe, paraphrase, interpret, summarize, classify)
3. APPLY — Carrying out or using a procedure in a given situation (implement, execute, use, solve, demonstrate)
4. ANALYZE — Breaking material into constituent parts and detecting relationships (differentiate, organize, compare, contrast, distinguish, examine)
5. EVALUATE — Making judgments based on criteria and standards (judge, critique, justify, argue, defend, assess trade-offs)
6. CREATE — Putting elements together to form a novel, coherent whole (design, construct, plan, produce, devise, formulate)

CLASSIFICATION GUIDELINES:
- The highest demonstrated level determines the classification
- A student may show evidence of multiple levels; classify at the HIGHEST level clearly demonstrated
- Brief, surface-level responses without explanation → Remember (1)
- Explaining "how" or "why" → Understand (2)
- Applying to a specific problem or scenario → Apply (3)
- Comparing, contrasting, or breaking down → Analyze (4)
- Justifying choices or evaluating trade-offs → Evaluate (5)
- Proposing novel solutions or designs → Create (6)

IMPORTANT: Use the concept graph evidence to assess depth. A student who mentions many interconnected concepts with correct relationships demonstrates deeper understanding than one who lists isolated terms."""


BLOOMS_COT_USER = """Classify this student response using Bloom's Revised Taxonomy.

QUESTION: {question}

STUDENT ANSWER: {student_answer}

CONCEPT GRAPH EVIDENCE:
- Concepts found: {num_concepts} ({concept_list})
- Relationships identified: {num_relationships}
- Correct relationships: {correct_rels}
- Misconceptions: {misconceptions}
- Integration quality: {integration}
- Depth assessment from KG comparison: {kg_depth}

Think step-by-step:
1. What cognitive verbs/actions does the student demonstrate?
2. Does the student just recall facts, or explain, apply, analyze, evaluate, or create?
3. What does the concept graph evidence tell us about depth?
4. What is the HIGHEST Bloom's level clearly demonstrated?

Return ONLY valid JSON:
{{
  "reasoning_steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ...",
    "Step 4: ..."
  ],
  "evidence": {{
    "cognitive_verbs": ["list of cognitive verbs/actions demonstrated"],
    "surface_indicators": ["indicators of lower-level thinking"],
    "depth_indicators": ["indicators of higher-level thinking"]
  }},
  "blooms_level": 1-6,
  "blooms_label": "Remember|Understand|Apply|Analyze|Evaluate|Create",
  "confidence": 0.0-1.0,
  "justification": "Brief explanation of classification"
}}"""


@dataclass
class BloomsClassification:
    """Result of Bloom's taxonomy classification."""
    level: BloomsLevel
    confidence: float
    justification: str
    reasoning_steps: list[str]
    cognitive_verbs: list[str]
    surface_indicators: list[str]
    depth_indicators: list[str]

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "label": self.level.label,
            "description": self.level.description,
            "confidence": round(self.confidence, 3),
            "justification": self.justification,
            "reasoning_steps": self.reasoning_steps,
            "evidence": {
                "cognitive_verbs": self.cognitive_verbs,
                "surface_indicators": self.surface_indicators,
                "depth_indicators": self.depth_indicators,
            }
        }


class BloomsClassifier:
    """
    Classifies student responses along Bloom's Revised Taxonomy
    using Chain-of-Thought prompting with concept graph evidence.
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

    def classify(
        self,
        question: str,
        student_answer: str,
        concept_graph: Optional[dict] = None,
        comparison_result: Optional[dict] = None,
    ) -> BloomsClassification:
        """
        Classify a student response on Bloom's taxonomy.
        
        Args:
            question: The assessment question
            student_answer: Student's free-text response
            concept_graph: Output from ConceptExtractor (optional)
            comparison_result: Output from KnowledgeGraphComparator (optional)
        
        Returns:
            BloomsClassification with level, confidence, and reasoning
        """
        # Extract evidence from concept graph and comparison
        num_concepts = 0
        concept_list = "none extracted"
        num_rels = 0
        correct_rels = "N/A"
        misconceptions = "none"
        integration = "N/A"
        kg_depth = "not assessed"

        if concept_graph:
            concepts = concept_graph.get("concepts", [])
            num_concepts = len(concepts)
            concept_list = ", ".join(
                c.get("concept_id", c.get("id", "?")) for c in concepts[:15]
            )
            rels = concept_graph.get("relationships", [])
            num_rels = len(rels)
            kg_depth = concept_graph.get("overall_depth", "not assessed")

        if comparison_result:
            scores = comparison_result.get("scores", {})
            integration = f"{scores.get('integration_quality', 0):.0%}"
            analysis = comparison_result.get("analysis", {})
            correct_rels = str(len(analysis.get("correct_relationships", [])))
            incorrect = analysis.get("incorrect_relationships", [])
            if incorrect:
                misconceptions = "; ".join(
                    f"{m.get('source', '?')}→{m.get('target', '?')}: {m.get('explanation', 'unknown')}"
                    for m in incorrect[:3]
                )

        user_prompt = BLOOMS_COT_USER.format(
            question=question,
            student_answer=student_answer,
            num_concepts=num_concepts,
            concept_list=concept_list,
            num_relationships=num_rels,
            correct_rels=correct_rels,
            misconceptions=misconceptions,
            integration=integration,
            kg_depth=kg_depth,
        )

        raw = self._call_llm(BLOOMS_COT_SYSTEM, user_prompt)

        try:
            parsed = self._parse_json(raw)
        except Exception:
            # Fallback: heuristic-based classification
            return self._heuristic_classify(student_answer, num_concepts, num_rels)

        level_val = int(parsed.get("blooms_level", 1))
        level_val = max(1, min(6, level_val))

        return BloomsClassification(
            level=BloomsLevel(level_val),
            confidence=float(parsed.get("confidence", 0.5)),
            justification=parsed.get("justification", ""),
            reasoning_steps=parsed.get("reasoning_steps", []),
            cognitive_verbs=parsed.get("evidence", {}).get("cognitive_verbs", []),
            surface_indicators=parsed.get("evidence", {}).get("surface_indicators", []),
            depth_indicators=parsed.get("evidence", {}).get("depth_indicators", []),
        )

    def _heuristic_classify(
        self, answer: str, num_concepts: int, num_rels: int
    ) -> BloomsClassification:
        """Fallback heuristic classification when LLM parsing fails."""
        words = answer.lower().split()
        word_count = len(words)

        # Simple heuristics based on text characteristics
        analyze_words = {"compare", "contrast", "differ", "whereas", "unlike", "however", "advantage", "disadvantage"}
        evaluate_words = {"better", "worse", "prefer", "should", "best", "trade-off", "tradeoff", "optimal"}
        apply_words = {"example", "for instance", "suppose", "implement", "code", "algorithm"}
        
        has_analyze = any(w in words for w in analyze_words)
        has_evaluate = any(w in words for w in evaluate_words)
        has_apply = any(w in answer.lower() for w in apply_words)

        if has_evaluate and num_concepts > 5:
            level = BloomsLevel.EVALUATE
        elif has_analyze and num_rels > 3:
            level = BloomsLevel.ANALYZE
        elif has_apply or num_rels > 2:
            level = BloomsLevel.APPLY
        elif word_count > 30 and num_concepts > 3:
            level = BloomsLevel.UNDERSTAND
        else:
            level = BloomsLevel.REMEMBER

        return BloomsClassification(
            level=level,
            confidence=0.3,
            justification="Heuristic-based fallback classification",
            reasoning_steps=["LLM classification failed; used heuristic fallback"],
            cognitive_verbs=[],
            surface_indicators=[],
            depth_indicators=[],
        )
