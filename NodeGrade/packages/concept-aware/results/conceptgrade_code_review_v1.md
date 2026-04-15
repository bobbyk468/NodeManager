# ConceptGrade — Code Review Request v1

**Date:** 2026-04-14  
**Purpose:** Request a structured code review of the user study instrumentation layer before the pilot study. The system is feature-complete; this review is about correctness, edge-case robustness, and measurement validity — not new features.  
**Reviewer:** Gemini 2.5 Pro  
**Stack:** React 18 + TypeScript + MUI v5 (frontend), NestJS (backend), Python 3.12 (analysis)

---

## System Architecture (Brief)

```
Student answers
      ↓
[Stage 1] KG generation        generate_auto_kg_prompt.py
[Stage 2] Concept matching     concept_matching.py  
[Stage 3a] LRM Verifier        lrm_verifier.py  ← Gemini Flash / DeepSeek-R1
[Stage 3b] Trace parser        trace_parser.py  → ParsedStep[]
[Stage 4]  C5 scoring          c5_scorer.py
      ↓
NestJS API  →  React Dashboard (11 linked panels)
                    ↓
              [USER STUDY LAYER — this review]
              DashboardContext ← VerifierReasoningPanel
                    ↓
              RubricEditorPanel  →  studyLogger.ts  →  localStorage / POST /api/study/log
                    ↓
              analyze_study_logs.py  →  GEE Binomial/Logit moderation analysis
```

---

## Layer 1 — DashboardContext.tsx

Central state machine. All study-relevant metrics flow through here.

**Key state fields (study-relevant):**

```typescript
interface DashboardSelectionState {
  recentContradicts: ContradictsEntry[];  // rolling 60-s window, pruned on each PUSH
  lastTraceGapCount: number;              // leap count from current trace (moderator H1)
  lastGroundingDensity: number;           // fraction of steps with kg_nodes (moderator)
  // ...selection state omitted
}

// Rolling window logic (in reducer):
case 'PUSH_CONTRADICTS': {
  const now = Date.now();
  const pruned = state.recentContradicts.filter(
    e => now - e.timestamp_ms < ROLLING_WINDOW_MS,  // ROLLING_WINDOW_MS = 60_000
  );
  return {
    ...state,
    recentContradicts: [...pruned, { nodeId: action.nodeId, timestamp_ms: now }],
  };
}
```

**Potential issues to review:**
1. The rolling window is pruned only on PUSH, not on read. If an educator views the rubric panel a long time after their last trace interaction, `recentContradicts` may still contain entries that are now >60 s old (because no new PUSH occurred to trigger pruning). The 60 s / 30 s / 15 s windows are re-filtered at read time in `RubricEditorPanel.handleEdit` — but is the re-filtering correct?
2. `lastTraceGapCount` and `lastGroundingDensity` are set via `useEffect` in `VerifierReasoningPanel` whenever `parsedSteps` changes. If multiple students are selected in rapid succession, could stale values from a previous trace be used in a rubric edit?

---

## Layer 2 — VerifierReasoningPanel.tsx (gap detection + grounding density)

**Gap detection (node-only adjacency, v10 lock):**

```typescript
function hasTopologicalGap(stepA: ParsedStep, stepB: ParsedStep): boolean {
  if (stepA.kg_nodes.length === 0 || stepB.kg_nodes.length === 0) return false;
  const nodesA = new Set(stepA.kg_nodes);
  return !stepB.kg_nodes.some(n => nodesA.has(n));  // gap iff no shared concept node
}
```

**Grounding Density + Gap Count published to context:**

```typescript
const topologicalGapCount = useMemo(() => {
  let count = 0;
  for (let i = 1; i < parsedSteps.length; i++) {
    if (hasTopologicalGap(parsedSteps[i - 1], parsedSteps[i])) count++;
  }
  return count;
}, [parsedSteps]);

const groundingDensity = useMemo(() => {
  if (parsedSteps.length === 0) return 0;
  const grounded = parsedSteps.filter(s => s.kg_nodes.length > 0).length;
  return grounded / parsedSteps.length;
}, [parsedSteps]);

useEffect(() => {
  setTraceGapCount(topologicalGapCount);
}, [topologicalGapCount, setTraceGapCount]);

useEffect(() => {
  setGroundingDensity(groundingDensity);
}, [groundingDensity, setGroundingDensity]);
```

