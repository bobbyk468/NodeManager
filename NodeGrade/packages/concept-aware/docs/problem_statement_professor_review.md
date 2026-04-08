# ConceptGrade: Problem Statement, Approach, and References
**Prepared for Professor Review — April 2026**

---

## 1. Problem Statement

Grading short written answers is one of the most demanding parts of teaching, particularly in technical subjects like Computer Science. When a class has hundreds of students, each writing a few sentences in response to questions like "What is a linked list?" or "How does backpropagation work?", the sheer volume of grading becomes overwhelming. Beyond the time cost, manual grading is also inconsistent — two instructors reading the same answer often assign slightly different scores.

Automated Short Answer Grading (ASAG) has been studied for over two decades as a solution to this problem. The goal is to build a system that reads a student's free-text answer and predicts the score a human expert would give. While meaningful progress has been made, existing approaches all share two fundamental weaknesses: they measure how similar an answer looks to the model answer rather than whether the student actually understood the underlying concepts, and they produce a number — but nothing more. An instructor who receives a score of 2.5 out of 5 from an automated system cannot tell whether the student understood half the material well, understood everything superficially, or missed one specific concept entirely.

The three main families of existing approaches each fail in a different but related way.

**Lexical overlap methods** (such as TF-IDF) compare the words in the student's answer against the words in the reference answer. If the student uses many of the same words, they score well. The obvious problem is that a student who has memorized the right vocabulary but understands nothing will score just as well as one who genuinely understands the concept. Equally, a student who explains an idea correctly using different words gets penalized unfairly.

**Neural embedding methods** (such as BERT and sentence transformers) are more sophisticated — they convert answers into numerical vectors that capture meaning, not just surface words. This handles paraphrases better, but these methods still operate by measuring overall textual similarity between two passages. They have no understanding of which specific concepts a student covered, which ones they missed, or whether the understanding demonstrated is shallow or deep.

**Large Language Model (LLM) zero-shot grading** — asking models like GPT-4 or Gemini to read a student's answer and assign a score — is surprisingly capable and has attracted considerable recent research attention. However, LLMs suffer from a systematic problem we call **cognitive-level calibration bias**: they tend to assign high scores to answers that are written fluently and sound confident, regardless of whether the student has actually covered the required concepts. A student who writes a long, well-structured paragraph using domain keywords but misapplying them will receive an inflated score. In our own measurements, the pure LLM baseline consistently overestimates student scores by an average of +0.19 points on a 0–5 scale compared to expert human graders.

None of these approaches can answer the questions that matter most to an instructor: Which concepts did the student correctly demonstrate? Which expected concepts are missing? Is the student's understanding shallow (just recall) or deep (integrated across multiple ideas)? Does the student have any misconceptions? And — equally important — can these answers be presented to the instructor in a form they can actually act on? These are the questions our system, ConceptGrade, is designed to answer.

---

## 2. Research Question

The central question guiding this work is:

> **Can we improve both the accuracy and interpretability of automated short answer grading by explicitly checking whether a student's answer covers the expected concepts in a domain knowledge graph — and can the resulting structured evidence be rendered as actionable visual analytics for instructors?**

This question has two parts that are inseparable in practice. Accurate scoring without explanation provides limited value to an educator. Explanations without accuracy lose credibility. ConceptGrade pursues both simultaneously: the Knowledge Graph provides structured, auditable evidence for the score, and the visualization layer converts that evidence into instructor-facing dashboards — concept coverage heatmaps, misconception maps, Bloom's-level distributions, and student radar charts — that make the diagnostic information actionable at the classroom scale.

---

## 3. Proposed Approach: ConceptGrade

### 3.1 Core Idea

The key insight behind ConceptGrade is that expert grading is fundamentally about concepts, not text. When a professor reads a student's answer, they are mentally checking whether the student has demonstrated understanding of specific ideas — and whether those ideas are connected correctly. We can make this process explicit by representing the expert's expected knowledge as a structured **Knowledge Graph (KG)** and then checking how well the student's answer covers that graph.

A knowledge graph is simply a structured representation of domain knowledge as a set of concepts (nodes) and the relationships between them (edges). For the question "What is a stack?", an expert KG would contain concepts like `stack`, `LIFO_principle`, `push_operation`, `pop_operation`, and relationships such as `stack implements LIFO` and `push_operation has_complexity O(1)`. A student who correctly explains all of these concepts and their connections would cover the KG well and earn a high score. A student who only writes "a stack stores data" covers almost none of it.

This structured representation does something that no existing ASAG method does: it produces a named, auditable record of what the student understood and what they did not. This record is the foundation for both more accurate scoring and for the visualization layer described below.

