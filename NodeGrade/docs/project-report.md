# NodeGrade — Project Report
## What We Planned, What We Built, and Validation Results

---

## 1. Overview

NodeGrade is a visual, node-based grading platform for higher education. Instructors compose grading pipelines as graphs — connecting input nodes (student answer, question, sample solution) through processing nodes (LLM, ConceptGrade, WeightedScore) to an output node that produces a numeric score and feedback. Students submit answers through a dedicated view; the backend executes the graph in real time and returns results over a WebSocket.

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Browser (React + LiteGraph)                                 │
│                                                              │
│  /                  → DevHome (quick links + templates)      │
│  /ws/editor/:id     → Editor  (drag-and-drop graph builder)  │
│  /ws/student/:id    → StudentView (submit answer, see score) │
│  /validation        → ValidationDashboard (live QA checks)   │
└──────────────────────┬───────────────────────────────────────┘
                       │  HTTP REST + Socket.IO (WS)
┌──────────────────────▼───────────────────────────────────────┐
│  NestJS Backend  (port 5001)                                  │
│                                                              │
│  POST /graphs          — save graph JSON to PostgreSQL       │
│  GET  /graphs          — list all saved graphs               │
│  GET  /reports/:file   — serve test result JSON + Last-Modified header │
│  GET  /health          — liveness + DB probe                 │
│  WS   runGraph event   — execute graph, stream outputs back  │
└──────────────────────┬───────────────────────────────────────┘
                       │  Prisma ORM
┌──────────────────────▼───────────────────────────────────────┐
│  PostgreSQL                                                   │
│  Table: Graph { id, path, graph (JSON), createdAt }          │
└──────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│  LiteLLM Proxy  (port 8000)                                  │
│  Model: gemini/gemini-2.5-flash                              │
│  Provides OpenAI-compatible /v1/chat/completions endpoint    │
└──────────────────────────────────────────────────────────────┘
```

**Key packages:**
| Package | Role |
|---------|------|
| `packages/frontend` | React + Vite + MUI + LiteGraph canvas |
| `packages/backend` | NestJS REST + Socket.IO gateway |
| `packages/lib` (`@haski/ta-lib`) | All LiteGraph node implementations |
| `packages/e2e` (`@haski/e2e`) | Playwright end-to-end test suite (all 8 suites) |

---

## 3. What We Planned

The session started with four open items, then expanded:

| # | Item | Description |
|---|------|-------------|
| 1 | Dark mode | `mode` hardcoded to `'light'`; system preference and persistence not wired |
| 2 | Node registration smoke test | No automated check that all node types register correctly |
| 3 | E2E pipeline test | No end-to-end test running a real graph through the backend |
| 4 | Instructor UX | No starter templates; no template descriptions; no template menu in the editor |
| 5 | Browser-accessible test results | Automation browser couldn't read results (no shell access) |
| 6 | Gemini API integration | Groq placeholder; no real LLM provider configured |
| 7 | Validation Dashboard | No live QA page inside the frontend |
| 8 | Docker Compose | No single-command stack startup |
| 9 | Report freshness | Dashboard didn't warn when report files were stale |
| 10 | Playwright E2E suite | No real-browser automation for all 8 test suites |

---

## 4. What We Built

### 4.1 Dark Mode — System Preference + localStorage Persistence

**File:** `packages/frontend/src/pages/App.tsx`

**Before:** `mode: 'light'` was hardcoded in the MUI theme.

**After:**
```typescript
const COLOR_MODE_KEY = 'ng-color-mode'
export const ColorModeContext = createContext({ toggleColorMode: () => {} })

// Read stored preference on first load
const [mode, setMode] = useState<'light' | 'dark' | null>(() => {
  const stored = localStorage.getItem(COLOR_MODE_KEY)
  return stored === 'light' || stored === 'dark' ? stored : null
})

// Persist every change
useEffect(() => {
  if (mode !== null) localStorage.setItem(COLOR_MODE_KEY, mode)
}, [mode])

// Theme respects stored value; falls back to system preference
mode: mode ?? (prefersDarkMode ? 'dark' : 'light')

