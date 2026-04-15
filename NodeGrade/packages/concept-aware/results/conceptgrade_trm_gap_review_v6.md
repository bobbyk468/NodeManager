# ConceptGrade — TRM Edge Traversal & Paper Framing Review v6

**Date:** 2026-04-14  
**Context:** IEEE VIS 2027 VAST — post-pilot-prep, pre-writing  
**Prior reviews:** v1 (ablation), v2 (empirical), v3 (rubric tracking), v4 (semantic alignment), v5 (submission readiness)  
**This review:** Two additions since v5 — (1) topological gap visualization implementing the TRM edge-traversal definition, (2) locked paper framing decisions

---

## 1. What Was Built Since v5

### 1.1 Topological Gap Indicator (TRM Edge-Traversal Proof-of-Concept)

Gemini v5 refined the TRM formal definition to include edge traversal:

> *"TRM evaluates the topological continuity of R by measuring whether sequential reasoning steps (sᵢ, sᵢ₊₁) map to connected subgraphs within G, thereby exposing structural leaps or hallucinations in the machine's logic."*

This is now implemented in `VerifierReasoningPanel.tsx`:

**Gap detection logic:**
```typescript
function hasTopologicalGap(stepA: ParsedStep, stepB: ParsedStep): boolean {
  if (stepA.kg_nodes.length === 0 || stepB.kg_nodes.length === 0) return false;
  const nodesA = new Set(stepA.kg_nodes);
  if (stepB.kg_nodes.some(n => nodesA.has(n))) return false;  // shared node → connected
  const edgesA = new Set(stepA.kg_edges);
  if (stepB.kg_edges.some(e => edgesA.has(e))) return false;  // shared edge type → connected
  return true;  // both nodes AND edges disjoint → structural leap
}
```

**Visual output:**
- Between disconnected step pairs: amber dashed pill — *"structural leap — disconnected KG region"*
- Tooltip names the specific nodes on each side (e.g., "step #3 refs [chain_rule] but step #4 jumps to [gradient_descent] with no shared KG node or edge")
- Summary bar: amber warning badge — *"N leaps"* — visible at a glance before reading individual steps

**Purpose in the paper:** This gives reviewers a concrete visual artifact that proves the graph topology is computationally load-bearing, not decorative. A flat NLP model would never surface this.

### 1.2 Paper Framing Decisions Locked

From v5 review, the following are now committed to memory and not to be re-opened:

| Decision | Verdict |
|----------|---------|
| Kaggle ASAG framing | "Domain boundary condition" — report honestly, explain n.s. as expected KG mismatch |
| Primary H2 metric | Semantic alignment rate (exact = strict lower bound) |
| Co-auditing vs IMT | Distinction: human updates *their own rubric*, not the model weights |
| TRM definition | Must include edge traversal (topological continuity) |
| Recruitment risk | Begin expert outreach NOW — highest critical path risk |

---

## 2. Full System Status (Pre-Pilot Snapshot)

### ML Accuracy (Paper 1 / Section 5a)
| Dataset | N | C_LLM MAE | C5 MAE | Δ | p |
|---------|---|-----------|--------|---|---|
| Mohler (CS) | 120 | 0.3300 | **0.2229** | −32.4% | 0.0026 |
| DigiKlausur (NN) | 646 | 1.1842 | **1.1262** | −4.9% | 0.0489 |
| Kaggle ASAG (Sci) | 473 | 1.2082 | **1.1797** | −2.4% | 0.340 n.s. |
| Fisher combined | 1,239 | | | | **0.0027** |

### User Study Infrastructure (Section 5b)
| Component | Status |
|-----------|--------|
| RubricEditorPanel — Condition A blank | ✓ |
| RubricEditorPanel — Click-to-Add chips + pulse | ✓ |
| Rolling 60-second CONTRADICTS window | ✓ |
| Multi-window logging (15s/30s/60s) | ✓ |
| Semantic alias matching (conceptAliases.ts) | ✓ |
| Hypergeometric p-value (per session) | ✓ |
| Topological gap counter in study log | ✗ Not yet logged |
| `POST /api/study/log` backend endpoint | ✗ Not built |
| Cued Retrospective Think-Aloud script | ✗ Not written |
| Expert participant pool | ✗ Not yet recruited |

---

## 3. Open Design Questions for This Review

### Q1 — Topological Gap: Correct Approximation?

The current gap detection uses **node set intersection + edge type intersection** as a proxy for KG connectivity. The limitation: two nodes might have a direct edge in the KG that is NOT captured in the step's `kg_edges` field (because the trace parser only records the edge types the LRM *explicitly mentioned*, not all edges between the nodes).

This means the gap detection could produce **false positives** — flagging a "structural leap" when the two nodes are actually connected in the underlying KG but the LRM didn't explicitly traverse that edge.

