"""
Combined Cognitive Depth Classifier.

Classifies both Bloom's Revised Taxonomy level AND SOLO Taxonomy level
in a SINGLE LLM call, cutting two separate API calls to one.

Research rationale: Both Bloom's and SOLO assess cognitive depth from the
same evidence (question, answer, concept graph). Asking the model once for
both is not only cheaper but produces more internally consistent results
because the model reasons about the same evidence simultaneously.
"""

import json
import re
from dataclasses import dataclass

from conceptgrade.llm_client import LLMClient as Groq

# ── Combined system prompt ─────────────────────────────────────────────────

COGNITIVE_DEPTH_SYSTEM = """You are an expert educational researcher specializing in cognitive assessment taxonomies.

Given a student's answer and its knowledge-graph evidence, classify the response on TWO frameworks simultaneously:

BLOOM'S REVISED TAXONOMY (1-6):
1. Remember   — Recall facts, definitions, terms (define, list, name)
2. Understand — Explain, paraphrase, interpret, summarize
3. Apply      — Use knowledge in a new situation, solve, implement
4. Analyze    — Compare, contrast, differentiate, break into parts
5. Evaluate   — Justify, critique, defend, assess trade-offs
6. Create     — Design novel solutions, synthesize, formulate

SOLO TAXONOMY (1-5):
1. Prestructural   — Irrelevant or no understanding
2. Unistructural   — One relevant concept, no connections
3. Multistructural — Several concepts but listed without integration
4. Relational      — Concepts connected into a coherent structure
5. Extended Abstract — Goes beyond the question, generalises or transfers

CLASSIFICATION RULES:
- Bloom's: assign the HIGHEST level clearly demonstrated
- SOLO: focus on STRUCTURAL complexity (how concepts connect), not just count
- Use concept graph evidence (count, integration score, relationships) to inform both
- Be concise — reasoning steps should be 1 sentence each"""


COGNITIVE_DEPTH_USER = """Classify this student response on BOTH Bloom's and SOLO taxonomies.

QUESTION: {question}

STUDENT ANSWER: {student_answer}

CONCEPT GRAPH EVIDENCE:
- Concepts found: {num_concepts} ({concept_list})
- Relationships: {num_relationships} (correct: {correct_rels})
- Integration quality: {integration}
- KG depth signal: {kg_depth}
- Misconceptions: {misconceptions}

Return ONLY valid JSON:
{{
  "blooms_level": <1-6>,
  "blooms_label": "Remember|Understand|Apply|Analyze|Evaluate|Create",
  "blooms_confidence": <0.0-1.0>,
  "blooms_justification": "<one sentence>",
  "blooms_reasoning_steps": ["step 1", "step 2", "step 3"],
  "solo_level": <1-5>,
  "solo_label": "Prestructural|Unistructural|Multistructural|Relational|Extended Abstract",
  "solo_confidence": <0.0-1.0>,
  "solo_justification": "<one sentence>",
  "solo_reasoning_steps": ["step 1", "step 2", "step 3"]
}}"""


# ── Result dataclass ───────────────────────────────────────────────────────

@dataclass
class CognitiveDepthResult:
    """Combined Bloom's + SOLO classification from a single LLM call."""

    # Bloom's
    blooms_level: int
    blooms_label: str
    blooms_confidence: float
    blooms_justification: str
    blooms_reasoning_steps: list

    # SOLO
    solo_level: int
    solo_label: str
    solo_confidence: float
    solo_justification: str
    solo_reasoning_steps: list

    # Source
    from_cache: bool = False

    def to_blooms_dict(self) -> dict:
        from cognitive_depth.blooms_classifier import BloomsLevel  # local import avoids circular
        try:
            level_enum = BloomsLevel(self.blooms_level)
            description = level_enum.description
        except ValueError:
            description = ""
        return {
            "level": self.blooms_level,
            "label": self.blooms_label,
            "description": description,
            "confidence": round(self.blooms_confidence, 3),
            "justification": self.blooms_justification,
            "reasoning_steps": self.blooms_reasoning_steps,
            "evidence": {"cognitive_verbs": [], "surface_indicators": [], "depth_indicators": []},
            "source": "combined_classifier",
            "from_cache": self.from_cache,
        }

    def to_solo_dict(self) -> dict:
        return {
            "level": self.solo_level,
            "label": self.solo_label,
            "confidence": round(self.solo_confidence, 3),
            "justification": self.solo_justification,
            "reasoning_steps": self.solo_reasoning_steps,
            "source": "combined_classifier",
            "from_cache": self.from_cache,
        }


# ── Classifier ─────────────────────────────────────────────────────────────

