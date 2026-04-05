# NodeGrade — Research Methodology

## Automated Knowledge-Graph-Informed Grading of Free-Text Student Responses

**Draft for PhD dissertation / conference paper**
**Date:** March 2026

---

## 1. Research Questions

| RQ | Question |
|----|----------|
| RQ1 | Can a knowledge-graph-informed grading pipeline outperform a pure LLM grader on free-text short answers in CS education? |
| RQ2 | Does the same advantage hold for long-form essay answers? |
| RQ3 | How robust is the system against adversarial student inputs (hallucination, keyword stuffing, concept injection)? |
| RQ4 | Can a visual node-based authoring interface make such a pipeline accessible to instructors without programming knowledge? |

---

## 2. System Overview

The research comprises two tightly coupled components:

| Component | Role |
|-----------|------|
| **ConceptGrade** | 5-layer Python grading algorithm (concept extraction → KG comparison → cognitive depth → misconception detection → SURE ensemble verifier) |
| **NodeGrade** | Visual web platform that wraps ConceptGrade (and other graders) as LiteGraph nodes, enabling instructors to compose, deploy, and monitor grading pipelines without code |

---

## 3. ConceptGrade — Algorithm Methodology

### 3.1 Five-Layer Architecture

```
Student Answer + Question
        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Concept Extraction                             │
│   LLM extracts (concept, confidence, depth) triples    │
│   → StudentConceptGraph                                 │
├─────────────────────────────────────────────────────────┤
│ Layer 2: Knowledge Graph Comparison                     │
│   Student KG ↔ Expert Domain KG                        │
│   Metrics: Coverage, Integration, Confidence-Weighted  │
│   Outputs: matched_concepts, missing_concepts, gaps     │
├─────────────────────────────────────────────────────────┤
│ Layer 3: Cognitive Depth Assessment                     │
│   Bloom's Taxonomy: Remember(1) → Create(6)            │
│   SOLO Taxonomy: Pre-structural(1) → Extended(5)       │
│   Method: Hybrid rule-based + LLM ensemble             │
├─────────────────────────────────────────────────────────┤
│ Layer 4: Misconception Detection                        │
│   16-entry domain taxonomy (DS-STACK-01 … OOP-INH-04)  │
│   Severity: CRITICAL / MAJOR / MINOR                   │
│   Matched against student concept graph                 │
├─────────────────────────────────────────────────────────┤
│ Layer 5: SURE Ensemble Verifier                         │
│   3 LLM personas (Meticulous / Standard / Lenient)     │
│   Input: covered concepts, missing concepts            │
│   Output: median of 3 scores → final [0–5] grade       │
└─────────────────────────────────────────────────────────┘
        ↓
Score (0–5) + Bloom's Level + SOLO Level
+ Misconceptions + Feedback
```

### 3.2 Key Design Decisions

| Decision | Rationale | Empirical Outcome |
|----------|-----------|------------------|
| `verifier_weight = 1.0` (full LLM weight) | KG provides *evidence*; LLM provides holistic judgment. Numerical blending of KG score degrades calibration. | Optimal MAE |
| SURE median (3 personas) | Single-persona LLM variance is high. Median of Meticulous/Standard/Lenient is stable across score ranges. | Consistent with human annotators |
| Remove KG numerical score from verifier prompt | KG score anchored the LLM → over-estimated low-scoring answers. | Bias reduced from −0.237 to −0.008 |
| Flat concept list (no critical/minor split) | Explicit "heavily penalise critical gaps" caused uniform under-scoring in mid-range. | MAE: 0.287 vs 0.367 with split |
| Anchor-Conductance topological detection | When anchor_ratio < 0.65, injected warning into verifier prompt. | Silent Hallucination MAE: 0.467 → 0.300 |
| Epistemic Uncertainty ρ | When KG relevance < 25%, verifier switches to holistic mode. | Prevents structural over-penalisation |

### 3.3 Long Answer Grading (LAG) Extensions

