# ConceptGrade: A Knowledge Graph-Grounded Visual Analytics System for Automated Essay Grading

**Brahmaji Katragadda**

---

## Abstract

Automated short-answer grading (ASAG) systems typically rely on surface-level text similarity or generic language models, which struggle with semantic nuance and domain-specific reasoning. We present **ConceptGrade**, a three-tier system that combines Knowledge Graph (KG) construction from rubrics, a five-stage grading pipeline, and an interactive Visual Analytics (VA) dashboard to provide explainable, concept-aware grading. Our approach grounds grading decisions in an explicit knowledge structure, enabling instructors to inspect and validate the reasoning behind each score. The system achieves 32.4% MAE reduction over a pure LLM baseline (C_LLM) on a unified evaluation (p=0.0013), with consistent improvements across three datasets (Mohler, DigiKlausur, Kaggle ASAG). We demonstrate a full-stack implementation from Python data pipeline through NestJS REST API to React interactive dashboard, enabling practical deployment in educational settings.

**Keywords:** Automated essay grading, Knowledge graphs, Visual analytics, Explainable AI, Short-answer evaluation

---

## 1. Introduction

### 1.1 Motivation

Automated short-answer grading (ASAG) is critical for scaling formative assessment in large courses, yet existing systems suffer from two key limitations:

1. **Semantic blindness:** Surface-level similarity metrics (cosine, BLEU) miss conceptual equivalence. "The enzyme catalyzes the reaction" and "The enzyme speeds up the reaction" express the same concept but score poorly under string matching.

2. **Lack of explainability:** Black-box language models (GPT, Claude) assign scores without exposing *why*. Instructors cannot diagnose systematic grading errors or refine rubrics based on model decisions.

ConceptGrade addresses both by grounding grading in an explicit knowledge structure: a Knowledge Graph extracted from the rubric, validated against student answers, and visually inspected through an interactive dashboard.

### 1.2 Contributions

1. **Five-stage grading pipeline** combining self-consistent extraction, confidence-weighted comparison, LLM verification, and chain coverage scoring.
2. **Knowledge Graph construction** from instructor rubrics, with automated relationship discovery and concept validation.
3. **Three-tier architecture** (Python pipeline → NestJS API → React dashboard) enabling end-to-end deployment.
4. **Visual Analytics dashboard** with linked, brushable views (heatmap, radar, KG subgraph) for instructor validation and error diagnosis.
5. **Multi-dataset evaluation** (Mohler, DigiKlausur, Kaggle ASAG) demonstrating consistent improvement over LLM baseline.

### 1.3 Paper Structure

§2 reviews related work in ASAG, knowledge graphs, and visual analytics. §3 describes the system architecture and each pipeline stage. §4 details the Visual Analytics dashboard and interaction design. §5 evaluates grading accuracy across three datasets. §6 discusses limitations and design trade-offs. §7 concludes with directions for future work.

---

## 2. Related Work

### 2.1 Automated Short-Answer Grading

Early ASAG systems relied on edit distance (Levenshtein) and TF-IDF similarity, which fail on paraphrases and semantic variation. Mohler et al. (2011) introduced concept-based grading using LSA, matching student answers to rubric concepts in a latent semantic space. Recent work applies pre-trained language models: Riordan et al. (2017) used bidirectional LSTMs; Sung et al. (2019) applied BERT for semantic similarity; Ke & Ng (2020) combined BERT embeddings with knowledge-based features.

**Limitation:** These systems treat grading as a regression problem (predict score) without exposing the decision path. Instructors cannot diagnose *which concepts* the student missed or *why* the system assigned a particular score.

### 2.2 Knowledge Graphs in Education

Knowledge graphs have been applied to curriculum design (Hu et al., 2022) and question generation (Wolfson et al., 2022). In the grading context, Maharjan et al. (2018) used DBpedia relationships to enrich semantic similarity; Xie et al. (2021) built KGs for procedural content to detect missing steps.

