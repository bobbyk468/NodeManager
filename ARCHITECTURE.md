# ConceptGrade Architecture Documentation

## System Overview

ConceptGrade is a 5-layer concept-understanding assessment framework that extends NodeGrade. It processes student free-text responses through concept extraction, knowledge graph comparison, cognitive depth classification, misconception detection, and visual analytics.

```
Student Answer → [Concept Extraction] → [KG Comparison] → [Bloom's/SOLO] → [Misconceptions] → [V-NLI Analytics]
                      Layer 2               Layer 2          Layer 3           Layer 4            Layer 5
                                                              Layer 4
```

Layer 1 (Domain Knowledge Graph) provides the expert reference used by all other layers.

## Module Map

### Layer 1: Domain Knowledge Graph

**Purpose:** Define the expert reference knowledge for the target domain.

| Module | File | Description |
|--------|------|-------------|
| `Ontology` | `knowledge_graph/ontology.py` | Base types: `Concept` (8 types), `Relationship` (11 types), `ConceptType`, `RelationshipType` enums |
| `DomainKnowledgeGraph` | `knowledge_graph/domain_graph.py` | Graph container: add/query concepts and relationships, NetworkX-based |
| `DS Knowledge Graph` | `knowledge_graph/ds_knowledge_graph.py` | Pre-built Data Structures graph: 101 concepts, 137 relationships across linked lists, arrays, trees, graphs, hash tables, stacks, queues, heaps, sorting, searching |
| `GraphBuilder` | `knowledge_graph/graph_builder.py` | Interactive CLI for building new domain knowledge graphs |

**Concept Types:** `data_structure`, `algorithm`, `operation`, `property`, `complexity_class`, `design_pattern`, `abstract_concept`, `programming_construct`

**Relationship Types:** `is_a`, `has_part`, `prerequisite_for`, `implements`, `uses`, `variant_of`, `has_property`, `has_complexity`, `operates_on`, `produces`, `contrasts_with`

### Layer 2: Concept Extraction + KG Comparison

**Purpose:** Extract student concepts and compare against expert reference.

| Module | File | Key Class | Description |
|--------|------|-----------|-------------|
| `ConceptExtractor` | `concept_extraction/extractor.py` | `ConceptExtractor` | LLM-powered concept/relationship extraction with ontology-guided validation. Produces `StudentConceptGraph` with `ExtractedConcept` and `ExtractedRelationship` objects. |
| `KGComparator` | `graph_comparison/comparator.py` | `KnowledgeGraphComparator` | Multi-dimensional comparison: concept coverage (0-1), relationship accuracy (0-1), integration quality (0-1). Produces `ComparisonResult` with gap analysis and misconception reports. |

**Data Flow:**
```
Student Answer + Question
    ↓
ConceptExtractor.extract(question, student_answer)
    ↓ produces StudentConceptGraph
KnowledgeGraphComparator.compare(student_graph)
    ↓ produces ComparisonResult
    ↓   - concept_coverage: fraction of expected concepts
    ↓   - relationship_accuracy: correct vs incorrect relationships
    ↓   - integration_quality: graph connectivity metric
    ↓   - gaps: missing concepts and relationships
    ↓   - misconception_reports: incorrect relationships found
```

### Layer 3: Cognitive Depth Classification

**Purpose:** Classify the cognitive level of student responses.

| Module | File | Key Class | Levels |
|--------|------|-----------|--------|
| `BloomsClassifier` | `cognitive_depth/blooms_classifier.py` | `BloomsClassifier` | 6 levels: Remember (1), Understand (2), Apply (3), Analyze (4), Evaluate (5), Create (6) |
| `SOLOClassifier` | `cognitive_depth/solo_classifier.py` | `SOLOClassifier` | 5 levels: Prestructural (1), Unistructural (2), Multistructural (3), Relational (4), Extended Abstract (5) |

**Innovation:** The SOLO classifier uses graph topology from the concept extraction step — counting unique concepts (nodes), relationships (edges), and relationship diversity to inform structural complexity judgments. This is a novel contribution not found in existing ASAG systems.

**Classification Method:** Chain-of-Thought (CoT) prompting where the LLM receives the question, student answer, extracted concept graph, and comparison results, then reasons through the taxonomy before assigning a level with confidence score.