**CONTRADICTS interaction → rolling window:**

```typescript
const handleSelectStep = useCallback(
  (stepId: number) => {
    const nextId = selectedStepId === stepId ? null : stepId;
    setSelectedStepId(nextId);
    if (nextId !== null) {
      const step = parsedSteps.find((s) => s.step_id === nextId);
      if (step) {
        if (step.classification === 'CONTRADICTS') {
          const nodeId = step.kg_nodes[0] ?? `step_${step.step_id}`;  // ← fallback?
          pushContradicts(nodeId);
        }
        if (onNodeClick && step.kg_nodes.length > 0) {
          onNodeClick(step.kg_nodes[0]);
        }
      }
    }
  },
  [selectedStepId, parsedSteps, onNodeClick, pushContradicts],
);
```

**Potential issues to review:**
1. The fallback `step.kg_nodes[0] ?? \`step_${step.step_id}\`` for CONTRADICTS steps with empty `kg_nodes`: this pushes a synthetic node ID (`step_3`, `step_7`) into `recentContradicts`. In `RubricEditorPanel`, the semantic matching (`matchesContradictsNode`) will try to fuzzy-match `step_3` against educator edits — and will never match. Is this the intended behaviour, or should we skip the PUSH entirely when `kg_nodes` is empty?
2. Toggle behaviour: clicking a selected step deselects it (`nextId = null`) but does NOT push a CONTRADICTS event even if the step is CONTRADICTS. This means a de-selection is not counted. Is that correct for the causal attribution model?
3. `handleNodePillClick` also pushes CONTRADICTS for any node pill click on a CONTRADICTS step. This could double-count interactions: if an educator clicks the step card AND then clicks a node pill within that card, both fire. Is double-counting intentional (stronger signal of engagement) or a bug?

---

## Layer 3 — RubricEditorPanel.tsx (causal attribution at edit time)

**Multi-window attribution:**

```typescript
function handleEdit(conceptId, conceptLabel, editType, source = 'manual') {
  const now = Date.now();

  // Re-filter from the rolling 60-s window at the moment of edit
  const w60 = recentContradicts.filter(e => now - e.timestamp_ms <= 60_000);
  const w30 = w60.filter(e => now - e.timestamp_ms <= 30_000);
  const w15 = w30.filter(e => now - e.timestamp_ms <= 15_000);

  const mostRecent = w60.length > 0 ? w60[w60.length - 1] : null;

  const { matched: semanticMatch, bestMatch, score } = matchesContradictsNode(
    conceptId,
    sessionContradictsNodes,  // full session accumulation, not just 60-s window
  );

  const payload: RubricEditPayload = {
    // ...
    within_15s: w15.length > 0,
    within_30s: w30.length > 0,
    within_60s: w60.length > 0,
    time_since_last_contradicts_ms: mostRecent ? now - mostRecent.timestamp_ms : null,
    source_contradicts_nodes_60s: [...new Set(w60.map(e => e.nodeId))],
    concept_in_contradicts_exact: sessionContradictsNodes.includes(conceptId),
    concept_in_contradicts_semantic: semanticMatch,
    semantic_match_score: score > 0 ? score : null,
    semantic_match_node: bestMatch,
    session_contradicts_nodes: sessionContradictsNodes,
    panel_focus_before_trace: panelBeforeTrace.current,
    interaction_source: source,
    trace_gap_count: lastTraceGapCount,
    grounding_density: lastGroundingDensity,
  };

  logEvent(condition, dataset, 'rubric_edit', payload as unknown as Record<string, unknown>);
}
```

**panelBeforeTrace capture:**

```typescript
const panelBeforeTrace = useRef<boolean>(sessionContradictsNodes.length === 0);
```

This captures the value at mount. If `sessionContradictsNodes` is populated before the panel renders (e.g., the educator clicked a trace step before opening the rubric panel), `panelBeforeTrace.current` will be `false`. If it was empty at mount but populates later (educator views trace AFTER opening the panel), `panelBeforeTrace.current` remains `true`.

