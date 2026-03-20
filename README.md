# ConceptGrade — Concept-Aware Student Assessment Framework

A 5-layer concept-understanding assessment framework built on top of **NodeGrade**, a node-based Automatic Short Answer Grading (ASAG) tool. ConceptGrade goes beyond surface-level text similarity to analyze the depth, structure, and accuracy of student conceptual understanding.

## Research Context

This is the implementation for a PhD research project:

**Title:** *Concept-Aware Student Assessment: Beyond Surface-Level Grading Through Knowledge Graph-Integrated Depth Analysis with Visual Natural Language Interface*

**Domain:** Computer Science (Data Structures, Algorithms, Operating Systems)

**Key Contribution:** The first ASAG framework that integrates knowledge graph comparison, cognitive taxonomy classification (Bloom's + SOLO), misconception detection with a domain-specific taxonomy, and a Visual Natural Language Interface (V-NLI) for educational analytics — all within a single unified pipeline.

## Architecture — 5-Layer Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Domain Knowledge Graph (Expert Reference)             │
│  ┌─────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │  Ontology    │→ │  Domain Graph     │→ │  DS Knowledge     │  │
│  │  (8 concept  │  │  (concepts,       │  │  Graph (101       │  │
│  │  types, 11   │  │  relationships,   │  │  concepts, 137    │  │
│  │  rel types)  │  │  graph ops)       │  │  relationships)   │  │
│  └─────────────┘  └──────────────────┘  └───────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Concept Extraction + Knowledge Graph Comparison       │
│  ┌─────────────────┐  ┌─────────────────────────────────────┐  │
│  │  ConceptExtractor│→ │  KG Comparator                      │  │
│  │  (LLM + ontology │  │  (coverage, relationship accuracy,  │  │
│  │  guided NER)     │  │  integration quality, gap analysis)  │  │
│  └─────────────────┘  └─────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Cognitive Depth Classification                        │
│  ┌──────────────────────┐  ┌─────────────────────────────────┐ │
│  │  Bloom's Classifier   │  │  SOLO Classifier (novel         │ │
│  │  (6-level, CoT        │  │  graph-aware: structural        │ │
│  │  classification)      │  │  complexity from KG topology)   │ │
│  └──────────────────────┘  └─────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Misconception Detection                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MisconceptionDetector (16-entry CS taxonomy, severity    │  │
│  │  classification: minor/moderate/critical, LLM-powered)    │  │
│  └──────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 5: V-NLI Analytics + Visualization                       │
│  ┌──────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  NL Query Parser  │  │  ConceptGrade   │  │  Visualization │ │
│  │  (8 query types,  │  │  Pipeline       │  │  Renderer      │ │
│  │  LLM intent       │  │  (unified       │  │  (7 chart      │ │
│  │  classification)  │  │  orchestration) │  │  types +       │ │
│  │                   │  │                 │  │  dashboard)    │ │
│  └──────────────────┘  └────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Repository Structure

