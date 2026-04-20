# Cursor Testing Guide v2 — Gemini Feedback Features

**Date:** April 2026  
**Purpose:** Step-by-step instructions to verify the three features implemented from the Gemini Review v2 feedback.  
**Prerequisite:** Backend running on `http://localhost:5001`, frontend on `http://localhost:5173`.

---

## Prerequisites

```bash
# Terminal 1 — backend
cd packages/backend
node_modules/.bin/nest start

# Terminal 2 — frontend
cd packages/frontend
yarn dev
```

Verify backend data is present:
```bash
ls packages/concept-aware/data/*_eval_results.json
# Should list at least 2 of: mohler, digiklausur, kaggle_asag
```

---

## Feature A: Slopegraph Vocabulary Richness Annotation Brackets (Q1)

**What changed:** The cross-dataset slopegraph now draws right-side annotation brackets grouping datasets by domain vocabulary richness, visually encoding the "preliminary observation" hypothesis.

### Test A-1: Bracket renders

1. Navigate to `http://localhost:5173/dashboard`
2. Scroll to the **Cross-Dataset MAE** slopegraph (first chart below the summary cards)

**Expected:**
- Two annotation groups visible on the RIGHT side of the chart, after the delta percentage labels:
  - A bracket (vertical spine + horizontal tick marks) spanning Mohler and DigiKlausur lines, labelled *"High KG Vocab"* / *"Richness ↑"* in small italic grey text
  - A single horizontal tick mark at the Kaggle ASAG line, labelled *"Everyday"* / *"Vocabulary"* in small italic grey text
- The brackets appear at a consistent x-position to the right of all delta labels (no overlap)

**Failure indicators:**
- Brackets invisible (SVG clipped or W too narrow) — check viewBox width is 620
- Both datasets in the same bracket group (VOCAB_CLASS map not applied)
- Bracket text overlaps the delta percentage labels

### Test A-2: Subtitle reflects preliminary framing

**Expected:**
- Below the chart title, two caption lines:
  - *"Each line = one dataset · steeper drop = KG adds more value · dashed = p ≥ 0.05"*
  - *"Preliminary observation: KG improvements are stronger in vocabulary-rich academic domains than in everyday-language domains."* (italic)

**Failure indicators:**
- Old subtitle only: *"Each line = one dataset. Steeper downward slope = KG adds more value in that domain."*

### Test A-3: Bracket adjusts when only 1 high-vocab dataset is loaded

1. Stop the backend temporarily for digiklausur (or rename its eval file to force a fetch failure)
2. Reload the dashboard

**Expected:**
- Only 1 line in the "high vocab" group → bracket renders as a **single tick mark** (not a two-point spine)
- "Everyday Vocabulary" tick still renders for Kaggle

Restore the file after testing.

---

## Feature B: Unified KG Overlay — Answer Panel Student Click (Q3 Option A)

**What changed:** Clicking a student in the Student Answer Panel (reached via heatmap → concept drill-down) now also fires an async `/sample/:id` fetch and populates the KG node overlay. Previously only the Score Samples Table row expand triggered the overlay.

### Test B-1: Answer Panel student click activates KG overlay

1. Navigate to `http://localhost:5173/dashboard`
2. Scroll to the **Misconception Heatmap** and click any coloured cell (e.g., a red "critical" cell)
3. The **Student Answer Panel** opens below
4. Click the **KG** button in the answer panel header (top-right)
5. The **KG Panel** appears beside the answer panel — nodes are in default colours (blue/green/grey)
6. In the Student Answer Panel LEFT list, click any student

**Expected:**
- After a brief delay (~0.5–1s for the `/sample/:id` fetch), the KG nodes recolour:
  - **Green** — concepts this student demonstrated
  - **Red** — concepts expected for their question but not demonstrated
  - **Grey** — concepts in the KG neighborhood not required for this question
- The KG panel legend switches from default mode to **student state overlay mode**:
  - Shows: Demonstrated (green) · Missing expected (red) · Not required (grey)
- Caption text "student state overlay active" appears below the KG title
- Hovering a green node shows tooltip: *"✓ Demonstrated by this student"*
- Hovering a red node shows tooltip: *"✗ Expected but not demonstrated"*

**Failure indicators:**
- KG nodes remain default colour after clicking a student in the answer panel
- Overlay only works from the Score Samples Table (old behaviour)
- Legend doesn't switch to overlay mode

### Test B-2: KG overlay transitions between students

1. With the KG panel open and a student already selected (overlay active):
2. Click a different student in the answer panel left list

**Expected:**
- KG nodes briefly revert to default colour while the new fetch is in-flight
- Then update to reflect the new student's concept state (different green/red pattern)
- The student detail pane on the right also updates immediately

**Failure indicators:**
- KG stays showing the previous student's overlay after switching students
- KG goes blank and doesn't recover

### Test B-3: Confirm Score Table path still works (no regression)

1. Scroll to the **Per-Sample Score Table**
2. Expand any row

