# ConceptGrade Dashboard — Gemini Code Review v6

**Date:** 2026-04-19  
**Prior reviews:** v1 → v2 → v3 → v4 → v5 (GEMINI_FEEDBACK_PAPER2_V5.md) → this document  
**Input:** `GEMINI_FEEDBACK_PAPER2_V5.md` — answers to Q-G through Q-K  
**Status:** All 5 v5 questions resolved. `tsc --noEmit` — 0 errors. Pipeline output verified.

---

## 1. v5 Question Dispositions

| Q | Finding | Action taken |
|---|---------|-------------|
| Q-G | Severity chips in `StudentAnswerPanel` confirmed confound | **Fixed** — Condition A gets neutral "Student answer" chip; no severity colour |
| Q-H | `capture_method: null` on start event is brittle | **Fixed** — `capture_method: 'start'` explicit sentinel; type union updated |
| Q-I | `0.000` for Condition A H1 is misleading | **Fixed** — report shows `N/A †` with footnote; structurally impossible explained |
| Q-J | Condition A heatmap static box is correct isolation | **Confirmed** — no code change |
| Q-K | Methods paragraph drafted (97 words) | **Incorporated** — see Section 3 below |

---

## 2. Implemented Fixes (v6)

### Fix G — `StudentAnswerPanel` Condition A Severity Neutralisation

**`StudentAnswerPanel.tsx`** — two sub-components updated:

```typescript
const CONDITION_A_ROW_COLOR = '#6b7280'; // neutral grey — no AI severity signal

// StudentListItem: neutral grey dot + border in Condition A
const color = isConditionA
  ? CONDITION_A_ROW_COLOR
  : (SEVERITY_COLOR[answer.severity] ?? '#6b7280');

// StudentDetailPane: neutral chip replaces severity chip in Condition A
{isConditionA
  ? <Chip label="Student answer" size="small"
      sx={{ bgcolor: '#f3f4f6', color: '#374151', fontWeight: 600 }} />
  : <Chip label={label} size="small"
      sx={{ bgcolor: `${color}22`, color, fontWeight: 700 }} />
}

// Answer box: neutral background in Condition A (no severity-tinted colouring)
bgcolor: isConditionA ? '#f8fafc' : `${color}0d`
border:  isConditionA ? '1px solid #e2e8f0' : `1px solid ${color}33`
```

**Isolation achieved:** Condition A educators see student answers with score numbers (human/C_LLM/ConceptGrade) and KG metadata chips (SOLO, Bloom, chain_pct) but without any AI-derived severity label or colour that would reveal which concepts the KG considers "expected."

---

### Fix H — `capture_method: 'start'` Explicit Sentinel

**`studyLogger.ts`** — type union updated:

```typescript
capture_method: 'start' | 'beacon_sent' | 'beacon_ls_only' | 'cleanup' | null;
//              ^^^^^^^
//              'start'          — answer_view_start (event lifecycle begun)
//              'beacon_sent'    — answer_view_end via sendBeacon (reliable)
//              'beacon_ls_only' — answer_view_end via localStorage only (at-risk)
//              'cleanup'        — answer_view_end via React cleanup navigation
//              null             — legacy / unset (should not appear in new logs)
```

**`StudentAnswerPanel.tsx`** — `answer_view_start` payload:

```typescript
const startPayload: AnswerDwellPayload = {
  ...
  capture_method: 'start',   // ← was null; now explicit discriminator
  ...
};
```

**Post-study join query (clean semantics):**
```sql
SELECT s.student_answer_id, e.dwell_time_ms
FROM events s
JOIN events e ON s.session_id = e.session_id
             AND s.student_answer_id = e.student_answer_id
WHERE s.event_type = 'answer_view_start'   -- or: capture_method = 'start'
  AND e.event_type = 'answer_view_end'     -- or: capture_method IN ('beacon_sent', ...)
```

---

### Fix I — Condition A H1 Rates Reported as `N/A †`

