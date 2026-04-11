# ConceptGrade Dashboard — E2E test instructions (remote browser)

**Audience:** An automated or AI-controlled browser (e.g. Comet) that is **not** on the same machine as the Nest/Vite processes.

**Use this document as the single prompt** for remote E2E testing. Do not assume `localhost` or `127.0.0.1` reach the app under test.

---

## 0. Developer handoff (required — paste above this doc in chat)

The **human** must prepend a filled block **in the same message** as these instructions (or immediately above them). The **remote agent** must parse it before section 3.

```
FRONTEND_BASE=https://your-frontend-tunnel.example.ngrok-free.app
API_BASE=https://your-api-tunnel.example.ngrok-free.app
```

**Rules**

- Each value is an **`https://` public URL** with **no trailing slash**.
- **Invalid handoff:** either line missing; any value containing `localhost`, `127.0.0.1`, or a private IP; unfilled placeholders (`REPLACE`, `TODO`, etc.).
- **Do not** treat links or prose **inside** the running app (e.g. a local “Node Grade” launcher page that **displays** `http://localhost:5173/dashboard` or `http://localhost:5001/`) as `FRONTEND_BASE` / `API_BASE`. That text only describes the **developer’s machine**. For remote E2E, the **only** authoritative bases are the two lines in this handoff block, and they **must** be tunnel or staging URLs.

**If handoff is missing or invalid**

