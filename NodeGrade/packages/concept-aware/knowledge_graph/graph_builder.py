"""
LLM-Assisted Knowledge Graph Builder.

Uses Groq API (Llama-3.3-70B) to extract concepts and relationships
from curriculum materials, then validates and builds the domain graph.
"""

import json
import re
from typing import Optional
from groq import Groq

from .ontology import Concept, Relationship, ConceptType, RelationshipType
from .domain_graph import DomainKnowledgeGraph


CONCEPT_EXTRACTION_PROMPT = """You are an expert Computer Science educator specializing in Data Structures and Algorithms.

Given the following topic description, extract ALL relevant concepts and their relationships.

Topic: {topic}

For each concept, provide:
- id: snake_case unique identifier
- name: Human-readable name
- concept_type: One of [data_structure, algorithm, operation, property, complexity_class, design_pattern, abstract_concept, programming_construct]
- description: Brief 1-2 sentence definition
- aliases: Alternative names (list)
- difficulty_level: 1-5 (1=introductory, 5=advanced)

For each relationship, provide:
- source_id: Source concept ID
- target_id: Target concept ID  
- relation_type: One of [is_a, has_part, prerequisite_for, implements, uses, variant_of, has_property, has_complexity, operates_on, produces, contrasts_with]
- weight: 0.0-1.0 importance
- description: Brief explanation

Return ONLY valid JSON in this exact format:
{{
  "concepts": [...],
  "relationships": [...]
}}"""


VALIDATION_PROMPT = """You are validating a Computer Science knowledge graph for educational assessment.

Review the following concepts and relationships for accuracy:

{graph_json}

Check for:
1. Incorrect relationships (e.g., wrong is_a hierarchies)
2. Missing critical relationships
3. Concept type misclassifications
4. Missing important concepts for the topic

Return JSON with corrections:
{{
  "corrections": [
    {{"type": "fix_relationship", "source": "...", "target": "...", "old_type": "...", "new_type": "..."}},
    {{"type": "add_concept", "concept": {{...}}}},
    {{"type": "add_relationship", "relationship": {{...}}}},
    {{"type": "remove_relationship", "source": "...", "target": "...", "relation_type": "..."}}
  ],
  "validation_notes": "..."
}}"""


class KnowledgeGraphBuilder:
    """
    Builds domain knowledge graphs using LLM-assisted extraction
    followed by expert validation.
    """

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def _call_llm(self, prompt: str, max_tokens: int = 4096) -> str:
        """Call the Groq API and return the response text."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Low temperature for factual extraction
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _parse_json_response(self, text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Try to find JSON in code blocks first
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        
        # Try direct JSON parse
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to find the first { ... } block
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
        
        raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}...")

    def extract_concepts_from_topic(self, topic: str) -> dict:
        """Use LLM to extract concepts and relationships from a topic description."""
        prompt = CONCEPT_EXTRACTION_PROMPT.format(topic=topic)
        response = self._call_llm(prompt, max_tokens=4096)
        return self._parse_json_response(response)

    def build_from_topics(self, topics: list[str], domain: str = "data_structures") -> DomainKnowledgeGraph:
        """
        Build a complete knowledge graph from multiple topic descriptions.
        
        Args:
            topics: List of topic descriptions to extract concepts from
            domain: Domain name for the graph
            
        Returns:
            A populated DomainKnowledgeGraph
        """
        graph = DomainKnowledgeGraph(domain=domain, version="1.0-llm-generated")
        all_concepts = {}
        all_relationships = []

        for topic in topics:
            print(f"  Extracting concepts from: {topic[:60]}...")
            try:
                extracted = self.extract_concepts_from_topic(topic)
                
                for c_data in extracted.get("concepts", []):
                    cid = c_data.get("id", "").strip()
                    if cid and cid not in all_concepts:
                        all_concepts[cid] = c_data

                for r_data in extracted.get("relationships", []):
                    all_relationships.append(r_data)
                    
            except Exception as e:
                print(f"  Warning: Failed to extract from topic '{topic[:40]}': {e}")
                continue

        # Add all concepts to graph
        for cid, c_data in all_concepts.items():
            try:
                concept = Concept.from_dict(c_data)
                graph.add_concept(concept)
            except Exception as e:
                print(f"  Warning: Skipping concept '{cid}': {e}")

        # Add relationships (skip if concepts don't exist)
        for r_data in all_relationships:
            try:
                rel = Relationship.from_dict(r_data)
                if rel.source_id in all_concepts and rel.target_id in all_concepts:
                    graph.add_relationship(rel)
            except Exception as e:
                pass  # Silently skip invalid relationships

        return graph

    def validate_graph(self, graph: DomainKnowledgeGraph) -> dict:
        """Use LLM to validate and suggest corrections to the graph."""
        graph_json = json.dumps(graph.to_dict(), indent=2)[:3000]  # Truncate for context window
        prompt = VALIDATION_PROMPT.format(graph_json=graph_json)
        response = self._call_llm(prompt, max_tokens=2048)
        return self._parse_json_response(response)

    def apply_corrections(self, graph: DomainKnowledgeGraph, corrections: dict) -> DomainKnowledgeGraph:
        """Apply LLM-suggested corrections to the graph."""
        for correction in corrections.get("corrections", []):
            try:
                ctype = correction.get("type")
                if ctype == "add_concept":
                    concept = Concept.from_dict(correction["concept"])
                    graph.add_concept(concept)
                elif ctype == "add_relationship":
                    rel = Relationship.from_dict(correction["relationship"])
                    graph.add_relationship(rel)
            except Exception as e:
                print(f"  Warning: Could not apply correction: {e}")
        
        return graph
