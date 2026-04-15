# ConceptGrade — TRM Formalization & Section 3.1 Review v10

**Date:** 2026-04-14  
**Context:** IEEE VIS 2027 VAST — pre-pilot, writing phase starting  
**Prior reviews:** v1–v9 (ablation → contributions locked)  
**This review:** (1) ρ added to GEE output; (2) v9 decisions locked; (3) Section 3.1 TRM formal definition drafted for feedback; (4) 5 open questions on formalization

---

## 1. What Was Completed Since v9

### 1.1 GEE Working Correlation ρ Added

`analyze_study_logs.py` now extracts and reports the exchangeable working correlation ρ:

```python
rho = float(model.cov_struct.dep_params)  # statsmodels GEE Exchangeable
```

**Report in paper** as: "Working correlation ρ = [value] (Exchangeable structure)". If |ρ| > 0.20, this justifies why GEE is needed over a standard GLM — edits within the same participant are meaningfully correlated (likely because participants have consistent rubric-editing tendencies independent of trace content).

**Print output** (study report): `ρ={rho:.3f}` shown alongside N edits and N sessions, with note "ρ justifies GEE over GLM — report in Methods."

---

## 2. Section 3.1 — TRM Formal Definition (Draft for Review)

This is the core scientific contribution. It must be precise enough to satisfy VIS Theory & Model reviewers while remaining accessible to practitioners.

---

### 2.1 Preliminaries

Let **G = (V, E, L)** be a domain Knowledge Graph where:
- **V** is a finite set of concept nodes (e.g., `gradient_descent`, `synaptic_weights`)
- **E ⊆ V × R × V** is a set of typed edges, where **R** is a finite set of relation types (`PREREQUISITE_FOR`, `HAS_PART`, `PRODUCES`, `IMPLEMENTS`, `RESEMBLES`, `VARIANT_OF`, `CONTRASTS_WITH`, `OPERATES_ON`)
- **L: V → Σ*** assigns a natural-language label to each node

Let **R = ⟨s₁, s₂, …, sₙ⟩** be a large reasoning model's (LRM) linear chain-of-thought for a given student answer, where each step **sᵢ** is a natural-language proposition.

---

### 2.2 TRM Step Mapping (Classification)

**Definition 1 — TRM Step Mapping.** A *Topological Reasoning Map* is a function:

$$\phi: \{s_1, \ldots, s_n\} \rightarrow \mathcal{P}(V) \times \mathcal{P}(R) \times \{\text{SUPPORTS, CONTRADICTS, UNCERTAIN}\}$$

that assigns to each step sᵢ:
- **Nᵢ ⊆ V** — the set of KG concept nodes referenced in sᵢ's propositional content
- **Eᵢ ⊆ R** — the set of KG relation types invoked in sᵢ's reasoning
- **cᵢ ∈ {SUPPORTS, CONTRADICTS, UNCERTAIN}** — the classification of sᵢ's propositional content with respect to the structural neighborhood of Nᵢ in G

**Classification semantics:**
- **SUPPORTS**: sᵢ asserts a claim consistent with the domain model — the relationship it claims between concepts in Nᵢ is present in G
- **CONTRADICTS**: sᵢ asserts a claim inconsistent with the domain model — a relationship it claims is absent from G, or a concept it references is not in V
- **UNCERTAIN**: the mapping cannot be verified against G with sufficient confidence (e.g., Nᵢ = ∅, or the propositional content is ambiguous)

*Note for implementation:* The mapping φ is computed by the LRM Verifier (Stage 3a). The LRM is prompted with the domain KG G and the student answer; its structured output for each step includes `kg_nodes`, `kg_edges`, and `classification`.

---

### 2.3 Topological Continuity (TRM Gap Detection)

**Definition 2 — Topological Adjacency.** Two consecutive steps sᵢ, sᵢ₊₁ are *topologically adjacent* if their KG projections share at least one node or one relation type:

$$(N_i \cap N_{i+1} \neq \emptyset) \lor (E_i \cap E_{i+1} \neq \emptyset)$$

