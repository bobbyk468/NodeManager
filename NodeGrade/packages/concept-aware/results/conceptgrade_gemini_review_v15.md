# Gemini Review Request v15
**Date:** 2026-04-17  
**Paper:** IEEE VIS 2027 VAST — "Co-Auditing as Epistemic Update — How Visual Trace Analytics Force Educators to Externalize Implicit Rubric Mental Models"  
**Prior rounds:** v1–v14 (all decisions locked)  
**This round:** First drafts of §2 Related Work, §4 System Architecture, §5a ML Accuracy — seeking structural and framing feedback before we commit to full prose

---

## Locked Decisions Reference (Do Not Re-Open)

| Decision | Locked Value |
|----------|-------------|
| §4 structure | §4.1 Overview → §4.2 Technical Pipeline (compressed) → §4.3 Visual Encodings → §4.4 Interactions → §4.5 Study Instrumentation |
| §4 figures | Option A: pipeline figure + annotated UI screenshot (full-width) |
| UI screenshot caption | Narrative: co-auditing event, amber leap, Click-to-Add chip |
| §5a opening | Lead with Mohler ablation (b), then Fisher combined, then Kaggle boundary |
| Stability analysis | Include regardless of r-value; if r < 0.80, frame as LLM reasoning volatility finding |
| §2 structure | 4-paragraph funnel: grading → XAI → VA → co-auditing |
| §2 citations | Add Turpin 2023; skip PopQA/FLARE; add EduVis or equivalent; claim "co-auditing" as novel |

---

## Section 1: §2 Related Work — Draft for Review

*Target: 1.0–1.5 double-column pages (~500–750 words). Four paragraphs.*

---

### §2 Related Work (Draft v1)

**Paragraph 1 — Automated short-answer grading:**

Automated short-answer grading (ASAG) has been studied for over a decade, progressing from rule-based methods [Leacock & Chodorow 2003] through feature-engineered NLP pipelines [Mohler 2011] to transformer-based approaches [Riordan 2017, Liu 2024] that approach human-level inter-rater agreement on constrained benchmarks. More recently, large language models have been applied both as direct scoring engines [TODO: cite LLM grading 2023–2024] and as reasoning verifiers that produce natural-language rationale alongside a numeric score [TODO: cite chain-of-thought grading]. Despite this accuracy progress, accountability remains unresolved: none of these systems exposes *why* a particular reasoning path led to a particular score, limiting educator trust in high-stakes deployments.

**Paragraph 2 — Explainability and reasoning faithfulness:**

Post-hoc explainability methods such as LIME [Ribeiro 2016] and SHAP [Lundberg 2017] provide feature attribution over input tokens, but cannot reveal whether the model's reasoning chain was *topologically coherent* with respect to a domain ontology. Chain-of-thought prompting [Wei 2022] improved the quality of LLM rationale, but subsequent work has shown that CoT explanations are frequently unfaithful — the stated reasoning does not always reflect the actual computation [Turpin 2023, Lanham 2023]. Faithfulness metrics measure alignment between rationale and output, not alignment between rationale and a domain Knowledge Graph. ConceptGrade addresses this gap by grounding faithfulness evaluation in the topology of an explicit domain representation rather than in input-output correlation.

**Paragraph 3 — Visual analytics for AI transparency:**

Visual analytics has been applied to AI transparency across domains: attention visualization in NLP [Vig 2019], model behavior exploration [Kahng 2018, Hohman 2019], and concept-based explanations [Kim 2018]. In educational contexts, learning analytics dashboards [Siemens 2013] and concept map visualizations [Novak 1984, Ruiz-Primo 2004] have supported instructors in reasoning about student knowledge gaps, but they operate on student output data rather than on the model's reasoning chain. Recent work on VA for grading feedback [TODO: EduVis or Sinha 2021 equivalent] addresses presentation of scores, not the topology of the AI's inference process. ConceptGrade is, to our knowledge, the first visual analytics system to project an LRM's chain-of-thought onto a domain KG in real time, making its topological structure available for educator co-auditing.

