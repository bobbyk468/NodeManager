# Gemini Review Request v19
**Date:** 2026-04-17  
**Paper:** IEEE VIS 2027 VAST — "Co-Auditing as Epistemic Update"  
**Prior rounds:** v1–v18 (all decisions locked)  
**This round:** Final co-author readiness pass — Abstract, Title, Supplemental A, figure captions, cross-section consistency, submission strategy

---

## Current Paper State (Post v18)

All sections assembled and locked:

| Section | Words | Status |
|---------|-------|--------|
| §1 Introduction | ~670 | ✅ Locked |
| §2 Related Work | ~450 | ✅ Locked |
| §3 TRM Formalization | ~350 | ✅ Locked |
| §4 System Architecture | ~920 | ✅ Locked (KG expansion applied) |
| §5a ML Accuracy | ~400 | ✅ Locked (data [TODO] remaining) |
| §5b User Study | scaffold | ✅ Scaffold locked (prose post-pilot) |
| §6 Discussion | ~530 | ✅ Locked |
| §7 Conclusion | ~230 | ✅ Locked |
| **Total** | **~3,550** | **Ready for co-author circulation** |

**Not yet written:** Abstract, Supplemental Material A, figure captions (pipeline + running example).

---

## Section 1: Abstract

The abstract is the most-read part of the paper and the first thing co-authors, program chairs, and reviewers will see. IEEE VIS allows up to 150 words. A VAST abstract should follow this structure: Problem (1–2 sentences) → Approach (2–3 sentences) → Evaluation (2 sentences) → Impact (1 sentence).

### Proposed Abstract Draft (~145 words):

> Automated short-answer grading has reached human-level accuracy on structured benchmarks, yet educators remain reluctant to rely on it in high-stakes assessments. The bottleneck is accountability: when a model downgrades a student's answer, the educator has no mechanism to inspect why. We present **ConceptGrade**, a visual analytics system that addresses this gap through **Topological Reasoning Mapping (TRM)** — a technique that projects a large reasoning model's chain-of-thought onto a domain Knowledge Graph, making structural leaps in the model's reasoning visible and actionable. ConceptGrade enables *co-auditing*: a bidirectional process in which an educator inspects the AI's reasoning topology and updates their own rubric criteria in response. We evaluate ConceptGrade at two levels: a KG-grounded scoring pipeline that reduces mean absolute grading error by 32.4% over a pure LLM baseline across 1,239 student answers (Fisher p = 0.003), and a controlled user study demonstrating that TRM visualization facilitates measurable semantic alignment between the AI's flagged reasoning gaps and the educator's rubric updates.

---

### Q1 — Abstract: Problem Sentence Placement

**Question:** The proposed abstract leads with "Automated short-answer grading has reached human-level accuracy…" — the same opening as §1. For a 150-word abstract, starting with the known-good result (accuracy) and then immediately introducing the accountability gap is structurally strong but may feel like it buries the lede.

An alternative opening: *"Educators cannot audit what they cannot see: when an AI grading system downgrades a student's answer, its reasoning chain is invisible."*

**Please answer:** Keep the current abstract opening (parallel to §1, conventional academic tone) or adopt the shorter punchy opener? Justify for VAST program chairs who read ~200 abstracts.

---

### Q2 — Abstract: User Study Placeholder

**Question:** The abstract ends with "a controlled user study demonstrating that TRM visualization facilitates measurable semantic alignment between the AI's flagged reasoning gaps and the educator's rubric updates." This is a forward-projection (study data is pending). Should the abstract:
(a) Keep this forward-projection as-is (standard for a draft circulated pre-data)
(b) Replace with: "a controlled user study design with pre-registered causal proximity and semantic alignment metrics" (describes the study without claiming results)
(c) Omit the user study from the abstract until data is available

**Please answer:** Which option is most appropriate for a co-author draft that will eventually become a submission abstract?

---

## Section 2: Paper Title

Current title: **"Co-Auditing as Epistemic Update — How Visual Trace Analytics Force Educators to Externalize Implicit Rubric Mental Models"**

This title has been in use since the project began. Before co-author circulation, it should be validated against VAST submission norms.

### Q3 — Title Validation

