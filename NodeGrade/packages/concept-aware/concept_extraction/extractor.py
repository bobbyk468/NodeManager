"""
Concept Extraction Pipeline.

Extracts domain concepts and relationships from student free-text answers
using LLM-based extraction with ontology-guided validation.

This produces a "student concept sub-graph" that can be compared
against the expert domain knowledge graph.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from conceptgrade.llm_client import LLMClient as Groq

try:
    from ..knowledge_graph.ontology import (
        Concept, Relationship, ConceptType, RelationshipType
    )
    from ..knowledge_graph.domain_graph import DomainKnowledgeGraph
except ImportError:
    from knowledge_graph.ontology import (
        Concept, Relationship, ConceptType, RelationshipType
    )
    from knowledge_graph.domain_graph import DomainKnowledgeGraph


CONCEPT_EXTRACTION_SYSTEM = """You are an expert Computer Science educator analyzing student answers about Data Structures and Algorithms.

Your task is to extract ALL domain concepts mentioned or implied in a student's response, and identify the relationships between them.

IMPORTANT RULES:
1. Extract concepts the student actually demonstrates understanding of (not just mentions in passing)
2. Identify relationships the student explicitly or implicitly establishes between concepts
3. Use ONLY concepts from the provided domain ontology when possible
4. If a student uses informal language, map it to the closest formal concept
5. Capture misconceptions as incorrect relationships (wrong_edge flag)

Available concept types: data_structure, algorithm, operation, property, complexity_class, design_pattern, abstract_concept, programming_construct
Available relationship types: is_a, has_part, prerequisite_for, implements, uses, variant_of, has_property, has_complexity, operates_on, produces, contrasts_with"""


CONCEPT_EXTRACTION_USER = """Given the following question and student answer, extract all domain concepts and relationships.

QUESTION: {question}

STUDENT ANSWER: {student_answer}

DOMAIN CONCEPTS (reference ontology):
{ontology_concepts}

Return ONLY valid JSON:
{{
  "concepts_found": [
    {{
      "id": "concept_id_from_ontology",
      "confidence": 0.0-1.0,
      "evidence": "exact quote from student answer",
      "is_correct_usage": true/false
    }}
  ],
  "relationships_found": [
    {{
      "source": "concept_id",
      "target": "concept_id",
      "relation_type": "relationship_type",
      "confidence": 0.0-1.0,
      "evidence": "quote showing this relationship",
      "is_correct": true/false,
      "misconception_note": "explanation if incorrect"
    }}
  ],
  "unmapped_terms": ["terms not in ontology"],
  "overall_depth": "surface|moderate|deep"
}}"""


@dataclass
class ExtractedConcept:
    """A concept found in a student's answer."""
    concept_id: str
    confidence: float
    evidence: str
    is_correct_usage: bool = True

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "is_correct_usage": self.is_correct_usage
        }


@dataclass
class ExtractedRelationship:
    """A relationship extracted from a student's answer."""
    source_id: str
    target_id: str
    relation_type: str
    confidence: float
    evidence: str
    is_correct: bool = True
    misconception_note: str = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "is_correct": self.is_correct,
            "misconception_note": self.misconception_note
        }