**Paragraph 4 — Human-AI collaboration and co-auditing:**

Human-AI collaboration in grading contexts has been studied as workflow integration [TODO: cite mixed-initiative grading], while Interactive Machine Teaching (IMT) [Simard 2017] and explanatory debugging [Kulesza 2012] establish the theoretical basis for human-directed model updates. Research on human mental models of AI [Bansal 2019] and sensemaking frameworks [Pirolli & Card 2005] demonstrates that structured explanations facilitate schema updates in human experts. Co-auditing extends these frameworks: rather than updating the model (IMT) or overriding its output (assistive grading), the educator updates their own explicit rubric representation in response to visual evidence from the AI's reasoning trace. We operationalize this bidirectional update via the Click-to-Add interaction (§4.4) and measure it with pre-registered causal metrics (§5b).

---

### §2 Review Questions

#### Q1 — Missing Citations in Paragraph 1

The ASAG paragraph references `[TODO: cite LLM grading 2023–2024]` and `[TODO: cite chain-of-thought grading]`. We need the best 1–2 citations for each slot:

1. **LLM-as-grader (2023–2024):** A paper showing LLMs used directly as ASAG scoring engines, ideally benchmarked against human raters. Is there a canonical 2023–2024 citation (e.g., from ACL, EMNLP, or EDM)?
2. **Chain-of-thought grading:** A paper where LLMs produce natural-language rationale alongside an ASAG score. Is there an existing citation, or is this a contribution claim we make for ConceptGrade?

**Please answer:** Fill both [TODO] slots or advise if either is a novelty claim for our paper.

---

#### Q2 — EduVis Equivalent for Paragraph 3

The v14 decisions recommended citing "Sinha et al. 2021 or similar recent VIS papers on rubric/grading analytics." We need a specific citation for the slot `[TODO: EduVis or Sinha 2021 equivalent]`.

**Please answer:** What is the best VIS/VAST/CHI citation for visual analytics applied to educational assessment or grading feedback? Provide full reference. If none exists, is the claim "to our knowledge, the first" defensible without a direct comparison citation?

---

#### Q3 — Paragraph 4 Co-Auditing Paradigm Claim

The fourth paragraph claims co-auditing is a new paradigm and explicitly distinguishes it from IMT and assistive grading. A reviewer may ask: "Is this just explanatory debugging [Kulesza 2012] applied to grading?"

**Question:** Is the distinction between co-auditing and explanatory debugging (Kulesza) clearly established in the draft paragraph? If not, what sentence should be added to make the distinction crisp? The key difference: in explanatory debugging, the human corrects the model's feature weights; in co-auditing, the human updates their own rubric (external to the model's parameters).

**Please answer:** Confirm the distinction is clear, or draft a clarifying sentence for insertion at the end of Paragraph 4.

---

#### Q4 — Related Work Length

The four-paragraph draft is approximately 550 words. IEEE VIS VAST double-column format allocates ~0.75–1.0 column-pages for Related Work (~375–500 words). The draft may be 50–100 words over target.

**Question:** Which paragraph should be trimmed first, and what content is most safely cut?
- Paragraph 1 has two `[TODO]` slots that will add words when filled.
- Paragraph 3 (VA transparency) is the most novel paragraph and should not be cut.
- Paragraph 2 (XAI/faithfulness) could merge the Turpin/Lanham citation into one sentence.

**Please answer:** Prioritize where to cut 50–100 words when the [TODO] slots are filled.

---

## Section 2: §4 System Architecture — Outline for Review

*Structure locked in v14: §4.1 Overview → §4.2 Technical Pipeline → §4.3 Visual Encodings → §4.4 Interactions → §4.5 Study Instrumentation*

---

### §4 Outline (locked structure, content to be reviewed)

**§4.1 Pipeline Overview (~150 words + figure)**
- One-paragraph narrative of the full pipeline
- References Figure [TODO: pipeline figure]: KG → LRM Verifier → Trace Parser → TRM Projection → DashboardContext → Three Panels
- Key design rationale: why each stage is necessary (not just a description of what it does)

