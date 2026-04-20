# Cursor Testing Guide — ConceptGrade Dashboard (Gemini Feature Set)

**Date:** April 2026  
**Purpose:** Instructions for Cursor (or any testing agent) to verify all 8 Gemini-recommended features implemented in the ConceptGrade instructor analytics dashboard.

---

## Prerequisites

### 1. Start the backend
```bash
cd packages/backend
node_modules/.bin/nest start
# Should print: "Application is running on: http://localhost:5001"
```

### 2. Start the frontend dev server
```bash
cd packages/frontend
yarn dev
# Should be available at http://localhost:5173 (or Vite's default)
```

### 3. Verify backend data is present
```bash
ls packages/concept-aware/data/*_eval_results.json
# Should list: mohler_eval_results.json, digiklausur_eval_results.json, kaggle_asag_eval_results.json
```

---

## Feature 1: Severity Default Filter

**What to test:** When a heatmap cell is clicked, the Student Answer Panel opens pre-filtered to that severity.

**Steps:**
1. Navigate to `http://localhost:5173/dashboard`
2. Switch to any dataset tab (Mohler 2011, DigiKlausur, or Kaggle ASAG)
3. Scroll down to the **Misconception Heatmap** section
4. Click any red cell (labeled "critical" column)
5. The **Student Answer Panel** should appear below

**Expected behavior:**
- The severity filter toggle buttons show "Critical" as the active/selected option
- The student list shows ONLY critical-severity students for that concept
- The toggle group buttons are visible: All / Critical / Moderate / Minor / Covered

**Failure indicators:**
- Filter defaults to "All" instead of the clicked severity
- No students appear (filter too narrow — check that the concept has critical students)

---

## Feature 2: Master-Detail Layout (Student Answer Panel)

**What to test:** Student list on left, detail pane on right — no accordion jumping.

**Steps:**
1. Click any heatmap cell to open the Student Answer Panel
2. Observe the layout

**Expected behavior:**
- LEFT pane (~280px fixed width): scrollable list of student items, each showing:
  - Colored severity dot (red=critical, orange=moderate, grey=minor, green=covered)
  - Student ID (e.g., "#42")
  - 1-line truncated answer preview (max 55 chars with "…")
  - Two score badges: **H** (human) and **C5** (ConceptGrade) side-by-side
- RIGHT pane (flex-grow): fixed detail panel showing full student answer
  - Score breakdown: Human / C_LLM / ConceptGrade
  - Full question text (italicized)
  - Full student answer text (in colored box)
  - Metadata chips: SOLO level, Bloom level, KG coverage %
- Clicking different students in the left list updates the right pane **without any layout jump**

**Failure indicators:**
- Content is in a vertical accordion (old design)
- Clicking a student scrolls/jumps the page
- Both panes not visible simultaneously

---

## Feature 3: Bidirectional Brushing — Radar → Answer Panel

**What to test:** Clicking a quartile chip in the Radar chart filters the Student Answer Panel to that score range.

**Steps:**
1. Make sure a heatmap cell is already selected (Student Answer Panel is open)
2. Scroll up to the **Cognitive Profile Radar** chart
3. Click one of the colored quartile chips above the radar (e.g., the purple "Low Scorers (Q1)" chip)

**Expected behavior:**
- The chip turns solid (filled background with white text) to show selection
- A "Clear filter" chip appears next to the quartile chips
- The Student Answer Panel updates its list to show only students in Q1 (lowest ~25% of scores)
- A badge appears in the answer panel header: "Radar Q1 filter active"
- Clicking the same quartile chip again deselects it (list returns to full)
- Clicking "Clear filter" chip also deselects

**Also test:**
- Non-selected radar lines fade (opacity ~30%) when a quartile is selected
- Selected quartile line remains at full opacity

**Failure indicators:**
- Radar chip click has no effect on answer panel
- Answer panel shows same students regardless of quartile filter
- No "filter active" badge appears

---

## Feature 4: KG Draggable Nodes

**What to test:** Nodes in the KG Subgraph panel can be dragged to reorganize layout.

**Steps:**
1. Click any heatmap cell to open the Student Answer Panel
2. Click the **"KG"** button in the Student Answer Panel header (top-right of the panel)
   - OR: wait for the "View KG subgraph for this concept" button and click it
3. The ConceptKGPanel should appear
4. Click and drag one of the circular concept nodes

