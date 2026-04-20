# ConceptGrade Dashboard — Gemini Code Review v7

**Date:** 2026-04-19  
**Prior reviews:** v1 → v2 → v3 → v4 → v5 → v6 (GEMINI_FEEDBACK_PAPER2_V6.md) → this document  
**Input:** `GEMINI_FEEDBACK_PAPER2_V6.md` — answers to Q-L, Q-M, Q-N  
**Status:** All 3 v6 questions resolved. Pipeline output verified with synthetic logs.

---

## 1. v6 Question Dispositions

| Q | Finding | Action taken |
|---|---------|-------------|
| Q-L | ConceptGrade bar label and green colour in Condition A introduce confound | **Fixed** — neutral "System Score" / "LLM Score" labels; blue (`#3b82f6`) for all bars; KG metadata hidden; XAI + LRM panels suppressed in Cond A |
| Q-M | `semantic_alignment_rate_manual` always 0 for Cond A; N/A wastes H2 control group | **Fixed** — Placebo Alignment Rate computed in `main()`; shown as `0.xxx ‡` in H2 table with footnote |
| Q-N | No automated pilot GO/NO-GO gate | **Fixed** — `--pilot` flag prints coloured GO/NO-GO message against 50% threshold |

---

## 2. Implemented Fixes (v7)

### Fix L — `ScoreProvenancePanel` Condition A Neutralisation

**`ScoreSamplesTable.tsx`** — condition-aware score bar labels and colours:

```typescript
const isConditionA = (condition ?? 'B') === 'A';
const c5Color  = isConditionA ? '#3b82f6' : '#16a34a';
const c5Label  = isConditionA ? 'System Score'  : 'ConceptGrade (+ KG)';
const llmLabel = isConditionA ? 'LLM Score'     : 'C_LLM (no KG)';
```

**KG metadata row suppression in Condition A:**

```typescript
// metaRows: hide chain_pct and KG-derived error labels in Cond A
const metaRows = isConditionA
  ? [
      { label: 'Baseline error', value: `${Math.abs(llmErr).toFixed(2)} pts` },
      { label: 'System error',   value: `${Math.abs(c5Err ).toFixed(2)} pts` },
    ]
  : [
      { label: 'KG chain coverage', value: `${chainPct}%` },
      { label: 'Baseline (LLM) error', value: `${Math.abs(llmErr).toFixed(2)} pts` },
      { label: 'System (KG) error',    value: `${Math.abs(c5Err ).toFixed(2)} pts` },
      { label: 'KG net effect', value: `${(Math.abs(llmErr) - Math.abs(c5Err)).toFixed(2)} pts` },
    ];
```

**XAI Concept Analysis and LRM Trace suppressed in Condition A:**

```typescript
{xai && (condition ?? 'B') !== 'A' && (/* XAI concept pills */)}
{traceData && showTrace && (condition ?? 'B') !== 'A' && (/* LRM trace */)}
```

**Isolation achieved:** Condition A educators see three numeric score bars with neutral labels and identical blue colour. No KG-chain coverage, no concept alignment pills, no LRM trace reasoning is visible.

---

### Fix M — Placebo Alignment Rate for Condition A (H2 Control Baseline)

**`analyze_study_logs.py`** — `main()` builds the hidden CONTRADICTS reference set from all Condition B `trace_interact` events, then post-hoc annotates each Condition A session:

```python
# Build CONTRADICTS reference set from Condition B trace events
b_contradicts: dict[str, set] = defaultdict(set)
for events in sessions.values():
    cond = next((e.get('condition') for e in events if e.get('condition')), None)
    if cond != 'B':
        continue
    for e in events:
        if e.get('event_type') == 'trace_interact' and \
           e.get('payload', {}).get('classification') == 'CONTRADICTS':
            ds, node_id = e.get('dataset', ''), e.get('payload', {}).get('node_id', '')
            if ds and node_id:
                b_contradicts[ds].add(node_id)

# Compute placebo alignment rate for each Condition A session
for m in session_metrics:
    if m.get('condition') != 'A':
        continue
    reference = b_contradicts.get(m.get('dataset', ''), set())
    if not reference:
        continue
    manual_concepts = [
        e['concept_id'] for e in m.get('raw_edits', [])
        if e.get('interaction_source') == 'manual' and e.get('concept_id')
    ]
    if manual_concepts:
        aligned = sum(1 for c in manual_concepts if c in reference)
        m['placebo_alignment_rate'] = round(aligned / len(manual_concepts), 3)
```

