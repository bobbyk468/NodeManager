# ConceptGrade Coding Agent Guide: Research Evaluation & Testing Infrastructure

## 1. Context and Objective

As an AI coding agent working on this repository, your definition of "testing" must shift. We are preparing **Paper 2 for the IEEE VIS VAST track**. Therefore, "testing" does not primarily mean standard software unit/integration testing (like Jest or PyTest).

In this phase, **Testing = System Evaluation for Research**.

Your objective is to implement the frontend and backend infrastructure required to execute two specific research evaluation methods:

1. **Data-Driven Case Studies (Usage Scenarios):** UI states that allow the researcher to load 600+ dataset batches (Mohler, Kaggle, DigiKlausur) to take narrative screenshots.
2. **The Co-Auditing Benchmark (User Study):** Telemetry and data seeding required for the N=30 controlled user study.

Do not write standard unit tests unless explicitly asked. Focus on data pipelines, static caching, UI rendering of edge cases, and event logging.

---

## 2. Part A: Infrastructure for "Data-Driven Case Studies"

The researcher needs to evaluate the system by loading massive datasets to prove visual scalability.

**Agent Tasks:**

- **Dataset Loading Modularity:** Ensure the React frontend and NestJS/Python backend can cleanly swap between datasets via URL parameters or environment variables (e.g., `?dataset=mohler`, `?dataset=kaggle_asag`, `?dataset=digiklausur`).
- **Zero-Grounding Graceful Rendering:** DeepSeek-R1 traces exhibit 97.7% zero-grounding degeneracy. Ensure the UI (specifically `VerifierReasoningPanel.tsx` and the `SummaryBar`) handles `kg_nodes: []` gracefully without throwing errors. It should display a clear "No Domain Grounding" visual indicator (e.g., red status, empty graph) rather than a blank panel.
- **Static TRM Caching:** All TRM metrics must remain strictly decoupled from live LLM calls during the UI evaluation. Ensure `generate_trm_cache.py` outputs a static `data/{dataset}_trm_cache.json` and the backend serves this cache directly.

---

## 3. Part B: Infrastructure for "The Co-Auditing Benchmark"

For the N=30 user study, we are evaluating how the human-AI team navigates pedagogical edge cases. You must implement **Strategic Seeding** into the data layer without breaking the ecological validity of the user's dashboard foraging.

### 3.1 Benchmark Seed Configuration

The seed configuration is split into two files:

**Backend (Python analysis):** `packages/concept-aware/data/benchmark_seeds.json`
Maps `student_answer_id` to trap type + rationale for post-study analysis.

**Frontend (TypeScript runtime):** `packages/frontend/src/utils/benchmarkSeeds.ts`
Provides `getBenchmarkCase(id)` lookup used at logging time to tag events.

### 3.2 Four Pedagogical Trap Types

| Trap Type | Pattern | Study Metric |
|-----------|---------|-------------|
| `fluent_hallucination` | High `trace_gap_count`, reads well but skips concepts | Did Condition B catch the leap? Rubric edit within 60s of viewing. |
| `unorthodox_genius` | Low AI score, human gave high score — correct but colloquial vocab | Did Condition B override the AI score? TC code = 3 or 4. |
| `lexical_bluffer` | Many `CONTRADICTS` steps, AI still overestimates | Did Condition B dwell longer and add a contradicting concept to rubric? |
| `partial_credit_needle` | Mixed support/contradict trace; missing concept visible in KG only | Time-to-insight: dwell gap B−A for SOLO=2 band. |

### 3.3 Event Payload Extension

When an educator naturally clicks a seeded answer via the Concept Heatmap, the `benchmark_case` field is injected into the event payload automatically — no UI change visible to the participant.

```typescript
// In AnswerDwellPayload (studyLogger.ts):
benchmark_case?: BenchmarkCase;  // undefined for non-seeded answers
answer_content_hash?: string;    // FNV-1a hash of student answer text (FERPA compliance)
```

### 3.4 Tagging Mechanism

The lookup happens in `StudentAnswerPanel.tsx` at the moment of `handleSelectStudent`:

```typescript
import { getBenchmarkCase } from '../../utils/benchmarkSeeds';

// Inside handleSelectStudent:
const benchmarkCase = getBenchmarkCase(answer.id);
const startPayload: AnswerDwellPayload = {
  // ...existing fields...
  benchmark_case: benchmarkCase,
  answer_content_hash: fnv1a(answer.student_answer),
};
```

