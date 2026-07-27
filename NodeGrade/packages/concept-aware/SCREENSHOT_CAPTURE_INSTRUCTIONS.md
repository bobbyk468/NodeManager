# Complete Instructions: Capture Screenshots for Paper 2 Figures
## For Coding Agent Execution

**Purpose:** Capture 5 high-resolution screenshots of the ConceptGrade dashboard interface  
**Total Time:** ~45 minutes (includes server startup and screenshot capture)  
**Output:** 5 PNG files saved to `docs/figures/` directory  
**Success Criteria:** All 5 images present, high resolution (≥150 DPI), properly named

---

## PREREQUISITE CHECK

Before starting, verify these files exist:

```bash
ls -la packages/concept-aware/docs/figures/ | grep -E "(usability|alignment|themes|pipeline|component)"
# Should show 5 recently created PNG files (generated earlier)

ls -la packages/frontend/package.json
# Should exist (frontend is ready to boot)

ls -la packages/backend/package.json
# Should exist (optional, but needed if backend integration required)
```

If any files are missing, STOP and report the error.

---

## PART A: START DEVELOPMENT SERVERS (10 min)

### Step A1: Kill any existing Vite processes

```bash
# Kill any process on port 5173 or 5174
lsof -ti:5173 | xargs kill -9 2>/dev/null || echo "Port 5173 was free"
lsof -ti:5174 | xargs kill -9 2>/dev/null || echo "Port 5174 was free"
sleep 2
```

### Step A2: Start the React frontend development server

```bash
cd /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/frontend

# Start Vite dev server
npm run dev > /tmp/frontend_startup.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Wait for server to be ready
sleep 8

# Check for startup success
if grep -q "Local:" /tmp/frontend_startup.log; then
    echo "✓ Frontend server started successfully"
    cat /tmp/frontend_startup.log | grep "Local:"
else
    echo "✗ Frontend startup may have issues. Check log:"
    cat /tmp/frontend_startup.log | tail -20
    exit 1
fi
```

### Step A3: Verify frontend is running

```bash
# Test if frontend responds
curl -s http://localhost:5173/ | head -20 | grep -q "<!DOCTYPE\|<html" && echo "✓ Frontend responding" || echo "⚠ Frontend may not be ready yet"
```

---

## PART B: OPEN BROWSER AND NAVIGATE (5 min)

### Step B1: Open browser to frontend

```bash
# On macOS:
open http://localhost:5173

# On Linux:
xdg-open http://localhost:5173 &

# On Windows (Git Bash):
start http://localhost:5173
```

**WAIT FOR PAGE TO LOAD** (You should see the ConceptGrade interface in ~3-5 seconds)

### Step B2: Login (if required)

If you see a login page:
- Look for test credentials (check README.md or environment variables)
- Typical test user: `test@example.com` / `password123`
- If you don't know credentials, check: `packages/frontend/.env` or `packages/frontend/.env.example`

### Step B3: Navigate to Instructor Dashboard

- Click on "Instructor Dashboard" or equivalent menu item
- Select a dataset (prefer "Kaggle ASAG" as it has most visualizations populated)
- Wait for dashboard to fully load (~5 seconds)

---

## PART C: CAPTURE FIVE SCREENSHOTS (25 min)

### Screenshot 1: Full Dashboard Teaser
**Filename:** `dashboard_teaser_full.png`  
**Purpose:** Complete overview of all three main panels  
**Time to capture:** 5 minutes

**Instructions:**

1. Make sure full InstructorDashboard is visible on screen
2. Ensure all three panels are visible:
   - Left: MisconceptionHeatmap (red/yellow/gray cells)
   - Top-right: VerifierReasoningPanel (concept graph with boxes and arrows)
   - Bottom: ScoreSamplesTable (rows with student scores)
3. Use macOS screenshot tool:
   ```bash
   # macOS: Press Cmd+Shift+5
   # Then: Click "Capture Selected Window" or drag to select entire dashboard
   # Save to Desktop (you'll move it later)
   ```
