"""
Misconception Detection Module.

Identifies specific incorrect mental models in student responses by
comparing student concept graphs against expert knowledge graphs and
matching against a curated CS misconception taxonomy.

Classification types:
  - Systematic misconception: Consistent pattern across related questions
  - Isolated error: One-off mistake, not a deep misunderstanding
  - Knowledge gap: Missing understanding rather than wrong understanding

Severity levels:
  - Critical: Fundamental misunderstanding that blocks further learning
  - Moderate: Incorrect relationship that could cause problems
  - Minor: Imprecise language or slight inaccuracy
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from groq import Groq


class MisconceptionType(str, Enum):
    """Classification of misconception nature."""
    SYSTEMATIC = "systematic"     # Persistent, pattern-based misunderstanding
    ISOLATED = "isolated"         # One-off error
    KNOWLEDGE_GAP = "knowledge_gap"  # Missing understanding, not wrong
    CONFLATION = "conflation"     # Confusing two related concepts
    OVERGENERALIZATION = "overgeneralization"  # Applying a rule too broadly
    UNDERGENERALIZATION = "undergeneralization"  # Failing to see a general pattern


class Severity(str, Enum):
    """Severity of the misconception."""
    CRITICAL = "critical"     # Blocks further learning
    MODERATE = "moderate"     # Could cause problems in related topics
    MINOR = "minor"           # Imprecise but not fundamentally wrong


@dataclass
class DetectedMisconception:
    """A single detected misconception."""
    misconception_id: str
    taxonomy_category: str
    misconception_type: MisconceptionType
    severity: Severity
    source_concept: str
    target_concept: str
    student_claim: str       # What the student expressed
    correct_understanding: str  # What they should know
    explanation: str         # Natural language explanation for the student
    remediation_hint: str    # Suggested learning action
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "misconception_id": self.misconception_id,
            "taxonomy_category": self.taxonomy_category,
            "type": self.misconception_type.value,
            "severity": self.severity.value,
            "source_concept": self.source_concept,
            "target_concept": self.target_concept,
            "student_claim": self.student_claim,
            "correct_understanding": self.correct_understanding,
            "explanation": self.explanation,
            "remediation_hint": self.remediation_hint,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class MisconceptionReport:
    """Complete misconception analysis report."""
    total_misconceptions: int = 0
    critical_count: int = 0
    moderate_count: int = 0
    minor_count: int = 0
    misconceptions: list[DetectedMisconception] = field(default_factory=list)
    summary: str = ""
    overall_accuracy: float = 1.0  # 1.0 = no misconceptions

    def to_dict(self) -> dict:
        return {
            "total_misconceptions": self.total_misconceptions,
            "by_severity": {
                "critical": self.critical_count,
                "moderate": self.moderate_count,
                "minor": self.minor_count,
            },
            "misconceptions": [m.to_dict() for m in self.misconceptions],
            "summary": self.summary,
            "overall_accuracy": round(self.overall_accuracy, 3),
        }


# ================================================================
# CS Data Structures Misconception Taxonomy
# Curated from literature + common student errors
# ================================================================
CS_MISCONCEPTION_TAXONOMY = {
    "DS-LINK-01": {
        "category": "Linked Lists",
        "description": "Confusing array indices with pointer-based access",
        "concepts": ["linked_list", "array", "pointer", "index"],
        "common_claim": "You can access linked list elements by index in O(1)",
        "correct": "Linked list access requires O(n) traversal; only arrays support O(1) index access",
        "severity": "critical",
    },
    "DS-LINK-02": {
        "category": "Linked Lists",
        "description": "Believing linked lists use contiguous memory",
        "concepts": ["linked_list", "array", "static_memory", "dynamic_memory"],
        "common_claim": "Linked list nodes are stored next to each other in memory",
        "correct": "Linked list nodes are dynamically allocated and can be anywhere in memory; pointers connect them",
        "severity": "critical",
    },
    "DS-LINK-03": {
        "category": "Linked Lists",
        "description": "Thinking insertion is always O(1) in linked lists",
        "concepts": ["linked_list", "insertion", "o_1", "o_n"],
        "common_claim": "Insertion in a linked list is always O(1)",
        "correct": "Insertion at HEAD is O(1), but insertion at a specific position requires O(n) traversal first",
        "severity": "moderate",
    },
    "DS-STACK-01": {
        "category": "Stacks & Queues",
        "description": "Confusing LIFO (stack) with FIFO (queue)",
        "concepts": ["stack", "queue", "lifo", "fifo"],
        "common_claim": "A stack follows First In First Out order",
        "correct": "A stack follows LIFO (Last In First Out); a queue follows FIFO (First In First Out)",
        "severity": "critical",
    },
    "DS-STACK-02": {
        "category": "Stacks & Queues",
        "description": "Thinking stacks can only be implemented with arrays",
        "concepts": ["stack", "array", "linked_list"],
        "common_claim": "Stacks must use arrays as the underlying storage",
        "correct": "Stacks can be implemented with either arrays or linked lists",
        "severity": "minor",
    },
    "DS-TREE-01": {
        "category": "Trees",
        "description": "Assuming all binary trees are binary search trees",
        "concepts": ["binary_tree", "binary_search_tree"],
        "common_claim": "Any binary tree has the ordered property (left < root < right)",
        "correct": "Only BSTs maintain the ordering property; a general binary tree has no ordering constraint",
        "severity": "critical",
    },
    "DS-TREE-02": {
        "category": "Trees",
        "description": "Confusing tree height with number of nodes",
        "concepts": ["tree", "tree_height", "node"],
        "common_claim": "A tree with n nodes has height n",
        "correct": "Tree height is the longest root-to-leaf path; a balanced tree with n nodes has height O(log n)",
        "severity": "moderate",
    },
    "DS-TREE-03": {
        "category": "Trees",
        "description": "Thinking BST operations are always O(log n)",
        "concepts": ["binary_search_tree", "o_log_n", "balanced_tree"],
        "common_claim": "BST search/insert is always O(log n)",
        "correct": "BST operations are O(log n) only when balanced; worst case (degenerate/linear tree) is O(n)",
        "severity": "moderate",
    },
    "DS-HASH-01": {
        "category": "Hash Tables",
        "description": "Assuming hash tables never have worst-case O(n)",
        "concepts": ["hash_table", "collision", "o_1", "o_n"],
        "common_claim": "Hash table operations are always O(1)",
        "correct": "Hash table operations are O(1) AVERAGE case; worst case with many collisions is O(n)",
        "severity": "moderate",
    },
    "DS-HASH-02": {
        "category": "Hash Tables",
        "description": "Confusing hash function with encryption",
        "concepts": ["hash_function", "hash_table"],
        "common_claim": "Hash functions encrypt the data for security",
        "correct": "Hash functions in hash tables map keys to indices; they are not cryptographic and not for security",
        "severity": "minor",
    },
    "DS-SORT-01": {
        "category": "Sorting",
        "description": "Believing quicksort is always faster than merge sort",
        "concepts": ["quick_sort", "merge_sort", "o_n_log_n", "o_n2"],
        "common_claim": "Quick sort is always the fastest sorting algorithm",
        "correct": "Quick sort average is O(n log n) but worst case is O(n²); merge sort guarantees O(n log n)",
        "severity": "moderate",
    },
    "DS-SORT-02": {
        "category": "Sorting",
        "description": "Thinking all O(n log n) sorts are equally fast in practice",
        "concepts": ["merge_sort", "quick_sort", "heap_sort"],
        "common_claim": "Merge sort and quick sort have the same performance",
        "correct": "Despite same asymptotic complexity, quick sort is often faster due to better cache locality and lower constant factors",
        "severity": "minor",
    },
    "DS-GRAPH-01": {
        "category": "Graphs",
        "description": "Assuming BFS always finds the shortest path",
        "concepts": ["bfs", "shortest_path", "weighted_graph", "dijkstra"],
        "common_claim": "BFS finds the shortest path in any graph",
        "correct": "BFS finds the shortest path in UNWEIGHTED graphs only; for weighted graphs, use Dijkstra's algorithm",
        "severity": "moderate",
    },
    "DS-GRAPH-02": {
        "category": "Graphs",
        "description": "Confusing DFS with BFS behavior",
        "concepts": ["bfs", "dfs", "queue", "stack"],
        "common_claim": "DFS uses a queue / BFS uses a stack",
        "correct": "BFS uses a queue (level-by-level); DFS uses a stack (depth-first via recursion or explicit stack)",
        "severity": "critical",
    },
    "DS-COMP-01": {
        "category": "Complexity",
        "description": "Confusing best case with average case complexity",
        "concepts": ["time_complexity", "big_o_notation"],
        "common_claim": "Big-O notation describes the best case",
        "correct": "Big-O describes the UPPER BOUND (worst case); best case is described by Big-Ω (Omega)",
        "severity": "moderate",
    },
    "DS-COMP-02": {
        "category": "Complexity",
        "description": "Thinking O(n²) is always slower than O(n log n)",
        "concepts": ["o_n2", "o_n_log_n", "time_complexity"],
        "common_claim": "O(n log n) algorithms are always faster than O(n²)",
        "correct": "For small n, O(n²) algorithms with low constant factors (like insertion sort) can be faster than O(n log n) algorithms",
        "severity": "minor",
    },
}


MISCONCEPTION_ANALYSIS_SYSTEM = """You are an expert CS educator analyzing student misconceptions about Data Structures.

