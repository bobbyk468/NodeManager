# ConceptGrade — Introduction Draft v13
**Date:** 2026-04-17  
**Context:** IEEE VIS 2027 VAST — writing phase  
**Prior reviews:** v1–v12 (ablation → TRM formalization → Introduction v12 + Q1–Q5)  
**This version:** Q1–Q5 edits applied; target ~650 words; ready for §3 / §4 / §5a drafting

---

## Changes Applied from Gemini v12 Q1–Q5

| # | Decision | Change |
|---|----------|--------|
| Q1 | Add CoT concession sentence | Added to para 2 before LIME/SHAP cut |
| Q2 | Cite Kulesza 2012 + Bansal 2019, not Norman | "implicit mental models" now cites [Kulesza 2012, Bansal 2019] |
| Q3 | Mark X/Y/Z as explicit [TODO] placeholders | All placeholders annotated |
| Q4 | Narrow "first approach" to VA + educational context | Contribution 1 scope narrowed |
| Q5 | Cut LIME/SHAP para, trim eval, target 650 words | Para 2 reduced by ~250 words; eval para trimmed |

---

## §1 Introduction (v13 — ~640 words)

Automated short-answer grading has reached human-level accuracy on structured benchmarks [Mohler 2011, Dzikovska 2016, Liu 2024], yet educators remain reluctant to rely on it in high-stakes assessments. The bottleneck is not performance — it is accountability: when a model downgrades a student's answer, the educator has no mechanism to inspect why. This opacity makes the system an oracle to be trusted or ignored, rather than a collaborator to be audited. We argue that the missing link is not a better model, but a better interface — one that projects the model's reasoning onto the educator's domain knowledge, creating a shared visual topology for co-auditing. We present **ConceptGrade**, a visual analytics system that implements this topology through **Topological Reasoning Mapping (TRM)**: a technique that projects a large reasoning model's chain-of-thought onto a domain Knowledge Graph, enabling educators to co-audit both machine reasoning and student knowledge gaps simultaneously.

The opacity problem is structural. Large reasoning models (LRMs) produce extensive chain-of-thought rationale for every grading decision, yet this rationale is generated as a flat sequence of propositions disconnected from any formal domain representation. Recent work on chain-of-thought prompting [Wei 2022] demonstrates that LRMs can produce domain-accurate reasoning chains — our claim is not that the reasoning is wrong, but that its topological structure is invisible to the educator without a reference Knowledge Graph. An educator reading "the student partially addresses backpropagation but misses the role of the learning rate" cannot determine whether the model correctly identified a conceptual gap or made an inferential leap that no domain expert would sanction. Existing explanatory AI techniques answer "what did the model look at?" but not "was the model's reasoning *about the domain* coherent?" — a fundamentally different question that requires a structured domain representation.

This gap motivates a different design paradigm. Rather than explaining a model's behavior post-hoc, ConceptGrade situates the model's reasoning *within* the domain Knowledge Graph during grading, exposing the topological structure of its chain-of-thought in real time. When the LRM's reasoning trace jumps between disconnected KG regions — referencing `processing_unit` in one step and `human_brain` in the next, with no bridging concept — TRM flags this as a structural leap: an incomplete explanation that an educator can inspect, question, and act on. The educator's response — adding the skipped concept to the rubric — is not a correction of the model's output but an update to their own implicit mental model of what the rubric should require [Kulesza 2012, Bansal 2019]. This bidirectional process, in which both the AI and the educator refine their domain representations, is what we term **co-auditing**.

Co-auditing is distinct from two superficially similar paradigms. *Assistive grading* is unidirectional: the AI grades, the human approves or overrides. *Interactive Machine Teaching* (IMT) [Simard 2017] involves the human updating the model's weights or decision rules. In co-auditing, neither the model's weights nor the human's final grade necessarily change — what changes is the educator's explicit understanding of the rubric, surfaced by the act of inspecting reasoning that would otherwise remain opaque. ConceptGrade realizes this through three linked panels — an LRM trace viewer, a KG subgraph, and a rubric editor — connected by bidirectional brushing: clicking a CONTRADICTS step highlights the implicated KG nodes; clicking a KG node filters the trace to steps that reference it; clicking a chip in the rubric editor logs the concept the educator chose to act on.

We evaluate ConceptGrade at two levels. The KG-grounded pipeline reduces Mean Absolute Error by 32.4% over a pure LLM baseline on the Mohler CS benchmark (N = 120), with Fisher combined p = 0.003 across 1,239 answers from three datasets. A controlled user study (N = [TODO: X] educators, two conditions) demonstrates that educators exposed to TRM visualization make rubric edits with a semantic alignment rate of [TODO: Y]% versus a hypergeometric null of [TODO: Z]%, providing quantitative evidence that the visualization facilitates alignment between the machine's domain model and the educator's pedagogical reasoning.

---

## Contributions

1. **Topological Reasoning Mapping (TRM)** — A formal technique (Definitions 1–5, §3) that maps each LRM reasoning step to KG concept nodes, defines structural leaps, and introduces leap count and grounding density as measurable trace properties. To our knowledge, TRM is the first visual analytics approach to operationalize reasoning-chain continuity as a visualizable topological property in the educational grading context.

2. **Bidirectional Co-Auditing Interface** — A visual analytics system (§4) linking an LRM trace panel, a KG subgraph, and a rubric editor through bidirectional brushing. The Click-to-Add interaction provides zero-ambiguity attribution for causal proximity analysis.

3. **Multi-Dataset ML Accuracy Evidence** — 32.4% MAE reduction on Mohler (N = 120); Fisher combined p = 0.003 across 1,239 answers from three domain datasets. Non-significance on Kaggle ASAG defines the KG discriminability boundary condition (§5a).

4. **Controlled User Study with Pre-Registered Causal Metrics** — Two-condition study using multi-window causal attribution (primary: 30 s), semantic alignment rate as the H2 primary metric, and leap count as a pre-registered H1 moderator, analyzed via GEE Binomial/Logit with exchangeable working correlation (§5b).