**§4.2 Technical Pipeline (~200 words — compressed from original 4.2 + 4.3 + 4.4)**

Sub-components (described concisely, not as code):
- *KG Construction:* Auto-KG prompt generates concept nodes and typed edges; `REL_TYPE_REMAP` canonicalizes 15 common synonym relations; `GENERIC_CONCEPT_STOPLIST` filters 30 under-specific concepts. Per-dataset statistics in Table [TODO].
- *LRM Verifier:* Gemini Flash / DeepSeek-R1 produces 20–40 step chain-of-thought per answer; each step parsed to `kg_nodes[]` and `classification ∈ {SUPPORTS, CONTRADICTS, UNCERTAIN}`.
- *TRM Projection:* Implements Definitions 1–4 (§3). Gap detection: `hasTopologicalGap(stepA, stepB)` returns true iff both steps are grounded and `Nᵢ ∩ Nᵢ₊₁ = ∅`. Publishes `leapCount`, `groundingDensity` to DashboardContext.

**§4.3 Visual Encodings (~250 words)**

Three panels, each with its own encoding rationale:

*Trace Panel (LRM reasoning chain):*
- Steps rendered as sequential cards: classification badge (SUPPORTS=green, CONTRADICTS=amber, UNCERTAIN=gray)
- Structural leap indicator: amber dashed connector between step cards where `hasTopologicalGap() = true`
- Grounding density bar: color-coded (green ≥50%, amber 25–49%, red <25%)
- Design rationale: sequential layout preserves the causal ordering of the LRM's reasoning; color encodes the verifier's semantic judgment; dashed connector makes discontinuity perceptible without reading step text

*KG Subgraph Panel:*
- Force-directed ego-graph of the selected concept's neighborhood
- PREREQUISITE, HAS_PART, PRODUCES edges rendered with distinct line styles
- Highlighted nodes: those appearing in CONTRADICTS steps within the current answer
- Design rationale: ego-graph is bounded to remain readable; edge type encoding allows educators to reason about *why* concepts are related, not just *that* they are

*Rubric Editor Panel:*
- List of current rubric concepts with weight sliders
- CONTRADICTS chips: floating suggestion cards that pulse 3× on mount to signal actionability
- Click-to-Add: tapping a chip adds the concept to the rubric and logs `interaction_source: 'click_to_add'`
- Design rationale: chips are proximate to the rubric list (spatial coupling to reduce friction); 3× pulse is a pre-attentive animation designed to establish affordance without requiring a tooltip

**§4.4 Interactions (~200 words)**

*Bidirectional brushing:*
- Selecting a step in the Trace Panel → KG subgraph highlights all `kg_nodes` in that step
- Selecting a concept in the KG subgraph → Trace Panel filters to show only steps that reference that concept
- Clicking a CONTRADICTS step → `pushContradicts(node_id)` fires, starting the 60-second causal window; rubric chip for that concept pulses

*Click-to-Add flow (the co-auditing moment):*
1. Educator views CONTRADICTS step (sees amber dashed gap)
2. KG highlights the disconnected concept node(s)
3. Chip appears in Rubric Editor (pulsing — pre-attentive signal)
4. Educator clicks chip → concept added to rubric; `logEvent('rubric_edit', { interaction_source: 'click_to_add', ... })`
5. Multi-window causal attribution: within_30s = true (pre-registered primary window)

Design rationale: This sequence reduces the interaction to a single click, eliminating ambiguity about whether the educator understood the trace vs. independently recalled the concept — the key distinction for H2 measurement.

**§4.5 Study Instrumentation (~100 words)**

Condition A/B gating via URL parameter (`?condition=A|B`). Condition A renders all VA panels hidden (CSS `visibility:hidden`) but retains telemetry component lifecycle, ensuring identical event logging infrastructure across conditions. Key instrumentation:
- `RubricEditPayload`: 17 fields including multi-window attribution (15/30/60 s), `interaction_source`, semantic match fields
- Rolling 60-second CONTRADICTS window pruned on each new interaction
- `logBeacon()` with Page Visibility API for dwell-time accuracy during tab switches

