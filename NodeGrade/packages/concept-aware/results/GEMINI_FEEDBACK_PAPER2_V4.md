# Gemini Review Answers — ConceptGrade Paper 2 v4

Based on the review of `conceptgrade_gemini_paper2_v4.md`, here are the technical evaluations and recommendations for the 6 open questions (Q-A1 through Q-F) concerning the experimental design, statistical framing, and system behavior.

---

## 4.1 Condition A Isolation — Completeness

### Q-A1: Heatmap Severity Labels in Condition A
**Finding:** If the "severity" labels (critical/moderate/minor/matched) are derived from the exact same AI concept-matching algorithm that powers the `CONTRADICTS` trace, then showing this in Condition A **is a confound**. It provides educators with a prioritized list of which concepts the AI thinks are missing (critical), essentially leaking the semantic trace signal through a different visual channel.
**Recommendation:** For Condition A, the heatmap should be downgraded to a simple "Student Answer vs. Concept Occurrence" matrix (e.g., binary presence/absence or raw TF-IDF score) without the AI-derived severity color-coding. If severity must be shown, it should be based on a non-AI heuristic (like raw word count) to preserve the control condition's baseline status.

### Q-A2: `total_misconceptions` in Class Summary
**Finding:** Showing a single aggregated integer (e.g., "20 students have missing concepts") does not leak *which* concepts are missing. It provides class-level context without breaking the semantic isolation.
**Recommendation:** **Acceptable.** Keep this metric in Condition A. As long as it remains a scalar aggregate and does not provide a breakdown of the specific concepts, it poses no risk to the H2 semantic alignment baseline.

---

## 4.2 Statistical Framing & Pre-registration

### Q-B: `min_edits=3` Pre-Registration Framing
**Finding:** Introducing a threshold (`min_edits=3`) that was not explicitly defined in the original pre-registration document is a classic "researcher degree of freedom." If you frame this post-hoc filter as your "Primary" result, rigorous IEEE VIS reviewers will flag it as p-hacking or a deviation from the pre-registration protocol.
**Recommendation:** **You must swap the framing.** 
1. The `participant_mean_ratio` with **all participants (`min_edits=1`)** MUST be reported as the "Primary Pre-Registered Estimator" in your Results section.
2. The `min_edits=3` and edit-weighted variants should be introduced in a dedicated "Sensitivity & Robustness Analysis" subsection. 
*Suggested Paper Language:* "To ensure our primary pre-registered findings were not skewed by high-variance outlier sessions (educators making only 1-2 total edits), we conducted a post-hoc sensitivity analysis restricted to high-engagement sessions (≥ 3 edits). The causal attribution trend held stable..."

---

## 4.3 Dwell Time Calibration

### Q-C: 500ms Dwell Threshold Citation
**Finding:** 500ms is a highly defensible threshold for intentional cognitive processing (reading/comprehension) versus incidental cursor transit. 
**Recommendation:** Use the following citations to defend the 500ms threshold in your methodology:
1. **Primary HCI/Mouse-tracking:** *Chen, M. C., Anderson, J. R., & Sohn, M. H. (2001). What can a mouse cursor tell us more?: correlation of eye/mouse movements on web browsing.* (Establishes the link between mouse hover and visual attention/fixation).
2. **Cognitive/Reading duration:** *Just, M. A., & Carpenter, P. A. (1980). A theory of reading: From eye fixations to comprehension.* (Establishes that meaningful semantic processing and "eye-mind" fixations typically range from 250ms to 500ms+).
*Suggested Paper Language:* "We applied a 500ms dwell-time gate to `xai_pill_hover` events to filter out incidental cursor transits, capturing only intentional semantic processing in alignment with established eye-mind cognitive thresholds (Just & Carpenter, 1980; Chen et al., 2001)."

---

## 4.4 System Behavior & Cache Management

### Q-D: Layout Cache — Dataset Switch Clearing
**Finding:** Keying the cache by `dataset::conceptId` completely eliminates cross-contamination. Since the map implements an LRU eviction policy capped at 50 items (consuming a negligible ~8KB of memory), allowing stale entries from previous datasets to persist is harmless.
**Recommendation:** **No code change needed.** Preserving the cache across dataset switches provides a better UX if the educator navigates back to a previous dataset. The bounded LRU map ensures memory safety automatically.

### Q-E: `logBeacon` `capture_method` Field
**Finding:** Distinguishing between an actual network dispatch and a local-storage-only fallback is crucial for data quality auditing. If a session is missing its end event, knowing that it fell back to `ls_only` explains the data loss.
**Recommendation:** **Implement the distinction.** Update the `capture_method` payload to explicitly log `'beacon_sent'` when `navigator.sendBeacon` is called, and `'beacon_ls_only'` when it skips the network call due to `studyApiBase` being undefined.

### Q-F: Python Syntax & Closure Scoping Verification
**Finding:** Defining 4 inner functions (like `mean_of`, `std_of`) inside a `for` loop of size 2 (for Conditions A and B) carries absolutely zero measurable performance penalty in Python. The interpreter garbage-collects the old function objects automatically. Furthermore, because you explicitly pass `cond_rows` as an argument to these helpers now, there is zero risk of closure late-binding bugs.
**Recommendation:** **Confirmed safe.** The code is perfectly idiomatic for analysis scripts and completely safe from both performance and scoping perspectives.