### Layer 4: Misconception Detection

**Purpose:** Identify specific incorrect mental models in student understanding.

| Module | File | Key Class | Description |
|--------|------|-----------|-------------|
| `MisconceptionDetector` | `misconception_detection/detector.py` | `MisconceptionDetector` | LLM-powered detection with 16-entry CS taxonomy, severity classification (minor/moderate/critical), per-concept and per-relationship analysis |

**CS Misconception Taxonomy (16 entries):**

| Category | Examples |
|----------|----------|
| Pointer/Reference | Confusing pointers with data values; assuming arrays use pointers |
| Recursion | Treating recursion as simple iteration; missing base case understanding |
| Complexity | Confusing O(log n) with O(n); assuming hash tables are always O(1) |
| Tree Structures | BST always balanced; confusing BST with heap ordering |
| Linked Lists | Random access in O(1); confusing with arrays |
| Sorting | Stable vs unstable confusion; complexity misattribution |
| Graph Algorithms | BFS/DFS confusion (stack vs queue); shortest path assumptions |
| Hashing | No collision understanding; confusing chaining with open addressing |

**Severity Levels:**
- `minor` — Imprecise but not fundamentally wrong
- `moderate` — Incorrect understanding that could cause errors
- `critical` — Fundamental misunderstanding of core concepts

### Layer 5: V-NLI Analytics + Visualization

**Purpose:** Enable educators to query assessment data using natural language.

| Module | File | Key Class | Description |
|--------|------|-----------|-------------|
| `NLQueryParser` | `nl_query_engine/parser.py` | `NLQueryParser` | Parses educator queries into structured `ParsedQuery` with query type, focus entity, filters, and visualization type |
| `ConceptGradePipeline` | `conceptgrade/pipeline.py` | `ConceptGradePipeline` | Unified orchestration: `assess_student()`, `assess_class()`, `analyze_class()`, `query()` |
| `VisualizationRenderer` | `visualization/renderer.py` | `VisualizationRenderer` | 7 chart types + dashboard generation |

**Query Types (8):**

| Type | Example Query | Visualization |
|------|--------------|---------------|
| `bloom_distribution` | "What are the Bloom's levels in the class?" | Bar chart |
| `solo_distribution` | "Show SOLO taxonomy distribution" | Bar chart |
| `misconception_analysis` | "Which misconceptions are most common?" | Heatmap |
| `concept_analysis` | "What concepts are students missing?" | Radar chart |
| `concept_heatmap` | "Show concept coverage across students" | Heatmap |
| `student_comparison` | "Compare Alice and Bob's understanding" | Radar chart |
| `class_summary` | "Give me an overview of the class" | Dashboard |
| `at_risk_students` | "Which students need help?" | Table |

**Visualization Types (7):** `bar_chart`, `stacked_bar`, `heatmap`, `radar`, `sankey`, `table`, `dashboard`

## Evaluation Framework

| Module | File | Description |
|--------|------|-------------|
| `Metrics` | `evaluation/metrics.py` | Pearson r, Spearman ρ, QWK, Cohen's κ, RMSE, MAE, F1 (macro/weighted), Precision, Recall, concept extraction F1, confusion matrix |
| `Baselines` | `evaluation/baselines.py` | `CosineSimilarityBaseline` (TF-IDF), `LLMZeroShotBaseline` (direct LLM grading) |
| `Mohler Loader` | `datasets/mohler_loader.py` | Mohler et al. (2011) CS dataset: 6 questions, 30 embedded samples, full file loader |
| `Evaluation Script` | `run_evaluation.py` | Complete pipeline: load dataset → run all systems → compute metrics → generate comparison |

## NodeGrade Integration

ConceptGrade modules are integrated into NodeGrade's node-graph system as TypeScript node wrappers:

| Node | File | ConceptGrade Layer |
|------|------|--------------------|
| `ConceptExtractorNode` | `lib/src/nodes/ConceptExtractorNode.ts` | Layer 2 |
| `KnowledgeGraphCompareNode` | `lib/src/nodes/KnowledgeGraphCompareNode.ts` | Layer 2 |
| `CognitiveDepthNode` | `lib/src/nodes/CognitiveDepthNode.ts` | Layer 3 |
| `MisconceptionDetectorNode` | `lib/src/nodes/MisconceptionDetectorNode.ts` | Layer 4 |
| `ConceptGradeNode` | `lib/src/nodes/ConceptGradeNode.ts` | All layers (unified) |
| `NLQueryNode` | `lib/src/nodes/NLQueryNode.ts` | Layer 5 |

