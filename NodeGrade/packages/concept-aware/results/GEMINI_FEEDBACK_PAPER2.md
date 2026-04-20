# Gemini Code Review Feedback — ConceptGrade Paper 2

Based on the review of the remaining open questions from `conceptgrade_gemini_paper2_v2.md`, here are my findings and recommendations:

## Priority 1 (Blocking for IRB/Publication)

### Q6: K over-estimation from last-edit's `session_contradicts_nodes`?
**Finding:** In `analyze_study_logs.py`, `K` (number of flagged concepts) is calculated using `rubric_edits[-1]['session_contradicts_nodes']`. Since the hypergeometric test evaluates the *session as a whole* (where `n` is the total number of manual edits in the session, and `k` is the total aligned edits), using the final set of flagged concepts is an approximation. However, if an educator made an edit *before* a concept was flagged, that concept shouldn't theoretically be in `K` for that specific edit. By over-estimating `K`, the test becomes strictly **more conservative** (it's mathematically harder to achieve a low p-value when `K` is larger). 
**Recommendation:** For a more precise model, compute a per-edit hypergeometric p-value using the `session_contradicts_nodes` exactly at the time of each edit, and then combine them (e.g., using Fisher's method). Alternatively, add a footnote in the paper stating that using the final session `K` acts as a conservative lower-bound estimator for the null model.

### Q7: Condition A RubricEditorPanel — could UI accidentally leak trace signals?
**Finding:** Yes. Condition A participants see the "Concept Frequency" chart and other summary metrics. If the frequency chart highlights the exact same concepts that the trace would have flagged as `CONTRADICTS`, a Condition A participant might add those concepts to the rubric simply because they are highly frequent, simulating the semantic alignment we're trying to attribute to the trace.
**Recommendation:** This is a potential confounding variable for H2. You should empirically check if Condition A participants are adding concepts that appear at the top of the frequency chart. If so, you may need to control for "concept frequency" in your semantic alignment model to isolate the specific causal effect of the `CONTRADICTS` trace interaction.

## Priority 2 (Data Quality)

### Q1: Dual-write failure mode — can localStorage and POST fail silently?
**Finding:** Yes. If a participant uses a restrictive browser environment (like Safari in strict Private Browsing mode, which can set localStorage quota to 0) AND they have an aggressive ad-blocker or tracking prevention extension that blocks the `/api/study/log` endpoint, both writes will fail. Since the `catch()` on the `fetch` is empty, this fails silently, leading to permanent data loss for that participant.
**Recommendation:** Add a `try/catch` around `safeLocalStorageAppend`. If both the local storage append and the network request fail, present a fatal error UI overlay to the participant ("Logging error: Please disable ad-blockers to participate in this study") to prevent them from completing a study session whose data cannot be recorded.

### Q3: Missing event coverage — unlogged interaction paths?
**Finding:** Dragging KG nodes and hovering over concept pills in the XAI provenance panel represent active cognitive engagement with the AI explanation. Not logging these means you are under-counting "trace interaction time."
**Recommendation:** Add `kg_node_drag` and `xai_pill_hover` to `StudyEventType` and log them (using a debounce for hovers to prevent event spam). This will provide a richer picture of how participants explore the explanation space.

## Priority 3 (UX / Publication Polish)

### Q2: FERPA compliance — is FNV-1a 32-bit sufficient?
**Finding:** A 32-bit hash has a non-negligible collision risk due to the Birthday Paradox (approx. 50% chance of collision at only ~77,000 items). While a single dataset may not hit this, it weakens the technical claim of cryptographic uniqueness for FERPA compliance.
**Recommendation:** Upgrade to a 64-bit FNV-1a hash, or a truncated SHA-256 hash. This takes only a few lines of code and provides bulletproof mathematical certainty for the IRB.

### Q8: Condition validation — silent accept of invalid condition strings?
**Finding:** Casting `condition as StudyCondition` in TypeScript provides no runtime safety. A typo like `?condition=C` in the URL will propagate 'C' throughout the app and logs, potentially breaking charts or polluting the analytical dataset.
**Recommendation:** Add a strict runtime guard in `InstructorDashboard.tsx`: 
`const validCondition = ['A', 'B'].includes(condition) ? condition : 'B';`

### Q11: KG layout persistence per conceptId?
**Finding:** Resetting the layout every time `ConceptKGPanel` mounts destroys the user's mental map if they toggle between concepts.
**Recommendation:** Store the node position state keyed by `conceptId` in `DashboardContext` or a local ref cache within a parent component, so that when a user returns to a previously viewed concept, the nodes remain where they originally dragged them.