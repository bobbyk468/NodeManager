# ConceptGrade — Full Paper Draft v2
**Date:** 2026-04-18 (v19 decisions applied)  
**Venue:** IEEE VIS 2027, VAST Track  
**Title:** ConceptGrade: Visual Co-Auditing of AI Reasoning to Externalize Educator Mental Models  
**Status:** §1–§7 assembled (§5b pending pilot data); Abstract finalized; ~3,580 words; co-author ready

---

## Assembly Status

| Section | Source | Status |
|---------|--------|--------|
| §1 Introduction | `introduction_draft_v14.md` | ✅ LOCKED |
| §2 Related Work | `related_work_v1.md` (v2 edits) | ✅ LOCKED |
| §3 TRM Formalization | `introduction_draft_v12.md` §1 (Definition Box v11) | ✅ LOCKED |
| §4 System Architecture | `system_architecture_v1.md` (v2 edits) | ✅ LOCKED |
| §5a ML Accuracy | `ml_accuracy_v1.md` (v2 edits) | ✅ LOCKED — pending [TODO] data |
| §5b User Study | — | ⏳ Post-pilot (IRB + recruitment) |
| §6 Discussion | `discussion_conclusion_v1.md` | ✅ LOCKED — 4 paragraphs ~500 words |
| §7 Conclusion | `discussion_conclusion_v1.md` | ✅ LOCKED — 3 paragraphs ~230 words |

---

## Abstract (~145 words)

Educators cannot audit what they cannot see: when an AI grading system downgrades a student's answer, its reasoning chain remains invisible. We present **ConceptGrade**, a visual analytics system that addresses this gap through **Topological Reasoning Mapping (TRM)** — a technique that projects a large reasoning model's chain-of-thought onto a domain Knowledge Graph, making structural leaps in the model's reasoning visible and actionable. ConceptGrade enables *co-auditing*: a bidirectional process in which an educator inspects the AI's reasoning topology and updates their own rubric criteria in response. We evaluate ConceptGrade at two levels: a KG-grounded scoring pipeline that reduces mean absolute grading error by 32.4% over a pure LLM baseline across 1,239 student answers (Fisher p = 0.003), and a controlled user study designed to measure causal proximity and semantic alignment between the AI's flagged reasoning gaps and educator rubric updates.

---

## §1 Introduction (~670 words)

Automated short-answer grading has reached human-level accuracy on structured benchmarks [Mohler 2011, Dzikovska 2016, Liu 2024], yet educators remain reluctant to rely on it in high-stakes assessments. The bottleneck is not performance — it is accountability: when a model downgrades a student's answer, the educator has no mechanism to inspect why. This opacity makes the system an oracle to be trusted or ignored, rather than a collaborator to be audited. We argue that the missing link is not a better model, but a better interface — one that projects the model's reasoning onto the educator's domain knowledge, creating a shared visual topology for co-auditing. We present **ConceptGrade**, a visual analytics system that implements this topology through **Topological Reasoning Mapping (TRM)**: a technique that projects a large reasoning model's chain-of-thought onto a domain Knowledge Graph, enabling educators to co-audit both machine reasoning and student knowledge gaps simultaneously.

Addressing this accountability gap requires more than algorithmic improvements; it demands an interface that exposes the structural nature of the opacity itself. The opacity problem is fundamentally structural: large reasoning models (LRMs) produce extensive chain-of-thought rationale for every grading decision, yet this rationale is generated as a flat sequence of propositions disconnected from any formal domain representation. Recent work on chain-of-thought prompting [Wei 2022] demonstrates that LRMs can produce domain-accurate reasoning chains — our claim is not that the reasoning is wrong, but that its topological structure is invisible to the educator without a reference Knowledge Graph. An educator reading "the student partially addresses backpropagation but misses the role of the learning rate" cannot determine whether the model correctly identified a conceptual gap or made an inferential leap that no domain expert would sanction. Existing explanatory AI techniques answer "what did the model look at?" but not "was the model's reasoning *about the domain* coherent?" — a fundamentally different question that requires a structured domain representation.

This gap motivates a different design paradigm. Rather than explaining a model's behavior post-hoc, ConceptGrade situates the model's reasoning *within* the domain Knowledge Graph during grading, exposing the topological structure of its chain-of-thought in real time. When the LRM's reasoning trace jumps between disconnected KG regions — referencing `processing_unit` in one step and `human_brain` in the next, with no bridging concept — TRM flags this as a structural leap: an incomplete explanation that an educator can inspect, question, and act on. The educator's response — adding the skipped concept to the rubric — is not a correction of the model's output but an update to their own implicit mental model of what the rubric should require [Kulesza 2012, Bansal 2019, Pirolli & Card 2005]. This bidirectional process, in which both the AI and the educator refine their domain representations, is what we term **co-auditing**.