**Is this a problem for the paper claim?** The claim is about the LRM's *reasoning continuity*, not the KG's actual connectivity. If the LRM jumped from node A to node C without mentioning the A→B→C path, that IS a structural leap in the reasoning trace — even if A and C are technically connected through B. So the false positive might actually be correctly identifying an incomplete explanation.

**Question:** Should the gap indicator be based on:
- (a) The LRM's *referenced* nodes/edges (current implementation — shows reasoning gaps)
- (b) The actual KG topology (requires querying the graph — shows KG connectivity)

Which is more defensible for the co-auditing claim?

### Q2 — Gap Count as a Study Metric

We don't currently log topological gap count per trace to `analyze_study_logs.py`. This could be a valuable metadata field:

- Does the number of structural leaps in a trace predict whether the educator clicks CONTRADICTS steps?
- Do traces with more gaps produce higher causal attribution rates (because the gaps are more salient/alarming)?

**Should we add `trace_gap_count` to the `rubric_edit` payload?** This would require passing the gap count from `VerifierReasoningPanel` up through the component hierarchy to the `RubricEditorPanel`.

**Cost vs. benefit:** This adds ~10 lines of state-threading code. If gap count predicts educator engagement, it's a strong moderating variable for H1 that would strengthen the paper. If it doesn't predict engagement, it's just noise in the logs.

### Q3 — Paper Writing Order

Given the system is feature-complete and the pilot is imminent, what is the correct writing order for a VAST submission?

**Proposed order:**
1. System Design section (concrete, can be written now — architecture, TRM definition, interaction model)
2. ML Accuracy evaluation (Sections 5a — data is final, no pilot needed)
3. Related Work (can be written now — IMT, model debugging, educational analytics)
4. User Study section skeleton (5b — write the method now; fill in results after pilot)
5. Introduction + Conclusion (written last, after the paper's argument is crystallized)

**Question:** Is this the right order, or should Introduction be written first to lock the narrative arc before writing subsections?

### Q4 — The TRM Visualization as a Figure in the Paper

The VerifierReasoningPanel with topological gaps is the core visual contribution. For the paper figure, we need a concrete example that shows:

1. A student answer (e.g., "neural networks learn by adjusting weights using gradient descent")
2. The LRM reasoning trace with 4-5 steps
3. SUPPORTS steps mapped to KG nodes (green)
4. A CONTRADICTS step (red) — the key causal trigger
5. A structural leap gap between two steps (amber)
6. The KG subgraph with highlighted nodes

**Question:** Should this figure use a real sample from the DigiKlausur dataset (authentic but possibly complex) or a simplified constructed example (cleaner but potentially criticized as cherry-picked)?

VIS papers typically use real data for credibility. But if the real examples are too noisy (too many steps, unclear structure), a simplified representative example might be more pedagogically effective.

### Q5 — `POST /api/study/log` — Build Before Pilot or After?

The localStorage fallback is active. Risk assessment:

- **Without the endpoint:** If a participant's browser crashes or tab closes during the session, all event data for that session is lost. For N=20 participants, losing even 2 sessions reduces statistical power significantly.
- **Building the endpoint:** ~2 hours of NestJS work (controller + DTOs + file write / DB insert). Not complex — it mirrors the existing `/api/visualization` pattern.

**Recommendation requested:** Given the pilot is 2-3 participants only (low loss risk), should we build the backend endpoint before the full study (N=20) but not block the pilot on it? Or should we build it now to establish the IRB-grade data collection baseline from the very first session?

---

## 4. Proposed Paper Abstract (v1 — for feedback)

> **ConceptGrade: A Visual Analytics System for Human-AI Co-Auditing of Knowledge Graph-Grounded Short-Answer Grading**
>
> Automated short-answer grading remains opaque: educators cannot inspect *why* a model assigns a score, nor can they trace which domain concepts drove the assessment. We present ConceptGrade, a visual analytics system that introduces **Topological Reasoning Mapping (TRM)**—a technique that projects a large reasoning model's chain-of-thought onto a structured Knowledge Graph topology, enabling educators to co-audit machine reasoning and student knowledge gaps simultaneously.
>
> ConceptGrade is evaluated at two levels. At the accuracy level, our KG-grounded pipeline reduces Mean Absolute Error by 32.4% over a pure LLM baseline on the Mohler CS dataset (Wilcoxon p=0.003) and achieves a Fisher combined p=0.003 across 1,239 answers from three domains. At the interaction level, a controlled user study (N=X, two conditions) demonstrates that educators exposed to TRM-rendered reasoning traces make rubric edits with a semantic alignment rate of Y% versus a hypergeometric null baseline of Z% (p<0.05), providing quantitative evidence that the visualization causally transfers epistemic knowledge from the machine's domain model to the human educator's pedagogical mental model.

**Questions on the abstract:**
- Does "co-auditing" need a brief definition in the abstract, or is the concept clear from context?
- Is "epistemic knowledge transfer" the right framing, or is it too philosophical for a VIS audience?
- Should we mention the topological gap (structural leap) detection in the abstract, or save it for the body?