All 6 nodes are registered in:
- `lib/src/nodes/LGraphRegisterCustomNodes.ts`
- `lib/src/nodes/index.ts`

## Data Flow (Full Pipeline)

```
Input:
  - question: str
  - student_answer: str
  - student_id: str

ConceptGradePipeline.assess_student(student_id, question, answer)
    │
    ├── Layer 1: self.domain_graph (pre-loaded, 101 concepts)
    │
    ├── Layer 2a: self.extractor.extract(question, student_answer)
    │   → StudentConceptGraph {concepts: [...], relationships: [...]}
    │
    ├── Layer 2b: self.comparator.compare(student_graph)
    │   → ComparisonResult {scores: {coverage, accuracy, integration}, gaps, misconceptions}
    │
    ├── Layer 3a: self.blooms_clf.classify(question, answer, concept_graph, comparison)
    │   → BloomsResult {level: 1-6, label: str, confidence: float, reasoning: str}
    │
    ├── Layer 3b: self.solo_clf.classify(question, answer, concept_graph, comparison)
    │   → SOLOResult {level: 1-5, label: str, confidence: float, reasoning: str}
    │
    ├── Layer 4: self.misconception_det.detect(question, answer, concept_graph, comparison)
    │   → MisconceptionResult {misconceptions: [...], by_severity: {...}, accuracy: float}
    │
    └── Composite: _compute_overall_score(), _categorize_depth()
        → StudentAssessment {
            concept_graph, comparison, blooms, solo, misconceptions,
            overall_score: 0.0-1.0, depth_category: surface|moderate|deep|expert
        }
```

## Composite Scoring Formula

```
overall_score = (
    concept_coverage * 0.15 +      # What fraction of expected concepts?
    relationship_accuracy * 0.15 +  # Are relationships correct?
    integration_quality * 0.15 +    # How connected is the knowledge?
    blooms_normalized * 0.20 +      # Cognitive depth (Bloom's 1-6 → 0-1)
    solo_normalized * 0.20 +        # Structural complexity (SOLO 1-5 → 0-1)
    misconception_accuracy * 0.15   # Factual accuracy (1 - penalty per misconception)
)

depth_category:
    expert   → Bloom's ≥ 5, SOLO ≥ 4, no critical misconceptions
    deep     → Bloom's ≥ 4, SOLO ≥ 3, no critical misconceptions
    moderate → Bloom's ≥ 2, SOLO ≥ 2
    surface  → Otherwise
```

## Dependencies

### Python (ConceptGrade Framework)
- `groq` — LLM API client (Groq cloud)
- `networkx` — Knowledge graph operations
- `scikit-learn` — TF-IDF, cosine similarity, classification metrics
- `scipy` — Pearson/Spearman correlation
- `numpy` — Numerical operations

### Node.js (NodeGrade Platform)
- `@nestjs/core` — Backend framework
- `react` + `vite` — Frontend
- `litegraph.js` — Node-graph editor
- `sentence-transformers` (Python worker) — Embedding-based similarity

## LLM Configuration

All LLM-powered modules accept `api_key` and `model` parameters:

```python
# Default: Groq with Llama 3.3 70B
extractor = ConceptExtractor(
    domain_graph=graph,
    api_key="gsk_...",
    model="llama-3.3-70b-versatile"
)

# OpenAI GPT-4o
extractor = ConceptExtractor(
    domain_graph=graph,
    api_key="sk-...",
    model="gpt-4o"
)
```

Rate limiting is handled per-module with configurable `rate_limit_delay` (default: 1.5s between calls).

## Testing

```bash
cd NodeGrade/packages/concept-aware

# Run evaluation with metrics
python run_evaluation.py --offline

# Run Phase 2 demo (Bloom's, SOLO, Misconceptions)
export GROQ_API_KEY="your-key"
python run_phase2_demo.py

# Run Phase 3 demo (Full pipeline + V-NLI)
python run_phase3_demo.py
```