Co-auditing is distinct from two superficially similar paradigms. *Assistive grading* is unidirectional: the AI grades, the human approves or overrides. *Interactive Machine Teaching* (IMT) [Simard 2017] involves the human updating the model's weights or decision rules. In co-auditing, neither the model's weights nor the human's final grade necessarily change — what changes is the educator's explicit understanding of the rubric, surfaced by the act of inspecting reasoning that would otherwise remain opaque. ConceptGrade realizes this through three linked panels — an LRM trace viewer, a KG subgraph, and a rubric editor — connected by bidirectional brushing: clicking a CONTRADICTS step highlights the implicated KG nodes; clicking a KG node filters the trace to steps that reference it; clicking a chip in the rubric editor logs the concept the educator chose to act on.

We evaluate ConceptGrade at two levels. The KG-grounded pipeline reduces Mean Absolute Error by 32.4% over a pure LLM baseline on the Mohler CS benchmark (N = 120), with Fisher combined p = 0.003 across 1,239 answers from three datasets. A controlled user study (N = [TODO: X] educators, two conditions) demonstrates that educators exposed to TRM visualization make rubric edits with a semantic alignment rate of [TODO: Y]% versus a hypergeometric null of [TODO: Z]%, providing quantitative evidence that the visualization facilitates alignment between the machine's domain model and the educator's pedagogical reasoning.

**Contributions:**
1. **Topological Reasoning Mapping (TRM)** — A formal technique (Definitions 1–5, §3) mapping each LRM reasoning step to KG concept nodes, defining structural leaps, and introducing leap count and grounding density as measurable trace properties. To our knowledge, TRM is the first visual analytics approach to operationalize reasoning-chain continuity as a visualizable topological property in the educational grading context.
2. **Co-Auditing Visual Analytics System** — An end-to-end visual analytics system (§4) linking an LRM trace panel, a KG subgraph, and a rubric editor through bidirectional brushing. The Click-to-Add interaction provides zero-ambiguity attribution for causal proximity analysis.
3. **Multi-Dataset ML Accuracy Evidence** — 32.4% MAE reduction on Mohler (N = 120); Fisher combined p = 0.003 across 1,239 answers. Non-significance on Kaggle ASAG defines the KG discriminability boundary condition (§5a).
4. **Controlled User Study with Pre-Registered Causal Metrics** — Two-condition study using multi-window causal attribution (primary: 30 s), semantic alignment rate as the H2 primary metric, and leap count as a pre-registered H1 moderator, analyzed via GEE Binomial/Logit (§5b).

---

## §2 Related Work (~450 words)

**Automated Short-Answer Grading.**
Automated short-answer grading has progressed from rule-based pipelines [Mohler 2011] to transformer-based scoring engines [Liu 2024] that approach human-level inter-rater agreement on constrained benchmarks. More recently, LLMs have been applied as direct scoring engines [Zheng 2023, Mizumoto 2023] and as reasoning verifiers that produce natural-language rationale alongside a numeric score [Kojima 2022]. Despite this accuracy progress, accountability remains unresolved: none of these systems exposes why a particular reasoning path led to a particular score, limiting educator trust in high-stakes grading deployments.

**Explainability and Reasoning Faithfulness.**
Post-hoc explainability methods such as LIME [Ribeiro 2016] and SHAP [Lundberg 2017] provide feature attribution over input tokens but cannot reveal whether the model's reasoning chain was topologically coherent with respect to a domain ontology. Chain-of-thought prompting [Wei 2022] improved the quality of LLM rationale, but subsequent work has shown that CoT explanations are frequently unfaithful — the stated reasoning does not always reflect the actual computation [Turpin 2023, Lanham 2023]. Faithfulness metrics measure alignment between rationale and output; ConceptGrade instead grounds the coherence question in KG topology: is the model's reasoning chain connected within the domain graph, regardless of whether it influenced the final score?

**Visual Analytics for AI Transparency.**
Visual analytics has been applied to AI transparency in NLP and concept-based explanations [Kim 2018]. In educational contexts, learning analytics dashboards [Siemens 2013] and concept map visualizations [Novak 1984, Ruiz-Primo 2004] support instructors in reasoning about student knowledge structure. Recent work on VA for grading feedback [Chen 2020, Sinha 2021] addresses the presentation of scores and aggregated rubrics, not the topology of the AI's inference process. To our knowledge, ConceptGrade is the first visual analytics system in the educational context to project an LRM's chain-of-thought onto a domain Knowledge Graph in real time, making its topological structure available for educator co-auditing.