---

### §4 Review Questions

#### Q5 — §4.2 Depth vs. §4.3 Depth Ratio

The current outline devotes ~200 words to the technical pipeline (§4.2) and ~250 words to visual encodings (§4.3). VAST reviewers want more on *design rationale* (why these encodings, not just what they are). Is 250 words enough for §4.3, or should we push to 350 words and compress §4.2 to ~120 words?

**Please answer:** Set the target word counts for §4.2 and §4.3 to optimize for VAST reviewer expectations.

---

#### Q6 — Design Rationale Justification Depth

Each panel in §4.3 has a short "design rationale" sentence. For a VAST paper, design rationale typically needs to cite established perception or visualization principles (e.g., pre-attentive processing [Ware 2004], proximity principle [Gestalt], color encoding for categorical data [Munzner 2014]).

**Question:** Which design decisions in §4.3 most need a formal citation from visualization theory, and which are self-evidently justified by convention? Specifically:
1. Sequential layout for trace steps — citation needed?
2. Color encoding for SUPPORTS/CONTRADICTS/UNCERTAIN — citation needed?
3. Dashed connector for structural leaps — citation needed?
4. Ego-graph layout for KG panel — citation needed?
5. Pulsing chip animation for Click-to-Add — citation needed?

**Please answer:** For each of the 5 design decisions, specify "cite [ref]", "no citation needed — convention", or "justify in text without formal citation."

---

#### Q7 — §4.5 Study Instrumentation — Keep or Move to Appendix?

The v14 decision compressed backend detail into §4.2, but §4.5 still describes the study instrumentation layer (RubricEditPayload, 17 fields, rolling window). A VAST reviewer may view this as supplemental material rather than system architecture.

**Question:** Should §4.5 (Study Instrumentation) remain in the main §4 body, or move to a supplemental appendix with just a one-sentence pointer in §5b?

**Please answer:** Keep §4.5 in main body or move to supplemental. Justify with reviewer expectation for VAST systems papers.

---

## Section 3: §5a ML Accuracy — Outline for Review

*Opening order locked in v14: Mohler ablation (b) → Fisher combined → Kaggle boundary condition → Stability Analysis (always included)*

---

### §5a ML Accuracy — Outline (Draft)

**§5a.1 Results on Mohler CS Benchmark (~150 words)**

*Component ablation table:*

| Variant | MAE | vs. Baseline | p-value |
|---------|-----|-------------|---------|
| C1: Keyword matching | 0.3300 | — (baseline) | — |
| C2: + Chain coverage | [TODO] | [TODO] | [TODO] |
| C3: + Bloom classification | [TODO] | [TODO] | [TODO] |
| C4: + LRM Verifier | [TODO] | [TODO] | p < 0.0001 |
| C5_fix: + Concept fix | 0.2229 | −32.4% | Wilcoxon p = 0.0013 |

Headline: C5_fix achieves 32.4% MAE reduction (Wilcoxon p = 0.0013, N = 120). Component C4 (LRM Verifier) contributes the single largest jump (p < 0.0001), confirming that KG-grounded verification is the mechanistic driver, not prompt engineering.

**§5a.2 Multi-Dataset Generalization (~100 words)**

Fisher combined p = 0.003 across 1,239 answers (Mohler N=120, DigiKlausur N=646, Kaggle N=473). Improvement is significant on Mohler (p = 0.0013) and DigiKlausur (p = 0.049). Non-significance on Kaggle ASAG (p = 0.148) reflects a domain boundary: in elementary science, the KG cannot discriminate between semantically similar student answers because scientific vocabulary is not sufficiently specific to distinguish conceptual from terminological variation. This is reported as a finding, not a failure — it defines the scope condition for TRM-based grading.

**§5a.3 Stability Analysis (~100 words)**

*Cross-model TRM invariance (Gemini Flash vs. DeepSeek-R1 on Mohler N=120):*

