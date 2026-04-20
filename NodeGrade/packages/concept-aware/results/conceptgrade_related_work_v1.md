# ConceptGrade — §2 Related Work (v1)
**Date:** 2026-04-17  
**Context:** IEEE VIS 2027 VAST — writing phase  
**Decisions applied:** Gemini v15 Q1–Q4 locked  
**Target:** ~500 words, 4-paragraph funnel structure

---

## Changes Applied from Gemini v15 Q1–Q4

| # | Decision | Applied |
|---|----------|---------|
| Q1 | [Zheng 2023, Mizumoto 2023] for LLM-as-grader; [Kojima 2022] for CoT rationale | ✅ Para 1 |
| Q2 | [Chen 2020, Sinha 2021] + "to our knowledge" claim | ✅ Para 3 |
| Q3 | Add clarifying sentence distinguishing co-auditing from explanatory debugging | ✅ Para 4, final sentence |
| Q4 | Trim Para 1 first sentence to remove pre-BERT history | ✅ Para 1 |

---

## §2 Related Work v2 (~450 words — FINAL)

**Automated Short-Answer Grading.**
Automated short-answer grading has progressed from rule-based pipelines [Mohler 2011] to transformer-based scoring engines [Liu 2024] that approach human-level inter-rater agreement on constrained benchmarks. More recently, LLMs have been applied as direct scoring engines [Zheng 2023, Mizumoto 2023] and as reasoning verifiers that produce natural-language rationale alongside a numeric score [Kojima 2022]. Despite this accuracy progress, accountability remains unresolved: none of these systems exposes why a particular reasoning path led to a particular score, limiting educator trust in high-stakes grading deployments.

**Explainability and Reasoning Faithfulness.**
Post-hoc explainability methods such as LIME [Ribeiro 2016] and SHAP [Lundberg 2017] provide feature attribution over input tokens but cannot reveal whether the model's reasoning chain was topologically coherent with respect to a domain ontology. Chain-of-thought prompting [Wei 2022] improved the quality of LLM rationale, but subsequent work has shown that CoT explanations are frequently unfaithful — the stated reasoning does not always reflect the actual computation [Turpin 2023, Lanham 2023]. Faithfulness metrics measure alignment between rationale and output; ConceptGrade instead grounds the coherence question in KG topology: is the model's reasoning chain connected within the domain graph, regardless of whether it influenced the final score?

**Visual Analytics for AI Transparency.**
Visual analytics has been applied to AI transparency in NLP and concept-based explanations [Kim 2018]. In educational contexts, learning analytics dashboards [Siemens 2013] and concept map visualizations [Novak 1984, Ruiz-Primo 2004] support instructors in reasoning about student knowledge structure. Recent work on VA for grading feedback [Chen 2020, Sinha 2021] addresses the presentation of scores and aggregated rubrics, not the topology of the AI's inference process. To our knowledge, ConceptGrade is the first visual analytics system in the educational context to project an LRM's chain-of-thought onto a domain Knowledge Graph in real time, making its topological structure available for educator co-auditing.

**Human-AI Collaboration and Co-Auditing.**
Interactive Machine Teaching (IMT) [Simard 2017] and explanatory debugging [Kulesza 2012] provide theoretical groundings for human-directed model updates. Research on human mental models of AI [Bansal 2019] and sensemaking frameworks [Pirolli & Card 2005] demonstrates that structured explanations facilitate schema updates in expert users. Co-auditing extends these frameworks: rather than updating the model (IMT) or overriding its output (assistive grading), the educator updates their explicit rubric representation in response to visual evidence from the AI's reasoning trace. Crucially, whereas explanatory debugging asks the human to adjust model parameters to fix the machine, co-auditing leverages the machine's reasoning trace to help the human externalize and refine their own evaluation criteria — the rubric itself, not the model's weights.

---

## Open [TODO] Items (v2)

- [ ] Confirm Sinha 2021 full reference is in bibliography
- [ ] Confirm Mizumoto 2023 full reference is in bibliography
- [ ] Confirm Chen 2020 (ViTA) is in bibliography or replace with confirmed VIS paper