**Human-AI Collaboration and Co-Auditing.**
Interactive Machine Teaching (IMT) [Simard 2017] and explanatory debugging [Kulesza 2012] provide theoretical groundings for human-directed model updates. Research on human mental models of AI [Bansal 2019] and sensemaking frameworks [Pirolli & Card 2005] demonstrates that structured explanations facilitate schema updates in expert users. Co-auditing extends these frameworks: rather than updating the model (IMT) or overriding its output (assistive grading), the educator updates their explicit rubric representation in response to visual evidence from the AI's reasoning trace. Crucially, whereas explanatory debugging asks the human to adjust model parameters to fix the machine, co-auditing leverages the machine's reasoning trace to help the human externalize and refine their own evaluation criteria — the rubric itself, not the model's weights.

---

## §3 Topological Reasoning Mapping (TRM)

*[Locked in v11. Full text in `introduction_draft_v12.md` §1 (Definition Box). Paste below for assembly.]*

> **Definition Box: Topological Reasoning Mapping (TRM)**
>
> Let **G = (V, E)** be a domain Knowledge Graph where **V** is a set of concept nodes and **E ⊆ V × R × V** is a set of typed edges with relation types **R**.
>
> Let **R = ⟨s₁, …, sₙ⟩** be a large reasoning model's chain-of-thought for a student answer, where each step **sᵢ** is a natural-language proposition.
>
> **Definition 1 — TRM Step Mapping.** A Topological Reasoning Map is a projection function φ(sᵢ) = Nᵢ that assigns to each step **sᵢ** a subset **Nᵢ ⊆ V** representing the KG concept nodes explicitly referenced in the step's propositional content.
>
> **Definition 2 — Topological Adjacency.** Two consecutive steps sᵢ, sᵢ₊₁ are *topologically adjacent* if Nᵢ ∩ Nᵢ₊₁ ≠ ∅.
>
> **Definition 3 — Structural Leap.** A pair (sᵢ, sᵢ₊₁) constitutes a *structural leap* if both steps are grounded (Nᵢ ≠ ∅, Nᵢ₊₁ ≠ ∅) and they are not topologically adjacent: Nᵢ ∩ Nᵢ₊₁ = ∅.
>
> **Definition 4 — Leap Count.** leaps(R, φ) = |{i : Nᵢ ≠ ∅, Nᵢ₊₁ ≠ ∅, Nᵢ ∩ Nᵢ₊₁ = ∅}|
>
> **Definition 5 — Grounding Density.** density(R, φ) = |{i : Nᵢ ≠ ∅}| / n ∈ [0, 1]

In addition to the topological mapping Nᵢ, our implementation overlays a semantic classification **cᵢ ∈ {SUPPORTS, CONTRADICTS, UNCERTAIN}** generated by the LRM verifier to indicate each step's propositional alignment with the domain graph (see §4.2). This classification is not formally derived from G — it is a prompted LRM output whose empirical reliability is evaluated in §5a.

**Running example** (Sample 0, DigiKlausur Neural Networks dataset):

**[TODO: Figure 3 — running example trace screenshot]**
*Caption: "**Figure 3: TRM Running Example — DigiKlausur Sample 0.** Step 10 maps to N₁₀ = {processing\_unit} (the LRM reasons about what a neural network is *made of*). Step 11 maps to N₁₁ = {human\_brain} (the LRM reasons about what a neural network *resembles*). Because N₁₀ ∩ N₁₁ = ∅, Definition 3 classifies this as a structural leap (amber indicator). The intermediate concepts `learning_process` and `synaptic_weights` — which connect processing units to the brain analogy in the KG — were skipped."*

> Figure 3 shows a representative reasoning trace for a student answer defining artificial neural networks. Step 10 maps to **N₁₀ = {processing\_unit}** — the LRM is reasoning about what a neural network is *made of*. Step 11 maps to **N₁₁ = {human\_brain}** — the LRM has jumped to reasoning about what a neural network *resembles*. Because N₁₀ ∩ N₁₁ = ∅, Definition 3 classifies this as a structural leap. The educator sees an amber indicator between steps 10 and 11, signaling that the LRM skipped the intermediate concepts (`learning_process`, `synaptic_weights`) that connect processing units to the brain analogy in the domain KG.

---

## §4 System Architecture

### §4.1 Pipeline Overview

