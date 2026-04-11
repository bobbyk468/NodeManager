# ConceptGrade Visualization Dashboard — Implementation Guide

**Status:** Implemented in-repo (local workspace; not tied to a specific git revision)
**Goal:** Instructor-facing visual analytics dashboard for explainable AI grading (IEEE VIS 2027 VAST track — dates TBD per official CfP)

**QA — local:** [ConceptGrade_Dashboard_Manual_Test_Guide.md](./ConceptGrade_Dashboard_Manual_Test_Guide.md) · **QA — remote AI browser (tunnel URLs):** [ConceptGrade_Dashboard_E2E_Remote_Browser.md](./ConceptGrade_Dashboard_E2E_Remote_Browser.md) · **Status (done vs pending):** [ConceptGrade_Pending_vs_Implemented.md](./ConceptGrade_Pending_vs_Implemented.md)

**Latest recorded run (manual guide changelog):** 2026-04-08 — Comet AI browser on co-located localhost: **13 PASS**, **1 CONDITIONAL** (TC-UI-008: full “API down” `Alert` needs manual Nest stop; structured **404** for bad slug confirmed).

**Request E2E test run:** `cd packages/backend && npm run request:e2e-test` (or `request:e2e-test:full` with Vite check) — runs automated gates and prints copy-paste instructions for testers.

---

## Architecture Overview

```
packages/concept-aware/
  data/*_eval_results.json     ← cached evaluation results (the data source)
  generate_auto_kg_prompt.py   ← Phase 1: KG quality + validation
        ↓
packages/backend/src/visualization/
  visualization.service.ts     ← reads + adapts eval_results → VisualizationSpec
  visualization.controller.ts  ← REST API: GET /api/visualization/...
        ↓
packages/frontend/src/
  pages/InstructorDashboard.tsx  ← main dashboard page (/dashboard)
  components/charts/             ← Recharts charts + MUI per-sample table
  utils/studyLogger.ts           ← user study event logging
```

Data flows one-way: **Python eval results → NestJS adapter → React charts**. No live API calls are needed during dashboard use — all data is read from pre-computed JSON files.

---

## Phase 1: KG Quality Improvements

**File:** [generate_auto_kg_prompt.py](../generate_auto_kg_prompt.py)

### What was added

| Addition | Purpose |
|----------|---------|
| `REL_TYPE_REMAP` (20 entries) | Maps non-standard Gemini relationship types to canonical types (e.g. `STORES→HAS_PART`, `RESEMBLES→VARIANT_OF`, `LEADS_TO→PRODUCES`) |
| `GENERIC_CONCEPT_STOPLIST` (~40 terms) | Removes domain-generic concepts like "process", "method", "thing" that pollute KG matching signal |
| `validate_and_clean_kg()` | Cleans a raw Gemini KG response: fixes concept IDs (spaces→underscores), removes stop-words, remaps relationships, flags questions with <4 concepts for retry |
| `build_retry_prompt()` | Builds a focused re-prompt for questions that survived with too few concepts |
| `--process-response PATH` CLI arg | Point at a Gemini response JSON → produces cleaned `data/{dataset}_auto_kg.json` |
| `--max-retries INT` CLI arg | Controls how many retry passes to run (default: 1) |

### Usage

```bash
# Step 1: generate the initial prompt (unchanged from before)
python3.12 generate_auto_kg_prompt.py --dataset digiklausur

# Step 2: send /tmp/auto_kg_prompt_digiklausur.txt to Gemini
# Save response to /tmp/auto_kg_response_digiklausur.json

# Step 3: clean the response
python3.12 generate_auto_kg_prompt.py \
    --dataset digiklausur \
    --process-response /tmp/auto_kg_response_digiklausur.json

# Output:
#   data/digiklausur_auto_kg.json  (cleaned, validated)
#   /tmp/auto_kg_retry_digiklausur.txt  (if any questions need retry)
```

### What the cleaner does to each KG

1. Normalizes concept IDs: `"neural network"` → `"neural_network"`
2. Removes generic concepts: `"process"`, `"method"`, `"thing"`, etc.
3. Remaps non-standard relationship types to canonical 10-type vocabulary
4. Drops relationships referencing removed concepts or using completely unknown types
5. Prunes `expected_concepts` to only surviving concept IDs
6. Flags entries with <4 concepts as `_needs_retry` (these are excluded from final output)

---

## Phase 2 (Skipped)

Adding a 4th dataset was skipped — three datasets (1,239 answers) are sufficient for a VIS VAST paper. Effort is better invested in the frontend and user study.

---

## Phase 3: NestJS Backend API

**Directory:** [packages/backend/src/visualization/](../../backend/src/visualization/)

### Files