**`analyze_study_logs.py`** — print_report section updated:

```python
# Condition A has no VerifierReasoningPanel → CONTRADICTS structurally impossible
cond_a_has_trace = (cond_a.get('contradicts_interactions_mean') or 0) > 0
...
a_str = f'{a_val:.3f}' if (a_val is not None and cond_a_has_trace) else 'N/A †'
...
print(f'  † N/A: Condition A has no trace panel; CONTRADICTS interaction structurally impossible.')
```

**Report output:**
```
Causal Attribution (multi-window)        Cond A   Cond B
  Primary = pre-registered (≥1 edit); 30s window
────────────────────────────────────────────────────────────────
Attribution rate @ 15 s (sensitivity)     N/A †    0.800
Attribution rate @ 30 s [PRIMARY H1]      N/A †    0.800
Attribution rate @ 60 s (sensitivity)     N/A †    0.800
  ↳ high-engagement only (≥3 edits)       N/A †    0.600
  ↳ edit-weighted mean                    N/A †    0.667
† N/A: Condition A has no trace panel; CONTRADICTS interaction structurally impossible.
```

**Paper Table 3 note (suggested):**
> "† N/A: Condition A educators do not receive trace explanations and therefore cannot perform the triggering CONTRADICTS interaction. The between-condition comparison uses a one-sample test against the null hypothesis that Condition B's rate equals chance."

---

## 3. Paper Methods Section Paragraph (Q-K — from Gemini)

The following 97-word paragraph is ready for insertion into **Section 4.2 "Study Conditions"** of the paper:

> "To establish a strict baseline for H2 (semantic alignment), Condition A provides standard grading analytics while strictly isolating all AI-derived diagnostic signals. The Concept Frequency chart renders in a uniform color, suppressing the AI's expected-concept encoding. The Misconception Heatmap is downgraded to a static, aggregated list, removing severity color-coding and disabling drill-down filtering. Furthermore, student answer views omit AI-generated severity labels. Condition A educators retain full capability to read student answers, view score distributions, and edit the rubric, ensuring observed differences in rubric concept selection are causally attributable to the trace explanations provided exclusively in Condition B."

---

## 4. Complete Condition A Isolation Inventory

All components where KG-derived signal isolation has been applied:

| Component | What Condition A sees | What is hidden |
|-----------|----------------------|----------------|
| `ConceptFrequencyChart` | Uniform blue bars; "total frequency (coverage status not shown)" | Per-concept expected/incidental colour encoding |
| `MisconceptionHeatmap` | Static sorted list of "N students affected" per concept | Severity columns (critical/moderate/minor); colour intensity; drill-down filtering |
| `StudentAnswerPanel` — list | Neutral grey row indicator; score numbers | Severity colour dot and border (red/orange/grey/green) |
| `StudentAnswerPanel` — detail | "Student answer" neutral chip; neutral answer box | Severity chip label (Critical miss / Moderate miss / Covered); severity-tinted background |
| `class_summary` MetricCard | `total_misconceptions` scalar count | Acceptable — aggregate count does not reveal which concepts are missing |
| `VerifierReasoningPanel` | Not rendered | Entire trace panel (CONTRADICTS/SUPPORTS/UNCERTAIN steps) |
| `RubricEditorPanel` | Fully visible; editing enabled | Nothing — rubric editing is the measured behaviour |

**Interaction paths closed for Condition A:**
- Heatmap cell click → `StudentAnswerPanel` (severity-filtered): **CLOSED** (static list has no `onCellClick`)
- `VerifierReasoningPanel` trace step click → `RubricEditorPanel` Click-to-Add: **CLOSED** (panel not rendered)

**Interaction paths preserved for Condition A:**
- `ScoreSamplesTable` row expand → `ScoreProvenancePanel` (score bars only): **OPEN** (no severity encoding)
- Manual rubric editing: **OPEN** (full capability)
- Dataset tab switching: **OPEN**
- Task submit + SUS questionnaire: **OPEN**