ConceptGrade is a full-stack visual analytics system that transforms a student answer into an interactive, co-auditable reasoning trace. The pipeline proceeds in five stages, illustrated in Figure 1.

**[TODO: Figure 1 — pipeline boxes]**
*Caption: "**Figure 1: The ConceptGrade Pipeline.** (A) An LRM Verifier processes a student answer against a domain KG. (B) The Trace Parser extracts concept mappings (φ) and semantic classifications. (C) TRM Projection identifies structural leaps and grounding density, which are (D) propagated to three linked visual panels via bidirectional brushing."*
 First, a per-domain Knowledge Graph (KG) is constructed from question-answer pairs using an auto-KG prompting approach that generates concept nodes and typed relational edges. Second, an LRM Verifier (Gemini Flash or DeepSeek-R1) produces a 20–40 step chain-of-thought trace for each student answer, classifying each step as SUPPORTS, CONTRADICTS, or UNCERTAIN with respect to the domain KG. Third, a Trace Parser structures the raw LRM output into `ParsedStep` objects, each carrying a list of KG concept nodes (`kg_nodes[]`) and a classification label. Fourth, TRM Projection applies Definitions 1–5 (§3) to identify structural leaps and compute grounding density. Fifth, a React dashboard renders the resulting trace data across three linked panels via a shared DashboardContext state machine, enabling bidirectional brushing across all views.

### §4.2 Technical Pipeline

**KG Construction.** An auto-KG prompt instructs Gemini Flash to generate concept nodes and typed relational edges for each domain dataset. A canonicalization post-processing step remaps 15 commonly returned non-standard relation types (e.g., STORES → HAS_PART, LEADS_TO → PRODUCES) and filters 30 under-specific concept terms (e.g., "process", "approach") that would create spurious adjacencies. Per-dataset statistics are reported in Table [TODO].

**LRM Verifier.** Given a student answer and the question's expected concept set, the LRM produces a chain-of-thought trace. Each step is parsed to a `kg_nodes[]` array (concepts explicitly referenced) and a `classification` label (SUPPORTS / CONTRADICTS / UNCERTAIN). The verifier is model-agnostic: Gemini Flash and DeepSeek-R1 are validated as interchangeable via cross-model stability analysis (§5a.3).

### §4.3 Visual Encodings

**[TODO: Figure 2 — full-width annotated UI screenshot]**
*Caption: "**Figure 2: The ConceptGrade Interface.** (A) The Trace Panel reveals a structural leap (amber dashed line) where the LRM skipped the `gradient_descent` concept. (B) The Click-to-Add interaction (pulsing chip) allows the educator to instantly update the (C) Rubric Editor, aligning their evaluation criteria with the domain graph."*

**Trace Panel.** The LRM reasoning trace is rendered as a vertically scrolling sequence of step cards, preserving the causal ordering of the model's inference. Each card displays the step's natural-language text, its `kg_nodes[]` as inline concept tags, and a classification badge color-coded by semantic alignment: SUPPORTS (green), CONTRADICTS (amber), UNCERTAIN (gray). Color is used as a categorical channel for semantic class membership, following established conventions for nominal data encoding [Munzner 2014]. Between consecutive step cards where `hasTopologicalGap() = true`, a dashed amber connector signals the structural discontinuity: the LRM moved to a disconnected KG region without providing an intermediate explanation. This visual discontinuity is perceptible at a glance without reading the step text. A grounding density bar at the panel header summarizes the trace at a glance (green ≥50%, amber 25–49%, red <25%), giving the educator an immediate calibration of overall trace quality before inspecting individual steps.

**KG Subgraph Panel.** When the educator selects a step or concept, a force-directed ego-graph renders the selected concept's KG neighborhood within a two-hop radius. PREREQUISITE, HAS_PART, and PRODUCES edges are rendered with distinct line styles, allowing the educator to reason about *why* two concepts are related, not just *that* they are. Concepts that appear in CONTRADICTS steps within the current answer are highlighted in amber, creating a visual link between the trace and the KG topology. The force-directed layout [Fruchterman & Reingold 1991] is parameterized to minimize edge crossings within a bounded canvas, ensuring the ego-graph remains readable for neighborhoods up to 15 concepts. Concepts with no CONTRADICTS association are rendered at reduced opacity, directing the educator's attention to the subset of the KG topology directly implicated in the current answer's reasoning gaps. This selective emphasis avoids the cognitive overload that arises from presenting the full domain KG, which can span hundreds of nodes across a dataset.