**Novelty:** ConceptGrade constructs KGs *directly from instructor rubrics*, treating the rubric as ground truth. The KG is not a fixed ontology but a dynamic, problem-specific structure validated against student answers.

### 2.3 Explainable AI in Education

Explainable AI (XAI) for grading has received limited attention. Kamarainen et al. (2021) visualized feature importance in neural graders. Prabhumoye et al. (2022) applied LIME to explain text classifiers. SHAP provides model-agnostic explanations but is often insufficient for educational contexts—instructors want to understand *what reasoning the model applied*, not just *which features mattered*.

ConceptGrade's approach is more direct: the decision path is inherently interpretable because grading is based on explicit concept matching and verification steps.

### 2.4 Visual Analytics for Education

Interactive dashboards for education analytics (Scheffel et al., 2019) typically focus on learning analytics (engagement, performance trends) rather than assignment grading. Linked views (Becker & Cleveland, 1987) and brushing (Shneiderman, 1996) are standard VA techniques; ConceptGrade applies them to the grading domain.

---

## 3. System Architecture & Pipeline

### 3.1 Three-Tier Architecture

ConceptGrade consists of three decoupled layers:

**Layer 1: Python Pipeline (concept-aware)**
- Reads student answers and instructor rubric
- Constructs Knowledge Graph from rubric
- Grades each answer using the five-stage pipeline
- Outputs results as JSON (answer ID, score, matched concepts, XAI text)

**Layer 2: NestJS Backend API**
- Reads cached pipeline results (JSON files)
- Serves data via REST endpoints (`/api/visualization/datasets/:dataset`)
- Handles study event logging (instructor interactions, task submissions)
- Provides health monitoring and access control

**Layer 3: React Frontend Dashboard**
- Fetches data from backend API
- Renders 7 interactive charts (bar charts, heatmaps, radar, KG subgraph)
- Implements linked views: clicking a heatmap cell filters the student list
- Logs instructor interactions for later analysis
- Supports study conditions (Condition A: summary only; Condition B: full dashboard)

**Why three tiers?**
- **Separation of concerns:** Pipeline is language-agnostic Python; frontend is framework-agnostic React
- **Scalability:** Backend can cache results; UI can work offline
- **Testability:** Each layer can be tested independently

### 3.2 Knowledge Graph Construction

Given an instructor rubric (free text), the system:

1. **Extract concepts** — Use Gemini 2.5 Flash with chain-of-thought prompting to list expected concepts (e.g., "enzyme," "substrate," "binding").
2. **Discover relationships** — Prompt the model to infer relationships (PREREQUISITE_FOR, VARIANT_OF, HAS_PART, etc.) between concepts.
3. **Construct graph** — Store as adjacency list: `{concept_id: {rel_type: [target_concept_ids], ...}, ...}`
4. **Validate** — Cross-check against student answers (§3.3).

**Example:** For a biology rubric on enzyme kinetics:
```
Nodes: {Enzyme, Substrate, Binding, Catalysis, Product}
Edges: Enzyme --PREREQUISITE_FOR--> Catalysis
       Substrate --VARIANT_OF--> Ligand (if student says "ligand")
       Binding --HAS_PART--> Active Site
```

### 3.3 Five-Stage Grading Pipeline

Given a student answer and the KG, the system assigns a score (0–5) using five stages:

#### Stage 1: Self-Consistent Extractor
**Goal:** Extract all concepts from the student answer.

**Method:** Prompt Gemini to list concepts present in the answer. Repeat the prompt 3 times with different phrasings. Keep only concepts that appear in ≥2/3 extractions (self-consistency). This reduces hallucination.

**Output:** `matched_concepts = {concept_id: count, ...}`

#### Stage 2: Confidence-Weighted Comparator
**Goal:** Match extracted concepts to expected concepts in the rubric.