---

## 5. Verification

```
tsc --noEmit:                0 errors ✓
H1 report (Cond A):          N/A † on all causal attribution rows ✓
H1 report (Cond B):          0.800 (primary), 0.600 (min3), 0.667 (weighted) ✓
StudentAnswerPanel (Cond A): neutral grey chip; no severity colour ✓
StudentAnswerPanel (Cond B): full severity chip + colour ✓
capture_method on start:     'start' (not null) ✓
type union:                  'start'|'beacon_sent'|'beacon_ls_only'|'cleanup'|null ✓
```

---

## 6. Remaining Open Questions (v6)

The system is now feature-complete for the user study. The following questions are lower-priority polish items for Gemini's final review pass.

### 6.1 `ScoreProvenancePanel` — Score Bars in Condition A

`ScoreProvenancePanel` (inside `ScoreSamplesTable`) shows three score bars: Human / C_LLM / ConceptGrade. The ConceptGrade bar is coloured green (`#16a34a`) — it represents the KG-augmented score. Showing a distinctly coloured KG score bar to Condition A participants implicitly signals that a KG-based system produced a different (and visually highlighted) score.

**Q-L:** Should the ConceptGrade score bar in `ScoreProvenancePanel` be labelled differently (e.g., "System score" without the "+ KG" label) for Condition A, or is a score bar acceptable since it doesn't reveal which concepts were matched/missing?

### 6.2 `analyze_study_logs.py` — Condition A H2 Semantic Alignment Rate

Condition A can still make rubric edits. If a Condition A participant coincidentally adds a concept that appears in `session_contradicts_nodes` (which is empty for Condition A since there are no trace interactions), their `semantic_alignment_rate_manual` will be 0 by construction (no CONTRADICTS nodes to align with). The H2 metric is therefore structurally 0 for Condition A — similar to H1.

**Q-M:** Should `semantic_alignment_rate_manual` for Condition A also be reported as "N/A †" in the paper's Table 4, with the same footnote logic? Or is 0.000 appropriate here because the hypergeometric test is still meaningful (chance alignment of Condition A edits with any concept that WOULD have been flagged, as a placebo test)?

### 6.3 Pilot Study Threshold

The pre-registration document specifies a pilot threshold of >50% task completion rate before proceeding to the full study (see `project_user_study_design.md`). The `analyze_study_logs.py` report currently outputs `task_completion_rate` but does not flag whether the pilot threshold is met.

**Q-N:** Should `analyze_study_logs.py` add an explicit GO/NO-GO pilot gate output when `--pilot` flag is passed? For example:
```
PILOT GATE: task_completion_rate = 0.80 > 0.50 → GO ✓
```

---

## 7. File Reference Map (current)

```
packages/frontend/src/
  components/charts/
    StudentAnswerPanel.tsx       ← Q-G severity neutralisation; Q-H 'start' sentinel (v6)
    ConceptFrequencyChart.tsx    ← Condition A neutral colour (v4)
    MisconceptionHeatmap.tsx     ← Condition A aggregated view (v5)
    ScoreSamplesTable.tsx        ← dwell gate; citations; condition/dataset to VRP (v4/v5)
    ConceptKGPanel.tsx           ← dataset::conceptId cache; LRU; kg_node_drag (v3/v4)
    VerifierReasoningPanel.tsx   ← condition/dataset received (v3) — not rendered in Cond A
    RubricEditorPanel.tsx        ← rubric_edit; semantic alignment (unchanged)
    SUSQuestionnaire.tsx         ← SUS logging (unchanged)
  pages/InstructorDashboard.tsx  ← condition guard; dual-write handler (v3)
  utils/studyLogger.ts           ← 'start' in type union; getBeaconCaptureMethod (v5/v6)

packages/concept-aware/
  analyze_study_logs.py          ← N/A † for Cond A H1; footnote (v6)
  results/
    conceptgrade_gemini_paper2_v6.md  ← this document
```