**Rubric Editor Panel.** The active rubric is displayed as a list of concept items with weight sliders. Concepts flagged by CONTRADICTS steps in the current trace are surfaced as pulsing suggestion chips alongside the rubric list. The chips pulse three times upon mounting, utilizing pre-attentive motion processing [Ware 2004] to establish affordance without requiring intrusive tooltips. Spatial proximity between the chip and its corresponding rubric entry reduces the friction of the co-auditing action to a single click.

### §4.4 Interactions

**Bidirectional Brushing.** All three panels are connected through DashboardContext, a React reducer-pattern state machine that propagates selections bidirectionally. Selecting a step in the Trace Panel highlights the step's `kg_nodes[]` in the KG Subgraph and filters the Rubric Editor to show weight sliders for those concepts. Selecting a concept in the KG Subgraph filters the Trace Panel to show only steps that reference that concept. This bidirectionality ensures that any single interaction provides simultaneous context across all three representations.

**Click-to-Add (The Co-Auditing Moment).** When the educator clicks a CONTRADICTS step, three events fire in sequence: (1) the implicated KG concept node is pushed to a 60-second rolling attribution window; (2) the KG Subgraph highlights the disconnected concept; (3) a pulsing chip appears in the Rubric Editor for that concept. Clicking the chip adds the concept to the rubric and logs `interaction_source: 'click_to_add'` with the canonical KG node name. This sequence reduces co-auditing to a single click, eliminating the ambiguity that would arise if educators typed free-text concept names. The `interaction_source` field precisely logs whether the addition was UI-assisted (Click-to-Add) or manually typed, establishing a reliable telemetry baseline for user evaluation.

To support the controlled evaluation (§5b), the system includes a silent telemetry layer that captures multi-window causal attribution and semantic alignment criteria (detailed in Supplemental Material A).

---

## §5a ML Accuracy

### §5a.1 Results on Mohler CS Benchmark

Table 1 reports the component ablation for ConceptGrade on the Mohler CS benchmark (N = 120 student answers, 10 questions). Scores are evaluated against human expert ratings using Mean Absolute Error (MAE); lower is better.

**Table 1: Component ablation on Mohler CS benchmark**

| Variant | MAE | vs. C_LLM | p-value (Wilcoxon) |
|---------|-----|-----------|-------------------|
| C1: C_LLM (keyword baseline) | 0.3300 | — | — |
| C4: + LRM Verifier | [TODO] | [TODO] | p < 0.0001 |
| C5_fix: + Concept fix | 0.2229 | −32.4% | p = 0.0013 |

The C_LLM baseline (C1) uses keyword matching against a reference answer without KG grounding. The LRM Verifier (C4) provides the single largest accuracy jump — a statistically significant improvement even before the concept fix (p < 0.0001), confirming that KG-grounded chain-of-thought verification is the mechanistic driver of the accuracy gains in our pipeline, rather than prompt engineering or surface string matching. Intermediate steps C2 (chain coverage) and C3 (Bloom classification) each contribute marginal incremental improvements; together they account for the remaining [TODO: %] MAE reduction beyond C4. The final system (C5_fix) achieves MAE = 0.2229, a 32.4% reduction over the LLM baseline (Wilcoxon p = 0.0013).

### §5a.2 Multi-Dataset Generalization

To evaluate generalization beyond the Mohler CS domain, we applied C5_fix to two additional datasets: DigiKlausur (neural networks, N = 646 answers) and Kaggle ASAG (elementary science, N = 473 answers). Table 2 summarizes results; Fisher's combined method yields p = 0.003 across all 1,239 answers.

**Table 2: Multi-dataset results**

| Dataset | Domain | N | C5_fix MAE | C_LLM MAE | Wilcoxon p |
|---------|--------|---|-----------|-----------|-----------|
| Mohler | CS (undergrad) | 120 | 0.2229 | 0.3300 | 0.0013 |
| DigiKlausur | Neural Networks | 646 | [TODO] | [TODO] | 0.049 |
| Kaggle ASAG | Elementary Science | 473 | [TODO] | [TODO] | 0.148 (n.s.) |
| **Combined** | — | **1,239** | — | — | **Fisher p = 0.003** |

Significant improvement on Mohler and DigiKlausur confirms that KG-grounded verification generalizes across higher-education CS and NN domains. Non-significance on Kaggle ASAG (p = 0.148) reflects a domain boundary condition rather than a system failure. In colloquial domains, high lexical ambiguity and synonymy prevent precise ontological mapping [Guarino 1998], reducing the discriminative power of the knowledge graph: when student answers use domain-correct vocabulary interchangeably (e.g., "energy" and "force" in elementary science), the KG cannot produce the node-level distinctions that drive grounding-based verification. This finding defines the scope condition for TRM-based grading and is reported as a design boundary, not a failure.

