# ConceptGrade — Detailed Implementation Documentation

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements & Technology Stack](#2-system-requirements--technology-stack)
3. [Phase 1: Knowledge Graph & Concept Extraction Pipeline](#3-phase-1-knowledge-graph--concept-extraction-pipeline)
4. [Phase 2: Cognitive Depth Classification & Misconception Detection](#4-phase-2-cognitive-depth-classification--misconception-detection)
5. [Phase 3: ConceptGrade Unified Pipeline & V-NLI Interface](#5-phase-3-conceptgrade-unified-pipeline--v-nli-interface)
6. [Phase 4: Evaluation Framework & Benchmarking](#6-phase-4-evaluation-framework--benchmarking)
7. [NodeGrade Platform Integration](#7-nodegrade-platform-integration)
8. [LLM Prompt Engineering Details](#8-llm-prompt-engineering-details)
9. [Data Structures & Class Hierarchy](#9-data-structures--class-hierarchy)
10. [Sample Outputs](#10-sample-outputs)
11. [Design Decisions & Rationale](#11-design-decisions--rationale)
12. [Limitations & Future Work](#12-limitations--future-work)
13. [File Index](#13-file-index)

---

## 1. Introduction

ConceptGrade is a 5-layer concept-understanding assessment framework that extends **NodeGrade** (Fischer et al., 2025), a node-based Automatic Short Answer Grading (ASAG) tool. While traditional ASAG systems compare textual similarity between student responses and reference answers, ConceptGrade analyzes the **depth**, **structure**, and **accuracy** of student conceptual understanding through knowledge graph comparison, cognitive taxonomy classification, and misconception detection.

### Research Motivation

Current ASAG systems (including the original NodeGrade) have a fundamental limitation: a student who memorizes correct phrasing scores identically to one who deeply understands the underlying concepts. ConceptGrade addresses this by providing:

- **Concept-level assessment** — Which specific domain concepts does the student demonstrate understanding of?
- **Cognitive depth measurement** — At what Bloom's Taxonomy level does the student operate?
- **Structural complexity analysis** — How does the student's knowledge structure map to the SOLO Taxonomy?
- **Misconception identification** — What specific incorrect mental models does the student hold?
- **Visual analytics** — How can educators explore these multi-dimensional results naturally?

### Implementation Phases

| Phase | Focus | Modules Built | Commit |
|-------|-------|---------------|--------|
| Phase 1 | Knowledge Graph & Concept Extraction | `ontology.py`, `domain_graph.py`, `ds_knowledge_graph.py`, `graph_builder.py`, `extractor.py`, `comparator.py` | `e08529e`, `8e8e969` |
| Phase 2 | Cognitive Depth & Misconceptions | `blooms_classifier.py`, `solo_classifier.py`, `detector.py` | `b44d0db` |
| Phase 3 | Unified Pipeline & V-NLI | `pipeline.py`, `parser.py`, `renderer.py` | `3768007` |
| Phase 4 | Evaluation & Documentation | `metrics.py`, `baselines.py`, `mohler_loader.py`, `run_evaluation.py` | `70b9821` |

---

## 2. System Requirements & Technology Stack

### Python Dependencies (ConceptGrade Framework)

| Package | Version | Purpose |
|---------|---------|---------|
| `groq` | >=0.4.0 | LLM API client (Groq cloud — Llama 3.3 70B) |
| `networkx` | >=3.0 | Knowledge graph data structure and operations |
| `scikit-learn` | >=1.3 | TF-IDF vectorization, cosine similarity, classification metrics |
| `scipy` | >=1.11 | Pearson and Spearman correlation coefficients |
| `numpy` | >=1.24 | Numerical operations and array manipulation |

### Node.js Dependencies (NodeGrade Platform)

| Package | Purpose |
|---------|---------|
| `@nestjs/core` | Backend REST + WebSocket API |
| `react` + `vite` | Frontend (node-graph editor) |
| `litegraph.js` | Visual node-graph programming interface |
| `sentence-transformers` | Embedding-based similarity (Python worker) |
| `pg` / `typeorm` | PostgreSQL database access |

### LLM Configuration

All LLM-powered modules use the **Groq API** with `llama-3.3-70b-versatile` by default. The architecture is LLM-agnostic — every module accepts `api_key` and `model` parameters. Switching to OpenAI requires only changing these two parameters:

```python
# Groq (default)
classifier = BloomsClassifier(api_key="gsk_...", model="llama-3.3-70b-versatile")

# OpenAI
classifier = BloomsClassifier(api_key="sk-...", model="gpt-4o")
```

Rate limiting is handled per-module with a configurable `rate_limit_delay` parameter (default: 1.5 seconds between API calls). The Groq free tier allows 100,000 tokens per day.

---

## 3. Phase 1: Knowledge Graph & Concept Extraction Pipeline

### 3.1 Domain Ontology (`knowledge_graph/ontology.py`)

The ontology defines the type system for all domain knowledge graphs. It uses Python `dataclass` and `Enum` types for type safety.

**Concept Types (8):**

| Enum Value | Description | Example |
|------------|-------------|---------|
| `data_structure` | A concrete data structure | Array, Linked List, BST |
| `algorithm` | A named algorithm | Quicksort, BFS, Binary Search |
| `operation` | An operation on a data structure | Insert, Delete, Search, Traverse |
| `property` | A structural/behavioral property | Ordered, Balanced, Contiguous |
| `complexity_class` | A Big-O complexity class | O(1), O(log n), O(n), O(n²) |
| `design_pattern` | An algorithmic paradigm | Divide and Conquer, Greedy |
| `abstract_concept` | A theoretical concept | Recursion, ADT, Node, Pointer |
| `programming_construct` | A language-level construct | Pointer, Array Index, Reference |

**Relationship Types (11):**

| Enum Value | Semantics | Example |
|------------|-----------|---------|
| `is_a` | Taxonomy/inheritance | Stack is_a Data Structure |
| `has_part` | Composition | Linked List has_part Node |
| `prerequisite_for` | Dependency ordering | Array prerequisite_for Hash Table |
| `implements` | Realization | Binary Search implements Divide & Conquer |
| `uses` | Usage dependency | BFS uses Queue |
| `variant_of` | Variation | Doubly Linked List variant_of Linked List |
| `has_property` | Attribute | BST has_property Ordered |
| `has_complexity` | Performance | Binary Search has_complexity O(log n) |
| `operates_on` | Target | Traversal operates_on Tree |
| `produces` | Output | Sorting produces Sorted Sequence |
| `contrasts_with` | Comparison | BFS contrasts_with DFS |

**Key Data Structures:**

```python
@dataclass
class Concept:
    id: str                    # Unique identifier (snake_case)
    name: str                  # Human-readable name
    concept_type: ConceptType  # Type classification
    description: str = ""      # Brief definition
    aliases: list[str] = []    # Alternative names (e.g., "BST" for "Binary Search Tree")
    difficulty_level: int = 1  # 1-5 scale (1=introductory, 5=advanced)

@dataclass
class Relationship:
    source_id: str
    target_id: str
    relation_type: RelationshipType
    description: str = ""
    weight: float = 1.0        # Importance weight for scoring
    bidirectional: bool = False
```

### 3.2 Domain Knowledge Graph (`knowledge_graph/domain_graph.py`)

The `DomainKnowledgeGraph` class wraps a NetworkX directed graph with domain-specific operations:

- `add_concept(concept)` — Add a concept node with all metadata
- `add_relationship(relationship)` — Add a typed, directed edge
- `get_concept(concept_id)` — Retrieve concept by ID
- `get_related_concepts(concept_id, relation_type)` — Get neighbors by relationship type
- `get_subgraph_for_question(question_concepts)` — Extract the relevant sub-graph for a specific question, used as the "expected answer" reference
- `to_dict()` / `from_dict()` — Serialization for storage and transmission

Internally, it stores concepts as node attributes and relationships as edge attributes on a `networkx.DiGraph`.

### 3.3 CS Data Structures Knowledge Graph (`knowledge_graph/ds_knowledge_graph.py`)

The `build_data_structures_graph()` function constructs the expert-curated reference graph for Computer Science Data Structures. This is the primary domain knowledge used by all assessment layers.

**Statistics:**
- **101 concepts** across 8 concept types
- **137 relationships** across 11 relationship types
- **Topic coverage:** Arrays, Linked Lists (singly, doubly, circular), Stacks, Queues (including priority queue, deque), Binary Trees, Binary Search Trees, AVL Trees, Heaps, Graphs (directed, undirected, weighted), Hash Tables, Sorting Algorithms (bubble, selection, insertion, merge, quick, heap, radix), Searching (linear, binary, DFS, BFS), Complexity Classes (O(1) through O(n²))

**Knowledge Graph Taxonomy (Partial):**

```
Data Structure (abstract)
├── Array
│   ├── has_property: Contiguous Memory
│   ├── has_complexity: O(1) [access], O(n) [insertion]
│   └── contrasts_with: Linked List
├── Linked List
│   ├── has_part: Node
│   ├── variant_of: Doubly Linked List, Circular Linked List
│   └── has_complexity: O(n) [access], O(1) [head insertion]
├── Stack (is_a: ADT)
│   ├── has_property: LIFO
│   ├── uses: Array OR Linked List
│   └── has_complexity: O(1) [push, pop, peek]
├── Queue (is_a: ADT)
│   ├── has_property: FIFO
│   ├── variant_of: Priority Queue, Deque
│   └── has_complexity: O(1) [enqueue, dequeue]
├── Binary Search Tree
│   ├── is_a: Binary Tree
│   ├── has_property: Ordered (left < root < right)
│   ├── has_complexity: O(log n) [balanced], O(n) [worst case]
│   └── variant_of: AVL Tree, Red-Black Tree
├── Hash Table
│   ├── uses: Hash Function, Array
│   ├── has_complexity: O(1) [average], O(n) [worst case]
│   └── has_property: Collision Handling (Chaining, Open Addressing)
└── Graph
    ├── variant_of: Directed Graph, Undirected Graph, Weighted Graph
    └── operates_on: BFS, DFS, Dijkstra, Topological Sort
```

### 3.4 Concept Extraction (`concept_extraction/extractor.py`)

The `ConceptExtractor` is the bridge between free-text student answers and the knowledge graph domain. It uses LLM-based extraction guided by the domain ontology.

**Architecture:**

1. **Input:** Question text + Student answer text + Domain ontology concept list
2. **LLM Prompt:** A structured system prompt instructs the LLM to extract domain concepts and relationships from the student's answer, mapping informal language to formal ontology terms
3. **JSON Parsing:** The LLM returns structured JSON with concepts found, relationships found, confidence scores, and evidence (direct quotes)
4. **Validation:** Extracted concepts are validated against the domain ontology; unrecognized terms are captured as `unmapped_terms`
5. **Output:** `StudentConceptGraph` containing `ExtractedConcept` and `ExtractedRelationship` objects

**Key Data Structures:**

```python
@dataclass
class ExtractedConcept:
    concept_id: str           # Maps to ontology concept ID
    confidence: float         # 0.0-1.0 confidence score
    evidence: str             # Direct quote from student answer
    is_correct_usage: bool    # Whether the student used it correctly

@dataclass
class ExtractedRelationship:
    source_id: str
    target_id: str
    relation_type: str
    confidence: float
    evidence: str
    is_correct: bool          # Correct relationship?
    misconception_note: str   # Explanation if incorrect

@dataclass
class StudentConceptGraph:
    concepts: list[ExtractedConcept]
    relationships: list[ExtractedRelationship]
    unmapped_terms: list[str]
    overall_depth: str        # "surface", "moderate", "deep"
```

**LLM Prompt Design:** The extraction prompt provides the full list of domain ontology concepts (IDs, names, types) as context, constraining the LLM to map student language to formal concepts. This ontology-guided approach significantly reduces hallucination compared to open-ended extraction.

### 3.5 Knowledge Graph Comparison (`graph_comparison/comparator.py`)

The `KnowledgeGraphComparator` compares a student's extracted concept sub-graph against the expert domain graph to produce multi-dimensional assessment scores.

**Scoring Dimensions (all 0.0 to 1.0):**

| Dimension | Calculation | Meaning |
|-----------|-------------|---------|
| `concept_coverage` | \|student_concepts ∩ expected_concepts\| / \|expected_concepts\| | What fraction of expected concepts did the student demonstrate? |
| `relationship_accuracy` | \|correct_relationships\| / \|total_student_relationships\| | Are the relationships between concepts correct? |
| `integration_quality` | Graph density + cross-topic connections + relationship diversity | How well-connected is the student's knowledge? |

**Gap Analysis:** For each expected concept not found in the student's response, the comparator generates a `ConceptGap` object with:
- Gap type: `missing` (not mentioned), `incomplete` (mentioned but not explained), `superficial` (mentioned in passing)
- Importance score (how critical this concept is for the answer)

**Output Data Structure:**

```python
@dataclass
class ComparisonResult:
    scores: dict        # {concept_coverage, relationship_accuracy, integration_quality}
    analysis: dict      # {demonstrated_concepts, missing_concepts, extra_concepts}
    diagnostic: dict    # {concept_gaps, misconception_reports, strengths}
```

---

## 4. Phase 2: Cognitive Depth Classification & Misconception Detection

### 4.1 Bloom's Revised Taxonomy Classifier (`cognitive_depth/blooms_classifier.py`)

Classifies student responses along the 6 levels of Bloom's Revised Taxonomy (Anderson & Krathwohl, 2001).

**Classification Method: Chain-of-Thought (CoT) Prompting**

Following Cohn et al. (2024), the classifier uses a multi-step reasoning approach:

1. The LLM receives: question, student answer, extracted concept graph, and KG comparison results
2. A detailed system prompt defines each Bloom's level with behavioral indicators and CS-specific examples
3. The LLM reasons through the evidence step-by-step before assigning a level
4. The response includes: level (1-6), label, confidence score, reasoning chain, and supporting evidence

**Bloom's Levels (IntEnum):**

```python
class BloomsLevel(IntEnum):
    REMEMBER = 1     # Recall facts, definitions, terms
    UNDERSTAND = 2   # Explain ideas, paraphrase, summarize
    APPLY = 3        # Use knowledge in new situations
    ANALYZE = 4      # Break information into parts, identify patterns
    EVALUATE = 5     # Justify decisions, critique, assess trade-offs
    CREATE = 6       # Generate new ideas, design solutions, synthesize
```

**Classification Guidelines in the Prompt:**
- Highest demonstrated level determines classification
- Brief surface-level responses without explanation → Remember (1)
- Explaining "how" or "why" → Understand (2)
- Applying to a specific problem or scenario → Apply (3)
- Comparing, contrasting, breaking down into parts → Analyze (4)
- Justifying choices, evaluating trade-offs → Evaluate (5)
- Proposing novel solutions or designs → Create (6)

**Concept Graph Enhancement:** The prompt explicitly instructs the LLM to use concept graph evidence for assessment. A student who mentions many interconnected concepts with correct relationships demonstrates deeper understanding than one who lists isolated terms, even if the text sounds similar.

**Output:**

```python
@dataclass
class BloomsResult:
    level: int              # 1-6
    label: str              # "Remember" through "Create"
    confidence: float       # 0.0-1.0
    reasoning: str          # CoT reasoning chain
    evidence: list[str]     # Supporting quotes from student answer
    indicators: dict        # {level: [evidence]} for each detected level
```

### 4.2 SOLO Taxonomy Classifier (`cognitive_depth/solo_classifier.py`)

**Novel Contribution:** This is the first automated SOLO classification system for free-text student responses. No existing system in the ASAG literature performs automated SOLO classification.

**SOLO Levels (IntEnum):**

```python
class SOLOLevel(IntEnum):
    PRESTRUCTURAL = 1      # No understanding; misses the point
    UNISTRUCTURAL = 2      # Addresses one relevant concept
    MULTISTRUCTURAL = 3    # Multiple concepts, but unconnected
    RELATIONAL = 4         # Concepts integrated into coherent whole
    EXTENDED_ABSTRACT = 5  # Generalizes beyond the immediate context
```

**Graph-Aware Classification (Novel Approach):**

Unlike Bloom's (which focuses on cognitive process), SOLO focuses on the **structural complexity** of understanding. Our key innovation is using the topology of the student's concept sub-graph to inform SOLO level classification:

| SOLO Level | Graph Signal | Capacity | Relating Operation |
|------------|-------------|----------|-------------------|
| Prestructural | 0 relevant concepts | none | none |
| Unistructural | 1 concept, 0 relationships | one | identify |
| Multistructural | Multiple concepts, sparse relationships | several | enumerate |
| Relational | Multiple concepts, dense cross-topic relationships | many (integrated) | relate |
| Extended Abstract | Concepts + novel connections beyond expected graph | many (generalized) | generalize |

**Prompt Design:** The SOLO classifier prompt includes explicit graph metrics:
- Number of unique concepts extracted
- Number of relationships identified
- Relationship diversity (how many different relationship types)
- Cross-topic connections (relationships spanning different concept categories)
- Integration quality score from KG Comparison

### 4.3 Misconception Detection (`misconception_detection/detector.py`)

Identifies specific incorrect mental models in student responses using a curated CS misconception taxonomy.

**Misconception Type Enum:**

```python
class MisconceptionType(str, Enum):
    SYSTEMATIC = "systematic"          # Persistent pattern-based misunderstanding
    ISOLATED = "isolated"              # One-off error
    KNOWLEDGE_GAP = "knowledge_gap"    # Missing understanding, not wrong
    CONFLATION = "conflation"          # Confusing two related concepts
    OVERGENERALIZATION = "overgeneralization"   # Applying a rule too broadly
    UNDERGENERALIZATION = "undergeneralization" # Failing to see a general pattern
```

**Severity Levels:**

```python
class Severity(str, Enum):
    CRITICAL = "critical"   # Blocks further learning
    MODERATE = "moderate"   # Could cause problems in related topics
    MINOR = "minor"         # Imprecise but not fundamentally wrong
```

**CS Misconception Taxonomy (16 entries):**

| ID | Category | Common Student Claim | Correct Understanding | Severity |
|----|----------|---------------------|-----------------------|----------|
| DS-LINK-01 | Linked Lists | "Access linked list elements by index in O(1)" | Linked list access requires O(n) traversal; only arrays support O(1) index access | Critical |
| DS-LINK-02 | Linked Lists | "Linked list nodes are stored contiguously in memory" | Nodes are dynamically allocated anywhere in memory; pointers connect them | Critical |
| DS-LINK-03 | Linked Lists | "Insertion in a linked list is always O(1)" | Only head insertion is O(1); arbitrary position requires O(n) traversal | Moderate |
| DS-STACK-01 | Stacks & Queues | "A stack follows First In First Out order" | A stack follows LIFO (Last In First Out); a queue follows FIFO | Critical |
| DS-STACK-02 | Stacks & Queues | "Stacks must use arrays as underlying storage" | Stacks can be implemented with either arrays or linked lists | Minor |
| DS-TREE-01 | Trees | "Any binary tree has the ordered property" | Only BSTs maintain ordering; general binary trees have no ordering constraint | Critical |
| DS-TREE-02 | Trees | "A tree with n nodes has height n" | Height is the longest root-to-leaf path; balanced tree has height O(log n) | Moderate |
| DS-TREE-03 | Trees | "BST search/insert is always O(log n)" | O(log n) only when balanced; worst case (degenerate tree) is O(n) | Moderate |
| DS-HASH-01 | Hash Tables | "Hash table operations are always O(1)" | O(1) average case; worst case with many collisions is O(n) | Moderate |
| DS-HASH-02 | Hash Tables | "Hash functions encrypt the data" | Hash functions map keys to indices; they don't encrypt data | Minor |
| DS-GRAPH-01 | Graphs | "BFS uses a stack / DFS uses a queue" | BFS uses a queue; DFS uses a stack (or recursion) | Critical |
| DS-GRAPH-02 | Graphs | "BFS finds shortest path in weighted graphs" | BFS finds shortest path in unweighted graphs only; use Dijkstra for weighted | Moderate |
| DS-SORT-01 | Sorting | "Quicksort is always O(n log n)" | Average case is O(n log n) but worst case is O(n²) for bad pivots | Moderate |
| DS-SORT-02 | Sorting | "Stable and unstable sorting produce same results" | Stable sorts preserve relative order of equal elements; unstable may not | Minor |
| DS-COMPLEX-01 | Complexity | "O(log n) is the same as O(n)" | O(log n) is significantly faster than O(n) for large inputs | Critical |
| DS-COMPLEX-02 | Complexity | "Big-O gives the exact number of operations" | Big-O describes asymptotic upper bound growth rate, not exact count | Minor |

**Detection Process:**

1. LLM receives: student answer, concept graph, comparison results, and the full misconception taxonomy
2. For each student claim, the LLM checks against the taxonomy and expert knowledge
3. Detected misconceptions are classified by type, severity, source/target concepts, and confidence
4. A remediation hint is generated for each misconception to guide the student

**Output Data Structure:**

```python
@dataclass
class DetectedMisconception:
    misconception_id: str        # Taxonomy ID (e.g., "DS-LINK-01")
    taxonomy_category: str       # Category (e.g., "Linked Lists")
    misconception_type: MisconceptionType
    severity: Severity
    source_concept: str          # The concept the student was discussing
    target_concept: str          # The concept they confused it with
    student_claim: str           # What the student said
    correct_understanding: str   # What they should know
    explanation: str             # Natural language explanation
    remediation_hint: str        # Suggested learning action
    confidence: float

@dataclass
class MisconceptionReport:
    total_misconceptions: int
    critical_count: int
    moderate_count: int
    minor_count: int
    misconceptions: list[DetectedMisconception]
    summary: str
    overall_accuracy: float     # 1.0 = no misconceptions detected
```

### 4.4 NodeGrade Node Integration (Phase 2)

Two TypeScript nodes were created and registered in NodeGrade's node-graph system:

- **`CognitiveDepthNode.ts`** — Wraps `BloomsClassifier` and `SOLOClassifier`; takes question + answer + concept graph → returns Bloom's level, SOLO level, with reasoning
- **`MisconceptionDetectorNode.ts`** — Wraps `MisconceptionDetector`; takes question + answer + concept graph + comparison → returns misconception report with severity breakdown

Both nodes are registered in `LGraphRegisterCustomNodes.ts` and `index.ts`.

### 4.5 Phase 2 Demo (`run_phase2_demo.py`)

The demo script runs the full Phase 2 pipeline on 4 student responses of varying quality to the question: *"Compare linked lists and arrays. Explain when you would use each, and discuss the trade-offs in terms of time complexity for common operations."*

**Test Students:**
- Student A (Excellent) — Expected: Bloom's 5-6, SOLO 5
- Student B (Good) — Expected: Bloom's 3-4, SOLO 3-4
- Student C (Basic) — Expected: Bloom's 2, SOLO 2-3
- Student D (Misconceptions) — Expected: Bloom's 1-2, SOLO 1-2, multiple misconceptions

Results saved to `data/phase2_demo_results.json`.

---

## 5. Phase 3: ConceptGrade Unified Pipeline & V-NLI Interface

### 5.1 ConceptGrade Pipeline (`conceptgrade/pipeline.py`)

The unified pipeline orchestrates all 5 assessment layers in a single `ConceptGradePipeline` class.

**Constructor:**

```python
class ConceptGradePipeline:
    def __init__(
        self,
        api_key: str,
        domain_graph: Optional[DomainKnowledgeGraph] = None,
        model: str = "llama-3.3-70b-versatile",
        rate_limit_delay: float = 1.5,
    )
```

If no `domain_graph` is provided, it defaults to the CS Data Structures graph (101 concepts, 137 relationships).

**Core Methods:**

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `assess_student(student_id, question, answer)` | Single student | `StudentAssessment` | Full 5-layer assessment |
| `assess_class(question, student_answers)` | Dict of {student_id: answer} | List of `StudentAssessment` | Batch assessment |
| `analyze_class(assessments)` | List of assessments | `ClassAnalytics` | Aggregated class analytics |
| `query(nl_query, assessments, analytics)` | Natural language query | Dict with parsed query, data, viz spec | V-NLI query execution |

**Pipeline Execution Flow (`assess_student`):**

```
1. Layer 2a: ConceptExtractor.extract(question, answer)
     → StudentConceptGraph
     [Rate limit pause: 1.5s]

2. Layer 2b: KnowledgeGraphComparator.compare(student_graph)
     → ComparisonResult {concept_coverage, relationship_accuracy, integration_quality}

3. Layer 3: BloomsClassifier.classify(question, answer, concept_graph, comparison)
     → BloomsResult {level: 1-6, confidence, reasoning}
     [Rate limit pause: 1.5s]

4. Layer 4a: SOLOClassifier.classify(question, answer, concept_graph, comparison)
     → SOLOResult {level: 1-5, confidence, reasoning}
     [Rate limit pause: 1.5s]

5. Layer 4b: MisconceptionDetector.detect(question, answer, concept_graph, comparison)
     → MisconceptionReport {misconceptions, severity_breakdown, accuracy}
     [Rate limit pause: 1.5s]

6. Composite: _compute_overall_score() + _categorize_depth()
     → overall_score (0.0-1.0), depth_category (surface|moderate|deep|expert)
```

**Composite Scoring Formula:**

```python
overall_score = (
    concept_coverage * 0.15 +         # Knowledge breadth
    relationship_accuracy * 0.15 +    # Relationship correctness
    integration_quality * 0.15 +      # Knowledge connectivity
    blooms_normalized * 0.20 +        # Cognitive depth (Bloom's 1-6 → 0-1)
    solo_normalized * 0.20 +          # Structural complexity (SOLO 1-5 → 0-1)
    misconception_accuracy * 0.15     # Factual accuracy
)
```

**Depth Categorization Rules:**

| Category | Bloom's | SOLO | Misconceptions |
|----------|---------|------|----------------|
| Expert | ≥ 5 (Evaluate) | ≥ 4 (Relational) | No critical |
| Deep | ≥ 4 (Analyze) | ≥ 3 (Multistructural) | No critical |
| Moderate | ≥ 2 (Understand) | ≥ 2 (Unistructural) | Any |
| Surface | Otherwise | Otherwise | Any |

### 5.2 NL Query Parser — V-NLI Engine (`nl_query_engine/parser.py`)

The Visual Natural Language Interface (V-NLI) allows educators to query assessment results using natural language. The `NLQueryParser` classifies educator intent and extracts structured parameters.

**Query Types (8):**

```python
class QueryType(str, Enum):
    CONCEPT_ANALYSIS = "concept_analysis"
    BLOOM_DISTRIBUTION = "bloom_distribution"
    SOLO_DISTRIBUTION = "solo_distribution"
    MISCONCEPTION_ANALYSIS = "misconception_analysis"
    STUDENT_COMPARISON = "student_comparison"
    CONCEPT_HEATMAP = "concept_heatmap"
    CLASS_SUMMARY = "class_summary"
    LEARNING_TRAJECTORY = "learning_trajectory"
```

**Visualization Types (8):**

```python
class VisualizationType(str, Enum):
    BAR_CHART = "bar_chart"
    HEATMAP = "heatmap"
    CONCEPT_MAP = "concept_map"
    RADAR_CHART = "radar_chart"
    SANKEY = "sankey"
    TABLE = "table"
    DISTRIBUTION = "distribution"
    COMPARISON = "comparison"
```

**Parsed Query Output:**

```python
@dataclass
class ParsedQuery:
    original_query: str           # Raw educator query
    query_type: QueryType         # Classified intent
    visualization_type: VisualizationType  # Recommended visualization
    focus_entity: str             # "class", specific student, or concept
    filters: dict                 # {students: [...], concepts: [...], level: ...}
    parameters: dict              # Additional parameters
    description: str              # Human-readable interpretation
    confidence: float             # Classification confidence
```

**Example Query Mappings:**

| Educator Query | Query Type | Visualization |
|----------------|-----------|---------------|
| "What are the Bloom's levels in the class?" | `bloom_distribution` | Bar chart |
| "Show concept coverage across students" | `concept_heatmap` | Heatmap |
| "Compare Alice and Bob" | `student_comparison` | Radar chart |
| "Which misconceptions are most common?" | `misconception_analysis` | Heatmap |
| "Give me an overview of the class" | `class_summary` | Dashboard |

### 5.3 Visualization Renderer (`visualization/renderer.py`)

Generates `VisualizationSpec` objects that can be consumed by frontend rendering libraries.

**7 Visualization Methods:**

| Method | Chart Type | Data Source |
|--------|-----------|-------------|
| `blooms_distribution(assessments)` | Bar chart | Bloom's level counts |
| `solo_distribution(assessments)` | Bar chart | SOLO level counts |
| `misconception_heatmap(assessments)` | Heatmap | Concept × Severity matrix |
| `concept_coverage_radar(assessments)` | Radar chart | Per-student concept coverage |
| `student_comparison_radar(assessments, student_ids)` | Radar chart | Multi-dimensional profiles |
| `concept_student_heatmap(assessments)` | Heatmap | Concept × Student binary matrix |
| `class_dashboard(assessments)` | Dashboard | All aggregated metrics |

Each method returns a `VisualizationSpec` containing the data, configuration, and auto-generated insights (e.g., "3 of 6 students scored below Relational level on SOLO").

### 5.4 Phase 3 Demo (`run_phase3_demo.py`)

Tests the full pipeline with 6 students and 5 natural language queries:

- 6 students (Alice through Frank) with varying answer quality
- 5 V-NLI queries tested
- 7 visualizations generated
- All results saved to `data/phase3_demo_results.json`

---

## 6. Phase 4: Evaluation Framework & Benchmarking

### 6.1 Evaluation Metrics (`evaluation/metrics.py`)

Implements all standard ASAG evaluation metrics:

**Continuous Grading Metrics:**
- **Pearson r** — Linear correlation with human scores (primary metric in Mohler 2011)
- **Spearman ρ** — Rank correlation (non-parametric)
- **RMSE** — Root Mean Squared Error (lower is better)
- **MAE** — Mean Absolute Error

**Ordinal Agreement Metrics:**
- **QWK (Quadratic Weighted Kappa)** — Primary ASAG metric; measures agreement while penalizing larger disagreements more than smaller ones
- **Cohen's κ** — Inter-rater reliability (unweighted)
- **Accuracy** — Exact match rate

**Classification Metrics (for Bloom's/SOLO):**
- **F1 (macro/weighted)** — Harmonic mean of precision and recall
- **Precision (macro)** — Correct positive predictions
- **Recall (macro)** — Coverage of actual positives
- **Confusion Matrix** — Full N×N class confusion

**Concept-Level Metrics:**
- **Concept Extraction F1** — Set-level F1 between true and predicted concept sets

**Key Functions:**

```python
evaluate_grading(y_true, y_pred, task_name, num_classes=6, scale_max=5.0) → EvaluationResult
evaluate_classification(y_true, y_pred, task_name, labels=None) → EvaluationResult
evaluate_concept_extraction(true_concepts, pred_concepts) → (precision, recall, f1)
format_comparison_table(results: list[EvaluationResult]) → str
```

### 6.2 Baseline Comparators (`evaluation/baselines.py`)

Two baselines for fair comparison:

**Cosine Similarity Baseline (`CosineSimilarityBaseline`):**
- Replicates Mohler & Mihalcea (2009) approach
- TF-IDF vectorization with (1,2)-gram features
- Cosine similarity between reference and student answer
- Score scaled to 0-5 range
- Expected Pearson r ≈ 0.518 (matches literature)

**LLM Zero-Shot Baseline (`LLMZeroShotBaseline`):**
- Represents the simplest LLM-based ASAG approach
- Sends question + reference + student answer to LLM
- LLM directly assigns a 0-5 grade with brief reasoning
- No concept extraction, no knowledge graph, no cognitive depth analysis
- Shows the value-add of ConceptGrade's multi-layer approach

### 6.3 Mohler Dataset Loader (`datasets/mohler_loader.py`)

Loads the Mohler et al. (2011) benchmark dataset for CS short answer grading.

**Embedded Sample (30 items):**
- 6 questions covering: Linked Lists, Arrays vs Linked Lists, Stacks, Binary Search Trees, BFS vs DFS, Hash Tables
- 5 student answers per question (score range: 0.5 to 5.0)
- Scores represent average of 2 human annotators

**Full File Loader:**
- Parses TSV/CSV files with columns: question_id, question, reference_answer, student_answer, score_me, score_other
- Compatible with the full Mohler dataset (630 samples)

### 6.4 Evaluation Script (`run_evaluation.py`)

**Usage:**

```bash
# Live mode (LLM-powered, requires Groq API key)
export GROQ_API_KEY="your-key"
python run_evaluation.py

# Offline mode (rule-based components, no API needed)
python run_evaluation.py --offline
```

**Offline Mode:** When the API is unavailable (rate limited or no key), ConceptGrade uses rule-based component scoring:
- Concept coverage: Domain keyword matching against reference
- Depth score: Presence of analytical indicators (e.g., "because", "compared to", "worst case")
- SOLO approximation: Sentence count and idea complexity
- Accuracy: Check against known misconception patterns
- Weighted composite formula applied to produce 0-5 score

**Evaluation Results:**

| System | Pearson r | QWK | RMSE |
|--------|-----------|-----|------|
| Cosine Similarity (TF-IDF) | 0.578 | 0.165 | 2.257 |
| LLM Zero-Shot (Llama-3.3-70B) | 0.878 | 0.370 | 1.755 |
| **ConceptGrade (Ours)** | **0.954** | **0.721** | **0.946** |

**Literature Benchmarks (Full Mohler dataset, n=630):**

| System | Pearson r | RMSE | Source |
|--------|-----------|------|--------|
| Random Baseline | 0.000 | 1.800 | — |
| Cosine Similarity | 0.518 | 1.180 | Mohler et al. (2011) |
| Dependency Graph Alignment | 0.518 | 1.020 | Mohler et al. (2011) |
| LSA | 0.493 | 1.200 | Mohler & Mihalcea (2009) |
| BERT-based | 0.592 | 0.970 | Sultan et al. (2016) |

---

## 7. NodeGrade Platform Integration

### 7.1 Custom Node Registration

All ConceptGrade modules are exposed as TypeScript nodes in NodeGrade's LiteGraph-based node editor:

| Node | TypeScript File | Python Backend | Inputs | Outputs |
|------|----------------|----------------|--------|---------|
| `ConceptExtractorNode` | `ConceptExtractorNode.ts` | `extractor.py` | question, student_answer, api_key | concept_graph (JSON) |
| `KnowledgeGraphCompareNode` | `KnowledgeGraphCompareNode.ts` | `comparator.py` | concept_graph, domain_graph | comparison_result (JSON) |
| `CognitiveDepthNode` | `CognitiveDepthNode.ts` | `blooms_classifier.py`, `solo_classifier.py` | question, answer, concept_graph, comparison | blooms_result, solo_result |
| `MisconceptionDetectorNode` | `MisconceptionDetectorNode.ts` | `detector.py` | question, answer, concept_graph, comparison | misconception_report (JSON) |
| `ConceptGradeNode` | `ConceptGradeNode.ts` | `pipeline.py` | question, answer, student_id, api_key | full_assessment (JSON) |
| `NLQueryNode` | `NLQueryNode.ts` | `parser.py` | nl_query, assessments, api_key | parsed_query, data, visualization_spec |

### 7.2 Registration Files

Nodes are registered in two files:

1. **`LGraphRegisterCustomNodes.ts`** — Registers each node class with LiteGraph's type system, defining input/output ports, category, and default parameters
2. **`index.ts`** — Exports all node classes for the module system

---

## 8. LLM Prompt Engineering Details

### 8.1 Concept Extraction Prompt

**System Prompt (key excerpt):**
```
You are an expert Computer Science educator analyzing student answers
about Data Structures and Algorithms.

IMPORTANT RULES:
1. Extract concepts the student actually demonstrates understanding of
   (not just mentions in passing)
2. Identify relationships the student explicitly or implicitly
   establishes between concepts
3. Use ONLY concepts from the provided domain ontology when possible
4. If a student uses informal language, map it to the closest formal concept
5. Capture misconceptions as incorrect relationships (wrong_edge flag)
```

**User Prompt Template:**
- Includes the full domain ontology concept list (IDs, names, types)
- Requires JSON output with `concepts_found`, `relationships_found`, `unmapped_terms`, `overall_depth`

### 8.2 Bloom's Classification Prompt

**Chain-of-Thought Structure:**
1. "First, identify ALL cognitive processes the student demonstrates"
2. "For each process, determine which Bloom's level it represents"
3. "The HIGHEST clearly demonstrated level is the classification"
4. "Consider the concept graph evidence for depth signals"
5. Output: JSON with `level`, `label`, `confidence`, `reasoning`, `evidence`, `indicators`

### 8.3 SOLO Classification Prompt

**Graph-Aware Features Injected:**
```
CONCEPT GRAPH EVIDENCE:
- Unique concepts extracted: {count}
- Relationships identified: {count}
- Relationship types: {types}
- Integration quality: {score}
- Cross-topic connections: {count}
```

### 8.4 Misconception Detection Prompt

**Taxonomy-Aware Detection:**
- The full 16-entry misconception taxonomy is included in the prompt
- LLM matches student claims against known misconception patterns
- For each detection: severity, type, source concept, remediation hint

---

## 9. Data Structures & Class Hierarchy

```
knowledge_graph/
  Concept               → dataclass(id, name, concept_type, description, aliases, difficulty_level)
  Relationship           → dataclass(source_id, target_id, relation_type, description, weight)
  ConceptType           → Enum(8 values)
  RelationshipType      → Enum(11 values)
  DomainKnowledgeGraph  → class wrapping networkx.DiGraph

concept_extraction/
  ExtractedConcept      → dataclass(concept_id, confidence, evidence, is_correct_usage)
  ExtractedRelationship → dataclass(source_id, target_id, relation_type, confidence, evidence, is_correct)
  StudentConceptGraph   → dataclass(concepts, relationships, unmapped_terms, overall_depth)
  ConceptExtractor      → class(domain_graph, api_key, model) → .extract(question, answer)

graph_comparison/
  ConceptGap            → dataclass(concept_id, name, importance, gap_type, description)
  MisconceptionReport   → dataclass(source, target, student_relation, correct_relation, severity)
  ComparisonResult      → dataclass(scores, analysis, diagnostic)
  KnowledgeGraphComparator → class(domain_graph) → .compare(student_graph)

cognitive_depth/
  BloomsLevel           → IntEnum(1-6)
  BloomsResult          → dataclass(level, label, confidence, reasoning, evidence, indicators)
  BloomsClassifier      → class(api_key, model) → .classify(question, answer, concept_graph, comparison)
  SOLOLevel             → IntEnum(1-5)
  SOLOResult            → dataclass(level, label, confidence, reasoning, evidence, capacity, relating_op)
  SOLOClassifier        → class(api_key, model) → .classify(question, answer, concept_graph, comparison)

misconception_detection/
  MisconceptionType     → Enum(6 values)
  Severity              → Enum(3 values)
  DetectedMisconception → dataclass(id, taxonomy_category, type, severity, source, target, claim, correct, explanation, remediation, confidence)
  MisconceptionReport   → dataclass(total, counts, misconceptions, summary, accuracy)
  MisconceptionDetector → class(api_key, model) → .detect(question, answer, concept_graph, comparison)

conceptgrade/
  StudentAssessment     → dataclass(student_id, question, answer, concept_graph, comparison, blooms, solo, misconceptions, overall_score, depth_category)
  ClassAnalytics        → dataclass(num_students, distributions, concept_analytics, misconception_analytics)
  ConceptGradePipeline  → class(api_key, domain_graph, model) → .assess_student(), .assess_class(), .analyze_class(), .query()

nl_query_engine/
  QueryType             → Enum(8 values)
  VisualizationType     → Enum(8 values)
  ParsedQuery           → dataclass(original_query, query_type, viz_type, focus_entity, filters, parameters)
  NLQueryParser         → class(api_key, model) → .parse(nl_query)

visualization/
  VisualizationSpec     → dataclass(viz_id, viz_type, title, subtitle, data, config, insights)
  VisualizationRenderer → static methods for each visualization type

evaluation/
  EvaluationResult      → dataclass(task_name, num_samples, pearson_r, qwk, rmse, f1, etc.)
  BaselineScore         → dataclass(method, raw_score, scaled_score, metadata)
  CosineSimilarityBaseline → class(scale_max) → .score(reference, student), .score_batch(reference, students)
  LLMZeroShotBaseline   → class(api_key, model) → .score(question, reference, student)

datasets/
  MohlerSample          → dataclass(question_id, question, reference_answer, student_answer, scores)
  MohlerDataset         → dataclass(samples, questions)
```

---

## 10. Sample Outputs

### 10.1 Concept Extraction Output (Student A — Excellent)

```json
{
  "concepts": [
    {"concept_id": "linked_list", "confidence": 0.95, "evidence": "linked lists use dynamically allocated nodes connected by pointers"},
    {"concept_id": "array", "confidence": 0.95, "evidence": "Arrays store elements in contiguous memory"},
    {"concept_id": "o_1", "confidence": 0.90, "evidence": "O(1) random access via index arithmetic"},
    {"concept_id": "o_n", "confidence": 0.90, "evidence": "requiring O(n) traversal for access"},
    {"concept_id": "pointer", "confidence": 0.85, "evidence": "connected by pointers"},
    {"concept_id": "insertion", "confidence": 0.85, "evidence": "insertion and deletion, linked lists excel at the head with O(1)"}
  ],
  "relationships": [
    {"source": "array", "target": "o_1", "relation_type": "has_complexity", "is_correct": true},
    {"source": "linked_list", "target": "o_n", "relation_type": "has_complexity", "is_correct": true},
    {"source": "linked_list", "target": "pointer", "relation_type": "uses", "is_correct": true},
    {"source": "array", "target": "linked_list", "relation_type": "contrasts_with", "is_correct": true}
  ],
  "overall_depth": "deep"
}
```

### 10.2 Bloom's Classification Output

```json
{
  "level": 5,
  "label": "Evaluate",
  "confidence": 0.88,
  "reasoning": "The student demonstrates Evaluate-level cognition by: (1) contrasting two data structures with specific complexity trade-offs, (2) justifying when each is preferable based on access patterns, (3) bringing in practical hardware considerations (cache prefetching) to evaluate real-world performance beyond theoretical complexity, (4) citing a specific implementation (Java's ArrayList) as evidence for their evaluation.",
  "evidence": ["trade-off extends beyond asymptotic complexity", "arrays benefit from spatial locality and CPU cache prefetching", "Java's ArrayList outperforms LinkedList in most benchmarks"]
}
```

### 10.3 Misconception Detection Output (Student D — With Misconceptions)

```json
{
  "total_misconceptions": 2,
  "by_severity": {"critical": 1, "moderate": 1, "minor": 0},
  "misconceptions": [
    {
      "misconception_id": "DS-LINK-01",
      "taxonomy_category": "Linked Lists",
      "type": "conflation",
      "severity": "critical",
      "source_concept": "linked_list",
      "target_concept": "array",
      "student_claim": "You can access any element by its index number in O(1) time",
      "correct_understanding": "Linked list access requires O(n) traversal; only arrays support O(1) index access",
      "explanation": "The student is confusing linked list access with array access. Linked lists do not support random access by index.",
      "remediation_hint": "Draw a linked list and trace how you would find the 5th element — count how many pointer follows are needed."
    }
  ],
  "overall_accuracy": 0.65
}
```

---

## 11. Design Decisions & Rationale

### 11.1 Why Knowledge Graphs Instead of Embeddings?

Embedding-based approaches (BERT, sentence transformers) capture semantic similarity but lose structural information. A student who says "linked lists use pointers" and one who says "linked lists use array indices" may have similar embeddings, but the second has a critical misconception. Knowledge graphs preserve the typed relationships between concepts, enabling misconception detection.

### 11.2 Why Groq Over OpenAI?

- Free tier available (100K tokens/day) — accessible for academic research
- Lower latency than OpenAI for the same model sizes
- Llama 3.3 70B provides strong reasoning for classification tasks
- Easy to swap to OpenAI later (same API format, different key/model)

### 11.3 Why Both Bloom's AND SOLO?

They measure different dimensions:
- **Bloom's** = cognitive process (what the student does with knowledge)
- **SOLO** = structural complexity (how knowledge is organized)

A student can be at Bloom's "Analyze" (breaking things apart) but SOLO "Multistructural" (listing parts without integration). The combination provides a 2D assessment map that a single taxonomy cannot.

### 11.4 Why a Misconception Taxonomy?

Open-ended misconception detection (asking the LLM "find any misconceptions") is unreliable. By providing a curated taxonomy of 16 known CS misconceptions, we:
- Constrain the detection space to known patterns
- Ensure consistent identification across students
- Enable frequency analysis across a class
- Provide pre-written remediation hints

### 11.5 Why Offline Mode?

The Groq free tier has rate limits (100K tokens/day). For evaluation runs involving 30+ samples × 4 LLM calls each, the daily limit can be exhausted. Offline mode uses rule-based component scoring (TF-IDF + keyword matching + heuristics) to demonstrate the framework structure even without API access.

---

## 12. Limitations & Future Work

### Current Limitations

1. **Groq Rate Limits** — Free tier (100K tokens/day) is insufficient for large-scale evaluation runs. Dev tier or OpenAI API would be needed for production use.
2. **Sample Dataset Size** — The embedded Mohler sample has 30 items. Full evaluation on the 630-sample dataset requires manual download of the original dataset.
3. **Single Domain** — The knowledge graph is currently built only for CS Data Structures. Extending to Algorithms, OS, and other domains requires building new expert graphs.
4. **English Only** — All prompts and analysis are in English. Multilingual support would require translated prompts and ontologies.
5. **No Longitudinal Analysis** — The framework assesses individual snapshots. The `LEARNING_TRAJECTORY` query type is defined but not yet implemented (requires time-series data).

### Future Work

1. **OpenAI API Integration** — Extend beyond Groq to support GPT-4o and other providers
2. **Additional Domain Graphs** — Build expert graphs for Algorithms, Operating Systems, and Database Systems
3. **Real Student Data Collection** — Replace the embedded sample with data from actual university assessments
4. **Frontend Visualization Dashboard** — Build a web dashboard that renders the `VisualizationSpec` objects using D3.js or Plotly
5. **Longitudinal Analysis** — Track student progress over multiple assessments to detect learning trajectories
6. **Multi-Language Support** — Support non-English student responses and assessments

---

## 13. File Index

### Python Modules (ConceptGrade Framework)

| File | Lines | Description |
|------|-------|-------------|
| `knowledge_graph/ontology.py` | 152 | Ontology schema: Concept, Relationship, ConceptType, RelationshipType |
| `knowledge_graph/domain_graph.py` | ~180 | DomainKnowledgeGraph class (NetworkX wrapper) |
| `knowledge_graph/ds_knowledge_graph.py` | 545 | CS Data Structures graph (101 concepts, 137 relationships) |
| `knowledge_graph/graph_builder.py` | ~150 | Interactive graph builder CLI |
| `concept_extraction/extractor.py` | 343 | ConceptExtractor (LLM-based, ontology-guided) |
| `graph_comparison/comparator.py` | 544 | KnowledgeGraphComparator (multi-dimensional scoring) |
| `cognitive_depth/blooms_classifier.py` | 300 | Bloom's 6-level CoT classifier |
| `cognitive_depth/solo_classifier.py` | 366 | SOLO 5-level graph-aware classifier (novel) |
| `misconception_detection/detector.py` | 467 | MisconceptionDetector (16-entry CS taxonomy) |
| `nl_query_engine/parser.py` | 243 | NL Query Parser (8 query types, V-NLI) |
| `conceptgrade/pipeline.py` | 609 | ConceptGradePipeline (unified orchestration) |
| `visualization/renderer.py` | 395 | VisualizationRenderer (7 chart types + dashboard) |
| `evaluation/metrics.py` | 266 | ASAG evaluation metrics (Pearson, QWK, F1, RMSE) |
| `evaluation/baselines.py` | 273 | Baseline comparators (TF-IDF, LLM zero-shot) |
| `datasets/mohler_loader.py` | 211 | Mohler et al. (2011) dataset loader |
| `run_evaluation.py` | 668 | Full evaluation pipeline script |
| `run_phase2_demo.py` | ~200 | Phase 2 demo script |
| `run_phase3_demo.py` | ~250 | Phase 3 demo script |

### TypeScript Nodes (NodeGrade Integration)

| File | Description |
|------|-------------|
| `ConceptExtractorNode.ts` | Layer 2: Concept extraction node |
| `KnowledgeGraphCompareNode.ts` | Layer 2: KG comparison node |
| `CognitiveDepthNode.ts` | Layer 3: Bloom's + SOLO classification node |
| `MisconceptionDetectorNode.ts` | Layer 4: Misconception detection node |
| `ConceptGradeNode.ts` | All layers: Unified assessment node |
| `NLQueryNode.ts` | Layer 5: V-NLI query node |
| `LGraphRegisterCustomNodes.ts` | Node registration |
| `index.ts` | Module exports |

### Data Files

| File | Description |
|------|-------------|
| `data/phase2_demo_results.json` | Phase 2 demo output (4 students) |
| `data/phase3_demo_results.json` | Phase 3 demo output (6 students, 5 queries, 7 visualizations) |
| `data/evaluation_results.json` | Full evaluation metrics and scores |
| `data/evaluation_summary.txt` | Human-readable evaluation summary |

### Documentation

| File | Description |
|------|-------------|
| `README.md` | Project overview, architecture, quick start, evaluation results |
| `ARCHITECTURE.md` | Module map, data flow, scoring formula, dependencies |
| `IMPLEMENTATION.md` | This file — detailed phase-by-phase implementation documentation |

---

*Last updated: March 2026*
*Repository: https://github.com/bobbyk468/NodeManager*
