"""
Natural Language Query Parser for Educational Analytics (V-NLI).

Interprets educator natural language queries into structured data
operations over assessment results. This is the V-NLI (Visual Natural
Language Interface) component of the ConceptGrade framework.

Example queries:
  - "Show which concepts are most misunderstood in this class"
  - "Compare Student A and Student B on Bloom's levels"
  - "What misconceptions are most common for linked lists?"
  - "Show the class distribution of SOLO taxonomy levels"
  - "Which students are at Remember level on Bloom's?"

Query types supported:
  1. concept_analysis — Concept coverage, gaps, strengths
  2. bloom_distribution — Class-wide Bloom's level distribution
  3. solo_distribution — Class-wide SOLO level distribution
  4. misconception_analysis — Misconception patterns and frequency
  5. student_comparison — Compare specific students
  6. concept_heatmap — Concept × student matrix
  7. learning_trajectory — Progress over time (if longitudinal data)
  8. class_summary — Overall class performance summary
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from groq import Groq


class QueryType(str, Enum):
    """Types of educational analytics queries."""
    CONCEPT_ANALYSIS = "concept_analysis"
    BLOOM_DISTRIBUTION = "bloom_distribution"
    SOLO_DISTRIBUTION = "solo_distribution"
    MISCONCEPTION_ANALYSIS = "misconception_analysis"
    STUDENT_COMPARISON = "student_comparison"
    CONCEPT_HEATMAP = "concept_heatmap"
    CLASS_SUMMARY = "class_summary"
    LEARNING_TRAJECTORY = "learning_trajectory"


class VisualizationType(str, Enum):
    """Supported visualization types."""
    BAR_CHART = "bar_chart"
    HEATMAP = "heatmap"
    CONCEPT_MAP = "concept_map"
    RADAR_CHART = "radar_chart"
    SANKEY = "sankey"
    TABLE = "table"
    DISTRIBUTION = "distribution"
    COMPARISON = "comparison"


@dataclass
class ParsedQuery:
    """Result of parsing a natural language educator query."""
    original_query: str
    query_type: QueryType
    visualization_type: VisualizationType
    focus_entity: str  # "class", specific student, specific concept, etc.
    filters: dict = field(default_factory=dict)
    parameters: dict = field(default_factory=dict)
    description: str = ""  # Human-readable interpretation
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "original_query": self.original_query,
            "query_type": self.query_type.value,
            "visualization_type": self.visualization_type.value,
            "focus_entity": self.focus_entity,
            "filters": self.filters,
            "parameters": self.parameters,
            "description": self.description,
            "confidence": round(self.confidence, 3),
        }


NL_QUERY_SYSTEM = """You are a query parser for an educational analytics system called ConceptGrade.
Parse educator natural language queries into structured operations.

AVAILABLE QUERY TYPES:
1. concept_analysis — Analysis of which concepts students understand or struggle with
2. bloom_distribution — Distribution of Bloom's taxonomy levels across students
3. solo_distribution — Distribution of SOLO taxonomy levels across students
4. misconception_analysis — Analysis of misconceptions (frequency, type, severity)
5. student_comparison — Compare two or more specific students
6. concept_heatmap — Matrix of concepts × students showing mastery
7. class_summary — Overall class performance summary
8. learning_trajectory — Progress over time

AVAILABLE VISUALIZATION TYPES:
- bar_chart: For distributions, counts, comparisons
- heatmap: For concept × student matrices, misconception frequency
- concept_map: For showing concept relationships and gaps
- radar_chart: For multi-dimensional student comparison
- sankey: For flow diagrams (concept → misconception → remediation)
- table: For detailed tabular data
- distribution: For histogram/pie charts of levels
- comparison: For side-by-side student comparison

Parse the query and return ONLY valid JSON:
{
  "query_type": "one of the query types above",
  "visualization_type": "best visualization for this query",
  "focus_entity": "class | student_name | concept_name | topic_name",
  "filters": {"key": "value pairs for filtering, e.g. bloom_level, topic, severity"},
  "parameters": {"additional parameters like top_n, sort_by"},
  "description": "Human-readable interpretation of what the user wants",
  "confidence": 0.0-1.0
}"""


NL_QUERY_USER = """Parse this educator query:
"{query}"

