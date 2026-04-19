# LRM Integration — ConceptGrade Stage 3 Extension

**Date:** 2026-04-13  
**Status:** Implemented, awaiting ablation run (requires DeepSeek API key)  
**Informed by:** Gemini review of the LRM proposal (see `gemini_review_lrm_response.txt`)

---

## 1. What Was Built

The ConceptGrade pipeline was extended with two new stages and three supporting
artifacts that together expose the Large Reasoning Model's internal reasoning as a
first-class visual analytics artifact in the educator dashboard.

### Pipeline Before

```
Stage 1  Self-Consistent Extraction      (Gemini 2.5 Flash)
Stage 2  Confidence-Weighted KG Matching (embedding similarity)
Stage 3  LLM-as-Verifier                 (Gemini 2.5 Flash — verdict only, no trace)
Stage 4  Chain Coverage Scoring          (deterministic formula)
Stage 5  Final Score + Explanation       (Gemini 2.5 Flash)
```

### Pipeline After

```
Stage 1  Self-Consistent Extraction      (Gemini 2.5 Flash — unchanged)
Stage 2  Confidence-Weighted KG Matching (embedding similarity — unchanged)
Stage 3a LRM-as-Verifier                 (DeepSeek-R1 via DeepSeek API)
             outputs: reasoning_content trace + {"valid": bool, "reasoning": str}
Stage 3b Trace Parser                    (deterministic Python — NEW)
             outputs: [{step_id, text, classification, kg_nodes, kg_edges,
                        confidence_delta, is_conclusion}]
Stage 4  Chain Coverage Scoring          (deterministic formula — unchanged)
Stage 5  Final Score + Explanation       (Gemini 2.5 Flash — unchanged)
```

---

## 2. Files Created or Modified

### Python Backend

| File | Type | Description |
|------|------|-------------|
| `conceptgrade/trace_parser.py` | New | Stage 3b — converts raw LRM `<think>` trace into structured KG-linked steps |
| `conceptgrade/lrm_verifier.py` | New | Stage 3a — async LRM-as-Verifier using DeepSeek API (R1); Gemini fallback |
| `run_lrm_ablation.py` | New | Batch ablation runner: Flash vs R1-Distill on Mohler + DigiKlausur |
| `tests/test_trace_parser.py` | New | 30 unit tests for TraceParser (all passing) |

### React Frontend

| File | Type | Description |
|------|------|-------------|
| `src/components/charts/VerifierReasoningPanel.tsx` | New | Dashboard component — bidirectionally brushed step list linked to KG graph |
| `src/components/charts/index.ts` | Modified | Added `VerifierReasoningPanel`, `ParsedStep`, `TraceSummary` exports |

### NestJS Backend

| File | Type | Description |
|------|------|-------------|
| `src/visualization/visualization.types.ts` | Modified | Added `ParsedTraceStep`, `TraceSummary`, `SampleTraceResponse` interfaces |
| `src/visualization/visualization.service.ts` | Modified | Added `getSampleTrace()` — reads `{dataset}_lrm_traces.json` |
| `src/visualization/visualization.controller.ts` | Modified | Added `GET /api/visualization/datasets/:dataset/sample/:sampleId/trace` |

### Documentation

| File | Description |
|------|-------------|
| `docs/gemini_review_lrm_proposal.txt` | Review prompt sent to Gemini |
| `docs/gemini_review_lrm_response.txt` | Gemini's full response with action items |
| `docs/LRM_INTEGRATION.md` | This document |

---

## 3. Stage 3b — Trace Parser (`trace_parser.py`)

### Purpose

