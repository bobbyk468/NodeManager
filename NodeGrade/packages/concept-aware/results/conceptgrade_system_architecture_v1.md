# ConceptGrade — §4 System Architecture (v1)
**Date:** 2026-04-17  
**Context:** IEEE VIS 2027 VAST — writing phase  
**Decisions applied:** Gemini v15 Q5–Q7 locked  
**Word targets:** §4.2 = ~120 words, §4.3 = ~330 words, §4.4 = ~200 words

---

## Changes Applied from Gemini v15 Q5–Q7

| # | Decision | Applied |
|---|----------|---------|
| Q5 | §4.2 ~120 words (compressed backend), §4.3 ~330 words (expanded encodings) | ✅ Word targets set |
| Q6 | [Munzner 2014] for color encoding; [Ware 2004] for pulsing chip; others in-text or convention | ✅ Citations placed |
| Q7 | Move §4.5 telemetry detail to Supplemental A; add one-sentence pointer at end of §4.4 | ✅ Applied |

---

## §4 System Architecture

### §4.1 Pipeline Overview (~150 words)

To operationalize the TRM framework (§3), ConceptGrade is designed as a full-stack visual analytics system that transforms a student answer into an interactive, co-auditable reasoning trace. The pipeline proceeds in five stages, illustrated in Figure [TODO: pipeline figure]. First, a per-domain Knowledge Graph (KG) is constructed from question-answer pairs using an auto-KG prompting approach that generates concept nodes and typed relational edges. Second, an LRM Verifier (Gemini Flash or DeepSeek-R1) produces a 20–40 step chain-of-thought trace for each student answer, classifying each step as SUPPORTS, CONTRADICTS, or UNCERTAIN with respect to the domain KG. Third, a Trace Parser structures the raw LRM output into `ParsedStep` objects, each carrying a list of KG concept nodes (`kg_nodes[]`) and a classification label. Fourth, TRM Projection applies Definitions 1–5 (§3) to identify structural leaps and compute grounding density. Fifth, a React dashboard renders the resulting trace data across three linked panels via a shared DashboardContext state machine, enabling bidirectional brushing across all views.

---

### §4.2 Technical Pipeline (~120 words)

**KG Construction.** An auto-KG prompt instructs Gemini Flash to generate concept nodes and typed relational edges for each domain dataset. A canonicalization post-processing step remaps 15 commonly returned non-standard relation types (e.g., STORES → HAS_PART, LEADS_TO → PRODUCES) and filters 30 under-specific concept terms (e.g., "process", "approach") that would create spurious adjacencies. Per-dataset statistics are reported in Table [TODO].

**LRM Verifier.** Given a student answer and the question's expected concept set, the LRM produces a chain-of-thought trace. Each step is parsed to a `kg_nodes[]` array (concepts explicitly referenced) and a `classification` label (SUPPORTS / CONTRADICTS / UNCERTAIN). The verifier is model-agnostic: Gemini Flash and DeepSeek-R1 are validated as interchangeable via cross-model stability analysis (§5a.3).

---

### §4.3 Visual Encodings (~330 words)

**[TODO: Figure X — full-width annotated UI screenshot]**
*Caption: "**Figure X: The ConceptGrade Interface.** (A) The Trace Panel reveals a structural leap (amber dashed line) where the LRM skipped the `gradient_descent` concept. (B) The Click-to-Add interaction (pulsing chip) allows the educator to instantly update the (C) Rubric Editor, aligning their evaluation criteria with the domain graph."*