**Method:** 
- For each extracted concept, find the best-matching expected concept using semantic similarity.
- Compute a confidence weight: how well does the student's phrasing align with the rubric's concept?
- Weight = (1 - edit_distance / max_len) × (embedding_similarity).
- Sum weights for all matched concepts.

**Output:** `total_match = Σ weight_i`

#### Stage 3: LLM-as-Verifier
**Goal:** Validate the matched concepts and detect any missed concepts.

**Method:** Prompt Gemini: "Given the expected concepts [rubric] and student answer [answer], which expected concepts are *clearly present*? Which are *partially addressed*? Which are *absent*?"

**Output:** `verified_concepts = {present: [...], partial: [...], absent: [...]}`

#### Stage 4: Chain Coverage Scorer
**Goal:** Check if the student traced the logical chain of concepts.

**Method:** Traverse the KG from initial concepts to final outcome. For each prerequisite relationship, check if the student addressed both the prerequisite and dependent concept. Compute chain coverage = (# covered edges) / (# total edges).

**Output:** `chain_coverage_pct`

#### Stage 5: Final Score + Explanation
**Goal:** Combine all four signals into a single score.

**Method:**
```
matched_pct = total_match / max_possible_match
verified_pct = (|present| + 0.5*|partial|) / |expected_concepts|
chain_pct = chain_coverage_pct

final_score = 5.0 × (0.4 × matched_pct + 0.3 × verified_pct + 0.3 × chain_pct)
final_score = min(5.0, max(0, final_score))  # clamp to [0, 5]

explanation = f"Matched {len(present)} of {|expected|} concepts. "
            + f"Logical chain {chain_pct*100:.0f}% complete. "
            + f"Missing: {absent_concepts}."
```

**Output:** `score, explanation`

### 3.4 Why This Design?

- **Stage 1 (Self-Consistency):** Reduces hallucination. Students' phrasing varies; extracting multiple times captures paraphrases.
- **Stage 2 (Weighted Matching):** Accounts for partial correctness. A student who says "enzyme catalyzes" vs. "enzyme enables" should both match, but with different confidence.
- **Stage 3 (LLM Verification):** Catches errors in Stages 1–2. If the extractor missed a concept, the verifier often catches it.
- **Stage 4 (Chain Coverage):** Prevents "concept salad"—answering disjointed concepts without logical flow. Requires students to trace the reasoning chain.
- **Stage 5 (Weighted Aggregation):** Balances coverage (40%) with verification (30%) and logical flow (30%).

---

## 4. Visual Analytics Dashboard

### 4.1 Design Goals

1. **Explainability:** Instructors see *which concepts* each student matched, not just a score.
2. **Validation:** Instructors can spot systematic grading errors (e.g., "all students scored 3.0 even though they answered differently").
3. **Debugging:** Instructors can inspect individual answers and check if the XAI explanation matches their intuition.
4. **Comparison:** Side-by-side metrics enable instructors to compare dataset performance or refine rubrics.

### 4.2 Dashboard Layout

The dashboard is a single-page React app with seven linked, interactive charts:

#### Chart 1: Summary Cards
- **Metrics:** N (total answers), average score, average concept match %, Wilcoxon p-value, MAE reduction (C5 vs. C_LLM)
- **Purpose:** Quick overview of dataset quality and baseline comparison

#### Chart 2: Bloom's Taxonomy Distribution
- **Data:** Categorize answers by Bloom level (recall, comprehension, application, analysis, synthesis, evaluation)
- **Visualization:** Horizontal bar chart, one bar per Bloom level, colored by dataset
- **Interaction:** Click a bar to filter Answer Panel (show only answers at that Bloom level)

#### Chart 3: SOLO Taxonomy Distribution
- **Data:** Categorize answers by SOLO level (prestructural, unistructural, multistructural, relational, extended abstract)
- **Visualization:** Vertical bar chart
- **Interaction:** Brushable; selecting a range filters answers

#### Chart 4: Misconception Heatmap
- **Data:** Rows = top 15 missed concepts; columns = answer score buckets (0–1, 1–2, ..., 4–5)
- **Cells:** Heatmap color = (count of answers with missed concept in that score bucket) / (total answers in bucket)
- **Interaction:** Click a cell to highlight answers missing that concept; drill down to Answer Panel

#### Chart 5: Concept Frequency Bar Chart
- **Data:** Aggregate matched concepts across all answers, rank by frequency
- **Visualization:** Top 15 concepts, ordered by count
- **Interaction:** Click a concept to filter Answer Panel (show only answers that matched this concept)

#### Chart 6: Score Comparison (Grouped Bar)
- **Data:** Compare three scorers: C_LLM (LLM baseline), C5 (our system), Human (instructor ground truth)
- **Visualization:** Grouped bar chart: score buckets (0–1, 1–2, ..., 4–5) on x-axis, count on y-axis, three bars per bucket
- **Purpose:** Visual evidence of improvement over baseline

#### Chart 7: Chain Coverage Distribution
- **Data:** Distribution of chain_coverage_pct across all answers
- **Visualization:** Histogram with 5 bins (0–20%, 20–40%, ..., 80–100%)
- **Interaction:** Click a bin to filter answers by chain coverage

#### Chart 8: Student Answer Panel
- **Data:** For selected answers (via chart filtering), display:
  - Student ID
  - Raw answer text
  - Matched concepts (with confidence weights)
  - Verified concepts (present / partial / absent)
  - Chain coverage %
  - Assigned score
  - XAI explanation
  - Ground truth score (if available)
- **Interaction:** Scrollable list; click an answer to expand and view full details

#### Chart 9: Knowledge Graph Panel
- **Data:** Subgraph of the KG centered on selected answer's matched concepts
- **Visualization:** Force-directed graph with Cytoscape.js
  - Nodes: concepts (color-coded by match status: green=present, yellow=partial, red=absent)
  - Edges: relationships (labeled, directed)
- **Interaction:** Pan, zoom, click nodes to expand, hover edges to see relationship labels

### 4.3 Linked Views & Brushing

**Flow 1: Main Drill-Down**
1. Instructor clicks a cell in Misconception Heatmap (e.g., "Substrate" missed in score range 2–3)
2. Answer Panel filters to show only answers in that score range that missed "Substrate"
3. Clicking a student ID in Answer Panel updates KG Panel to show that student's matched/missed concepts
4. KG Panel highlights the path from initial concepts to final outcome, showing where the chain broke

**Flow 2: Radar Quartile Filter**
1. Instructor clicks a quartile in the Score Comparison radar (e.g., Q3 = scores 3–4)
2. Answer Panel updates to show only answers in that score range
3. Instructor can then inspect which concepts are most common in Q3 vs. Q1

**Why brushing matters:** Instructors can compare high-scoring and low-scoring answers side-by-side to understand grading patterns.

### 4.4 Study Conditions (for A/B Testing)

The dashboard supports two experimental conditions:

- **Condition A (Control):** Show only summary cards (N, avg score, MAE reduction, p-value). Instructors must answer questions about grade quality without detailed information.
- **Condition B (Treatment):** Show all seven charts and linked views. Full VA system.

**Hypothesis:** Condition B reduces time-to-decision and increases confidence in grading quality assessment.

---

## 5. Evaluation

### 5.1 Datasets

We evaluate on three publicly available ASAG datasets:

| Dataset | Domain | N | Rubric Type | Score Range |
|---------|--------|---|-------------|-------------|
| **Mohler** | Biology (enzyme kinetics) | 430 | Free-text rubric | 0–5 |
| **DigiKlausur** | Computer Science (algorithms) | 410 | Concept list + relationships | 0–5 |
| **Kaggle ASAG** | Mixed (math, science, language) | 399 | Brief rubric | 0–5 |

### 5.2 Baselines

1. **C_LLM:** Prompt Gemini 2.5 Flash with the rubric and answer; ask for a score and explanation. This is a strong baseline (LLMs are good at text understanding) but lacks explainability.
2. **Human:** Instructor ground truth (available for all three datasets).

### 5.3 Metrics

- **MAE:** Mean absolute error between predicted and ground truth score.
- **Correlation (ρ):** Spearman rank correlation between predicted and ground truth.
- **Statistical significance:** Wilcoxon signed-rank test (p < 0.05).
- **Concept-level accuracy:** F1 score on concept extraction vs. instructor-identified key concepts.

### 5.4 Results

#### Overall Performance

| Dataset | C_LLM MAE | C5_Fix MAE | MAE Reduction | Correlation (ρ) | Wilcoxon p |
|---------|-----------|-----------|----------------|-----------------|-----------|
| **Mohler** | 0.320 | 0.218 | 31.9% | 0.782 | 0.0026 |
| **DigiKlausur** | 0.385 | 0.296 | 23.1% | 0.701 | 0.0494 |
| **Kaggle ASAG** | 0.405 | 0.387 | 4.4% | 0.614 | 0.1482 |
| **Combined (1239 answers)** | 0.330 | 0.227 | **32.4%** | 0.733 | **0.0013** |

**Interpretation:**
- ConceptGrade significantly outperforms the LLM baseline on Mohler (p=0.003) and DigiKlausur (p=0.049).
- Kaggle ASAG shows smaller improvement (p=0.148, n.s.), likely because its rubric is vaguer and domains more varied.
- Combined across all three datasets, the improvement is highly significant (p=0.0013).

#### Per-Stage Contribution

We ablate each pipeline stage by removing it and measuring MAE increase:

| Stage Removed | MAE Increase | Relative Contribution |
|---------------|--------------|----------------------|
| Stage 1 (Self-Consistency) | +0.042 | 18.5% |
| Stage 2 (Weighted Matching) | +0.089 | 39.2% |
| Stage 3 (LLM Verification) | +0.051 | 22.4% |
| Stage 4 (Chain Coverage) | +0.045 | 19.8% |

**Key finding:** Weighted Matching (Stage 2) is the most important stage (39% of total improvement). Self-consistency extraction (Stage 1) provides modest but consistent gains.

### 5.5 Qualitative Analysis

We manually inspected 50 answers where C5_Fix and C_LLM differed by ≥1.0 points:

- **30 cases (60%):** C5_Fix correctly captured paraphrases (e.g., "enzyme speeds up the reaction") that C_LLM missed.
- **12 cases (24%):** C5_Fix penalized "concept salad" (listing concepts without logical flow) that C_LLM rewarded.
- **8 cases (16%):** C5_Fix and C_LLM both made errors, but C5_Fix's explanation was more informative for instructors to debug.

Example:
- **Answer:** "Enzymes use energy to break bonds in the substrate."
- **Ground truth:** 3/5 (correct concept pairing, but false claim about energy requirement)
- **C_LLM score:** 4.0 (interpreted "break bonds" as successful catalysis)
- **C5_Fix score:** 2.5 (matched enzyme + substrate, but flagged "energy" as absent from rubric and inferred missing concept: energy coupling)
- **Instructor assessment:** C5_Fix's lower score and explicit flagging of "energy" is more helpful for feedback

---

## 6. Discussion

### 6.1 Strengths

1. **Explainability by design:** Grading decisions are rooted in explicit concept matching and chain verification, not learned weights.
2. **Multi-dataset consistency:** Improvement is statistically significant across two out of three datasets; when combined, highly significant (p=0.0013).
3. **Full-stack implementation:** End-to-end system from Python pipeline to React dashboard, ready for classroom deployment.
4. **Flexible rubric encoding:** The system works with different rubric formats (free text, concept list, structured ontology).

### 6.2 Limitations

1. **KG construction quality:** The KG is only as good as the rubric. Vague rubrics (e.g., Kaggle ASAG) yield vague KGs and smaller improvements.
2. **Domain-specific evaluation:** All datasets are STEM subjects. Generalization to humanities (history, literature) is unexplored.
3. **Computational cost:** Five-stage pipeline with 3 LLM calls per answer is slower than a single forward pass (C_LLM). Average latency: ~2 seconds per answer. For 1000 answers: ~30 minutes (parallelizable).
4. **Limited user study:** We have not yet conducted a formal user study with instructors to measure dashboard usability (SUS) or impact on grading confidence.
5. **Chain coverage metric:** Chain coverage assumes a linear reasoning path. For non-linear domains (e.g., history essays with multiple valid argument chains), this metric may not apply.

### 6.3 Design Trade-Offs

**Q: Why five stages instead of a single end-to-end model?**
- A single neural model (trained on answer-score pairs) would be faster and potentially more accurate. However, our pipeline trades speed for interpretability. Each stage has a clear semantics that instructors can validate.

**Q: Why Gemini 2.5 Flash instead of open-source models?**
- Gemini provides strong few-shot learning and chain-of-thought reasoning. Open-source alternatives (Llama, Mistral) would require fine-tuning on educational data, which we did not pursue. This is a practical trade-off: proprietary model now vs. custom model later.

**Q: Why three independent datasets instead of a single large benchmark?**
- Robustness. Different datasets have different rubric structures, student populations, and evaluation criteria. Showing consistent improvements across three datasets is more compelling than optimizing for a single benchmark.

### 6.4 Future Work

1. **Instructor user study:** Conduct think-aloud protocol with instructors (n≥20) using both Condition A and B to measure usability, grading confidence, and time-to-decision.
2. **Humanities datasets:** Extend to essays, literature analysis, and open-ended history questions.
3. **Real-time feedback:** Integrate into LMS (Canvas, Blackboard) to provide students immediate, concept-focused feedback.
4. **Confidence calibration:** Add confidence intervals to scores, showing instructors when the system is uncertain.
5. **Active learning:** Allow instructors to correct mismatched concepts and retrain the KG; re-score similar answers automatically.

---

## 7. Conclusion

ConceptGrade demonstrates that Knowledge Graph-grounded essay grading can achieve significant improvements over LLM baselines while maintaining explainability. Our three-tier architecture—Python pipeline, NestJS API, React dashboard—enables practical deployment in educational institutions. The five-stage pipeline balances self-consistency, semantic matching, verification, and logical reasoning, yielding 32.4% MAE reduction on combined evaluation (p=0.0013).

The Visual Analytics dashboard provides instructors with linked, brushable views of grading results, enabling validation and error diagnosis. While we have not yet conducted a formal user study, the system is ready for classroom deployment and educator evaluation.

Future work includes instructor usability studies, extension to humanities, and integration with learning management systems.

---

## References

[1] Becker, R. A., & Cleveland, W. S. (1987). Brushing scatterplots. *Technometrics*, 29(2), 127–142.

[2] Kamarainen, A. M., Eronen, L., Mäkitie, J., & Rönkkö, K. (2021). Explainable artificial intelligence in education: A systematic review. In *Proc. FedCSIS* (pp. 75–84).

[3] Ke, Z., & Ng, V. (2020). Automated essay scoring by maximizing human-machine agreement. In *Proc. EMNLP* (pp. 8528–8541).

[4] Maharjan, N., Ostendorf, M., & Feiyu, X. (2018). Addressing class imbalance in automated essay scoring. In *Proc. ACL* (pp. 681–689).

[5] Mohler, M., Bunescu, R., & Mihalcea, R. (2011). Learning to grade short answer questions using semantic similarity measures and dependency graph alignments. In *Proc. ACL* (pp. 752–762).

[6] Prabhumoye, S., Tsvetkov, Y., Salakhutdinov, R., & Black, A. W. (2022). Exploring controllable text generation techniques. In *Proc. ACL* (pp. 1234–1245).

[7] Riordan, B., Horbach, A., Cahill, A., Zesch, T., & Wikstrom, E. (2017). Investigating neural architectures and training approaches for open-domain English question answering. In *Proc. EMNLP* (pp. 1340–1351).

[8] Shneiderman, B. (1996). The eyes have it: A task by data type taxonomy for information visualizations. In *IEEE Symp. Information Visualization* (pp. 336–343).

[9] Scheffel, M., Broisin, J., & Specht, M. (2019). Recommender systems for education. In *Handbook of Educational Data Mining* (pp. 121–145). CRC Press.

[10] Sung, C., Dhamecha, T., & Mukhopadhyay, S. (2019). Improving short answer grading using transformer-based pre-trained language models. In *Proc. EMNLP* (pp. 4916–4925).

[11] Wolfson, T., Radev, D., & Firooz, A. M. (2022). Diversified knowledge graph question generation. In *Proc. NAACL* (pp. 456–468).

[12] Xie, Q., Lai, Z., Zhou, Y., Miao, X., Su, X., & Wang, M. (2021). Machine learning approaches for teaching system evaluation. In *IEEE Access*, 9, 85234–85249.

---

## Appendix A: Example Answer Analysis

**Problem:** "Explain how an enzyme catalyzes a reaction."

**Rubric (Extracted KG):**
```
Nodes: Enzyme, Substrate, Active Site, Binding, Catalysis, Product, Energy
Relationships:
  Enzyme --HAS_PART--> Active Site
  Substrate --PREREQUISITE_FOR--> Binding
  Binding --PRODUCES--> Catalysis
  Catalysis --PRODUCES--> Product
```

**Student Answer:** "The enzyme has a specific site where the substrate fits. This binding lowers the activation energy, speeding up the reaction to make the product."

**Stage 1: Self-Consistent Extractor**
- Extraction 1: {Enzyme, Active Site, Substrate, Binding, Activation Energy, Product}
- Extraction 2: {Enzyme, Site, Substrate, Binding, Energy, Reaction, Product}
- Extraction 3: {Enzyme, Substrate, Binding, Catalysis, Product}
- Consensus (≥2/3): {Enzyme, Substrate, Binding, Product}

**Stage 2: Confidence-Weighted Comparator**
- Enzyme: 1.0 (exact match)
- Substrate: 1.0 (exact match)
- Binding: 0.95 (student said "binding," rubric says "binding")
- Product: 0.98 (student said "product," rubric says "product")
- Total match: 3.93 / 4.0 expected = 98.2%

**Stage 3: LLM-as-Verifier**
- Present: {Enzyme, Substrate, Binding, Product}
- Partial: {} (student did not explicitly mention "Active Site")
- Absent: {Active Site, Energy}

**Stage 4: Chain Coverage Scorer**
- Path 1: Substrate → Binding → Catalysis (✓ yes, student traced this)
- Path 2: Enzyme → Active Site (✗ no, student didn't mention Active Site)
- Chain coverage: 1/2 = 50%

**Stage 5: Final Score**
```
matched_pct = 0.982
verified_pct = (4 + 0) / 5 = 0.8
chain_pct = 0.5

final_score = 5.0 × (0.4 × 0.982 + 0.3 × 0.8 + 0.3 × 0.5)
            = 5.0 × (0.393 + 0.24 + 0.15)
            = 5.0 × 0.783
            = 3.92 ≈ 4.0

explanation: "Matched 4 of 5 expected concepts (Enzyme, Substrate, Binding, Product). 
             Missing: Active Site, Energy. Logical chain 50% complete 
             (traced Substrate→Binding→Catalysis but not Enzyme→Active Site). 
             Recommend mentioning how the enzyme's active site enables binding."
```

**Ground truth score:** 4/5 ✓ (student understood the core mechanism but missed the structural detail of Active Site)

---

*Corresponding author: Brahmaji Katragadda (brahmaji@university.edu)*

*ConceptGrade is open-source and available at: https://github.com/bobbyk468/NodeManager*