Context: The system has assessment data for students answering CS Data Structures questions.
Available data per student: concept graph, comparison scores, Bloom's level, SOLO level, misconceptions."""


class NLQueryParser:
    """
    Parses educator natural language queries into structured
    data operations for the ConceptGrade analytics system.
    """

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def _call_llm(self, system: str, user: str, max_tokens: int = 1000) -> str:
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

    def parse(self, query: str) -> ParsedQuery:
        """Parse a natural language query into a structured operation."""
        user_prompt = NL_QUERY_USER.format(query=query)

        try:
            raw = self._call_llm(NL_QUERY_SYSTEM, user_prompt)
            parsed = self._parse_json(raw)

            # Validate query type
            try:
                query_type = QueryType(parsed.get("query_type", "class_summary"))
            except ValueError:
                query_type = self._infer_query_type(query)

            # Validate visualization type
            try:
                viz_type = VisualizationType(parsed.get("visualization_type", "bar_chart"))
            except ValueError:
                viz_type = self._default_viz_for_query(query_type)

            return ParsedQuery(
                original_query=query,
                query_type=query_type,
                visualization_type=viz_type,
                focus_entity=parsed.get("focus_entity", "class"),
                filters=parsed.get("filters", {}),
                parameters=parsed.get("parameters", {}),
                description=parsed.get("description", ""),
                confidence=float(parsed.get("confidence", 0.7)),
            )

        except Exception:
            # Fallback: keyword-based parsing
            return self._keyword_parse(query)

    def _infer_query_type(self, query: str) -> QueryType:
        """Infer query type from keywords."""
        q = query.lower()
        if any(w in q for w in ["misconception", "misunderst", "wrong", "incorrect", "error"]):
            return QueryType.MISCONCEPTION_ANALYSIS
        if any(w in q for w in ["bloom", "cognitive", "depth", "remember", "understand", "analyze", "evaluate", "create"]):
            return QueryType.BLOOM_DISTRIBUTION
        if any(w in q for w in ["solo", "prestructural", "unistructural", "multistructural", "relational", "extended"]):
            return QueryType.SOLO_DISTRIBUTION
        if any(w in q for w in ["compare", "versus", "vs", "difference between"]):
            return QueryType.STUDENT_COMPARISON
        if any(w in q for w in ["concept", "topic", "knowledge", "gap"]):
            return QueryType.CONCEPT_ANALYSIS
        if any(w in q for w in ["heatmap", "matrix", "grid"]):
            return QueryType.CONCEPT_HEATMAP
        if any(w in q for w in ["summary", "overall", "overview", "class"]):
            return QueryType.CLASS_SUMMARY
        return QueryType.CLASS_SUMMARY

    def _default_viz_for_query(self, query_type: QueryType) -> VisualizationType:
        """Return default visualization type for a query type."""
        mapping = {
            QueryType.CONCEPT_ANALYSIS: VisualizationType.BAR_CHART,
            QueryType.BLOOM_DISTRIBUTION: VisualizationType.DISTRIBUTION,
            QueryType.SOLO_DISTRIBUTION: VisualizationType.DISTRIBUTION,
            QueryType.MISCONCEPTION_ANALYSIS: VisualizationType.HEATMAP,
            QueryType.STUDENT_COMPARISON: VisualizationType.RADAR_CHART,
            QueryType.CONCEPT_HEATMAP: VisualizationType.HEATMAP,
            QueryType.CLASS_SUMMARY: VisualizationType.TABLE,
            QueryType.LEARNING_TRAJECTORY: VisualizationType.BAR_CHART,
        }
        return mapping.get(query_type, VisualizationType.BAR_CHART)

    def _keyword_parse(self, query: str) -> ParsedQuery:
        """Fallback keyword-based parser."""
        query_type = self._infer_query_type(query)
        viz_type = self._default_viz_for_query(query_type)

        return ParsedQuery(
            original_query=query,
            query_type=query_type,
            visualization_type=viz_type,
            focus_entity="class",
            filters={},
            parameters={},
            description=f"Keyword-parsed: {query_type.value} query",
            confidence=0.4,
        )