**Question:** The current title is 19 words — longer than typical IEEE VIS titles (12–15 words). It has two parts: (a) a conceptual claim ("Co-Auditing as Epistemic Update") and (b) a descriptive subtitle ("How Visual Trace Analytics Force Educators to Externalize Implicit Rubric Mental Models").

VAST titles tend to be either:
- **System-centric:** "ConceptGrade: Visual Co-Auditing of AI Reasoning for Educational Assessment"
- **Paradigm-centric:** "Co-Auditing: A Visual Analytics Paradigm for AI-Educator Alignment in Grading"
- **Effect-centric:** "Visualizing Structural Leaps: How Reasoning Topology Transparency Enables Rubric Co-Auditing"

**Please answer:**
1. Is the current 19-word title appropriate for VAST, or should it be shortened?
2. If shortening: which of the three alternatives above best preserves the paper's contribution framing?
3. Or: draft a fourth option that combines the co-auditing paradigm name with the visual analytics system identity.

---

## Section 3: Supplemental Material A

§4.4 and §5b both reference "Supplemental Material A" for the telemetry layer details. This supplemental has not been outlined yet.

### Proposed Supplemental A Structure:

```
Supplemental Material A: Study Telemetry Specification

A.1 Event Schema
    - StudyEvent JSON structure (session_id, condition, dataset, event_type,
      timestamp_ms, elapsed_ms, payload)
    - RubricEditPayload: all 17 fields with types and descriptions
    - AnswerDwellPayload: all fields including benchmark_case metadata

A.2 Multi-Window Attribution Logic
    - Rolling 60-second CONTRADICTS window implementation
    - within_15s / within_30s / within_60s re-filtering at edit time
    - interaction_source: 'manual' vs 'click_to_add' split

A.3 Semantic Matching Algorithm
    - 3-layer fuzzy matching (exact → alias dict → Levenshtein ≥ 0.80)
    - Alias dictionary scope: CS + NN domains only
    - matchesContradictsNode() return signature

A.4 Condition A/B Gating
    - CSS visibility:hidden implementation (telemetry retained)
    - URL parameter routing (?condition=A|B)
    - Session consistency validation criteria
```

### Q4 — Supplemental A: What to Include

**Question:** The proposed Supplemental A covers four topics: event schema, attribution logic, semantic matching, and condition gating. For VAST supplementals:
1. Is this level of implementation detail (JSON schemas, algorithm pseudocode) appropriate for a VAST supplemental, or does it belong in a GitHub repository with a pointer in the paper?
2. Should Supplemental A prioritize the telemetry specification (for reproducibility reviewers) or the condition gating design (for HCI reviewers who may question the Condition A control)?

**Please answer:** Which 1–2 topics from the proposed outline are most essential for the VAST supplemental? Which should move to a GitHub repo README?

---

## Section 4: Figure Captions (Remaining 2 of 3)

The UI screenshot caption was locked in v14. Two figure captions remain unwritten.

### Figure 1: Pipeline Figure

**Question (Q5):** The pipeline figure shows: KG → LRM Verifier → Trace Parser → TRM Projection → DashboardContext → Three Panels.

Draft caption:
> *"**Figure 1: The ConceptGrade Pipeline.** A domain Knowledge Graph (KG) and student answer are jointly processed by an LRM Verifier (Gemini Flash / DeepSeek-R1), which produces a 20–40 step chain-of-thought trace. The Trace Parser extracts concept node mappings (φ) and classifications (SUPPORTS / CONTRADICTS / UNCERTAIN). TRM Projection (§3, Definitions 1–5) identifies structural leaps and computes grounding density. DashboardContext propagates all derived state to three linked panels via bidirectional brushing."*

Is this caption the right length and detail level for a VAST pipeline figure? Should it reference specific section numbers or definitions, or stay high-level?

**Please answer:** Approve caption as-is, trim to 2 sentences, or expand to include a specific example (e.g., "for the DigiKlausur sample in Figure 3...").

---

### Figure 3: Running Example (DigiKlausur Sample 0)

**Question (Q6):** The running example figure shows the processing_unit → human_brain structural leap from §3. This figure appears in §3 (TRM Formalization) and serves as the concrete instantiation of Definitions 1–3.