For multi-paragraph essay answers, a parallel wave pipeline is used:

```
Essay
  ↓
Wave 1: SmartSegmenter → paragraph segments
Wave 2: Concept extraction (parallel per segment)
Wave 3: Bloom's + Misconception detection (parallel)
Wave 4: KG comparison per segment
Wave 5: SURE Verifier (LAG personas: Analytical replaces Lenient)
Wave 6: FeedbackSynthesizer → structured professor feedback
```

The `CrossParaIntegrator` detects contradictions across paragraphs using a 3-tier detector (lexical → semantic → SVO contradiction) and applies a 0.6× multiplicative penalty when critical contradictions are found.

---

## 4. Evaluation Methodology

### 4.1 Short Answer Grading (SAG)

**Dataset:** Mohler et al. (2011) CS Short Answer dataset
**Subset used:** n = 120, stratified across full score range 0–5

**Baselines:**
| System | Description |
|--------|-------------|
| Cosine Similarity (TF-IDF) | Lexical surface baseline |
| Pure LLM (zero-shot) | `gemini-2.5-flash` with no KG |
| KG-Only | ConceptGrade without LLM verifier (Layer 2 coverage score mapped directly to [0–5] via linear scaling) |

**Metrics:**
| Metric | Description |
|--------|-------------|
| MAE | Mean Absolute Error (primary) |
| RMSE | Root Mean Square Error |
| Pearson r | Linear correlation with human scores |
| Bias (mean Δ) | Systematic over/under-scoring tendency |

### 4.2 Long Answer Grading (LAG) — Pilot Evaluation

> **Scope note:** The LAG benchmark is an internal pilot evaluation (n=20). Results are reported as exploratory findings and directional evidence that the same KG-informed approach extends to essay grading. They are not intended to support the same level of statistical inference as the SAG benchmark. A larger-scale LAG study is planned as future work (see Section 9).

**Dataset:** Internal essay benchmark
**n = 20 essays**, 5 CS topics: BST, Virtual Memory, TCP/UDP, Garbage Collection, Hash Tables
**Score range:** 0–5 (matching SAG scale)

**Comparison:** ConceptGrade LAG pipeline vs Pure LLM zero-shot on same essays, same evaluator.

### 4.3 Adversarial Robustness

**n = 100 scenarios** across 7 adversarial categories:

| Category | n | Description |
|----------|---|-------------|
| Standard Mastery | 20 | Genuine good answers (control) |
| Prose Trap | 15 | Vague/general language, no specific concepts |
| Adjective Injection | 15 | Incorrect adjectives injected into correct answers |
| Silent Hallucination | 15 | Invented vocabulary that sounds plausible |
| Breadth Bluffer | 10 | Many keywords, no depth |
| Code-Logic Drift | 10 | Correct keywords, wrong logical relationships |
| Structural Split | 15 | Coherent paragraphs with a contradictory final paragraph |

---

## 5. Results Summary

### 5.1 SAG Results (n=120, Mohler 2011)

| Metric | Pure LLM | KG-Only | ConceptGrade | CG vs LLM |
|--------|----------|---------|--------------|-----------|
| MAE | 0.354 | 1.375 | **0.287** | **−18.9%** |
| RMSE | 0.496 | 1.593 | **0.395** | **−20.4%** |
| Pearson r | 0.9679 | 0.5070 | **0.9697** | better |
| Bias | −0.237 | +0.741 | **−0.008** | **97% less** |

> **KG-Only underperformance — explanation for reviewers:** The KG-Only baseline maps Layer 2 concept coverage (a ratio in [0,1]) linearly to the human grading scale [0,5]. This fails for two structural reasons: (1) *coverage is not monotone with quality* — a student who mentions 60% of domain concepts in a semantically wrong context scores higher than one who mentions 20% of concepts correctly; (2) *the KG does not penalise misconceptions or cognitive depth*, so a fluent but incorrect answer can match many KG terms and receive a falsely high score. The LLM verifier in Layer 5 corrects both effects by re-reading the evidence holistically. This result reinforces the claim that KG structure is necessary as *evidence input* to the verifier but is insufficient as a direct grader.

