# Research: Knowledge Graphs & Misconception Detection in Educational Assessment

**Compiled:** March 20, 2026  
**Purpose:** Deep research synthesis for an intelligent student assessment system

---

## Table of Contents

1. [Topic 1: Knowledge Graphs in Educational Assessment](#topic-1-knowledge-graphs-in-educational-assessment)
2. [Topic 2: Concept Maps for Assessment](#topic-2-concept-maps-for-assessment)
3. [Topic 3: Misconception Detection](#topic-3-misconception-detection)
4. [Topic 4: Concept Understanding vs Surface Matching](#topic-4-concept-understanding-vs-surface-matching)
5. [Cross-Cutting Themes & Synthesis](#cross-cutting-themes--synthesis)
6. [Research Gaps & Future Directions](#research-gaps--future-directions)

---

## Topic 1: Knowledge Graphs in Educational Assessment

### 1.1 Conceptual Foundations: How Knowledge Graphs Represent Domain Relationships

A **knowledge graph** is a structured representation of entities, concepts, and their semantic relationships, typically expressed as nodes (concepts/entities) and directed edges (relationships). The core components are:

- **Nodes** — individual concepts (e.g., "photosynthesis," "chloroplast," "light reaction")
- **Edges** — typed relationships between concepts (e.g., `is_part_of`, `requires`, `produces`, `prerequisite_for`)
- **Properties** — metadata attached to nodes or edges (e.g., difficulty level, learning objective ID)

In educational contexts, knowledge graphs model **prerequisite relationships** (what must be understood before a new concept), **hierarchical structures** (broad topic → subtopic → fact), and **lateral associations** (cross-domain connections). These relationships encode the structural logic of a curriculum and can formalize what "mastery" looks like for a given domain.

**Ontologies** serve as the formal schema for educational knowledge graphs. As described by [Ontotext's foundational guide](https://www.ontotext.com/knowledgehub/fundamentals/what-is-a-knowledge-graph/), an ontology defines the vocabulary of entity types, property types, and logical constraints—acting as the "data schema" and a formal contract for how knowledge is organized. In educational settings, an ontology might define classes such as `LearningObjective`, `Concept`, `Prerequisite`, `MisconceptionCategory`, and relationships such as `conceptBelongsToObjective`, `isPrerequisiteOf`, `studentDemonstratesUnderstandingOf`.

**MOOC-scale construction** has been demonstrated by [Jifan Yu et al. (2021) in the Journal of Computer Science and Technology](https://jcst.ict.ac.cn/fileup/1000-9000/PDF/2021-5-18-0328.pdf), who built an educational knowledge graph from MOOC platforms (Coursera, EDX, XuetangX, ICourse) containing 9,312 courses, 604 universities, 18,671 instructors, and 24,188 concepts linked to Wikipedia entries. Their pipeline followed a top-down approach: first building the ontology, then acquiring knowledge through entity extraction, entity disambiguation, and concept linking, and finally inferring prerequisite relations from MOOC descriptions.

**Curriculum structure** can itself be modeled as a knowledge graph. [Tuzón, Salvà & Fernández-Gracia (2025) in arXiv](https://arxiv.org/html/2412.15929v1) applied complex network analysis to Physics and Mathematics curricula, discovering modularity that mirrored but differed from the original curriculum layout—revealing hidden interdisciplinary connections and key "hub" concepts not obvious from textbook chapter organization.

---

### 1.2 Knowledge Graph Construction from Educational Content

Construction pipelines typically follow these steps:

1. **Knowledge Modeling (Ontology Design)** — Define entity types and relationship types relevant to the domain
2. **Knowledge Acquisition** — Extract concept mentions, prerequisite relations, and domain entities from textbooks, course materials, or lecture transcripts using NLP (NER, relation extraction)
3. **Knowledge Fusion** — Disambiguate entities (linking "Newton's Second Law" in chapter 3 to the same concept in chapter 7), resolve synonymy, and integrate multiple sources
4. **Knowledge Storage** — Persist the graph in a graph database (e.g., Neo4j) with query capability

The [Graphusion framework (Yang et al., 2024)](https://arxiv.org/html/2407.10794v1) demonstrates LLM-assisted knowledge graph construction for NLP education, using a global perspective to extract knowledge triplets—capturing not just local sentence-level relations but cross-document semantic connections. Their system also introduced TutorQA, a benchmark with 1,200 QA pairs for evaluating graph-based educational reasoning.

**Automated ontology construction** for course knowledge graphs has been explored in IEEE proceedings. A [2024 IEEE paper](https://ieeexplore.ieee.org/document/10857583/) proposed a method based on dependency relationships between knowledge points, constructing course knowledge graphs where prerequisite dependencies drive the graph structure.

---

### 1.3 Flagship Paper: Zhang (2025) — AI Writing Assessment with Knowledge Graphs

**Citation:** Zhang, C. (2025). Optimising AI writing assessment using feedback and knowledge graph integration. *PeerJ Computer Science*, article cs-2893. DOI: [10.7717/peerj-cs.2893](https://peerj.com/articles/cs-2893)

**Authors:** Ci Zhang

**Year:** 2025

**Key Methodology:**
- **Dynamic relational knowledge graph** where nodes represent writing concepts (grammar, coherence, vocabulary) and edges represent semantic/thematic relationships
- **BERT** (fine-tuned for writing quality assessment): bidirectional transformer, pre-trained on Masked Language Modeling and Next Sentence Prediction
- **GPT-3** (175B parameters): generative scoring with RLHF fine-tuning
- **Graph Neural Networks (GNNs)**: 3-layer architecture (hidden units: 128, ReLU activation, dropout 0.2) that performs message-passing over the knowledge graph to boost understanding of complex semantic relationships between writing concepts
- **Iterative feedback loop**: system collects user feedback, adjusts future feedback based on historical data and changes in writing behavior over time
- Dataset: research papers (40%), blog posts (30%), business documents (30%); 100 participants across beginner/intermediate/advanced proficiency levels

**Key Findings / Metrics:**

| Model | Accuracy | Precision | Recall | F1-Score |
|-------|----------|-----------|--------|----------|
| Rule-based grammar checker | 75.0% | 70.0% | 65.0% | 67.5% |
| Logistic Regression | 80.0% | 75.0% | 70.0% | 72.5% |
| SVM | 85.0% | 80.0% | 75.0% | 77.5% |
| BERT | 96.5% | 95.8% | 96.2% | 96.0% |
| **GNN** | **97.2%** | **96.5%** | **97.0%** | **96.7%** |
| GPT-3 | 95.6% | 95.2% | 95.5% | 95.4% |

- GNN achieved highest performance overall, leveraging the knowledge graph structure
- BERT vs. GNN: p=0.01, Cohen's d=1.22 (large effect)
- 80% of users rated the system "Very Useful" or "Somewhat Useful"
- Grammar accounted for 40% of feature importance; coherence 30%

**Limitations:**
- Dataset biases: genre (academic-heavy), cultural (mostly English), demographic
- GPT-3 processing time 2× longer than BERT
- No explicit generalizability testing across non-English writing contexts
- Evaluation primarily user-satisfaction based rather than independent expert scoring benchmarks

**Relevance to Student Assessment:** This paper demonstrates that a knowledge graph encoding concept relationships (here: writing concepts) can meaningfully improve an AI assessor's ability to provide contextually grounded, personalized feedback—outperforming both pure language models and traditional classifiers.

---

### 1.4 Graph Neural Networks for Concept Dependencies

GNNs are particularly valuable in educational assessment because they can model the **structural dependencies** between concepts—not just whether a student knows an isolated fact, but whether their understanding of upstream prerequisites is consistent with their performance on downstream concepts.

**Heterogeneous GNNs for Prerequisite Relations:** [Jia et al. (2021, NAACL)](https://www.aclweb.org/anthology/2021.naacl-main.164.pdf) proposed CPRL (Concept Prerequisite Relation Learning), combining concept representations from a heterogeneous graph with pairwise concept features. Their system learned prerequisite relationships from weakly supervised data, demonstrating that graph structure enables detection of implicit prerequisites not explicit in any single document.

**Curriculum-Aware Cognitive Diagnosis:** [Fu & Fang (2025)](https://www.mdpi.com/2078-2489/16/11/996) proposed CA-GNCD, integrating curriculum prerequisite priors into graph-based neural modeling. On benchmarks (ASSISTments2017, EdNet-KT1, Eedi), the framework improved AUC by more than 4.5 percentage points over classical probabilistic and psychometric baselines, demonstrating that explicitly encoding curriculum structure into GNN models enhances both accuracy and interpretability.

**Concept Map Analysis with GNNs:** [Göhler & Yadav (2024, ACM)](https://dl.acm.org/doi/10.1145/3686852.3687071) applied Node2Vec and GraphSAGE (unsupervised GNNs) to analyze student concept maps autonomously, identifying 10 clusters of subgraph patterns in student knowledge representations without manual labeling effort.

**Student Answer Mapping to Knowledge Graph:**  
When a student provides a text answer, the assessment pipeline involves:
1. **Named Entity Recognition / Concept Extraction** — identify which knowledge graph concepts the student's text mentions or implies
2. **Relation Extraction** — determine which relationships between concepts the student has expressed (correctly or incorrectly)
3. **Coverage Analysis** — compare the student's concept-relation map against the expert reference subgraph for the question topic
4. **Gap/Error Detection** — identify missing concepts (knowledge gaps), incorrectly asserted relationships (misconceptions), or orphaned mentions (surface-level recall without integration)

The [Hybrid Knowledge Graph–Neural Network Framework (Dongre et al., 2025, IEEE)](https://ieeexplore.ieee.org/document/11323975/) operationalizes this approach: the Knowledge Graph component provides structured representation of educational material, the Neural Network component handles deep data-driven analysis, and the hybrid system provides "timely, relevant, and specific feedback" by modeling relationships between learning activities, assessments, and outcomes.

---

## Topic 2: Concept Maps for Assessment

### 2.1 What Are Concept Maps and Why They Matter for Assessment

Concept maps are graphical knowledge representations consisting of **concept nodes** connected by **labeled linking phrases** forming **propositions** (concept A → *relationship* → concept B). Originally developed by Joseph Novak at Cornell University in the 1970s, based on Ausubel's assimilation theory of meaningful learning, concept maps externalize a learner's cognitive structure.

Unlike multiple-choice or short-answer questions, concept maps reveal:
- **Relational understanding** (not just isolated facts)
- **Knowledge integration** across topics
- **Misconceptions** (incorrect linking phrases or wrong relationships)
- **Knowledge gaps** (missing concepts or isolated nodes)

As **formative assessment tools**, concept maps provide diagnostic information teachers can use to identify where understanding breaks down—but traditional manual evaluation is time-intensive at scale.

---

### 2.2 Meta-Analysis: Effect Size of Concept Maps on Achievement

**Citation:** İzci, E., & Açıkgöz Akkoç, E. (2023). The impact of concept maps on academic achievement: A meta-analysis. *Heliyon*, 9(12), e23290. DOI: [10.1016/j.heliyon.2023.e23290](https://linkinghub.elsevier.com/retrieve/pii/S2405844023104981) | [PMC version](https://pmc.ncbi.nlm.nih.gov/articles/PMC10755297/)

**Authors:** Eyup İzci, Ece Açıkgöz Akkoç (İnönü University, Turkey)

**Year:** 2023

**Key Methodology:**
- Meta-analysis of **78 studies** (9 doctoral dissertations, 26 master's theses, 19 national articles, 18 international articles, 3 proceedings) published 2005–2017
- Databases searched: Higher Education Board Theses Center, ProQuest, Google Scholar, ERIC, and others
- Inclusion criteria: pre-test/post-test experimental design with control group; concept maps as independent variable; reporting N, mean, SD for experimental and control groups
- Effect sizes computed with Comprehensive Meta-Analysis (CMA) software; **random effects model** (justified by significant heterogeneity: Q=686.354, p<0.001, I²=88.78%)
- Total sample: 6,464 students (3,325 experimental, 3,139 control)
- Moderators analyzed: year of publication, education level, course type, country, sample size

**Key Findings:**

| Moderator | Subgroup | Effect Size (d) | 95% CI |
|-----------|----------|-----------------|--------|
| **Overall** | All 78 studies | **1.08** | [0.914, 1.237] |
| Education Level | High School | 1.61 | [1.20, 2.02] |
| Education Level | Junior High | 1.02 | [0.81, 1.22] |
| Education Level | University | 0.62 | [0.45, 0.79] |
| Course Type | Numerical | 1.07 | [0.88, 1.26] |
| Course Type | Verbal | 1.10 | [0.77, 1.43] |

- **d = 1.08** categorized as "large positive effect" per Cohen (1988) — one of the strongest documented effects in educational intervention research
- Effect was significant in 59/78 studies; effect sizes ranged 0.02 to 5.36
- No significant difference between numerical and verbal course types (Q_between = 0.027)
- High school students show the largest effects (d=1.61), suggesting concept maps are especially powerful when students are consolidating foundational knowledge

**Limitations:**
- Over-representation of Turkish studies (66.7% of 78 studies)
- Restricted publication window (2005–2017); no studies after 2017
- Language restriction (Turkish/English only)
- Cannot isolate which component of concept mapping drives benefit (construction? review? feedback?)

---

### 2.3 Machine Learning for Automated Concept Map Evaluation

**Citation:** Bleckmann, T., & Friege, G. (2023). Concept maps for formative assessment: Creation and implementation of an automatic and intelligent evaluation method. *Knowledge Management & E-Learning*, 15(3). DOI: [10.34105/j.kmel.2023.15.025](http://www.kmel-journal.org/ojs/index.php/online-publication/article/view/556) | [ERIC PDF](https://files.eric.ed.gov/fulltext/EJ1407891.pdf)

**Authors:** Tom Bleckmann, Gunnar Friege

**Year:** 2023

**Key Methodology:**
- Concept map developed on **mechanics** (a physics topic) and deployed in **14 physics classes in Germany**
- Structured approach: students fill in linking words in labeled blank boxes (partial map completion task)
- **Two human raters** analyzed student maps using a **four-level feedback scheme**:
  - Category A: Wrong answers (physically incorrect)
  - Category B: Correct but vague/generic ("has", "needs", "changes") — 16% of responses
  - Category C: Simple but directed ("increases/decreases", "x depends on y") — 24%
  - Category D: Detailed, precise answers ("increases linearly/exponentially", "proportional to") — 22%
- **Supervised ML algorithm (Support Vector Classifier, SVC)** trained on human-rated data

**Key Findings:**
- SVC achieved "very good agreement" with human raters across all four categories
- Highest performance on categories A (wrong) and D (detailed correct); slight drop on category B (generic correct), likely due to smaller training samples
- The system could feasibly provide near-real-time feedback to teachers, enabling classroom-level adaptive instruction
- Authors envision the ML evaluation as support for Wiliam & Thompson's (2008) five key strategies of formative assessment

**Limitations:**
- Single topic (mechanics), single country (Germany) — generalizability untested
- Small data from 14 classes may limit robustness for edge-case linking phrases
- The four-level scheme is coarse; does not distinguish types of misconceptions
- Trained on "fill in the blank" format, not free-form concept map construction

---

### 2.4 Kit-Build Concept Map with Confidence Tagging (Pailai et al., 2018)

**Citations:**  
(a) Pailai, J., Wunnasri, W., Hayashi, Y., & Hirashima, T. (2018). Correctness- and Confidence-Based Adaptive Feedback of Kit-Build Concept Map with Confidence Tagging. *Lecture Notes in Computer Science*, 10947. DOI: [10.1007/978-3-319-93843-1_29](http://link.springer.com/10.1007/978-3-319-93843-1_29)  
(b) Pailai, J., Hirashima, T., Wunnasri, W., & Hayashi, Y. (2018). Kit-Build Concept Map with Confidence Tagging in Practical Uses for Assessing the Understanding of Learners. *International Journal of Advanced Computer Science and Applications*, 9(1). DOI: [10.14569/IJACSA.2018.090111](http://thesai.org/Publications/ViewPaper?Volume=9&Issue=1&Code=ijacsa&SerialNo=11)

**Authors:** J. Pailai, Warunya Wunnasri, Y. Hayashi, T. Hirashima

**Year:** 2018

**Key Methodology:**
- **Kit-Build (KB) Concept Map** is a constrained concept mapping paradigm: the teacher creates an expert reference map, which is decomposed into individual components (nodes and links); students **recompose** the map from those components rather than constructing from scratch
- **Confidence Tagging**: students attach a confidence level (high/medium/low) to each proposition they place — capturing not just whether an answer is correct but the student's meta-cognitive certainty about it
- Practical study design: **control classes** received only correctness visualization; **experimental classes** received correctness + confidence information; both used the same KB map tool
- Learning gains measured using **normalized learning gain (NLG)** and **effect size** calculations
- Assessment delivered in-class with instructor adapting supplementary content based on the combined correctness-confidence dashboard

**Key Findings:**
- Classes with confidence information showed **different instructor behaviors**: instructors selected and ordered supplementary content differently when armed with both dimensions
- Normalized learning gains and effect sizes demonstrated **statistically different learning achievements** between control (correctness-only) and experimental (correctness + confidence) classes
- Confidence information provided **positive changing behavior** for improving student understanding
- Student questionnaire responses confirmed KB map with confidence tagging as an "accepted mechanism for representing the learner's understanding and their confidence"
- Instructors confirmed that confidence information was "valuable information for recognizing the learning situation"

**Theoretical Contribution:**  
This work formalizes a **two-dimensional diagnostic space** (correctness × confidence) that maps students into four quadrants:
- **Correct + Confident** → Mastery
- **Correct + Unconfident** → Lucky guess / fragile knowledge
- **Incorrect + Confident** → Misconception (highest priority for intervention)
- **Incorrect + Unconfident** → Unknown/gap

**Limitations:**
- Specific to the KB map paradigm (constrained recomposition), not free-form mapping
- KB map relies on predetermined expert maps — teacher expertise required upfront
- Effect size and NLG details not reported precisely in the available abstract

---

### 2.5 Network Analysis of Student Concept Maps (Abraham et al., 2025)

**Citation:** Abraham, S. M., Sudhamathy, G., & Sreelakshmi. (2025). Mapping Student Understanding: Analyzing Concept Maps Using Network Similarity Measures. In *Proceedings of IEEE DICCT 2025*. DOI: [10.1109/DICCT64131.2025.10986693](https://ieeexplore.ieee.org/document/10986693/)

**Authors:** Sunu Mary Abraham, G. Sudhamathy, Sreelakshmi

**Year:** 2025 (published March)

**Key Methodology:**
- Treats student concept maps as **network graphs**, applying graph-theoretic metrics to assess structural and relational properties
- Network analysis techniques applied: **degree centrality**, **betweenness centrality**, **graph similarity measures**, and **community detection**
- Two types of student-generated maps analyzed: (1) concept maps constructed by students independently; (2) concept maps derived from student quiz responses
- **Comparison approach**: student-generated maps compared against an instructor's **reference map** using network similarity measures to quantify closeness to expert understanding
- Provides **quantitative framework** for evaluating depth and coherence of student learning

**Key Findings:**
- Network analysis highlights **key concepts** (high centrality nodes) and **relationship patterns** that distinguish high-understanding from low-understanding students
- Comparing student maps to the instructor reference map reveals both **fundamental understanding** (core nodes present) and **deeper conceptual comprehension** (correct edge structure)
- The approach offers a **scalable, quantitative** assessment method that goes beyond counting correct propositions
- Method has potential to **inform teaching strategies** based on class-level patterns in concept map networks

**Limitations:**
- Limited detail available (published March 2025, full paper behind IEEE access)
- Network similarity measures may not capture semantic accuracy of linking phrase labels
- Relies on instructor reference map being a comprehensive and unambiguous "gold standard"

---

### 2.6 Comparing Student Maps to Expert Reference Maps

The general pipeline for automated concept map assessment involves:

1. **Structural Comparison** — counting matched propositions, nodes, and relationships (quantity-based)
2. **Semantic Comparison** — checking whether linking phrases convey the same meaning, even if worded differently
3. **Network Analysis** — evaluating topological similarity (centrality patterns, clustering, key hub nodes)
4. **Diagnostic Extraction** — identifying which specific propositions are missing, incorrect, or inverted

The KB Map framework uses **Full Map Scoring (FMS)**, comparing the recomposed learner map proposition-by-proposition against the expert map. However, as noted by [Pinandito et al. (2024)](https://rptel.apsce.net/index.php/RPTEL/article/download/2024-19021/2024-19021), FMS only evaluates the final product of recomposition, neglecting the process—a limitation because different processes leading to the same result can reflect different understanding levels.

An online **Knowledge Maps tool** for medical education, studied by [Powell et al. at a medical school](https://pmc.ncbi.nlm.nih.gov/articles/PMC5907351/), showed Cronbach's α = 0.77 for internal consistency, high point-biserial correlations (minimum 0.47) indicating strong discrimination between students of differing knowledge levels, and significant correlation between map scores and Modified Essay Question (MEQ) scores—confirming that automated map-based scoring captures comparable information to open-ended writing assessment.

---

## Topic 3: Misconception Detection

### 3.1 The Challenge: Detecting What a Student Misunderstands, Not Just That They're Wrong

Standard assessment scores a student as "correct" or "incorrect." Misconception detection goes deeper: it identifies the **specific incorrect mental model** a student holds. This is fundamentally different because:

- A student scoring 60% on a test might hold one systematic misconception affecting 40% of questions, or might simply have 40% random gaps
- The instructional intervention is completely different: systematic misconceptions require targeted conceptual reframing; random gaps require additional exposure
- A score of 0% might indicate "does not understand the topic at all" or "has a persistent inverted model" — interventions differ radically

The goal is to identify **which of the known misconception categories** (pre-identified by domain experts) a student's response maps to, or whether it reveals a novel misconception pattern.

---

### 3.2 Three-Tier Multiple Choice Questions for Misconception Diagnosis

**Citation:** Anintia, R., Sadhu, S., & Annisa, D. (2017). Identify Students' Concept Understanding Using Three-Tier Multiple Choice Questions (TTMCs) on Stoichiometry. *International Journal of Science and Applied Science: Conference Series*, 2(1). DOI: [10.20961/ijsascs.v2i1.16734](https://jurnal.uns.ac.id/ijsascs/article/view/16734)

**Authors:** Rinayu Anintia, Satya Sadhu, Desfi Annisa

**Year:** 2017

**Key Methodology:**

The **Three-Tier Multiple Choice Question (TTMC)** format consists of three layers per item:
- **Tier 1**: A standard multiple-choice content question
- **Tier 2**: A set of reasoning/justification options explaining *why* the student chose their Tier 1 answer
- **Tier 3**: A confidence rating (typically "confident" / "not confident")

The combination of tiers maps to diagnostic categories:

| Tier 1 | Tier 2 | Tier 3 | Diagnosis |
|--------|--------|--------|-----------|
| Correct | Correct | Confident | **Conceptual Understanding** |
| Correct | Correct | Not Confident | Guessing (lucky) |
| Correct | Incorrect | Either | **Partial Understanding / Surface Match** |
| Incorrect | Incorrect | Confident | **Misconception** |
| Incorrect | Incorrect | Not Confident | **Lack of Knowledge** |
| Incorrect | Correct | Either | Careless error |

Study-specific details:
- 176 students from 3 schools (cluster sampling); topic: **stoichiometry**
- 30 items developed; 28/30 validated (content validity 0.56–1.00; reliability 0.47)
- Discrimination index: 42.86% "good," 42.86% "fair"

**Key Findings on Stoichiometry Understanding:**

| Category | Percentage |
|----------|-----------|
| Correct conceptual understanding | 33.10% |
| Less understanding | 4.06% |
| **Misconception** | **31.53%** |
| Did not comprehend concept | 19.50% |
| Guessing | 11.81% |

**Critical finding:** Nearly one-third (31.53%) of students held active misconceptions — they had wrong beliefs they were confident in. This is categorically different from the 19.5% who simply lacked knowledge.

**Limitations:**
- Reliability of 0.47 is moderate; item refinement needed
- Single topic (stoichiometry), single regional setting
- TTMC format detects misconception presence within predefined distractor categories, but cannot discover novel/unanticipated misconceptions
- Self-reported confidence (Tier 3) is subject to metacognitive calibration errors

**Broader Applicability:** The three-tier structure has been validated across many chemistry topics. [Jusniar (2020)](https://eu-jer.com/EU-JER_9_4_1405.pdf) used three-tier tests with 245 eleventh-graders to show that misconceptions on Rate of Reaction significantly predicted misconceptions on Chemical Equilibrium — establishing that misconceptions propagate through prerequisite chains and must be caught early.

---

### 3.3 Distilling ChatGPT for Explainable Student Assessment (Aloisi et al., 2023)

**Citation:** Li, J., Gui, L., Zhou, Y., West, D., Aloisi, C., & He, Y. (2023). Distilling ChatGPT for Explainable Automated Student Answer Assessment. In *Findings of EMNLP 2023*. DOI: [10.48550/arXiv.2305.12962](https://arxiv.org/abs/2305.12962) | [ACL Anthology](https://aclanthology.org/2023.findings-emnlp.399.pdf)

**Authors:**
- Jiazheng Li, Lin Gui, Yuxiang Zhou, Yulan He — Department of Informatics, King's College London
- David West, Cesare Aloisi — AQA (Assessment and Qualifications Alliance), UK

**Year:** 2023

**Key Methodology — AERA (Automated Explainable Student Response Assessment):**

The framework proceeds in three stages:

**Stage 1: Prompting ChatGPT for Rationale Generation**
Three prompt template types:
- *Simple Instruction* (zero-shot): "What score should this student answer get and why?"
- *Complex Instruction* (zero-shot): Detailed guidance—compare student answer with key elements, apply rubric, spell out reasoning step by step
- *Example Instruction* (few-shot): Provides sample (question, answer, score, rationale) tuples as demonstrations

Inputs: Question (Q), Key Elements (K), Rubric (R), Student Answer (x_i)  
Outputs: Predicted score (ŷ_i) and natural language rationale (r̂_i)

**Stage 2: Data & Rationale Refinement**
- *Fixing Wrongly Labeled Data*: Uses semantic confidence interval — if ChatGPT predictions cluster consistently around a different score from the gold label, update the training label
- *Rationale Refinement*: Uses XY→R template (providing gold score as prior) to regenerate rationales aligned with the correct score

**Stage 3: Distillation into Smaller Model**
- Fine-tune **Long T5 (long-t5-tglobal-large)** on the refined data
- The smaller model simultaneously assesses student answers AND generates rationales
- Long T5 handles inputs >1024 tokens (full question + rubric + student answer)

**Dataset:** ASAP-SAS benchmark (questions #1, #2, #5, #6); ~23,000 student responses from grades 7–10 science/biology

**Key Findings:**

| Method | Accuracy | Macro F1 | QWK |
|--------|----------|----------|-----|
| Longformer-all (baseline) | 76.37 | 62.61 | 81.14 |
| ChatGPT (Example Instruction) | 60.31 | 51.57 | 64.36 |
| **AERA (Ours)** | **69.92** | **54.73** | **71.62** |

- AERA improves QWK by **11% over raw ChatGPT** (71.62 vs 64.36)
- Human evaluation: AERA rationales show higher **key element correctness** (0.83 vs 0.52) and **rubric faithfulness** (0.94 vs 0.86) compared to ChatGPT rationales
- Framework generalizes to unseen datasets ("leave one out"); works with GPT-4 and Bard
- Identifies and corrects noisy training labels (mislabels, corrupted data) via high-confidence ChatGPT predictions

**Why This Matters for Misconception Detection:**  
AERA generates **natural language rationales** explaining *why* a score was assigned — moving beyond binary correct/incorrect toward identifying the specific conceptual failure. A rationale might state: "The student correctly identifies that osmosis requires a semi-permeable membrane but incorrectly states that water moves from low to high concentration — this inverts the direction of osmotic flow." This is a step toward automated misconception labeling.

**Limitations:**
- Prompt template designs vary across individual annotators and datasets
- Annotators lacked formal exam assessment backgrounds (though trained)
- Trade-off between interpretability and raw scoring performance
- ChatGPT hallucinations in zero-shot settings (wrong scales, factual errors); mitigated by few-shot examples
- QWK 71.62 still below supervised Longformer (81.14) — explainability comes at a performance cost

---

### 3.4 LLMs for Rationale Generation: The Broader Landscape

The AERA paper represents a growing paradigm: using LLMs not just to score but to explain. Key developments:

1. **Rationale-first approaches**: Generate an explanation of what key concepts the answer should contain, then assess whether the student's answer covers them
2. **Rubric-conditioned scoring**: Ground the LLM's judgment in explicit rubric criteria, reducing hallucination risk
3. **Chain-of-thought distillation**: Transfer reasoning chains from large LLMs (GPT-4) to smaller, deployable models

The [Gao et al. (2024) systematic review of text-based assessment](https://arxiv.org/abs/2308.16151) identifies that LLM-based systems represent the current frontier, but notes persistent challenges: domain-specific knowledge gaps, sensitivity to phrasing, inability to verify conceptual coherence (as opposed to surface similarity), and lack of standardized benchmarks for concept-level assessment.

---

## Topic 4: Concept Understanding vs Surface Matching

### 4.1 The Hierarchy: Keyword Matching → Semantic Similarity → Concept Understanding

Three levels of response assessment exist, each more cognitively demanding to implement:

#### Level 1: Keyword Matching
- **Mechanism**: Presence/absence of target terms (e.g., does the answer contain "osmosis," "membrane," "concentration gradient"?)
- **Strengths**: Computationally trivial; interpretable
- **Failures**: "The membrane does not allow water to pass based on concentration gradient" contains all keywords but expresses the opposite of the correct relationship; "Diffusion, which is distinct from osmosis, involves..." uses "osmosis" in a contrasting context
- **Use case**: Appropriate only for highly constrained factual recall questions

#### Level 2: Semantic Similarity
- **Mechanism**: Embedding-based cosine similarity (e.g., BERT, Sentence-BERT) measuring how close the student's response is to a reference answer in vector space
- **Strengths**: Captures paraphrase, synonymy, and conceptual proximity beyond surface words
- **Failures**: A student answer that correctly names all concepts but describes their relationships incorrectly ("water moves from low to high concentration") may score high similarity to a correct answer ("water moves from high to low concentration") because both share the same semantic vocabulary. Negation detection is notoriously unreliable in embedding models. Two answers that are semantic opposites can have high cosine similarity.
- **Use case**: Better than keyword matching for partial credit assignment; still inadequate for detecting misconceptions

#### Level 3: Concept Understanding Assessment
- **Mechanism**: Mapping the student's expressed propositions (concept → relationship → concept) onto a domain knowledge graph; verifying correctness of both the concepts mentioned AND the relationships between them
- **Strengths**: Can detect whether a student has the correct mental model, not just the correct vocabulary; enables misconception identification
- **Failures**: Technically complex; requires a well-formed knowledge graph; relationship extraction from student text is an unsolved NLP challenge at scale
- **Use case**: Essential for deep learning assessment; enabled by knowledge graph approaches

As the [ASAG literature documents](https://ijtech.eng.ui.ac.id/download/article/4651): "Semantic similarity is still the most unresolved issue in short-answer grading systems. Due to the semantic and syntactic restrictions, a number of models were unable to identify the short answer accurately." The field recognizes that true conceptual understanding cannot be captured by similarity alone.

---

### 4.2 Haycocks et al. (2024) — Conceptual Knowledge is More Durable Than Factual Knowledge

**Citation:** Haycocks, N. G., Hernandez-Moreno, J., Bester, J. C., Hernandez, R., Jr., Kalili, R., Samrao, D., Simanton, E., & Vida, T. A. (2024). Assessing the Difficulty and Long-Term Retention of Factual and Conceptual Knowledge Through Multiple-Choice Questions: A Longitudinal Study. *Advances in Medical Education and Practice*, 15, 1187–1199. DOI: [10.2147/AMEP.S478193](https://pmc.ncbi.nlm.nih.gov/articles/PMC11653852/)

**Authors:** Neil G. Haycocks, Jessica Hernandez-Moreno, Johan C. Bester, Robert Hernandez Jr., Rosalie Kalili, Daman Samrao, Edward Simanton, Thomas A. Vida  
(Affiliations: University of Utah; Kirk Kerkorian School of Medicine at UNLV; Saint Louis University School of Medicine)

**Year:** 2024

**Key Methodology:**
- 45 MCQs from a summative exam in pulmonary and renal physiology (Kirk Kerkorian School of Medicine)
- Questions classified by faculty consensus into:
  - **Recall/verbatim** (33 questions, 73%): simple cognitive processes, factual recall
  - **Concept/inference** (10 questions, 22%): complex cognitive processes, relationships and predictions
  - Mixed/ambiguous (2, excluded)
- **Retrospective analysis**: 2020 summative exam performance (n=120 cohort, class median 84.1%)
- **Longitudinal follow-up**: Same questions re-administered as voluntary quizzes in January–February 2022 (after clerkship year) to n=56 volunteers
- Subgroup analysis by performance quartiles (Q1–Q4)
- Statistical analysis: paired t-tests, homoscedastic linear regression

**Key Findings:**

| Period | Recall/Verbatim Correct | Concept/Inference Correct | Difference |
|--------|------------------------|--------------------------|------------|
| 2020 | 82.0% | 60.9% | 21.1 pp (p=0.002) |
| 2022 | 59.8% | 42.9% | 16.9 pp (p=0.079, NS) |

- In 2020: Recall/verbatim was significantly **easier** (82.0% vs 60.9%)
- By 2022: The gap **collapsed** (no longer statistically significant)
- **Recall/verbatim declined by ~22 points** (82.0% → 59.8%, p<0.001)
- **Concept/inference declined by ~18 points** (60.9% → 42.9%)

- **Key interpretation**: Conceptual/inferential knowledge declines less in absolute terms, especially when clinically reinforced. The top-performing students (top half) retained concept/inference questions better than bottom-half students even 2 years later. By 2022, performance on both types converged across groups — the differentiation that concept questions provided in 2020 had stabilized.

**Conclusion:** "Conceptual/inferential thinking is more complex than rote memorization. However, the knowledge acquired is more durable in a longitudinal fashion, especially if it is reinforced in clinical settings."

**Implications for Assessment Design:**
- Assessments should prioritize concept/inference questions to evaluate genuinely durable learning
- High performance on recall questions alone does not predict long-term retention
- Concept questions better discriminate between truly understanding and surface-memorizing students

**Limitations:**
- Limited scope (pulmonary/renal physiology only)
- Small sample (n=56 from a cohort of 120; voluntary follow-up)
- Only 10 concept/inference questions — insufficient for fine-grained analysis
- Post-clerkship context may confound results (clinical reinforcement vs. forgetting)
- Voluntary 2022 assessment had lower stakes than 2020 summative exam

---

### 4.3 Surface vs. Deep Learners: Alvarez (2019) on Chemical Equilibrium

**Citation:** Alvarez, M. L. C. (2019). Conceptual Understanding in Chemical Equilibrium of Surface and Deep Learners. *Granthaalayah*, 7(6). DOI: [10.29121/granthaalayah.v7.i6.2019.764](https://www.granthaalayahpublication.org/journals/index.php/granthaalayah/article/view/IJRG19_A06_2389)

**Author:** M. L. C. Alvarez

**Year:** 2019

**Key Methodology:**
- 58 engineering students enrolled in General Chemistry II (two intact classes), 3-week study on chemical equilibrium
- **Study Process Questionnaire (SPQ)** classified students as surface learners (47%) or deep learners (53%)
- **Conceptual Understanding Test (CUT)** administered after instruction
- Students grouped into six cells (2 learning approaches × 3 understanding levels)
- Statistical analysis: t-test (score differences), chi-square test of independence

**Surface Learners** employ rote memorization, pattern recognition, and formula application without understanding underlying mechanisms. **Deep Learners** seek to understand the relationships between concepts, underlying mechanisms, and the *why* behind procedures.

**Key Findings:**
- Surface and deep learners differed significantly on **factors affecting equilibrium** concepts (t-test significant)
- Chi-square test showed surface and deep learners **significantly differ** in their level of conceptual understanding on equilibrium factors
- However, for some sub-concepts within chemical equilibrium, the difference was **not significant** — suggesting that even surface learners can achieve conceptual-level performance on specific, memorizable relationships
- 53% of the class were classified as deep learners; 47% as surface learners

**Critical Insight:** Surface-level matching (whether keyword or semantic embedding) would not distinguish these groups — both groups could produce answers containing the same vocabulary. The difference lies in whether the student can explain *why* Le Chatelier's principle applies in a novel situation vs. simply recalling its statement. This is precisely the gap that existing ASAG systems fail to bridge.

**Limitations:**
- Small sample (58 students from a single institution)
- SPQ classification as surface/deep learner is itself a self-reported measure subject to social desirability bias
- Single topic (chemical equilibrium) limits generalizability

---

### 4.4 Webb's Depth of Knowledge Framework

**Source:** Webb, N. L. (1997). Alignment of Science and Mathematics Standards and Assessments in Four States. National Institute for Science Education. [Edutopia overview](https://www.edutopia.org/article/how-use-norman-webb-depth-of-knowledge/)

Webb's Depth of Knowledge (DOK) is a four-level framework categorizing tasks by **cognitive complexity** — specifically, how deeply a student must think to complete the task, independent of content difficulty.

| DOK Level | Name | Description | Example |
|-----------|------|-------------|---------|
| **Level 1** | Recall & Reproduction | Recall facts, definitions, formulas; simple one-step procedures | "What is the formula for photosynthesis?" |
| **Level 2** | Skills & Concepts | Apply concepts; explain, interpret, classify | "Explain why plants need sunlight for photosynthesis" |
| **Level 3** | Strategic Thinking & Reasoning | Use evidence from multiple sources; formulate hypotheses; analyze | "Compare the efficiency of photosynthesis in C3 vs C4 plants under drought conditions" |
| **Level 4** | Extended Thinking | Synthesize across disciplines; design experiments; evaluate competing arguments | "Design a study to test whether manipulating light wavelength affects crop yield under varying CO₂ concentrations" |

**DOK vs Bloom's Taxonomy:** Bloom's focuses on *what verb the task uses* (remember, understand, apply, analyze, evaluate, create). DOK focuses on *how deeply the mind must engage* — a "creative" task at DOK 1 could still only require recall. DOK is considered more precise for measuring genuine cognitive rigor in assessment design.

**Why Current ASAG Fails at DOK 3–4:**
- Most ASAG systems are benchmarked on questions at DOK 1–2 (factual recall, direct explanation)
- DOK 3–4 tasks require multi-step reasoning, integration across concepts, and evaluation of trade-offs
- Semantic similarity models cannot distinguish between a student who correctly states a fact and one who correctly *applies* that fact to a novel context
- Without a knowledge graph mapping concept dependencies, systems cannot verify whether a student's reasoning pathway (A → B → C) is valid or whether it skips prerequisite steps

---

### 4.5 Why Current ASAG Fails at Measuring Concept Understanding

The limitations of current Automated Short Answer Grading (ASAG) systems for measuring true concept understanding include:

1. **Reference-answer dependency**: Most ASAG systems compare student responses to a fixed reference answer. If a student expresses a correct idea in an unexpected way, or if the reference answer is incomplete, the system misscores.

2. **Semantic similarity ≠ conceptual equivalence**: Two responses can be high-similarity but semantically opposite (e.g., "water moves from low to high" vs "water moves from high to low" concentration). BERT-based embeddings encode words and their context but cannot reliably evaluate relational correctness.

3. **Negation and qualifier blindness**: Current models often fail to correctly handle negation ("osmosis does *not* require..."), hedged claims ("osmosis *might* require..."), and conditional logic ("osmosis requires X *only when* Y").

4. **No misconception taxonomy**: ASAG systems output scores; they do not identify which diagnostic category of misunderstanding the student holds. This makes feedback generic rather than targeted.

5. **Domain knowledge not grounded**: Without a structured knowledge graph encoding what the correct relationships between concepts are, the system cannot check whether a student's stated relationship is valid within the domain.

6. **Shallow training benchmarks**: The dominant benchmark (ASAP-SAS) focuses on general science questions where vocabulary-level similarity is sufficient to distinguish correct from incorrect answers. This does not stress-test relational understanding.

7. **No process information**: As the [GradeAid framework (Gao et al., 2023)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10197042/) notes, current systems analyze only the final text product, not the reasoning process that generated it.

---

## Cross-Cutting Themes & Synthesis

### Theme 1: The Complementarity of Knowledge Graphs and Concept Maps

Both knowledge graphs (designed by domain experts) and concept maps (drawn by students) are graph-structured representations of domain knowledge. Their complementarity enables a powerful assessment architecture:

- **Expert knowledge graph** → defines the "target" structure: which concepts matter, which relationships are correct, which are prerequisite to others
- **Student concept map** → reveals the student's current mental model: which concepts they include, which relationships they believe, where their model deviates from the expert
- **Comparison** → computes a gap analysis: missing nodes (knowledge gaps), wrong edges (misconceptions), isolated nodes (surface recall without integration), inverted edges (systematic misconceptions)

This is architecturally equivalent to the expert-reference comparison approach in KB maps, but grounded in a richer, formally defined knowledge structure.

### Theme 2: Confidence Information Dramatically Enhances Diagnostic Value

The Pailai et al. (2018) work and the three-tier MCQ literature (Annisa et al., 2017) both demonstrate that **combining correctness with confidence** is essential for distinguishing:
- Misconceptions (wrong + confident) — highest pedagogical priority
- Lucky guesses (correct + not confident) — knowledge is fragile
- Solid understanding (correct + confident)
- Knowledge gaps (wrong + not confident)

Any system that reports only "correct/incorrect" discards half the diagnostic information available.

### Theme 3: The Durability Argument for Deep Assessment

Haycocks et al. (2024) provides empirical longitudinal evidence that conceptual/inferential knowledge is more durable than factual recall. Combined with Alvarez (2019) showing that surface learners and deep learners can score similarly on rote tasks but diverge on concept application, this suggests:

- **Assessments optimizing for factual accuracy are optimizing for the wrong target** — they measure something that decays rapidly and does not predict long-term understanding
- **Concept-level assessments are the appropriate measure** of educational value
- Current ASAG systems, by targeting semantic similarity to reference answers, are largely measuring DOK 1–2 performance

### Theme 4: LLMs Provide Explanation, Knowledge Graphs Provide Structure

The AERA framework (Aloisi et al., 2023) shows LLMs can generate natural language rationales for scoring decisions. But rationales are only as reliable as the model's domain knowledge. A complementary architecture would:

1. Use a **knowledge graph** to define what correct concept relationships look like (structured ground truth)
2. Use an **LLM** to extract concept-relationship propositions from student free-text responses
3. Map extracted propositions onto the knowledge graph
4. Use the graph comparison to generate both a score and a structured misconception diagnosis
5. Use the LLM again to convert the structured diagnosis into natural language feedback

This separation of concerns addresses the AERA limitation that LLMs hallucinate domain-specific facts.

---

## Research Gaps & Future Directions

1. **No benchmark dataset for concept-level ASAG**: Existing benchmarks (ASAP-SAS) do not annotate student responses with misconception categories. A dataset pairing student answers with expert-identified misconception labels would enable supervised misconception detection.

2. **Relationship extraction from student text at scale**: Current NLP can extract named entities but struggles with multi-hop relational claims in short student answers. Improved lightweight relation extraction models tuned for educational domains are needed.

3. **Dynamic knowledge graphs for evolving curricula**: Most educational KG work builds static graphs. Real curricula evolve, and a student's understanding must be modeled as a dynamic state over time (knowledge tracing + graph structure).

4. **Cross-cultural and cross-linguistic validation**: The Bleckmann/Friege (2023) concept map work is Germany-specific; the Izci meta-analysis is Turkey-dominated. Most ASAG benchmarks are English-language. Assessment systems need validation across languages and educational systems.

5. **Integration of process-level data**: KB map systems capture the recomposition process; future systems could analyze the sequence of edits a student makes to identify confidence patterns and moment-of-confusion markers.

6. **From ASAG to Adaptive Formative Assessment**: The trajectory from automated scoring toward misconception-aware adaptive feedback systems is clear in the literature, but production-quality systems remain rare. The gap between research demos and classroom-deployable tools is substantial.

---

## Full Citation Index (Alphabetical by First Author)

| # | Authors | Year | Title (abbreviated) | Venue | DOI/URL |
|---|---------|------|---------------------|-------|---------|
| 1 | Abraham, Sudhamathy, Sreelakshmi | 2025 | Mapping Student Understanding: Analyzing Concept Maps Using Network Similarity Measures | IEEE DICCT | [10.1109/DICCT64131.2025.10986693](https://ieeexplore.ieee.org/document/10986693/) |
| 2 | Alvarez, M.L.C. | 2019 | Conceptual Understanding in Chemical Equilibrium of Surface and Deep Learners | Granthaalayah 7(6) | [10.29121/granthaalayah.v7.i6.2019.764](https://www.granthaalayahpublication.org/journals/index.php/granthaalayah/article/view/IJRG19_A06_2389) |
| 3 | Anintia, Sadhu, Annisa | 2017 | Identify Students' Concept Understanding Using TTMCs on Stoichiometry | IJSASCS 2(1) | [10.20961/ijsascs.v2i1.16734](https://jurnal.uns.ac.id/ijsascs/article/view/16734) |
| 4 | Bleckmann, Friege | 2023 | Concept maps for formative assessment: automatic and intelligent evaluation | KMEL 15(3) | [10.34105/j.kmel.2023.15.025](http://www.kmel-journal.org/ojs/index.php/online-publication/article/view/556) |
| 5 | Fu, Fang | 2025 | Curriculum-Aware Cognitive Diagnosis via Graph Neural Networks | Information 16(11) | [10.3390/info16110996](https://www.mdpi.com/2078-2489/16/11/996) |
| 6 | Göhler, Yadav | 2024 | Analyzing Concept Maps in CS Education: Unsupervised Learning with GNNs | ACM SIGCSE | [10.1145/3686852.3687071](https://dl.acm.org/doi/10.1145/3686852.3687071) |
| 7 | Haycocks et al. | 2024 | Difficulty and Long-Term Retention of Factual and Conceptual Knowledge (Longitudinal) | AMEP 15 | [10.2147/AMEP.S478193](https://pmc.ncbi.nlm.nih.gov/articles/PMC11653852/) |
| 8 | İzci, Açıkgöz Akkoç | 2023 | The impact of concept maps on academic achievement: A meta-analysis | Heliyon 9(12) | [10.1016/j.heliyon.2023.e23290](https://pmc.ncbi.nlm.nih.gov/articles/PMC10755297/) |
| 9 | Jia et al. | 2021 | Heterogeneous GNNs for Concept Prerequisite Relation Learning | NAACL 2021 | [10.18653/v1/2021.naacl-main.164](https://www.aclweb.org/anthology/2021.naacl-main.164.pdf) |
| 10 | Jusniar | 2020 | Misconceptions in Rate of Reaction and impact on Chemical Equilibrium | EU-JER 9(4) | [10.12973/eu-jer.9.4.1405](https://eu-jer.com/EU-JER_9_4_1405.pdf) |
| 11 | Li, Gui, Zhou, West, Aloisi, He | 2023 | Distilling ChatGPT for Explainable Automated Student Answer Assessment | EMNLP Findings | [10.48550/arXiv.2305.12962](https://aclanthology.org/2023.findings-emnlp.399.pdf) |
| 12 | Pailai, Wunnasri, Hayashi, Hirashima | 2018 | Correctness- and Confidence-Based Adaptive Feedback of Kit-Build Concept Map | LNCS 10947 | [10.1007/978-3-319-93843-1_29](http://link.springer.com/10.1007/978-3-319-93843-1_29) |
| 13 | Pailai, Hirashima, Wunnasri, Hayashi | 2018 | Kit-Build Concept Map with Confidence Tagging in Practical Uses | IJACSA 9(1) | [10.14569/IJACSA.2018.090111](http://thesai.org/Publications/ViewPaper?Volume=9&Issue=1&Code=ijacsa&SerialNo=11) |
| 14 | Pan et al. | 2024 | Unifying Large Language Models and Knowledge Graphs: A Roadmap | IEEE TKDE | [10.1109/TKDE.2024.3352100](https://arxiv.org/abs/2306.08302) |
| 15 | Webb, N.L. | 1997 | Alignment of Science and Math Standards and Assessments | NISE Research Monograph 18 | [Edutopia overview](https://www.edutopia.org/article/how-use-norman-webb-depth-of-knowledge/) |
| 16 | Yang et al. | 2024 | Graphusion: LLM-based Scientific Knowledge Graph Fusion for NLP Education | arXiv | [10.48550/arXiv.2407.10794](https://arxiv.org/html/2407.10794v1) |
| 17 | Yu et al. | 2021 | Constructing an Educational Knowledge Graph with Concepts from MOOCs | JCST 36(5) | [JCST PDF](https://jcst.ict.ac.cn/fileup/1000-9000/PDF/2021-5-18-0328.pdf) |
| 18 | Zhang, C. | 2025 | Optimising AI writing assessment using feedback and knowledge graph integration | PeerJ CS | [10.7717/peerj-cs.2893](https://peerj.com/articles/cs-2893) |

---

*Research compiled using academic database searches (semantic scholar, arXiv, IEEE, ACM, PMC), direct paper retrieval, and web sources. All citations include verifiable DOIs or URLs.*
