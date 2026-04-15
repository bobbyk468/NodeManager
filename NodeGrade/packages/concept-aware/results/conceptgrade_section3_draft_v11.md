# ConceptGrade — Section 3.1 Draft Review v11

**Date:** 2026-04-14  
**Context:** IEEE VIS 2027 VAST — writing phase  
**Prior reviews:** v1–v10 (ablation → TRM formalization)  
**This review:** (1) Node-only adjacency implemented; (2) Grounding Density wired end-to-end; (3) Section 3.1 Formal Definition box + Pedagogical Interpretation drafted

---

## 1. What Was Implemented Since v10

### 1.1 Node-Only Adjacency (v10 decision, now live)

`hasTopologicalGap` in `VerifierReasoningPanel.tsx` now uses node-only adjacency:

```typescript
function hasTopologicalGap(stepA: ParsedStep, stepB: ParsedStep): boolean {
  if (stepA.kg_nodes.length === 0 || stepB.kg_nodes.length === 0) return false;
  const nodesA = new Set(stepA.kg_nodes);
  return !stepB.kg_nodes.some(n => nodesA.has(n));  // gap iff no shared concept node
}
```

Edge-type overlap is no longer a continuity criterion. This matches Definition 2 below and is simpler to defend formally.

### 1.2 Grounding Density — Wired End-to-End

**Definition** (implemented): `grounding_density = |{i : Nᵢ ≠ ∅}| / n`

Wired through:
- `VerifierReasoningPanel.tsx`: computed via `useMemo`, published to `DashboardContext.lastGroundingDensity` via `setGroundingDensity()`
- `SummaryBar`: shows `"{X}% grounded"` in green (≥50%), amber (25–49%), or red (<25%)
- `DashboardContext`: `lastGroundingDensity: number`, `SET_GROUNDING_DENSITY` action
- `studyLogger.ts`: `grounding_density: number` in `RubricEditPayload`
- `RubricEditorPanel.tsx`: reads `lastGroundingDensity`, includes in `handleEdit` payload
- `analyze_study_logs.py`: `mean_grounding_density` per session; `mean_grounding_density_mean` in aggregate; shown in Rubric Edit Metrics table

---

## 2. Section 3.1 — Formal Definition Box (Draft)

*For the IEEE VIS VAST paper. Target: one clearly delimited box, ~0.4 column-pages. Surrounding prose explains each definition in plain English — only the box uses mathematical notation.*

---

> **Definition Box: Topological Reasoning Mapping (TRM)**
>
> Let **G = (V, E)** be a domain Knowledge Graph where **V** is a set of concept nodes and **E ⊆ V × R × V** is a set of typed edges with relation types **R** (e.g., `PREREQUISITE_FOR`, `HAS_PART`, `PRODUCES`).
>
> Let **R = ⟨s₁, …, sₙ⟩** be a large reasoning model's chain-of-thought for a student answer, where each step **sᵢ** is a natural-language proposition.
>
> ---
>
> **Definition 1 — TRM Step Mapping.** A Topological Reasoning Map is a function
> $$\phi(s_i) = (N_i,\; c_i)$$
> that assigns to each step **sᵢ**:
> - **Nᵢ ⊆ V** — the set of KG concept nodes referenced in sᵢ
> - **cᵢ ∈ {SUPPORTS, CONTRADICTS, UNCERTAIN}** — the classification of sᵢ's propositional content with respect to the structural neighborhood of Nᵢ in G
>
> ---
>
> **Definition 2 — Topological Adjacency.** Two consecutive steps sᵢ, sᵢ₊₁ are *topologically adjacent* if their KG projections share at least one concept node:
> $$N_i \cap N_{i+1} \neq \emptyset$$
>
> ---
>
> **Definition 3 — Structural Leap.** A pair (sᵢ, sᵢ₊₁) constitutes a *structural leap* if both steps are grounded (Nᵢ ≠ ∅ and Nᵢ₊₁ ≠ ∅) and they are not topologically adjacent:
> $$N_i \cap N_{i+1} = \emptyset$$
>
> ---
>
> **Definition 4 — Leap Count.** The *leap count* of a reasoning chain R under map φ is the number of structural leaps between consecutive grounded steps:
> $$\text{leaps}(R, \phi) = \left|\{i : N_i \neq \emptyset,\; N_{i+1} \neq \emptyset,\; N_i \cap N_{i+1} = \emptyset\}\right|$$
>
> ---
>
> **Definition 5 — Grounding Density.** The *grounding density* of R under φ is the fraction of steps anchored to at least one KG concept:
> $$\text{density}(R, \phi) = \frac{|\{i : N_i \neq \emptyset\}|}{n}$$
>
> A trace with density(R, φ) = 1 is *fully grounded* — every step names at least one domain concept. A trace with low density relies on natural-language reasoning not anchored to the domain model.