### 5.2 LAG Results (n=20 essays, 5 topics — pilot evaluation)

| Metric | Pure LLM | ConceptGrade | CG vs LLM |
|--------|----------|--------------|-----------|
| MAE | 0.575 | **0.375** | **−34.8%** |
| RMSE | 0.716 | **0.487** | **−32.0%** |
| Pearson r | 0.9641 | **0.9671** | better |
| Bias | +0.575 | **+0.175** | **70% less** |

### 5.3 Adversarial Robustness (n=100)

| Metric | Pure LLM | ConceptGrade | CG vs LLM |
|--------|----------|--------------|-----------|
| MAE | 0.630 | **0.558** | **−11.4%** |
| RMSE | 0.911 | **0.823** | **−9.7%** |
| Pearson r | 0.873 | **0.890** | better |

ConceptGrade wins in 5 of 7 adversarial categories. The two regression cases (Prose Trap, Breadth Bluffer) occur where base LLM is already near-perfect (MAE < 0.2).

---

## 6. NodeGrade — Platform Methodology

### 6.1 Design Rationale

Most ASAG research systems are Python scripts run by researchers. NodeGrade addresses three practical barriers to classroom adoption:

| Barrier | NodeGrade Solution |
|---------|-------------------|
| Instructor must write code to define a grading rubric | Visual drag-and-drop graph editor — no code required |
| Grading pipeline is fixed and not composable | Modular node library — WeightedScore, LLM, ConceptGrade, etc. |
| No real-time feedback loop for students | Socket.IO WebSocket delivers scores to StudentView in real time |

### 6.2 Node-Based Pipeline Execution

A grading pipeline is represented as a directed acyclic graph (DAG) of LiteGraph nodes. The execution model:

1. Instructor saves graph JSON to PostgreSQL
2. Student submits answer via WebSocket (`runGraph` event)
3. Backend loads graph from DB, injects answer into `AnswerInputNode`
4. LiteGraph executes the DAG in topological order (`runStep` loop)
5. `OutputNode` values are collected and emitted back as `graphOutput`

### 6.3 Starter Templates

Three pre-built pipelines ship with the platform:

| Template | Description | Nodes | Use case |
|----------|-------------|-------|---------|
| `starter.json` | Input nodes + OutputNode | 4 | Starting point for custom rubrics |
| `concept-grade.json` | Full ConceptGrade pipeline | 5 | CS concept-based grading |
| `llm-grader.json` | Prompt-engineering pipeline | 12 | Rubric-via-prompt grading |

---

## 7. Technical Validation

All claims in this paper are backed by automated tests:

| Layer | Test type | Tool | Coverage |
|-------|-----------|------|---------|
| Node library | Unit (registration) | Vitest | 6/6 node types |
| Backend API | Integration (Jest) | Jest | 40/40 tests, 11 suites |
| Grading pipeline | E2E Socket.IO | Custom CJS script | WeightedScore=82.5, LLM JSON ✓ |
| Platform | Browser E2E | Playwright | 27/27 tests, 8 suites, 7.2s |

A live **Validation Dashboard** at `/validation` re-runs all checks on demand and shows a staleness warning if test reports are older than 2 hours.

---

## 8. Statistical Significance

All SAG comparisons (ConceptGrade vs Pure LLM) tested with **Wilcoxon signed-rank test** (paired, non-parametric):

- SAG MAE improvement: **p < 0.001**
- SAG Pearson r (0.954): **95% CI [0.922, 0.974]**
- Adversarial MAE improvement: **p < 0.05**

---

## 9. Limitations and Threats to Validity

