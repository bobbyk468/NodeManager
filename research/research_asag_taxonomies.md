# Research: ASAG & Bloom's/SOLO Taxonomies
**Compiled:** March 20, 2026  
**Topics:** Automatic Short Answer Grading (ASAG) · Bloom's Taxonomy in Automated Assessment · SOLO Taxonomy · NLP for Conceptual Understanding

---

## Table of Contents

1. [Topic 1: Current State of Automatic Short Answer Grading (ASAG)](#topic-1)
   - [Overview & Core Limitation](#asag-overview)
   - [Key Systems: NodeGrade, GradeAid, EngSAF](#key-systems)
   - [Core Methods](#core-methods)
   - [Key Datasets](#key-datasets)
   - [Performance Metrics](#performance-metrics)
2. [Topic 2: Bloom's Taxonomy in Automated Assessment](#topic-2)
   - [Bloom's Revised Taxonomy Overview](#blooms-overview)
   - [EduEval (2025)](#edueval)
   - [BloomAPR (2025)](#bloomapr)
   - [LLMs meet Bloom's Taxonomy — COLING 2025](#llms-blooms)
   - [Chain-of-Thought Prompting — Cohn et al. 2024 (AAAI/EAAI)](#cohn-2024)
   - [Emirtekin & Özarslan 2025 — LLM-Human Agreement Decline](#emirtekin-2025)
3. [Topic 3: SOLO Taxonomy for Depth Assessment](#topic-3)
   - [SOLO Taxonomy Overview](#solo-overview)
   - [Fernandez & Guzon 2025](#fernandez-2025)
   - [SOLO vs. Bloom's: Why SOLO May Better Measure Understanding Depth](#solo-vs-blooms)
4. [Topic 4: Somers et al. 2021 — NLP for Conceptual Understanding](#topic-4)
5. [Cross-Topic Synthesis & Implications](#synthesis)

---

## Topic 1: Current State of Automatic Short Answer Grading (ASAG) {#topic-1}

### Overview & Core Limitation {#asag-overview}

Automatic Short Answer Grading (ASAG) is the computational task of assigning scores to free-text student responses to questions, using a reference answer for comparison. The field has progressed from keyword matching through corpus-based similarity to deep learning and, most recently, large language models (LLMs). Despite these advances, the dominant paradigm remains one of **surface-level textual similarity**: systems measure how much a student's answer looks like (or encodes similarly to) the reference answer, rather than probing the depth or quality of the student's conceptual understanding. This means a response that correctly paraphrases domain vocabulary can receive a high score even if the student lacks genuine conceptual grasp, while a non-standard but insightful answer may score poorly.

---

### Key Systems {#key-systems}

#### NodeGrade (Fischer et al., 2025)

| Field | Details |
|-------|---------|
| **Authors** | David Vincent Fischer et al. (6 authors), Hochschule Kempten / HASKI-RAK project |
| **Year** | 2025 |
| **Title** | "Evaluation of a Node-based Automatic Short Answer Tool 'NodeGrade'" |
| **Venue** | ACM (DOI: 10.1145/3723010.3723021); also OPUS4 Hochschule Kempten |
| **URLs** | [ACM DL](https://dl.acm.org/doi/abs/10.1145/3723010.3723021) · [OPUS4 PDF page](https://opus4.kobv.de/opus4-hs-kempten/3050) · [GitHub](https://github.com/HASKI-RAK/NodeGrade) |

**Methodology:**  
NodeGrade uses a **node-graph interface** that allows instructors to visually design grading pipelines. The system assembles modular "worker units" — NLP models hosted via the OpenAPI standard — that can be chained together in a directed graph of processing steps. Each node can call sentence transformers (producing semantic embeddings), cosine similarity computations, keyword/stemming processors (Porter Stemmer), and LLM API calls. Instructors configure which models are invoked and how scores are aggregated. The system exposes a benchmarking endpoint that accepts `question`, `realAnswer` (reference), and `answer` (student) and returns predicted labels/scores. The research triangulates performance, functionality, and user experience.

**Key Findings/Metrics:**  
- Comparable performance to published ASAG systems on public benchmark datasets.  
- **Outperforms GPT-4 on SemEval 2013 Task 7** (Beetle/SciEntsBank) on at least one benchmark split.  
- Identified weaknesses: performance degrades on responses near the score boundaries (lowest and highest scores).

**Limitations:**  
- Node-graph pipeline requires instructor configuration effort; non-technical users may struggle.  
- Boundary-case handling is weak.  
- The system's modular flexibility means results depend heavily on which worker units are selected — no single universal configuration.  
- Like most ASAG systems, scoring is relative to the reference answer; conceptual depth beyond surface similarity is not explicitly assessed.

---

#### GradeAid (del Gobbo, Guarino, Cafarelli & Grilli, 2023)

| Field | Details |
|-------|---------|
| **Authors** | Emiliano del Gobbo, Alfonso Guarino, Barbara Cafarelli, Luca Grilli |
| **Institutions** | University of Foggia (Economics & Humanities), Italy |
| **Year** | 2023 (submitted July 2022; published May 2023) |
| **Title** | "GradeAid: a framework for automatic short answers grading in educational contexts — design, implementation and evaluation" |
| **Journal** | *Knowledge and Information Systems* (Springer) |
| **URLs** | [PubMed / PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC10197042/) · [ACM DL](https://dl.acm.org/doi/abs/10.1007/S10115-023-01892-9) · [Semantic Scholar](https://www.semanticscholar.org/paper/e7c29dc8d22c58ae3359ebde4560061151749e3b) |

**Methodology:**  
GradeAid jointly analyzes **lexical** and **semantic** features of student answers:

1. **Lexical features** — TF-IDF (Term Frequency–Inverse Document Frequency) matrix encoding word occurrences in the answer corpus.  
2. **Semantic features** — BERT Cross-Encoder similarity score using the pre-trained `cross-encoder/stsb-roberta-large` model, which takes student answer + reference answer simultaneously and outputs a continuous similarity value (−1 to 1).  
3. The two feature representations are **concatenated** into a unified feature matrix.  
4. **Regressors** (supervised learning) predict a continuous score. Best performers: Adaptive Boosting, Random Forest, Support Vector Regressor.  
5. Validation via **leave-one-out cross-validation (LOO-CV)** on per-question subsets.

**Distinctive features compared to prior work:**
- Supports **non-English datasets** (tested on Italian language data — RMSE down to 0.42).
- Benchmarked on *every* publicly available ASAG dataset at the time (ASAP, SAG, SciEntsBank, CU-NLP).
- Introduces a new Italian ASAG dataset.
- Provides standardized repository and code for reproducibility.

**Key Findings/Metrics:**  
- RMSE as low as **0.25** on a 0–5 scale for specific dataset-question tuples.  
- Performance comparable to or better than state-of-the-art systems on all tested datasets.  
- Single regressors outperform ensemble methods in this task.

**Limitations:**  
- Still fundamentally a reference-answer similarity system; does not model conceptual depth or understanding quality.  
- Very short answers are not graded reliably.  
- Performance is sensitive to the specific dataset-question tuple; no single configuration works uniformly well.  
- Cross-encoder semantic similarity does not differentiate between a student who correctly paraphrases and one who genuinely understands the concept.

---

#### EngSAF Dataset (Aggarwal et al., 2024)

| Field | Details |
|-------|---------|
| **Authors** | Dishank Aggarwal, Pritam Sil, Bhaskaran Raman, Pushpak Bhattacharyya |
| **Institution** | Indian Institute of Technology Bombay (IIT Bombay) |
| **Year** | 2024 (arXiv submitted June 30, 2024) |
| **Title** | '"I understand why I got this grade": Automatic Short Answer Grading with Feedback' |
| **Repository** | [https://github.com/dishankaggarwal/EngSAF](https://github.com/dishankaggarwal/EngSAF) |
| **URLs** | [arXiv abstract](https://arxiv.org/abs/2407.12818) · [arXiv HTML full text](https://arxiv.org/html/2407.12818v1) |

**Dataset Description:**  
EngSAF (Engineering Short Answer Feedback) is a **multi-domain engineering ASAG dataset with synthetic feedback**, the first of its kind designed for the dual task of grading and feedback generation:

- **Size:** ~5,800 student answer instances  
- **Coverage:** 119 questions from 25 undergraduate and graduate engineering courses at IIT Bombay  
- **Label space:** Correct / Partially Correct / Incorrect (3-way)  
- **Feedback:** Synthetically generated via the Label-Aware Synthetic Feedback Generation (LASFG) strategy, which conditions a generative LLM on the question, reference answer, student answer, and assigned label to produce constructive, non-discouraging feedback  
- **Human validation:** 3 annotators; 98% label accuracy; Cohen's κ = 0.65 (substantial agreement); Fleiss' κ = 0.83 for feedback quality  

**Key Methodology:**  
The LASFG strategy prompts state-of-the-art LLMs (including GPT-3.5-turbo-16k) with the following pattern:

> "Given a question, a student answer, a reference answer, and a correctness label, provide constructive feedback. Do not reference the provided reference answer. Keep it concise (3–4 lines) and aim to guide the learner without invoking negative emotions."

**LLM Baselines:**

| Model | Accuracy (Unseen Answers) | Accuracy (Unseen Questions) |
|-------|--------------------------|------------------------------|
| Mistral-7B (fine-tuned) | **75.4%** | **58.7%** |
| GPT-3.5 (zero-shot) | ~62% | ~45% |

- Real-world deployment at IIT Bombay end-semester exam: 92.5% accuracy on 25 sampled answers per question; feedback quality score >4.5/5 by subject matter experts.

**Limitations:**  
- Feedback is synthetically generated — not verified by real instructors for pedagogical depth.  
- 3-way label granularity limits scoring precision.  
- Dataset is domain-specific (engineering) and potentially biased toward Indian university question styles.  
- Like all ASAG systems, labels correctness relative to the reference answer; does not capture the *level* of understanding or *why* an answer is conceptually sound.

---

### Core Methods in ASAG {#core-methods}

| Method Category | Description | Representative Works |
|-----------------|-------------|----------------------|
| **Keyword / Pattern Matching** | Surface token overlap; regular expressions | Mitchell et al. 2002; Sukkarieh et al. 2004 |
| **Corpus-Based Similarity (LSA, ESA)** | Latent Semantic Analysis; cosine similarity in semantic vector space | Mohler et al. 2009; LaVoie et al. 2020 |
| **Cosine Similarity (Sentence Embeddings)** | Encode student + reference answer as dense vectors; measure cosine distance | Most pre-LLM ASAG systems |
| **Sentence Transformers (SBERT)** | Siamese BERT networks producing fixed-size sentence embeddings optimized for semantic similarity | Reimers & Gurevych 2019; Condor et al. 2021 |
| **TF-IDF + BERT Cross-Encoder (Hybrid)** | Lexical bag-of-words combined with BERT pairwise semantic similarity | GradeAid (del Gobbo et al. 2023) |
| **LLM-Based Scoring (Zero-Shot / Few-Shot)** | Prompt LLMs directly with rubric + question + reference + student answer | EngSAF (Aggarwal et al. 2024); multiple 2024–2025 studies |
| **LLM + Chain-of-Thought (CoT)** | LLM generates step-by-step reasoning before assigning a score; enables explainable grading | Cohn et al. 2024 (AAAI/EAAI); NodeGrade (Fischer et al. 2025) |
| **Node-Graph Pipeline** | Modular, instructor-configurable grading graphs combining multiple NLP worker units | NodeGrade (Fischer et al. 2025) |

**Core Limitation:** All of these methods, including LLM-based ones, measure the **semantic or structural proximity** between the student's answer and a reference answer. They are not designed to assess *why* a student answered correctly or incorrectly, nor to locate the student's answer on a dimension of conceptual depth. A student who memorizes the reference answer phrasing may score identically to one who has deeply internalized and can apply the concept.

---

### Key Datasets {#key-datasets}

| Dataset | Source | Domain | Size | Language | Labels | Availability |
|---------|--------|--------|------|----------|--------|--------------|
| **Mohler (Texas/Texas Extended)** | Mohler et al. 2009/2011, Univ. of North Texas | Data Structures (CS) | 630 / 2,273 answers; 80/87 questions | English | 0–5 continuous | Yes (public) |
| **SemEval 2013 Task 7 — SciEntsBank** | Dzikovska et al. 2013; Nielsen et al. 2008 | 15 science domains | ~10,000 answers; 197 questions | English | 5-way: correct, partially correct incomplete, contradictory, irrelevant, non-domain | Yes |
| **SemEval 2013 Task 7 — Beetle** | Dzikovska et al. 2013; Nielsen et al. 2008 | Basic electricity & electronics | ~3,000 answers; 56 questions | English | Same 5-way as above | Yes |
| **EngSAF** | Aggarwal et al. 2024, IIT Bombay | 25 engineering courses | ~5,800 answers; 119 questions | English | 3-way: correct, partially correct, incorrect | Yes ([GitHub](https://github.com/dishankaggarwal/EngSAF)) |
| **OS Dataset** | Mohler et al. 2011 extended | Operating Systems | Subset of Texas Extended | English | 0–5 continuous | Yes |
| **ASAP (Hewlett Foundation)** | Kaggle competition | Science, Biology | ~2,200 answers | English | Variable by question | Yes (Kaggle) |
| **SAF (Short Answer Feedback)** | Filighera et al. 2022 | Physics | 4,519 answers | English + German | Scores + feedback | Yes |

**SemEval 2013 Task 7** ([ACL Anthology paper](https://aclanthology.org/S13-2045.pdf)) introduced the standard 3-way (UA/UQ/UD: unseen answers, unseen questions, unseen domains) split structure that became the benchmark for ASAG generalization, measuring a system's ability to grade answers not seen during training — a harder and more realistic evaluation condition.

---

### Performance Metrics {#performance-metrics}

| Metric | Full Name | What It Measures | Typical Range | Notes |
|--------|-----------|-----------------|---------------|-------|
| **QWK** | Quadratic Weighted Kappa | Agreement between predicted and human scores, penalizing larger disagreements more | 0–1 (0 = chance, 1 = perfect) | Standard for ordinal ASAG; QWK ≥ 0.8 = strong agreement |
| **Pearson's r** | Pearson Correlation Coefficient | Linear correlation between predicted and human scores | −1 to 1 | Used for regression-scored datasets (e.g., Mohler) |
| **RMSE** | Root Mean Squared Error | Magnitude of prediction error in original score units | 0–∞ (lower = better) | GradeAid: RMSE 0.25 on 0–5 scale |
| **F1** | F1 Score (weighted or macro) | Harmonic mean of precision and recall on classification | 0–1 | Used for categorical ASAG (e.g., SemEval 3-way/5-way) |
| **ROC-AUC** | Area Under the Receiver Operating Characteristic Curve | Classifier discrimination ability across thresholds | 0.5–1 | Used in binary or one-vs-rest ASAG classification settings |
| **ICC** | Intraclass Correlation Coefficient | Consistency among raters (including LLM vs. human) | 0–1 | Used in newer LLM-based grading studies |
| **Cohen's κ** | Cohen's Kappa | Inter-annotator agreement corrected for chance | 0–1 | Emirtekin & Özarslan 2025 use QWK; Cohn et al. 2024 use QWK |

---

## Topic 2: Bloom's Taxonomy in Automated Assessment {#topic-2}

### Bloom's Revised Taxonomy Overview {#blooms-overview}

Bloom's Revised Taxonomy (Anderson & Krathwohl, 2001 — a revision of Bloom et al., 1956) provides a **two-dimensional hierarchical framework** for classifying educational objectives:

**Cognitive Process Dimension** (6 levels, from lower-order to higher-order):

| Level | Name | Description | Typical Verbs |
|-------|------|-------------|---------------|
| 1 | **Remember** | Recognize and recall facts | define, list, recall, identify |
| 2 | **Understand** | Explain what facts mean; paraphrase | explain, summarize, classify |
| 3 | **Apply** | Use facts, rules, concepts in new situations | solve, compute, execute |
| 4 | **Analyze** | Break material into component parts; infer | differentiate, compare, attribute |
| 5 | **Evaluate** | Make judgments based on criteria | critique, defend, justify |
| 6 | **Create** | Combine parts to create a new whole | design, construct, formulate |

**Knowledge Dimension** (4 types): Factual → Conceptual → Procedural → Metacognitive

Levels 1–3 are considered **Lower-Order Thinking Skills (LOTS)**; levels 4–6 are **Higher-Order Thinking Skills (HOTS)**. The key pedagogical insight is that most short-answer assessments and most ASAG systems operate at levels 1–2, but HOTS levels (4–6) are where genuine learning depth is demonstrated.

Reference: Anderson, L.W. & Krathwohl, D.R. (Eds.) (2001). *A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy of Educational Objectives*. Longman.

---

### EduEval (2025) {#edueval}

| Field | Details |
|-------|---------|
| **Authors** | Not individually listed in accessible abstract; institutional affiliation: multiple Chinese universities |
| **Year** | November 2025 (arXiv:2512.00290) |
| **Title** | "EduEval: A Hierarchical Cognitive Benchmark for Evaluating Large Language Models in Education" |
| **URLs** | [arXiv abstract](https://arxiv.org/html/2512.00290v1) · [arXiv PDF](https://www.arxiv.org/pdf/2512.00290) |

**Key Methodology:**  
EduEval introduces the **EduAbility Taxonomy**, which integrates Bloom's Revised Taxonomy with Webb's Depth of Knowledge (DOK) into a 6-dimensional framework specifically designed for K-12 educational LLM evaluation:

| Dimension | Maps to | Description |
|-----------|---------|-------------|
| Memorization | Bloom L1 + DOK 1 | Factual recall |
| Understanding | Bloom L2 + DOK 1–2 | Concept comprehension |
| Application | Bloom L3 + DOK 2–3 | Applying knowledge |
| Reasoning | Bloom L4–5 + DOK 3 | Analysis and synthesis |
| Creativity | Bloom L6 + DOK 4 | Novel construction |
| Ethics | (New dimension) | Moral reasoning in educational contexts |

**Dataset:** >11,000 questions across 24 task types from genuine Chinese K-12 classroom scenarios (including dialogue classification and essay scoring). Multi-agent human-in-the-loop annotation pipeline.

**Key Findings:**
- LLM performance approaches ceiling at Memory/Understanding levels.
- Application and Reasoning dimensions remain challenging.
- No existing standard benchmark covers the Evaluate, Create, or Ethics dimensions.
- Neither Bloom's nor Webb's DOK alone is sufficient; integration is necessary for comprehensive assessment.

**Limitations:**
- Chinese K-12 context limits direct generalizability to English-language or higher education ASAG.
- The Ethics dimension is newly introduced and lacks validation against established psychological frameworks.
- Dataset construction relies on LLM classifiers, which could introduce circular biases.

---

### BloomAPR (2025) {#bloomapr}

| Field | Details |
|-------|---------|
| **Authors** | Yinghang Ma, Jiho Shin, Leuson Da Silva, Zhen Ming (Jack) Jiang, Song Wang, Foutse Khomh, Shin Hwei Tan |
| **Institutions** | York University (Toronto), Polytechnique Montréal, Concordia University |
| **Year** | September 2025 (arXiv:2509.25465; submitted to ACM TOSEM) |
| **Title** | "BloomAPR: A Bloom's Taxonomy-based Framework for Assessing the Capabilities of LLM-Powered APR Solutions" |
| **URLs** | [arXiv abstract](https://arxiv.org/abs/2509.25465) · [arXiv HTML](https://arxiv.org/html/2509.25465v1) · [Semantic Scholar](https://www.semanticscholar.org/paper/BloomAPR:-A-Bloom's-Taxonomy-based-Framework-for-of-Ma-Shin/5f36e7a57fb2e13ed3137ed750e183083d7dd9ac) |

**Key Methodology:**  
BloomAPR is a **dynamic evaluation framework** for Automated Program Repair (APR) that maps evaluation tasks to Bloom's Taxonomy layers. Unlike typical ASAG, it targets code repair rather than natural language grading, but its Bloom's mapping methodology is highly relevant to cognitive depth assessment:

| Bloom Layer | APR Evaluation Method | Key Question |
|-------------|----------------------|-------------|
| **Remember** | Membership inference; known bug patterns | Has the model seen this bug before? |
| **Understand** | LLM-generated synthetic bugs with same semantics | Can it understand the *logic* of the bug? |
| **Apply** | Inject known bug patterns into new projects | Can it apply fix patterns in new contexts? |
| **Analyze** | Behavioral-preserving code transformations (variable renaming, AST manipulation) | Is the model brittle to surface changes? |
| **Evaluate / Create** | Not yet implemented in prototype | — |

**Models Evaluated:** ChatRepair, CigaR under GPT-3.5-Turbo, Llama-3.1, StarCoder-2 on Defects4J benchmark.

**Key Findings:**
- LLM-powered APR systems fix up to **81.57% of bugs at the Remember layer** (known patterns).
- Performance drops to **up to 60.66% at Understand** (semantically equivalent but novel bugs).
- Further drop at **Apply** (13.46% to 41.34%), with up to **43.32% decrease** for minor syntactic changes.
- Demonstrates severe **brittleness** — models that appear competent on static benchmarks fail dramatically when surface representations change.
- Data contamination is a significant threat to static benchmark validity.

**Limitations:**
- Evaluate and Create layers not yet implemented.
- Currently domain-specific to software bug-fixing, not natural language ASAG.
- Benchmark restricted to Defects4J; generalizability to SWE-bench is future work.

---

### LLMs meet Bloom's Taxonomy — COLING 2025 {#llms-blooms}

| Field | Details |
|-------|---------|
| **Authors** | Thomas Huber, Christina Niklaus |
| **Institution** | University of St. Gallen, Switzerland |
| **Year** | January 2025 |
| **Venue** | *Proceedings of the 31st International Conference on Computational Linguistics (COLING 2025)*, pages 5211–5246, Abu Dhabi, UAE |
| **URLs** | [ACL Anthology](https://aclanthology.org/2025.coling-main.350/) · [PDF](https://aclanthology.org/2025.coling-main.350.pdf) |

**Key Methodology:**  
The paper maps **commonly used LLM benchmarks** to Bloom's Taxonomy levels via:
1. **Human annotation** — Expert annotators labeled benchmark tasks by cognitive dimension.
2. **LLM annotation** — GPT-4, GPT-4o, Claude 3, Llama 3 annotated the same tasks.
3. **RoBERTa classifier** — Fine-tuned on 21,380 Bloom's-labeled learning objectives (xlm-roberta-base).

Inter-rater agreement measured using Cohen's Weighted Kappa. Then LLM performance scores on each benchmark were aggregated by Bloom's level to reveal cognitive profiles.

**Benchmark coverage analysis:**

| Bloom Level | Coverage by Current Benchmarks |
|-------------|-------------------------------|
| Remember | 1 task — severely underrepresented |
| Understand | 11 tasks |
| Apply | 15 tasks — most represented |
| Analyze | 16 tasks, but LLMs show weakness here |
| Evaluate | **0 tasks** — completely absent |
| Create | **0 tasks** — completely absent |

**Key Findings:**
- LLMs generally **perform better on the lower end** of the taxonomy (Remember, Understand, Apply).
- Pronounced **weakness at the Analyze dimension** in higher-order reasoning.
- **Evaluate and Create** are entirely unrepresented in current standard benchmarks (MT-Bench partially addresses this but is not mainstream).
- Average human-LLM inter-rater agreement on cognitive dimension: **κ ≈ 0.63** (high reliability for taxonomy mapping).
- Average human-LLM agreement on knowledge type: **κ ≈ 0.30** (much lower; knowledge typing is harder).

**Limitations:**
- Benchmark subtasks may contain multiple cognitive levels in a single task instance; aggregate labeling loses within-task variance.
- The RoBERTa classifier trained on learning objectives may not generalize perfectly to benchmark tasks.
- Does not compare LLM performance to human baselines at each taxonomy level.

---

### Chain-of-Thought Prompting — Cohn et al. 2024 (AAAI/EAAI) {#cohn-2024}

| Field | Details |
|-------|---------|
| **Authors** | Clayton Cohn, Nicole Hutchins, Tuan Le, Gautam Biswas |
| **Institutions** | Vanderbilt University (Cohn, Hutchins, Biswas); separate affiliation (Le) |
| **Year** | 2024 |
| **Title** | "A Chain-of-Thought Prompting Approach with LLMs for Evaluating Students' Formative Assessment Responses in Science" |
| **Venue** | EAAI-24 (14th Symposium on Educational Advances in Artificial Intelligence, co-located with AAAI 2024); DOI: 10.1609/aaai.v38i21.30364 |
| **URLs** | [arXiv abstract](https://arxiv.org/abs/2403.14565) · [arXiv HTML](https://arxiv.org/html/2403.14565v1) |

**Key Methodology:**  
The study uses GPT-4 to score and explain short-answer responses to K-12 Earth Science formative assessments (water runoff curriculum; NGSS-aligned). The four-component approach:

1. **Zero-Shot Baseline** — rubric in prompt, no examples.
2. **Few-Shot** — rubric + few labeled examples.
3. **Few-Shot + CoT** — labeled examples with explicit chain-of-thought reasoning chains: *"The student says X. The rubric states Y. Based on the rubric, the student earned a score of Z."*
4. **CoT + Active Learning (CoT + AL)** — iterative addition of reasoning chains targeting observed failure patterns (error analysis on validation set).

Human-in-the-loop: Inter-Rater Reliability (IRR) among two human scorers (Cohen's κ > 0.7); consensus scores as ground truth. Model evaluated across 3 formative assessment questions (Q1, Q2, Q3) with subscores for conceptual knowledge and scientific reasoning.

**Key Findings/Metrics:**

| Condition | Best QWK | Notable Pattern |
|-----------|----------|-----------------|
| Zero-Shot | 0.65–0.85 | Already reasonable for simpler concepts |
| Few-Shot | 0.55–1.00 | High variance; sometimes worse than zero-shot |
| Few-Shot + CoT | 0.80–0.95 | Consistent improvement for science concepts |
| **CoT + AL** | **0.87–0.95** | Best overall; QWK ≥ 0.8 for 9/11 subscores + totals |

- 4 subscores reached QWK > 0.90 ("almost perfect" agreement) with CoT + AL.
- Science **concepts** (factual knowledge application) were easier to grade reliably than **reasoning** (explaining via principles like conservation of matter).
- CoT initially *hurts* performance on simple tasks (over-complicates reasoning), but improves it for multi-component science explanations.

**Key Insight for Bloom's:** Scientific reasoning scores (Bloom's Analyze/Evaluate) showed lower grading reliability and benefited more from CoT, while factual concept scores (Bloom's Remember/Apply) were more reliably graded even zero-shot. This empirically supports the finding that higher-order thinking is harder to automate.

**Limitations:**
- Small, imbalanced dataset; one school setting in the US Southeast.
- CoT + AL risks **overfitting** to the validation set patterns.
- Model exhibits **keyword sensitivity** (e.g., presence of "because" as a reasoning cue).
- Privacy/bias concerns in K-12 deployment.
- Does not explicitly frame scoring in terms of Bloom's levels; conceptual understanding depth is a proxy of rubric compliance.

---

### Emirtekin & Özarslan 2025 — LLM-Human Agreement Drops at Higher Cognitive Levels {#emirtekin-2025}

| Field | Details |
|-------|---------|
| **Authors** | Emrah Emirtekin, Yasin Özarslan |
| **Year** | 2025 (published online Dec 2025; journal volume Jan 2026) |
| **Title** | "Automatic Short-Answer Grading in Sustainability Education: AI-Human Agreement" |
| **Journal** | *Journal of Computer Assisted Learning*, vol. 42, no. 1 (SSCI, Scopus) |
| **URLs** | [Wiley Online Library](https://onlinelibrary.wiley.com/doi/10.1002/jcal.70160) · [Avesis record](https://avesis.mcbu.edu.tr/yayin/8adc6694-7e10-4913-8d60-0c817f9f764d/automatic-short-answer-grading-in-sustainability-education-ai-human-agreement) |

**Key Methodology:**
- **232 short-answer responses** from a university-level Sustainability course (domain requiring contextual, interdisciplinary reasoning).
- **Rubric aligned with Bloom's Revised Taxonomy** — each criterion maps to a Bloom's cognitive level.
- LLMs evaluated: **GPT-4o, Gemini 2.0 Flash, DeepSeek V3, LLaMA 3.3**.
- Statistical comparison of consensus human scores vs. LLM scores using:
  - **QWK** (Quadratic Weighted Kappa)
  - **ICC** (Intraclass Correlation Coefficient)
  - **Pearson correlation**
  - **Distributional overlap (eta)**

**Key Findings/Metrics:**

| Measure | LLM-Human Agreement | Human-Human Agreement |
|---------|--------------------|-----------------------|
| QWK | **0.585–0.640** | — |
| Pearson r | **0.660–0.668** | — |
| Eta (distributional overlap) | **0.681–0.803** | — |
| ICC (humans) | — | **0.667–0.800** (good to excellent) |

**Critical finding:** Criterion-level agreement **systematically declined as Bloom's cognitive complexity increased**. Agreement at higher-order skill criteria (Analyze, Evaluate, Create) was notably low. Overall:

> "LLM-human agreement was moderate on total scores but declined at higher cognitive levels, indicating that LLMs are suitable for basic comprehension checks while human oversight remains necessary for complex reasoning."

**Significance:** This is the most direct empirical evidence (as of 2025) for the hypothesis that ASAG systems — even modern LLMs — cannot reliably grade responses requiring higher-order thinking. It establishes a clear **cognitive ceiling** for current automated grading reliability.

**Limitations:**
- Single course/domain (Sustainability); may not generalize.
- LLMs were not fine-tuned for this specific task.
- Human consensus process is not fully described (how were disagreements resolved?).
- Does not examine whether different prompting strategies (e.g., CoT) would improve higher-order agreement.

---

## Topic 3: SOLO Taxonomy for Depth Assessment {#topic-3}

### SOLO Taxonomy Overview {#solo-overview}

**SOLO (Structure of Observed Learning Outcomes)** was developed by John Biggs and Kevin Collis (1982, revised 2014). Unlike Bloom's Taxonomy, which classifies the *type* of cognitive process required by a task, SOLO classifies the **structural quality of a student's actual response** — measuring how many relevant concepts the student demonstrates and how well they integrate those concepts.

**The Five SOLO Levels:**

| Level | Name | Description | Knowledge Quality |
|-------|------|-------------|-------------------|
| 0 | **Prestructural** | Response uses no relevant concepts; irrelevant information; clear misconceptions. Student misses the point. | No meaningful knowledge |
| 1 | **Unistructural** | Response demonstrates exactly one relevant concept, with no integration of other ideas. | Quantity: minimal |
| 2 | **Multistructural** | Response demonstrates several relevant concepts, but these remain isolated — not connected or integrated. | Quantity: sufficient; Quality: fragmented |
| 3 | **Relational** | Response demonstrates a fully integrated understanding; all relevant concepts are connected into a coherent whole. | Quantity + Quality: integrated |
| 4 | **Extended Abstract** | Response goes beyond the immediate task; student generalizes principles to novel contexts, hypothetical constructs, or abstract theories. | Depth: transcendent |

**Movement from prestructural → multistructural** represents growth in **knowledge quantity** (the student knows more facts).  
**Movement from multistructural → extended abstract** represents growth in **knowledge quality** (the student integrates and transcends those facts).

Biggs & Collis's key design principle: SOLO levels *arise naturally from the understanding of the material itself*, unlike Bloom's levels which are set a priori by the teacher as external standards. This means SOLO is fundamentally **response-adaptive** — it reads what the student actually produced and classifies its structural complexity, rather than checking whether it meets predetermined criteria.

Original source: Biggs, J. & Collis, K. (1982). *Evaluating the Quality of Learning: The SOLO Taxonomy (Structure of the Observed Learning Outcome)*. Academic Press.

---

### Fernandez & Guzon 2025 {#fernandez-2025}

| Field | Details |
|-------|---------|
| **Authors** | Patrick John Martinez Fernandez, Angela Fatima Hilado Guzon |
| **Institution** | Department of Mathematics, Ateneo de Manila University, Quezon City, Philippines |
| **Year** | 2025 (received Jan 22; revised Mar 25; accepted Apr 18; published online Apr 21) |
| **Title** | "A SOLO Taxonomy-based rubric for assessing conceptual understanding in applied calculus" |
| **Journal** | *Journal on Mathematics Education*, 16(2), 559–580 |
| **DOI** | https://doi.org/10.22342/jme.v16i2.pp559-580 |
| **URLs** | [JME article](https://jme.ejournal.unsri.ac.id/index.php/jme/article/view/3580) · [PDF](https://jme.ejournal.unsri.ac.id/index.php/jme/article/download/3580/335) |

**Key Methodology:**

The study has a twofold purpose: (1) develop a SOLO-based rubric for applied calculus conceptual understanding; and (2) validate it on student responses.

**Rubric Development Process:**
1. Identified **conceptual knowledge components** for each calculus item (components validated by an expert with 10+ years of university calculus / real analysis teaching).
2. For each student solution, categorized each knowledge component as: *explicitly expressed*, *implied*, *incorrectly demonstrated*, or *absent*.
3. Classified the solution's SOLO level using a rubric mapping *capacity* (number of relevant concepts demonstrated) and *relating operation* (degree of integration among demonstrated concepts).
4. Included **transitional levels** (e.g., a MR level between Multistructural and Relational) to capture nuanced, in-between responses — particularly important in mathematics where conceptual development happens in small steps.
5. Provided **qualitative feedback** justifying each SOLO assignment.

**Special adjustments for mathematics:**
- Solutions lacking verbal explanations were penalized one SOLO level if the absence of explanation reduced clarity of integration.
- Unconventional but correct solutions were handled explicitly.
- Transitional levels had sub-distinctions: *low integration* (emerging connections) vs. *high integration* (logical connections with minor gaps).

**Study Population:** 57 first-year undergraduate students (chemistry and computer science majors) at a private Philippine university. Test items: linear approximations and the Extreme Value Theorem — items specifically designed to require conceptual understanding with minimal procedural components.

**Interrater Reliability:**

| Item | Weighted Cohen's κ | Qualitative Interpretation |
|------|--------------------|---------------------------|
| Item 5 (Linear Approx.) | **0.659** | Substantial agreement |
| Item 6 (Extreme Value Theorem) | **0.667** | Substantial agreement |

**Key Findings:**
- For Item 5: **63% of responses at multistructural level or below** — students could identify and demonstrate relevant knowledge components but could not *integrate* them.
- The rubric successfully differentiated levels and revealed key patterns:
  - **Reasoning gaps** — students knew procedures but couldn't explain underlying principles.
  - **Reliance on symbolic manipulation** without conceptual grounding.
  - **Misconceptions in mathematical logic** (e.g., incorrectly applying differentiability conditions).
- The rubric is adaptable beyond calculus, suggesting broader applicability for conceptually-oriented mathematics assessment.

**Limitations:**
- Small sample (57 students); single institution; Philippines context.
- Primary evaluator rated all responses; secondary validation used only 3 solutions per item per rater.
- Rubric development process was iterative and not fully formal (post-hoc reliability serves as validity evidence).
- Manual SOLO classification is time-intensive; no automated NLP implementation is provided.
- Transitional levels add complexity and may reduce reliability in less-trained raters.

---

### SOLO vs. Bloom's: Why SOLO May Better Measure Understanding Depth {#solo-vs-blooms}

The Fernandez & Guzon (2025) paper draws a definitive distinction between the two frameworks:

| Dimension | Bloom's Revised Taxonomy | SOLO Taxonomy |
|-----------|--------------------------|---------------|
| **What it classifies** | *Type* of cognitive process required by a task | *Structural quality* of the student's actual response |
| **Standard-setting** | A priori — teacher sets standards and checks if criteria are met | Empirical — levels arise naturally from the student's response |
| **Unit of analysis** | The learning objective / task design | The individual student response |
| **Scoring logic** | "Does this response meet Level X criteria?" | "What is the structural complexity of what the student actually wrote?" |
| **Suitability for rubric** | "Based on judgments about quality, which may be arbitrary" (Biggs & Collis, 2014, p. 13) | Directly suitable; describes what was observed, not what was expected |
| **Best for** | Designing curriculum and assessments at different levels | Evaluating depth of understanding in student-generated responses |
| **Knowledge quality** | Implicit in the level definitions | Explicit: quantity (uni/multi) vs. quality (relational/extended abstract) |
| **Conceptual integration** | Not explicitly modeled | Central: distinguishes "knows many facts" from "integrates facts into understanding" |

**The key insight for ASAG research:** SOLO is directly suited to the task of automated understanding-depth assessment because it describes the response itself rather than checking against external criteria. An ASAG system grounded in SOLO would not ask "does this match the reference answer?" but instead "how many relevant conceptual components does this response contain, and how well are they integrated?" — a fundamentally different computational problem requiring deeper semantic understanding.

**Additional comparison with Bloom's beyond Fernandez & Guzon:**
- SOLO explicitly captures the transition from *surface learning* (quantity-driven; Uni/Multi levels) to *deep learning* (quality-driven; Relational/Extended Abstract), which corresponds roughly to Hattie's (2009) surface/deep/transfer learning model.
- Bloom's six levels are cognitively heterogeneous (memory recall and creative synthesis are both defined a priori); SOLO levels are structurally homogeneous (all defined by the same two dimensions: capacity and relating operation).
- For open-ended responses in mathematics, science, and humanities, SOLO provides a more natural and less teacher-dependent framework for automated classification.

---

## Topic 4: Somers et al. (2021) — NLP for Conceptual Understanding {#topic-4}

| Field | Details |
|-------|---------|
| **Authors** | Rick Somers, Sam Cunningham-Nelson, Wageeh W. Boles |
| **Institution** | Queensland University of Technology (implied from prior related work by Cunningham-Nelson & Boles); Australia |
| **Year** | 2021 |
| **Title** | "Applying natural language processing to automatically assess student conceptual understanding from textual responses" |
| **Journal** | *Australasian Journal of Educational Technology* |
| **URLs** | [Semantic Scholar record](https://www.semanticscholar.org/paper/Applying-natural-language-processing-to-assess-from-Somers-Cunningham-Nelson/74ddc64ccd760df61031b4640c3fee45e5e1ce79) · [EBSCOhost](https://search.ebscohost.com/login.aspx?direct=true&profile=ehost&scope=site&authtype=crawler&jrnl=14493098&AN=154035111) |

**Context:**  
This paper builds on a series of prior work by Cunningham-Nelson and Boles on automated textual analysis for formative assessment in electrical engineering education. It represents one of the earliest attempts to go *beyond correctness* — explicitly distinguishing between (1) whether a student's free-text justification is valid, and (2) whether the student expresses *confidence* in their response — as proxies for the *level* and *nature* of conceptual understanding.

---

### Key Methodology

**Models evaluated:** Four transformer-based NLP models, selected for their ability to achieve high performance on small datasets:
- **ELECTRA-small** (generator-discriminator architecture; efficient on small corpora)
- **RoBERTa-base** (robustly optimized BERT with dynamic masking)
- **XLNet-base** (autoregressive bidirectionality with Transformer-XL memory)
- **ALBERT-base-v2** (lightweight BERT with cross-layer parameter sharing; 12M parameters)

**Two distinct assessment targets** (the "level and nature" framing):

1. **Free-text validity** — Is the student's justification of their answer conceptually valid?  
   → Binary classification (valid / invalid).  
   → Ensemble model combining predictions from all four NLP models.

2. **Confidence in response** — Does the student express high or low confidence in their response?  
   → Binary classification (high / low confidence).  
   → Single best-performing model.  

The combination of (1) and (2) enables 4 quadrant interpretations:
- Valid + High Confidence = genuine conceptual understanding
- Valid + Low Confidence = fragile or uncertain understanding
- Invalid + High Confidence = confident misconception
- Invalid + Low Confidence = guessing or confusion

**Training data:** Fewer than 100 student responses per question — demonstrating feasibility with realistic classroom dataset sizes.

---

### Key Findings/Metrics

| Task | Best Accuracy Range | Model(s) |
|------|--------------------|---------:|
| Free-text validity (ensemble) | **91.46% – 98.66%** | ELECTRA-small, RoBERTa-base, XLNet-base, ALBERT-base-v2 |
| Confidence-in-response | **93.07% – 99.46%** | Best single model (not specified in available abstract) |

**The critical conceptual contribution:**  
> "Students' conceptual understanding can be accurately and automatically extracted from their short answer responses using NLP to assess the level and nature of their understanding, without the overhead of traditional formative assessment."

This reframes ASAG not as a grading problem but as a **conceptual understanding classification problem**. The paper demonstrates that NLP models can operationalize the difference between knowing the right answer and understanding why it is right — a distinction most ASAG systems ignore.

**Practical implications stated by authors:**
- Educators and students can receive feedback on *conceptual understanding* as needed, without manual formative assessment overhead.
- Accurate models can be built with fewer than 100 student responses — removing the data scalability barrier for individual instructors.

---

### Limitations

- The full methodology (dataset construction, specific question types, domain) is not fully accessible from the abstract; the paper likely focuses on electrical engineering concepts.
- Binary classifications (valid/invalid; high/low confidence) are coarse; they do not provide the granularity of SOLO or Bloom's levels.
- The confidence-in-response signal may be influenced by writing style or personality rather than actual epistemic state.
- The models are not evaluated on cross-domain generalization (a new question type may require retraining).
- This paper focuses on *detecting* the level and nature of understanding, not on *scoring* or *grading* — it does not report standard ASAG metrics (QWK, Pearson r, RMSE).
- The approach is formative (feedback-oriented), not summative — it should not be compared directly to score-prediction ASAG systems.

---

### Relationship to Broader ASAG Field

As noted in a 2023 systematic review ([Automatic Assessment of Text-Based Responses, arXiv:2308.16151](https://arxiv.org/pdf/2308.16151)):

> "Somers et al. (2021) used transformer-based NLP models to evaluate student conceptual understanding. The output of this TBAAS is their customized level of understanding with more than 90% accuracy."

This situates the paper as one of a small set of systems that explicitly targets understanding depth rather than surface-level correctness. Most ASAG systems reviewed in the same survey produce *classification labels* or *scores/grades* — Somers et al. uniquely produces a *conceptual profile* (validity + confidence) that maps to a multi-dimensional theory of understanding.

---

## Cross-Topic Synthesis & Implications {#synthesis}

### The Depth Gap in ASAG

The through-line connecting all four research topics is a **depth gap**: automated systems can measure whether a response is textually similar to a reference answer, and LLMs can do this at moderate human agreement levels, but none of the current mainstream ASAG systems systematically measure the *depth* or *structural quality* of the student's conceptual understanding.

```
Surface-Level ←————————————————————————————————→ Deep Understanding
[Cosine Similarity]  [LLM Scoring]  [CoT Prompting]  [SOLO/Bloom-aware NLP]
     GradeAid          EngSAF           Cohn 2024         Somers 2021
```

The Emirtekin & Özarslan (2025) finding — that LLM-human agreement drops systematically at higher Bloom's levels — quantifies exactly this gap. Even the most capable LLMs (GPT-4o, Gemini 2.0 Flash) cannot reliably judge responses requiring Analyze, Evaluate, or Create-level cognition, precisely because they are measuring textual alignment rather than conceptual depth.

### Taxonomy Fit for ASAG Applications

| Use Case | Best-Fit Framework | Reason |
|----------|--------------------|--------|
| Designing assessment questions at specific cognitive levels | Bloom's Revised Taxonomy | A priori task design framework |
| Grading essays or short answers for depth of understanding | SOLO Taxonomy | Empirical, response-adaptive; captures integration quality |
| Benchmarking LLMs on cognitive reasoning | Bloom's (as in Huber & Niklaus COLING 2025) | Hierarchical levels map to task difficulty |
| Formative assessment of conceptual understanding | NLP validity + confidence (Somers et al. 2021) | Direct operationalization of understanding nature |
| Automated program repair evaluation | BloomAPR cognitive layers | Structured brittleness diagnosis |

### Open Research Questions

1. Can SOLO taxonomy levels be predicted from short free-text responses using transformer-based NLP models? Fernandez & Guzon (2025) develop the rubric; no automated classifier yet exists.
2. Can the Somers et al. (2021) validity/confidence dual-axis model be extended to predict full SOLO levels?
3. Can NodeGrade or similar node-graph ASAG systems incorporate SOLO-level nodes that explicitly assess integration depth rather than similarity to reference?
4. Can chain-of-thought prompting (Cohn et al. 2024 style) be re-engineered to elicit Bloom's level-specific reasoning from student answers — making the *cognitive level* of the response an output, not just a correctness score?
5. What is the practical inter-rater reliability ceiling for human SOLO classification of short answers at scale (as baseline for automated approaches)?

---

## Full Citation Reference List

1. **Fischer et al. (2025).** Evaluation of a Node-based Automatic Short Answer Tool "NodeGrade." ACM. DOI: 10.1145/3723010.3723021. [https://dl.acm.org/doi/abs/10.1145/3723010.3723021](https://dl.acm.org/doi/abs/10.1145/3723010.3723021)

2. **del Gobbo, E., Guarino, A., Cafarelli, B., & Grilli, L. (2023).** GradeAid: a framework for automatic short answers grading in educational contexts — design, implementation and evaluation. *Knowledge and Information Systems*. DOI: 10.1007/s10115-023-01892-9. [https://pmc.ncbi.nlm.nih.gov/articles/PMC10197042/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10197042/)

3. **Aggarwal, D., Sil, P., Raman, B., & Bhattacharyya, P. (2024).** "I understand why I got this grade": Automatic Short Answer Grading with Feedback. arXiv:2407.12818. [https://arxiv.org/abs/2407.12818](https://arxiv.org/abs/2407.12818)

4. **Dzikovska, M. et al. (2013).** SemEval-2013 Task 7: The Joint Student Response Analysis and 8th Recognizing Textual Entailment Challenge. *SemEval 2013*. [https://aclanthology.org/S13-2045.pdf](https://aclanthology.org/S13-2045.pdf)

5. **Mohler, M. et al. (2011).** Learning to Grade Short Answer Questions using Semantic Similarity Measures and Dependency Graph Alignments. ACL 2011. [University of North Texas dataset; widely cited as "Mohler dataset"]

6. **Anderson, L.W. & Krathwohl, D.R. (Eds.) (2001).** A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy of Educational Objectives. Longman. [Foundational reference; no URL — standard citation]

7. **Huber, T. & Niklaus, C. (2025).** LLMs meet Bloom's Taxonomy: A Cognitive View on Large Language Model Evaluations. *Proceedings of COLING 2025*, pp. 5211–5246. [https://aclanthology.org/2025.coling-main.350/](https://aclanthology.org/2025.coling-main.350/)

8. **EduEval authors (2025).** EduEval: A Hierarchical Cognitive Benchmark for Evaluating Large Language Models in Education. arXiv:2512.00290. [https://arxiv.org/html/2512.00290v1](https://arxiv.org/html/2512.00290v1)

9. **Ma, Y., Shin, J., Da Silva, L., Jiang, Z.M., Wang, S., Khomh, F., & Tan, S.H. (2025).** BloomAPR: A Bloom's Taxonomy-based Framework for Assessing the Capabilities of LLM-Powered APR Solutions. arXiv:2509.25465. [https://arxiv.org/abs/2509.25465](https://arxiv.org/abs/2509.25465)

10. **Cohn, C., Hutchins, N., Le, T., & Biswas, G. (2024).** A Chain-of-Thought Prompting Approach with LLMs for Evaluating Students' Formative Assessment Responses in Science. EAAI-24 at AAAI. DOI: 10.1609/aaai.v38i21.30364. [https://arxiv.org/abs/2403.14565](https://arxiv.org/abs/2403.14565)

11. **Emirtekin, E. & Özarslan, Y. (2025/2026).** Automatic Short-Answer Grading in Sustainability Education: AI-Human Agreement. *Journal of Computer Assisted Learning*, vol. 42, no. 1. [https://onlinelibrary.wiley.com/doi/10.1002/jcal.70160](https://onlinelibrary.wiley.com/doi/10.1002/jcal.70160)

12. **Fernandez, P.J.M. & Guzon, A.F.H. (2025).** A SOLO Taxonomy-based rubric for assessing conceptual understanding in applied calculus. *Journal on Mathematics Education*, 16(2), 559–580. DOI: 10.22342/jme.v16i2.pp559-580. [https://jme.ejournal.unsri.ac.id/index.php/jme/article/view/3580](https://jme.ejournal.unsri.ac.id/index.php/jme/article/view/3580)

13. **Biggs, J. & Collis, K. (1982/2014).** Evaluating the Quality of Learning: The SOLO Taxonomy (Structure of the Observed Learning Outcome). Academic Press. [Foundational reference; no URL]

14. **Somers, R., Cunningham-Nelson, S., & Boles, W.W. (2021).** Applying natural language processing to automatically assess student conceptual understanding from textual responses. *Australasian Journal of Educational Technology*. [https://www.semanticscholar.org/paper/Applying-natural-language-processing-to-assess-from-Somers-Cunningham-Nelson/74ddc64ccd760df61031b4640c3fee45e5e1ce79](https://www.semanticscholar.org/paper/Applying-natural-language-processing-to-assess-from-Somers-Cunningham-Nelson/74ddc64ccd760df61031b4640c3fee45e5e1ce79)