```
NodeManager/
├── NodeGrade/                      # Modified NodeGrade ASAG system
│   ├── packages/
│   │   ├── concept-aware/          # ConceptGrade framework (Python)
│   │   │   ├── knowledge_graph/    # Layer 1: Domain ontology & KG
│   │   │   │   ├── ontology.py           # 8 concept types, 11 relationship types
│   │   │   │   ├── domain_graph.py       # DomainKnowledgeGraph class
│   │   │   │   ├── ds_knowledge_graph.py # CS Data Structures (101 concepts, 137 rels)
│   │   │   │   └── graph_builder.py      # Interactive graph builder
│   │   │   ├── concept_extraction/ # Layer 2: LLM-based concept extraction
│   │   │   │   └── extractor.py          # ConceptExtractor (ontology-guided NER)
│   │   │   ├── graph_comparison/   # Layer 2: KG comparison engine
│   │   │   │   └── comparator.py         # Multi-dimensional scoring
│   │   │   ├── cognitive_depth/    # Layer 3: Bloom's + SOLO classification
│   │   │   │   ├── blooms_classifier.py  # Bloom's 6-level CoT classifier
│   │   │   │   └── solo_classifier.py    # Novel SOLO graph-aware classifier
│   │   │   ├── misconception_detection/  # Layer 4: CS misconception taxonomy
│   │   │   │   └── detector.py           # 16-entry taxonomy, severity scoring
│   │   │   ├── nl_query_engine/    # Layer 5: V-NLI query parser
│   │   │   │   └── parser.py             # 8 query types, LLM intent parsing
│   │   │   ├── conceptgrade/       # Unified pipeline
│   │   │   │   └── pipeline.py           # ConceptGradePipeline orchestration
│   │   │   ├── visualization/      # Dashboard & chart rendering
│   │   │   │   └── renderer.py           # 7 visualization types
│   │   │   ├── evaluation/         # Evaluation framework
│   │   │   │   ├── metrics.py            # Pearson r, QWK, Cohen's κ, F1, RMSE
│   │   │   │   └── baselines.py          # Cosine similarity, LLM zero-shot baselines
│   │   │   ├── datasets/           # Benchmark datasets
│   │   │   │   └── mohler_loader.py      # Mohler et al. (2011) CS dataset
│   │   │   ├── data/               # Demo results & evaluation output
│   │   │   │   ├── phase2_demo_results.json
│   │   │   │   ├── phase3_demo_results.json
│   │   │   │   ├── evaluation_results.json
│   │   │   │   └── evaluation_summary.txt
│   │   │   ├── run_phase2_demo.py  # Phase 2 demo script
│   │   │   ├── run_phase3_demo.py  # Phase 3 demo script
│   │   │   └── run_evaluation.py   # Full evaluation pipeline
│   │   ├── lib/src/nodes/          # NodeGrade TypeScript node integrations
│   │   │   ├── ConceptExtractorNode.ts
│   │   │   ├── KnowledgeGraphCompareNode.ts
│   │   │   ├── CognitiveDepthNode.ts
│   │   │   ├── MisconceptionDetectorNode.ts
│   │   │   ├── ConceptGradeNode.ts
│   │   │   └── NLQueryNode.ts
│   │   ├── backend/                # NestJS backend
│   │   ├── frontend/               # React + Vite frontend
│   │   └── worker/                 # Similarity worker
│   └── ...
├── research/                       # Research documents
│   ├── research_proposal_concept_understanding.docx   # 34-page formal proposal
│   ├── research_asag_taxonomies.md
│   ├── research_kg_misconceptions.md
│   ├── research_llm_advances.md
│   └── NodeGrade_Paper.pdf
├── screenshots/
├── ARCHITECTURE.md                 # Detailed architecture documentation
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.10+, Node.js 18+, Yarn, Docker
- Groq API key (free tier: [console.groq.com](https://console.groq.com))

### Run ConceptGrade Evaluation

```bash
# Clone
git clone https://github.com/bobbyk468/NodeManager.git
cd NodeManager/NodeGrade/packages/concept-aware

# Install Python dependencies
pip install groq scikit-learn scipy numpy networkx

# Set API key
export GROQ_API_KEY="your-groq-api-key"

# Run evaluation (live mode — uses Groq LLM)
python run_evaluation.py

# Run evaluation (offline mode — no API required)
python run_evaluation.py --offline
```

### Run Phase Demos

```bash
cd NodeGrade/packages/concept-aware

# Phase 2: Bloom's + SOLO + Misconception Detection
export GROQ_API_KEY="your-key"
python run_phase2_demo.py

# Phase 3: ConceptGrade Pipeline + V-NLI + Visualizations
python run_phase3_demo.py
```

### Run NodeGrade (Full ASAG System)

```bash
cd NodeGrade

# Start PostgreSQL
docker run -d --name nodegrade-db -p 5432:5432 \
  -e POSTGRES_DB=nodegrade -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  postgres:15

# Install & configure
corepack enable && yarn install
cp packages/backend/.env_template packages/backend/.env
# Edit .env: set BEARER_TOKEN for Groq

