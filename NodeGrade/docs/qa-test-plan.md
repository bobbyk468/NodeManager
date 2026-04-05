# NodeGrade — Automated QA Test Plan

Hand this document to your automation browser. It covers all current features independently.

---

## Prerequisites (verify before starting)

| Service | URL | Expected |
|---------|-----|----------|
| Frontend (Vite) | http://localhost:5173 | HTTP 200 |
| Backend (NestJS) | http://localhost:5001 | HTTP 200 |
| PostgreSQL | via `/health` | `components.database.status === "up"` |

---

## Suite 1 — Backend API Health

**Scenario 1.1 — Health endpoint**
1. `GET http://localhost:5001/health`
2. Assert HTTP 200
3. Assert response JSON has `status === "ok"`
4. Assert `components.database.status === "up"` *(field is under `components`, not `info`)*

**Scenario 1.2 — Graphs endpoint returns a list**
1. `GET http://localhost:5001/graphs`
2. Assert HTTP 200
3. Assert response is a JSON array
4. Assert array length > 0

**Scenario 1.3 — Unknown route returns 404**
1. `GET http://localhost:5001/nonexistent-route`
2. Assert HTTP 404

---

## Suite 2 — Report Files Served by Backend

**Scenario 2.1 — Jest report is accessible**
1. `GET http://localhost:5001/reports/jest-results.json`
2. Assert HTTP 200
3. Assert `numFailedTestSuites === 0`
4. Assert `numPassedTests >= 40`
5. Assert `success === true`

**Scenario 2.2 — Vitest report is accessible**
1. `GET http://localhost:5001/reports/vitest-results.json`
2. Assert HTTP 200
3. Assert `testResults` array is non-empty
4. Assert every item in `testResults` has `status === "passed"`
5. Count total assertions with `status === "passed"` across all suites — assert count >= 6

**Scenario 2.3 — Integration report is accessible**
1. `GET http://localhost:5001/reports/integration-results.json`
2. Assert HTTP 200
3. Assert `tests.weightedScore.status === "passed"`
4. Assert `tests.weightedScore.value` is between 82.4 and 82.6
5. Assert `tests.llmJson.status` is either `"passed"` or `"skipped"` (never `"failed"`)
6. Assert `success === true`

**Scenario 2.4 — Unknown report returns 404**
1. `GET http://localhost:5001/reports/secrets.json`
2. Assert HTTP 404

---

## Suite 3 — Frontend Routing

> Note: NodeGrade is a React SPA — all routes return the same static HTML shell from Vite.
> Link and heading assertions must be verified against the JSX source files, not raw HTTP responses.

**Scenario 3.1 — Home page loads**
1. `GET http://localhost:5173/` — Assert HTTP 200
2. Assert `<title>` in raw HTML contains "Node Grade"
3. Read source file `packages/frontend/src/pages/App.tsx` — Assert it contains a `<Link>` or `<MuiLink>` to `/ws/editor/local/1/1`
4. Read source file `packages/frontend/src/pages/App.tsx` — Assert it contains a `<Link>` or `<MuiLink>` to `/ws/student/local/1/1`
5. Read source file `packages/frontend/src/pages/App.tsx` — Assert it contains a `<Link>` or `<MuiLink>` to `/validation`

**Scenario 3.2 — Editor route loads**
1. `GET http://localhost:5173/ws/editor/local/1/1`
2. Assert HTTP 200
3. Assert raw HTML does not contain "Something went wrong"

**Scenario 3.3 — Student route loads**
1. `GET http://localhost:5173/ws/student/local/1/1`
2. Assert HTTP 200
3. Assert raw HTML does not contain "Something went wrong"

**Scenario 3.4 — Validation dashboard route loads**
1. `GET http://localhost:5173/validation` — Assert HTTP 200
2. Read source file `packages/frontend/src/pages/ValidationDashboard.tsx` — Assert it contains the text "NodeGrade — Validation Dashboard" in the JSX
3. Read source file `packages/frontend/src/pages/App.tsx` — Assert `<Route path="validation"` is present and renders `<ValidationDashboard />`

---

## Suite 4 — Validation Dashboard Behaviour

> Verify by reading source file: `packages/frontend/src/pages/ValidationDashboard.tsx`