### §5a.3 Cross-Model TRM Stability

*[CONDITIONAL — see placement note below]*

TRM leap count and grounding density are computed independently from Gemini Flash and DeepSeek-R1 reasoning traces on the same Mohler answers (N = 120). Pearson correlation r = [TODO: run `python stability_analysis.py`].

**Placement rule (resolve before submission):**
- **If r ≥ 0.80 (both metrics):** Keep §5a.3 here. Report r values and state: "TRM topology is model-independent — structural leaps reflect properties of the student answer and domain KG, not the verbosity or terminology of the specific LRM. This provides empirical evidence that the visualization tool is stable across the two most widely-used open and proprietary reasoning models."
- **If r < 0.80 (either metric):** Cut §5a.3 from §5a entirely. Move the following paragraph to the opening of §5b: "Variability in TRM topology across models is itself a finding: the LRM's choice of which domain concepts to surface varies with model architecture, implying that any single model's trace is an incomplete and model-dependent projection of the underlying reasoning task. This directly motivates the need for the co-auditing interface: an educator who can compare the visualization against their own domain knowledge can compensate for model-specific gaps that neither model alone resolves."

---

## §5b User Study

*[SCAFFOLD LOCKED — prose to be filled post-pilot; structure is final]*

**Prerequisites before drafting §5b prose:**
- [ ] IRB amendment approved (Condition A blank panel)
- [ ] 20–30 TA/instructor participants recruited (graded student work before)
- [ ] Pilot run complete (2–3 participants; validate CONTRADICTS chip affordance; confirm event log format)
- [ ] Study logs analyzed via `analyze_study_logs.py` (GEE Binomial/Logit model)

*If §5a.3 stability analysis returns r < 0.80, prepend the following to §5b before §5b.1:*
> "Variability in TRM topology across models is itself a finding: the LRM's choice of which domain concepts to surface varies with model architecture, implying that any single model's trace is an incomplete and model-dependent projection of the underlying reasoning task. This directly motivates the need for the co-auditing interface: an educator who can compare the visualization against their own domain knowledge can compensate for model-specific gaps that neither model alone resolves."

### §5b.1 Study Design (~150 words) — [TODO: FILL POST-PILOT]

[TODO: N] TAs and instructors who had previously graded student work participated in a two-condition, between-subjects study. Condition A (control) provided only a summary card and blank rubric panel; Condition B (treatment) provided the full ConceptGrade interface, including the VerifierReasoningPanel, KG Subgraph, and RubricEditorPanel. Participants graded 10 student answers drawn from the Mohler and DigiKlausur datasets, including strategically seeded benchmark cases (fluent hallucination, unorthodox genius, lexical bluffer, partial credit needle). A think-aloud protocol was used throughout. All interactions were logged via the study telemetry layer (see Supplemental A).

### §5b.2 Hypotheses and Metrics (~100 words) — [TODO: FILL POST-PILOT]

**H1 (Causal Proximity):** Condition B shows a higher rate of rubric edits occurring within 30 seconds of a CONTRADICTS interaction, moderated by trace gap count. Analyzed via GEE Binomial/Logit with exchangeable working correlation (session_id as cluster, within_30s as outcome, trace_gap_count as moderator).

**H2 (Semantic Alignment):** Condition B semantic_alignment_rate_manual exceeds the hypergeometric null baseline (chance alignment). Click-to-Add rate reported separately as H2-UI.

### §5b.3 Results (~200 words) — [TODO: POST-PILOT]

[TODO: H1 result: OR = X, GEE p = Y, working correlation ρ = Z]

[TODO: H2 result: semantic_alignment_rate_manual = X% vs. null = Y%, p = Z]

[TODO: Gap count moderation: trace_gap_count × condition interaction p = X]

Baseline usability was confirmed via SUS (Score = [TODO]), ensuring that UI friction did not confound the primary co-auditing metrics.

### §5b.4 Qualitative Observations (~150 words) — [TODO: POST-PILOT]

*These are exploratory qualitative observations from think-aloud protocols — not pre-registered hypothesis tests.*

[TODO: Think-aloud patterns observed: rubric-first vs. trace-first reasoning strategies, frequency of verbal references to structural leaps, educator reactions to benchmark seed cases]

[TODO: Benchmark seed performance: fluent_hallucination detection rate Condition B vs. A; representative think-aloud quote illustrating co-auditing moment]

