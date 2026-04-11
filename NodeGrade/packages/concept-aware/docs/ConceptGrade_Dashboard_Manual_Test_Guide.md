# ConceptGrade Dashboard — Manual & Browser Test Guide

Use this document for **local** QA: human tester or browser **on the same machine** as Nest/Vite. Each case has an **ID**, **steps**, and **expected results**. Record outcomes in the [Feedback template](#feedback-template-for-testers) at the end.

**Remote AI browser (Comet, cloud sandbox, etc.):** Do **not** use this file alone — those environments **cannot** reach `localhost` on the developer’s PC. Use only **[ConceptGrade_Dashboard_E2E_Remote_Browser.md](./ConceptGrade_Dashboard_E2E_Remote_Browser.md)** after the developer provides **HTTPS tunnel URLs** for the frontend and API.

**Related docs:** [ConceptGrade_Dashboard_Implementation.md](./ConceptGrade_Dashboard_Implementation.md) (architecture) · Scripts under `packages/backend/scripts/` (prerequisites + API smoke).

### Request an end-to-end pipeline test

From **`packages/backend`** (Nest running, eval JSON present; add `--frontend` if Vite is up):

```bash
npm run request:e2e-test
# or also check Vite is reachable:
npm run request:e2e-test:full
```

From monorepo root with Yarn: `yarn request:e2e-test` / `yarn request:e2e-test:full`.

This runs **prerequisites** + **visualization API smoke** (9 specs per dataset). On success it prints **copy-paste blocks** for:

- **Local QA** — pointer to this guide + typical dashboard URL  
- **Remote browser** — handoff template + path to [ConceptGrade_Dashboard_E2E_Remote_Browser.md](./ConceptGrade_Dashboard_E2E_Remote_Browser.md)

If either step fails, the script exits **1** and does not print the request (fix services / `DATA_DIR` / eval files first).

Override Nest port if needed:

```bash
python3 packages/backend/scripts/request_e2e_pipeline_test.py --api-base http://localhost:5000 --frontend http://localhost:5173
```

---

## 1. Test environment

| Item | Default | Notes |
|------|---------|--------|
| Backend (NestJS) | `http://localhost:5000` (or **5001** if `PORT` / `.env` says so) | `packages/backend` → `npm run start:dev`; confirm log line “running on port …” |
| Frontend (Vite) | `http://localhost:5173` | `packages/frontend` → `npx vite --host 0.0.0.0` |
| API base URL in UI | Must match backend | `packages/frontend/public/config/env.development.json` → `API` |
| Data | `packages/concept-aware/data/*_eval_results.json` | Only files with non-empty `results[]` + per-sample scores appear as tabs |

### 1.1 Start required components (before any tests)

| What you are testing | Required running |
|------------------------|------------------|
| **TC-AUTO-001, TC-API-*** | **Backend only** |
| **TC-UI-*, TC-ACC-*** | **Backend + frontend** |

**Terminal 1 — backend (always):**

```bash
cd packages/backend && npm run start:dev
```

**Terminal 2 — frontend (for browser / UI cases):**

```bash
cd packages/frontend && npx vite --host 0.0.0.0
```

### 1.2 Verify services are up (do not skip)

Run these **after** starting the processes above. They **fail fast** with hints if something is missing.

**API only** (Nest reachable + visualization route):

```bash
cd packages/backend && npm run check:dashboard-test-env
```

**API + Vite** (required before TC-UI-001):

```bash
cd packages/backend && npm run check:dashboard-test-env -- --frontend http://localhost:5173
```

From monorepo root (`NodeGrade/`) with Yarn:

```bash
yarn check:dashboard-test-env
# or with frontend:
cd packages/backend && npm run check:dashboard-test-env -- --frontend http://localhost:5173
```

**If servers are slow to boot**, poll for up to 120 seconds then run the API smoke test in one go:

```bash
cd packages/backend && npm run test:dashboard:wait
```

That runs: prerequisites (wait + frontend check) + `verify_visualization_api.py`.

**One-shot (API assumed already up):** prerequisites + smoke, no frontend check:

```bash
cd packages/backend && npm run test:dashboard
# or from root: yarn test:dashboard
```

**Full gate (backend + frontend + smoke):**

```bash
cd packages/backend && npm run test:dashboard:full
# or from root: yarn test:dashboard:full
```

Custom base URL (non-default port):

```bash
python3 packages/backend/scripts/dashboard_test_prerequisites.py --api-base http://localhost:3001 --frontend http://localhost:5173
```

### 1.3 Pre-flight API contract

After `check:dashboard-test-env` passes, confirm **9** visualization specs:

```bash
cd packages/backend && npm run verify:visualization
```

Exit code **0** = dataset list + 9 `viz_id`s per dataset. **TC-AUTO-001** is this command (or use `test:dashboard` / `test:dashboard:wait` which include it).

---

## 2. Test case summary

| ID | Area | Brief objective |
|----|------|-----------------|
| TC-PRE-001 | Env | Prerequisite checker (API + optional frontend) |
| TC-AUTO-001 | API | Smoke script passes |
| TC-API-001 | API | Dataset list JSON |
| TC-API-002 | API | Dataset payload shape (e.g. `digiklausur`) |
| TC-API-003 | API | Second dataset payload (e.g. `kaggle_asag`) — same contract as TC-API-002 |
| TC-UI-001 | UI | Dashboard loads without study mode |
| TC-UI-002 | UI | Dataset tabs match API |
| TC-UI-003 | UI | Summary metric cards |
| TC-UI-004 | UI | Charts + table in condition B |
| TC-UI-005 | UI | Condition A hides charts |
| TC-UI-006 | UI | Study panel + submit |
| TC-UI-007 | UI | Export study log |
| TC-UI-008 | UI | Backend down / error handling |
| TC-UI-009 | UI | Refresh control |
| TC-ACC-001 | Accessibility | Keyboard / focus (smoke) |

---

## 3. Test cases (detailed)

### TC-PRE-001 — Prerequisite services reachable

| Field | Content |
|-------|---------|
| **Objective** | Prove Nest and (for UI runs) Vite are listening before other cases. |
| **Preconditions** | Intended processes started per section 1.1. |
| **Steps** | 1. For API-only work: `cd packages/backend && npm run check:dashboard-test-env`<br>2. Before UI cases: same with `--frontend http://localhost:5173` |
| **Expected** | Exit code **0**; stdout contains `OK: visualization API reachable` and, if frontend flag used, `OK: frontend reachable`. |
| **Failure hints** | Script prints **FAIL** and **Start commands** on stderr — follow them, then re-run. |

---

### TC-AUTO-001 — Automated API smoke

| Field | Content |
|-------|---------|
| **Objective** | Confirm visualization API contract before UI testing. |
| **Preconditions** | Run **section 1.2** `npm run check:dashboard-test-env` (or `test:dashboard`) so backend is proven up; eval JSON under `concept-aware/data/`. |
| **Steps** | 1. `cd packages/backend`<br>2. `npm run verify:visualization` *(or use `npm run test:dashboard` which checks reachability first)* |
| **Expected** | Exit code **0**; stdout includes `OK:` lines per dataset and ends with `Smoke test passed.` |
| **Failure hints** | Connection refused → start backend (see section 1.1). Wrong visualization count → backend/data drift. |

---

### TC-API-001 — GET dataset list

| Field | Content |
|-------|---------|
| **Objective** | List endpoint returns JSON array of dataset slugs. |
| **Preconditions** | Backend running. |
| **Steps** | 1. `curl -sS "http://localhost:<PORT>/api/visualization/datasets"` (replace `<PORT>` with your Nest port, e.g. **5000** or **5001**)<br>2. Parse JSON (e.g. `jq .`). |
| **Expected** | HTTP **200**. Body: `{"datasets":["..."]}` with **non-empty** `datasets`. Typical: `digiklausur`, `kaggle_asag`. **`offline`** must **not** appear (ablation file excluded). |
| **Failure hints** | Empty list → no compatible `*_eval_results.json`. 404 → wrong path/port. |

---

### TC-API-002 — GET single dataset (first slug)

| Field | Content |
|-------|---------|
| **Objective** | Full payload includes metrics and nine visualizations. |
| **Preconditions** | TC-API-001 returned at least one dataset name `D` (often `digiklausur`). |
| **Steps** | 1. `curl -sS "http://localhost:<PORT>/api/visualization/datasets/D"` (same `<PORT>` as TC-API-001; replace `D` with first slug).<br>2. Confirm `visualizations` length and `viz_id` values. |
| **Expected** | HTTP **200**. Top-level keys include `dataset`, `n`, `metrics` (`C_LLM`, `C5_fix`), `wilcoxon_p`, `mae_reduction_pct`, `visualizations`. **`visualizations` length = 9**. `viz_id` set exactly: `class_summary`, `blooms_dist`, `solo_dist`, `score_comparison`, `concept_frequency`, `chain_coverage_dist`, `score_scatter`, `student_radar`, `misconception_heatmap`. |
| **Failure hints** | Missing spec → backend regression. |

---

### TC-API-003 — GET second dataset (same contract)

| Field | Content |
|-------|---------|
| **Objective** | Every listed dataset satisfies the same 9-spec contract (regression guard when adding datasets). |
| **Preconditions** | TC-API-001 returned a **second** slug `D2` (e.g. `kaggle_asag`). If only one dataset exists, mark **N/A**. |
| **Steps** | Same as TC-API-002 but `D2` instead of `D`. |
| **Expected** | Identical structural expectations as TC-API-002 for `D2`. |
| **Failure hints** | One dataset passes and another fails → data-file or adapter bug for that slug only. |

---

### TC-UI-001 — Dashboard default route (no query params)

| Field | Content |
|-------|---------|
| **Objective** | Default `/dashboard` behavior without study scaffolding. |
| **Preconditions** | **Section 1.1** both terminals; **section 1.2** with `--frontend http://localhost:5173` passes; API base URL matches backend port. |
| **Steps** | 1. Open `http://localhost:5173/dashboard` (no query string).<br>2. Wait for content (no infinite spinner). |
| **Expected** | Title contains **ConceptGrade** and **Instructor Analytics Dashboard**. **No** study task panel at top (no “task prompt” textarea). **Dataset tabs** visible if API returned datasets. **Charts visible** (default condition behaves like **B** for chart visibility: not control). **No** “Export study log” button (study-only). |
| **Failure hints** | Blank/error → CORS, wrong API URL, or backend stopped. Spinner forever → failed fetch. |

---

### TC-UI-002 — Dataset tabs match API

| Field | Content |
|-------|---------|
| **Objective** | Tab labels correspond to listed datasets. |
| **Preconditions** | TC-API-001 known; TC-UI-001 loaded. |
| **Steps** | 1. Note `datasets` from curl or smoke script.<br>2. Count tabs on dashboard.<br>3. Switch each tab; confirm no error banner. |
| **Expected** | Tab **count** = length of API `datasets`. Switching tabs updates content without red error `Alert`. Known labels: **DigiKlausur (NN)**, **Kaggle ASAG (Science)** (exact text may use dataset slug fallback if unmapped). |
| **Failure hints** | Extra tab “mohler” with errors → API fetch failed and UI fell back to hardcoded list (check network tab + API URL). |

---

### TC-UI-003 — Summary metric cards

| Field | Content |
|-------|---------|
| **Objective** | Top row metrics render numeric values. |
| **Preconditions** | TC-UI-001; at least one dataset selected. |
| **Steps** | 1. Observe row: Total Answers, C5 MAE, Baseline MAE, MAE Reduction, Wilcoxon p, Pearson r (C5). |
| **Expected** | All show **numbers** (or `<0.001` for tiny p). No `NaN` / blank for a loaded dataset. Values change when switching tabs (if datasets differ). |
| **Failure hints** | Zeros everywhere → empty `results` or wrong JSON schema. |

---

### TC-UI-004 — Full analytics (condition B + charts)

| Field | Content |
|-------|---------|
| **Objective** | Treatment view shows all main visuals including per-sample table. |
| **Preconditions** | Open `http://localhost:5173/dashboard?condition=B`. |
| **Steps** | 1. Scroll through page.<br>2. Confirm sections: Bloom bar, SOLO bar, score comparison, chain coverage, concept frequency, **per-sample score table** (scrollable), student radar area, misconception heatmap area. |
| **Expected** | **Study task panel** visible at top. **Charts** render (bars/lines; no blank cards except intentional empty states). **Per-sample table** has column headers and multiple rows. Radar/heatmap may show **empty-state** text (no crash). |
| **Failure hints** | Table missing → frontend regression. Chart JS error in console → Recharts/data issue. |

---

### TC-UI-005 — Control condition A (charts hidden)

| Field | Content |
|-------|---------|
| **Objective** | Condition A shows summary only for study control arm. |
| **Preconditions** | Open `http://localhost:5173/dashboard?condition=A`. |
| **Steps** | 1. Confirm study panel present.<br>2. Scroll below summary cards and insights. |
| **Expected** | **Summary metric cards** and **insight** `Alert`s still visible. **No** Bloom/SOLO/score comparison/chain/concept chart sections **below** the summary block (no Recharts chart areas). |
| **Failure hints** | Charts still visible → `condition` not read as `A` (typo in URL). |

---

### TC-UI-006 — Study task submit

| Field | Content |
|-------|---------|
| **Objective** | Task flow records answer and shows success. |
| **Preconditions** | `?condition=B` (or `A`). |
| **Steps** | 1. Focus answer textarea (task prompt visible).<br>2. Type short text.<br>3. Adjust confidence slider.<br>4. Click **Submit answer**. |
| **Expected** | After submit: **green success** alert; submit controls no longer required for “recorded” state. |
| **Failure hints** | No reaction → JS error; check console. |

---

### TC-UI-007 — Export study log

| Field | Content |
|-------|---------|
| **Objective** | JSON export contains events. |
| **Preconditions** | `?condition=B`; TC-UI-006 completed (optional: hover a chart). |
| **Steps** | 1. Click **Export study log (JSON)**.<br>2. Open downloaded file in editor. |
| **Expected** | File downloads; name like `study-log-XXXXXXXX.json`. JSON is an **array** of objects with fields such as `event_type`, `elapsed_ms`, `payload` / nested data. Includes at least `page_view`; after interactions: `tab_change`, `task_submit`, possibly `chart_hover`. |
| **Failure hints** | No download → browser blocked popups; button only in study mode. |

---

### TC-UI-008 — API unreachable

| Field | Content |
|-------|---------|
| **Objective** | Graceful error when backend stops. |
| **Preconditions** | Dashboard loaded on a dataset; then **stop** Nest backend. |
| **Steps** | 1. Click refresh (circular icon) or switch tab to force refetch.<br>2. Observe UI. |
| **Expected** | **Red error** `Alert` explaining failure to load; mentions backend / eval path. No unhandled white screen. |
| **Failure hints** | Silent failure → check network tab. |
| **Remote / browser agents** | Mark **SKIP** or **CONDITIONAL PASS** if the sandbox cannot stop the backend: optional **404** check — `GET /api/visualization/datasets/nonexistent` returns structured **404** JSON (confirms API errors; **not** the same as the red UI `Alert` when Nest is down). |

---

### TC-UI-009 — Refresh

| Field | Content |
|-------|---------|
| **Objective** | Refresh icon triggers reload of visualization data. |
| **Preconditions** | Backend running; dashboard on a dataset. |
| **Steps** | 1. Click refresh **IconButton** in header.<br>2. Observe brief loading if implemented. |
| **Expected** | Data reloads without full page navigation; metrics/charts consistent after reload (same data file). |
| **Failure hints** | If refresh clears to broken state, note console errors. |

---

### TC-ACC-001 — Keyboard / focus (smoke)

| Field | Content |
|-------|---------|
| **Objective** | Basic accessibility smoke for study flow. |
| **Preconditions** | `?condition=B`. |
| **Steps** | 1. Press **Tab** repeatedly from top of page.<br>2. Reach **Submit** / **Export** without mouse.<br>3. **Enter** or **Space** on focused button where applicable. |
| **Expected** | Focus visible on interactive controls; no keyboard trap in study panel; buttons activatable. |
| **Failure hints** | Document where focus is lost or invisible. |

---

## 4. Remote / AI-controlled browser (Comet, etc.)

**This section is intentionally short.** A browser that runs in a **cloud sandbox** cannot use the TC-UI-* steps that point at `http://localhost:5173` — that is not the developer’s machine.

**Give the remote agent:** (1) your filled **section 0 handoff** (two `https://` tunnel lines), then (2) the full text of [ConceptGrade_Dashboard_E2E_Remote_Browser.md](./ConceptGrade_Dashboard_E2E_Remote_Browser.md). Do **not** send the E2E doc alone — without the handoff, the agent will correctly **SKIP** all cases.

That file defines **`FRONTEND_BASE`** and **`API_BASE`**, the ordered **E2E-1 … E2E-12** checks, and the **output table**. You must start tunnels, add CORS for the tunnel origin, and set the SPA **`API`** to **`API_BASE/`** before the remote run. In-app text showing `localhost:5173` / `localhost:5001` is **not** a substitute for the handoff.

**Local** scripted checks remain: `npm run check:dashboard-test-env`, `npm run verify:visualization` (use the same `<PORT>` as Nest).

---

## 5. Feedback template for testers

Copy for spreadsheet or issue comments:

```
Tester / agent name:
Date:
Browser + version:
OS:
Backend URL:
Frontend URL:
TC-PRE-001: PASS / FAIL / SKIPPED — notes:
TC-AUTO-001: PASS / FAIL / SKIPPED — notes:
TC-API-001: PASS / FAIL / SKIPPED — notes:
TC-API-002: PASS / FAIL / SKIPPED — notes:
TC-API-003: PASS / FAIL / SKIPPED / N/A — notes:
TC-UI-001: PASS / FAIL / SKIPPED — notes:
TC-UI-002: PASS / FAIL / SKIPPED — notes:
TC-UI-003: PASS / FAIL / SKIPPED — notes:
TC-UI-004: PASS / FAIL / SKIPPED — notes:
TC-UI-005: PASS / FAIL / SKIPPED — notes:
TC-UI-006: PASS / FAIL / SKIPPED — notes:
TC-UI-007: PASS / FAIL / SKIPPED — notes:
TC-UI-008: PASS / FAIL / SKIPPED / CONDITIONAL — notes:
TC-UI-009: PASS / FAIL / SKIPPED — notes:
TC-ACC-001: PASS / FAIL / SKIPPED — notes:

Blockers:
Screenshots / logs (paths or links):
```

---

## 6. Changelog (maintenance)

| Date | Change |
|------|--------|
| 2026-04-08 | Comet (AI browser, co-located localhost): **13 PASS**, **1 CONDITIONAL** on TC-UI-008 (full “API down” red `Alert` needs manual Nest stop; structured **404** for bad dataset slug confirmed). **TC-API-003** added for second-dataset API parity. |
| (add rows when specs or routes change) | e.g. visualization count 9 → N |

When the API **visualization count** or **viz_id** set changes, update **TC-API-002/003**, **TC-AUTO-001** (script), and **Section 2** summary.
