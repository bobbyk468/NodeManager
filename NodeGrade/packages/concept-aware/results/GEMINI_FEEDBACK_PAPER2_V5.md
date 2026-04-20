# Gemini Review Answers — ConceptGrade Paper 2 v5

Based on the review of `conceptgrade_gemini_paper2_v5.md`, here are the technical evaluations, recommendations, and drafted content for the 5 new open questions (Q-G through Q-K).

---

## 5.1 Condition A `StudentAnswerPanel` — Answer Severity Labels

### Q-G: Severity Labels in `StudentAnswerPanel` for Condition A
**Finding:** If the `StudentAnswerPanel` displays AI-derived severity chips (Critical miss, Moderate miss, etc.) in Condition A, it re-introduces the confound that was just removed from the heatmap. The control condition should not have access to the AI's granular diagnostic labeling of concepts.
**Recommendation:** Yes, the severity `Chip` labels must be neutralized in Condition A. 
*   **Action:** In `StudentAnswerPanel.tsx`, check `isConditionA`. If true, replace the specific severity labels with a neutral indicator like "Not reviewed", or simply hide the severity chip entirely and only show the score/quartile. 
*   **Verification:** Ensure that clicking a row in the `ScoreSamplesTable` (which still works in Condition A) does not reveal AI-derived concept-level severity in the resulting `StudentAnswerPanel` view.

---

## 5.2 `answer_view_start` `capture_method` Field

### Q-H: Differentiating Start vs. End Events
**Finding:** Relying on `capture_method: null` as an implicit indicator of a "start" event is brittle. If a future update changes how `capture_method` is populated, or if a malformed payload is sent, joining start and end events could fail or produce Cartesian products.
**Recommendation:** Make the event type explicit in the payload.
*   **Action:** Do not use `capture_method` to distinguish start from end. The `event_type` field itself (`answer_view_start` vs `answer_view_end`) is the correct primary differentiator. However, to keep the schema clean, `answer_view_start` should explicitly send `capture_method: 'start'` instead of `null` so the column has consistent semantics (describing the *context* of the capture).

---

## 5.3 `causal_attribution_rate_*` — Condition A Interpretation

### Q-I: Reporting Condition A Rates in Table 3
**Finding:** Reporting `0.000` for Condition A's causal attribution rate is mathematically true (zero aligned edits / total edits) but conceptually misleading. It implies an observed lack of effect rather than a structural impossibility (since Condition A literally cannot perform the `CONTRADICTS` interaction required to trigger the timer).
**Recommendation:** Use **"N/A"** in the paper's main table.
*   **Action:** In Table 3, report Condition A's rate as "N/A". Add a table footnote: *"N/A: Condition A educators do not receive trace explanations and therefore cannot perform the triggering CONTRADICTS interaction."* This clearly communicates the experimental design constraint to reviewers.

---

## 5.4 MisconceptionHeatmap Condition A — Interaction Path Audit

### Q-J: Heatmap Interaction Path Isolation
**Finding:** You noted that the new Condition A heatmap early-returns a static Box without calling `onCellClick`. This means clicking the aggregated list does *not* update `selectedConcept` or open the `StudentAnswerPanel` filtered by that concept.
**Recommendation:** **This is the correct and intended isolation.**
*   **Rationale:** If Condition A could click an aggregated concept and see a filtered list of student answers that *failed* that concept, they could easily reverse-engineer the AI's matching logic by reading those answers. Breaking this interaction path in Condition A is necessary to prevent them from using the dashboard as an ad-hoc trace tool. They can still read student answers via the `ScoreSamplesTable` (which is not filtered by a specific missing concept).

---

## 5.5 Paper Methods Section — Condition Isolation Statement

### Q-K: Methods Paragraph (≤100 words)
Here is the drafted paragraph for Section 4.2 "Study Conditions" explaining the visual and interactive isolation:

> **Draft:** 
> "To establish a strict baseline for H2 (semantic alignment), Condition A provides standard grading analytics while strictly isolating all AI-derived diagnostic signals. The Concept Frequency chart renders in a uniform color, suppressing the AI's expected-concept encoding. The Misconception Heatmap is downgraded to a static, aggregated list, removing severity color-coding and disabling drill-down filtering. Furthermore, student answer views omit AI-generated severity labels. Condition A educators retain full capability to read student answers, view score distributions, and edit the rubric, ensuring observed differences in rubric concept selection are causally attributable to the trace explanations provided exclusively in Condition B." (97 words)