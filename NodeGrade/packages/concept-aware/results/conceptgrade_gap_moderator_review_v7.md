# ConceptGrade — Trace Gap Moderator & Paper Writing Review v7

**Date:** 2026-04-14  
**Context:** IEEE VIS 2027 VAST — post-pilot-prep, pre-writing  
**Prior reviews:** v1–v5 (ablation → submission readiness), v6 (TRM gap visualization)  
**This review:** (1) `trace_gap_count` moderator variable fully wired; (2) updated abstract; (3) paper writing order; (4) 5 open questions

---

## 1. What Was Built Since v6

### 1.1 `trace_gap_count` Wired End-to-End

Gemini v6 recommended adding `trace_gap_count` to the `rubric_edit` payload as a moderator variable for H1 (do more structurally gapped traces elicit higher causal attribution?). This is now implemented across the full stack:

**`DashboardContext.tsx`** — new state field + action:
```typescript
// State
lastTraceGapCount: number;   // published by VerifierReasoningPanel via SET_TRACE_GAP_COUNT

// Action
| { type: 'SET_TRACE_GAP_COUNT'; count: number }

// Action creator
const setTraceGapCount = (count: number) =>
  dispatch({ type: 'SET_TRACE_GAP_COUNT', count });
```

**`VerifierReasoningPanel.tsx`** — publishes count to context whenever `parsedSteps` changes:
```typescript
useEffect(() => {
  setTraceGapCount(topologicalGapCount);
}, [topologicalGapCount, setTraceGapCount]);
```

**`studyLogger.ts`** — new field in `RubricEditPayload`:
```typescript
// Topological gap moderator
trace_gap_count: number;   // # structural leaps in most recent LRM trace
```

**`RubricEditorPanel.tsx`** — reads from context, includes in payload:
```typescript
const { recentContradicts, lastTraceGapCount } = useDashboard();
// ...in handleEdit payload:
trace_gap_count: lastTraceGapCount,
```

**`analyze_study_logs.py`** — parses `trace_gap_count`, computes per-session mean, reports:
```python
# Per session: mean gap count at time of each edit
mean_trace_gap_count = sum(gap_counts_at_edit) / len(gap_counts_at_edit)

# In aggregate report: "Trace gap count at edits [moderator]" row
```

**Why this matters for the paper:** If `trace_gap_count` predicts higher `within_30s` attribution rates, it is a moderating variable that explains *why* some traces are more causally effective than others. This would appear in the Discussion section as a structural explanation for H1 effect size variability.

**Backwards compatibility:** `trace_gap_count` defaults to `0` in `analyse_session()` for any pre-v7 logs.

---

## 2. Updated Abstract (v2)

Based on Gemini v6 feedback, the abstract was revised:

> **ConceptGrade: A Visual Analytics System for Human-AI Co-Auditing of Knowledge Graph-Grounded Short-Answer Grading**
>
> Automated short-answer grading remains opaque: educators cannot inspect why a model assigns a score, nor trace which domain concepts drove the assessment. We present ConceptGrade, a visual analytics system that introduces **Topological Reasoning Mapping (TRM)**—a technique that projects a large reasoning model's chain-of-thought onto a structured Knowledge Graph topology, surfacing structural reasoning gaps and enabling educators to co-audit machine reasoning and student knowledge gaps simultaneously.
>
> ConceptGrade is evaluated at two levels. At the accuracy level, our KG-grounded pipeline reduces Mean Absolute Error by 32.4% over a pure LLM baseline on the Mohler CS dataset (Wilcoxon p=0.003) and achieves a Fisher combined p=0.003 across 1,239 answers from three domains. At the interaction level, a controlled user study (N=X, two conditions) demonstrates that educators exposed to TRM-rendered reasoning traces make rubric edits that facilitate mutual alignment between the machine's domain model and the human educator's pedagogical mental model, with a semantic alignment rate of Y% versus a hypergeometric null baseline of Z% (p<0.05).

**Changes from v1:**
- Added "surfacing structural reasoning gaps" to highlight the topological gap visualization
- Replaced "causally transfers epistemic knowledge" with "facilitate mutual alignment between the machine's domain model and the human educator's pedagogical mental model" (Gemini v6 recommendation — avoids overclaiming causality in the abstract)

---

## 3. Paper Writing Order (Locked for v7)

Based on Gemini v6 recommendation (write Introduction first to anchor the narrative arc):

| Order | Section | Status | Notes |
|-------|---------|--------|-------|
| 1 | Introduction | ✗ Not started | Write first — locks narrative arc |
| 2 | System Design | ✗ Not started | TRM formal definition; 5-stage pipeline; co-auditing model |
| 3 | Evaluation 5a (ML Accuracy) | ✗ Not started | Data final; Mohler 32.4%, Fisher p=0.0027 |
| 4 | Related Work | ✗ Not started | XAI for NLP, Educational Analytics, IMT vs co-auditing |
| 5 | Evaluation 5b (User Study) | ✗ Not started | Method skeleton now; fill results after pilot |
| 6 | Discussion + Conclusion | ✗ Not started | After study data |
| 7 | Introduction polish | ✗ Not started | Revise after full paper is written |

**Rationale for Introduction first:** The introduction must make the co-auditing claim concrete before writing the System Design section. Without a locked narrative, the System Design can drift toward feature enumeration rather than argument.

---

## 4. Open Questions for This Review

### Q1 — Paper Figure: Real Data vs. Constructed Example

The VerifierReasoningPanel with topological gaps is the core visual contribution. The paper needs a concrete figure showing:

1. A student answer (e.g., "neural networks learn by adjusting weights using gradient descent")
2. The LRM reasoning trace with 4–5 steps
3. SUPPORTS steps (green) + one CONTRADICTS step (red) + one structural leap gap (amber)
4. The KG subgraph with highlighted nodes

**Options:**
- (a) **Real DigiKlausur sample** — authentic, harder to cherry-pick criticism, but traces may be complex or noisy
- (b) **Simplified constructed example** — pedagogically cleaner, but risks "cherry-picked" reviewer critique

Gemini v6 recommended real DigiKlausur data for credibility. The concern: if the real trace has 12+ steps, it may be too dense for a half-column figure.

**Question:** Should we run the full DigiKlausur LRM ablation now (all 646 samples through Gemini Flash) to have a corpus of real traces to choose from? Or pick a representative 4–5 step example manually by inspecting the existing per-sample data?

**Note:** The LRM ablation for DigiKlausur was not yet run (Stage 3a verifier output exists for Mohler only).

---

### Q2 — IRB Protocol Update Required

Condition A changed since the original IRB submission: the rubric panel in Condition A is now **blank** (no pre-populated concepts), not a populated rubric without trace context. This is a different baseline condition.

**Question:** Does this constitute a protocol deviation requiring IRB amendment, or is it within the scope of "interface A vs. interface B" as described in the original protocol?

If an amendment is required, the pilot study (2–3 participants) should be paused until the amendment is approved.

---

### Q3 — Introduction First Paragraph Draft

Gemini v6 confirmed Introduction should be written first. The challenge: the opening must establish why short-answer grading is a *high-stakes HCAI problem* (not just an NLP task) in a way that VIS reviewers find compelling.

**Candidate opening (for feedback):**

> "Automated grading of student short answers has reached human-level accuracy on structured benchmarks [ref], yet educators remain reluctant to rely on it in high-stakes assessments. The gap is not accuracy — it is accountability: when a model downgrades a student's answer, the educator has no mechanism to inspect why. This opacity makes automated grading an adversarial co-pilot rather than a collaborative one. We argue that the missing link is not a better model, but a better interface — one that projects the model's reasoning onto the educator's domain knowledge, creating a shared epistemic workspace for co-auditing."

**Question:** Is "epistemic workspace" too jargon-heavy for a VIS introduction? Should the opening center on the model's reasoning opacity, the educator's accountability gap, or the visualization opportunity?

---

### Q4 — Moderation Analysis Plan for `trace_gap_count`

The `trace_gap_count` moderator is now logged on every `rubric_edit` event. Before the full study, we need a pre-registered analysis plan so the gap count analysis is not a post-hoc researcher DoF.

**Proposed moderation analysis:**
- Outcome: `within_30s` (binary, primary H1 variable)
- Moderator: `trace_gap_count` (continuous, 0–N)
- Test: Logistic regression — does `trace_gap_count` predict `within_30s` after controlling for condition?
- Hypothesis: Higher gap count → higher within_30s rate (in Condition B only; Condition A has no trace)

**Question:**
- Is logistic regression the right test, or should this be a mixed-effects model (random effect = participant)?
- If the pilot yields only 2–3 participants with 5–10 edits each, we won't have power for this analysis. Should we flag it as exploratory only and not pre-register it as a primary hypothesis?

---

### Q5 — Expert Recruitment Strategy

Gemini v5 identified expert recruitment as the highest critical path risk. The full study needs 20–30 CS/NN domain experts for 45-minute think-aloud sessions.

**Current status:** No outreach started.

**Proposed strategy:**
- Target pool 1: CS teaching assistants at local universities (accessible, motivated)
- Target pool 2: Online CS communities (Reddit r/cscareerquestions, Hacker News "Who wants to be interviewed?")
- Target pool 3: Professional ML practitioners (LinkedIn, Twitter/X)
- Compensation: $30–50 Amazon gift card for 45 minutes

**Question:**
- What is the minimum domain expertise threshold for a valid participant? (PhD student vs. industry practitioner vs. professor — which is sufficient?)
- Should "domain expert" be operationalized as: can identify whether "gradient descent" is a concept in the neural networks domain, or stricter (has taught NN/CS courses)?

---

## 5. Full System Status (Pre-Pilot Snapshot)

### Study Infrastructure
| Component | Status |
|-----------|--------|
| RubricEditorPanel — Condition A blank | ✓ |
| RubricEditorPanel — Click-to-Add chips + pulse | ✓ |
| Rolling 60-second CONTRADICTS window | ✓ |
| Multi-window logging (15s/30s/60s) | ✓ |
| Semantic alias matching (conceptAliases.ts) | ✓ |
| Hypergeometric p-value (per session) | ✓ |
| `trace_gap_count` in rubric_edit payload | ✓ **NEW** |
| `trace_gap_count` in analyze_study_logs.py | ✓ **NEW** |
| `POST /api/study/log` backend endpoint | ✗ Not built — before full study (N=20) |
| Cued Retrospective Think-Aloud script | ✗ Not written |
| Expert participant pool | ✗ Not yet recruited |
| DigiKlausur LRM traces (Stage 3a) | ✗ Not run |

### Next Actions Before Pilot
| Action | Priority |
|--------|----------|
| Write Introduction draft (first ~800 words) | HIGH |
| Begin expert outreach (target: 5 confirmed before full study) | HIGH |
| Confirm IRB protocol scope (Condition A blank panel) | HIGH |
| Select pilot dataset and real trace for paper figure | MEDIUM |
| Run DigiKlausur LRM ablation for figure corpus | MEDIUM |
| Build `POST /api/study/log` endpoint | MEDIUM — before full study |