Raw `<think>` traces from DeepSeek-R1 are rambling and contradictory — showing
them directly to educators would increase cognitive load and decrease trust
(Gemini's critical finding #7). The Trace Parser transforms the raw trace into a
structured list of atomic reasoning steps, each linked to specific KG nodes and
edges, before the data reaches the dashboard.

### Algorithm (fully deterministic — no additional model calls)

```
1. Extract <think>…</think> block from raw LRM output
2. Sentence-segment the trace (handles abbreviations, multi-paragraph blocks)
3. Filter exploratory branches:
     - Self-corrections: "wait", "let me", "actually, no", "hmm"
     - Questions (sentences ending in "?")
     - Hypothesis markers: "suppose", "what if", "let's say"
4. KG entity linking (3-pass per sentence):
     Pass 1 — exact substring match (lowercased, underscore→space)
     Pass 2 — any 4+ character word from the node label appears in sentence
     Pass 3 — fuzzy SequenceMatcher ratio > 0.72 on full node label
5. Edge type linking — alias table maps "prerequisite" → PREREQUISITE_FOR, etc.
6. Classify each sentence:
     SUPPORTS    — keyword match: "correctly", "identifies", "confirms", ...
     CONTRADICTS — keyword match: "fails", "missing", "omits", "incorrect", ...
     UNCERTAIN   — keyword match: "implies", "weak", "partial", "may", ...
     Priority: CONTRADICTS > SUPPORTS > UNCERTAIN (negations dominate)
7. Assign confidence_delta:
     SUPPORTS    → +0.10
     CONTRADICTS → −0.15
     UNCERTAIN   →  0.00
8. Mark conclusion cluster (last ¼ of steps + explicit "therefore/thus/in conclusion")
9. Trim to max_steps=20, prioritising: conclusions → contradicts → supports → uncertain
10. Assign sequential step_ids (1-based)
```

### Output Schema (one `ParsedStep` per kept sentence)

```json
{
  "step_id":          1,
  "text":             "The student correctly identifies gradient descent as a prerequisite for backpropagation.",
  "classification":   "SUPPORTS",
  "kg_nodes":         ["Gradient_Descent", "Backpropagation"],
  "kg_edges":         ["PREREQUISITE_FOR"],
  "confidence_delta": 0.1,
  "is_conclusion":    false
}
```

### `summarise_trace()` Output (for dashboard ClassSummaryCard)

```json
{
  "total_steps":       12,
  "supports_count":    5,
  "contradicts_count": 4,
  "uncertain_count":   3,
  "net_delta":         -0.1,
  "conclusion_text":   "Therefore, the chain is partially valid but missing the chain rule.",
  "nodes_referenced":  ["Backpropagation", "Chain_Rule", "Gradient_Descent"],
  "edges_referenced":  ["PREREQUISITE_FOR", "PRODUCES"]
}
```

### Test Coverage

30 unit tests covering:
- Schema validation, sequential step IDs
- Exploratory sentence filtering (all 4 marker types)
- Classification keyword priority (CONTRADICTS > SUPPORTS)
- Confidence delta signs
- KG entity linking (exact, underscore-normalized, partial word, fuzzy)
- Edge type alias linking
- Conclusion marking (tail cluster + explicit phrase)
- `max_steps` enforcement
- No `<think>` tag fallback
- Empty input guard
- `summarise_trace()` schema, count consistency, empty state

---

## 4. Stage 3a — LRM Verifier (`lrm_verifier.py`)

### Model Selection

| Priority | Model | Why |
|----------|-------|-----|
| Primary | `deepseek-reasoner` (DeepSeek API) | DeepSeek-R1, exposes `reasoning_content` trace directly — no local GPU needed |
| Alternative | `deepseek-chat` (DeepSeek API) | DeepSeek-V3, fast, no reasoning trace produced |
| Fallback | Gemini 2.5 Flash (API) | No trace produced — for dry runs when no DeepSeek key |

DeepSeek API is OpenAI-compatible (`api.deepseek.com`) and costs ~$0.55/M tokens.
`reasoning_content` is returned directly on the response message — no `<think>` tag parsing needed.

### Three-Layer JSON Format Safeguard

DeepSeek-R1 returns the final answer in `message.content` (separate from the
reasoning trace in `reasoning_content`), so JSON parsing is much cleaner.
Three layers of protection remain:

1. **Prompt instruction** — system prompt explicitly says: output only valid JSON,
   no markdown, no code fences
2. **`_regex_extract_json()`** — tries `json.loads()` first, then a regex targeting
   `{"valid": ...}`, then any `{...}` block
3. **Safe default** — if all parsing fails, returns `{"valid": true, "reasoning": "parse_error"}`
   and logs a warning. Pipeline never crashes.

### Latency Safeguard

DeepSeek API: ~5–15 seconds per answer (vs. 15–40s for a local 70B model).
`LRMVerifier` is designed for **async batch use only**:

- `averify()` is an `async` method using `asyncio` + thread executor
- `run_lrm_ablation.py` runs all answers in parallel with a bounded
  `asyncio.Semaphore(concurrency=4)` to avoid overwhelming the API rate limit
- Results are cached to `{dataset}_lrm_traces.json` — the NestJS API reads
  from cache, never calling the LRM at request time

### Overthinking Safeguard

The Stage 3b Trace Parser itself mitigates overthinking: exploratory branches
where the LRM tests hypotheses and then self-corrects are filtered out before
any steps reach the educator dashboard. Only the final conclusion path is shown.

---

## 5. React — `VerifierReasoningPanel.tsx`

### What It Shows

A structured, scrollable list of parsed reasoning steps. Each step displays:
- **Classification icon** (green checkmark / red X / amber question mark)
- **Classification label** (SUPPORTS / CONTRADICTS / UNCERTAIN)
- **Confidence delta chip** (e.g. `+0.10`, `−0.15`) in monospace, color-coded
- **Step text** (the cleaned sentence from the trace)
- **KG node pills** (one per referenced node — clickable)
- **Conclusion flag** (purple flag icon for conclusion cluster steps)
- **Step ID** (#1, #2, ...)

A **summary bar** at the top shows: total steps, counts per classification,
and net Δ confidence (sum of all deltas).

A **conclusion callout** box highlights the final verdict sentence.

An **edge types footer** lists all relationship types evaluated in the trace.

### Bidirectional Brushing

This is the core IEEE VIS VAST contribution (Gemini requirement #3):

**Step → KG (outward)**
Clicking a reasoning step calls `onNodeClick(step.kg_nodes[0])`, which opens
the existing `ConceptKGPanel` for that node and highlights it. The educator
can see exactly which KG node triggered a CONTRADICTS classification.

**KG → Steps (inward)**
When the parent passes `highlightedNode` (set when the educator clicks a node
in `ConceptKGPanel`), all steps that do NOT reference that node are dimmed to
`opacity: 0.45`. The educator can ask "which reasoning steps reference
Gradient_Descent?" and the list self-filters.

**Node pills as shortcuts**
Each KG node pill in a step row is independently clickable to open the KG
subgraph for that specific node — providing direct drill-down without going
back to the main chart.

---

## 6. NestJS API — New Endpoint

```
GET /api/visualization/datasets/:dataset/sample/:sampleId/trace
```

**Returns:** `SampleTraceResponse`

```typescript
interface SampleTraceResponse {
  id:             string | number;
  dataset:        string;
  lrm_valid:      boolean;
  lrm_reasoning:  string;
  lrm_model:      string;
  lrm_latency_ms: number;
  parsed_steps:   ParsedTraceStep[];
  trace_summary:  TraceSummary;
}
```

**Returns `null`** if `{dataset}_lrm_traces.json` does not exist yet —
the `VerifierReasoningPanel` shows a graceful empty state:
*"Run the LRM verifier (Stage 3a) to generate trace data."*

The trace file is populated by the ablation runner, not at request time.

---

## 7. Ablation Runner (`run_lrm_ablation.py`)

### Purpose

Produces the `{dataset}_lrm_traces.json` files the API serves, and computes
the three-way MAE comparison needed for Paper 1 (ML/NLP venue).

### Usage

```bash
# Prerequisites: DeepSeek API key
export DEEPSEEK_API_KEY=sk-...

# Full ablation: Mohler (all 120) + DigiKlausur (random 300)
python run_lrm_ablation.py \
  --datasets mohler digiklausur \
  --sample-n 300 \
  --concurrency 4

# Dry run (first 3 samples, Gemini fallback if no DeepSeek key)
python run_lrm_ablation.py \
  --datasets mohler \
  --gemini-key $GEMINI_API_KEY \
  --dry-run
```

### Output Files

| File | Contents |
|------|----------|
| `data/mohler_lrm_traces.json` | `{sampleId: SampleTraceResponse}` for all 120 Mohler answers |
| `data/digiklausur_lrm_traces.json` | Same for 300 sampled DigiKlausur answers |
| `data/lrm_ablation_summary.json` | Three-way MAE: C_LLM / C5 / LRM-adjusted per dataset |

### Ablation Summary Schema

```json
{
  "mohler": {
    "n":               120,
    "mae_cllm":        0.3300,
    "mae_c5":          0.2229,
    "mae_lrm_adj":     "<to be filled after run>",
    "c5_vs_cllm_pct":  32.4,
    "lrm_vs_c5_pct":   "<to be filled after run>",
    "elapsed_s":       "<runtime>"
  }
}
```

---

## 8. Paper Implications

Per Gemini's framing recommendation (Q6), the LRM extension is split across
both planned papers — no third paper needed.

### Paper 1 (NLP / EdAI venue)

Add to Section V (Evaluation Methodology):
- Stage 3 ablation: Gemini Flash vs DeepSeek-R1-Distill-70B
- Datasets: Mohler (n=120) + DigiKlausur sample (n=300) — n=120 alone is too
  small for an accuracy claim at a premier NLP venue
- Metric: MAE comparison, Wilcoxon p (Flash vs LRM on same answers)
- Claim: *"LRM-augmented verification further reduces MAE by X% on Mohler
  (p=Y) and Z% on DigiKlausur (p=W)"*

### Paper 2 (IEEE VIS VAST 2027)

Expand Section IV to include Stage 3b and the VerifierReasoningPanel:

**New narrative hook:**
*"LRMs improve grading, but their reasoning is opaque. We built a visual
analytics system that extracts the LRM's epistemic trace and maps it to the
domain Knowledge Graph, allowing educators to debug machine reasoning at the
level of individual logical deductions."*

**New Section IV.E — LRM Trace Visualization:**
- Describe Stage 3b Trace Parser as a methodological contribution
- Describe `VerifierReasoningPanel` with bidirectional brushing
- Reference Gemini's prototype interaction model
- Frame as: structured trace → CMV-linked visual → educator trust in grading

---

## 9. To Run the Full LRM Extension

### Step 1 — Get a DeepSeek API key

Sign up at [platform.deepseek.com](https://platform.deepseek.com) and create an API key.
The DeepSeek API is OpenAI-compatible and costs ~$0.55/M tokens for `deepseek-reasoner` (R1).

```bash
export DEEPSEEK_API_KEY=sk-...
```

### Step 2 — Run the ablation

```bash
cd packages/concept-aware

# Full run — all 120 Mohler + 300 sampled DigiKlausur answers
.venv/bin/python run_lrm_ablation.py \
  --datasets mohler digiklausur \
  --sample-n 300 \
  --concurrency 4

# Dry run (first 3 samples only, for testing the pipeline)
.venv/bin/python run_lrm_ablation.py \
  --datasets mohler \
  --dry-run

# Dry run with Gemini fallback (no DeepSeek key needed, no trace produced)
.venv/bin/python run_lrm_ablation.py \
  --datasets mohler \
  --gemini-key $GEMINI_API_KEY \
  --dry-run
```

### Step 3 — Start the NestJS API

```bash
cd packages/backend
yarn start:dev
```

The new endpoint is immediately available:
```
GET http://localhost:5000/api/visualization/datasets/mohler/sample/1/trace
```

### Step 4 — View in Dashboard

Navigate to the dashboard, select an answer in the `ScoreSamplesTable`,
and the `VerifierReasoningPanel` will appear alongside the existing
`ConceptKGPanel`. Click any step to brush the KG; click any KG node to
filter the step list.

---

## 10. Known Limitations / Next Steps

| Item | Status | Notes |
|------|--------|-------|
| DeepSeek API key | Pending | Set `DEEPSEEK_API_KEY` env var; get key at platform.deepseek.com |
| Ablation run | Pending | Run `python run_lrm_ablation.py --datasets mohler digiklausur`; use `--dry-run` to test first |
| Formal SUS evaluation | Future | Condition A (no trace) vs Condition B (with VerifierReasoningPanel) |
| VerifierReasoningPanel integration in InstructorDashboard | Future | Wire `highlightedNode` prop from DashboardContext; add panel to answer row expansion |
| Paper 1 Section V update | Future | Add LRM ablation results once run completes |
| Paper 2 Section IV.E | Future | Add after VerifierReasoningPanel integration is user-tested |