**Scenario 4.1 — Dashboard auto-runs on load**
- Assert `useEffect(() => { run() }, [run])` is present — checks fire without user interaction
- Assert `running` state renders a loading indicator ("Running checks…") while checks are in progress
- Assert `setSections(result)` populates the table after `runChecks` resolves

**Scenario 4.2 — Summary chip shows correct counts**
- Assert chip label uses the format: `${passed} passed · ${skipped} skipped · ${failed} failed`
- Assert `passed`, `skipped`, `failed` are computed as separate `filter()` counters — not conflated

**Scenario 4.3 — All check rows have a status**
- Assert every `CheckResult` maps to a `<StatusChip>` in the JSX
- Fetch all three report files from `http://localhost:5001/reports/` and trace through `runChecks` logic to predict check results
- Assert total check count = 19 (3 Jest + 3 Vitest + 4 Integration + 6 Smoke + 3 Templates)
- Assert no check produces `status === "fail"` given the current report data

**Scenario 4.4 — Refresh button re-runs checks**
- Assert a `<RefreshIcon>` `<IconButton>` is present near the heading
- Assert it has `onClick={run}`
- Assert it has `disabled={running}` (prevents double-submission)

**Scenario 4.5 — Report timestamps are shown**
- Assert `jestTimestamp` is populated from `testResults[0].endTime` in the Jest report JSON
- Assert `vitestTimestamp` is populated from the max `endTime` across Vitest suites
- Assert `intTimestamp` is populated from the `timestamp` field in the integration report JSON
- Verify all three timestamp source fields actually exist in the fetched report JSONs

---

## Suite 5 — Starter Templates

**Scenario 5.1 — Starter skeleton template**
1. `GET http://localhost:5173/templates/starter.json`
2. Assert HTTP 200
3. Assert valid JSON with a `nodes` array
4. Assert `nodes.length === 4`

**Scenario 5.2 — ConceptGrade pipeline template**
1. `GET http://localhost:5173/templates/concept-grade.json`
2. Assert HTTP 200
3. Assert valid JSON with a `nodes` array
4. Assert `nodes.length === 5`
5. Assert `links` array length > 0

**Scenario 5.3 — LLM grader template**
1. `GET http://localhost:5173/templates/llm-grader.json`
2. Assert HTTP 200
3. Assert valid JSON with a `nodes` array
4. Assert `nodes.length >= 10`
5. Assert `links` array length > 0

---

## Suite 6 — Dark Mode

> Verify by reading source files listed in each scenario.

**Scenario 6.1 — Dark mode toggle exists on editor page**
- Read `packages/frontend/src/components/AppBar.tsx`
- Assert a button with `aria-label="toggle color mode"` is present in the JSX
- Assert it calls `colorMode.toggleColorMode` on click

**Scenario 6.2 — Dark mode state persists across reload**
- Read `packages/frontend/src/pages/App.tsx`
- Assert `localStorage.getItem("ng-color-mode")` is read inside the `useState` initializer
- Assert `localStorage.setItem("ng-color-mode", mode)` is called in a `useEffect` with `[mode]` dependency
- Assert theme `mode` uses stored value with `mode ?? (prefersDarkMode ? 'dark' : 'light')` — stored value takes priority over system default

---

## Suite 7 — WeightedScore Integration (backend grading logic)

**Scenario 7.1 — WeightedScore result in integration report**
1. `GET http://localhost:5001/reports/integration-results.json`
2. Read `tests.weightedScore.value`
3. Assert value is between 82.49 and 82.51
4. Assert `tests.weightedScore.expected === 82.5`
5. *(Confirms: score_1=80, score_2=0.85 normalised to 85, weights=0.5/0.5 → 82.5)*

---

## Suite 8 — Browser / GUI Checks

> All assertions run inside the browser context via `ValidationDashboard.tsx` (`runChecks()`).
> No external tool required — these fire automatically when the dashboard loads.

**Scenario 8.1 — localStorage read/write**
- Assert `localStorage.setItem('ng-gui-test', '1')` followed by `getItem` returns `"1"`
- Assert key is cleaned up (`removeItem`) after the check
- Confirms dark mode persistence (`ng-color-mode`) will work at runtime