Draft caption:
> *"**Figure 3: TRM Running Example — DigiKlausur Sample 0.** Step 10 maps to N₁₀ = {processing\_unit} (the LRM reasons about what a neural network is *made of*). Step 11 maps to N₁₁ = {human\_brain} (the LRM reasons about what a neural network *resembles*). Because N₁₀ ∩ N₁₁ = ∅, Definition 3 classifies this as a structural leap (amber indicator). The intermediate concepts `learning_process` and `synaptic_weights` — which connect processing units to the brain analogy in the KG — were skipped."*

**Please answer:** Approve caption as-is or suggest trimming. Note: this figure is the first concrete visual in the paper and should be immediately graspable by a non-expert reviewer.

---

## Section 5: Cross-Section Consistency Check

Before co-author circulation, the paper should be checked for terminology and framing consistency across sections.

### Q7 — Terminology Audit

**Question:** The following terms appear across multiple sections. Please confirm each is used consistently:

| Term | Where used | Potential inconsistency to check |
|------|-----------|----------------------------------|
| "structural leap" | §1, §3, §4, §6 | Should never appear as "inferential leap" or "reasoning gap" (those are different) |
| "co-auditing" | §1, §4, §6, §7 | Should be consistently hyphenated (co-auditing, not coauditing or co auditing) |
| "implicit mental model" | §1, §6 | Should consistently cite [Kulesza 2012, Bansal 2019, Pirolli & Card 2005] |
| "CONTRADICTS" | §3, §4, §5b | Should always be capitalized (it is a system classification, not an English word) |
| "boundary condition" | §5a, §6 | Must not slip to "limitation" in §5a context |
| "LRM" | §1, §2, §3, §4 | Should always be expanded on first use per section: "large reasoning model (LRM)" |

**Please answer:** Are there any other terminology consistency risks in a paper of this structure that we should check before submission?

---

## Section 6: Submission Strategy

### Q8 — VAST Track Reviewer Profile

**Question:** IEEE VIS 2027 has multiple tracks: VAST, InfoVis, SciVis, and associated workshops. Within VAST, papers are typically reviewed by 3 reviewers from a pool that spans VA systems, ML+VA, and human-centered AI. Given the paper's balance:
- 40% VA system design (§4)
- 25% evaluation (§5a + §5b)
- 20% formalization + related work (§2 + §3)
- 15% framing (§1 + §6 + §7)

Which reviewer profile is most likely to be our "Reviewer 2" (the hardest to satisfy)?
1. **ML/NLP reviewer** who will question the KG grounding accuracy and LRM faithfulness
2. **HCI reviewer** who will question whether the user study sample size is sufficient for causal claims
3. **VA systems reviewer** who will question the novelty of bidirectional brushing and linked views

**Please answer:** Identify the highest-risk reviewer profile and advise on which paper sections most need pre-emptive hardening before submission.

---

### Q9 — Submission Timeline

**Question:** The paper's critical path to VIS 2027 submission is blocked by: (1) IRB amendment approval (48–72 hours for expedited), (2) participant recruitment (4–8 weeks for 20–30 TAs), (3) study execution (1–2 weeks), (4) analysis and §5b drafting (1–2 weeks). VIS 2027 submission deadline is likely March 2027.

Working backward: recruitment must begin by **October 2026** at the latest to preserve a 2-week buffer.

**Please answer:** Is this timeline feasible, or does the pilot study need to begin earlier (e.g., August 2026) to account for IRB, recruitment delays, and conference revision cycles? What is the recommended "no-later-than" date to begin recruitment?

---

## Locked Decisions Reminder

All prior decisions (v1–v18) are locked. Do not reopen:

| Decision | Locked Value |
|----------|-------------|
| §7 closing | "should form a central research agenda for the visual analytics community" |
| §6.2 faithfulness | Pre-emption: "co-auditing transforms hidden algorithmic unfaithfulness into visible structural gaps" |
| §5b.4 | "exploratory qualitative observations" — not pre-registered hypothesis tests |
| SUS placement | Brief mention in §5b.3 as sanity check only |
| §4.3 KG expansion | Approved as written (force-directed, opacity reduction, 15-concept bound) |

---

## Expected Output Format

For each question:
1. **Decision** (1 sentence)
2. **Rationale** (2–3 sentences, reviewer-risk framing)
3. **Draft text** (where text changes recommended — full sentence, paste-ready)

**Priority this round:** Q1 (abstract opening), Q3 (title), Q8 (highest-risk reviewer profile), Q9 (submission timeline).

---

**End of Gemini Review v19**