| Limitation | Impact | Mitigation / Future Work |
|-----------|--------|--------------------------|
| **SAG benchmark limited to CS domain** (Data Structures, OOP) | Results may not generalise to humanities, social sciences, or open-ended domains | Two expert KGs cover core CS curriculum; cross-domain ρ guard prevents over-penalisation when KG coverage is structurally low; extending to non-CS domains is a planned next step |
| **LLM provider dependency** (Gemini 2.5 Flash) | Results may vary with different LLM versions or providers | System is provider-agnostic via LiteLLM proxy; any OpenAI-compatible endpoint can be substituted; provider sensitivity analysis is planned |
| **LAG benchmark is internal, n=20** | Too small to support robust statistical inference; cannot rule out dataset-specific effects | Results are framed as a pilot/exploratory evaluation. A larger-scale LAG study (target n≥100 from multiple courses) is the primary planned future work. The SAG results on Mohler 2011 (n=120, public benchmark) provide the main external validity. |
| **KG-Only baseline is a single fixed calibration** | The linear coverage-to-grade mapping is one of many possible KG-only approaches | Future work: calibrated regression head trained on KG features; this may narrow the gap and make the LLM verifier's marginal contribution clearer |
| **Adversarial suite is synthetically generated** | Adversarial scenarios may not reflect realistic student writing strategies | 5 of 7 categories show CG wins; the two regressions (Prose Trap, Breadth Bluffer) involve near-perfect base-LLM performance (MAE < 0.2), limiting ceiling room for improvement |
| **User study not yet completed** | Instructor usability and student experience claims remain unvalidated | Platform and pipeline are technically validated; user study scheduled April–August 2026 (see `docs/user-study.md`) |

---

## 10. Limitations and Future Work

### 10.1 Primary Future Work

**LAG at scale:** The most important next step is extending the LAG evaluation to a larger, ideally public, essay benchmark. The current n=20 pilot demonstrates directional feasibility but cannot support the same statistical claims as the SAG evaluation.

**Cross-domain knowledge graphs:** The current KGs cover Data Structures (101 concepts) and OOP (62 concepts). Constructing KGs for further CS sub-domains (Algorithms, Computer Networks, Operating Systems) and non-CS disciplines is required to demonstrate breadth of applicability.

**Calibrated KG scoring:** Future work should explore replacing the linear coverage-to-grade mapping in the KG-Only baseline with a trained regression head. If a calibrated KG-Only scorer performs near ConceptGrade, it would suggest the LLM verifier's role can be reduced — lowering cost and latency.

**Automated KG construction:** Expert hand-curation does not scale. Semi-automated KG construction from course materials (lecture slides, textbooks) via LLM extraction is a necessary step for practical adoption.

### 10.2 Platform Future Work

**Multi-domain node library:** Expand beyond CS grading nodes to include rubric-based grading nodes for STEM problem sets and citation-aware grading nodes for essay-heavy disciplines.

**LTI 1.3 deep integration:** Current LTI support handles authentication; grade passback to LMS gradebook (Canvas, Moodle) is not yet implemented.

**Asynchronous batch grading:** The current architecture processes one answer at a time via WebSocket. For large cohorts (>100 students), a queue-backed batch processing mode is needed.

---

## Appendix A — SURE Ensemble Verifier: Persona System Prompts

*Source: `packages/concept-aware/conceptgrade/verifier.py`*

Layer 5 instantiates three independent LLM calls with different system prompts; the final score is the **median** of the three returned values. This stabilises variance that would result from any single persona.

### A.1 Short Answer Grading (SAG) Personas

| Persona | System Prompt |
|---------|--------------|
| **Meticulous** | "You are a strict academic grader. Penalise vague language, missing mechanisms, and incomplete explanations. Require precision. An answer missing any critical concept from the reference scores no higher than 3.5." |
| **Standard** | "You are a fair academic grader. Reward correct core ideas, penalise significant omissions or misconceptions. Use the reference answer as the definitive standard." |
| **Lenient** | "You are a supportive academic grader. Reward demonstrated understanding and effort. Only penalise factually wrong statements." |