---

**Plain-English gloss** (surrounding prose, not in the box):

- *Step Mapping* (Def 1): For each sentence the AI writes while reasoning, we identify which KG concepts it mentions and whether the claim it makes about those concepts is supported, contradicted, or uncertain given the domain model.
- *Topological Adjacency* (Def 2): Two consecutive reasoning steps are "connected" if they reference at least one concept in common — the AI stayed in the same conceptual neighborhood.
- *Structural Leap* (Def 3): When the AI jumps from one concept cluster to a completely unrelated one without naming any bridging concept, it has made a structural leap — the reasoning chain has a gap.
- *Leap Count* (Def 4): The integer count of structural leaps in a trace. Zero means fully continuous reasoning; higher values mean more unexplained jumps.
- *Grounding Density* (Def 5): How much of the AI's reasoning is actually anchored to domain knowledge. Low density means the AI reasoned in general language without naming the specific concepts the educator cares about.

---

## 3. Section 3.2 — Pedagogical Interpretation (Draft)

*Target: ~0.3 column-pages. No mathematical notation. Bridges the formal TRM definitions to the educator's experience. Essential for VIS reviewers who expect a Human-Centered rationale for the visualization design.*

---

**3.2 Why Structural Leaps Matter to Educators**

The formal properties of TRM — grounding density and structural leaps — are not abstractions: they correspond directly to the interpretive challenges educators face when evaluating AI-generated grading rationale.

**Grounding density as epistemic confidence.** When a grading model explains its decision using general reasoning ("the student's answer is incomplete"), an educator cannot verify whether the AI applied the rubric or relied on surface-level language patterns. High grounding density — a trace where the AI explicitly names the domain concepts it evaluated — transforms an opaque verdict into a verifiable audit trail. In ConceptGrade, steps with high Nᵢ are rendered with concept node pills that the educator can click to inspect the KG subgraph, turning a read-only explanation into a navigable domain map.

**Structural leaps as pedagogical red flags.** A structural leap (Definition 3) signals that the AI jumped between two disconnected knowledge regions without providing the bridging reasoning an educator would consider essential. Consider a student answer that mentions "backpropagation" and "learning rate" — two concepts separated by the chain `backpropagation → gradient_descent → weight_update → learning_rate` in the Neural Networks KG. If the AI's reasoning trace references `backpropagation` in step 3 and `learning_rate` in step 4 without any intervening concept, it has made a structural leap: it implicitly assumed the connection rather than explaining it. An educator who relies on this explanation to justify a grade cannot reconstruct the reasoning for a student who disputes the score.

**The co-auditing loop.** TRM makes these properties *visible* rather than merely *detectable*. The amber "structural leap" indicator between steps invites the educator to ask: "What concept should have appeared here?" This question is precisely the rubric-editing moment ConceptGrade is designed to capture. When an educator clicks the CONTRADICTS chip for `gradient_descent` (which appeared in the trace but was jumped over), they are not just correcting the AI's output — they are making their own pedagogical model explicit. This bidirectional update — AI trace forces human to articulate tacit knowledge — is the mechanism behind the co-auditing claim.

---

## 4. Open Questions for This Review

### Q1 — Definition 1: Should cᵢ be in the box, or just Nᵢ?

The current Definition 1 includes both **Nᵢ** (node mapping) and **cᵢ** (classification). But the classification is operationally defined by the LRM verifier's prompt, not by G itself — it's a learned/prompted judgment, not a formal derivation from the graph structure.

**The tension**: Including cᵢ in the formal definition box implies it has formal semantics (provable correctness), when in practice it is a probabilistic LRM output. Excluding cᵢ from the box and describing it only in prose would be more formally honest.

