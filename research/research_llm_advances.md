# LLM Cognitive Assessment and Recent Advances: Research Findings

> Compiled: March 20, 2026  
> Research scope: 2024–2026, with selected foundational work

---

## Table of Contents

1. [Topic 1: LLM-Based Cognitive Level Classification](#topic-1-llm-based-cognitive-level-classification)
   - [Bloom's Taxonomy and LLMs Overview](#blooms-taxonomy-and-llms-overview)
   - [Chain-of-Thought Prompting for Educational Assessment (Cohn et al., 2024)](#chain-of-thought-prompting-for-educational-assessment)
   - [CoTAL: Extended Follow-up (Cohn et al., 2025)](#cotal-extended-follow-up)
   - [Few-Shot Grading with LLMs (Zhao et al., 2025)](#few-shot-grading-with-llms-zhao-et-al-2025)
   - [LLMarking: Adaptive ASAG with LLMs (Chi & Zhu, 2025)](#llmarking-adaptive-asag-with-llms)
   - [Prompt Engineering for Concept Understanding vs. Simple Scoring](#prompt-engineering-for-concept-understanding-vs-simple-scoring)

2. [Topic 2: Recent ASAG Advances (2024–2025)](#topic-2-recent-asag-advances-2024-2025)
   - [ASAG2024 Benchmark (Meyer et al., 2024)](#asag2024-benchmark-meyer-et-al-2024)
   - [Beyond Human Subjectivity (Gobrecht et al., 2024)](#beyond-human-subjectivity-gobrecht-et-al-2024)
   - [Cross-Prompt ASAG (Krisnawati et al., 2025)](#cross-prompt-asag)
   - [BERT+GRU Hybrid (Joseph & Varghese, 2025)](#bertgru-hybrid-joseph--varghese-2025)
   - [MMSAF: Multimodal Short Answer Grading (Sil et al., 2025)](#mmsaf-multimodal-short-answer-grading-sil-et-al-2025)
   - [Arabic ASAG with AraBERTv2 (Mahmood, 2025)](#arabic-asag-with-arabertv2-mahmood-2025)
   - [Hybrid ANN + Text Similarity for Polish (Bani Saad et al., 2025)](#hybrid-ann--text-similarity-for-polish-bani-saad-et-al-2025)

3. [Topic 3: Concept-Aware NLP Approaches](#topic-3-concept-aware-nlp-approaches)
   - [Knowledge-Based Validation (Hondarangala & Wickramaarachchi, 2025)](#knowledge-based-validation-hondarangala--wickramaarachchi-2025)
   - [Concept Extraction from Text Using NLP/LLMs](#concept-extraction-from-text-using-nlpllms)
   - [Relation Extraction Between Concepts in Student Answers](#relation-extraction-between-concepts-in-student-answers)
   - [Comparing Against Reference Ontologies](#comparing-against-reference-ontologies)
   - [NLP Pipeline for Assessment Data (CE-JEME)](#nlp-pipeline-for-assessment-data)

4. [Topic 4: V-NLI Integration Opportunities](#topic-4-v-nli-integration-opportunities)
   - [NL4DV (Narechania et al., 2020)](#nl4dv-narechania-et-al-2020)
   - [DataTone (Gao et al., 2015)](#datatone-gao-et-al-2015)
   - [Chat2VIS (Maddigan & Susnjak, 2023)](#chat2vis-maddigan--susnjak-2023)
   - [Limitations in Educational Contexts](#limitations-of-existing-v-nli-systems-in-educational-contexts)
   - [Opportunity: Visualizing Concept Understanding Patterns](#opportunity-visualizing-concept-understanding-patterns)

5. [Cross-Cutting Synthesis](#cross-cutting-synthesis)
6. [Research Gaps and Future Directions](#research-gaps-and-future-directions)

---

## Topic 1: LLM-Based Cognitive Level Classification

### Bloom's Taxonomy and LLMs Overview

Bloom's Taxonomy provides a six-level hierarchy of cognitive skills—Remember, Understand, Apply, Analyze, Evaluate, Create—that educational assessment frameworks use to design and evaluate questions and answers. Recent work has increasingly applied LLMs not just to *score* short answers, but to *classify* the cognitive level of both questions and student responses.

**Key distinction**: Most ASAG systems assign a numeric score (correct/partially correct/incorrect). Cognitive level classification assigns a Bloom's level label, which conveys *depth of understanding* rather than mere correctness. This matters for formative feedback, curriculum gap analysis, and adaptive instruction.

---

### Chain-of-Thought Prompting for Educational Assessment

**Paper:** Cohn, C., Hutchins, N., Le, T., & Biswas, G. (2024). *A Chain-of-Thought Prompting Approach with LLMs for Evaluating Students' Formative Assessment Responses in Science.*  
**Published:** AAAI 2024  
**URL:** [https://ojs.aaai.org/index.php/AAAI/article/view/30364](https://ojs.aaai.org/index.php/AAAI/article/view/30364)  
**ArXiv mirror:** [https://arxiv.org/abs/2403.14565](https://arxiv.org/abs/2403.14565)

**Methodology:**
- Applies GPT-4 to automatically score and explain short-answer formative assessment responses in K-12 middle school Earth Science.
- Combines **few-shot prompting** (labeled examples), **active learning** (iterative human labeling of uncertain cases), and **chain-of-thought (CoT) reasoning** (requiring the model to reason step-by-step before assigning a score).
- Uses a **human-in-the-loop** design where teachers review and correct LLM outputs, with those corrections fed back to refine future prompts.
- Employs **Evidence-Centered Design (ECD)** to align rubrics with curriculum learning objectives.

**Key Findings:**
- GPT-4 with CoT prompting successfully scores short-answer science responses while also generating meaningful explanations for those scores.
- The human-in-the-loop refinement loop improves scoring accuracy and explanation quality iteratively.
- Explanations enable formative feedback beyond simple grade assignment.
- Chain-of-thought reasoning proves essential for open-ended science assessments where surface-form matching is insufficient.

**Metrics:** The paper focuses on qualitative analysis of pros/cons; specific Cohen's Kappa or QWK values are not prominently published in the AAAI abstract.

**Limitations:**
- Limited to middle school Earth Science; generalization to other domains tested separately in the follow-up CoTAL work.
- Human-in-the-loop remains labor-intensive even if reduced compared to full manual grading.
- GPT-4 dependency raises cost and API availability concerns for deployment at scale.

---

### CoTAL: Extended Follow-Up

**Paper:** Cohn, C., AshwinT., S., Mohammed, N., & Biswas, G. (2025). *CoTAL: Human-in-the-Loop Prompt Engineering for Generalizable Formative Assessment Scoring.*  
**Published:** April 3, 2025 (Semantic Scholar preprint)  
**URL:** [https://www.semanticscholar.org/paper/27ee7b71a805c4641db4578a0a4e7f5fa92c04b1](https://www.semanticscholar.org/paper/27ee7b71a805c4641db4578a0a4e7f5fa92c04b1)

**Methodology:**
- Extends the 2024 Cohn et al. work into the **CoTAL** framework (Chain-of-Thought Prompting + Active Learning).
- Explicitly tests whether the prompting methodology **generalizes across domains**: science, computing, and engineering.
- Three-component design: (1) ECD-aligned rubrics, (2) human-in-the-loop prompt engineering, (3) CoT + iterative teacher/student feedback for prompt refinement.

**Key Findings:**
- CoTAL improves GPT-4 scoring performance by **up to 38.9%** over a non-engineered baseline (no labeled examples, no CoT, no iteration).
- Generalization confirmed across science, computing, and engineering domains—a significant advance over prior domain-specific systems.
- Teacher and student feedback yields actionable insights that improve both grading accuracy and explanation quality.

**Limitations:**
- Requires iterative prompt engineering cycles with teacher involvement—not a one-shot deployment.
- Tested on K-12/early undergraduate contexts; higher education generalization is an open question.

---

### Few-Shot Grading with LLMs (Zhao et al., 2025)

**Paper:** Zhao, C., Silva, M., & Poulsen, S. (2025). *Language Models are Few-Shot Graders.*  
**Published:** February 18, 2025 (arXiv preprint)  
**URL:** [https://arxiv.org/abs/2502.13337](https://arxiv.org/abs/2502.13337)

**Methodology:**
- Presents a complete ASAG pipeline using state-of-the-art LLMs as few-shot graders.
- Compares three OpenAI models: **GPT-4**, **GPT-4o**, and **o1-preview**.
- Systematically investigates three strategies for incorporating instructor-graded examples into prompts:
  1. No examples (zero-shot)
  2. Random selection of few-shot examples
  3. **RAG-based selection** (retrieval-augmented generation selects the most semantically similar graded examples)
- Also evaluates the effect of integrating **grading rubrics** into the prompt.

**Key Findings:**
- The LLM-based ASAG pipeline outperforms existing custom-built models on the same benchmark datasets.
- **GPT-4o achieves the best balance** between accuracy and cost-effectiveness.
- **o1-preview** achieves higher raw accuracy but exhibits larger variance in error—making it less suitable for operational classroom use.
- Providing graded examples (few-shot) enhances accuracy over zero-shot; **RAG-based selection outperforms random selection**.
- Adding grading rubrics to prompts provides a structured evaluation standard that further improves accuracy.

**Metrics:** Outperforms custom-built baselines; specific QWK/accuracy values by dataset not extracted in this compilation (see full paper for per-dataset results).

**Limitations:**
- Relies on proprietary OpenAI models; cost and data privacy concerns limit deployment in institutions.
- RAG-based selection requires a database of pre-graded examples—cold-start problem for new courses.
- Variance in o1-preview outputs undermines reliability for high-stakes grading.

---

### LLMarking: Adaptive ASAG with LLMs

**Paper:** Chi, B., & Zhu, X. (2025). *LLMarking: Adaptive Automatic Short-Answer Grading Using Large Language Models.*  
**Published:** ACM, July 17, 2025  
**URL:** [https://dl.acm.org/doi/10.1145/3698205.3729551](https://dl.acm.org/doi/10.1145/3698205.3729551)  
**Author profile:** [https://biboyqg.github.io](https://biboyqg.github.io)

**Methodology:**
- Introduces **LLMarking**, a novel ASAG system built on LLMs with two core components:
  1. **Key Point Scoring Framework**: Decomposes model answers into discrete key points; evaluates student answers point-by-point rather than holistically.
  2. **Prompt Dynamic Adjustment**: Adapts the grading prompt based on the difficulty level and domain of the question, enabling flexible and context-sensitive assessment.
- Published through ACM, targeting the educational AI/NLP community.

**Key Findings:**
- The Key Point Scoring Framework enables granular, explainable feedback beyond binary or holistic scores.
- Prompt Dynamic Adjustment improves generalization across different subject domains and question types.
- LLMarking delivers "flexible, accurate, and explainable assessments across various educational contexts."

**Limitations:**
- Published as ACM paper with limited publicly accessible metrics at time of research compilation.
- Key Point decomposition requires model answers to be explicitly structured; messy or vague rubrics degrade performance.
- Prompt engineering overhead for new domains.

---

### Prompt Engineering for Concept Understanding vs. Simple Scoring

A critical distinction in the emerging literature is between prompts designed for **binary/holistic scoring** (correct vs. incorrect) versus prompts designed for **concept understanding evaluation**. The former is sufficient for factual recall (Bloom's L1–L2: Remember/Understand), but the latter requires the model to identify whether a student has correctly *applied*, *analyzed*, or *evaluated* a concept.

Key engineering strategies from the literature:

| Strategy | Description | Best For |
|---|---|---|
| Zero-shot with rubric | Prompt includes rubric only | Structured factual questions |
| Few-shot (random) | Adds graded examples | General ASAG |
| Few-shot (RAG) | Retrieves semantically similar examples | Domain-specific, nuanced questions |
| Chain-of-thought (CoT) | Requires step-by-step reasoning before scoring | Open-ended, higher-order thinking assessment |
| Bloom's-aligned CoT | CoT prompts specify which Bloom's level to evaluate | Cognitive level classification |

**Emerging insight**: Prompts that ask the LLM to first identify the *concepts* present in a student answer, then verify their accuracy and depth, outperform prompts that ask directly for a score—particularly for higher Bloom's levels (Analyze, Evaluate, Create). This is supported by the AMMORE dataset work ([Henkel et al., 2024](https://arxiv.org/abs/2409.17904)), which found that CoT prompting lifted edge-case grading accuracy from 98.7% to 99.9%.

---

## Topic 2: Recent ASAG Advances (2024–2025)

### ASAG2024 Benchmark (Meyer et al., 2024)

**Paper:** Meyer, G., Breuer, P., & Fürst, J. (2024). *ASAG2024: A Combined Benchmark for Short Answer Grading.*  
**Published:** ACM L@S 2024 (September 27, 2024)  
**URL (ACM):** [https://dl.acm.org/doi/10.1145/3649409.3691083](https://dl.acm.org/doi/10.1145/3649409.3691083)  
**URL (arXiv):** [https://arxiv.org/abs/2409.18596](https://arxiv.org/abs/2409.18596)

**Methodology:**
- Identifies a critical gap: prior ASAG evaluations used isolated datasets with incompatible structures and grading scales, making cross-system comparisons impossible.
- **ASAG2024** combines **seven commonly used short-answer grading datasets** into a unified structure with a common grading scale.
- Evaluates a curated set of recent SAG methods (including LLM-based and fine-tuned transformer approaches) across all seven constituent datasets.

**Key Findings:**
- LLM-based grading approaches reach **new state-of-the-art scores** across the combined benchmark.
- Despite LLM improvements, **LLM-based systems still fall significantly short of human performance** on complex, multi-domain short answers.
- The gap between LLM performance and human performance points to the need for hybrid human-machine SAG systems.
- The benchmark facilitates systematic generalizability testing that was previously impossible.

**Limitations:**
- Authors label this "preliminary work"—the benchmark may require further curation and expansion.
- Combining datasets with different origin domains (biology, computer science, history) flattens domain-specific performance differences.
- Does not address cognitive level (Bloom's) classification—only scoring correctness.

---

### Beyond Human Subjectivity (Gobrecht et al., 2024)

**Paper:** Gobrecht, A., Tuma, F., Möller, M., Zöller, T., Zakhvatkin, M., Wuttig, A., Sommerfeldt, H., & Schütt, S. (2024). *Beyond Human Subjectivity and Error: A Novel AI Grading System.*  
**Published:** May 7, 2024 (arXiv preprint)  
**URL:** [https://arxiv.org/abs/2405.04323](https://arxiv.org/abs/2405.04323)

**Methodology:**
- Introduces an ASAG system based on a **fine-tuned open-source transformer model** trained on a large collection of exam data from **university courses across multiple disciplines**.
- Runs two experiments:
  1. *Held-out test*: Evaluates model on unseen questions and unseen courses from the same institutions.
  2. *Human comparison*: Assembles a test set from real historical exams with official grades as ground truth. Both the model and **certified human domain experts** re-grade the same answers without seeing the historical grades.
- Compares both model errors and human re-grader errors against official historical grades as ground truth.

**Key Findings:**
- High accuracy on a broad spectrum of unseen questions, even in entirely unseen courses—strong generalization at scale.
- For the courses examined, **the model deviated less from official historical grades than the human re-graders**.
- The model's **median absolute error was 44% smaller** than human re-graders' median absolute error.
- Demonstrates that AI grading can reduce human subjectivity, improve consistency, and thereby increase fairness in education.

**Limitations:**
- Evaluated on a single institutional dataset—generalization to other universities or languages is unconfirmed.
- The "ground truth" (historical grades) itself carries embedded human subjectivity; perfect truth is not truly known.
- Open-source transformer architecture details and dataset specifics not fully disclosed.
- Does not address cognitive level classification—focuses exclusively on correctness scoring.

---

### Cross-Prompt ASAG

**Paper:** Krisnawati, et al. (2025). *Cross-Prompt Based Automatic Short Answer Grading System.*  
**Published:** October 2025 (researcher.life)  
**URL:** [https://discovery.researcher.life/article/cross-prompt-based-automatic-short-answer-grading-system/d68dcccaef9d3607975c93cad7131f70](https://discovery.researcher.life/article/cross-prompt-based-automatic-short-answer-grading-system/d68dcccaef9d3607975c93cad7131f70)

**Methodology:**
- Addresses a known weakness in ASAG: most systems require labeled training data for each specific question (prompt), making deployment expensive for new questions.
- Develops an ASAG system explicitly designed to transfer knowledge **across prompts**—training on graded answers for some questions, then grading answers to *different* questions.
- Tests in multiclass grading scenarios that "closely reflect real-world assessment scenarios."

**Key Findings:**
- Demonstrates measurable gains in cross-prompt generalization compared to prompt-specific baselines.
- Multiclass classification settings (partial credit, not just binary) add complexity that benefits from cross-prompt transfer.
- Bridging the gap between prompt-specific and prompt-agnostic grading is an active open problem.

**Limitations:**
- Specific performance metrics not publicly accessible at time of compilation; paper in preprint status.
- Cross-prompt transfer tends to degrade when subject domains vary widely.
- Short answer grading is inherently more challenging than essay scoring for cross-prompt transfer, as short answers are highly context-dependent.

**Related work:** See also [Funayama et al., 2024](https://arxiv.org/html/2408.13966v1) for cross-prompt pre-finetuning approaches using key phrase annotation, and [S-GRADES (Seuti & Ray Choudhury, 2026)](https://www.semanticscholar.org/paper/ca5715dd4cbc81b6deb98644ba11f37fb704d2de) for a new 14-dataset generalization benchmark.

---

### BERT+GRU Hybrid (Joseph & Varghese, 2025)

**Paper:** Joseph, N., & Varghese, S. M. (2025). *Investigating the BERT Capabilities with GRU Model in Semantic Extraction for Short Answer Grading Tasks: A Regression Problem.*  
**Published:** IEEE ICTEST 2025 (April 3, 2025)  
**URL:** [https://ieeexplore.ieee.org/document/11042547/](https://ieeexplore.ieee.org/document/11042547/)

**Methodology:**
- Frames ASAG as a **regression problem** (predicting scores on a 0–5 continuous scale) rather than a classification problem.
- Investigates three architectural configurations on a **small dataset** (a known challenge where overfitting is a major concern):
  1. BERT with standard fine-tuning
  2. GRU-only models for sequential dependency modeling
  3. **Hybrid BERT+GRU**: BERT embeddings serve as inputs to a GRU layer, combining transformer-based contextual representations with recurrent sequence modeling
- Evaluates architectural variants for their ability to handle the small-data, overfitting-prone regime typical of classroom-scale assessments.

**Key Findings:**
- **Hybrid BERT+GRU models effectively leverage the strengths of both architectures**: BERT captures rich contextual semantics; GRU models temporal/sequential dependencies in student response patterns.
- Hybrid models outperform BERT-alone and GRU-alone configurations on the regression task, especially in small-dataset settings.
- Offers a promising approach for automated answer evaluation when labeled training data is scarce.

**Metrics:** Predicts numerical scores (0–5); specific Pearson correlation or RMSE values not extracted.

**Limitations:**
- Evaluated on a small, single-domain dataset—generalization not demonstrated.
- Regression framing loses interpretability (no partial credit categories or explanation).
- GRU's sequential modeling may be redundant when BERT already captures long-range context well.
- Does not address higher-order cognitive features or Bloom's levels.

---

### MMSAF: Multimodal Short Answer Grading (Sil et al., 2025)

**Paper:** Sil, P., Bhattacharyya, P., Goyal, P., & Ramakrishnan, G. (2025). *"Did my figure do justice to the answer?": Can MLLMs Generate Human-Like Feedback in Grading Multimodal Short Answers?*  
**Published:** arXiv, December 27, 2024 (revised February 2025)  
**URL:** [https://arxiv.org/abs/2412.19755](https://arxiv.org/abs/2412.19755)

**Methodology:**
- Introduces the **MMSAF (Multimodal Short Answer Grading with Feedback)** problem: grading student answers that contain both **text and diagrams/figures**, as commonly used in STEM competency assessments.
- Develops an automated data generation framework leveraging **LLM hallucinations** to mimic common student errors, constructing a dataset of **2,197 instances** across 3 STEM subjects.
- Evaluates 4 **Multimodal Large Language Models (MLLMs)** across the dataset.
- Conducts human evaluation with **9 annotators** across 5 parameters using a rubric-based scoring approach.
- Uses rubrics to evaluate feedback quality **semantically** rather than through overlap-based metrics (e.g., BLEU), which is a methodological contribution.

**Key Findings:**
- MLLMs achieve up to **62.5% accuracy** in predicting answer correctness (correct / partially correct / incorrect).
- MLLMs achieve up to **80.36% accuracy** in assessing image relevance (whether the diagram contributed meaningfully).
- Rubric-based evaluation reveals qualitative differences between model families—some MLLMs are better suited for semantic feedback, others for factual correctness checking.
- Current MLLMs are far from human performance on the full MMSAF task—significant headroom remains.

**Limitations:**
- Dataset generated programmatically using LLM hallucinations—may not fully capture the diversity of real student errors.
- Limited to 3 STEM subjects; social sciences and humanities remain untested.
- 62.5% accuracy on correctness prediction is insufficient for practical deployment without human oversight.
- Rubric design requires significant domain expert effort.

---

### Arabic ASAG with AraBERTv2 (Mahmood, 2025)

**Paper:** Mahmood, S. A. (2025). *Optimizing Architectural-Feature Tradeoffs in Arabic Automatic Short Answer Grading: Comparative Analysis of Fine-Tuned AraBERTv2 Models.*  
**Published:** Frontiers in Computer Science, October 17, 2025  
**URL:** [https://www.frontiersin.org/articles/10.3389/fcomp.2025.1683272/full](https://www.frontiersin.org/articles/10.3389/fcomp.2025.1683272/full)

**Methodology:**
- Focuses on the underserved Arabic ASAG problem, using the **AS-ARSG dataset** (2,133 student responses from a cybercrime teaching course, master's-level students at University of Basrah, Iraq).
- Fine-tunes **AraBERTv2** (`aubmindlab/bert-base-arabertv02`, 768-dimensional embeddings) combined with three downstream neural network architectures:
  - **MLP** (Multilayer Perceptron)
  - **CNN** (Convolutional Neural Network)
  - **LSTM** (Long Short-Term Memory)
- Tests each architecture with **2, 3, and 4 input features**:
  - 2 features: reference answer + student answer
  - 3 features: + question text
  - 4 features: + human score
- Evaluates generalizability under limited data conditions using 80:20 train-test split with question-wise stratification.

**Key Findings:**

| Architecture | Features | MAE | RMSE | Pearson (r) | Spearman (ρ) |
|---|---|---|---|---|---|
| MLP | 2 | **1.31** | **1.67** | **0.803** | **0.808** |
| CNN | 2 | 1.45 | — | 0.784 | ~0.78 |
| LSTM | 2 | 1.48 | — | 0.757 | ~0.77 |
| LSTM | 4 | 3.62 | — | 0.388 | 0.419 |

- The **2-feature MLP model significantly outperforms** all others—simpler feature sets generalize better in small-data settings.
- Increasing features (adding question text or human scores) paradoxically degrades performance, especially in LSTM models, likely due to overfitting.
- Establishes a new state-of-the-art on the AS-ARSG dataset (previous best by Meccawy et al., 2023: RMSE 1.003, Pearson 0.842).
- Demonstrates the feasibility of Arabic ASAG under limited annotation resources.

**Limitations:**
- Exclusive use of AS-ARSG dataset limits cross-corpus generalizability.
- Only AraBERTv2 tested—no comparison to modern Arabic LLMs (e.g., AraGPT, Jais).
- Dataset is domain-specific (cybercrime/computer science); other Arabic subject areas unexplored.
- Lack of student demographic diversity in dataset.
- Human scores in the dataset averaged from two expert annotators—inter-rater agreement not reported.

---

### Hybrid ANN + Text Similarity for Polish (Bani Saad et al., 2025)

**Paper:** Bani Saad, M., Jackowska-Strumillo, L., & Bieniecki, W. (2025). *Hybrid ANN-Based and Text Similarity Method for Automatic Short-Answer Grading in Polish.*  
**Published:** Applied Sciences (MDPI), February 5, 2025  
**DOI:** [10.3390/app15031605](https://doi.org/10.3390/app15031605)  
**URL:** [https://www.mdpi.com/2076-3417/15/3/1605](https://www.mdpi.com/2076-3417/15/3/1605)

**Methodology:**
- Addresses ASAG for **Polish-language** responses—a low-resource NLP language compared to English.
- Proposes a **hybrid pipeline**:
  1. Word splitting and preprocessing (Polish-specific tokenization, stopword removal)
  2. Multiple text similarity algorithms applied to student-answer vs. reference-answer pairs
  3. Set of **ANN (artificial neural network) classifiers** trained on similarity features
  4. **Heuristic decision rules** layered on top of classifier outputs
- Implemented in the interactive **e-test system** at the Institute of Applied Computer Science, Łódź University of Technology.
- Dataset: Polish exam questions and student answers from 2015–2022, covering over 1,000 students.

**Key Findings:**
- **Precision = 1.0** (zero false positives), **Recall = 0.97**—excellent performance for the binary/multiclass grading task.
- Outperforms prior approaches for Polish ASAG.
- The hybrid approach (similarity + ANN + heuristics) proves more robust than any single component alone.
- Demonstrates that domain-specific heuristic rules are valuable when NLP resources for a language are limited.

**Limitations:**
- Single institutional dataset in Polish; limited generalizability to other Polish-language curricula.
- Precision = 1.0 may reflect dataset characteristics rather than true real-world performance.
- Heavy reliance on heuristic rules requires manual rule engineering per domain.
- No LLM component—likely to be outperformed by multilingual LLMs (e.g., multilingual-BERT, mT5) in head-to-head comparison.

---

## Topic 3: Concept-Aware NLP Approaches

### Knowledge-Based Validation (Hondarangala & Wickramaarachchi, 2025)

**Paper:** Hondarangala, C., & Wickramaarachchi, D. (2025). *Leveraging AI to Ensure Authenticity in Student Assignments: A Knowledge-Based Validation and Evaluation Framework.*  
**Published:** IEEE ICARC 2025 (February 19, 2025)  
**URL:** [https://ieeexplore.ieee.org/document/10962918/](https://ieeexplore.ieee.org/document/10962918/)  
**DOI:** [10.1109/ICARC64760.2025.10962918](https://doi.org/10.1109/ICARC64760.2025.10962918)

**Methodology:**
- Introduces a **two-phase AI-driven assessment model** designed to evaluate genuine conceptual understanding while detecting AI-assisted plagiarism:

  **Phase 1 — Authenticity Check:**
  - AI generates **contextually relevant questions** based on student-submitted assignments.
  - Students answer these dynamically generated questions to demonstrate that they understand (not just submitted) the content.
  - Uses LLM capability to generate questions calibrated to the content's complexity and Bloom's level.

  **Phase 2 — Conceptual Depth Evaluation:**
  - Aligns student submissions against **course-specific materials** (lecture notes, textbooks, learning objectives).
  - Evaluates three dimensions: **relevance**, **depth**, and **originality**.
  - A fine-tuned LLM trained on domain-specific educational data performs the evaluation against academic standards.
  
- This two-phase structure is notable: Phase 1 targets authenticity (anti-cheating), Phase 2 targets concept comprehension (learning outcome verification).

**Key Findings:**
- Students demonstrated **marked improvements in understanding and performance** when using the two-phase system.
- The model effectively reduces the likelihood of students submitting AI-generated content without comprehension.
- Encourages deeper engagement and comprehension, increasing students' actual knowledge of material.
- Validates the effectiveness of knowledge-based validation for detecting surface-level assignment submission.

**Limitations:**
- Results reported qualitatively; specific accuracy or reliability metrics not published in the abstract.
- Phase 1 (dynamic question generation) depends on LLM accuracy—poor or off-topic questions could unfairly penalize students.
- Fine-tuned LLM in Phase 2 requires domain-specific training data per course—significant upfront investment.
- Evaluation based on student performance improvements (pre/post), not external ground-truth validation of concept identification.

---

### Concept Extraction from Text Using NLP/LLMs

Concept extraction involves automatically identifying the key domain concepts present in a piece of text (e.g., a student answer). This is a prerequisite for concept-aware grading.

**Current state of the art:**

| Approach | Method | Key Properties |
|---|---|---|
| Named Entity Recognition (NER) | Fine-tuned BERT/RoBERTa | Identifies noun phrases as concept candidates |
| Ontology-guided extraction | NLP + domain ontology | Uses ontology to constrain and validate extracted concepts |
| LLM-based extraction | GPT-4, LLaMA prompt | Flexible, zero-shot; may hallucinate |
| Keyphrase extraction | YAKE, KeyBERT | Lightweight; no ontology needed |

**Relevant work:**
- [Automated Ontology Evaluation (Zaitoun et al., 2023)](https://dl.acm.org/doi/pdf/10.1145/3543873.3587617) demonstrates domain-tuned NER for extracting phrasal concepts from text and comparing them against an ontology.
- [Ontology-Guided Information Extraction (Anantharangachar et al., 2013)](https://arxiv.org/abs/1302.1335) establishes the framework of using ontology structure to guide semantic triple extraction from text—foundational for concept-relation modeling.
- [Do LLMs Really Adapt to Domains? (Mai et al., 2024)](https://arxiv.org/abs/2407.19998) examines whether LLMs consistently extract structured knowledge (concept hierarchies) from domain text—finds they leverage lexical patterns rather than true semantic reasoning, especially without fine-tuning.

**Implications for ASAG:**
- Pure keyword-based concept extraction misses paraphrased or implicit concepts in student answers.
- LLM-based extraction can handle paraphrase but requires validation against a reference ontology to avoid accepting hallucinated concept labels.
- Hybrid approaches (LLM extraction + ontology verification) are the emerging best practice.

---

### Relation Extraction Between Concepts in Student Answers

Beyond identifying individual concepts, understanding whether students correctly articulate the *relationships* between concepts is critical for higher-order Bloom's assessment (Analyze, Evaluate, Create).

**Methodology pattern:**
1. Extract candidate concepts using NER or keyphrase extraction.
2. Apply **relation extraction** (RE) to identify how concepts are connected in the student's answer (e.g., "protein synthesis *requires* ribosomes" — subject–predicate–object triple).
3. Compare extracted triples against a reference knowledge graph or ontology.

**Relevant literature:**
- [Machine Learning Techniques with Ontology for Subjective Answer Evaluation (Syamala Devi & Mittal, 2016)](https://arxiv.org/abs/1605.02442) shows that incorporating ontology-based concept coverage checking improves evaluation holism—presence of keywords, synonyms, correct word combinations, and concept coverage can all be verified.
- [Enacting Textual Entailment and Ontologies for Automated Essay Grading (Groza & Szabo, 2015)](https://arxiv.org/abs/1511.02669) proposes checking if the truth of ontology-derived hypotheses follows from the student's text—a semantic entailment approach to concept verification.
- Recent LLM-based work from CoTAL and similar frameworks can be adapted to extract relational triples as intermediate reasoning steps in chain-of-thought prompting, then verify those triples against expected concept relationships.

---

### Comparing Against Reference Ontologies

Once concepts and relations are extracted from student answers, they must be compared against a **reference ontology** (or knowledge graph) that encodes the correct conceptual structure of the domain.

**Key challenges:**
- **Ontology construction**: Manually building domain ontologies is expensive; LLMs offer semi-automated pathways ([Ontology Learning Using Formal Concept Analysis and WordNet, Hassan, 2023](https://arxiv.org/abs/2311.14699)).
- **Semantic matching**: Student answers use varied vocabulary; concepts must be mapped via synonymy or embedding similarity before structural comparison.
- **Partial credit modeling**: A student's concept graph may be partially correct—scoring requires measuring graph edit distance or concept overlap rather than exact match.

**Promising recent approach:**
- [SDoEd Ontology (Kollapally et al., 2025)](https://arxiv.org/abs/2501.10300) demonstrates a human-AI collaborative ontology construction workflow using LLMs to suggest concepts, validated by domain experts—applicable to educational domain ontologies.
- The ASAG system in Gobrecht et al. (2024) implicitly uses reference answers as compressed concept representations; explicit ontology comparison would extend this to structured concept verification.

---

### NLP Pipeline for Assessment Data

A complete NLP pipeline for concept-aware educational assessment would include:

```
Student Answer Text
      ↓
[Preprocessing] → tokenization, lemmatization, stopword removal
      ↓
[Concept Extraction] → NER/keyphrase + LLM refinement
      ↓
[Relation Extraction] → dependency parsing or LLM triple extraction
      ↓
[Ontology Alignment] → map extracted concepts to reference ontology nodes
      ↓
[Concept Coverage Scoring] → compare student concept graph vs. reference
      ↓
[Bloom's Level Classification] → infer cognitive depth from concept completeness + relations
      ↓
[Feedback Generation] → LLM generates explanation citing missing/incorrect concepts
```

**CE-JEME Journal context:** The Computer Engineering – Journal of Electrical and Mechanical Engineering has published related NLP pipeline work. The pipeline above aligns with the direction described in Hondarangala & Wickramaarachchi (2025) and with broader concept-aware ASAG research. Key references on NLP pipelines for assessment:
- [Survey of NLP for Education (Lan et al., 2024)](https://arxiv.org/abs/2401.07518) provides a taxonomy of NLP assessment tasks including question answering, automated assessment, and error correction.
- [Enhancing Instructional Quality via Computer-Assisted Textual Analysis (Tian et al., 2024)](https://arxiv.org/abs/2403.03920) demonstrates how NLP can analyze student responses at the concept and discourse level to support instructional improvement.

---

## Topic 4: V-NLI Integration Opportunities

### NL4DV (Narechania et al., 2020)

**Paper:** Narechania, A., Srinivasan, A., & Stasko, J. (2020). *NL4DV: A Toolkit for Generating Analytic Specifications for Data Visualization from Natural Language Queries.*  
**Published:** IEEE Transactions on Visualization and Computer Graphics (TVCG), August 24, 2020  
**URL:** [https://arxiv.org/abs/2008.10723](https://arxiv.org/abs/2008.10723)  
**IEEE URL:** [https://ieeexplore.ieee.org/document/9222342/](https://ieeexplore.ieee.org/document/9222342/)

**Methodology:**
- NL4DV is a **Python package** (Natural Language for Data Visualization) that takes:
  - Input: tabular dataset + natural language query
  - Output: analytic specification (JSON) containing data attributes, analytic tasks, and Vega-Lite chart specifications
- Implements classic NLP components: POS tagging, named entity recognition, dependency parsing.
- Enables developers without NLP expertise to build visualization NLIs.
- Demonstrated in four use cases: Jupyter notebooks, NLI for Vega-Lite, DataTone ambiguity widgets, multimodal (speech) visualization.

**Subsequent extension (2022):** [NL4DV conversational extension (Mitra et al., 2022)](https://arxiv.org/abs/2207.00189) adds multi-turn dialog support.  
**LLM integration (2024):** [NL4DV + GPT-4 (Sah et al., 2024)](https://arxiv.org/html/2408.13391v1) integrates GPT-4 for improved query translation in an open-source update.

**Limitations in Educational Context:**
- Designed for **generic tabular data analysis**—not for educational data structures (e.g., concept maps, rubric matrices, Bloom's level distributions).
- Cannot interpret **semantic nuances** in educational queries ("show me students who understand the concept of photosynthesis but not cellular respiration").
- Vega-Lite output covers standard chart types (bar, scatter, line)—cannot produce educational-specific visualizations like concept dependency graphs or skill mastery heat maps.
- No mechanism to handle multi-dimensional concept scores or Bloom's hierarchies.

---

### DataTone (Gao et al., 2015)

**Paper:** Gao, T., Dontcheva, M., Adar, E., Liu, Z., & Karahalios, K. G. (2015). *DataTone: Managing Ambiguity in Natural Language Interfaces for Data Visualization.*  
**Published:** ACM UIST 2015 (November 5, 2015)  
**URL:** [https://dl.acm.org/doi/10.1145/2807442.2807478](https://dl.acm.org/doi/10.1145/2807442.2807478)

**Methodology:**
- Addresses the fundamental NLI challenge of **ambiguity** in natural language queries (e.g., "show me students who struggled" is ambiguous—struggled at what? how much?).
- DataTone uses **ambiguity widgets**: interactive UI elements that surface multiple interpretations of an ambiguous query, allowing users to disambiguate through direct manipulation.
- Classified ambiguity into types: attribute ambiguity, value ambiguity, operation ambiguity.
- Balances automatic resolution for common cases with explicit user control for genuinely ambiguous ones.

**Key Findings:**
- Ambiguity widgets enable users to efficiently explore multiple possible interpretations without reformulating queries.
- The system reduces frustration from NLI misinterpretation while maintaining a natural language interaction paradigm.

**Limitations in Educational Context:**
- Developed in 2015—predates LLM era; uses rule-based NLP rather than neural methods.
- Ambiguity widget design assumes simple attribute/value queries; educational queries about concept mastery or misconception patterns involve complex, compositional semantics beyond the widget model.
- No support for temporal learning trajectories, rubric-based multi-dimensional scoring, or concept hierarchy queries.

---

### Chat2VIS (Maddigan & Susnjak, 2023)

**Paper:** Maddigan, P., & Susnjak, T. (2023). *Chat2VIS: Generating Data Visualizations via Natural Language using ChatGPT, Codex and GPT-3 Large Language Models.*  
**Published:** IEEE Access, February 4, 2023  
**URL:** [https://arxiv.org/abs/2302.02094](https://arxiv.org/abs/2302.02094)  
**IEEE URL:** [https://ieeexplore.ieee.org/document/10121440/](https://ieeexplore.ieee.org/document/10121440/)

**Methodology:**
- **Chat2VIS** leverages pre-trained LLMs (ChatGPT, GPT-3, Codex) to convert free-form natural language queries directly into Python/matplotlib visualization code.
- Key innovation: Rather than building a custom NLU pipeline, Chat2VIS relies on LLMs' implicit understanding of visualization intent, enabled through careful prompt engineering.
- Constructs prompts that preserve data security (data columns and types described but not uploaded to LLM).
- Evaluates GPT-3, Codex, and ChatGPT across multiple case studies, comparing against prior rule-based/grammar NLP approaches.

**Key Findings:**
- Chat2VIS produces correct, executable visualizations even from **highly misspecified or underspecified queries**.
- LLMs with effective prompting outperform traditional NLP approaches (rule-based grammar, tailored models) in visualization inference ability.
- Significantly reduces NLI development costs: no need for custom models or annotated training data.
- Generalizable to new datasets through prompt adaptation alone.

**Limitations in Educational Context:**
- Generates **generic statistical visualizations** (bar charts, scatter plots)—cannot produce concept maps, misconception heatmaps, or Bloom's taxonomy distributions without significant prompt engineering extensions.
- Code generation approach is brittle for complex multi-step educational analytics (e.g., "show the class distribution of Bloom's levels for chemistry vs. biology questions").
- No built-in mechanism for educational data schemas—would require custom prompt templates per assessment system.
- Security and privacy concerns when linking to student assessment databases.
- Tested (2023) before GPT-4o and reasoning models; recent capabilities updates significantly expand what is possible.

---

### Limitations of Existing V-NLI Systems in Educational Contexts

A systematic comparison of the three core V-NLI systems against educational assessment needs:

| Capability | NL4DV | DataTone | Chat2VIS | Educational Need |
|---|---|---|---|---|
| Standard chart generation | ✅ | ✅ | ✅ | Partially sufficient |
| Ambiguity resolution | ❌ | ✅ | Partial | Critical for vague teacher queries |
| Concept map visualization | ❌ | ❌ | ❌ | **Missing** |
| Bloom's taxonomy charts | ❌ | ❌ | Potential | **Missing** |
| Misconception pattern maps | ❌ | ❌ | ❌ | **Missing** |
| Temporal learning trajectories | ❌ | ❌ | Potential | Partially missing |
| Multi-dimensional rubric views | ❌ | ❌ | Partial | **Missing** |
| Class-level vs. individual drill-down | ❌ | ❌ | Potential | **Missing** |
| Domain-specific educational ontologies | ❌ | ❌ | ❌ | **Missing** |

**Core limitation**: All three systems were designed for general business analytics on tabular data. Educational assessment data has fundamentally different characteristics:
- Hierarchical rubric structures (not flat columns)
- Latent cognitive constructs (Bloom's levels, misconceptions)
- Temporal sequences (learning trajectories across assignments)
- Concept relational graphs (not numeric fields)

---

### Opportunity: Visualizing Concept Understanding Patterns

The convergence of (1) LLM-based ASAG, (2) concept-aware NLP, and (3) V-NLI technologies creates a novel opportunity space:

#### Proposed V-NLI for Educational Assessment

An educational V-NLI system would go beyond score visualization to enable queries such as:

> *"Show me which concepts about photosynthesis are most commonly misunderstood by students in class 3B."*  
> *"For the last quiz, display a Bloom's taxonomy distribution overlay for each question."*  
> *"Identify students who demonstrate Apply-level knowledge but fail at Analyze-level on enzyme kinetics."*  
> *"Visualize concept dependency errors—students who understand glucose but not ATP production."*

#### Visualization Types Needed

| Visualization Type | What It Shows | Benefit |
|---|---|---|
| **Concept map overlay** | Which concepts students mentioned vs. expected | Shows comprehension gaps per concept |
| **Bloom's distribution chart** | Distribution of cognitive levels across class | Identifies if curriculum reaches higher-order thinking |
| **Misconception heatmap** | Frequency of specific wrong concepts across students | Enables targeted remediation |
| **Learning trajectory graph** | Cognitive level changes over time per student | Supports adaptive instruction |
| **Concept co-occurrence matrix** | Which concepts students associate together | Reveals relational understanding vs. isolated knowledge |
| **Concept depth radar** | Per-concept Bloom's level for individual student | Personalized cognitive profile |

#### Integration Architecture

```
Teacher NL Query
      ↓
[Educational V-NLI Layer]
      ↓
[Query Interpretation] ← Domain ontology + assessment schema
      ↓
[Data Retrieval] ← ASAG output database (scores + concept labels + Bloom's levels)
      ↓
[Visualization Specification]
      ↓
[Educational Chart Rendering] → concept maps, Bloom's charts, misconception views
```

**Key technical challenges:**
1. **Concept-enriched ASAG database**: Existing ASAG systems output scores, not concept labels—the output schema must be extended.
2. **Educational query parsing**: V-NLI systems must understand domain-specific educational vocabulary (rubric, Bloom's level, misconception, mastery).
3. **Appropriate chart selection**: The NLI must select or construct visualization types that do not exist in standard libraries.
4. **Privacy-preserving aggregation**: Class-level views must aggregate without exposing individual student data inappropriately.

**Related enabling work:**
- [LAVA Model: Learning Analytics Meets Visual Analytics (Chatti et al., 2023)](https://arxiv.org/abs/2303.12392) proposes integrating visual analytics principles into learning analytics—the closest existing framework to the proposed educational V-NLI.
- [Gaze Analytics Dashboard for ELA (Davalos et al., 2025)](https://www.semanticscholar.org/paper/4c201e2d46bf8e4613e1adc5dfd65f6bdd815fef) demonstrates an LLM-powered conversational agent enabling teachers to query multimodal learning analytics dashboards using natural language—a near-term existence proof of the proposed approach.

---

## Cross-Cutting Synthesis

### The Assessment Stack: From Scoring to Understanding

Current ASAG systems operate at different levels of abstraction:

```
Level 5: Concept Relationship Understanding  ← Frontier (largely unsolved)
Level 4: Concept Presence Classification     ← Emerging (ontology-based ASAG)
Level 3: Bloom's Level Classification        ← Active research (CoTAL, Bloomify)
Level 2: Partial Credit Scoring             ← Mature (LLMarking, Gobrecht et al.)
Level 1: Binary Correct/Incorrect           ← Solved (GPT-4o achieves human-level)
```

Most deployed systems operate at Levels 1–2. The research frontier is at Levels 3–5, where understanding *why* an answer is correct or incorrect at a conceptual level becomes the goal.

### Trend Summary (2024–2025)

| Trend | Evidence |
|---|---|
| LLMs surpass custom models on ASAG benchmarks | ASAG2024 (Meyer et al.); Zhao et al. |
| GPT-4o is the practical sweet spot (accuracy + cost) | Zhao et al. 2025 |
| RAG-based example retrieval beats random few-shot | Zhao et al. 2025 |
| CoT prompting improves higher-order assessment | Cohn et al. 2024/2025 |
| Multimodal (text+diagram) grading is now being formalized | Sil et al. 2025 |
| Cross-lingual ASAG advancing (Arabic, Polish) | Mahmood 2025; Bani Saad et al. 2025 |
| Concept-aware validation is the next frontier | Hondarangala & Wickramaarachchi 2025 |
| V-NLI systems need educational domain adaptation | Gap analysis above |

---

## Research Gaps and Future Directions

1. **Bloom's Level Classification for Short Answers**: Most work classifies Bloom's level of *questions*, not *student answers*. A system that infers from a student's answer what cognitive level they are demonstrating (independent of the question's intended level) would enable genuine learning diagnosis.

2. **Concept-Aware LLM Prompting**: Prompts that explicitly extract a student's "concept map" from their answer (as a structured intermediate representation) before scoring would produce explainable, concept-level feedback—not just a grade.

3. **Educational V-NLI**: A purpose-built NLI for educational assessment data that understands rubrics, Bloom's hierarchies, and concept graphs—moving beyond score-centric dashboards to *understanding-centric* visualizations for teachers.

4. **Cross-Language, Cross-Domain Benchmarks**: ASAG2024 is English-centric and domain-heterogeneous. Multilingual, concept-annotated benchmarks (including Arabic, Polish, and other languages) would accelerate global adoption.

5. **Longitudinal Concept Tracking**: Linking ASAG outputs across multiple assignments over a course to track how a student's concept understanding evolves—concept mastery curves rather than point-in-time scores.

6. **Human-AI Collaborative Grading Workflows**: Rather than fully automated grading, systems like CoTAL demonstrate the value of human-in-the-loop architectures. Formalizing when and how humans review AI-generated grades (especially for Bloom's level 4–6 content) is an open systems design problem.

7. **Privacy-Preserving Concept Analytics**: Class-level concept visualizations must aggregate individual student data. Differential privacy and federated learning approaches for educational analytics remain underdeveloped.

---

*End of research document. All source URLs are cited inline throughout the document.*