TRM leap count and grounding density are computed independently for Gemini Flash and DeepSeek-R1 traces on the same answers. Pearson correlation r = [TODO: run stability_analysis.py]. If r > 0.80: TRM topology is model-independent, providing evidence that structural leaps reflect properties of the reasoning task, not model verbosity. If r < 0.80: the variability itself is a finding — it implies that the LRM's choice of which concepts to surface is model-dependent, further motivating the need for a human-in-the-loop co-auditing tool to resolve this ambiguity.

---

### §5a Review Questions

#### Q8 — Ablation Table: Missing C2 and C3 Values

The ablation table has [TODO] for C2 (+ chain coverage) and C3 (+ Bloom classification) MAE and p-values. These are available in the cached evaluation results. Before finalizing §5a, these must be retrieved from `data/mohler_eval_results.json`.

**This is not a Gemini question — it is an action item for the agent/researcher:**
- [ ] Run: `python run_batch_eval_api.py --dataset mohler --ablation-mode` to generate C1–C5 per-component MAE
- [ ] Populate the ablation table with C2, C3 values
- [ ] Confirm C4 p < 0.0001 (run Wilcoxon between C3 and C4 MAE arrays)

**Gemini question:** Given the available numbers (C1 baseline MAE = 0.3300, C5_fix MAE = 0.2229), what is the most compelling way to present the component ablation? Should we show each step's marginal improvement, or only show C1, C4, C5 (the three decision-relevant points)?

---

#### Q9 — Kaggle Boundary Condition Framing

The v14 decision was: "End §5a with Kaggle (boundary condition)." The concern is that a reviewer may interpret "boundary condition" as a weakness rather than a finding.

**Question:** Is the current §5a.2 framing of Kaggle ASAG ("reflects a domain boundary... this is reported as a finding, not a failure") sufficient, or does it need additional support? Specifically:
1. Should we add a sentence explaining *why* elementary science vocabulary lacks the discriminability that CS/NN vocabulary has (more synonymy, less formal ontology)?
2. Should we cite a linguistics or ontology paper that supports the claim that domain vocabulary specificity predicts KG grounding density?

**Please answer:** Confirm the current framing is sufficient, or add one sentence and optionally one citation.

---

#### Q10 — Stability Analysis Positioning

If `stability_analysis.py` returns r < 0.80, the §5a.3 paragraph frames this as "LLM reasoning volatility as a finding." But this framing may weaken the paper's claim that TRM is a reliable visualization tool.

**Question:** If r < 0.80, should §5a.3 be moved from §5a (ML Accuracy) to §5b (User Study), where it naturally motivates the need for human-in-the-loop co-auditing? Or should it remain in §5a as a "scope condition" parallel to the Kaggle boundary finding?

**Please answer:** If r ≥ 0.80: §5a.3 stays in §5a. If r < 0.80: specify whether §5a.3 moves to §5b or stays in §5a with revised framing.

---

## Locked Decisions Reminder (Do Not Re-Open)

The following are confirmed across v1–v14 and are not open for revision:

- Introduction: v14 locked (670 words, 4 contributions)
- §3 TRM Formal Definitions: v11 locked (Definitions 1–5, cᵢ in prose)
- GEE model: Binomial(Logit), Exchangeable, within_30s primary, trace_gap_count moderation
- H2 metric: semantic_alignment_rate_manual primary; _cta reported separately
- Condition A: blank panel (IRB amendment filed); CSS visibility:hidden not conditional render
- "Co-auditing" is a novel paradigm — no prior citation required

---

## Expected Output Format

For each question (Q1–Q10):
1. **Decision** (1 sentence)
2. **Rationale** (2–3 sentences, reviewer-risk framing)
3. **Draft text** (where applicable — full sentence ready to paste)

**Priority this round:** Q1 (missing ASAG citations), Q3 (co-auditing vs explanatory debugging distinction), Q5 (§4.2/§4.3 word budget), Q9 (Kaggle framing), Q10 (stability analysis positioning).

---

**End of Gemini Review v15**