**Options:**
- (a) Keep cᵢ in the box with a footnote: "cᵢ is computed by the LRM verifier (Section 4.1); its correctness is evaluated empirically in Section 5a."
- (b) Remove cᵢ from Definition 1 — define only the node mapping φ(sᵢ) = Nᵢ — and introduce cᵢ in the Implementation section as an LRM output.
- (c) Keep cᵢ but add formal semantics: SUPPORTS iff the propositional content of sᵢ is consistent with every edge incident to nodes in Nᵢ; CONTRADICTS iff it is inconsistent with at least one such edge.

**Question:** Which option is most defensible to a VIS Theory reviewer?

---

### Q2 — Definition 5 (Grounding Density): Primary or Secondary Metric?

Grounding Density was introduced as a Stability Analysis metric (Section 5a) for comparing Gemini Flash vs. DeepSeek-R1. But should it also appear in Section 5b (User Study) as a moderator?

**Hypothesis**: educators who viewed traces with higher grounding density may engage more with the CONTRADICTS chips (more concepts to click) and thus show higher semantic alignment rates (H2). If true, grounding density is a moderator for H2, not just a stability metric.

**Pre-registration question**: Should we add grounding density as a second GEE moderator in `analyze_study_logs.py`? The current GEE model only includes `trace_gap_count`. Adding `grounding_density` would be:

```python
'within_30s ~ condition * trace_gap_count + condition * grounding_density'
```

Or should the two moderators be analyzed in separate models to avoid collinearity (gap count and grounding density may be correlated — low density → fewer grounded step pairs → fewer detectable gaps)?

---

### Q3 — Section 3.1 Length and the "Glossy" Risk

Five definitions + a theorem-style statement is dense for VAST. The risk: reviewers who are primarily HCI/VIS practitioners may skim the formal box and fail to connect it to the UI behavior.

**Mitigation options already in the draft:**
- Plain-English gloss paragraph after the box (Section 2, above)
- Section 3.2 (Pedagogical Interpretation) bridges to the educator experience
- Cross-reference to the TypeScript implementation in Section 4

**Question:** Should the paper include a **running example** immediately after the definition box — e.g., "Figure 2a shows a five-step trace for a student answer about backpropagation. Step 3 references `gradient_descent` and step 4 references `learning_rate`. Since these nodes are disjoint in the KG, Definition 3 classifies this as a structural leap (amber indicator)."? A concrete trace walkthrough would ground the abstract definitions.

---

### Q4 — Pedagogical Interpretation: Tone and Target Audience

The Section 3.2 draft (above) is written for a mixed VIS+HCI audience. The phrase "bidirectional update — AI trace forces human to articulate tacit knowledge" is the key argument for the co-auditing claim.

**Questions:**
- Is "tacit knowledge" the right term (Polanyi 1966), or should we use "implicit mental model" to be more accessible to VIS readers?
- The backpropagation → learning_rate example: should this be in Section 3.2 (motivation) or saved for the paper figure caption (where we show the actual trace from Sample 0)?
- Does "oracle to be trusted or ignored... collaborator to be audited" (from the Introduction) need to be echoed here, or does the Introduction + Section 3.2 avoid repetition?

---

### Q5 — Writing Order: After Section 3.1, What Next?

With Section 3.1 (Formal Definition box) and Section 3.2 (Pedagogical Interpretation) now drafted, the writing roadmap is:

| Next | Section | Content | Data needed |
|------|---------|---------|-------------|
| 1 | §1 (Intro) | Full 1,000-word draft using v8 first paragraph + contributions | None |
| 2 | §5a (ML Accuracy) | Table 1 (Mohler, DigiKlausur, Kaggle) + narrative | Data final |
| 3 | §3.3 (System Architecture) | 5-stage pipeline diagram + prose | None |
| 4 | §2 (Related Work) | XAI for NLP, IMT, Educational Dashboards | Literature |
| 5 | §5b (User Study) | Method skeleton now; fill results post-pilot | Post-pilot |

**Question:** Should §3.3 (System Architecture) be written before or after §5a (ML Accuracy)? Writing accuracy results first helps confirm which pipeline stages drove the improvement, making the architecture narrative more purposeful.