| File | Purpose |
|------|---------|
| `visualization.types.ts` | TypeScript interfaces: `VisualizationSpec`, `DatasetSummaryResponse`, `DatasetMetrics` |
| `visualization.service.ts` | Reads `*_eval_results.json`, adapts to 9 VisualizationSpec objects (7 data views + 2 extended placeholders) |
| `visualization.controller.ts` | REST controller at `@Controller('api/visualization')` |
| `visualization.module.ts` | NestJS module, imported in `AppModule` |

### API Endpoints

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/api/visualization/datasets` | `{ datasets: string[] }` |
| `GET` | `/api/visualization/datasets/:dataset` | `DatasetSummaryResponse` |
| `GET` | `/api/visualization/datasets/:dataset/specs` | `{ specs: VisualizationSpec[] }` |
| `GET` | `/api/visualization` | `{ datasets: DatasetSummaryResponse[] }` |

**Dataset names** correspond to filename prefixes of `*_eval_results.json` in `packages/concept-aware/data/`, **but only files that contain a non-empty `results[]` with per-sample `human_score`, `cllm_score`, and `c5_score`**. Ablation-style files such as `offline_eval_results.json` (aggregate metrics only) are **omitted** from `GET /api/visualization/datasets`. Typical dashboard datasets: `digiklausur`, `kaggle_asag`. To show Mohler-style batch data, add or generate `mohler_eval_results.json` (or any `*_eval_results.json`) in that schema.

### VisualizationSpec schema

Every spec shares this top-level shape (matching `visualization/renderer.py`):

```typescript
{
  viz_id: string        // unique identifier
  viz_type: 'bar_chart'|'heatmap'|'grouped_bar'|'radar'|'table'|'summary_card'|'concept_map'
  title: string
  subtitle: string
  data: Record<string, unknown>   // varies by viz_type — see table below
  config: Record<string, unknown>
  insights: string[]              // auto-generated text observations
}
```

### API specs (9 total)

**Primary (7)** — derived from per-sample `results[]`:

| `viz_id` | `viz_type` | Data fields | Source fields |
|----------|------------|-------------|---------------|
| `class_summary` | `summary_card` | `num_students`, `avg_score`, `c_llm_mae`, `c5_mae`, `mae_reduction_pct`, `wilcoxon_p`, `blooms_avg`, `solo_avg` | aggregate |
| `blooms_dist` | `bar_chart` | `bars[]{label, level, count, percentage, color}`, `x_label`, `y_label` | `bloom` per sample |
| `solo_dist` | `bar_chart` | same shape | `solo` per sample |
| `score_comparison` | `grouped_bar` | `students[]{student_id(bucket), cllm_mae, c5_mae, count}`, `metrics[]`, `labels{}` | `human_score`, `cllm_score`, `c5_score` |
| `concept_frequency` | `bar_chart` | `bars[]{label, concept, count, percentage, color}` — top 15 | `matched_concepts[]` per sample |
| `chain_coverage_dist` | `bar_chart` | `bars[]{label, count, percentage, color}` — 5 buckets 0-20%…80-100% | `chain_pct` per sample |
| `score_scatter` | `table` | `columns[]`, `rows[]{id, human_score, cllm_score, c5_score, cllm_error, c5_error, solo, bloom, chain_pct}` | all fields |

**Extended placeholders (2)** — always present so the frontend can render one code path; data is empty until the pipeline exports richer structures:

| `viz_id` | `viz_type` | Notes |
|----------|------------|--------|
| `student_radar` | `radar` | `dimensions: []`, `students: []` — `StudentRadarChart` shows empty state |
| `misconception_heatmap` | `heatmap` | `cells: []` — `MisconceptionHeatmap` shows empty state |

### Data path resolution

`VisualizationService` resolves the data directory at runtime:

```typescript
const DATA_DIR = path.resolve(__dirname, '../../../../packages/concept-aware/data');
```

This works from the compiled output at `dist/src/visualization/` → up 4 dirs → `NodeGrade/` → `packages/concept-aware/data/`. If you move the compiled output, update this path.

---

## Phase 3: React Frontend Dashboard

**Route:** `/dashboard` (also `/dashboard?condition=A` or `/dashboard?condition=B` for study mode)

### New files

| File | Purpose |
|------|---------|
| [src/common/visualization.types.ts](../../frontend/src/common/visualization.types.ts) | TS interfaces mirroring backend |
| [src/utils/studyLogger.ts](../../frontend/src/utils/studyLogger.ts) | Session-scoped localStorage event logger |
| [src/components/charts/BloomsBarChart.tsx](../../frontend/src/components/charts/BloomsBarChart.tsx) | Bloom's taxonomy bar chart |
| [src/components/charts/SoloBarChart.tsx](../../frontend/src/components/charts/SoloBarChart.tsx) | SOLO taxonomy bar chart |
| [src/components/charts/ConceptFrequencyChart.tsx](../../frontend/src/components/charts/ConceptFrequencyChart.tsx) | Horizontal bar chart: top 15 KG concepts |
| [src/components/charts/ScoreComparisonChart.tsx](../../frontend/src/components/charts/ScoreComparisonChart.tsx) | Grouped bar: C_LLM vs C5_fix MAE per score bucket |
| [src/components/charts/ChainCoverageChart.tsx](../../frontend/src/components/charts/ChainCoverageChart.tsx) | KG causal chain coverage distribution |
| [src/components/charts/ScoreSamplesTable.tsx](../../frontend/src/components/charts/ScoreSamplesTable.tsx) | Scrollable MUI table for `score_scatter` |
| [src/components/charts/StudentRadarChart.tsx](../../frontend/src/components/charts/StudentRadarChart.tsx) | 5-axis radar for up to 5 students |
| [src/components/charts/MisconceptionHeatmap.tsx](../../frontend/src/components/charts/MisconceptionHeatmap.tsx) | Concept × severity grid (MUI boxes) |
| [src/pages/InstructorDashboard.tsx](../../frontend/src/pages/InstructorDashboard.tsx) | Main dashboard page |

### Dashboard layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ConceptGrade — Instructor Analytics Dashboard            [↻]   │
│  Tabs: one per compatible *_eval_results.json (e.g. DigiKlausur, Kaggle ASAG) │
├──────────────────────────────────────────────────────────────── │
│  [Study Task Panel] — only if ?condition= param is present      │
├─────────────────────────────────────────────────────────────────│
│  N=120  │  C5 MAE=0.223  │  Baseline=0.330  │  -32.4%  │  p<0.001  │  r=0.97 │
├──────────────────────────────────────────────────────────────── │
│  💡 Insights (Alert bars)                                       │
├──────────────────────────────────────────────────────────────── │
│  Bloom's Distribution (md=6)  │  SOLO Distribution (md=6)       │
├──────────────────────────────────────────────────────────────── │
│  Score Comparison MAE (md=7)  │  Chain Coverage (md=5)          │
├──────────────────────────────────────────────────────────────── │
│  Concept Frequency — Top 15 (full width)                        │
├──────────────────────────────────────────────────────────────── │
│  Per-sample score table (score_scatter, scrollable)             │
├──────────────────────────────────────────────────────────────── │
│  Student Radar (md=6)         │  Misconception Heatmap (md=6)   │
├──────────────────────────────────────────────────────────────── │
│  [Export study log]  Session: abc12345                          │
└─────────────────────────────────────────────────────────────────┘
```