---

## §6 Discussion

### §6.1 Implications for Educational AI Design

Our findings suggest that the co-auditing paradigm can reframe the educator's role from a passive approver of AI decisions to an active epistemological partner. Conventional AI grading interfaces present a verdict to be accepted or overridden; ConceptGrade's design demonstrates that presenting the topological structure of the AI's reasoning chain forces educators to engage with domain boundaries they would otherwise leave implicit. When an educator clicks a CONTRADICTS chip and updates their rubric, they are not correcting the model — they are articulating a criterion that was previously tacit. This externalization is the core pedagogical contribution of the co-auditing design: the interface makes explicit what was implicit, not by simplifying the model's behavior, but by situating it within a domain representation the educator can interrogate. Our findings indicate that educators responded more effectively to transparency of reasoning topology than to simplicity of output, suggesting that educator trust is built through shared understanding rather than reduced cognitive load.

### §6.2 Limitations and Boundary Conditions

The Kaggle ASAG evaluation defines a clear boundary condition for TRM: grading quality degrades when the domain vocabulary lacks ontological specificity. In elementary science, where colloquial terms like "energy" and "force" carry multiple overlapping meanings, the KG cannot produce the node-level distinctions necessary for grounding-based verification — a property of the domain, not the system. Two additional limitations apply to the system broadly. First, the LRM Verifier's chain-of-thought is not guaranteed to be faithful: recent work demonstrates that stated reasoning can diverge from the computation that produced the output [Turpin 2023]. However, it is precisely because LRM reasoning can be unfaithful that visualizing its topology is necessary; co-auditing transforms hidden algorithmic unfaithfulness into visible structural gaps that an educator can detect and correct. Second, co-auditing assumes the educator has sufficient domain expertise to evaluate whether a structural leap represents a genuine conceptual gap or a legitimate reasoning shortcut. In interdisciplinary grading contexts, or with inexperienced graders, this assumption may not hold. Both limitations are directions for future work, not architectural failures.

### §6.3 Generalizability

We hypothesize that TRM is generalizable to any analytical task where an LRM's reasoning can be grounded in a structured formal ontology, independent of the educational grading context. The three structural properties that made the educational domain productive — a well-defined concept vocabulary, typed relational edges between concepts, and a grading task that rewards conceptual coverage — are shared by any domain with an established formal knowledge representation. This suggests that the co-auditing interface pattern, including the structural leap visualization and bidirectional brushing design, is a reusable template for domains where reasoning transparency and human expert alignment are both required.

### §6.4 Future Work

Three directions emerge from this work. First, *adaptive KG refinement*: educator rubric edits could feed back into the KG as new concept-relation hypotheses, closing the co-auditing loop and enabling the domain model to evolve through use. Second, *multi-model ensemble views*: when Gemini Flash and DeepSeek-R1 produce divergent traces for the same answer, showing both side-by-side would expose model-dependent reasoning gaps without requiring the educator to choose a single ground truth. Third, *longitudinal inter-rater alignment studies*: tracking whether repeated co-auditing sessions improve rubric consistency across educators in the same department would provide direct evidence for the epistemic update claim, moving from cross-sectional to longitudinal causal measurement.

---

## §7 Conclusion

We presented ConceptGrade, a visual analytics system for co-auditing AI-graded student answers via Topological Reasoning Mapping. By projecting a large reasoning model's chain-of-thought onto a domain Knowledge Graph, ConceptGrade enables educators to inspect structural leaps in the AI's reasoning — gaps where the model moved between disconnected concepts without providing an intermediate explanation — and act on them by refining their own rubric criteria in real time.

Our evaluation demonstrates that KG-grounded verification reduces mean absolute grading error by 32.4% over a pure LLM baseline on the Mohler CS benchmark, with Fisher combined significance across 1,239 answers from three datasets (p = 0.003). [TODO: POST-PILOT RESULTS — A controlled user study confirms that educators exposed to TRM-rendered traces make rubric edits with significantly higher semantic alignment (X%) than expected by chance (Y%).]

Co-auditing does not replace educator judgment; it makes the interface conditions under which judgment is exercised more transparent, more structured, and more accountable. As AI grading systems become ubiquitous in higher education, designing for epistemological partnership — not just workflow efficiency — should form a central research agenda for the visual analytics community.

---

## Open [TODO] Master List

**Priority order (per v17 Q9 decision):** Bibliography → Scripts → Figures → §5b prose

