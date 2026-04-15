# ConceptGrade — v4 Review: Semantic Alignment + Click-to-Add UX

**Date:** 2026-04-14  
**Context:** IEEE VIS 2027 VAST — implementing Gemini v3 review recommendations  
**Prior reviews:** v1 (ablation results), v2 (empirical follow-up), v3 (rubric edit tracking)  
**This review:** Four mechanisms for handling lexical mismatch in concept alignment measurement

---

## 1. What Was Built (Responding to v3 Recommendations)

### 1.1 The Four-Layer Solution

Gemini's v3 question was: *"How do you plan to handle cases where an educator wants to edit a rubric concept using terminology that is semantically identical to a CONTRADICTS node, but lexically different (e.g., typing 'learning rate' instead of 'step size')?"*

We implemented all four recommended mechanisms:

| Layer | Mechanism | Where | Status |
|-------|-----------|--------|--------|
| Preventative | Click-to-Add on CONTRADICTS chips | `RubricEditorPanel.tsx` | ✓ Built |
| Analytical | Fuzzy + alias matching at log time | `conceptAliases.ts` | ✓ Built |
| Post-hoc | Semantic resolution in Python | `analyze_study_logs.py` | ✓ Built |
| Qualitative | Cued Retrospective Think-Aloud | Study protocol | Planned |

### 1.2 Click-to-Add (Layer 1 — Preventative)

CONTRADICTS chips in the educator-facing panel are now actionable:

```
[+ learning rate]  [+ chain rule]  [+ error reduction]
```

- Each chip shows `AddCircleOutlineIcon` with tooltip: *"Click to Add this concept to your rubric"*
- On click: `handleEdit(nodeId, nodeId, 'add', 'click_to_add')` — logs the exact canonical KG node ID
- `interaction_source: 'click_to_add'` in the payload (vs `'manual'` for button clicks)
- Eliminates lexical ambiguity entirely for chips clicked directly

### 1.3 Semantic Alias Utility (`src/utils/conceptAliases.ts`)

Three-layer matching:

```
Layer 1: Normalize (lowercase, underscore→space, trim whitespace)
Layer 2: Domain alias dictionary (DOMAIN_ALIASES — 25 canonical concepts, ~100 synonyms)
Layer 3: Levenshtein similarity ratio ≥ 0.80

matchesContradictsNode('step size', ['learning_rate'])  → { matched: true, score: 1.0, via: alias }
matchesContradictsNode('learnin rate', ['learning_rate']) → { matched: true, score: 0.92, via: fuzzy }
matchesContradictsNode('dropout', ['regularization'])    → { matched: false, score: 0.07 }
```

Domains covered: Neural Network / ML (DigiKlausur) and CS Data Structures (Mohler).

### 1.4 Updated Payload (per `rubric_edit` event)

```json
{
  "event_type": "rubric_edit",
  "payload": {
    "edit_type": "add",
    "concept_id": "chain_rule",
    "within_15s": false,
    "within_30s": false,
    "within_60s": true,
    "time_since_last_contradicts_ms": 25000,
    "source_contradicts_nodes_60s": ["chain_rule"],
    "concept_in_contradicts_exact": true,
    "concept_in_contradicts_semantic": true,
    "semantic_match_score": 1.0,
    "semantic_match_node": "chain_rule",
    "panel_focus_ms": 1713000050000,
    "panel_focus_before_trace": false,
    "interaction_source": "manual"
  }
}
```

### 1.5 Rolling 60-Second Window (DashboardContext.tsx)

Replaced single `lastContradicts: { nodeId, timestamp_ms }` with:

```typescript
recentContradicts: ContradictsEntry[]   // pruned to 60 s on every PUSH_CONTRADICTS
```

`RubricEditorPanel` reads this array at edit time and filters to 15 s / 30 s / 60 s windows — no researcher DoF (all windows pre-logged).

### 1.6 Condition A Now Gets the Rubric Panel