### A.2 Long Answer Grading (LAG) Personas

The Lenient persona is replaced by **Analytical** for essay grading to prevent shallow breadth-bluffing from scoring well:

| Persona | System Prompt |
|---------|--------------|
| **Meticulous** | "You are a strict academic grader for long-form essays. Penalise shallow coverage, vague language, and missing mechanisms. A student who lists concepts without explaining them earns no more than 2.5/5." |
| **Standard** | "You are a fair academic grader for essays. Reward correct core ideas with clear explanations. Penalise significant omissions, misconceptions, and surface-level answers that lack depth. Breadth alone is not sufficient for a high score." |
| **Analytical** | "You are a depth-focused academic grader. Evaluate whether the student demonstrates genuine understanding of mechanisms and relationships, not just terminology recall. An essay that names concepts but does not explain how or why they work scores no higher than 3.0/5. Reserve 4.0+ for answers showing causal understanding." |

> **Design note:** The Lenient → Analytical substitution is deliberate. For short answers, a lenient anchor is needed to prevent over-penalising incomplete but correct answers. For essays, leniency would reward breadth-bluffing; the Analytical persona instead enforces depth-of-explanation as the high-score criterion.

---

## Appendix B — Misconception Taxonomy (Layer 4)

*Source: `packages/concept-aware/misconception_detection/detector.py`*

The taxonomy contains **17 entries** across 6 Data Structures sub-domains. Severity levels: **CRITICAL** (factual inversion that would produce wrong code or reasoning), **MODERATE** (incomplete understanding that degrades reliability), **MINOR** (imprecision that does not cause practical errors in most contexts).

Distribution: 5 CRITICAL · 8 MODERATE · 4 MINOR

### Representative entries (full table)

| Code | Category | Description | Severity |
|------|----------|-------------|----------|
| DS-LINK-01 | Linked Lists | Confusing array indices with pointer-based access — claims O(1) index access | **CRITICAL** |
| DS-LINK-02 | Linked Lists | Believing linked list nodes are stored contiguously in memory | **CRITICAL** |
| DS-LINK-03 | Linked Lists | Thinking insertion is always O(1) regardless of position | MODERATE |
| DS-STACK-01 | Stacks & Queues | Confusing LIFO (stack) with FIFO (queue) | **CRITICAL** |
| DS-STACK-02 | Stacks & Queues | Thinking stacks can only be implemented with arrays | MINOR |
| DS-TREE-01 | Trees | Assuming all binary trees have the BST ordering property | **CRITICAL** |
| DS-TREE-02 | Trees | Confusing tree height with node count | MODERATE |
| DS-TREE-03 | Trees | Claiming BST operations are always O(log n) — ignores degenerate case | MODERATE |
| DS-HASH-01 | Hash Tables | Claiming hash table operations are always O(1) — ignores worst case | MODERATE |
| DS-HASH-02 | Hash Tables | Confusing hash functions with cryptographic encryption | MINOR |
| DS-SORT-01 | Sorting | Believing quicksort is always faster than merge sort | MODERATE |
| DS-SORT-02 | Sorting | Treating all O(n log n) sorts as equally fast in practice | MINOR |
| DS-GRAPH-01 | Graphs | Claiming BFS finds shortest paths in weighted graphs | MODERATE |
| DS-GRAPH-02 | Graphs | Swapping BFS/DFS data structures (queue vs stack) | **CRITICAL** |
| DS-COMP-01 | Complexity | Claiming Big-O describes the best case | MODERATE |
| DS-COMP-02 | Complexity | Claiming O(n log n) is always faster than O(n²) — ignores small-n constants | MINOR |

> **Note:** The taxonomy currently covers Data Structures only. Extending it to OOP misconceptions (e.g., `OOP-INH-01` — conflating inheritance with composition) and additional CS sub-domains is part of the cross-domain future work described in Section 10.1.
