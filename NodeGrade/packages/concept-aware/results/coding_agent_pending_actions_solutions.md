# Pending Coding Agent Actions & Solutions (ConceptGrade Paper 2)

This document outlines the 6 open questions from `conceptgrade_gemini_paper2_v3.md` and provides concrete, actionable technical solutions for the coding agent to implement in the next iteration.

---

## 1. Q7 Confound: Condition A Signal Leak via Matched-Frequency Chart
**Issue:** If the concept frequency chart displays the same concepts that the trace would have flagged as `CONTRADICTS`, a Condition A participant might add those concepts simply because they are highly frequent. This confounds the semantic alignment (H2) results, as it simulates the AI trace effect.
**Proposed Solution:**
*   **Action:** Decouple or mask the AI-derived matching state from Condition A.
*   **Implementation:** In the `InstructorDashboard` or `ConceptFrequencyChart` components, if `condition === 'A'`, either hide the chart entirely OR ensure the chart only shows "total student frequency" without the trace-specific `CONTRADICTS` or `expected` vs `missing` highlighting. 
*   **Target Files:** `InstructorDashboard.tsx`, `ConceptFrequencyChart.tsx`

## 2. Layout Cache: Dataset-Switch Clearing, Memory Growth & Stale-Ref Risk
**Issue:** The module-level `layoutCache` introduced in Q11 persists forever. If a user switches datasets, node coordinate positions might erroneously map to a different dataset's nodes if they share the same `conceptId`. Additionally, a module-level variable can cause memory growth and stale UI references across React component lifecycles.
**Proposed Solution:**
*   **Action:** Scope the layout cache to the dashboard's lifecycle and key it by dataset.
*   **Implementation:** Move the `layoutCache` out of the module scope and into the `DashboardContext` (or use a `useRef` at the `InstructorDashboard` root). Update the cache structure to be a nested dictionary: `cache[dataset][conceptId]`. This ensures coordinates are safely isolated per dataset and automatically cleared if the dashboard unmounts.
*   **Target Files:** `ConceptKGPanel.tsx`, `DashboardContext.tsx`

## 3. `xai_pill_hover`: Dwell Time vs Enter-Only & Debounce Need
**Issue:** Triggering an event immediately on `onMouseEnter` will log spurious events (spam) when a user simply moves their cursor across the screen. We only care about intentional reading (dwell time).
**Proposed Solution:**
*   **Action:** Implement a dwell-time threshold and record the duration.
*   **Implementation:** Use a `useRef` to store the hover start time and a timeout ID. On `onMouseEnter`, start a timeout (e.g., 500ms). If `onMouseLeave` fires before 500ms, clear the timeout (cancel the log). If it fires after, log the `xai_pill_hover` event including a `dwell_ms` payload calculated via `Date.now() - startTime`.
*   **Target Files:** `ScoreProvenancePanel.tsx` (or wherever XAI pills are rendered)

## 4. `participant_mean_ratio`: Weighted vs Unweighted & Closure Scoping
**Issue:** The current unweighted participant mean gives a participant with 1 edit the same influence on the metric as a participant with 20 edits, potentially skewing results due to high variance in low-edit sessions. Additionally, Python closure scoping for `rows` within `aggregate_by_condition` might be fragile.
**Proposed Solution:**
*   **Action:** Fix scoping and provide a minimum-edit threshold.
*   **Implementation:** 
    1.  Update the helper signature to explicitly accept the dataset: `def participant_mean_ratio(rows, window_key):` to avoid late-binding closure bugs.
    2.  Add a minimum edit filter (e.g., `if n_edits >= 3:`) to exclude noisy single-edit outliers from the primary H1 estimator, or explicitly calculate and log both an unweighted and a weighted mean so the researchers can report the difference.
*   **Target Files:** `analyze_study_logs.py`

## 5. `logBeacon` + React 18 Strict Mode Double-Cleanup Risk
**Issue:** React 18 Strict Mode intentionally unmounts and remounts components immediately on initial render. If `logBeacon` is attached to a `useEffect` cleanup function (like `answer_view_end`), it will fire a spurious log event with ~0ms dwell time.
**Proposed Solution:**
*   **Action:** Filter out strict-mode lifecycle blips.
*   **Implementation:** In the `useEffect` that calls `logBeacon` on cleanup, calculate the duration (`Date.now() - mountTime`). If the duration is less than a minimum threshold (e.g., `< 50ms`), abort the beacon payload. This successfully silences the React 18 Strict Mode unmount/remount cycle while preserving valid user exits.
*   **Target Files:** `StudentAnswerPanel.tsx` (or wherever `logBeacon` is used for view tracking)

## 6. `rows` Closure Scoping in `aggregate_by_condition`
**Issue:** Python's late-binding in closures can lead to bugs if the `rows` variable mutates or if the helper is passed around outside its immediate lexical block.
**Proposed Solution:**
*   **Action:** Refactor all local helper functions inside `aggregate_by_condition` (`mean_of`, `std_of`, `participant_mean_ratio`) to accept `rows` as an explicit parameter rather than relying on implicit outer-scope access.
*   **Implementation:** `def mean_of(rows: list[dict], key: str) -> Optional[float]:`. Update all call sites within the function.
*   **Target Files:** `analyze_study_logs.py`