Given a student's incorrect relationships (from knowledge graph comparison) and their answer text, identify specific misconceptions and provide educational feedback.

For each misconception:
1. Identify the nature: systematic (deep misunderstanding), isolated (one-off error), knowledge_gap (missing info), conflation (confusing concepts), overgeneralization, or undergeneralization
2. Assess severity: critical (blocks learning), moderate (causes problems), minor (imprecise)
3. Provide a clear explanation the student can understand
4. Suggest a specific remediation action"""


MISCONCEPTION_ANALYSIS_USER = """Analyze these misconceptions from a student's Data Structures response:

QUESTION: {question}
STUDENT ANSWER: {student_answer}

INCORRECT RELATIONSHIPS DETECTED:
{incorrect_relationships}

KNOWN MISCONCEPTION TAXONOMY MATCHES:
{taxonomy_matches}

Return ONLY valid JSON:
{{
  "misconceptions": [
    {{
      "misconception_id": "unique_id",
      "taxonomy_match": "DS-XXX-NN or 'novel'",
      "type": "systematic|isolated|knowledge_gap|conflation|overgeneralization|undergeneralization",
      "severity": "critical|moderate|minor",
      "source_concept": "concept_id",
      "target_concept": "concept_id",
      "student_claim": "what the student said/implied",
      "correct_understanding": "what is actually correct",
      "explanation": "clear explanation for the student",
      "remediation_hint": "suggested learning action",
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "overall assessment of misconceptions"
}}"""


class MisconceptionDetector:
    """
    Detects and classifies misconceptions in student responses
    using knowledge graph evidence and a curated taxonomy.
    """

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.taxonomy = CS_MISCONCEPTION_TAXONOMY

    def _call_llm(self, system: str, user: str, max_tokens: int = 2048) -> str:
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

    def _find_taxonomy_matches(
        self, incorrect_rels: list[dict], student_concepts: set[str]
    ) -> list[tuple[str, dict]]:
        """Find matches in the misconception taxonomy based on involved concepts."""
        matches = []
        for tax_id, tax in self.taxonomy.items():
            tax_concepts = set(tax.get("concepts", []))
            # Check if student's error involves concepts from this taxonomy entry
            overlap = tax_concepts & student_concepts
            if len(overlap) >= 2:
                matches.append((tax_id, tax))
        return matches

    def detect(
        self,
        question: str,
        student_answer: str,
        concept_graph: Optional[dict] = None,
        comparison_result: Optional[dict] = None,
    ) -> MisconceptionReport:
        """
        Detect misconceptions in a student's response.
        
        Args:
            question: The assessment question
            student_answer: Student's free-text response
            concept_graph: Output from ConceptExtractor
            comparison_result: Output from KnowledgeGraphComparator
        
        Returns:
            MisconceptionReport with detected misconceptions and remediation
        """
        report = MisconceptionReport()

        # Extract incorrect relationships from comparison result
        incorrect_rels = []
        student_concept_ids = set()

        if comparison_result:
            analysis = comparison_result.get("analysis", {})
            incorrect_rels = analysis.get("incorrect_relationships", [])

        if concept_graph:
            student_concept_ids = {
                c.get("concept_id", c.get("id", ""))
                for c in concept_graph.get("concepts", [])
            }
            # Also check relationships flagged as incorrect in extraction
            for rel in concept_graph.get("relationships", []):
                if rel.get("is_correct") == False:
                    incorrect_rels.append({
                        "source": rel.get("source_id", rel.get("source", "")),
                        "target": rel.get("target_id", rel.get("target", "")),
                        "student_relation": rel.get("relation_type", "unknown"),
                        "note": rel.get("misconception_note", ""),
                    })

        if not incorrect_rels:
            report.summary = "No misconceptions detected. All demonstrated relationships appear correct."
            return report

        # Find taxonomy matches
        taxonomy_matches = self._find_taxonomy_matches(incorrect_rels, student_concept_ids)
        taxonomy_str = "\n".join(
            f"- {tid}: {t['description']} (severity: {t['severity']})\n"
            f"  Common claim: \"{t['common_claim']}\"\n"
            f"  Correct: \"{t['correct']}\""
            for tid, t in taxonomy_matches[:5]
        ) if taxonomy_matches else "No direct taxonomy matches found."

        incorrect_str = "\n".join(
            f"- {r.get('source', '?')} → {r.get('target', '?')} "
            f"(student used: '{r.get('student_relation', '?')}'"
            f"{', correct: ' + r.get('correct_relation', '') if r.get('correct_relation') else ''})"
            f"\n  Note: {r.get('note', r.get('explanation', 'N/A'))}"
            for r in incorrect_rels[:10]
        )

        # LLM-based analysis
        user_prompt = MISCONCEPTION_ANALYSIS_USER.format(
            question=question,
            student_answer=student_answer,
            incorrect_relationships=incorrect_str,
            taxonomy_matches=taxonomy_str,
        )

        try:
            raw = self._call_llm(MISCONCEPTION_ANALYSIS_SYSTEM, user_prompt)
            parsed = self._parse_json(raw)

            for m_data in parsed.get("misconceptions", []):
                try:
                    m_type = MisconceptionType(m_data.get("type", "isolated"))
                except ValueError:
                    m_type = MisconceptionType.ISOLATED

                try:
                    severity = Severity(m_data.get("severity", "moderate"))
                except ValueError:
                    severity = Severity.MODERATE

                misconception = DetectedMisconception(
                    misconception_id=m_data.get("misconception_id", f"M-{report.total_misconceptions + 1}"),
                    taxonomy_category=m_data.get("taxonomy_match", "novel"),
                    misconception_type=m_type,
                    severity=severity,
                    source_concept=m_data.get("source_concept", ""),
                    target_concept=m_data.get("target_concept", ""),
                    student_claim=m_data.get("student_claim", ""),
                    correct_understanding=m_data.get("correct_understanding", ""),
                    explanation=m_data.get("explanation", ""),
                    remediation_hint=m_data.get("remediation_hint", ""),
                    confidence=float(m_data.get("confidence", 0.5)),
                )
                report.misconceptions.append(misconception)

            report.summary = parsed.get("summary", "")

        except Exception as e:
            # Fallback: create basic misconception entries from incorrect relationships
            for r in incorrect_rels:
                report.misconceptions.append(DetectedMisconception(
                    misconception_id=f"M-fallback-{len(report.misconceptions) + 1}",
                    taxonomy_category="unclassified",
                    misconception_type=MisconceptionType.ISOLATED,
                    severity=Severity.MODERATE,
                    source_concept=r.get("source", "?"),
                    target_concept=r.get("target", "?"),
                    student_claim=f"Used relationship '{r.get('student_relation', '?')}'",
                    correct_understanding=r.get("correct_relation", "Unknown"),
                    explanation=r.get("note", r.get("explanation", "Incorrect relationship")),
                    remediation_hint="Review the relationship between these concepts",
                    confidence=0.3,
                ))
            report.summary = f"Detected {len(report.misconceptions)} potential misconception(s) (fallback analysis)"

        # Compute stats
        report.total_misconceptions = len(report.misconceptions)
        report.critical_count = sum(1 for m in report.misconceptions if m.severity == Severity.CRITICAL)
        report.moderate_count = sum(1 for m in report.misconceptions if m.severity == Severity.MODERATE)
        report.minor_count = sum(1 for m in report.misconceptions if m.severity == Severity.MINOR)

        # Overall accuracy: penalize based on severity
        if report.total_misconceptions > 0:
            penalty = (
                report.critical_count * 0.3 +
                report.moderate_count * 0.15 +
                report.minor_count * 0.05
            )
            report.overall_accuracy = max(0.0, 1.0 - penalty)

        return report