- Do **not** navigate to `localhost` to “try anyway.”
- Output the [mandatory table](#4-output-format-mandatory) with **E2E-1 … E2E-11 = SKIP**, **E2E-12 = N/A**, **Blockers** = *Blocked: no valid public `FRONTEND_BASE` and `API_BASE` in handoff (localhost visible in-app is not sufficient).*
- **That outcome is correct** — not an agent error.

---

## 1. Hard constraint (read first)

| Fact | Implication |
|------|-------------|
| Your browser runs in a **remote sandbox** (e.g. cloud). | `http://localhost:*` and `http://127.0.0.1:*` refer to **your** environment, **not** the developer’s laptop. |
| Requests to those URLs typically return **403** or fail. | **You cannot** validate this dashboard by opening `localhost:5173` or `localhost:5000` from a remote browser. |
| Valid testing requires **public HTTPS URLs** (or a shared staging host). | The developer must supply **`FRONTEND_BASE`** and **`API_BASE`** below. |

If **`FRONTEND_BASE`** / **`API_BASE`** were not set by a **valid handoff (section 0)**, you already stopped — do not re-use localhost from page copy.

---

## 2. Inputs (meaning of the handoff variables)

These are defined **only** by the section 0 block (not by URLs read off a local-only page):

| Variable | Example shape | Used for |
|----------|----------------|----------|
| **`FRONTEND_BASE`** | `https://xxxx.ngrok-free.app` | Vite app — open pages in the browser |
| **`API_BASE`** | `https://yyyy.ngrok-free.app` | Nest — `fetch` / XHR from the app must target this host |

**Rules for the developer (not for the browser):**

- Tunnel **the same ports** Nest and Vite actually use (often **5001** for Nest if `PORT=5001` in `.env`, **5173** for Vite — confirm on the host).
- **CORS:** Nest must allow **`FRONTEND_BASE`** as an origin (in addition to `http://localhost:5173`).
- **API URL in the SPA:** For tunnel E2E, `packages/frontend/public/config/env.development.json` (or build-time config) must set **`API`** to **`API_BASE/`** so the dashboard calls the tunneled backend, not `localhost`.

Until those match, the browser may see **CORS errors** or **empty data** even if tunnels work.

---

## 3. End-to-end procedure (execute in order)

**Prerequisite:** Valid **section 0** handoff. If absent, you already emitted the all-SKIP table in section 0 — do not enter this section.

Use **`API_BASE`** and **`FRONTEND_BASE`** from the handoff in every step. Record **PASS / FAIL** and a one-line note per ID.

### E2E-1 — API: dataset list

1. Request: `GET {API_BASE}/api/visualization/datasets`
2. **Expect:** HTTP **200**, JSON body with `"datasets"` a **non-empty** array of strings (e.g. `digiklausur`, `kaggle_asag`).
3. **If FAIL:** Report status code and body snippet (no localhost).

### E2E-2 — API: one dataset payload

1. Let `D` = first element of `datasets` from E2E-1.
2. Request: `GET {API_BASE}/api/visualization/datasets/{D}`
3. **Expect:** HTTP **200**, `"visualizations"` array **length === 9**, and `viz_id` values exactly this set:  
   `class_summary`, `blooms_dist`, `solo_dist`, `score_comparison`, `concept_frequency`, `chain_coverage_dist`, `score_scatter`, `student_radar`, `misconception_heatmap`.

### E2E-2b — API: second dataset payload (optional)

If E2E-1 returned more than one slug, let `D2` = second element of `datasets`. Repeat E2E-2 with `D2`. **Expect:** same length **9** and same `viz_id` set as E2E-2. **If** only one dataset exists, mark **SKIP**.

### E2E-3 — UI: dashboard default route

1. Navigate: `{FRONTEND_BASE}/dashboard` (no query string).
2. **Expect:** Visible title containing **ConceptGrade** and **Instructor Analytics** (or **Dashboard**). No infinite loading spinner. **No** study task panel (no large task textarea at top). **No** “Export study log” button.
3. **If FAIL:** Note network errors (CORS, 404 on API) from devtools if available.

### E2E-4 — UI: dataset tabs

1. Count visible dataset tabs.
2. **Expect:** Tab count equals `datasets.length` from E2E-1 (unless UI shows a clear error banner — then FAIL and quote message).
3. Click each tab; **Expect:** No red error alert saying the load failed (unless backend stopped).

### E2E-5 — UI: summary metrics

1. With a tab selected, read the top metric row (N, MAE, Wilcoxon p, r, etc.).
2. **Expect:** Values look numeric (not blank/`NaN` for a successfully loaded dataset).

### E2E-6 — UI: full analytics (condition B)

1. Navigate: `{FRONTEND_BASE}/dashboard?condition=B`
2. **Expect:** Study task panel at top. Below metrics, **charts** visible (Bloom, SOLO, score comparison, chain coverage, concept frequency). **Per-sample table** section with headers and rows. Radar / heatmap areas present (empty-state text is OK).
3. **If FAIL:** Describe which section is missing.

### E2E-7 — UI: control condition A

1. Navigate: `{FRONTEND_BASE}/dashboard?condition=A`
2. **Expect:** Study panel visible. Summary cards + insight alerts visible. **No** full chart grid below (no Bloom/SOLO bar chart blocks like in B).

### E2E-8 — UI: study submit

1. On `?condition=B` or `A`, enter text in the task answer field, move confidence slider, click **Submit answer**.
2. **Expect:** Success state (e.g. green alert) indicating the answer was recorded.

### E2E-9 — UI: export study log

1. On a study URL, click **Export study log (JSON)**.
2. **Expect:** A JSON file downloads or browser offers download; content is a JSON array with event objects (e.g. `page_view`). **If** the sandbox blocks downloads, report **SKIP** with reason.

### E2E-10 — UI: refresh

1. On a loaded dashboard, use the header **refresh** control.
2. **Expect:** Data reloads without a full broken state (metrics still coherent).

### E2E-11 — Accessibility (smoke)

1. On `?condition=B`, use **Tab** to move focus through interactive controls to **Submit** / **Export**.
2. **Expect:** Focus is visible; no obvious keyboard trap. **SKIP** with note if the sandbox cannot send Tab reliably.

### E2E-12 — API unreachable (optional)

**Only if the developer explicitly stops the backend** during the session: trigger a refetch (refresh or tab change) and **expect** a user-visible error (e.g. red alert). Otherwise mark **N/A**.

---

## 4. Output format (mandatory)

Reply with a table:

| ID | Result | Notes |
|----|--------|--------|
| E2E-1 | PASS / FAIL / SKIP / N/A | … |
| … | … | … |

End with **Blockers** (e.g. missing URLs, CORS, ngrok interstitial) and **Environment** (browser label if known).

---

## 5. What not to do

- Do **not** treat **403** on `localhost` as a product bug — it is an **environment** mismatch.
- Do **not** mark API tests PASS without using **`API_BASE`** from the developer.
- Do **not** assume port **5000**; the tunneled URL already encodes the correct target.

---

## 6. Local-only alternative

If no tunnels are available, **all E2E steps above must be run on the developer’s machine** (same browser as the host), using local URLs. A remote browser **cannot** substitute for that without **`FRONTEND_BASE` / `API_BASE`**.

See [ConceptGrade_Dashboard_Manual_Test_Guide.md](./ConceptGrade_Dashboard_Manual_Test_Guide.md) for local commands (`check:dashboard-test-env`, `verify:visualization`).