Both conditions see `RubricEditorPanel` after task submission:
- **Condition B:** Shows CONTRADICTS chip strip + LRM-flagged labels + Click-to-Add
- **Condition A:** Shows blank rubric concept list (no trace context)

This enables true between-condition comparison of *what* educators edit, not just *whether* they edit.

### 1.7 Updated Analyzer (`analyze_study_logs.py`)

New session metrics:

| Metric | Definition |
|--------|-----------|
| `rubric_edits_within_15s/30s/60s` | Count of edits within each window |
| `rubric_edits_exact_aligned` | Edits with exact concept ID in CONTRADICTS nodes |
| `rubric_edits_semantic_aligned` | Edits with fuzzy/alias match (broader coverage) |
| `rubric_edits_click_to_add` | Edits via chip click (zero ambiguity) |
| `rubric_panel_before_trace` | Edits by educators who opened panel before trace view |
| `concept_alignment_hyper_p` | Per-session hypergeometric p-value for semantic alignment |

Aggregated rates (both conditions):
- `causal_attribution_rate_15s/30s/60s` — pre-registered sensitivity analysis
- `exact_alignment_rate`, `semantic_alignment_rate` — H2 evidence
- `panel_before_trace_rate` — reasoning strategy classification

### 1.8 Hypergeometric Null Model

Implemented in `_hypergeometric_p(k, N, K, n)` using `scipy.stats.hypergeom`:
- **k** = edits semantically aligned with CONTRADICTS nodes
- **N** = rubric size (estimated, default 20)
- **K** = number of CONTRADICTS-flagged concepts
- **n** = total edits

Synthetic test (2 edits, 2/2 aligned, 2 CONTRADICTS from a 20-concept rubric): **p = 0.0053** ✓

---

## 2. Test Results

| Test | Result |
|------|--------|
| TypeScript compilation (`tsc --noEmit`) | ✓ 0 errors |
| Python syntax check | ✓ OK |
| Synthetic 2-session study (A + B) | ✓ Correct multi-window rates |
| Hypergeometric p (2/2 aligned, K=2, N=20, n=2) | ✓ p=0.0053 |
| Click-to-Add chip click → `interaction_source='click_to_add'` | ✓ Verified |
| Alias match: 'step size' → 'learning_rate' | ✓ score=1.0 |
| Fuzzy match: 'learnin rate' → 'learning_rate' | ✓ score=0.92 |
| Fuzzy reject: 'dropout' vs 'regularization' | ✓ score=0.07, not matched |
| Panel-before-trace: Condition A panel opens before trace | ✓ panel_focus_before_trace=True |
| Condition A rubric panel shown (no CONTRADICTS strip) | ✓ condition A → empty sessionContradictsNodes |

---

## 3. Design Decisions for Review

### Q1 — Auto-Suggest Typeahead: Skipped

Gemini recommended a Fuse.js fuzzy typeahead for free-text concept additions. We skipped this for now because:

1. **Click-to-Add covers the primary case**: educators clicking CONTRADICTS chips already get canonical IDs with zero ambiguity. This is the interaction the study is designed to measure.
2. **Manual add buttons target rubric concepts**: the existing "Increase weight / Decrease weight / Remove" buttons operate on pre-populated rubric concepts (already canonical IDs).
3. **Post-hoc semantic resolution handles the residual**: educators who type custom text (unlikely given the constrained UI) get fuzzy-matched in `analyze_study_logs.py`.

**Open question**: Is this justifiable for the VIS paper? Or does Gemini think free-text entry is needed for ecological validity?

### Q2 — The `panel_focus_before_trace` Flag

This flag distinguishes two reasoning strategies:
- **Trace-first**: educator views the LRM reasoning trace, then edits rubric (our predicted majority path in Condition B)
- **Rubric-first**: educator edits rubric based on prior domain knowledge, then views trace (happens when panel opens immediately after task submit before any trace interaction)

**Predicted distribution** (to confirm in pilot):
- Condition B: most educators will view at least one trace before the rubric panel appears (panel only shows after task submit, which happens after exploration)
- Condition A: all edits will be `panel_focus_before_trace=True` since no trace panel exists