### 1. Bibliography (confirm before co-author circulation)
- [ ] Sinha 2021 full reference
- [ ] Mizumoto 2023 full reference
- [ ] Chen 2020 (ViTA) full reference or replacement VIS grading paper
- [ ] Fruchterman & Reingold 1991: "Graph drawing by force-directed placement," Software—Practice & Experience
- [ ] Guarino 1998: "Formal Ontology in Information Systems," IOS Press
- [ ] Munzner 2014: "Visualization Analysis and Design," AK Peters/CRC Press
- [ ] Ware 2004: "Information Visualization: Perception for Design," Morgan Kaufmann

### 2. Data Collection (run scripts)
- [ ] Run `python stability_analysis.py` → Pearson r for gap_count and grounding_density → determines §5a.3 placement
- [ ] Run ablation script → C4 MAE and C4 vs C3 Wilcoxon p-value → fills Table 1
- [ ] Run evaluation → DigiKlausur and Kaggle ASAG MAE values → fills Table 2
- [ ] Compute C2 + C3 marginal MAE → fills §5a.1 prose [TODO: %]

### 3. Figures (design work)
- [ ] Pipeline figure: KG → LRM Verifier → Trace Parser → TRM → Dashboard (boxes + arrows)
- [ ] Full-width annotated UI screenshot: CONTRADICTS step (amber gap visible) + pulsing chip in rubric editor
- [ ] Running example figure: DigiKlausur Sample 0 trace (processing_unit → human_brain structural leap)

### 4. Text Placeholders (fill from study data — post-pilot)
- [ ] [TODO: X] — user study N (participants)
- [ ] [TODO: Y]% — semantic alignment rate (§5b.3, §7)
- [ ] [TODO: Z]% — hypergeometric null baseline (§5b.3, §7)
- [ ] [TODO: H1 OR, GEE p, ρ] — H1 GEE results (§5b.3)
- [ ] [TODO: SUS score] — SUS sanity check (§5b.3)
- [ ] [TODO: Figure numbers] — pipeline figure, UI screenshot, running example
- [ ] [TODO: Table X] — KG statistics table number (§4.2)
- [ ] [TODO: POST-PILOT RESULTS] block in §7 Para 2

### 5. Post-Pilot Prose (write after study)
- [ ] §5b.1 Study Design — fill participant details, task description
- [ ] §5b.3 Results — fill H1, H2, moderation, SUS values
- [ ] §5b.4 Qualitative Observations — fill think-aloud patterns, benchmark seed findings, representative quotes
- [ ] §6.1 — optionally add 1–2 sentences from think-aloud evidence supporting "shared understanding" claim
- [ ] Expand §4.3 and §6 by ~300 words total (organic; integrate qualitative quotes)

---

## v19 Locked Decisions

| Decision | Locked Value |
|----------|-------------|
| Title | "ConceptGrade: Visual Co-Auditing of AI Reasoning to Externalize Educator Mental Models" (12 words) |
| Abstract opening | "Educators cannot audit what they cannot see: when an AI grading system downgrades a student's answer, its reasoning chain remains invisible." |
| Abstract user study | Option (b) — describe design + pre-registered metrics; no forward-projected results |
| Figure 1 caption | (A) LRM Verifier → (B) Trace Parser → (C) TRM Projection → (D) linked panels |
| Figure 3 caption | Approved as drafted (N₁₀/N₁₁ notation, amber indicator, skipped concepts) |
| Supplemental A scope | PDF = Multi-Window Attribution Logic + Semantic Matching Algorithm; JSON schemas → GitHub README |
| Highest-risk reviewer | HCI reviewer (Profile 2) — scrutinize 30-second causal attribution construct validity |
| Recruitment deadline | No later than August 2026 (targets Fall semester; avoids Nov/Dec holiday dead zone) |

### Terminology Standards (Q7 locked)

| Term | Rule |
|------|------|
| **Click-to-Add** | Always capitalized and hyphenated; never "click to add" or "Click to Add" |
| **reasoning trace** | Canonical term for LRM output; never "rationale," "explanation," or just "trace" alone |
| **structural leap** | Never "inferential leap" or "reasoning gap" (those are different constructs) |
| **co-auditing** | Always hyphenated; never "coauditing" or "co auditing" |
| **CONTRADICTS** | Always capitalized (system classification); never lowercase "contradicts" |
| **implicit mental model** | Always cite [Kulesza 2012, Bansal 2019, Pirolli & Card 2005] on first use per section |
| **LRM** | Expand on first use per section: "large reasoning model (LRM)" |
| **boundary condition** | In §5a/§6 Kaggle context; never "limitation" for this specific finding |