### 3.2 The Grading Pipeline

ConceptGrade processes each grading task through four stages.

**Stage 0 — Knowledge Graph Construction.** For each question, we automatically generate a domain knowledge graph using Gemini. The model reads the question and the reference answer and produces a structured JSON graph of expected concepts and their relationships. This is a one-time step per question — once generated, the KG is stored and reused for all student answers to that question. For the Mohler CS dataset, we designed the KG manually (101 concepts, 151 relationships) to create a high-quality gold standard. For the DigiKlausur and Kaggle ASAG datasets, the KG was generated automatically, demonstrating that the pipeline scales to new domains without manual effort.

**Stage 1 — KG Feature Extraction.** For each student answer, we compute how well it covers the expected concepts in the KG. This is done using two techniques in combination: TF-IDF cosine similarity for exact keyword matching, and semantic similarity using the `all-MiniLM-L6-v2` sentence-transformer model for meaning-based matching that handles paraphrases. The output is a concept coverage score — what fraction of the expected concepts the student's answer correctly addresses. We also compute causal chain coverage (whether the student explained how concepts connect, not just listed them), and classify the answer on both Bloom's taxonomy (Remember → Evaluate) and the SOLO taxonomy (Unistructural → Extended Abstract).

**Stage 2 — Scoring.** We run two completely separate scoring passes using Gemini. The first is a pure LLM baseline (C_LLM) that receives only the question, reference answer, and student answer — no KG information. The second is our ConceptGrade system (C5_fix) that receives all of the above plus the structured KG evidence: which concepts were matched, coverage percentage, and the Bloom's/SOLO level. Keeping these two passes completely separate is critical — if they share the same context window, the LLM baseline is influenced by seeing the KG evidence, which artificially inflates the baseline and makes fair comparison impossible.

For domains where the vocabulary is common everyday language (elementary science), we apply an additional technique called **LLM-as-Judge**: rather than just showing the coverage percentage, we present the model with all expected concepts along with their full descriptions, and ask it to explicitly verify each one as TRUE (correctly demonstrated) or FALSE (mentioned but not actually understood) before assigning the final score. This prevents the "bag-of-words inflation" problem where common words like "energy" or "oxygen" trigger false concept matches.

**Stage 3 — Metric Computation and Visual Analytics Output.** We compare scores against human expert grades using Mean Absolute Error (MAE), Pearson correlation, Spearman rank correlation, Quadratic Weighted Kappa (QWK), and the paired Wilcoxon signed-rank test for statistical significance.

Alongside these quantitative metrics, the pipeline produces structured JSON visualization specifications that describe — in a format ready for rendering by a D3.js or Plotly frontend — the full diagnostic picture of each student's answer. The implemented visualization types include: concept coverage bar charts (which expected concepts were and were not addressed, per student), misconception heatmaps (which concepts are most commonly misunderstood across the class, by severity), student radar charts (a five-axis view of coverage, Bloom's level, SOLO level, misconception count, and causal chain depth), Bloom's and SOLO distribution plots across the class, and concept co-occurrence matrices showing which concepts tend to appear together in student answers. These outputs exist as a backend rendering engine (`visualization/renderer.py`) and are designed to be consumed by an interactive instructor-facing dashboard.

### 3.3 What ConceptGrade Tells the Instructor

The distinction between ConceptGrade and all prior ASAG work is not only in the score it produces but in the structured diagnostic report that accompanies every score. For a class of 100 students answering the same question, ConceptGrade can produce: a ranked list of concepts most frequently missed; a distribution of Bloom's levels showing what fraction of the class is operating at recall versus application versus synthesis; a misconception map identifying systematic errors (e.g., students who understand the `push` operation but consistently misattribute the complexity of `pop`); and a per-student radar chart summarizing their coverage profile across five dimensions. These outputs transform grading from a scoring act into a diagnostic tool — one that can inform which topics to revisit in the next lecture, which students need targeted feedback, and which parts of the question are ambiguous enough to generate systematic misunderstanding.

---

## 4. Datasets

We evaluated ConceptGrade on three datasets spanning different academic domains and difficulty levels, to test whether the approach generalizes beyond the domain it was originally designed for.

**Mohler et al. (2011) — Computer Science Data Structures.** This is the standard benchmark for ASAG research. It contains 120 student answers across 10 questions on data structures topics including linked lists, stacks, queues, BSTs, hash tables, sorting algorithms, and Big-O notation. Scores range from 0 to 5 and were assigned by expert human graders. We used a hand-crafted KG for this dataset.

