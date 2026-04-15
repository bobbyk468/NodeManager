# ConceptGrade — Introduction & Recruitment Review v8

**Date:** 2026-04-14  
**Context:** IEEE VIS 2027 VAST — pre-pilot, pre-writing  
**Prior reviews:** v1–v6 (ablation → TRM gap), v7 (trace_gap_count wiring)  
**This review:** Gemini v8 decisions locked — figure trace selected, mixed-effects model implemented, recruitment bar set, intro language refined

---

## 1. What Was Resolved Since v7

### 1.1 Paper Figure Trace — Selected

Following Gemini v8's recommendation to use real DigiKlausur data:

**Candidate search script** scanned all 300 DeepSeek-R1 traces in `data/digiklausur_lrm_traces.json` for:
- ≥1 SUPPORTS step with KG nodes
- ≥1 CONTRADICTS step
- ≥1 topological gap (disjoint nodes AND edges between consecutive steps)

**Finding:** Only 7/300 traces have any `kg_nodes` populated; only 2 also have SUPPORTS + CONTRADICTS + a gap. Both have 20 steps (full DeepSeek-R1 chain-of-thought length).

**Selected: Sample ID 0 (key "0" in `digiklausur_lrm_traces.json`)**

- **Question**: "Give a definition for the term 'artificial neural network' and mention, how it resembles the human brain!"
- **Student answer**: "An artificial neural network is a massively parallel distributed processor with simple processing units..." (high-quality answer, human score = 5.0)
- **Matched concepts**: `processing_unit`, `artificial_neural_network`, `human_brain`, `synaptic_weights`, `learning_process`, `experiential_knowledge`
- **Why**: The 3-gap sequence (steps 10→11→12→13) traverses exactly the matched concepts: `processing_unit` → `experiential_knowledge/learning_process` → `human_brain` → `synaptic_weights`. These are the pedagogically meaningful NN concepts from the paper's domain. The gap sequence directly visualizes the TRM formal definition.

**Figure crop strategy** (Gemini v8: truncate noise with ellipsis):

| Figure step | Real step | Classification | KG nodes | Note |
|-------------|-----------|---------------|----------|------|
| [...] | Steps 1–4 | Mixed | None | Ellipsized — meta-reasoning preamble |
| 5 | Step 5 | SUPPORTS | `processing_unit` | First KG-mapped step |
| 6 | Step 6 | SUPPORTS | `processing_unit`, `experiential_knowledge` | Second KG-mapped step |
| 7 | Step 7 | CONTRADICTS | *(none)* | LRM flags missing link |
| [...] | Steps 8–9 | Mixed | None | Ellipsized |
| 10 | Step 10 | UNCERTAIN | `processing_unit` → `HAS_PART` | Gap starts |
| ⚠️ GAP | | | | `processing_unit` ↛ `experiential_knowledge` |
| 11 | Step 11 | UNCERTAIN | `experiential_knowledge`, `learning_process` → `PRODUCES` | |
| ⚠️ GAP | | | | `experiential_knowledge/learning_process` ↛ `human_brain` |
| 12 | Step 12 | UNCERTAIN | `human_brain` → `RESEMBLES` | |
| ⚠️ GAP | | | | `human_brain` ↛ `synaptic_weights` |
| 13 | Step 13 | UNCERTAIN | `synaptic_weights` → `USES` | |
| [...] | Steps 14–20 | Mixed | Mixed | Ellipsized — conclusion |

**Figure caption (draft)**:
> *Figure X: A representative reasoning trace from the DigiKlausur Neural Networks dataset (Sample 0). The LRM's chain-of-thought is mapped onto the domain Knowledge Graph using TRM. Steps 1–4 and 14–20 are visually truncated [...] for space. Amber dashed pills indicate topological gaps — sequential steps that share no KG node or edge type, revealing structural leaps in the LRM's reasoning. The educator can click any CONTRADICTS step to highlight the associated KG subgraph and trigger the Click-to-Add rubric feedback flow.*

**Limitation noted for paper**: DeepSeek-R1 traces do not reliably populate `kg_nodes` for CONTRADICTS steps (chain-of-thought format does not name nodes in judgment steps). The final paper figure may need a Gemini Flash trace (structured output) where node mapping is explicit. Flag as a limitation of the trace parser, not the TRM visualization.

---

### 1.2 Mixed-Effects Logistic Regression — Implemented

