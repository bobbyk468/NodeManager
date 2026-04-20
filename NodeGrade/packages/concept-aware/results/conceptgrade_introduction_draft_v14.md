# ConceptGrade — Introduction Draft v14
**Date:** 2026-04-17  
**Context:** IEEE VIS 2027 VAST — writing phase  
**Prior reviews:** v1–v14 (all decisions locked through Q10)  
**This version:** Gemini v14 Q1–Q5 applied; ready for §2 / §4 / §5a drafting

---

## Changes Applied from Gemini v14 Q1–Q5

| # | Decision | Change |
|---|----------|--------|
| Q1 | Add bridging sentence to Para 2 opening | Added "Addressing this accountability gap requires more than algorithmic improvements..." |
| Q2 | Add Pirolli & Card 2005 to mental models citation | `[Kulesza 2012, Bansal 2019, Pirolli & Card 2005]` |
| Q3 | Standardize [TODO] placeholders | Confirmed: no stray "Figure X" or `[cite]` in intro body; [TODO: X/Y/Z] already present |
| Q4 | Keep contribution bullet order | No change — TRM → System → ML → Study ordering locked |
| Q5 | Rename Contribution 2 | "Co-Auditing Visual Analytics System" replaces "Bidirectional Co-Auditing Interface" |

---

## §1 Introduction (v14 — ~670 words)

Automated short-answer grading has reached human-level accuracy on structured benchmarks [Mohler 2011, Dzikovska 2016, Liu 2024], yet educators remain reluctant to rely on it in high-stakes assessments. The bottleneck is not performance — it is accountability: when a model downgrades a student's answer, the educator has no mechanism to inspect why. This opacity makes the system an oracle to be trusted or ignored, rather than a collaborator to be audited. We argue that the missing link is not a better model, but a better interface — one that projects the model's reasoning onto the educator's domain knowledge, creating a shared visual topology for co-auditing. We present **ConceptGrade**, a visual analytics system that implements this topology through **Topological Reasoning Mapping (TRM)**: a technique that projects a large reasoning model's chain-of-thought onto a domain Knowledge Graph, enabling educators to co-audit both machine reasoning and student knowledge gaps simultaneously.

Addressing this accountability gap requires more than algorithmic improvements; it demands an interface that exposes the structural nature of the opacity itself. The opacity problem is fundamentally structural: large reasoning models (LRMs) produce extensive chain-of-thought rationale for every grading decision, yet this rationale is generated as a flat sequence of propositions disconnected from any formal domain representation. Recent work on chain-of-thought prompting [Wei 2022] demonstrates that LRMs can produce domain-accurate reasoning chains — our claim is not that the reasoning is wrong, but that its topological structure is invisible to the educator without a reference Knowledge Graph. An educator reading "the student partially addresses backpropagation but misses the role of the learning rate" cannot determine whether the model correctly identified a conceptual gap or made an inferential leap that no domain expert would sanction. Existing explanatory AI techniques answer "what did the model look at?" but not "was the model's reasoning *about the domain* coherent?" — a fundamentally different question that requires a structured domain representation.

This gap motivates a different design paradigm. Rather than explaining a model's behavior post-hoc, ConceptGrade situates the model's reasoning *within* the domain Knowledge Graph during grading, exposing the topological structure of its chain-of-thought in real time. When the LRM's reasoning trace jumps between disconnected KG regions — referencing `processing_unit` in one step and `human_brain` in the next, with no bridging concept — TRM flags this as a structural leap: an incomplete explanation that an educator can inspect, question, and act on. The educator's response — adding the skipped concept to the rubric — is not a correction of the model's output but an update to their own implicit mental model of what the rubric should require [Kulesza 2012, Bansal 2019, Pirolli & Card 2005]. This bidirectional process, in which both the AI and the educator refine their domain representations, is what we term **co-auditing**.

Co-auditing is distinct from two superficially similar paradigms. *Assistive grading* is unidirectional: the AI grades, the human approves or overrides. *Interactive Machine Teaching* (IMT) [Simard 2017] involves the human updating the model's weights or decision rules. In co-auditing, neither the model's weights nor the human's final grade necessarily change — what changes is the educator's explicit understanding of the rubric, surfaced by the act of inspecting reasoning that would otherwise remain opaque. ConceptGrade realizes this through three linked panels — an LRM trace viewer, a KG subgraph, and a rubric editor — connected by bidirectional brushing: clicking a CONTRADICTS step highlights the implicated KG nodes; clicking a KG node filters the trace to steps that reference it; clicking a chip in the rubric editor logs the concept the educator chose to act on.

We evaluate ConceptGrade at two levels. The KG-grounded pipeline reduces Mean Absolute Error by 32.4% over a pure LLM baseline on the Mohler CS benchmark (N = 120), with Fisher combined p = 0.003 across 1,239 answers from three datasets. A controlled user study (N = [TODO: X] educators, two conditions) demonstrates that educators exposed to TRM visualization make rubric edits with a semantic alignment rate of [TODO: Y]% versus a hypergeometric null of [TODO: Z]%, providing quantitative evidence that the visualization facilitates alignment between the machine's domain model and the educator's pedagogical reasoning.

---

## Contributions (v14)

1. **Topological Reasoning Mapping (TRM)** — A formal technique (Definitions 1–5, §3) that maps each LRM reasoning step to KG concept nodes, defines structural leaps, and introduces leap count and grounding density as measurable trace properties. To our knowledge, TRM is the first visual analytics approach to operationalize reasoning-chain continuity as a visualizable topological property in the educational grading context.

2. **Co-Auditing Visual Analytics System** — An end-to-end visual analytics system (§4) linking an LRM trace panel, a KG subgraph, and a rubric editor through bidirectional brushing. The Click-to-Add interaction provides zero-ambiguity attribution for causal proximity analysis.

3. **Multi-Dataset ML Accuracy Evidence** — 32.4% MAE reduction on Mohler (N = 120); Fisher combined p = 0.003 across 1,239 answers from three domain datasets. Non-significance on Kaggle ASAG defines the KG discriminability boundary condition (§5a).

4. **Controlled User Study with Pre-Registered Causal Metrics** — Two-condition study using multi-window causal attribution (primary: 30 s), semantic alignment rate as the H2 primary metric, and leap count as a pre-registered H1 moderator, analyzed via GEE Binomial/Logit with exchangeable working correlation (§5b).

---

## Status: Introduction Complete — Next Sections

| Section | Status | Inputs Available |
|---------|--------|-----------------|
| §1 Introduction | ✅ v14 locked | — |
| §2 Related Work | 🔲 Draft next | Q6/Q7 decisions from v14 review |
| §3 TRM Formalization | ✅ v11 locked | Definition Box v11 + Running Example |
| §4 System Architecture | 🔲 Draft next | Q8/Q9 structure from v14 review |
| §5a ML Accuracy | 🔲 Draft next | All data available; Q10 ordering from v14 review |
| §5b User Study | ⏳ Post-pilot | Waiting for IRB + recruitment |