---

## 4. Telemetry & Logging Rules (The "Assertions")

In this research context, the telemetry logs are our "test assertions." If the logging fails, the study fails.

**Agent Coding Rules for `studyLogger.ts` and Backend Log Routes:**

1. **Dwell Time is Sacred:** Use React `useEffect` cleanup functions combined with `navigator.sendBeacon()` (with the correct `Blob` MIME type `application/json`) to log `answer_view_end` events. `window.beforeunload` is unreliable and strictly prohibited for critical dwell-time capture.

2. **No On-The-Fly Math:** The backend `POST /api/study/log` route must act as a dumb pipe. Do not compute `chain_pct` or `topological_gap_count` on the fly. These must be joined from the static `trm_cache.json` either before the payload is sent or during post-study Python analysis via `analyze_study_results.py`.

3. **Log All Bounces:** Do not implement any filtering logic (e.g., "ignore clicks under 2 seconds") in the frontend or backend logger. Capture 100% of interaction events; filtering occurs strictly in the Python analysis phase (`dwell_ms < 2000` bounce filter in `analyze_study_results.py`).

4. **Privacy/FERPA Compliance:** Never include raw student answer text in the log payload. Send only `student_answer_id` and `answer_content_hash` (FNV-1a hash of the answer text). Raw text stays server-side and is never transmitted in event logs.

5. **Beacon MIME Type:** `sendBeacon()` must use `new Blob([JSON.stringify(event)], { type: 'application/json' })`. Do not use `sendBeacon(url, JSON.stringify(event))` — this sends as `text/plain` and may be rejected by the NestJS JSON body parser.

---

## 5. Current Implementation Status

| Feature | File | Status |
|---------|------|--------|
| `answer_view_start/end` events | `studyLogger.ts` | ✅ Implemented |
| `sendBeacon()` with Blob | `studyLogger.ts` | ✅ Implemented |
| Dwell useEffect + stable closure | `StudentAnswerPanel.tsx` | ✅ Implemented |
| `studyCondition` prop wiring | `InstructorDashboard.tsx` | ✅ Implemented |
| `tracePanelOpen` via DashboardContext | `DashboardContext.tsx` + `ScoreSamplesTable.tsx` | ✅ Implemented |
| `kgPanelOpen` prop wiring | `InstructorDashboard.tsx` | ✅ Implemented |
| TRM cache generation | `generate_trm_cache.py` | ✅ Generated (300 entries) |
| Zero-grounding "No Domain Grounding" banner | `VerifierReasoningPanel.tsx` | ✅ Implemented |
| `benchmark_case` tagging | `benchmarkSeeds.ts` + `StudentAnswerPanel.tsx` | ✅ Implemented |
| `answer_content_hash` (FERPA) | `studyLogger.ts` + `StudentAnswerPanel.tsx` | ✅ Implemented |
| Post-study analysis script | `analyze_study_results.py` | ✅ Implemented |
| Backend dumb-pipe logging | `study.service.ts` | ✅ Implemented |

---

## 6. Key Data Files

| File | Purpose |
|------|---------|
| `packages/concept-aware/data/benchmark_seeds.json` | Trap case registry (Python analysis) |
| `packages/frontend/src/utils/benchmarkSeeds.ts` | Frontend trap lookup (TypeScript) |
| `packages/concept-aware/data/digiklausur_trm_cache.json` | Pre-computed TRM metrics (300 entries) |
| `packages/concept-aware/data/study_logs/*.jsonl` | Per-session event logs |
| `packages/concept-aware/data/study_logs/qualitative_codes.json` | Post-coding transcript codes |
| `packages/concept-aware/data/study_logs/sus_scores.json` | SUS questionnaire scores |
| `packages/concept-aware/analyze_study_results.py` | Full statistical analysis pipeline |

---

## 7. Running the Analysis

```bash
# Dry-run with synthetic N=30 data:
cd packages/concept-aware
.venv/bin/python analyze_study_results.py --synthetic

# Real data after study is complete:
.venv/bin/python analyze_study_results.py

# Output: data/study_analysis_results.json
```

---

**Document version:** April 17, 2026  
**Implementation status:** All items ✅ complete