class CognitiveDepthClassifier:
    """
    Classifies Bloom's and SOLO levels in a single LLM call.

    Replaces the separate BloomsClassifier + SOLOClassifier calls in the
    pipeline, reducing API calls from 2 to 1 per student submission.
    """

    BLOOMS_LABELS = {
        1: "Remember", 2: "Understand", 3: "Apply",
        4: "Analyze",  5: "Evaluate",  6: "Create",
    }
    SOLO_LABELS = {
        1: "Prestructural", 2: "Unistructural", 3: "Multistructural",
        4: "Relational",    5: "Extended Abstract",
    }

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def _call_llm(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.1,
            max_tokens=600,          # 600: sufficient for Bloom's+SOLO combined JSON
        )
        return response.choices[0].message.content

    def _parse_json(self, text: str) -> dict:
        from conceptgrade.llm_client import parse_llm_json
        return parse_llm_json(text)

    def _build_evidence(
        self,
        concept_graph: dict | None,
        comparison_result: dict | None,
    ) -> dict:
        """Extract compact evidence strings for the prompt."""
        num_concepts = 0
        concept_list = "none"
        num_rels = 0
        correct_rels = "N/A"
        integration = "N/A"
        kg_depth = "not assessed"
        misconceptions = "none"

        if concept_graph:
            concepts = concept_graph.get("concepts", [])
            num_concepts = len(concepts)
            concept_list = ", ".join(
                c.get("concept_id", c.get("id", "?")) for c in concepts[:12]
            ) or "none"
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
                    f"{m.get('source','?')}→{m.get('target','?')}"
                    for m in incorrect[:3]
                )

        return dict(
            num_concepts=num_concepts,
            concept_list=concept_list,
            num_relationships=num_rels,
            correct_rels=correct_rels,
            integration=integration,
            kg_depth=kg_depth,
            misconceptions=misconceptions,
        )

    def _fallback(self, num_concepts: int, num_rels: int) -> CognitiveDepthResult:
        """Rule-based fallback when LLM parsing fails."""
        if num_concepts >= 4 and num_rels >= 3:
            b_level, s_level = 4, 4
        elif num_concepts >= 2 and num_rels >= 1:
            b_level, s_level = 2, 3
        elif num_concepts >= 1:
            b_level, s_level = 2, 2
        else:
            b_level, s_level = 1, 1

        return CognitiveDepthResult(
            blooms_level=b_level,
            blooms_label=self.BLOOMS_LABELS[b_level],
            blooms_confidence=0.3,
            blooms_justification="Heuristic fallback (LLM parse failed)",
            blooms_reasoning_steps=["Rule-based: concept count + relationship count"],
            solo_level=s_level,
            solo_label=self.SOLO_LABELS[s_level],
            solo_confidence=0.3,
            solo_justification="Heuristic fallback (LLM parse failed)",
            solo_reasoning_steps=["Rule-based: concept count + relationship count"],
        )

    def classify(
        self,
        question: str,
        student_answer: str,
        concept_graph: dict | None = None,
        comparison_result: dict | None = None,
    ) -> CognitiveDepthResult:
        """
        Classify Bloom's and SOLO levels in one LLM call.

        Args:
            question:          The assessment question.
            student_answer:    Student's free-text response.
            concept_graph:     Output from ConceptExtractor (optional).
            comparison_result: Output from KnowledgeGraphComparator (optional).

        Returns:
            CognitiveDepthResult with both Bloom's and SOLO fields populated.
        """
        ev = self._build_evidence(concept_graph, comparison_result)
        user_prompt = COGNITIVE_DEPTH_USER.format(
            question=question,
            student_answer=student_answer,
            **ev,
        )

        try:
            raw = self._call_llm(COGNITIVE_DEPTH_SYSTEM, user_prompt)
            parsed = self._parse_json(raw)
        except Exception as e:
            err = str(e)
            if "429" in err or "529" in err or "rate_limit" in err.lower() or "overloaded" in err.lower():
                raise  # propagate so key rotator can handle it
            print(f"[CognitiveDepthClassifier] Fallback due to: {e}")
            return self._fallback(ev["num_concepts"], ev["num_relationships"])

        b_level = max(1, min(6, int(parsed.get("blooms_level", 1))))
        s_level = max(1, min(5, int(parsed.get("solo_level", 1))))

        return CognitiveDepthResult(
            blooms_level=b_level,
            blooms_label=parsed.get("blooms_label", self.BLOOMS_LABELS[b_level]),
            blooms_confidence=float(parsed.get("blooms_confidence", 0.5)),
            blooms_justification=parsed.get("blooms_justification", ""),
            blooms_reasoning_steps=parsed.get("blooms_reasoning_steps", []),
            solo_level=s_level,
            solo_label=parsed.get("solo_label", self.SOLO_LABELS[s_level]),
            solo_confidence=float(parsed.get("solo_confidence", 0.5)),
            solo_justification=parsed.get("solo_justification", ""),
            solo_reasoning_steps=parsed.get("solo_reasoning_steps", []),
        )