**Trace Panel.** The LRM reasoning trace is rendered as a vertically scrolling sequence of step cards, preserving the causal ordering of the model's inference. Each card displays the step's natural-language text, its `kg_nodes[]` as inline concept tags, and a classification badge color-coded by semantic alignment: SUPPORTS (green), CONTRADICTS (amber), UNCERTAIN (gray). Color is used as a categorical channel for semantic class membership, following established conventions for nominal data encoding [Munzner 2014]. Between consecutive step cards where `hasTopologicalGap() = true`, a dashed amber connector signals the structural discontinuity: the LRM moved to a disconnected KG region without providing an intermediate explanation. This visual discontinuity is perceptible at a glance without reading the step text. A grounding density bar at the panel header summarizes the trace at a glance (green ≥50%, amber 25–49%, red <25%), giving the educator an immediate calibration of overall trace quality before inspecting individual steps.

**KG Subgraph Panel.** When the educator selects a step or concept, a force-directed ego-graph renders the selected concept's KG neighborhood within a two-hop radius. PREREQUISITE, HAS_PART, and PRODUCES edges are rendered with distinct line styles, allowing the educator to reason about *why* two concepts are related, not just *that* they are. Concepts that appear in CONTRADICTS steps within the current answer are highlighted in amber, creating a visual link between the trace and the KG topology. The force-directed layout [Fruchterman & Reingold 1991] is parameterized to minimize edge crossings within a bounded canvas, ensuring the ego-graph remains readable for neighborhoods up to 15 concepts. Concepts with no CONTRADICTS association are rendered at reduced opacity, directing the educator's attention to the subset of the KG topology directly implicated in the current answer's reasoning gaps. This selective emphasis avoids the cognitive overload that arises from presenting the full domain KG, which can span hundreds of nodes across a dataset.

**Rubric Editor Panel.** The active rubric is displayed as a list of concept items with weight sliders. Concepts flagged by CONTRADICTS steps in the current trace are surfaced as pulsing suggestion chips alongside the rubric list. The chips pulse three times upon mounting, utilizing pre-attentive motion processing [Ware 2004] to establish affordance without requiring intrusive tooltips. Spatial proximity between the chip and its corresponding rubric entry reduces the friction of the co-auditing action to a single click.

---

### §4.4 Interactions (~200 words)

**Bidirectional Brushing.** All three panels are connected through DashboardContext, a React reducer-pattern state machine that propagates selections bidirectionally. Selecting a step in the Trace Panel highlights the step's `kg_nodes[]` in the KG Subgraph and filters the Rubric Editor to show weight sliders for those concepts. Selecting a concept in the KG Subgraph filters the Trace Panel to show only steps that reference that concept. This bidirectionality ensures that any single interaction provides simultaneous context across all three representations.

**Click-to-Add (The Co-Auditing Moment).** When the educator clicks a CONTRADICTS step, three events fire in sequence: (1) the implicated KG concept node is pushed to a 60-second rolling attribution window; (2) the KG Subgraph highlights the disconnected concept; (3) a pulsing chip appears in the Rubric Editor for that concept. Clicking the chip adds the concept to the rubric and logs `interaction_source: 'click_to_add'` with the canonical KG node name. This sequence reduces co-auditing to a single click, eliminating the ambiguity that would arise if educators typed free-text concept names. The `interaction_source` field precisely logs whether the addition was UI-assisted (Click-to-Add) or manually typed, establishing a reliable telemetry baseline for user evaluation.

To support the controlled evaluation (§5b), the system includes a silent telemetry layer that captures multi-window causal attribution and semantic alignment criteria (detailed in Supplemental Material A).

---

## Open [TODO] Items

- [ ] Insert pipeline figure at §4.1 (boxes: KG → LRM Verifier → Trace Parser → TRM → Dashboard)
- [ ] Insert full-width annotated UI screenshot at §4.3 (CONTRADICTS step, amber gap, pulsing chip)
- [ ] Fill Table [TODO] in §4.2 with per-dataset KG statistics (#concepts, #edges, density)
- [ ] Confirm [Munzner 2014] full reference: "Visualization Analysis and Design" (AK Peters, 2014)
- [ ] Confirm [Ware 2004] full reference: "Information Visualization: Perception for Design" (Morgan Kaufmann, 2004)
