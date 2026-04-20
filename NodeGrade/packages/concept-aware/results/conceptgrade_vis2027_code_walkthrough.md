# ConceptGrade — Code Walkthrough & VIS 2027 Readiness

This document provides a detailed code walkthrough of the ConceptGrade project, focusing on the instructor analytics dashboard (`packages/concept-aware`, `packages/backend/src/visualization`, `packages/frontend/src/components/charts`, `packages/frontend/src/pages`). The goal is to identify architectural issues, technical debt, hardcoded values, performance bottlenecks, and incomplete features that could impact an IEEE VIS 2027 paper submission or a formal user study.

---

## 1. Architecture & Data Flow

ConceptGrade uses a **static-file → NestJS adapter → React (MUI + Recharts)** pipeline. A separate Python evaluation stack produces JSON files consumed by the backend.

### Strengths for VIS 2027
*   **Decoupled Visualization Specs:** The backend sends explicit `VisualizationSpec` objects. This decouples chart layout from raw evaluation rows, which is excellent for a systems paper narrative.
*   **Study-Oriented Logging:** The `studyLogger.ts` schema is exceptionally thorough for HCI telemetry, capturing multi-window causal attribution, trace gap counts, and grounding density.
*   **mtime-Aware Caching:** `VisualizationService` caches JSON files and invalidates them based on file modification times, supporting iterative research without server restarts.

### Risks & Technical Debt
*   **File-Backed "Database":** The system relies entirely on reading JSON files from disk (`packages/concept-aware/data/`). While fine for a controlled lab study, it lacks transactions and concurrent multi-user support.
*   **Path Resolution Coupling:** `VisualizationService` resolves `DATA_DIR` relative to the compiled `__dirname` (`../../../../concept-aware/data`). Moving the `dist/` folder or changing the build process will break the application.
*   **Duplicate Taxonomies:** Bloom/SOLO mappings and color palettes are duplicated in TypeScript (`visualization.service.ts`) and Python (`renderer.py`, `generate_dashboard_extras.py`). Drift here risks inconsistent figures between the paper and the live UI.

---

## 2. Backend Visualization (`packages/backend/src/visualization`)

### Incomplete Aggregates
*   **Hardcoded Misconceptions:** In `buildClassSummary`, `total_misconceptions` is hardcoded to `0`. The "Class Overview" card never reflects the actual misconception volume from the evaluation rows.
*   **Default Statistics:** `wilcoxon_p` defaults to `1.0`. In the UI, a missing statistic is indistinguishable from a non-significant result unless the JSON explicitly provides it.

### Placeholder Visualizations
*   **Radar & Heatmap Empty States:** `buildStudentRadar` and `buildMisconceptionHeatmap` fall back to empty structures if `generate_dashboard_extras.py` hasn't been run (i.e., if `*_dashboard_extras.json` is missing). 
*   **Study Risk:** A participant might see "working" charts that are structurally empty. The study protocol *must* mandate running the extras script.

### Concept Drill-Down Logic (Linking & Brushing)
*   **Semantic Mismatch:** In `getConceptStudentAnswers`, the severity for missed concepts is inferred from *human_score thresholds* (e.g., `< 2.0 = minor`, `>= 3.5 = critical`), not from the actual misconception detector output.
*   **Irrelevant Students:** The filtering logic includes all samples where the concept is expected globally, rather than filtering by the specific `question_id`. Educators might see students who weren't even asked the relevant question, undermining trust in the brushing interaction (a key VIS claim).

### Trace Endpoint
*   `getSampleTrace` returns `null` (HTTP 204) if `*_lrm_traces.json` is absent. Condition B will silently lack the `VerifierReasoningPanel` content unless the LRM batch pipeline was run.

---

## 3. Frontend Charts & Pages (`packages/frontend`)

### Performance Bottlenecks
*   **Recharts Rendering:** Wrapping many charts in `ResponsiveContainer` on a single page causes multiple SVG layout passes. Dashboard context updates can trigger broad subtree re-renders.
*   **`ScoreSamplesTable`:** Expanding a row triggers two separate REST calls (XAI and trace) per sample. This is acceptable for tens of rows but will lag significantly for hundreds of rows during exploratory analysis.
*   **`BloomsBarChart`:** `XAxis` uses `interval={0}`, forcing all labels to render. This works for 6 Bloom levels but scales poorly if reused.

### UI & UX Issues
*   **Cross-Dataset Chart:** `CrossDatasetComparisonChart.tsx` returns `null` if there is only one dataset. The visualization simply vanishes, which looks like a broken UI during a pilot.
*   **Refresh Button No-Op:** In `InstructorDashboard.tsx`, the refresh icon calls `setSelectedTab((t) => t)`. This is a React state no-op and *does not* refetch the visualization JSON from the backend. Facilitators may falsely believe they refreshed cached data.
*   **Logging Semantics:** `chart_hover` is used for both hovering and some clicks (e.g., radar quartile clicks). This mixes interaction types in the logs, which could complicate pre-registered analyses.

---

## 4. Python Evaluation Pipeline (`packages/concept-aware`)

### Scientific Design Notes (Crucial for Paper)
*   **Scoring Blend:** In `conceptgrade/pipeline.py`, the composite score is blended as `0.05 * kg_score + 0.95 * holistic_score` before the verifier override. This is a very strong editorial decision (95% reliance on the LLM holistic score) that *must* be explicitly stated in the paper when discussing "KG-grounded" scoring.
*   **Temporary Comparator:** Bloom/SOLO prompts use a temporary `KnowledgeGraphComparator` even when the configured comparator is confidence-weighted. This saves tokens but must be documented if reviewers ask about weighting consistency.

### Operational Hardcoding
*   **File Paths:** `run_batch_eval_api.py` hardcodes `BATCH_DIR = "/tmp/batch_scoring"`. This is not portable across OSes or HPC environments.
*   **API Parameters:** The Gemini model ID (`gemini-2.5-flash`) and `RATE_LIMIT_SLEEP = 7` are hardcoded. These should be environment-driven for replication packages.
*   **Offline Lexicon:** `run_evaluation.py` uses hand-tuned keyword maps for offline mode. Mixing offline and live rows (e.g., after hitting rate limits) would corrupt benchmark numbers.

---

## 5. VIS 2027 Action Plan

To ensure the system is robust for a formal user study and a VIS 2027 submission, prioritize the following:

1.  **Fix the Refresh Button:** Update `InstructorDashboard.tsx` to actually refetch data from the API when the refresh icon is clicked.
2.  **Enforce Pipeline Completeness:** Create a single `Makefile` or `run_full_pipeline.sh` script that guarantees all sidecar JSONs (`extras`, `traces`) are generated before a study session begins.
3.  **Tighten Drill-Down Logic:** Update `getConceptStudentAnswers` to filter by `question_id` so educators only see relevant students. Fix the severity inference to use actual misconception data rather than score thresholds.
4.  **Clean Up Logging:** Differentiate `chart_hover` from `chart_click` in the frontend to ensure clean telemetry for the study analysis.
5.  **Document the Math:** Pre-register and explicitly document the 5%/95% scoring blend and the temporary comparator logic used in the Python pipeline.
6.  **Remove `/tmp` Hardcoding:** Update Python scripts to use a local `data/tmp/` directory or respect an environment variable to ensure cross-platform replicability.