**`aggregate_by_condition`** — new key in result dict:

```python
'placebo_alignment_rate_mean': mean_of(rows, 'placebo_alignment_rate'),
```

**`print_report`** — H2 table row for `semantic_alignment_rate_manual` now shows placebo rate in Condition A column:

```python
if key == 'semantic_alignment_rate_manual':
    a_placebo = cond_a.get('placebo_alignment_rate_mean')
    a_str = f'{a_placebo:.3f} ‡' if a_placebo is not None else 'N/A  ‡'
```

**Report output (verified with synthetic logs):**

```
Concept Alignment (H2_semantic)          Cond A   Cond B
  H2 PRIMARY = manual only; CTA reported separately
────────────────────────────────────────────────────────────────
Exact alignment rate   [baseline]         0.000    0.500
Semantic rate — manual [H2 PRIMARY]     0.500 ‡    0.500
Semantic rate — click_to_add [UI-assist]    0.000    0.000
Semantic rate — combined  [reference]     0.000    0.500
Panel-before-trace rate                   0.000    0.000
‡ Cond A: placebo baseline — manual edits tested against hidden CONTRADICTS
  reference derived from Cond B traces on the same dataset.
```

**Paper Table 4 suggested wording:**

> "‡ Condition A: Placebo alignment rate — fraction of unprompted Condition A rubric edits that coincidentally matched the set of concepts the AI *would have* flagged as CONTRADICTS, derived post-hoc from Condition B trace interactions on the same dataset. This is the coincidental-alignment baseline for H2."

---

### Fix N — `--pilot` GO/NO-GO Gate

**`analyze_study_logs.py`** — argparse flag and gate logic in `main()`:

```python
parser.add_argument('--pilot', action='store_true',
                    help='Print GO/NO-GO pilot gate based on overall task completion '
                         'rate (pre-registered threshold: >50%%).')

# After print_report():
if args.pilot:
    _PILOT_THRESHOLD = 0.50
    all_completed = sum(1 for m in session_metrics if m.get('task_completed'))
    overall_rate  = round(all_completed / len(session_metrics), 3) if session_metrics else 0.0
    if overall_rate > _PILOT_THRESHOLD:
        print(f'\033[92m[PILOT GATE] GO ✓  task_completion_rate = {overall_rate:.3f}'
              f' > {_PILOT_THRESHOLD} → proceed to full study\033[0m\n')
    else:
        print(f'\033[91m[PILOT GATE] NO-GO ✗  task_completion_rate = {overall_rate:.3f}'
              f' ≤ {_PILOT_THRESHOLD} → structural review required before full study\033[0m\n')
```

**Usage:** `python analyze_study_logs.py --pilot`

**Output examples:**
```
# GO case (verified with synthetic logs — all 3 sessions completed):
[PILOT GATE] GO ✓  task_completion_rate = 1.000 > 0.5 → proceed to full study

# NO-GO case:
[PILOT GATE] NO-GO ✗  task_completion_rate = 0.400 ≤ 0.5 → structural review required
```

**Note:** The gate uses the overall rate across both conditions (not per-condition), because the pilot assesses whether the task is comprehensible to any participant — condition contamination cannot occur before the full study reveals treatment effects.

---

### Housekeeping — Duplicate `if __name__ == '__main__':` Removed

Lines 974–975 (duplicate block) have been removed. The file now ends with a single:

```python
if __name__ == '__main__':
    main()
```

---

## 3. Complete Condition A Isolation Inventory (final)

All components where KG-derived signal isolation has been applied:

| Component | What Condition A sees | What is hidden |
|-----------|----------------------|----------------|
| `ConceptFrequencyChart` | Uniform blue bars; "total frequency (coverage status not shown)" | Per-concept expected/incidental colour encoding |
| `MisconceptionHeatmap` | Static sorted list of "N students affected" per concept | Severity columns; colour intensity; drill-down |
| `StudentAnswerPanel` — list | Neutral grey row indicator; score numbers | Severity colour dot and border |
| `StudentAnswerPanel` — detail | "Student answer" neutral chip; neutral box | Severity chip label; severity-tinted background |
| `ScoreProvenancePanel` | "System Score" / "LLM Score" labels; uniform blue bars; baseline/system error | Green KG highlight; KG chain coverage; KG contribution delta; XAI concept pills; LRM trace |
| `VerifierReasoningPanel` | Not rendered | Entire trace panel (CONTRADICTS/SUPPORTS/UNCERTAIN) |
| `RubricEditorPanel` | Fully visible; editing enabled | Nothing — measured behaviour |

**Interaction paths closed for Condition A:**
- Heatmap cell click → severity-filtered `StudentAnswerPanel`: **CLOSED** (static list has no `onCellClick`)
- `VerifierReasoningPanel` trace step → Click-to-Add: **CLOSED** (panel not rendered)
- XAI concept pill hover → `xai_pill_hover` log event: **CLOSED** (XAI section suppressed)
- LRM trace display: **CLOSED** (`traceData && showTrace && condition !== 'A'` guard)

---

## 4. Verification

```
Python pipeline (synthetic 3-session logs):   PASS ✓
  Condition B causal attribution (30s):        b1=0.600, b2=1.000  → mean=0.800
  Condition B causal attribution (_min3):      b1=0.600, b2=N/A    → mean=0.600
  Condition B causal attribution (weighted):   (5×0.6 + 1×1.0)/6  → 0.667
  Condition A causal attribution:              N/A † ✓
  Placebo alignment rate (a1):                 2/4 = 0.500 ‡ ✓
  PILOT GATE GO at 1.000 > 0.50:              ✓
  Duplicate __main__ block:                    removed ✓
TypeScript (tsc --noEmit on ScoreSamplesTable):  0 errors ✓  (Q-L)
```

---

## 5. System Status

**Feature-complete for pilot study launch.**

All pre-registered metrics are implemented and verified:
- H1 (temporal causal attribution): participant-mean estimator, 15s/30s/60s windows, sensitivity (`_min3`, `_weighted`)
- H2 (semantic alignment): manual-only primary, CTA reported separately, hypergeometric null, Placebo Alignment Rate for Condition A
- Answer dwell time: by severity, by benchmark_case, seed/non-seed ratio
- Topological gap moderation: GEE Binomial/Logit (requires statsmodels)
- Pilot gate: `--pilot` flag with pre-registered 50% threshold

---

## 6. File Reference Map (final)

```
packages/frontend/src/
  components/charts/
    StudentAnswerPanel.tsx       ← Q-G severity neutralisation; Q-H 'start' sentinel (v6)
    ConceptFrequencyChart.tsx    ← Condition A neutral colour (v4)
    MisconceptionHeatmap.tsx     ← Condition A aggregated view (v5)
    ScoreSamplesTable.tsx        ← Q-L System Score neutralisation; Q3 xai_pill_hover (v7)
    ConceptKGPanel.tsx           ← dataset::conceptId cache; LRU; kg_node_drag (v3/v4)
    VerifierReasoningPanel.tsx   ← condition/dataset received (v3) — not rendered in Cond A
    RubricEditorPanel.tsx        ← rubric_edit; semantic alignment (unchanged)
    SUSQuestionnaire.tsx         ← SUS logging (unchanged)
  pages/InstructorDashboard.tsx  ← condition guard; dual-write handler (v3)
  utils/studyLogger.ts           ← 'start' in type union; getBeaconCaptureMethod (v5/v6)

packages/concept-aware/
  analyze_study_logs.py          ← Q-M placebo; Q-N --pilot; duplicate main removed (v7)
  results/
    conceptgrade_gemini_paper2_v7.md  ← this document
```
