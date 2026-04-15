# ConceptGrade — Rubric Edit Causal Tracking: Design Review Request

**Date:** 2026-04-14  
**Context:** IEEE VIS 2027 VAST — user study instrumentation for "co-auditing interface" framing  
**Prior review:** Gemini v1 (ablation results), Gemini v2 (empirical follow-up)  
**This review:** The rubric edit tracking system built to answer: *"How do we prove the LRM's CONTRADICTS trace causally influences educator rubric decisions?"*

---

## 1. What Was Built

### 1.1 Component Stack

```
VerifierReasoningPanel   — educator clicks a CONTRADICTS step
         ↓ setLastContradicts(nodeId)
DashboardContext         — stores { nodeId, timestamp_ms }
         ↓ read at edit time
RubricEditorPanel        — educator flags rubric concept (add/remove/reweight)
         ↓ logEvent('rubric_edit', payload)
studyLogger.ts           — writes to localStorage + POST /api/study/log
         ↓ exported as JSONL
analyze_study_logs.py    — computes causal_attribution_rate, concept_alignment_rate
```

### 1.2 The Causal Proximity Payload

Every `rubric_edit` event captures (atomically at click time):

```json
{
  "event_type": "rubric_edit",
  "payload": {
    "edit_type": "add",
    "concept_id": "chain_rule",
    "concept_label": "chain rule",
    "source_contradicts_node": "chain_rule",
    "time_since_contradicts_ms": 4000,
    "concept_in_contradicts": true,
    "session_contradicts_nodes": ["chain_rule", "error_reduction"]
  }
}
```

### 1.3 Derived Metrics (per session, then aggregated per condition)

| Metric | Definition | Why it matters |
|--------|-----------|----------------|
| `rubric_edits` | Total edit actions | Baseline engagement measure |
| `causal_attribution_rate` | Fraction of edits within 30 s of a CONTRADICTS interaction | Temporal proximity to trace engagement |
| `concept_alignment_rate` | Fraction of edited concepts that appeared in session CONTRADICTS nodes | Semantic proximity — did they edit what the LRM flagged? |
| `contradicts_interactions` | Total clicks on CONTRADICTS steps in the trace panel | Depth of trace engagement |

---

## 2. The Causal Argument

### What we are trying to prove

**H1 (temporal):** Educators make rubric edits within 30 seconds of clicking a CONTRADICTS node more often than chance.  
**H2 (semantic):** Educators edit concepts that appeared in CONTRADICTS nodes at a rate higher than chance given the rubric size.

### How the 30-second window was chosen

30 seconds is the window for "active working memory" engagement with a visual element — long enough for the educator to read the step, process the concept, and act; short enough to exclude edits that occur during unrelated activity.

**Review question:** Is 30 seconds the right window? Should we report multiple windows (10 s, 30 s, 60 s) and find the one that maximises the attribution rate? Or does multiple-window testing introduce a researcher degrees-of-freedom problem?

### Chance baseline for H2

If an educator makes `k` edits from a rubric of `n` concepts, and the LRM flagged `m` concepts as CONTRADICTS, the expected alignment under the null is `k × m/n`. With typical values (k=3 edits, n=20 rubric concepts, m=5 CONTRADICTS nodes), the null alignment rate = 0.75/3 = 0.25.

**Review question:** Is hypergeometric probability the right null model here, or should we use a permutation test on the observed edit sequences?

---

## 3. What the RubricEditorPanel Shows Educators

Displayed in Condition B only, after the main task is submitted:

1. **CONTRADICTS node strip** — chips for every concept the LRM flagged across all visible traces  
2. **Warning banner** — highlights which flagged concepts are NOT in the current rubric (prime "add" candidates)  
3. **Rubric concept list** — all current rubric nodes with 4 action buttons each:
   - Remove from rubric
   - Increase weight
   - Decrease weight
   - (Add — for CONTRADICTS nodes not yet in rubric)
4. **Submit Rubric Feedback** — logs the full edit summary with causal attribution data

The panel is intentionally NOT shown in Condition A (summary card only) — this is the key between-condition manipulation.

---

## 4. Design Decisions for Review

### Q1 — Edit attribution: last-event vs. any-event

Current design: `source_contradicts_node` = the **last** CONTRADICTS node the educator clicked before the edit.