**Expected:**
- Score Provenance Panel appears with concept chips
- KG overlay still activates as before (green/red/grey node coloring)
- Both paths (Answer Panel click AND Score Table expand) produce the same overlay behaviour

**Failure indicators:**
- Score Table row expand no longer triggers the overlay (regression)

### Test B-4: Silent failure when sample has no XAI data

1. Open the answer panel for a concept that has no matching entry in `{dataset}_auto_kg.json`
2. Click a student

**Expected:**
- No crash, no error UI
- KG overlay simply stays in default colour (grey/green/blue)
- No console error that breaks other functionality

---

## Feature C: Collapsible Onboarding Panel (Q6)

**What changed:** A "Show interaction guide" toggle appears at the top of the charts section (condition B only), collapsed by default to avoid cognitive overload on first load.

### Test C-1: Panel is collapsed by default

1. Navigate to `http://localhost:5173/dashboard` (condition B, default)
2. Scroll past the summary metric cards to the first divider line

**Expected:**
- A single line of text: *"New to this dashboard?"* with a button *"Show interaction guide ▼"*
- The 4-bullet guide content is NOT visible (collapsed)
- The Cross-Dataset slopegraph appears immediately below with no large block of text in between

**Failure indicators:**
- Guide content is visible immediately on page load
- The button is not present

### Test C-2: Expanding and collapsing

1. Click **"Show interaction guide ▼"**

**Expected:**
- Button label changes to *"Hide guide ▲"*
- A blue `Alert` box appears with:
  - Bold heading: *"4 key interactions — start here:"*
  - 4 numbered tips:
    1. *Click any heatmap cell → student answer list opens, pre-filtered to that severity*
    2. *Click the KG button in the answer panel → concept knowledge graph appears; drag nodes to rearrange*
    3. *Expand any row in the score table → concept gap analysis loads + KG nodes colour green / red / grey*
    4. *Click a quartile chip in the Radar chart → filter the answer list to that score range*

2. Click **"Hide guide ▲"**

**Expected:**
- Alert collapses with a smooth animation
- Button label returns to *"Show interaction guide ▼"*

**Failure indicators:**
- Alert does not animate (Collapse component not wired)
- Wrong label on button after toggle
- Tips list is incomplete (fewer than 4 items)

### Test C-3: Panel is hidden in condition A

1. Navigate to `http://localhost:5173/dashboard?condition=A`

**Expected:**
- The "Show interaction guide" button is NOT present
- Only the summary metric cards and insight alerts are visible
- No chart content at all (condition A = metrics only)

**Failure indicators:**
- Onboarding panel appears in condition A (should be hidden)

### Test C-4: Panel persists state across dataset tab switches

1. Open the guide (click "Show interaction guide ▼")
2. Switch dataset tab (e.g., Mohler → DigiKlausur)

**Expected:**
- The guide remains expanded after switching tabs
- It does NOT reset to collapsed on dataset change

---

## End-to-End Integration Test — All Three Features Together

This test exercises all three new features in a single realistic workflow:

1. Open `http://localhost:5173/dashboard`
2. Click **"Show interaction guide ▼"** → read the 4 tips → click **"Hide guide ▲"**
3. Observe the **slopegraph** — confirm vocabulary richness bracket labels are visible
4. Click a **red heatmap cell** (critical severity) for any concept
5. Click the **KG** button in the answer panel header
6. In the Student Answer Panel LEFT list, click a student
7. Observe the KG nodes recolour (green/red/grey) — **no Score Table interaction needed**
8. Click a different student in the list — confirm KG updates again
9. Scroll to the Score Table, expand a row — confirm overlay still works from this path too

**Expected at each step:** Behaviour as described in Tests A/B/C above.

---

## API Smoke Tests for New Features

```bash
# Confirm /sample/:id returns matched_concepts (needed for Answer Panel → KG overlay)
curl http://localhost:5001/api/visualization/datasets/mohler/sample/1
# Expected JSON keys: matched_concepts[], missing_concepts[], expected_concepts[]

# Confirm all 3 datasets load (needed for slopegraph bracket computation)
curl http://localhost:5001/api/visualization/datasets
# Expected: {"datasets":["mohler","digiklausur","kaggle_asag"]}

curl http://localhost:5001/api/visualization/datasets/digiklausur | python3 -m json.tool | grep mae
# Expected: "mae": 0.XXX for both C_LLM and C5_fix

curl http://localhost:5001/api/visualization/datasets/kaggle_asag | python3 -m json.tool | grep mae
# Expected: "mae": 0.XXX for both C_LLM and C5_fix
```

---

## What NOT to Test Here

The following were covered in the previous testing guide (`Cursor_Testing_Guide_Gemini_Features.md`) and are not re-tested here unless specifically checking for regressions:

- Basic heatmap cell click → answer panel open
- Master-Detail layout (left list, right detail)
- Radar quartile chip filter
- KG draggable nodes
- XAI causal text and concept chips in Score Table
- Condition A vs B gating for chart visibility
- Study log export