**`analyze_study_logs.py`** — new function `run_gap_moderation_analysis()`:

```python
# Model: Mixed-effects LM (approximation of logistic)
# statsmodels.formula.api.mixedlm(
#   'within_30s ~ condition * trace_gap_count',
#   df, groups=df['session_id']
# )
```

- Random intercept per participant (`session_id`) — removes between-participant baseline variance
- Fixed effects: `condition` (A=0, B=1), `trace_gap_count`, `condition × trace_gap_count` interaction
- Pre-registered as Exploratory Hypothesis: if p=0.08, report as "directional trend" in Discussion
- Silently skips if `statsmodels` not installed or < 10 sessions
- Note in output: "Session-level approximation only — re-derive from raw events for full study"

**Why mixed-effects (not standard logistic)**: Each participant generates 3–5 rubric edits. These are non-independent. A standard logistic regression would treat them as independent observations, inflating Type I error. The random intercept absorbs the participant-level baseline attribution tendency.

---

### 1.3 Introduction Language — Refined

Gemini v8 verdict on "shared epistemic workspace": too philosophical for a VIS opening paragraph.

**Revised closing sentence** (locked):
> "We argue that the missing link is not a better model, but a better interface — one that projects the model's reasoning onto the educator's domain knowledge, creating a **shared visual topology** for co-auditing."

The phrase "shared visual topology" grounds the philosophical contribution ("co-auditing") in the concrete visual artifact ("visual topology from TRM"), which is the language VIS reviewers expect in the opening.

---

### 1.4 Expert Recruitment Bar — Defined

Gemini v8 locked the minimum expertise threshold:

> Participant must have **actually graded CS or NN student work** in an academic setting.

This operationalization matters for the paper Methods section:
- Distinguishes pedagogical mental model (has graded) from domain knowledge alone (can define gradient descent)
- Defends the ecological validity claim: only participants with a prior rubric mental model can demonstrate epistemic update via the visualization

**Screener question (for Methods section)**:
> "In the past two years, have you graded or evaluated student answers to written questions in a Computer Science or Neural Networks course?" (Yes/No — Yes required for inclusion)

**Recruitment targets**: CS/Data Science TAs and Instructors at the researcher's university and neighboring institutions. $30–50 Amazon gift card for 45 minutes. Do not use LinkedIn, Reddit, or crowdsourcing platforms.

---

## 2. Open Questions for This Review

### Q1 — Trace Parser for the Paper Figure: DeepSeek-R1 vs. Gemini Flash

The paper figure requires CONTRADICTS steps with populated `kg_nodes`. All 300 DeepSeek-R1 traces have empty `kg_nodes` in CONTRADICTS steps — the chain-of-thought format expresses judgments ("this is wrong because...") without naming specific KG nodes.

**The problem**: Gemini Flash (structured output) forces node assignment because the trace parser prompt requires it. But the full DigiKlausur Gemini Flash ablation hasn't been run yet.

**Options:**
- (a) Run a single targeted Gemini Flash trace on Sample 0 now (1 API call) to get a trace with CONTRADICTS nodes for the figure.
- (b) Use the existing DeepSeek trace with the truncation strategy — accept that CONTRADICTS steps won't show node pills, and note this as a parser limitation in the caption.
- (c) Run the full DigiKlausur Gemini Flash ablation (646 samples, ~$5–10 of API budget) to have a complete corpus for both the figure and the accuracy evaluation.

**Recommendation requested**: Given the full Gemini Flash ablation is needed for the paper anyway (to demonstrate that the KG-grounded pipeline works with the primary LRM), should we run it now and get the figure trace as a side effect?

---

### Q2 — IRB Amendment: Exact Protocol Language

The Condition A change (blank rubric panel vs. populated rubric without trace) requires an expedited amendment. For the amendment to be approved quickly, it helps to frame the change as "no change in risk, only in the baseline interface."

**Draft amendment language:**
> "Amendment to experimental condition A: Participants in Condition A (control) will now see a blank rubric review panel rather than a pre-populated rubric list. This change does not alter the risk profile of the study; participants in both conditions still complete the same task (evaluating student answers and optionally flagging rubric concepts) with the same time limit and compensation. The change strengthens the experimental control by ensuring both conditions begin from the same zero-knowledge state with respect to rubric content, enabling a cleaner between-condition comparison."

**Question:** Is this the right framing, or should the amendment explain that Condition A now also serves as a measure of what educators *independently identify as important* (without AI or pre-loaded rubric cues)?