**Expected behavior:**
- The cursor changes to `grab` on hover over a node
- The cursor changes to `grabbing` during drag
- The node moves smoothly following the cursor
- Edge lines update in real-time as the node moves (edges stay connected)
- Node stays within SVG bounds (cannot be dragged outside)
- Dragging the central concept node (larger, bold text) also works
- Releasing the mouse button drops the node in the new position

**Failure indicators:**
- Node doesn't move when dragged
- Edges don't update during drag (node detaches from edges)
- Node jumps to wrong position on drag start
- Node can be dragged outside the SVG frame

---

## Feature 5: KG Student State Overlay

**What to test:** When a student is selected in the ScoreSamplesTable, KG nodes change color to show which concepts that student demonstrated vs. missed.

**Steps:**
1. Make sure a concept's KG panel is open (Feature 4 prerequisites)
2. Scroll to the **Per-Sample Score Table** (ScoreSamplesTable)
3. Click any row to expand it — the Score Provenance Panel appears below the row
4. Wait ~1 second for the concept analysis to load
5. Scroll back up to the KG Panel

**Expected behavior:**
- KG nodes change color:
  - **Green** (`#16a34a`): concept was demonstrated by this student (in their matched_concepts)
  - **Red** (`#dc2626`): concept was expected for this question but NOT demonstrated
  - **Grey** (`#9ca3af`): concept is in the KG but not required for this question
- The KG panel legend switches from default mode to "student state overlay" mode:
  - Default legend shows: Selected concept (blue) / Expected in rubric (green) / Related (grey)
  - Overlay legend shows: Demonstrated (green) / Missing (expected, red) / Not required (grey)
- The caption "student state overlay active" appears below the KG title
- Node tooltips (hover any node) show the student state annotation:
  - "✓ Demonstrated by this student" (green italic)
  - "✗ Expected but not demonstrated" (red italic)

**Failure indicators:**
- All KG nodes remain blue/green/grey (default colors) after selecting a student in the table
- Legend doesn't switch to overlay mode
- Tooltips don't show student state annotation

---

## Feature 6: XAI Causal Text (Score Provenance)

**What to test:** Expanding a row in the Score Samples Table shows explicit concept names with causal explanation.

**Steps:**
1. Scroll to the **Per-Sample Score Table**
2. Click any row that has a "▼" (green) delta chip — these rows where ConceptGrade improved over C_LLM

**Expected behavior in the expanded Score Provenance Panel:**
- **Score bars** (left column): three colored progress bars — Human (grey), C_LLM (red), ConceptGrade green
- **Metadata** (right column): KG chain coverage %, SOLO level, Bloom level, error values
- **KG net effect** row: shows "Reduced error by X.XXX" (not just a number)
- **Concept Analysis** section (loads via API):
  - If concepts are missing: italic causal text, e.g.:  
    _"KG penalised this answer because 2 expected concepts were not demonstrated:"_  
    — followed by red chips for each missing concept (e.g., "backpropagation", "gradient descent")
  - Green chips for demonstrated concepts: _"Concepts demonstrated (3):"_ + green pills
  - If all concepts matched: _"All expected concepts were demonstrated — KG alignment is strong."_
- Loading spinner visible briefly while fetching concept analysis

**Failure indicators:**
- "Loading concept analysis…" spinner never resolves
- Concept chips not visible (check browser console for API errors)
- Causal text is missing (only chips shown)
- Chips appear but all unlabeled or show raw concept IDs

---

## Feature 7: Cross-Dataset Comparison Slopegraph

**What to test:** The slopegraph appears at the top of the charts section showing all 3 datasets side-by-side.

**Steps:**
1. Navigate to `/dashboard` (condition B, which is default)
2. Scroll down past the summary metric cards — the first chart section should be the slopegraph

**Expected behavior:**
- SVG slopegraph with two vertical columns labeled "C_LLM (no KG)" and "ConceptGrade (+ KG)"
- One slope line per dataset (up to 3 lines: Mohler, DigiKlausur, Kaggle ASAG)
- Each line shows:
  - Left dot: C_LLM MAE value with dataset label below (e.g., "Mohler", "CS / Q&A")
  - Right dot: ConceptGrade MAE value with delta label (e.g., "▼32.4%")
  - Line is **solid** if p < 0.05, **dashed** if not significant
  - "n.s." label appears on the right for non-significant results
- Summary chips below chart: "Mohler: ▼X.X% MAE", "DigiKlausur: ▼X.X% MAE", "Kaggle ASAG: ▲X.X% MAE (n.s.)"
- Y-axis reference lines visible at 0.1 intervals
- Chart does NOT appear in condition A (`?condition=A`)