### Chart components

All chart components accept:

```typescript
interface Props {
  spec: VisualizationSpec   // the spec object from the API
  condition?: string         // 'A' or 'B' — for study event logging
  dataset?: string           // dataset name — for study event logging
}
```

Each component calls `logEvent(condition, dataset, 'chart_hover', { viz_id })` on `onMouseEnter` for study tracking.

### Visualization library

**Recharts 2.12.7** is used for bar/radar charts; the per-sample view uses **MUI `Table`**. Recharts was added to `package.json` and may be installed with yarn/npm in your environment. When yarn 4 is properly available, run:

```bash
yarn workspace @haski/ta-frontend add recharts
```

The package.json entry `"recharts": "^2.12.7"` is already present.

---

## Phase 4: User Study Scaffolding

### Study conditions

Navigate to `/dashboard?condition=A` or `/dashboard?condition=B`:

| Condition | What the instructor sees |
|-----------|--------------------------|
| `A` (Control) | Summary metric cards only (N, MAE, reduction %, Wilcoxon p) |
| `B` (Treatment) | Full dashboard: summary cards + Recharts views + per-sample table + radar/heatmap slots |

Both conditions show the **Study Task Panel** at the top when a `condition` param is present.

### Study Task Panel

Rendered when `?condition=` is in the URL:
- **Task prompt:** "Looking at the data for this class, which concept do students struggle with most? Which students would you prioritize for office hours, and why?"
- **Answer textarea:** MUI `TextField multiline rows={3}`
- **Confidence slider:** 1–5 scale, "How confident are you in your answer?"
- **Submit button:** logs the event to localStorage

### Event logging (`studyLogger.ts`)

Events are written to `localStorage['ng-study-log']` as a JSON array.

| Event | When | Payload |
|-------|------|---------|
| `page_view` | Dashboard mount | `session_id`, `is_study` |
| `tab_change` | Dataset tab switch | `dataset` |
| `task_start` | First focus on answer textarea | — |
| `task_submit` | Submit button clicked | `answer`, `confidence`, `time_to_answer_ms` |
| `chart_hover` | Mouse enters any chart | `viz_id` |