**Definition 3 — Topological Gap.** A pair (sᵢ, sᵢ₊₁) constitutes a *topological gap* if and only if:
1. Both steps have non-empty KG projections: **Nᵢ ≠ ∅** and **Nᵢ₊₁ ≠ ∅**
2. The steps are *not* topologically adjacent: **Nᵢ ∩ Nᵢ₊₁ = ∅** and **Eᵢ ∩ Eᵢ₊₁ = ∅**

A topological gap indicates a *structural leap* in the LRM's reasoning — the model jumped to a disconnected region of the Knowledge Graph without an explicit connecting path.

**Definition 4 — Trace Gap Count.** The *gap count* of a reasoning chain R under map φ is:

$$\text{gap}(R, \phi) = \left|\{i \in \{1,\ldots,n-1\} : (s_i, s_{i+1}) \text{ is a topological gap}\}\right|$$

---

### 2.4 TRM Formal Statement

**Theorem (TRM Topological Continuity Property).** For a reasoning chain R and domain KG G:

- If gap(R, φ) = 0, the chain is *topologically continuous* — every consecutive step pair shares at least one KG node or relation type, and the LRM's reasoning traverses a connected subgraph of G.
- If gap(R, φ) > 0, the chain contains *structural leaps* — the LRM's reasoning at those positions cannot be traced to an explicit path in the domain Knowledge Graph.

*Pedagogical interpretation for co-auditing:* A topological gap does not necessarily indicate a factual error (the two disconnected KG regions may both be correct). It indicates an *incomplete explanation* — the LRM skipped an intermediate concept that a domain expert would consider essential to the reasoning chain. This is precisely what educators can identify and flag via the co-auditing interface.

---

### 2.5 Implementation Notes (for Section 4 cross-reference)

The TypeScript implementation in `VerifierReasoningPanel.tsx`:

```typescript
function hasTopologicalGap(stepA: ParsedStep, stepB: ParsedStep): boolean {
  if (stepA.kg_nodes.length === 0 || stepB.kg_nodes.length === 0) return false;
  const nodesA = new Set(stepA.kg_nodes);
  if (stepB.kg_nodes.some(n => nodesA.has(n))) return false;   // shared node → adjacent
  const edgesA = new Set(stepA.kg_edges);
  if (stepB.kg_edges.some(e => edgesA.has(e))) return false;   // shared edge → adjacent
  return true;  // Definition 3: both disjoint → gap
}
```

This directly implements Definition 3 above. The gap count is computed via `useMemo` on `parsedSteps` and published to `DashboardContext.lastTraceGapCount` for logging.

---

## 3. Open Questions for This Review

### Q1 — Definition 2 (Topological Adjacency): Node OR Edge — Is This Correct?

The current definition says two steps are adjacent if they share *either* a node *or* a relation type. The "edge type" condition (Eᵢ ∩ Eᵢ₊₁ ≠ ∅) is a weaker condition: two steps could share a relation type (e.g., both invoke `HAS_PART`) without sharing any concept node.

**The tension**: Is edge-type sharing sufficient evidence of topological continuity? If step 3 says "processing_unit HAS_PART neuron" and step 4 says "attention_head HAS_PART query_vector", they share the edge type `HAS_PART` but refer to completely different KG subgraphs.

**Options:**
- (a) Keep current definition (node OR edge type) — matches the implementation; more liberal; fewer false-positive gaps
- (b) Tighten to node-only adjacency — simpler, easier to defend formally; would produce more gaps in practice
- (c) Add a third condition: shared node OR (shared edge type AND node distance ≤ 2 in G) — captures "same neighborhood" rather than "same relation pattern"

**Recommendation requested**: For a VIS audience, is option (b) [node-only] simpler and more defensible, or does the edge-type condition add meaningful value?

---

### Q2 — The "N ≠ ∅" Precondition in Definition 3

Gap detection only fires when *both* steps have non-empty KG projections (Nᵢ ≠ ∅ and Nᵢ₊₁ ≠ ∅). In the DigiKlausur DeepSeek-R1 traces, 293/300 traces have empty `kg_nodes` for most steps — so gap detection effectively only applies to ~7 traces.