If Condition B shows meaningful `panel_before_trace_rate > 0`, it suggests some educators front-load rubric editing before exploring traces — a finding worth reporting.

### Q3 — Alias Dictionary Coverage

The DOMAIN_ALIASES dictionary covers ~25 canonical concepts across two domains (neural networks, CS data structures). Coverage assumptions:
- DigiKlausur (neural networks): activation functions, gradient descent, regularization, architecture components → high coverage
- Mohler (CS): linked lists, trees, recursion, pointers, complexity → moderate coverage

**Gap**: Kaggle ASAG (science domain — biology, physics) is not covered by the current alias dict. Since we're not using Kaggle ASAG in the user study (it's for the ML accuracy paper), this is acceptable.

**Open question**: Should we extend the alias dict to the science domain as a precaution, or rely on fuzzy matching for that dataset?

### Q4 — Semantic vs Exact Alignment in the Paper Claim

We now report two alignment rates:
- `exact_alignment_rate`: strict ID match (replicable by any future reader)
- `semantic_alignment_rate`: fuzzy + alias match (captures synonymy, harder to replicate without the alias dict)

**For the primary claim (H2)**: Should we use exact or semantic as the primary metric? 

Argument for **exact**: reproducible, conservative, no question about the alias dict's validity.  
Argument for **semantic**: more ecologically valid (educators use natural language, not KG node IDs).  
Argument for **both**: report exact as primary, semantic as robustness check. Frame in the paper: *"To account for natural language variation, we additionally computed semantic alignment rate using a domain alias dictionary..."*

### Q5 — Click-to-Add as a Study Design Choice

The Click-to-Add mechanism has a dual role:
1. **Measurement utility**: guarantees exact canonical node IDs for clicked CONTRADICTS chips → zero ambiguity for causal attribution
2. **Study design validity concern**: if educators mostly use Click-to-Add, is the study measuring their *understanding of the concept* or just their *ability to click a chip*?

**Mitigation**: Click-to-Add is opt-in (educators can also use the "Add" buttons on the rubric list for those concepts). The chip strip displays concepts the LRM flagged, not concepts the educator types — so clicking it is an active endorsement of the LRM's suggestion.

**Open question**: Does this mechanism conflate "I agree with the LRM's concept flag" with "I would have added this concept independently"? Should the panel include a confirmation dialog: "Are you adding [chain rule] because the LRM flagged it, or based on your own expertise?"

---

## 4. Remaining Gaps

| Item | Status |
|------|--------|
| Backend `POST /api/study/log` endpoint | Not yet built |
| Mohler batch evaluation (cllm/c5 per-sample) | Critical pre-submission blocker |
| IRB protocol for Condition A rubric panel (new) | Needs update |
| Pilot study (2–3 participants) | Not yet scheduled |
| Auto-suggest typeahead (Fuse.js) | Deliberately deferred |
| Cued Retrospective Think-Aloud protocol | Designed but not scripted |
| Science domain aliases for Kaggle ASAG | Not needed for user study |

---

## 5. Questions for This Review

1. **Q1 (Typeahead)**: Is the Click-to-Add + post-hoc semantic resolution sufficient, or do we need free-text typeahead for the user study to have ecological validity?

2. **Q2 (Primary metric for H2)**: Exact alignment rate or semantic alignment rate as the primary claim? Or report both with semantic as a robustness check?

3. **Q3 (Click-to-Add validity)**: Does the chip-click mechanism conflate "I endorse the LRM's flag" with "I would edit this concept independently"? Should we add a confirmation step?

4. **Q4 (Alias dict scope)**: Should the domain alias dictionary be extended to science/biology for the Kaggle ASAG condition (even though it's not in the user study)?

5. **Q5 (Panel-before-trace interpretation)**: If a meaningful fraction of Condition B educators open the rubric before viewing any trace, does this undermine the causal direction claim? What's the threshold (% panel-before-trace) at which the causal story becomes untenable?