**Potential issues to review:**
1. **`semantic_match_score: score > 0 ? score : null`** — this sets `score = null` when the best Levenshtein score is exactly 0 (completely different strings). But it also passes through 0-score values as null even if the alias matched (alias matches return `score = 1.0`). Is the `score > 0` guard correct? Should it be `score > 0 || matched === true`?
2. **`sessionContradictsNodes` vs `source_contradicts_nodes_60s`**: The semantic matching is run against `sessionContradictsNodes` (all-time accumulation) but the multi-window fields use `recentContradicts` (60-s rolling window). This is intentional by design — concept alignment (H2) is session-wide, not time-bounded. But it means a rubric edit could be flagged as `concept_in_contradicts_semantic = true` based on a CONTRADICTS interaction from 45 minutes ago. Is this the intended semantics for H2?
3. **`as unknown as Record<string, unknown>`** type cast: the payload is cast through `unknown` to satisfy `logEvent`'s generic type. This silently strips TypeScript's type checking from the payload. If a field is added to `RubricEditPayload` but not to `logEvent`'s schema, no error is raised. Is there a better pattern here?
4. **Click-to-Add + semantic matching**: when `source = 'click_to_add'`, `conceptId` is the exact canonical KG node ID (e.g., `gradient_descent`). Running `matchesContradictsNode(conceptId, sessionContradictsNodes)` on a canonical ID will almost always return `concept_in_contradicts_semantic = true` because the exact ID will match Layer 1. This means Click-to-Add edits will always inflate the semantic alignment rate. Should Click-to-Add edits be excluded from the H2 analysis, or analysed separately?

---

## Layer 4 — conceptAliases.ts (semantic matching)

**Three-layer matching:**

```typescript
export function matchesContradictsNode(
  editConcept: string,
  contradictsNodes: string[],
): ConceptMatchResult {
  const normEdit = normalizeConceptId(editConcept);

  // Build reverse lookup fresh on every call
  const aliasLookup = new Map<string, string>();
  for (const [canonicalId, aliases] of Object.entries(DOMAIN_ALIASES)) {
    for (const alias of aliases) {
      aliasLookup.set(normalizeConceptId(alias), canonicalId);
    }
    aliasLookup.set(normalizeConceptId(canonicalId), canonicalId);
  }

  let bestNode: string | null = null;
  let bestScore = 0;

  for (const node of contradictsNodes) {
    const normNode = normalizeConceptId(node);

    // Layer 1: exact normalised match
    if (normEdit === normNode) { return { matched: true, bestMatch: node, score: 1.0 }; }

    // Layer 2: alias dictionary
    const editCanonical  = aliasLookup.get(normEdit);
    const nodeCanonical  = aliasLookup.get(normNode) ?? normNode;
    if (editCanonical && editCanonical === nodeCanonical) {
      return { matched: true, bestMatch: node, score: 1.0 };
    }
    const reverseMatch = aliasLookup.get(normNode);
    if (reverseMatch && reverseMatch === normEdit) {
      return { matched: true, bestMatch: node, score: 1.0 };
    }

    // Layer 3: fuzzy Levenshtein (best across all nodes)
    const ratio = similarityRatio(normEdit, normNode);
    if (ratio > bestScore) { bestScore = ratio; bestNode = node; }
  }

  if (bestScore >= FUZZY_THRESHOLD) {
    return { matched: true, bestMatch: bestNode, score: bestScore };
  }
  return { matched: false, bestMatch: bestNode, score: bestScore };
}
```