Alternative: record **all** CONTRADICTS nodes clicked in the preceding 30-second window, not just the last one.

Which is more appropriate for a causal claim? The last-event model is simpler and avoids double-counting, but misses cases where the educator was considering multiple flagged concepts before acting.

### Q2 — Condition A control

Condition A educators have no trace panel, so they make 0 rubric edits (the RubricEditorPanel is gated to Condition B). This means we cannot use A vs B as a within-subjects comparison for rubric edit rate.

Two analysis options:
- **(a)** Report rubric edits as a Condition B-only metric; show that causal_attribution_rate > chance baseline
- **(b)** Show Condition A participants a blank rubric review panel (no trace context, no CONTRADICTS strip) and compare edit patterns

Option (b) would give a true A/B comparison of rubric edit *content* — do Condition B educators make more semantically aligned edits than Condition A? This would directly test whether the CONTRADICTS visualization changes *what* educators choose to edit, not just *whether* they edit.

**Recommendation requested:** Is option (b) worth the added complexity? The trade-off is IRB/protocol revision vs. stronger experimental control.

### Q3 — Temporal ordering assumption

The causal claim requires: CONTRADICTS interaction → rubric edit (in that order). The logger captures timestamps for both, so ordering is verifiable post-hoc. But educators may also:
1. Edit rubric first, *then* look at traces to confirm their decision (reverse causal)
2. Edit based on their own prior domain knowledge, not the trace at all

**How would you distinguish these in the data?** Proposed: compare `time_since_contradicts_ms` distribution for "concept in CONTRADICTS" edits vs. "concept NOT in CONTRADICTS" edits. If the former cluster at < 30 s and the latter are uniformly distributed, that supports the causal direction.

### Q4 — Think-aloud protocol integration

The quantitative causal proximity data is necessary but not sufficient for a VIS paper — reviewers will want qualitative evidence that educators were *consciously* influenced by the trace.

**Proposed:** Add a prompted think-aloud question immediately after each rubric edit: "What made you flag this concept?" with options:
- I saw it in the LRM trace
- I already knew this from my domain knowledge
- I noticed it from the student answers
- Other

This self-report would validate (or challenge) the temporal proximity signal.

**Review question:** Is self-report reliable enough to make causal claims in an HCI paper? Or does the temporal proximity data alone suffice for IEEE VIS?

### Q5 — Effect size for the VIS paper

With expected n=10–15 participants per condition, statistical power is limited. What effect size would be meaningful for this claim?

Proposed primary metric: **Concept Alignment Rate** in Condition B vs. null baseline (hypergeometric p).

With n=10 Condition B participants, average 3 edits each = 30 edit events. If concept_alignment_rate = 0.60 against a null of 0.25 (m=5 concepts, n=20 rubric), that's a large effect (Cohen's h ≈ 0.77) achievable with n=10.

**Review question:** For a VIS paper, is a statistically significant causal proximity result with n=10 per condition publishable, or does the community expect larger samples?

---

## 5. Test Results

All components were verified:

| Test | Result |
|------|--------|
| TypeScript compilation (`tsc --noEmit`) | ✓ 0 errors |
| Vite dev server bundle (both tsx files) | ✓ No transform errors |
| `analyze_study_logs.py` with synthetic Cond A + B sessions | ✓ Correct output |
| Synthetic Cond B session: 2 edits (1 causal, 1 not) | ✓ `causal_attribution_rate=0.500` |
| Synthetic Cond B session: 1 CONTRADICTS edit, 1 non-CONTRADICTS | ✓ `concept_alignment_rate=0.500` |
| 10-point wiring check (all components) | ✓ 10/10 pass |

---

## 6. Remaining Study Infrastructure Gaps

| Item | Status |
|------|--------|
| Backend `POST /api/study/log` endpoint | Not yet built — localStorage fallback is active |
| Mohler batch evaluation (per-sample cllm/c5 scores) | Not yet run — critical for paper |
| IRB protocol for think-aloud + rubric edit task | Not yet written |
| Pilot study (2–3 participants before full run) | Not yet scheduled |
| SUS → rubric edit → think-aloud ordering | Needs to be finalised in protocol |

---

*All code is production-quality and ready for a pilot study run. The primary open question for this review is whether the causal attribution design (Q1–Q5 above) is methodologically sound enough to support the IEEE VIS "co-auditing interface" contribution claim.*