4. **Required resolution:** Minimum 1600×1000 pixels
5. Ensure the window captures the entire dashboard without scrollbars covering content

**Verification:**
```bash
# After capturing, check the image properties
file ~/Desktop/Screenshot*.png
identify ~/Desktop/Screenshot*.png | grep "1600x\|1500x\|1400x"
# Should show dimensions around 1600x1000 or similar
```

6. Move to correct location:
```bash
mv ~/Desktop/Screenshot*.png /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/dashboard_teaser_full.png
```

---

### Screenshot 2: Concept Coverage Heatmap (Close-up)
**Filename:** `heatmap_closeup.png`  
**Purpose:** Show just the heatmap with severity colors  
**Time to capture:** 5 minutes

**Instructions:**

1. In the browser, locate the MisconceptionHeatmap (top-left panel)
2. This shows:
   - Rows = Concept names (e.g., "Stack", "Queue", "Recursion")
   - Columns = Severity levels (Critical, Moderate, Minor)
   - Cells = Color-coded (red/orange/yellow/gray) with student counts
3. Use screenshot to capture **just this component**, not the entire dashboard:
   ```bash
   # macOS: Press Cmd+Shift+5
   # Drag to select ONLY the heatmap area (ignore other panels)
   ```
4. **Required resolution:** Approximately 800×400 pixels
5. Save to Desktop, then move:
```bash
mv ~/Desktop/Screenshot*.png /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/heatmap_closeup.png
```

**What should be visible:**
- ✓ Column headers: "critical", "moderate", "minor"
- ✓ Concept row labels on left
- ✓ Color-coded cells with numbers (student counts)
- ✓ Color scale: Red (critical) → Yellow (moderate) → Light gray (minor)

---

### Screenshot 3: Topological Reasoning Visualization
**Filename:** `reasoning_trace_closeup.png`  
**Purpose:** Show the TRM graph with concept nodes and edges  
**Time to capture:** 5 minutes

**Instructions:**

1. Locate the VerifierReasoningPanel (top-right of dashboard)
2. This shows:
   - Concept boxes (nodes) in a graph
   - Green checkmarks (✓) on correct concepts
   - Red X marks (✗) on incorrect/missing concepts
   - Arrows/edges showing prerequisite relationships
   - Below: Step-by-step reasoning trace text
3. Use screenshot to capture **just this panel**:
   ```bash
   # macOS: Press Cmd+Shift+5
   # Drag to select ONLY the reasoning panel (ignore heatmap and table)
   ```
4. **Required resolution:** Approximately 800×500 pixels
5. Save and move:
```bash
mv ~/Desktop/Screenshot*.png /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/reasoning_trace_closeup.png
```

**What should be visible:**
- ✓ Concept graph with colored nodes
- ✓ Green checkmarks on some nodes
- ✓ Red X marks on others
- ✓ Arrows showing concept relationships
- ✓ Text description below the graph

---

### Screenshot 4: Score Samples Table (Expanded Row)
**Filename:** `score_samples_table_expanded.png`  
**Purpose:** Show one expanded row with score comparison and concept pills  
**Time to capture:** 5 minutes

**Instructions:**

1. Locate the ScoreSamplesTable (bottom panel)
2. Find a row with student data
3. Click on the row to **expand it** (should show details like: Human Score, C_LLM Score, ConceptGrade Score)
4. The expanded row should show:
   - Score comparison (three columns)
   - Matched concepts (blue "pills" with concept names)
   - Missing concepts (gray "pills")
   - Delta indicator (green for improvement, red for degradation)
5. Use screenshot to capture **just the expanded row area**:
   ```bash
   # macOS: Press Cmd+Shift+5
   # Drag to select from expanded row start to bottom of expanded content
   ```
6. **Required resolution:** Approximately 900×300 pixels
7. Save and move:
```bash
mv ~/Desktop/Screenshot*.png /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/score_samples_table_expanded.png
```