**DigiKlausur — Neural Networks.** This dataset contains 646 student answers to 17 questions on neural network fundamentals, including backpropagation, activation functions, convolutional neural networks, and recurrent neural networks. Scores follow a coarse three-level rubric (0, 2.5, or 5). We used automatically generated KGs for all 17 questions.

**Kaggle ASAG — Elementary Science.** This dataset contains 473 student answers to 150 questions at the K-5 level, covering topics like photosynthesis, cellular respiration, and ecosystems. Scores range from 0 to 3. We used automatically generated KGs for all 150 questions.

---

## 5. Results

### 5.1 Main Findings

ConceptGrade reduces grading error compared to the pure LLM baseline on all three datasets.

On the **Mohler CS dataset**, ConceptGrade reduces MAE by **32.4%** (from 0.3300 to 0.2229), with a statistically significant Wilcoxon p-value of 0.0013. It wins on MAE in 8 out of 10 individual questions. The non-overlapping 95% confidence intervals for C5_fix [0.179, 0.269] and C_LLM [0.273, 0.390] confirm this is a robust finding.

On the **DigiKlausur Neural Networks dataset**, ConceptGrade reduces MAE by **4.9%** (from 1.1842 to 1.1262), with a Wilcoxon p-value of 0.049. This is a more modest improvement, consistent with the greater difficulty of grading coarse-rubric responses.

On the **Kaggle ASAG Science dataset**, ConceptGrade reduces MAE by **3.2%** (from 1.2082 to 1.1691). This improvement is directionally consistent but does not reach statistical significance (p = 0.319). This is an important finding discussed in Section 5.3.

Taking all three datasets together, a Fisher combined test across all three p-values yields **p = 0.0014**, confirming that the overall evidence for ConceptGrade's advantage is highly significant even though one individual dataset does not independently cross the significance threshold. Across 1,239 student answers spanning Computer Science, Neural Networks, and Elementary Science, ConceptGrade consistently produces lower scoring error than the pure LLM baseline — though the magnitude of improvement is strongly modulated by the vocabulary characteristics of the domain.

### 5.2 Component Ablation (Mohler Dataset)

To understand which parts of the pipeline contribute most, we tested all intermediate configurations:

- **C0** (reference answer only, no student answer): MAE = 1.7113 — the KG alone is useless without reading the student's answer.
- **C1** (KG evidence only, no reference answer): MAE = 0.7405 — better, but missing critical rubric context.
- **C1_fix** (KG + student answer, no reference answer): MAE = 0.3458 — close to but slightly worse than the LLM baseline.
- **C_LLM** (full LLM baseline, no KG): MAE = 0.3300
- **CoT baseline** (chain-of-thought prompting): MAE = 0.2208
- **ConceptGrade / C5_fix** (full pipeline): MAE = 0.2229

ConceptGrade essentially matches the CoT baseline in raw accuracy. The critical difference is interpretability: ConceptGrade additionally tells you *which concepts* the student covered and *which are missing*, while CoT prompting produces only a score and a natural-language justification. This is the foundation for the visual analytics layer — the structured concept coverage data from the KG extraction stage is precisely what feeds the visualization renderer.

### 5.3 Why Kaggle ASAG Is Different: The Domain Boundary Condition

The smaller benefit on Kaggle ASAG is not a failure — it is a theoretically important finding. Elementary science questions use everyday vocabulary: "energy," "water," "oxygen," "plants." A student can write a fluent, confident sentence containing all these words while explaining the concept entirely incorrectly. Concept keyword presence becomes a weak signal of actual understanding when the vocabulary is common to everyday language.

By contrast, Computer Science and Neural Networks use specialized vocabulary — "backpropagation," "bipartite graph," "O(n log n)" — where using a term correctly is itself strong evidence of understanding. The KG provides much stronger grading signal in these domains.

This suggests a general principle: **the benefit of Knowledge Graph augmentation scales with the lexical specificity of the domain.** This is a boundary condition worth documenting rather than hiding, and it has direct practical implications for where ConceptGrade should be deployed. It also has implications for the visualization layer: in technical domains, the concept coverage heatmaps and misconception maps produced by ConceptGrade are highly informative; in everyday-language domains, additional verification (LLM-as-Judge) is needed to prevent false positives from inflating the visual diagnosis.

---

## 6. Discussion and Future Work

### 6.1 From Scoring to Explainable Visual Analytics

ConceptGrade's current design already produces substantially more than a score. Every graded answer generates a structured diagnostic record: which concepts were matched, at what Bloom's and SOLO level, and whether the student's reasoning shows causal integration or isolated recall. At the class level, these records aggregate into maps of collective understanding and misconception.

