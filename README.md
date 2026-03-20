# NodeManager — Concept-Aware Student Assessment Research

This repository contains the implementation, research, and proposal artifacts for extending **NodeGrade** — a node-based Automatic Short Answer Grading (ASAG) tool — into a concept-understanding assessment framework.

## Repository Structure

```
NodeManager/
├── NodeGrade/              # NodeGrade ASAG system (modified & tested)
│   ├── packages/
│   │   ├── backend/        # NestJS backend (API, WebSocket, grading pipeline)
│   │   ├── frontend/       # React + Vite frontend (node-graph editor)
│   │   └── worker/         # Similarity worker (sentence transformers, cosine similarity)
│   └── ...
├── research/               # Research documents
│   ├── research_proposal_concept_understanding.docx   # Formal research proposal (34 pages)
│   ├── research_asag_taxonomies.md                    # ASAG systems, Bloom's & SOLO taxonomies
│   ├── research_kg_misconceptions.md                  # Knowledge graphs & misconception detection
│   ├── research_llm_advances.md                       # LLM cognitive classification & 2024-2025 advances
│   └── NodeGrade_Paper.pdf                            # Original NodeGrade paper (Fischer et al., 2025)
├── screenshots/            # System screenshots
│   ├── nodegrade-graded.png                           # End-to-end grading results
│   └── nodegrade-editor-grading.png                   # Node editor with grading pipeline
└── README.md
```

## Research Proposal

**Title:** *Concept-Aware Student Assessment: Beyond Surface-Level Grading Through Knowledge Graph-Integrated Depth Analysis*

### Problem
Current ASAG systems (including NodeGrade) measure textual similarity between student responses and reference answers. They cannot assess the **depth** of a student's conceptual understanding — a student who memorizes phrasing scores identically to one who deeply understands the concept.

### Proposed Solution
A 5-layer architecture extending NodeGrade:

1. **Concept Extraction Pipeline** — Extract domain concepts and relationships from student free-text answers using LLM-based NER + ontology validation
2. **Knowledge Graph Comparison** — Compare student concept sub-graphs against expert reference graphs to identify gaps, misconceptions, and integration quality
3. **Cognitive Depth Classification** — Assign Bloom's Taxonomy and SOLO Taxonomy levels to student responses
4. **Misconception Detection** — Identify specific incorrect mental models, not just "wrong answers"
5. **V-NLI Visualization** — Natural language interface for teachers to query assessment data (e.g., *"Show which concepts are most misunderstood in Class 3B"*)

### Key Evidence
- Emirtekin & Özarslan (2025): LLM-human agreement drops systematically at higher Bloom's cognitive levels (QWK 0.585–0.640)
- Haycocks et al. (2024): Conceptual knowledge is more durable than factual recall
- No existing ASAG system combines knowledge graph comparison + cognitive taxonomy classification + misconception detection

## NodeGrade Setup

### Prerequisites
- Node.js 18+, Yarn, Docker (for PostgreSQL)
- LLM API key (Groq or OpenAI)

### Quick Start
```bash
cd NodeGrade

# Start PostgreSQL
docker run -d --name nodegrade-db -p 5432:5432 \
  -e POSTGRES_DB=nodegrade -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  postgres:15

# Install dependencies
corepack enable && yarn install

# Configure environment
cp packages/backend/.env_template packages/backend/.env
# Edit .env: set OPENAI_API_KEY (or BEARER_TOKEN for Groq)

# Build and start
yarn workspace backend build
yarn workspace backend start &
yarn workspace frontend dev &

# Start similarity worker
cd packages/worker && pip install -r requirements.txt && python main.py &
```

### Modifications Made
The following fixes were applied to the original NodeGrade codebase:

1. **Output node type fix** — Changed `output/feedback` to `output/output` in frontend node definitions
2. **Similarity worker URL** — Added `SIMILARITY_WORKER_URL` to node hydration environment
3. **CosineSimilarity string handling** — Enhanced to auto-embed string inputs via the similarity worker
4. **Groq LLM integration** — Configured `MODEL_WORKER_URL` and `BEARER_TOKEN` for Groq API with `llama-3.3-70b-versatile`

### Test Results
- **Score:** 66.79%
- **Feedback:** German-language LLM-generated feedback
- **Verdict:** "Bestanden!" (Passed)
- **LLM Models Available:** 18 Groq models

## References

Key papers cited in the research proposal:

- Fischer, D.V. et al. (2025). *NodeGrade: Evaluation of a Node-based Automatic Short Answer Tool.* ACM.
- Emirtekin, E. & Özarslan, Y. (2025). *Automatic Short-Answer Grading in Sustainability Education.* JCAL.
- Cohn, C. et al. (2024). *A Chain-of-Thought Prompting Approach with LLMs for Evaluating Students' Formative Assessment Responses.* AAAI.
- Biggs, J. & Collis, K. (1982). *SOLO Taxonomy.* Academic Press.
- Anderson, L.W. & Krathwohl, D.R. (2001). *Bloom's Revised Taxonomy.* Longman.

See `research/research_proposal_concept_understanding.docx` for the full 34-page proposal with 23+ references.

## License

NodeGrade is licensed under the [MIT License](./NodeGrade/LICENSE). Research documents are original work.