@dataclass
class StudentConceptGraph:
    """
    The student's demonstrated understanding as a concept sub-graph.
    This is what gets compared against the expert knowledge graph.
    """
    question: str
    student_answer: str
    concepts: list[ExtractedConcept] = field(default_factory=list)
    relationships: list[ExtractedRelationship] = field(default_factory=list)
    unmapped_terms: list[str] = field(default_factory=list)
    overall_depth: str = "surface"

    @property
    def num_concepts(self) -> int:
        return len(self.concepts)

    @property
    def num_relationships(self) -> int:
        return len(self.relationships)

    @property
    def correct_concepts(self) -> list[ExtractedConcept]:
        return [c for c in self.concepts if c.is_correct_usage]

    @property
    def misconceptions(self) -> list[ExtractedRelationship]:
        return [r for r in self.relationships if not r.is_correct]

    @property
    def concept_ids(self) -> set[str]:
        return {c.concept_id for c in self.concepts}

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "student_answer": self.student_answer,
            "concepts": [c.to_dict() for c in self.concepts],
            "relationships": [r.to_dict() for r in self.relationships],
            "unmapped_terms": self.unmapped_terms,
            "overall_depth": self.overall_depth,
            "stats": {
                "num_concepts": self.num_concepts,
                "num_relationships": self.num_relationships,
                "num_correct_concepts": len(self.correct_concepts),
                "num_misconceptions": len(self.misconceptions),
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StudentConceptGraph":
        return cls(
            question=data.get("question", ""),
            student_answer=data.get("student_answer", ""),
            concepts=[ExtractedConcept(**c) for c in data.get("concepts", [])],
            relationships=[ExtractedRelationship(**r) for r in data.get("relationships", [])],
            unmapped_terms=data.get("unmapped_terms", []),
            overall_depth=data.get("overall_depth", "surface")
        )


class ConceptExtractor:
    """
    Extracts concepts from student answers using LLM + ontology validation.
    
    The pipeline:
    1. LLM extracts raw concepts and relationships from student text
    2. Ontology-guided validation maps extracted concepts to the domain graph
    3. Confidence scoring based on evidence quality
    4. Misconception detection for incorrect relationships
    """

    def __init__(
        self,
        domain_graph: DomainKnowledgeGraph,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001"
    ):
        self.domain_graph = domain_graph
        self.client = Groq(api_key=api_key)
        self.model = model
        self._build_ontology_reference()

    def _build_ontology_reference(self) -> None:
        """Build a compact ontology reference string for the LLM prompt (full KG, used as fallback)."""
        concepts = self.domain_graph.get_all_concepts()
        lines = []
        for c in concepts:
            aliases = ", ".join(c.aliases) if c.aliases else "none"
            lines.append(f"- {c.id} ({c.name}): {c.description} [aliases: {aliases}]")
        self._ontology_reference = "\n".join(lines)

    def _build_question_ontology(self, question: str) -> str:
        """
        Return a filtered ontology reference containing only concepts near the
        question topic — typically 10-20 concepts instead of all 100.

        Strategy: keyword-match the question against concept IDs/names/descriptions,
        then expand 1 hop in the KG graph to pick up prerequisite/related concepts.
        Falls back to the full ontology if no focused match is found.
        """
        q_lower = question.lower()
        seed_ids: list[str] = []

        for c in self.domain_graph.get_all_concepts():
            # Match on id, name, description, or aliases
            text = f"{c.id} {c.name} {c.description} {' '.join(c.aliases or [])}".lower()
            # Score: how many question words appear in the concept text
            q_words = [w for w in q_lower.split() if len(w) > 3]
            if any(w in text for w in q_words):
                seed_ids.append(c.id)

        if not seed_ids:
            return self._ontology_reference  # full fallback

        # Expand 1 hop via the domain KG graph
        try:
            subgraph = self.domain_graph.get_subgraph_for_question(seed_ids, depth=1)
            focused = subgraph.get_all_concepts()
        except Exception:
            focused = [self.domain_graph.get_concept(cid) for cid in seed_ids
                       if self.domain_graph.get_concept(cid)]

        if not focused:
            return self._ontology_reference

        lines = []
        for c in focused:
            if c is None:
                continue
            aliases = ", ".join(c.aliases) if c.aliases else "none"
            lines.append(f"- {c.id} ({c.name}): {c.description} [aliases: {aliases}]")
        return "\n".join(lines)

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
        """Call Groq API with system and user prompts."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _parse_json_response(self, text: str) -> dict:
        """Extract JSON from LLM response."""
        from conceptgrade.llm_client import parse_llm_json
        return parse_llm_json(text)

    def extract(self, question: str, student_answer: str) -> StudentConceptGraph:
        """
        Extract concepts and relationships from a student's answer.
        
        Args:
            question: The assessment question
            student_answer: The student's free-text response
            
        Returns:
            StudentConceptGraph representing the student's demonstrated knowledge
        """
        # Step 1: LLM-based extraction
        # Use a question-focused ontology subset (~10-20 concepts) instead of all 100
        focused_ontology = self._build_question_ontology(question)
        user_prompt = CONCEPT_EXTRACTION_USER.format(
            question=question,
            student_answer=student_answer,
            ontology_concepts=focused_ontology
        )

        raw_response = self._call_llm(
            CONCEPT_EXTRACTION_SYSTEM,
            user_prompt,
            max_tokens=4096  # Expert answers can produce 15+ concepts; 800 truncated verbose responses
        )
        
        try:
            parsed = self._parse_json_response(raw_response)
        except Exception as e:
            print(f"Warning: Failed to parse LLM response: {e}")
            return StudentConceptGraph(
                question=question,
                student_answer=student_answer,
                overall_depth="surface"
            )

        # Step 2: Ontology-guided validation
        student_graph = StudentConceptGraph(
            question=question,
            student_answer=student_answer,
        )

        for c_data in parsed.get("concepts_found", []):
            concept_id = c_data.get("id", "").strip()
            if not concept_id:
                continue
            # Validate against ontology
            if self.domain_graph.get_concept(concept_id):
                student_graph.concepts.append(ExtractedConcept(
                    concept_id=concept_id,
                    confidence=float(c_data.get("confidence", 0.5)),
                    evidence=c_data.get("evidence", ""),
                    is_correct_usage=c_data.get("is_correct_usage", True)
                ))
            else:
                # Try alias lookup
                concept = self.domain_graph.find_concept_by_alias(concept_id)
                if concept:
                    student_graph.concepts.append(ExtractedConcept(
                        concept_id=concept.id,
                        confidence=float(c_data.get("confidence", 0.5)) * 0.9,
                        evidence=c_data.get("evidence", ""),
                        is_correct_usage=c_data.get("is_correct_usage", True)
                    ))
                else:
                    student_graph.unmapped_terms.append(concept_id)

        # Step 3: Validate relationships
        valid_concept_ids = student_graph.concept_ids
        for r_data in parsed.get("relationships_found", []):
            source = r_data.get("source", "").strip()
            target = r_data.get("target", "").strip()
            if source in valid_concept_ids and target in valid_concept_ids:
                student_graph.relationships.append(ExtractedRelationship(
                    source_id=source,
                    target_id=target,
                    relation_type=r_data.get("relation_type", "uses"),
                    confidence=float(r_data.get("confidence", 0.5)),
                    evidence=r_data.get("evidence", ""),
                    is_correct=r_data.get("is_correct", True),
                    misconception_note=r_data.get("misconception_note", "")
                ))

        # Deduplicate: merge LLM's unmapped_terms without re-adding already-stored ones
        existing = set(student_graph.unmapped_terms)
        for term in parsed.get("unmapped_terms", []):
            if term not in existing:
                student_graph.unmapped_terms.append(term)
                existing.add(term)
        student_graph.overall_depth = parsed.get("overall_depth", "surface")

        return student_graph

    def extract_batch(
        self,
        qa_pairs: list[tuple[str, str]],
        max_workers: int = 4,
    ) -> list[StudentConceptGraph]:
        """
        Extract concepts from multiple question-answer pairs in parallel.

        Args:
            qa_pairs:    List of (question, student_answer) tuples.
            max_workers: Max concurrent Groq calls (keep ≤5 to respect rate limits).

        Returns:
            List of StudentConceptGraph objects in the same order as qa_pairs.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results: list[StudentConceptGraph | None] = [None] * len(qa_pairs)

        def _extract(idx: int, question: str, answer: str):
            print(f"  Extracting [{idx+1}/{len(qa_pairs)}]: {question[:50]}...")
            return idx, self.extract(question, answer)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(_extract, i, q, a)
                for i, (q, a) in enumerate(qa_pairs)
            ]
            for future in as_completed(futures):
                idx, graph = future.result()
                results[idx] = graph

        return results