**The gap in our gap detection**: If a step has no KG nodes (because the LRM's chain-of-thought didn't name specific concepts), we can't detect a structural leap even if one occurred. This is a parser limitation, not a TRM limitation.

**For the paper**: Should Definition 3 include a note clarifying that the precondition "Nᵢ ≠ ∅" means gap detection is *best-effort* and depends on the LRM's tendency to name KG concepts explicitly? This would need to appear in the Limitations section.

**Question:** Is this limitation fatal for the TRM contribution claim, or is it simply a parser quality issue that Gemini Flash structured output resolves?

---

### Q3 — Topological Continuity as a "Property" vs. "Metric"

Section 2.4 frames gap(R, φ) as an integer count. But for the paper's claim about co-auditing effectiveness, we may want a normalized metric:

$$\text{continuity}(R, \phi) = 1 - \frac{\text{gap}(R, \phi)}{n - 1}$$

where n is the total number of steps with non-empty KG projections. This produces a [0,1] value where 1.0 = fully continuous chain.

**Advantages of normalized metric:**
- Comparable across traces of different lengths
- Can be correlated with educator engagement (Pearson r) rather than requiring regression
- Cleaner for the Stability Analysis subsection in Section 5a (compare Gemini Flash vs. DeepSeek-R1 continuity scores)

**Disadvantage:** Adding the normalized metric means the paper has two measures (gap count and continuity score), potentially confusing readers.

**Question:** Should the paper define *both* gap(R, φ) and continuity(R, φ), or report only the count? If both, which is primary?

---

### Q4 — "Structural Leap vs. Hallucination" in the Definition

Section 2.4 says a topological gap "indicates an incomplete explanation" but not necessarily a "hallucination." The Summary Bar in the UI uses the label "N leaps" and the tooltip uses "potential reasoning hallucination."

**The semantic precision problem**: "Hallucination" in LLM literature means the model generates false information. A topological gap is not necessarily false — it may be a correct reasoning step that skipped an intermediate concept. Calling it a "hallucination" overstates the claim.

**Proposed clean distinction for the paper:**
- **Structural leap**: the LRM's reasoning jumps to a disconnected KG region — measurable, value-neutral
- **Reasoning gap**: an incomplete explanation — the "why" behind the leap is not provided
- **Hallucination**: the step contains a factually incorrect claim — NOT what gap detection measures

**Question:** Should we remove "potential reasoning hallucination" from the UI tooltip and paper, replacing it consistently with "structural leap / incomplete explanation"? This would also require updating the `TopologicalGapBadge` tooltip text in `VerifierReasoningPanel.tsx`.

---

### Q5 — Section 3.1 Length and Mathematical Density

IEEE VIS VAST papers typically have 2-column layouts (ACM double-column format). A full formal definition section with 4 definitions + 1 theorem + implementation notes may run to ~0.75 column-pages, which is appropriate for the system design section.

**Risk**: Too much mathematical notation may alienate the target audience (VIS practitioners and HCI researchers) who are not formal-methods experts.

**Proposed mitigation**: Move Definitions 1–4 to a clearly labeled box ("Formal Definition: Topological Reasoning Mapping") and summarize them in plain English in the surrounding prose. This is the standard VIS approach for formal contributions (e.g., D3 [Bostock et al. 2011] presented grammar formally but surrounded it with intuitive descriptions).

**Question:** Should the formal box include all four definitions + the theorem, or just the two most critical definitions (Definition 2: Topological Adjacency and Definition 3: Topological Gap)?

---

## 4. Ablation Status

The DigiKlausur Gemini Flash ablation remains blocked on `GEMINI_API_KEY`. Once the key is available:

```bash
export GEMINI_API_KEY=your_key_here
cd packages/concept-aware
python run_lrm_ablation.py \
  --datasets digiklausur \
  --use-gemini \
  --gemini-key $GEMINI_API_KEY \
  --gemini-thinking-budget 8192 \
  --sample-n 646
```

After the ablation completes, inspect `data/digiklausur_lrm_traces_gemini.json` for Sample 0. The key check: does step 7 (CONTRADICTS) now have `kg_nodes` populated? If yes, the paper figure can be generated from the actual UI screenshot.