**Scenario 8.2 — System dark mode API**
- Assert `window.matchMedia('(prefers-color-scheme: dark)')` does not throw
- Assert the result has a boolean `matches` field
- Confirms the theme initializer fallback in `App.tsx` works correctly

**Scenario 8.3 — History API (SPA routing)**
- Assert `typeof window.history.pushState === 'function'`
- Confirms React Router's `createBrowserRouter` can push routes without full-page reloads

**Scenario 8.4 — Page title**
- Assert `document.title` contains `"Node Grade"` (case-insensitive)
- Confirms the `<title>` set in `index.html` is present in the loaded document

**Scenario 8.5 — WebSocket reachable (backend)**
- Open a native `WebSocket` to `ws://localhost:5001/socket.io/?EIO=4&transport=websocket`
- Assert connection opens within 3 seconds (`onopen` fires before timeout)
- Confirms the Socket.IO server accepts upgrade handshakes (required by Editor and StudentView)

---

## Browser Automation Instructions — Suite 8

These steps are written for a browser automation agent (Playwright, Puppeteer, Selenium, or equivalent).
All 5 checks run automatically when the Validation Dashboard loads — no user interaction required.

### Step 1 — Prerequisites
Verify the following before navigating:
- `GET http://localhost:5001/health` → HTTP 200, `status === "ok"`
- `GET http://localhost:5173/` → HTTP 200

### Step 2 — Navigate to the Validation Dashboard
1. Open `http://localhost:5173/validation` in the browser.
2. Wait for the loading spinner to disappear.
   - Condition: element matching text `"Running checks…"` is **no longer visible**.
3. Wait for the timestamp line to appear.
   - Condition: element matching text `"Checks evaluated at:"` is **visible** on the page.
   - Timeout: 15 seconds (the WebSocket check adds up to 3 s).

### Step 3 — Locate the "Browser / GUI Checks" section
4. Find the heading element whose text is exactly **`"Browser / GUI Checks"`**.
   - In the DOM this is a `<span>` inside a MUI `Typography` with `font-weight: 600`.
5. Assert the heading is visible (confirms the section rendered).

### Step 4 — Assert each check row is PASS
The table under "Browser / GUI Checks" has exactly 5 rows.
For each row assert: the `<span>` with class `MuiChip-label` inside that row reads **`"PASS"`**.

| Row | Expected label text (Check column) |
|-----|-------------------------------------|
| 1 | `localStorage read/write (dark mode persistence)` |
| 2 | `matchMedia API (system dark mode detection)` |
| 3 | `History API available (SPA routing)` |
| 4 | `Page <title> contains "Node Grade"` |
| 5 | `WebSocket reachable (backend)` |

For each row the chip must:
- Have label text `"PASS"` (not `"FAIL"` or `"SKIP"`)
- Have MUI color class `MuiChip-colorSuccess` (green chip)

### Step 5 — Assert overall summary chip
6. Find the summary `<Chip>` near the top of the page (filled, large chip).
7. Assert its label matches the pattern: `"N passed · 0 skipped · 0 failed"` where `N ≥ 27`.
8. Assert the chip has class `MuiChip-colorSuccess` (all green — no failures).

### Step 6 — Report
For each of the 5 rows record:
- **Row label** (Check column text)
- **Status observed** (`PASS` / `FAIL` / `SKIP`)
- **Detail text** (third column — e.g. `ok`, `prefers-dark=false`, `connected`)

Fill in the Suite 8 row of the summary table at the end of this document.

---

## Reporting Instructions

For each scenario report:
- **Suite / Scenario number and name**
- **PASS / FAIL / SKIP**
- **Actual values observed** (status codes, field values, element/text presence)
- **Failure reason** if FAIL

End with this summary table filled in:

| Suite | Total | PASS | FAIL | SKIP |
|-------|-------|------|------|------|
| 1 — Backend API Health | 3 | | | |
| 2 — Report Files | 4 | | | |
| 3 — Frontend Routing | 4 | | | |
| 4 — Validation Dashboard | 5 | | | |
| 5 — Starter Templates | 3 | | | |
| 6 — Dark Mode | 2 | | | |
| 7 — WeightedScore | 1 | | | |
| 8 — Browser / GUI Checks | 5 | | | |
| **Total** | **27** | | | |