**Potential issues to review:**
1. **`aliasLookup` rebuilt on every call**: for study-scale use (N=20 participants, 60 edits), this is fine. But the comment says "pre-compute once if this becomes a hot path." Given that `matchesContradictsNode` is called inside `handleEdit` (already called only on user action), is there any scenario where it could be called in a hot path (e.g., inside a `useMemo` or render loop)?
2. **Layer 2 edge case**: `const nodeCanonical = aliasLookup.get(normNode) ?? normNode`. If the CONTRADICTS node is not in `DOMAIN_ALIASES` at all (e.g., it's a Kaggle ASAG concept), `nodeCanonical` falls back to `normNode` (the node itself). Then `editCanonical === nodeCanonical` compares the edit's canonical form to the raw node string. This could produce false positives if, e.g., `editCanonical = "neural_network"` and the Kaggle node is literally `"neural_network"`. Is this intended?
3. **Layer 3 only tracks the best node globally**, not per-node. The function returns early on Layer 1/2 hits, but for Layer 3, it tracks the single best Levenshtein score across all `contradictsNodes`. This means if there are 5 CONTRADICTS nodes and none are an alias match, the function returns the best fuzzy match — but does not report the score against each individual node. Is this the right design, or should we return all matches above threshold?
4. **`normalizeConceptId` does not strip punctuation**: `"chain-rule"` normalises to `"chain-rule"` (hyphen retained). `"chain_rule"` normalises to `"chain rule"` (underscore → space). The Levenshtein distance between `"chain rule"` and `"chain-rule"` is 1 (hyphen vs space), similarity = 9/10 = 0.9 ≥ 0.80. This works correctly — but is it by design or by accident? Should hyphen be treated as a word separator like underscore?

---

## Layer 5 — studyLogger.ts (event schema)

**RubricEditPayload (current schema):**

```typescript
export interface RubricEditPayload {
  edit_type: 'add' | 'remove' | 'increase_weight' | 'decrease_weight';
  concept_id: string;
  concept_label: string;
  within_15s: boolean;
  within_30s: boolean;
  within_60s: boolean;
  time_since_last_contradicts_ms: number | null;
  source_contradicts_nodes_60s: string[];
  concept_in_contradicts_exact: boolean;
  concept_in_contradicts_semantic: boolean;
  semantic_match_score: number | null;
  semantic_match_node: string | null;
  session_contradicts_nodes: string[];
  panel_focus_ms: number;
  panel_focus_before_trace: boolean;
  interaction_source: 'click_to_add' | 'manual';
  trace_gap_count: number;
  grounding_density: number;
}
```

**Backend fire-and-forget:**

```typescript
if (studyApiBase) {
  fetch(`${studyApiBase}/api/study/log`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(event),
  }).catch(() => {
    // Backend unreachable — localStorage remains the fallback
  });
}
```

**Potential issues to review:**
1. **`panel_focus_ms`** is named as "ms when the panel first rendered" but its value is `panelMountMs.current` which is `Date.now()` at component mount — a Unix timestamp in ms, not a duration. The field name is misleading: `panel_mount_timestamp_ms` would be clearer.
2. **`session_contradicts_nodes`** is logged on every rubric edit, making the payload grow linearly with the number of CONTRADICTS interactions in the session. For N=20 and ~10 CONTRADICTS interactions per session, this is fine (~200 bytes per event). But it is a potential data-bloat issue for longer sessions.
3. **No session-level event logging for `trace_gap_count`**: the gap count is logged per rubric edit but not on the `trace_interact` event. If an educator views a gapped trace but makes no rubric edits, the gap count is never logged. Should `trace_interact` events also include `trace_gap_count` and `grounding_density`?

---

## Layer 6 — analyze_study_logs.py (GEE moderation analysis)

**GEE model (current implementation):**

```python
model = GEE.from_formula(
    'within_30s ~ condition * trace_gap_count',
    groups='session_id',
    data=df,
    family=Binomial(),
    cov_struct=Exchangeable(),
).fit()

rho = float(model.cov_struct.dep_params)  # working correlation
gap_or = round(float(np.exp(gap_coef)), 4)
```

**Session-level approximation note in the code:**

```python
# Expand to one row per edit, distributing within_30s attributions
# proportionally (first n_within_30 edits flagged as attributed).
for i in range(n_edits):
    rows.append({...})
for i in range(n_within_30):
    rows[-(n_edits) + i]['within_30s'] = 1
```

**Potential issues to review:**
1. **The session-level approximation is incorrect as written.** `rows[-(n_edits) + i]['within_30s'] = 1` sets the `within_30s` flag on the *last* `n_edits` rows of the entire `rows` list, not just the rows for the current session. If there are multiple sessions, this loop overwrites rows from previous sessions. The loop should index within the current session's slice: `rows[len(rows) - n_edits + i]['within_30s'] = 1` is also wrong for the same reason. The correct approach: append all `n_edits` rows first, capture the slice index, then update `within_30s` within that slice.
2. **GEE requires ≥2 groups per cluster**. If any session has only 1 rubric edit, the exchangeable correlation cannot be estimated for that cluster. Does statsmodels handle single-edit sessions gracefully, or will it raise a warning/error?
3. **`working_correlation_rho` may be negative**. In the dummy dataset, ρ = -0.308. A negative exchangeable correlation means edits within a participant are *negatively* correlated — which is theoretically possible (an educator who makes one high-attribution edit might make lower-attribution edits subsequently) but unusual. If ρ < 0 in the real study, should we switch to an Independence working correlation structure?
4. **The `interaction_p` for the printed `sig` check**: `'→ DIRECTIONAL TREND' if gap_result['interaction_p'] < 0.10 else '→ n.s.'` — this reports the interaction term (condition × gap_count) as the primary result, not the gap_count main effect. The moderation hypothesis is about the *interaction* (does gap count moderate the condition effect?), so this is correct. But the main effect of gap_count is printed separately. Should the report print clearly which p-value corresponds to which research question?

---

## Summary: Highest-Priority Issues

| Priority | Layer | Issue | Impact |
|----------|-------|-------|--------|
| 🔴 Critical | analyze_study_logs.py | `within_30s` flagging loop overwrites wrong rows | Corrupts moderation analysis |
| 🔴 Critical | VerifierReasoningPanel | Synthetic node IDs pushed to `recentContradicts` when `kg_nodes = []` | Inflates 60-s window with unmatchable nodes |
| 🟡 Medium | RubricEditorPanel | Click-to-Add always inflates semantic alignment rate (H2) | Overstates H2 effect size |
| 🟡 Medium | studyLogger | `panel_focus_ms` is a timestamp, not a duration — misleading field name | Analysis confusion |
| 🟡 Medium | conceptAliases | `aliasLookup` rebuilt on every call | Negligible now; risk if ever called in render loop |
| 🟢 Low | studyLogger | `session_contradicts_nodes` logged on every edit | Data bloat; fine for N=20 |
| 🟢 Low | analyze_study_logs.py | Negative ρ handling not specified | May need Independence fallback |
| 🟢 Low | conceptAliases | Hyphen not normalized to space | Works by accident; should be documented |

---

## Questions for Gemini Code Review

1. **[Critical]** Is the `within_30s` row-flagging loop in `run_gap_moderation_analysis()` definitively buggy, or does the Python list indexing happen to work correctly due to the append order? Please trace the execution for 2 sessions × 4 edits each to verify.

2. **[Critical]** For synthetic node IDs (`step_3`, `step_7`) pushed when a CONTRADICTS step has empty `kg_nodes`: should the fix be (a) skip the PUSH entirely when `kg_nodes = []`, or (b) push the step text hash as a unique ID (still unmatchable but deduplicated)?

3. **[Medium]** For Click-to-Add inflation of H2: should these edits be (a) excluded from H2 analysis entirely, (b) reported separately as "Click-to-Add alignment rate" vs "Manual alignment rate", or (c) included but flagged with `interaction_source` so the reader can see the breakdown?

4. **[Medium]** Is there a cleaner TypeScript pattern than `as unknown as Record<string, unknown>` for passing a typed payload to a generic event logger? Could `logEvent` be made generic: `logEvent<T>(condition, dataset, type, payload: T)`?

5. **[Low]** In `conceptAliases.ts`, should Layer 2 be re-ordered so that *both* direction checks (editCanonical vs nodeCanonical, and reverseMatch vs normEdit) are done before falling through to Layer 3? Is there a case where the current order would miss an alias match and fall through to a weaker fuzzy match?

---

## Gemini v11 Review — Corrections and Open Items

**Date applied:** 2026-04-14  
**Source:** Gemini v11 response covering §1 Introduction draft (conceptgrade_introduction_draft_v12.md) and code review v1

---

### Source: `conceptgrade_code_review_v1_feedback.md` (Gemini response to Q1–Q5)

---

### Correction 1 — Layer 6 "Critical Bug" Is Not Present in Actual Code

The Layer 6 issue Q1 ("`within_30s` flagging loop overwrites wrong rows") was based on a pseudocode representation that does not match the actual implementation. The actual code in `run_gap_moderation_analysis()` (lines 449–455) correctly assigns `within_30s` **inline during the single append loop**:

```python
for i in range(n_edits):
    rows.append({
        'session_id':     sid,
        'condition':      cond,
        'trace_gap_count': gap,
        'within_30s':     1 if i < n_within_30 else 0,  # ← correct: inline, no post-hoc indexing
    })
```

There is no second loop doing `rows[-(n_edits) + i]['within_30s'] = 1`. The code is correct. **Remove from 🔴 Critical list.**

---

### Gemini Answer — Q2: Synthetic Node IDs → **(a) Skip PUSH when `kg_nodes = []`**

**Implemented.** `VerifierReasoningPanel.tsx` line 434 changed from:
```typescript
const nodeId = step.kg_nodes[0] ?? `step_${step.step_id}`;
pushContradicts(nodeId);
```
to:
```typescript
if (step.classification === 'CONTRADICTS' && step.kg_nodes.length > 0) {
  pushContradicts(step.kg_nodes[0]);
}
```
CONTRADICTS steps with no KG nodes are silently skipped — they do not inflate the rolling window.

---

### Gemini Answer — Q3: Click-to-Add H2 Inflation → **(c) Include, flag by `interaction_source`, analyze separately**

**Implemented.** `analyze_study_logs.py` now computes:
- `semantic_alignment_rate_manual` — H2 **PRIMARY** metric (unprompted, no UI assist). Denominator = manual edits only.
- `semantic_alignment_rate_cta` — UI-assisted rate (Click-to-Add). Reported separately.
- `semantic_alignment_rate` — combined, kept as reference.

Print table now shows all three rows under "Concept Alignment (H2_semantic)".

---

### Gemini Answer — Q4: TypeScript Generic for `logEvent` → **Make generic, remove double-cast**

**Implemented.**

`studyLogger.ts`:
```typescript
export function logEvent<T extends Record<string, unknown>>(
  condition: string,
  dataset: string,
  event_type: StudyEventType,
  payload: T = {} as T,
): void {
```

`RubricEditorPanel.tsx`: call site changed from
```typescript
logEvent(condition, dataset, 'rubric_edit', payload as unknown as Record<string, unknown>);
```
to:
```typescript
logEvent(condition, dataset, 'rubric_edit', payload);
```
TypeScript now validates that `RubricEditPayload` satisfies `Record<string, unknown>` at the call site.

---

### Gemini Answer — Q5: `conceptAliases.ts` Layer 2 Ordering → **No change needed**

Assessment: the current implementation is logically sound. Both Layer 2 checks contain `return` statements and are evaluated sequentially. The `aliasLookup.get(normNode) ?? normNode` fallback correctly handles nodes not in `DOMAIN_ALIASES` without producing false positives. **No code change.**

---

### Correction 2 — Revised Summary Table

| Priority | Layer | Issue | Status |
|----------|-------|-------|--------|
| ✅ Fixed | VerifierReasoningPanel | Synthetic node IDs (`step_3`) pushed to `recentContradicts` when `kg_nodes = []` | Fixed — push guarded by `kg_nodes.length > 0` |
| ✅ Fixed | RubricEditorPanel + studyLogger | Click-to-Add inflates H2; no source split | Fixed — `semantic_alignment_rate_manual` is H2 PRIMARY; CTA reported separately |
| ✅ Fixed | studyLogger + RubricEditorPanel | `as unknown as Record<string, unknown>` double-cast | Fixed — `logEvent` now generic `<T extends Record<string, unknown>>` |
| 🟡 Medium | studyLogger | `panel_focus_ms` is a timestamp, not a duration | Open — rename to `panel_mount_timestamp_ms` before full study |
| 🟢 Low | conceptAliases | `aliasLookup` rebuilt on every call | Acceptable at N=20; document if hot-path use ever added |
| 🟢 Low | studyLogger | `session_contradicts_nodes` logged on every edit | Acceptable at N=20; fine |
| 🟢 Low | analyze_study_logs.py | Negative ρ handling not specified | Open — add Independence fallback if ρ < 0 in real study |
| 🟢 Low | conceptAliases | Hyphen not normalized to space (works by accident) | Open — document as intentional; add unit test |
| ✅ Non-issue | analyze_study_logs.py | `within_30s` flagging loop described as bug — NOT in actual code | Closed — inline `1 if i < n_within_30 else 0` is correct |
| ✅ Non-issue | conceptAliases | Layer 2 ordering | Closed — Gemini confirmed logically sound, no change needed |

---

### Gemini v11 — §1 Introduction Decisions (Locked)

These decisions apply to v13 of the Introduction draft (`conceptgrade_introduction_draft_v12.md`):

**Q1 — CoT Concession Sentence: ADD**  
Add the following sentence to paragraph 2, after "disconnected from any formal domain representation":
> *"Recent work on chain-of-thought prompting [Wei 2022] demonstrates that LRMs can produce domain-accurate reasoning chains — our claim is not that the reasoning is wrong, but that its topological structure is invisible to the educator without a reference KG."*

**Q2 — Citation for "Implicit Mental Models": Kulesza + Bansal, NOT Norman**  
Do not cite Norman [1988] (Design of Everyday Things). The concept here is about human-AI alignment of mental models, not affordance design. Cite instead:
- Kulesza et al. [2012] — "Tell Me More: The Effects of Mental Model Soundness on Personalizing an Intelligent Agent"
- Bansal et al. [2019] — "Updates in Human-AI Teams: Understanding and Addressing the Performance/Compatibility Tradeoff"

**Q3 — Placeholder Strategy: X/Y/Z with [TODO] markers**  
Keep `N = X`, `Y%`, and `Z%` as explicit placeholders for the co-author draft. Add a visible note:  
> `[TODO: fill from pilot study data — expected Y ≈ 60%, Z ≈ 25% from power analysis]`

**Q4 — "First Approach" Claim: Narrow to VA Educational Context**  
Replace "the first approach to operationalize reasoning-chain continuity as a visualizable topological property" with:
> "the first visual analytics approach, to our knowledge, to operationalize reasoning-chain continuity as a topological property of an LRM chain-of-thought in an educational grading context"

This is defensible against trace faithfulness [Lanham 2023], knowledge-grounded NLG [Ji 2023], and concept map visualization [Novak 1984] prior work.

**Q5 — Length Calibration: Target 650 words (~1.25 column-pages)**  
Three cuts to reduce from ~1,050 words:
1. **Move LIME/SHAP paragraph** (para 2) to §2 Related Work. Keep only 1 sentence summary: *"Existing XAI techniques answer 'what did the model look at?' but not 'was the model's domain reasoning coherent?' — a distinction that requires a structured domain representation."*
2. **Strip p-values from evaluation preview** (para 5). Keep only: "32.4% MAE reduction" and "p < 0.05". Move the Wilcoxon N=120, Fisher combined, and hypergeometric details to §5.
3. **Co-auditing paragraph (para 3): do not shorten** — this is the key paradigm distinction and must remain intact.

---

### New Open Item — §4 System Architecture: Pipeline Diagram

Gemini v11 asks: *"Does the paper include a figure for the 5-stage pipeline (KG generation → concept matching → LRM Verifier → trace parser → C5 scoring)? If so, what is the visual encoding — flowchart, swimlane, or annotated screenshot?"*

**Decision pending.** Options:
- **Option A (flowchart)**: boxes + arrows, one box per stage, annotated with the file name (`lrm_verifier.py`, `trace_parser.py`). Clean but generic.
- **Option B (annotated screenshot)**: actual system screenshot showing all 11 panels, with callout boxes indicating which stage produced which visual element. More compelling for VAST reviewers who expect system paper figures.
- **Option C (split)**: high-level flowchart as Figure 1 in §3; annotated screenshot as Figure 2 in §4.

**Recommendation for §4 draft**: use Option C. Figure 1 introduces TRM topology; Figure 2 shows the implemented system. This mirrors the ConceptGrade contribution structure (TRM in §3, system in §4).

Writing order consequence: **§4 cannot be finalized until the system screenshot is taken** (actual trace, not placeholder). Schedule this after the Sample 0 DigiKlausur figure is confirmed (requires Gemini Flash ablation with `GEMINI_API_KEY`).
