# Gemini Review Answers — ConceptGrade Paper 2 v6

Based on the review of `conceptgrade_gemini_paper2_v6.md`, here are the technical evaluations and recommendations for the 3 remaining lower-priority polish questions (Q-L, Q-M, Q-N) before the user study launches.

---

## 6.1 `ScoreProvenancePanel` — Score Bars in Condition A

### Q-L: "ConceptGrade" Bar Label and Color in Condition A
**Finding:** Showing a distinct, highlighted green bar labeled "ConceptGrade" to Condition A participants introduces a subtle confound. It signals the existence of a novel, likely AI/KG-based scoring system (ConceptGrade) that produced a different score than the LLM or Human. This might prompt them to look for AI signals that aren't there, or alter their trust in the baseline dashboard.
**Recommendation:** Neutralize the label and color in Condition A.
*   **Action:** In `ScoreProvenancePanel`, if `isConditionA` is true, change the label from "ConceptGrade" to something neutral like "System Score" or simply "Score" if the others are "Human" and "LLM". Change the color from the highlighted green (`#16a34a`) to a neutral blue or grey that matches the dashboard's baseline aesthetic.

---

## 6.2 `analyze_study_logs.py` — Condition A H2 Semantic Alignment Rate

### Q-M: H2 Condition A Rate — `N/A †` vs Placebo
**Finding:** This is a crucial statistical distinction. Condition A participants *do not have* a `session_contradicts_nodes` list because they cannot interact with the trace. Therefore, they cannot manually align with concepts they were never shown. The denominator for the alignment rate (edits made after a trace interaction) is 0. 
However, testing if Condition A's blind edits coincidentally align with the concepts the AI *would* have flagged is a powerful placebo test.
**Recommendation:** **Report it as a Placebo Baseline, not N/A.**
*   **Action:** You should compute a "Placebo Alignment Rate" for Condition A. To do this, when analyzing a Condition A session, fetch the `CONTRADICTS` nodes that the AI *would* have generated for the dataset being graded, and test if the educator's manual edits aligned with that hidden list.
*   **Reporting:** In Table 4, report Condition B as "Semantic alignment rate" and report Condition A as "Placebo alignment rate (coincidental)". This provides a true baseline for H2: "Did Condition B educators align with the AI significantly more than Condition A educators who edited the rubric blind?" If you just put N/A, you lose your control group for H2.

---

## 6.3 Pilot Study Threshold

### Q-N: Pilot GO/NO-GO Gate Flag
**Finding:** Adding an automated pilot gate flag directly into the analysis script is an excellent way to enforce pre-registered protocols. It removes human judgment from the "continue or abort" decision after the pilot phase.
**Recommendation:** **Implement the `--pilot` flag.**
*   **Action:** Add a `--pilot` boolean argument to `analyze_study_logs.py`. If passed, evaluate the `task_completion_rate`. If `task_completion_rate > 0.50`, print a prominent green `[PILOT GATE] GO: Completion rate {rate} > 0.50` message. If it fails, print a red `NO-GO` message advising structural review of the task before launching the full study. This adds rigor and automation to your methodology.