**Failure indicators:**
- Chart area is blank (API fetch failed — check backend is running)
- Only 1-2 lines appear (some dataset fetches failing)
- All lines dashed (wrong p-value threshold)
- Chart renders in condition A (should be hidden)

---

## Feature 8: Score Provenance Framing ("Reduced error by X")

**What to test:** The KG net effect row in Score Provenance uses relative framing, not just raw error values.

**Steps:**
1. Expand any row in the Score Samples Table
2. Look at the **KG net effect** row (bottom of the right column in Score Provenance Panel)

**Expected behavior:**
- If ConceptGrade improved: `"Reduced error by 0.XXX"` (green text)
- If ConceptGrade was worse: `"Increased error by 0.XXX"` (red text)
- If no change (within 0.01): `"No change"` (grey text)
- Try several rows to see each case

**Failure indicators:**
- Shows raw number like "0.123" without context
- Always shows same message regardless of direction

---

## Condition Gating Test

**What to test:** Condition A shows only summary cards; Condition B shows all charts.

**Steps:**
1. Visit `http://localhost:5173/dashboard?condition=A`
2. Verify only the 6 summary metric cards and insight alerts are visible
3. No charts (Bloom, SOLO, Radar, Heatmap, Slopegraph, etc.) should appear
4. A "Study Task" panel with a textarea and confidence slider should appear
5. An "Export study log (JSON)" button should be visible

6. Visit `http://localhost:5173/dashboard?condition=B`
7. All charts should appear
8. Study Task panel and Export button visible
9. Submit the task form — click "Submit answer" — success alert should appear

---

## Linking Flow Integration Test (End-to-End)

This tests that all interactive features work together in one flow:

1. Open `/dashboard` (default condition B)
2. Select the **Mohler** dataset tab
3. In the **Radar chart**, click the "Low Scorers (Q1)" quartile chip
4. Scroll down to the **Heatmap** — click a red "critical" cell for any concept
5. The **Student Answer Panel** opens with:
   - Severity filter set to "Critical"
   - "Radar Q1 filter active" badge
   - Only showing low-scoring + critical students
6. Click the **KG** button in the Student Answer Panel header
7. The **KG Panel** opens beside the Answer Panel
8. Scroll to the **Score Samples Table** — click any row
9. Confirm KG nodes change color (green/red/grey)
10. Scroll back — confirm KG legend shows "student state overlay mode"
11. Hover a node — tooltip shows "✓ Demonstrated" or "✗ Expected but not demonstrated"
12. Drag a KG node — confirm smooth movement with edge updates

**Expected:** All 7 steps produce the described behavior.  
**Failure:** Any step that doesn't match is a regression — report which step failed.

---

## API Endpoint Smoke Tests

Run these curl commands to confirm backend is serving data correctly before testing the UI:

```bash
# 1. List datasets
curl http://localhost:5001/api/visualization/datasets
# Expected: {"datasets":["mohler","digiklausur","kaggle_asag"]}

# 2. Dataset summary (replace 'mohler' with any dataset)
curl http://localhost:5001/api/visualization/datasets/mohler | python3 -m json.tool | head -30
# Expected: JSON with n, metrics.C_LLM.mae, metrics.C5_fix.mae, visualizations[]

# 3. Concept answers
curl "http://localhost:5001/api/visualization/datasets/mohler/concept/backpropagation"
# Expected: {"concept_id":"backpropagation","answers":[...]}

# 4. KG subgraph
curl "http://localhost:5001/api/visualization/datasets/mohler/kg/concept/backpropagation"
# Expected: {"nodes":[{"id":"...","is_central":true,...}],"edges":[...]}

# 5. Sample XAI (replace '1' with any sample id from the score table)
curl "http://localhost:5001/api/visualization/datasets/mohler/sample/1"
# Expected: {"matched_concepts":[...],"missing_concepts":[...],"expected_concepts":[...]}
```

If any of these return 404 or empty arrays, check:
- `packages/concept-aware/data/{dataset}_eval_results.json` exists
- `packages/concept-aware/data/{dataset}_auto_kg.json` exists  
- `packages/concept-aware/data/{dataset}_dataset.json` exists

---

## Known Limitations (Not Bugs)

- The slopegraph chart is invisible if only 1 dataset has loaded (it shows when ≥ 2 datasets have valid data)
- KG panel only shows if `{dataset}_auto_kg.json` exists for that dataset
- Student state overlay requires a row to be expanded in the Score Samples Table (not the Student Answer Panel click)
- Quartile boundaries are computed at runtime from the loaded dataset scores — filter counts will vary by dataset