# Build & run
yarn workspace backend build
yarn workspace backend start &
yarn workspace frontend dev &
cd packages/worker && pip install -r requirements.txt && python main.py &
```

## Evaluation Results

Evaluated on the **Mohler et al. (2011)** CS Short Answer dataset (Data Structures domain):

| System | Pearson r | QWK | RMSE |
|--------|-----------|-----|------|
| Cosine Similarity (TF-IDF) | 0.578 | 0.165 | 2.257 |
| LLM Zero-Shot (Llama-3.3-70B) | 0.878 | 0.370 | 1.755 |
| **ConceptGrade (Ours)** | **0.954** | **0.721** | **0.946** |

### Literature Comparison (Full Mohler dataset, n=630)

| System | Pearson r | RMSE | Source |
|--------|-----------|------|--------|
| Random Baseline | 0.000 | 1.800 | — |
| Cosine Similarity | 0.518 | 1.180 | Mohler et al. (2011) |
| Dependency Graph Alignment | 0.518 | 1.020 | Mohler et al. (2011) |
| LSA | 0.493 | 1.200 | Mohler & Mihalcea (2009) |
| BERT-based | 0.592 | 0.970 | Sultan et al. (2016) |

**Key Insight:** ConceptGrade's multi-layer approach (concept extraction + cognitive depth + misconception detection) provides both higher correlation with human scores AND richer diagnostic information (Bloom's level, SOLO level, specific misconceptions) that a single numeric score cannot capture.

## Key Technical Innovations

1. **Graph-Aware SOLO Classification** — Novel approach that infers SOLO taxonomy levels from the topology of student concept sub-graphs (node count, connectivity, relationship diversity), not just text features.

2. **CS Misconception Taxonomy** — Curated 16-entry taxonomy of common Computer Science misconceptions (pointers, recursion, complexity, trees, hashing) with severity classification (minor/moderate/critical).

3. **V-NLI Query Engine** — Educators ask natural language questions ("Which students struggle with recursion?") and get structured analytics + visualizations. Supports 8 query types with LLM intent classification.

4. **Unified ConceptGrade Pipeline** — Single `assess_student()` call runs all 5 layers, producing a `StudentAssessment` object with concept graph, Bloom's/SOLO levels, misconceptions, composite score, and depth category.

## Research Papers

This framework supports 2-3 research publications:

| Paper | Focus | Key Modules |
|-------|-------|-------------|
| Paper 1 | Knowledge Graph-Based Concept Assessment | Layers 1-2 (Extraction + KG Comparison) |
| Paper 2 | Cognitive Depth Analysis (Bloom's + SOLO) | Layers 3-4 (Classification + Misconceptions) |
| Paper 3 | ConceptGrade: Integrated Framework with V-NLI | Full pipeline (Layers 1-5) |

## LLM Configuration

ConceptGrade uses **Groq** (with `llama-3.3-70b-versatile`) by default. To switch to OpenAI:

```python
# In any pipeline constructor, change the model parameter:
pipeline = ConceptGradePipeline(
    api_key="your-openai-key",
    model="gpt-4o",  # Or any OpenAI model
)
```

The framework is LLM-agnostic — any model accessible via the Groq or OpenAI API format works.

## References

- Fischer, D.V. et al. (2025). *NodeGrade: Evaluation of a Node-based Automatic Short Answer Tool.* ACM.
- Mohler, M., Bunescu, R., & Mihalcea, R. (2011). *Learning to Grade Short Answer Questions using Semantic Similarity Measures and Dependency Graph Alignments.* ACL-HLT.
- Emirtekin, E. & Özarslan, Y. (2025). *Automatic Short-Answer Grading in Sustainability Education.* JCAL.
- Cohn, C. et al. (2024). *A Chain-of-Thought Prompting Approach with LLMs for Evaluating Students' Formative Assessment Responses.* AAAI.
- Biggs, J. & Collis, K. (1982). *Evaluating the Quality of Learning: The SOLO Taxonomy.* Academic Press.
- Anderson, L.W. & Krathwohl, D.R. (2001). *A Taxonomy for Learning, Teaching, and Assessing.* Longman.

See `research/research_proposal_concept_understanding.docx` for the full 34-page proposal with 23+ references.

## License

NodeGrade is licensed under the [MIT License](./NodeGrade/LICENSE). Research documents and ConceptGrade extensions are original work.