**What should be visible:**
- ✓ Student answer ID
- ✓ Three score columns (Human, C_LLM, ConceptGrade)
- ✓ Blue concept pills (matched)
- ✓ Gray concept pills (missing)
- ✓ Delta indicator showing improvement or degradation

---

### Screenshot 5: Condition A vs Condition B Comparison
**Filename:** `condition_a_vs_b_comparison.png`  
**Purpose:** Side-by-side showing what control vs treatment see  
**Time to capture:** 5 minutes

**Instructions:**

1. You need to capture TWO states of the dashboard
2. **LEFT SIDE (Condition A - Control):**
   - Navigate to show what Condition A sees (blank panel, no visualizations)
   - If available in the UI, select "Condition A" from dropdown/toggle
   - Screenshot this state
3. **RIGHT SIDE (Condition B - Treatment):**
   - Switch to "Condition B" (full dashboard with all visualizations)
   - Screenshot this state
4. **Combine into single image:**
   ```bash
   # Use ImageMagick or similar to combine horizontally
   # Required: ImageMagick installed (comes with macOS by default or brew install imagemagick)
   
   convert -append ~/Desktop/Screenshot_A.png ~/Desktop/Screenshot_B.png \
     -bordercolor white -border 10 \
     /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/condition_a_vs_b_comparison.png
   
   # OR: If images are different sizes, use +append (horizontal):
   convert +append ~/Desktop/Screenshot_A.png ~/Desktop/Screenshot_B.png \
     /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/condition_a_vs_b_comparison.png
   ```
5. **Alternative (no ImageMagick):**
   - Use Preview app on macOS to manually combine images side-by-side
   - Or use Photoshop, GIMP, or online tool
   - Save final result as `condition_a_vs_b_comparison.png`

6. **Required resolution:** Approximately 1600×600 pixels (two 800×600 panels side-by-side)

---

## PART D: VERIFY SCREENSHOTS (5 min)

### Step D1: Check all files exist and have correct names

```bash
cd /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/

# List all PNG files
ls -lh *.png

# Check file sizes (should be reasonable, not 0 bytes)
ls -lh dashboard_teaser_full.png heatmap_closeup.png reasoning_trace_closeup.png score_samples_table_expanded.png condition_a_vs_b_comparison.png 2>/dev/null

# Count total PNG files
ls -1 *.png | wc -l
# Should output: 10 or more (5 generated + 5 captured)
```

### Step D2: Verify image quality/resolution

```bash
# Check dimensions of each screenshot
identify dashboard_teaser_full.png
identify heatmap_closeup.png
identify reasoning_trace_closeup.png
identify score_samples_table_expanded.png
identify condition_a_vs_b_comparison.png

# Expected outputs:
# dashboard_teaser_full.png: 1600x1000 or similar
# heatmap_closeup.png: 800x400 or similar
# reasoning_trace_closeup.png: 800x500 or similar
# score_samples_table_expanded.png: 900x300 or similar
# condition_a_vs_b_comparison.png: 1600x600 or similar
```

### Step D3: Verify no screenshots are corrupt

```bash
# Try to open each file to verify it's a valid PNG
for f in dashboard_teaser_full.png heatmap_closeup.png reasoning_trace_closeup.png score_samples_table_expanded.png condition_a_vs_b_comparison.png; do
    if file docs/figures/$f | grep -q "PNG image"; then
        echo "✓ $f is valid PNG"
    else
        echo "✗ $f may be corrupt"
    fi
done
```

---

## PART E: CLEANUP AND FINAL VERIFICATION (5 min)

### Step E1: Kill frontend server (if no longer needed)

```bash
# Kill the frontend dev server
kill $(cat /tmp/frontend_pid.txt) 2>/dev/null || true
echo "Frontend server stopped"
```

### Step E2: Create summary of captured files