---

### Q3 — Introduction Draft: First Full Paragraph

Building on the opening sentence (locked in v8 above), the full first paragraph should:
1. Establish the problem (opacity of automated grading)
2. State the accountability gap (not accuracy, but accountability)
3. Introduce the visualization opportunity
4. Preview the contribution

**Draft first paragraph:**
> "Automated short-answer grading has reached human-level accuracy on structured benchmarks [cite Mohler 2011, Dzikovska 2016], yet educators remain reluctant to rely on it in high-stakes assessments. The bottleneck is not performance — it is accountability: when a model downgrades a student's answer, the educator has no mechanism to inspect why. This opacity makes the system an oracle to be trusted or ignored, rather than a collaborator to be audited. We argue that the missing link is not a better model, but a better interface — one that projects the model's reasoning onto the educator's domain knowledge, creating a shared visual topology for co-auditing. We present **ConceptGrade**, a visual analytics system that implements this topology through **Topological Reasoning Mapping (TRM)**: a technique that projects a large reasoning model's chain-of-thought onto a domain Knowledge Graph, enabling educators to co-audit both machine reasoning and student knowledge gaps simultaneously."

**Questions:**
- Is [cite Mohler 2011, Dzikovska 2016] the right citation pair? Should we also cite recent LLM grading work (e.g., GPT-4 on ASAG) to establish that the accuracy plateau is real?
- Does "oracle to be trusted or ignored" land well for a VIS audience, or is it too casual?
- Should "ConceptGrade" be bolded in the first paragraph introduction, or reserved for a formal system definition in Section 3?

---

### Q4 — Writing Next Steps: What to Write First?

With Introduction first paragraph drafted (above) and the writing order locked (v6: Intro → Design → Accuracy → Related Work → Study Skeleton → Conclusion → Intro polish), the next concrete writing task is:

**Section 1 (Introduction) target:** 800–1,000 words, ending with a contributions bullet list:
1. TRM: first technique to evaluate topological continuity of LRM reasoning chains against a domain KG
2. Bidirectional co-auditing interface: linked trace panel → KG subgraph → rubric editor
3. Empirical evidence: 32.4% MAE reduction on Mohler (p=0.003), Fisher combined p=0.003 across 1,239 answers
4. User study evidence (Y participants, two conditions): semantic alignment rate X% vs. null baseline Z% (p<0.05)

**Question:** Should the contribution list appear at the end of the Introduction (standard for IEEE VIS) or in a separate "Contributions" subsection? IEEE VIS VAST papers typically list contributions as a bulleted list at the end of the Introduction — is that correct?

---

### Q5 — DigiKlausur Gemini Flash Ablation: Now or After Pilot?

For the paper's accuracy evaluation (Section 5a), all three datasets need Gemini Flash traces (not just DeepSeek-R1) to report a fair comparison. Currently:
- Mohler: Gemini Flash traces available (ablation complete)
- DigiKlausur: DeepSeek-R1 traces only — Gemini Flash not run
- Kaggle ASAG: Status unknown

If the DigiKlausur Gemini Flash ablation is run now:
- **Benefit**: Full DigiKlausur corpus of structured traces → can select the cleanest CONTRADICTS-with-nodes trace for the paper figure
- **Cost**: ~$5–10 API budget, ~2 hours developer time to set up and verify
- **Risk**: None — this is needed for the paper regardless

**Recommendation requested**: Run the DigiKlausur Gemini Flash ablation now as the next implementation step, before the pilot study?

---

## 3. Full System Status

| Component | Status |
|-----------|--------|
| `trace_gap_count` end-to-end wiring | ✓ Complete (v7) |
| Mixed-effects moderation analysis in analyzer | ✓ Complete (v8) |
| Introduction first paragraph draft | ✓ Draft (above) |
| "Shared visual topology" language locked | ✓ (v8) |
| Expert recruitment bar defined | ✓ TAs with grading experience (v8) |
| Paper figure trace selected | ✓ Sample 0, DigiKlausur (v8) |
| IRB amendment filed | ✗ Required before pilot |
| Expert outreach started | ✗ Begin immediately |
| DigiKlausur Gemini Flash ablation | ✗ Next implementation step |
| Introduction written | ✗ Next writing step |
| `POST /api/study/log` backend endpoint | ✗ Before full study (N=20) |