**Export:** The "Export study log (JSON)" button downloads the full session as:
```
study-log-{first-8-chars-of-session-id}.json
```

Collect this file from each participant and load into Python for analysis.

### Analyzing study logs

```python
import json, pandas as pd

with open("study-log-abc12345.json") as f:
    events = json.load(f)

df = pd.DataFrame(events)

# Time to task submission
submit = df[df.event_type == 'task_submit'].iloc[0]
start = df[df.event_type == 'task_start'].iloc[0]
print(f"Time to answer: {submit.elapsed_ms - start.elapsed_ms:.0f} ms")

# Charts hovered
hovers = df[df.event_type == 'chart_hover']['payload'].apply(lambda p: p['viz_id'])
print("Charts explored:", hovers.value_counts().to_dict())
```

---

## Running the dashboard

### Prerequisites

1. **Same port for API and frontend config.** NestJS uses **`process.env.PORT ?? 5000`** (`packages/backend/src/main.ts`); `.env` may set **5001**. The dashboard loads `public/config/env.development.json`; **`API` and `WS` must match** the port Nest logs on startup.
   ```bash
   cd packages/backend && npm run start:dev
   ```

2. Frontend dev server:
   ```bash
   cd packages/frontend && npx vite --host 0.0.0.0
   ```

3. Eval results: at least one `*_eval_results.json` under `packages/concept-aware/data/` with a non-empty `results[]` and per-sample scores (e.g. `kaggle_asag_eval_results.json`, `digiklausur_eval_results.json`). No live Gemini calls needed for viewing.

### Automated smoke test

1. **Confirm services are up** (backend required; add `--frontend` for UI work):

   ```bash
   cd packages/backend && npm run check:dashboard-test-env
   # with Vite:
   npm run check:dashboard-test-env -- --frontend http://localhost:5173
   ```

   From monorepo root: `yarn check:dashboard-test-env`. Combined check + smoke: `yarn test:dashboard` or `yarn test:dashboard:full` (includes frontend). Boot polling: `yarn test:dashboard:wait`.

2. **API contract** (after step 1 passes):

   ```bash
   cd packages/backend && npm run verify:visualization
   ```

   Optional: `python3 scripts/verify_visualization_api.py --base http://127.0.0.1:<PORT>` (match Nest’s port).

The verify script asserts a non-empty dataset list and **exactly 9** `visualizations` per dataset with the expected `viz_id` keys. See [ConceptGrade_Dashboard_Manual_Test_Guide.md](./ConceptGrade_Dashboard_Manual_Test_Guide.md) for the full prerequisite flow.

### Verification checklist

- [ ] `npm run check:dashboard-test-env` exits 0 (and with `--frontend http://localhost:5173` before UI checks)
- [ ] `npm run verify:visualization` exits 0
- [ ] `curl http://localhost:<PORT>/api/visualization/datasets` returns e.g. `{"datasets":["digiklausur","kaggle_asag"]}` (order may vary; `offline` omitted)
- [ ] `curl http://localhost:<PORT>/api/visualization/datasets/kaggle_asag` returns JSON with **9** `visualizations`
- [ ] Navigate to `http://localhost:5173/dashboard` — dataset tabs appear, charts and per-sample table render
- [ ] Navigate to `http://localhost:5173/dashboard?condition=A` — only summary cards visible, study panel shown
- [ ] Navigate to `http://localhost:5173/dashboard?condition=B` — charts, table, and radar/heatmap areas visible (latter two may show empty-state copy)
- [ ] Fill in study task, click Submit, click "Export study log" — JSON file downloaded with all events

---

## What's missing for IEEE VIS 2027

| Component | Status | Notes |
|-----------|--------|-------|
| Backend API + 9 spec types | ✅ Complete | 7 data-driven + 2 empty extended placeholders |
| Study condition scaffolding | ✅ Complete | |
| Recharts + MUI table dashboard | ✅ Complete | Per-sample `score_scatter` rendered as `ScoreSamplesTable` |
| Misconception Heatmap | ⚠️ Partial | Empty cells until pipeline exports `cells` / `y_labels` |
| Student Radar Chart | ⚠️ Partial | Empty until pipeline exports `dimensions` + `students` |
| Educator user study (full) | ❌ Not started | Recruit 10–15 instructors; IRB if at a university; run A/B study |
| VIS paper submission | ❌ Not started | IEEE VIS 2027 abstracts ~January 2027 |

The radar and heatmap always receive API specs; components show empty states until extended fields are populated (e.g. from `visualization/renderer.py` or a future pipeline export).