The next natural step for this work is building the interactive instructor-facing layer that consumes these structured outputs. The backend visualization engine is complete — it generates JSON rendering specifications for seven visualization types (concept coverage charts, misconception heatmaps, student radar charts, co-occurrence matrices, Bloom's and SOLO distribution plots). The missing piece is a D3.js or Plotly frontend that renders these specifications interactively, and a user study with actual instructors to validate that the diagnostic outputs are useful and actionable in classroom practice.

This combination — KG-grounded accuracy, structured diagnostic evidence, and interactive visual exploration — positions ConceptGrade as a Visual Analytics system for explainable AI grading, a framing that opens up a distinct research direction from the crowded ASAG benchmarking literature. The VAST (Visual Analytics Science and Technology) track of IEEE VIS represents a fitting venue for presenting this work once the interactive frontend and educator study are complete.

### 6.2 Practical Deployment Considerations

Based on the multi-dataset evaluation, the clearest deployment targets for ConceptGrade are university-level courses in technical domains — Computer Science, engineering, and applied mathematics — where specialized vocabulary makes KG matching highly reliable. For K-12 science or humanities courses, the LLM-as-Judge enhancement mitigates the vocabulary specificity problem, but further domain-specific calibration would be needed before production deployment.

The automatic KG generation pipeline (Stage 0) already scales to new domains without manual KG design — the DigiKlausur and Kaggle datasets both used fully automated KG construction. A course instructor who wanted to deploy ConceptGrade on their own question bank would need only to provide the questions and reference answers; the system would build the KGs automatically and begin producing diagnostic outputs with no additional configuration.

---

## 7. References

1. Mohler, M., & Mihalcea, R. (2009). Text-to-text semantic similarity for automatic short answer grading. *Proceedings of the 12th Conference of the European Chapter of the ACL (EACL)*, pp. 567–575.

2. Mohler, M., Bunescu, R., & Mihalcea, R. (2011). Learning to grade short answer questions using semantic similarity measures and dependency graph alignments. *Proceedings of the 49th Annual Meeting of the ACL*, pp. 752–762. *(Primary benchmark dataset used in this work)*

3. Sultan, M. A., Salazar, C., & Sumner, T. (2016). Fast and easy short answer grading with high accuracy. *Proceedings of NAACL-HLT 2016*, pp. 1–11.

4. Dzikovska, M. et al. (2013). SemEval-2013 Task 7: The Joint Student Response Analysis and 8th Recognizing Textual Entailment Challenge. *Proceedings of the 7th International Workshop on Semantic Evaluation*, pp. 263–274.

5. Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. *Proceedings of NAACL-HLT 2019*, pp. 4171–4186.

6. Sung, T., Nain, N., & Sharma, H. K. (2023). Pre-trained language model-based automatic short answer grading for computer science education. *IEEE Access*, vol. 11, pp. 31,542–31,553.

7. Bhandari, P. et al. (2023). Can ChatGPT replace human evaluators? An empirical study of automatic short answer grading. *arXiv:2308.12505*.

8. Gao, H. et al. (2024). Automated short answer grading using large language models: A zero-shot and few-shot exploration. *Proceedings of IEEE ICALT 2024*.

9. Emirtekin, E., & Özarslan, Y. (2025). Automated classification of student responses using Bloom's taxonomy with large language models. *Computers & Education: Artificial Intelligence*, vol. 8.

10. Bloom, B. S. et al. (1956). *Taxonomy of Educational Objectives: Handbook I: Cognitive Domain*. New York: David McKay.

11. Anderson, L. W., & Krathwohl, D. R. (Eds.) (2001). *A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy*. New York: Longman.

12. Biggs, J. B., & Collis, K. F. (1982). *Evaluating the Quality of Learning: The SOLO Taxonomy*. New York: Academic Press.

13. Corbett, A. T., & Anderson, J. R. (1994). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction*, vol. 4, no. 4, pp. 253–278.

14. Pan, C., Li, N., Rusakov, M., & Faloutsos, C. (2017). Prerequisite relation learning for concepts in MOOCs. *Proceedings of the 55th Annual Meeting of the ACL*, pp. 1447–1456.

15. Leacock, C., & Chodorow, M. (2003). C-rater: Automated scoring of short-answer questions. *Computers in Human Behavior*, vol. 19, no. 4, pp. 491–508.

16. Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, vol. 33, no. 1, pp. 159–174.

17. Keim, D., Kohlhammer, J., Ellis, G., & Mansmann, F. (Eds.) (2010). *Mastering the Information Age: Solving Problems with Visual Analytics*. Goslar: Eurographics Association.

18. Amershi, S. et al. (2019). Software engineering for machine learning: A case study. *Proceedings of the 41st International Conference on Software Engineering (ICSE-SEIP)*, pp. 291–300.