```bash
cd /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/

echo "=== SCREENSHOT CAPTURE COMPLETE ===" 
echo ""
echo "Captured 5 new figures:"
ls -lh dashboard_teaser_full.png heatmap_closeup.png reasoning_trace_closeup.png score_samples_table_expanded.png condition_a_vs_b_comparison.png 2>/dev/null | awk '{print "  ✓", $9, "(" $5 ")"}'

echo ""
echo "Total figures available for Paper 2:"
ls -1 *.png | wc -l
echo "PNG files"

echo ""
echo "Next step: Update paper_phase2_vis2027.tex with LaTeX integration"
```

### Step E3: Verify directory structure

```bash
# Confirm all 10 figures are present
cd /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/

echo "=== FIGURE INVENTORY ===" 
echo ""
echo "Generated figures (auto-created):"
ls -1h usability_sus_scores.png study_outcome_semantic_alignment.png qualitative_themes_bars.png pipeline_architecture_5stages.png frontend_component_hierarchy.png 2>/dev/null && echo "✓ All 5 generated figures present" || echo "✗ Some generated figures missing"

echo ""
echo "Captured screenshots (manual):"
ls -1h dashboard_teaser_full.png heatmap_closeup.png reasoning_trace_closeup.png score_samples_table_expanded.png condition_a_vs_b_comparison.png 2>/dev/null && echo "✓ All 5 screenshots captured" || echo "✗ Some screenshots missing"

echo ""
echo "Total PNG count:"
ls -1 *.png 2>/dev/null | wc -l
echo "PNG files available for Paper 2"
```

---

## SUCCESS CRITERIA

All 5 of these must be true:

- [ ] `dashboard_teaser_full.png` exists and is ~1600×1000 pixels
- [ ] `heatmap_closeup.png` exists and is ~800×400 pixels
- [ ] `reasoning_trace_closeup.png` exists and is ~800×500 pixels
- [ ] `score_samples_table_expanded.png` exists and is ~900×300 pixels
- [ ] `condition_a_vs_b_comparison.png` exists and is ~1600×600 pixels

If all 5 checks pass:

```bash
echo "✓✓✓ SCREENSHOT CAPTURE COMPLETE ✓✓✓"
echo "Ready to proceed to Part F: LaTeX Integration"
```

---

## TROUBLESHOOTING

### Issue: "Port 5173 is already in use"
```bash
# Kill process using port 5173
lsof -ti:5173 | xargs kill -9
sleep 2
npm run dev
```

### Issue: "npm run dev fails to start"
```bash
# Try clearing cache
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Issue: "Dashboard doesn't show visualizations"
```bash
# Make sure you've selected a dataset that has data
# Try: Kaggle ASAG (has most students)
# Wait 5-10 seconds after selecting dataset
# Refresh page: Cmd+R or F5
```

### Issue: "Screenshots came out blurry"
```bash
# Try using Chrome/Brave's native screenshot:
# 1. Press F12 to open DevTools
# 2. Press Ctrl+Shift+P (or Cmd+Shift+P on Mac)
# 3. Type "screenshot"
# 4. Select "Capture full page" or "Capture node"
# This often gives higher quality
```

---

## NEXT STEPS (After Screenshots Complete)

Once all 5 screenshots are captured:

1. **LATEX INTEGRATION** (See: LATEX_INTEGRATION_GUIDE.md)
   - Add figures to paper_phase2_vis2027.tex
   - Compile PDF and verify
   
2. **FINAL VERIFICATION**
   - Check that all 10 figures appear in PDF
   - Verify captions are readable
   - Test PDF file size < 10 MB

3. **SUBMISSION**
   - Paper 2 is now ready for IEEE VIS 2027 (August 2026)

---

**Total Time: ~45 minutes**  
**Deliverable: 5 high-quality PNG screenshots**  
**Ready for: LaTeX integration and PDF compilation**

Let me know when you've completed the screenshots, and I'll help with the LaTeX integration!