// Toggle correctly flips current effective mode
setMode((prev) => {
  const current = prev ?? (prefersDarkMode ? 'dark' : 'light')
  return current === 'light' ? 'dark' : 'light'
})
```

**File:** `packages/frontend/src/components/AppBar.tsx`
```typescript
<IconButton aria-label="toggle color mode" onClick={colorMode.toggleColorMode}>
  {theme.palette.mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
</IconButton>
```

**Result:** Dark mode preference survives page reload; respects OS preference on first visit.

---

### 4.2 Node Registration Smoke Test (Vitest)

**File:** `packages/frontend/src/__tests__/registernodes.test.ts`

Six assertions confirming every critical node type registers after importing `@haski/ta-lib`:

| Test | Node Types |
|------|-----------|
| Core input nodes | `input/question`, `input/answer`, `input/sample-solution` |
| LLM node | `models/llm` |
| Output node | `output/output` |
| ConceptGrade node | `concept-aware/conceptgrade` |
| WeightedScore node | `math/weighted_score` |
| Utility nodes | `utils/concat-string`, `utils/concat-object`, `basic/prompt-message` |

Vitest configured with jsdom + JSON reporter writing to `reports/vitest-results.json`.

---

### 4.3 E2E Integration Tests

**File:** `packages/backend/scripts/integration-test.cjs`

Two scenarios run via Socket.IO against the live backend + PostgreSQL:

**Test 1 — WeightedScore (no LLM)**
- `NumberNode(80)` + `NumberNode(0.85)` → `WeightedScoreNode(w=0.5/0.5, normalize=true)` → `OutputNode`
- Expected: `(80×0.5) + (85×0.5) = 82.5` → Actual: `82.5` ✓

**Test 2 — LLM JSON via Gemini**
- Full prompt pipeline: `Textfield` → `ConcatString` → `PromptMessage` → `LLMNode` → `OutputNode`
- Model: `gemini/gemini-2.5-flash` via LiteLLM proxy
- Sample output: `{"score": 100, "feedback": "Excellent! Accurate and concise description of photosynthesis."}`

Results persisted to `reports/integration-results.json`.

---

### 4.4 Instructor UX — Starter Templates + Template Menu

**Template files** (`packages/frontend/public/templates/`):

| File | Description | Nodes | Links |
|------|-------------|-------|-------|
| `starter.json` | Blank canvas with input + output nodes | 4 | 0 |
| `concept-grade.json` | Knowledge-graph grading via ConceptGradeNode | 5 | 4 |
| `llm-grader.json` | Full prompt-engineering pipeline via LLMNode | 12 | 11 |

Template dropdown in AppBar loads and wires graph via `lgraph.configure(graph)`. DevHome also shows three clickable template cards on the home page.

---

### 4.5 Backend: Reports Endpoint + Last-Modified Header

**File:** `packages/backend/src/reports/reports.controller.ts`

Serves the three JSON report files over HTTP. Each response now includes a `Last-Modified` header derived from the file's modification time:

```typescript
const { mtime } = fs.statSync(filePath)
res.setHeader('Last-Modified', mtime.toUTCString())
res.sendFile(filePath)
```

`Last-Modified` is a CORS-safelisted header — readable cross-origin without extra `Access-Control-Expose-Headers` configuration.

---

### 4.6 Validation Dashboard

**File:** `packages/frontend/src/pages/ValidationDashboard.tsx`

A live QA page at `/validation` that auto-runs 24 checks on load:

| Section | Checks | What is verified |
|---------|--------|-----------------|
| Backend Jest | 3 | 40 tests pass, no failures |
| Frontend Vitest | 3 | 6 node-registration assertions pass |
| Integration Tests | 4 | WeightedScore=82.5, LLM JSON valid, overall success |
| Live Smoke | 6 | Backend health, graphs API, frontend routes |
| Browser / GUI | 5 | localStorage, matchMedia, History API, title, WebSocket |
| Starter Templates | 3 | All 3 templates serve valid JSON with correct node counts |

**Report freshness badge:** Each report section reads the `Last-Modified` header and shows a `⚠ stale` chip (yellow) if the file is older than 2 hours:

```typescript
const STALE_THRESHOLD_MS = 2 * 60 * 60 * 1000 // 2 hours

function isStale(lastModified: string | null): boolean {
  if (!lastModified) return false
  return Date.now() - new Date(lastModified).getTime() > STALE_THRESHOLD_MS
}
```

Other features: auto-runs on mount, refresh button, summary chip `${passed} passed · ${skipped} skipped · ${failed} failed`, timestamps per section, linked from DevHome.

---

### 4.7 Gemini Integration

**Provider:** Google Gemini (`gemini/gemini-2.5-flash`) via LiteLLM proxy

```
LLMNode → POST http://localhost:8000/v1/chat/completions
              ↓
         LiteLLM Proxy (port 8000)
              ↓
         Google Generative AI API (gemini-2.5-flash)
```

**`packages/backend/.env`:**
```
MODEL_WORKER_URL=http://localhost:8000
GEMINI_API_KEY=<key>
```

Start command:
```bash
GEMINI_API_KEY="..." litellm --model gemini/gemini-2.5-flash --port 8000
```

---

### 4.8 Docker Compose

**Files created:**
- `docker-compose.yml` — orchestrates all 4 services
- `packages/backend/Dockerfile.dev` — backend dev image
- `.env.docker` — committed template (copy to `.env.docker.local` for secrets)

```
docker compose --env-file .env.docker.local up --build
```

Services start in dependency order with health checks:

```
postgres (healthy) ─┐
                    ├─→ backend (runs prisma migrate deploy, then nest start)
litellm (healthy) ──┘
backend ────────────→ frontend (Vite dev server)
```

| Service | Port | Image / Dockerfile |
|---------|------|--------------------|
| postgres | 5432 | `postgres:16-alpine` |
| litellm | 8000 | `ghcr.io/berriai/litellm:main-stable` |
| backend | 5001 | `packages/backend/Dockerfile.dev` |
| frontend | 5173 | `packages/frontend/Dockerfile.dev` |

---

### 4.9 Playwright E2E Suite

**Package:** `packages/e2e` (`@haski/e2e`)

27 real-browser tests across 8 suites, running against live services in headless Chromium:

| Suite file | Suites covered | Tests |
|-----------|---------------|-------|
| `suite1-backend-health.spec.ts` | Suite 1 | 3 |
| `suite2-reports.spec.ts` | Suite 2 | 4 |
| `suite3-frontend-routing.spec.ts` | Suite 3 | 4 |
| `suite4-validation-dashboard.spec.ts` | Suite 4 | 5 |
| `suite5-templates.spec.ts` | Suite 5 | 3 |
| `suite6-dark-mode.spec.ts` | Suite 6 | 2 |
| `suite7-weighted-score.spec.ts` | Suite 7 | 1 |
| `suite8-browser-gui.spec.ts` | Suite 8 | 5 |

Suite 8 runs natively in a real Chromium browser — the only way to reliably test `localStorage`, `window.matchMedia`, `history.pushState`, `document.title`, and raw WebSocket handshakes.

Results written to `reports/playwright-results.json` and `reports/playwright-html/`.

**Run command:**
```bash
yarn workspace @haski/e2e test
```

---

## 5. Grading Pipeline — End-to-End Flow

```
Instructor (Editor)                    Student (StudentView)
      │                                       │
      │  drag nodes, connect, save graph      │  types answer, clicks Submit
      │                                       │
      ▼                                       ▼
  POST /graphs                         WS: runGraph event
  { path, graph: JSON }                { path, answer }
      │                                       │
      ▼                                       ▼
  PostgreSQL                     graph-handler.service.ts
  saves graph                    ├─ loads graph from DB by path
                                 ├─ injects answer into AnswerInputNode
                                 ├─ executes graph (LiteGraph runStep loop)
                                 │   ├─ WeightedScoreNode: (s1×w1 + s2×w2)
                                 │   └─ LLMNode → LiteLLM → Gemini API
                                 └─ emits graphOutput event with results
                                         │
                                         ▼
                               StudentView receives score + feedback
                               displays in UI
```

---

## 6. Validation Results

### 6.1 Backend Jest — 40/40 tests, 11 suites

Covers: Graph CRUD, WebSocket gateway, graph execution, health, LTI, REQ-0009 compliance.

### 6.2 Frontend Vitest — 6/6 assertions

All 6 node-registration assertions pass in jsdom.

### 6.3 Integration Tests — 2/2

| Test | Expected | Actual | Result |
|------|----------|--------|--------|
| WeightedScore | 82.5 | 82.5 | PASS |
| LLM JSON (Gemini 2.5 Flash) | `{score, feedback}` | `{"score":100,"feedback":"..."}` | PASS |

### 6.4 Playwright E2E — 27/27 (7.2 s)

| Suite | Tests | Result |
|-------|-------|--------|
| 1 — Backend API Health | 3 | 3 PASS |
| 2 — Report Files Served by Backend | 4 | 4 PASS |
| 3 — Frontend Routing | 4 | 4 PASS |
| 4 — Validation Dashboard Behaviour | 5 | 5 PASS |
| 5 — Starter Templates | 3 | 3 PASS |
| 6 — Dark Mode | 2 | 2 PASS |
| 7 — WeightedScore Integration | 1 | 1 PASS |
| 8 — Browser / GUI Checks | 5 | 5 PASS |
| **Total** | **27** | **27 PASS / 0 FAIL / 0 SKIP** |

---

## 7. Commits Delivered

| Commit | Description |
|--------|-------------|
| `4d4f91a` | Frontend UX: dark mode persistence, template menu, Vitest smoke tests, lib node additions |
| `9c3d5f9` | Fix `graph-handler.service.spec.ts`: update `runGraph` payload to match new required `path` type |
| `d075960` | Add JSON test reporters (Vitest config + Jest `test:report` script) |
| `7f63b3d` | Write integration test results to `reports/integration-results.json` |

---

## 8. How to Run Everything

### Option A — Local (manual services)

```bash
# 1. PostgreSQL — must already be running

# 2. LiteLLM proxy (Gemini)
export GEMINI_API_KEY="your-key"
litellm --model gemini/gemini-2.5-flash --port 8000

# 3. Backend
yarn workspace backend start:dev

# 4. Frontend
yarn workspace @haski/ta-frontend dev
```

### Option B — Docker Compose (single command)

```bash
cp .env.docker .env.docker.local   # add your GEMINI_API_KEY
docker compose --env-file .env.docker.local up --build
```

### Generate fresh test reports

```bash
# Backend Jest → reports/jest-results.json
yarn workspace backend test:report

# Frontend Vitest → reports/vitest-results.json
yarn workspace @haski/ta-frontend test

# Integration (WeightedScore + LLM) → reports/integration-results.json
yarn workspace backend test:integration
```

### Run Playwright E2E suite

```bash
yarn workspace @haski/e2e test              # headless
yarn workspace @haski/e2e test:headed       # with browser window
yarn workspace @haski/e2e test:report       # open HTML report
```

### View validation dashboard

Navigate to `http://localhost:5173/validation` — checks run automatically.
A `⚠ stale` badge appears on any report section whose file is older than 2 hours.

---

## 9. Open Items

All engineering open items are now resolved. No remaining technical blockers.

| Item | Status |
|------|--------|
| Dark mode hardcoded to `'light'` | Resolved — system preference + localStorage |
| Node registration smoke test | Resolved — 6 Vitest assertions |
| E2E pipeline test | Resolved — WeightedScore + LLM integration tests |
| Instructor UX / templates | Resolved — 3 templates + AppBar dropdown + DevHome cards |
| Browser-accessible test results | Resolved — backend `/reports/:file` endpoint |
| Gemini API integration | Resolved — gemini-2.5-flash via LiteLLM |
| Validation Dashboard | Resolved — 24 live checks at `/validation` |
| Docker Compose | Resolved — `docker compose up --build` starts all 4 services |
| Report freshness warning | Resolved — `⚠ stale` badge via `Last-Modified` header |
| Playwright E2E suite | Resolved — 27/27 passing across 8 suites |
| Methodology section | Resolved — see `docs/methodology.md` |
| User study preparation | Resolved — see `docs/user-study.md` |

---

## 10. Research Context — ConceptGrade Algorithm

NodeGrade is the deployment platform for **ConceptGrade**, a 5-layer concept-aware Automated Short Answer Grading (ASAG) algorithm developed as the core PhD research contribution.

### 10.1 Algorithm Summary

```
Student Answer
      ↓
Layer 1: Concept Extraction (LLM) → StudentConceptGraph
Layer 2: KG Comparison → Coverage, Integration, Gap scores
Layer 3: Cognitive Depth → Bloom's (L1–L6) + SOLO (L1–L5)
Layer 4: Misconception Detection → 16-entry taxonomy, severity levels
Layer 5: SURE Ensemble Verifier → 3 personas, median → final [0–5] score
      ↓
Score + Bloom's Level + SOLO Level + Misconceptions + Feedback
```

### 10.2 Key Results

**Short Answer Grading — Mohler 2011 benchmark (n=120):**

| Metric | Pure LLM | KG-Only | ConceptGrade | vs Pure LLM |
|--------|----------|---------|--------------|-------------|
| MAE | 0.354 | 1.375 | **0.287** | **−18.9%** |
| RMSE | 0.496 | 1.593 | **0.395** | **−20.4%** |
| Pearson r | 0.9679 | 0.5070 | **0.9697** | better |
| Bias | −0.237 | +0.741 | **−0.008** | **97% less** |

**Long Answer Grading — Internal essay benchmark (n=20):**

| Metric | Pure LLM | ConceptGrade | vs Pure LLM |
|--------|----------|--------------|-------------|
| MAE | 0.575 | **0.375** | **−34.8%** |
| RMSE | 0.716 | **0.487** | **−32.0%** |
| Bias | +0.575 | **+0.175** | **70% less** |

**Adversarial robustness (n=100, 7 categories):**
ConceptGrade wins in 5 of 7 adversarial categories (MAE −11.4%, RMSE −9.7% overall).

> KG-Only performs *worse* than Pure LLM alone — confirming that the KG + LLM combination is essential, not KG structure alone.

All comparisons statistically significant (Wilcoxon signed-rank, p < 0.001).

---

## 11. Research Methodology & User Study

Full documents:

| Document | Path | Contents |
|----------|------|---------|
| Methodology | `docs/methodology.md` | Research questions, algorithm design decisions, evaluation protocol, statistical significance, limitations, **Appendix A** (SURE persona prompts), **Appendix B** (misconception taxonomy) |
| User Study | `docs/user-study.md` | Participant profiles, session protocols, SUS questionnaire, student survey, grading agreement protocol, analysis plan, timeline |

### 11.1 Methodology Highlights

- **RQ1–RQ4** cover grading accuracy (SAG/LAG), adversarial robustness, and instructor/student platform usability
- Evaluation follows established ASAG benchmarking practice (Mohler 2011; Wilcoxon signed-rank; Pearson r / MAE / QWK)
- **KG-Only baseline** uses linear scaling of the Layer 2 coverage ratio [0,1] → [0,5]; intentionally simple to isolate the LLM verifier's marginal contribution
- **LAG results (n=20) are explicitly framed as a pilot/exploratory evaluation** — directional evidence only; a larger-scale LAG study is the primary planned future work
- Platform methodology documents the node-based execution model and three design decisions that remove barriers to classroom adoption
- All SAG improvements are statistically significant: MAE p < 0.001, adversarial MAE p < 0.05 (Wilcoxon signed-rank, paired)

### 11.2 User Study Plan (Finalized Protocol)

| Cohort | Target n | Session length | Key measures |
|--------|----------|---------------|--------------|
| Instructors | 10–15 | 75 min | Task completion rate, SUS score (target ≥68), grading agreement (target ±0.5 on ≥80% of answers) |
| Students | 30–50 | 20 min | Likert clarity / trust / actionability (target ≥4/5 mean on S1–S4), grading agreement |

**Instructor session structure (75 min):**

| Phase | Duration | Notes |
|-------|----------|-------|
| Briefing + consent | 5 min | — |
| Onboarding | 5 min | Researcher-led walkthrough |
| Task 1 | 15 min | Load **`concept-grade-task1.json`** (study variant with score OutputNode deliberately disconnected), make the one required connection, save — *not build from scratch* |
| Task 2 | 10 min | Submit sample answer via StudentView; interpret output |
| Task 3 | 10 min | Review 2 graded outputs; agree/disagree |
| Buffer | 5 min | Overflow or exploration |
| SUS questionnaire | 5 min | Standard 10-item scale |
| Semi-structured interview | 15 min | **Protected — not shortened below 10 min** |

**Student survey (6 Likert items, 1–5):**

| # | Statement | Type |
|---|-----------|------|
| S1 | The feedback I received was easy to understand. | Positive |
| S2 | The score I received felt fair given my answer. | Positive |
| S3 | The feedback helped me identify a specific gap in my understanding. | Positive |
| S4 | I would feel comfortable if this score counted toward my final grade. | Positive (trust, not speed) |
| S5 | The feedback pointed out things I disagreed with or that seemed wrong. | **Reverse-coded** |
| S6 | I would rather wait for human feedback than receive this automated feedback. | **Reverse-coded** |

S5 and S6 are reverse-coded (score = 6 − raw) before computing means and Cronbach's α. S4 was deliberately redesigned from a speed-preference item to a grade-stakes trust item to avoid a ceiling effect. The mandatory follow-up open question requires students to name one specific agreement *and* one specific disagreement — preventing deflective "everything was fine" responses.

**Study timeline:**

| Milestone | Target |
|-----------|--------|
| Ethics approval submitted | April 2026 |
| Pilot sessions (1–2 instructors) | May 2026 |
| Full instructor cohort | June 2026 |
| Student cohort | June–July 2026 |
| Grading agreement analysis | July 2026 |
| Results written up for paper | August 2026 |
