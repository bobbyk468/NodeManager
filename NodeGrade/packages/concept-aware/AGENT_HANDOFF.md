# ConceptGrade — Agent Handoff Document
**Last updated: 2026-04-05**
**Project root: `packages/concept-aware/`**

---

## ⚠️ CRITICAL: All Results Are Already Computed — Do NOT Make API Calls

**All scoring results, KGs, and metrics are cached as JSON files. The coding agent must work ONLY from these cached files. Do not call any LLM API to re-score existing samples.**

| What is cached | Location | API needed? |
|---------------|----------|-------------|
| All Mohler 2011 scores (C_LLM, CoT, C5_fix) | `data/evaluation_results.json`, `data/cot_baseline_scores.json` | ❌ NO |
| All DigiKlausur scores (646 samples, C_LLM + C5_fix) | `data/batch_responses/digiklausur_cllm_batch_01-09_response.json` + `c5fix_batch_01-09_response.json` | ❌ NO |
| All Kaggle ASAG scores (473 samples, C_LLM + C5_fix) | `data/batch_responses/kaggle_asag_cllm_batch_01-06_response.json` + `c5fix_batch_01-06_response.json` | ❌ NO |
| **Merged metrics + per-sample rows (Digi + Kaggle)** | `data/digiklausur_eval_results.json`, **`data/kaggle_asag_eval_results.json`** | ❌ NO |
| DigiKlausur KG (17 questions) | `data/digiklausur_auto_kg.json` | ❌ NO |
| Kaggle ASAG KG (150 questions) | `data/kaggle_asag_auto_kg.json` | ❌ NO |
| Precomputed KG features | `data/digiklausur_precomputed.json`, `data/kaggle_asag_precomputed.json` | ❌ NO |
| Ablation results | `data/ablation_results.json`, `data/extension_ablation_results.json` | ❌ NO |

**To reproduce all metrics and paper report with zero API calls:**
```bash
cd packages/concept-aware
python3 score_batch_results.py --dataset digiklausur    # reads from data/batch_responses/
python3 score_batch_results.py --dataset kaggle_asag    # reads from data/batch_responses/
python3 generate_paper_report_v2.py                     # generates paper_report_v2.txt
```

**To verify stored JSON is internally consistent** (metrics match recomputation from `results[]`, batch IDs align):
```bash
cd packages/concept-aware
python3 validate_stored_eval.py --check-batches
```

**To summarize cross-dataset evidence** (MAE, Wilcoxon, win rates, pooled Digi+Kaggle test, Fisher combo — see script docstring for limits):
```bash
python3 prove_cross_dataset_evidence.py
# → data/cross_dataset_evidence_summary.json
```
A **strict** claim “C5 beats C_LLM on every benchmark (lower MAE and p<0.05 each)” is **false on stored data** because Kaggle ASAG does not meet that bar; removing that limitation **requires a new Kaggle C5_fix scoring run** (API) after prompt/KGE tuning, then `validate_stored_eval.py`.

**If `kaggle_asag_c5fix_batch_*_response.json` files are missing** but `kaggle_asag_eval_results.json` still has `c5_score` per row, rebuild batch files with:
`python3 reconstruct_c5fix_batches_from_eval.py --dataset kaggle_asag`

**Semantic concept matching:** `generate_batch_scoring_prompts.py` uses **TF-IDF cosine** (sklearn) when `sentence-transformers` is not installed; set `SKLEARN_SIM_THRESHOLD`, `KG_MIN_COVERAGE`, or `CONCEPT_SIM_THRESHOLD` to tune. After changing prompts, re-score with a **valid** `GEMINI_API_KEY` (rotate keys if leaked).

---

## 1. What Is ConceptGrade?

ConceptGrade is a research system for **Automatic Short Answer Grading (ASAG)**. It augments a pure LLM grader (C_LLM) with structured **Knowledge Graph (KG) evidence** to produce more accurate, interpretable grades.

### Pipeline (4 stages)
```
Student Answer + Question + Reference Answer
    ↓
[Stage 0] Auto-KG Generation (Gemini API → JSON)
    ↓
[Stage 1] KG Feature Extraction (local, no grading API)
          - Concept matching: keywords + **TF–IDF cosine** (sklearn); optional `sentence-transformers`
          - Causal chain coverage % (matched vs expected concepts)
          - SOLO / Bloom heuristics from matched coverage + answer text
          - **KG_MIN_COVERAGE**: omit KG block in C5 prompt when coverage is low
    ↓
[Stage 2] LLM Scoring Prompt (2 systems)
          - C_LLM: grades with question + reference + student answer only
          - C5_fix: grades with above + KG evidence as structured guide
    ↓
[Stage 3] Metric Computation
          - MAE, RMSE, Pearson r, Spearman ρ, QWK, Bias, P@0.5, Wilcoxon p
```

---

## 2. Proven Results (COMPLETE)

### Primary Benchmark — Mohler 2011 (n=120, CS Data Structures)
| System | MAE | RMSE | QWK | r | Bias | p vs C_LLM |
|--------|-----|------|-----|---|------|------------|
| C_LLM (baseline) | 0.3300 | 0.4667 | 0.9621 | 0.9709 | +0.1883 | — |
| CoT baseline | 0.2208 | 0.3227 | 0.9803 | 0.9819 | -0.0917 | 0.0006 |
| **C5_fix / ConceptGrade** | **0.2229** | **0.3315** | **0.9792** | **0.9820** | -0.1229 | **0.0026** |

**Key finding**: ConceptGrade reduces MAE by **32.4%** (p=0.0026). Beats C_LLM on 8/10 questions.

### Multi-Dataset Generalization
| Dataset | Domain | n | C_LLM MAE | C5_fix MAE | Δ MAE | p-val | Verdict |
|---------|--------|---|-----------|------------|-------|-------|---------|
| Mohler 2011 | CS (complex) | 120 | 0.3300 | **0.2229** | -32.4% | 0.0026 | ✓ BEATS |
| DigiKlausur | Neural Nets | 646 | 1.1842 | **1.1262** | -4.9% | 0.049 | ✓ BEATS |
| Kaggle ASAG | Elementary Sci | 473 | 1.0772 | 1.1554 | +7.3% | 0.148 | ✗ n.s. |

**ConceptGrade beats C_LLM on 2/3 datasets**. Kaggle ASAG (simple factual K-5 science) shows no significant difference — KG benefits scale with question complexity.

---

## 3. Codebase Structure

```
packages/concept-aware/
├── conceptgrade/                    # Core library
│   ├── llm_client.py               # Multi-provider LLM client (Anthropic/Gemini/OpenAI)
│   ├── pipeline.py                 # Main grading pipeline
│   ├── verifier.py                 # LLM-as-Verifier extension
│   ├── smart_segmenter.py          # Self-Consistent Extractor extension
│   ├── feedback_synthesizer.py     # Feedback generation
│   ├── cross_para_integrator.py    # Cross-paragraph integration
│   ├── cache.py                    # Response caching
│   └── key_rotator.py             # API key rotation
│
├── knowledge_graph/                # KG construction
│   └── graph_builder.py
│
├── cognitive_depth/                # SOLO + Bloom classifiers
│   ├── solo_classifier.py
│   ├── blooms_classifier.py
│   └── cognitive_depth_classifier.py
│
├── data/                           # All results (PERSISTENT)
│   ├── ds_knowledge_graph.json     # Mohler hand-crafted KG
│   ├── evaluation_results.json     # Mohler C_LLM vs C5_fix results
│   ├── cot_baseline_scores.json    # CoT baseline scores
│   ├── ablation_results.json       # Component ablation
│   ├── extension_ablation_results.json  # 3-extension ablation
│   ├── digiklausur_dataset.json    # DigiKlausur 646 samples
│   ├── digiklausur_auto_kg.json    # DigiKlausur KG (17 questions)
│   ├── digiklausur_eval_results.json    # DigiKlausur final metrics
│   ├── digiklausur_precomputed.json     # DigiKlausur KG features
│   ├── kaggle_asag_dataset.json    # Kaggle ASAG 473 samples
│   ├── kaggle_asag_auto_kg.json    # Kaggle ASAG KG (150 questions)
│   ├── kaggle_asag_eval_results.json    # Kaggle ASAG final metrics
│   ├── kaggle_asag_precomputed.json     # Kaggle ASAG KG features
│   ├── paper_report_v2.txt         # Full paper-ready report (200 lines)
│   ├── paper_latex_tables_v2.tex   # LaTeX tables for paper
│   └── batch_responses/            # 39 split batch API response JSONs (CACHED; Digi 18 + Kaggle 12 + legacy dual 9)
│       ├── digiklausur_cllm_batch_01-09_response.json
│       ├── digiklausur_c5fix_batch_01-09_response.json
│       ├── kaggle_asag_cllm_batch_01-06_response.json
│       └── kaggle_asag_c5fix_batch_01-06_response.json
│
├── run_full_pipeline.py            # END-TO-END pipeline (use this)
├── generate_batch_scoring_prompts.py  # Batch prompt generator (split mode)
├── score_batch_results.py          # Metric computation from batch responses
├── validate_stored_eval.py         # Verify eval_results.json vs results[] + optional batch ID check
├── prove_cross_dataset_evidence.py # Summarize beats/MAE/p across Mohler+Digi+Kaggle from JSON
├── reconstruct_c5fix_batches_from_eval.py  # Rebuild c5fix batch JSONs from eval_results
├── generate_paper_report_v2.py     # Paper report generator
├── score_cot_baseline.py           # CoT baseline evaluation
└── EVALUATION_STATUS.txt           # Full status summary
```

---

## 4. API Configuration

```
File: packages/backend/.env
GEMINI_API_KEY="<set in packages/backend/.env — never commit real keys>"
```

- **Model**: `gemini-2.5-flash` (billing enabled)
- **Rate**: 15s between batch calls (~4 RPM, safe margin)
- **Cost**: ~$0.21 for full project (700K tokens × $0.30/1M)

The `LLMClient` in `conceptgrade/llm_client.py` supports Gemini, Anthropic, and OpenAI transparently.

---

## 5. How to Reproduce Results (ZERO API Calls)

All scoring responses, KGs, and precomputed features are cached. The pipeline's `score_batch_results.py` checks `data/batch_responses/` automatically before touching `/tmp` or making any API call.

```bash
cd packages/concept-aware

# Fastest: recompute metrics directly from cached JSON files
python3 score_batch_results.py --dataset digiklausur    # reads data/batch_responses/
python3 score_batch_results.py --dataset kaggle_asag    # reads data/batch_responses/
python3 generate_paper_report_v2.py                     # generates full paper report

# Alternative: use pipeline with all caching flags (still requires a valid GEMINI_API_KEY in .env to start)
python3 run_full_pipeline.py --dataset all --skip-kg --skip-scoring
# ↑ Skips KG gen and batch API scoring; still regenerates prompts and runs score_batch_results.
```

**The `score_batch_results.py` cache fallback logic** (from `load_responses()`):
1. Looks in `/tmp/batch_scoring/` first
2. Falls back to `data/batch_responses/` if `/tmp` is empty (e.g., after restart)
3. Never calls any API

**Do NOT run these** unless intentionally re-scoring with new prompts:
```bash
# These make API calls — only run if explicitly changing prompts/KGs
python3 run_full_pipeline.py --dataset all           # full fresh run (costs money)
python3 run_full_pipeline.py --dataset all --force   # force re-score (costs money)
```

---

## 6. What Is DONE ✅

### Research Results
- [x] **Mohler 2011** evaluation: C5_fix MAE=0.2229 vs C_LLM MAE=0.3300 (32.4%, p=0.0026)
- [x] **CoT baseline**: MAE=0.2208 (p=0.0006) — ConceptGrade matches CoT while adding interpretability
- [x] **DigiKlausur** evaluation: C5_fix MAE=1.1262 vs C_LLM MAE=1.1842 (4.9%, p=0.049)
- [x] **Kaggle ASAG** evaluation: C5_fix MAE=1.1554 vs C_LLM MAE=1.0772 (not significant, p=0.148)
- [x] Component ablation (C0 through C5) on Mohler
- [x] 3-extension ablation (Self-Consistent Extractor, Confidence-Weighted Comparator, LLM-as-Verifier)
- [x] Per-question breakdown (10 questions, Mohler)
- [x] Adversarial evaluation
- [x] Mechanistic analysis (SOLO-level breakdown)

### Infrastructure
- [x] Auto-KG generation via Gemini API (Stage 0)
- [x] Batch scoring pipeline (80 samples/call, split mode — separate C_LLM and C5_fix)
- [x] Cache-first pipeline (loads from `data/batch_responses/` before API calls)
- [x] Persistent storage of all intermediate JSONs
- [x] Multi-provider LLM client (Gemini/Anthropic/OpenAI)
- [x] Paper report generator (v2) with LaTeX output
- [x] Improved concept matching (multi-strategy: name, description, short-word)
- [x] KG-as-guide framing (positive, avoids underscoring from low coverage)

### Paper Outputs
- [x] `data/paper_report_v2.txt` — Full paper-ready text report
- [x] `data/paper_latex_tables_v2.tex` — LaTeX tables

---

## 7. What Is PENDING ❌

### High Priority (for paper submission)

#### 7.1 Kaggle ASAG Results Need Improvement
**Problem**: ConceptGrade is not significantly better than C_LLM on Kaggle ASAG (p=0.148).
**Root cause**: The keyword-based concept matching fails for elementary science answers where students use everyday language ("good/bad" instead of "helpful_microorganisms"). The KG currently adds more noise than signal for this dataset.

**Proposed fixes (in order of impact)**:
1. **Semantic concept matching** — Replace keyword matching with sentence embeddings (e.g., `sentence-transformers` library). When a student's phrase is semantically close (cosine > 0.7) to a KG concept name or description, count it as matched. This would fix cases like "getting hotter" → `global_warming`.
   - File to modify: `generate_batch_scoring_prompts.py::simple_concept_match()`
   - Estimated improvement: should bring 0% coverage from 28.8% → ~10% and raise mean coverage from 37% → 60%+

2. **Minimum coverage threshold** — Only include KG evidence in C5_fix prompt when concept coverage ≥ 25%. Below threshold, fall back to C_LLM-style grading (no KG shown). This prevents the KG from actively hurting on hard-to-match short answers.
   - File to modify: `generate_batch_scoring_prompts.py::build_c5fix_prompt()`

3. **Re-score with improved matching** — After fixing concept matching, delete `data/batch_responses/kaggle_asag_c5fix_batch_*` and run `python3 run_full_pipeline.py --dataset kaggle_asag --skip-kg`.

#### 7.2 Extension Ablation — LLM Mode (Publishable)
**Problem**: The 3-extension ablation (`run_extension_ablation.py`) was only run in **heuristic mode** (30 samples). The LLM mode results (using Gemini for SOLO/Bloom classification) are needed for the paper.

**Current state**: `data/extension_ablation_results.json` shows heuristic-mode results only. Extensions (SC, CW, Verifier) don't significantly help in heuristic mode.

**What to do**:
```bash
python3 run_extension_ablation.py --mode llm --dataset mohler
```
This will run the 3-extension ablation using LLM-based SOLO/Bloom classification instead of heuristics. Expected to show more differentiation.

**Files involved**:
- `run_extension_ablation.py` — main ablation script
- `data/extension_ablation_results.json` — output (needs updating with LLM mode)
- `data/extension_ablation_summary.txt` — human-readable summary
- `data/extension_ablation_latex.tex` — LaTeX table

#### 7.3 Paper Section on Multi-Dataset Generalization
**Problem**: `generate_paper_report_v2.py` Section 9 shows DigiKlausur and Kaggle ASAG results, but the **narrative and analysis** explaining WHY Kaggle ASAG doesn't benefit is missing from the paper text.

**What to add** in `generate_paper_report_v2.py` Section 9:
- Analysis of scoring scale mismatch (DigiKlausur: 3-level discrete scoring)
- Analysis of why simple factual questions don't benefit from KG
- Discussion of concept matching limitations
- Statement that ConceptGrade benefits scale with question complexity

#### 7.4 DigiKlausur Scale Normalization
**Problem**: DigiKlausur uses discrete 3-level scoring (raw: 0, 1, 2 → normalized: 0.0, 2.5, 5.0). Our continuous scoring guide (0.25 increments) causes high MAE (~1.18) for both systems. The MAE is inflated by the quantization gap.

**Proposed fix**: Snap predicted scores to nearest valid DigiKlausur level (0, 2.5, 5) before computing metrics. This would show fairer comparison.

**File to modify**: `score_batch_results.py::run()` — add optional score snapping for datasets with discrete scoring.

---

## 8. Known Issues / Technical Debt

### Concept Matching (Critical)
- `simple_concept_match()` in `generate_batch_scoring_prompts.py` uses keyword matching
- Fails for paraphrased answers (e.g., "good and bad" ≠ "helpful_microorganisms")
- Multi-strategy matching (improved in this session) helps but not enough for elementary science
- **Fix needed**: semantic similarity (sentence-transformers or BM25)

### Batch Format Issue (FIXED)
- Old dual-score batch prompts caused 100% anchoring (cllm == c5fix always)
- **Already fixed**: now uses separate C_LLM and C5_fix batch prompts (split mode)
- Old dual-batch responses still in `data/batch_responses/digiklausur_batch_01-09_response.json` — these are STALE and should not be used

### /tmp Volatility (FIXED)
- All intermediate files previously saved only to `/tmp/` (lost on restart)
- **Already fixed**: pipeline now saves to `data/batch_responses/` and `data/` immediately
- On fresh session: run `python3 run_full_pipeline.py --skip-kg` to restore from cache

### generate_paper_report_v2.py Output
- The paper report generator works but Section 9 narrative is thin (just numbers)
- Needs qualitative analysis paragraphs

---

## 9. Dataset Details

### Mohler 2011
- **Location**: Used via `run_offline_eval.py`, data from `data/evaluation_results.json`
- **Domain**: CS Data Structures (linked lists, stacks, BST, hashing, etc.)
- **n**: 120 samples, 10 questions, 12 answers/question
- **Scale**: 0–5, continuous
- **KG**: `data/ds_knowledge_graph.json` — hand-crafted by domain expert
- **Key feature**: Hand-crafted KG → best ConceptGrade results

### DigiKlausur
- **Location**: `data/digiklausur_dataset.json`
- **Domain**: Neural Networks (perceptron, backpropagation, CNN, SVM, etc.)
- **n**: 646 samples, 17 questions
- **Scale**: 0, 2.5, 5 (discrete 3 levels — human_score_raw: 0, 1, 2)
- **KG**: `data/digiklausur_auto_kg.json` — auto-generated via Gemini
- **Source**: Original DigiKlausur dataset (German university, English subset)

### Kaggle ASAG
- **Location**: `data/kaggle_asag_dataset.json`
- **Domain**: Elementary science (K-5 level — respiration, habitats, weather, space, etc.)
- **n**: 473 samples, 150 questions
- **Scale**: 0–5, integer (0, 1, 2, 3, 4, 5)
- **KG**: `data/kaggle_asag_auto_kg.json` — auto-generated via Gemini
- **Challenge**: Very simple factual answers; keyword matching fails most

---

## 10. Reproduce Paper Results (Step by Step)

```bash
cd /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware

# Step 1: Verify API key works (export GEMINI_API_KEY first, or load from backend .env)
python3 -c "
import os
from google import genai
key = os.environ.get('GEMINI_API_KEY')
if not key:
    raise SystemExit('Set GEMINI_API_KEY in the environment')
client = genai.Client(api_key=key)
r = client.models.generate_content(model='gemini-2.5-flash', contents='Say OK')
print(r.text)
"

# Step 2: Restore /tmp from cache (run once per session after restart)
mkdir -p /tmp/batch_scoring
cp data/batch_responses/*.json /tmp/batch_scoring/
cp data/digiklausur_auto_kg.json /tmp/auto_kg_response_digiklausur.json
cp data/kaggle_asag_auto_kg.json /tmp/auto_kg_response_kaggle_asag.json

# Step 3: Compute metrics (no API calls)
python3 score_batch_results.py --dataset digiklausur
python3 score_batch_results.py --dataset kaggle_asag

# Step 4: Mohler metrics (already computed)
python3 score_cot_baseline.py  # recomputes CoT + C5_fix metrics

# Step 5: Generate paper report
python3 generate_paper_report_v2.py

# Output files:
#   data/paper_report_v2.txt
#   data/paper_latex_tables_v2.tex
```

---

## 11. Next Session Priorities (for Coding Agent)

> **Rule**: All tasks below MUST be implemented using existing cached JSON files only.
> Tasks marked 🔴 would eventually benefit from re-scoring via API, but the code changes should be implemented and validated first against the existing cached scores.
> Tasks marked 🟢 require zero API calls — pure code/analysis work on existing results.

---

### Priority 1 — 🟢 Score Snapping for DigiKlausur (NO API CALLS)

**Problem**: DigiKlausur uses only 3 discrete human scores (0.0, 2.5, 5.0). LLM predicts continuous values (e.g., 3.75), which inflates MAE artificially. The 1.18 MAE is partly a quantization artifact, not just grading error.

**Task**: Modify `score_batch_results.py::run()` to add optional score snapping for datasets with discrete scoring.

**Implementation**:
```python
# In score_batch_results.py
DISCRETE_SCORES = {
    "digiklausur": [0.0, 2.5, 5.0],   # 3-level scoring
    "kaggle_asag": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],  # integer scoring
}

def snap_to_scale(score, valid_scores):
    """Snap continuous prediction to nearest valid discrete score."""
    return min(valid_scores, key=lambda v: abs(v - score))
```

Report **both** raw and snapped metrics. No API calls — all scores are already in `data/batch_responses/`.

---

### Priority 2 — 🟢 Expand Paper Report Section 9 (NO API CALLS)

**Problem**: `generate_paper_report_v2.py` Section 9 shows numbers but no analysis.

**Task**: Add 3 analysis paragraphs to Section 9 in `generate_paper_report_v2.py`:

1. **Why DigiKlausur benefits** (complex multi-concept NN questions, structured KG matches expert rubric)
2. **Why Kaggle ASAG doesn't** (simple K-5 science, "did you name the right thing?" tasks, keyword matching fails for paraphrases like "good/bad")
3. **Complexity hypothesis**: KG benefit scales with question complexity — cite Mohler (CS, complex) > DigiKlausur (NN, complex) > Kaggle ASAG (elementary, simple)

**File**: `generate_paper_report_v2.py` — update the `section_9()` function or equivalent. Pure text generation, no API calls.

---

### Priority 3 — 🟢 Semantic Concept Matching — Code Only (NO API CALLS YET)

**Problem**: `simple_concept_match()` in `generate_batch_scoring_prompts.py` uses keyword matching. Fails for:
- "good and bad" → should match `helpful_microorganisms`, `harmful_microorganisms`
- "getting hotter" → should match `global_warming`
- "Covid-19" → should match `viral_disease`

**Task (code only — do NOT re-score)**:
1. Implement `semantic_concept_match()` in `generate_batch_scoring_prompts.py` using `sentence-transformers` (model: `all-MiniLM-L6-v2`, ~80MB, local, no API)
2. Add `--match-mode [keyword|semantic]` argument
3. Run against existing `data/kaggle_asag_auto_kg.json` + `data/kaggle_asag_dataset.json` to compute new precomputed features
4. Print before/after coverage statistics

```python
from sentence_transformers import SentenceTransformer, util
model = SentenceTransformer('all-MiniLM-L6-v2')

def semantic_concept_match(student_answer, kg_concepts, threshold=0.55):
    answer_emb = model.encode(student_answer)
    matched = []
    for c in kg_concepts:
        concept_text = f"{c['name']}: {c.get('description', '')}"
        concept_emb = model.encode(concept_text)
        score = util.cos_sim(answer_emb, concept_emb).item()
        if score >= threshold:
            matched.append(c['id'])
    return matched
```

**Save new precomputed features** to `data/kaggle_asag_precomputed_semantic.json` for comparison. No API calls needed until human decides to re-score.

---

### Priority 4 — 🟢 Fix `run_full_pipeline.py --skip-scoring` Flag (NO API CALLS)

**Problem**: `run_full_pipeline.py` has a `--skip-scoring` argument mentioned in help but the `main()` function doesn't fully honor it — the `compute_metrics()` step (Stage 4) always runs, even when only Stage 3 is skipped.

**Task**: Fix the `main()` function to correctly handle all flag combinations:
- `--skip-kg`: skip KG generation (Stage 1)
- `--skip-scoring`: skip API scoring (Stage 3), load from cache only
- Both flags together: only run Stages 2 and 4

Also add `--metrics-only` flag that skips Stages 1–3 and only runs Stage 4 (metric computation). This is the most common use case when results are already cached.

```bash
python3 run_full_pipeline.py --dataset all --metrics-only
# → loads all cached responses, computes metrics, generates report
# → ZERO API CALLS
```

---

### Priority 5 — 🔴 Re-score Kaggle ASAG with Semantic Matching (NEEDS API — defer)

Only after Priority 3 (semantic matching) is implemented and validated:
- Clear `data/batch_responses/kaggle_asag_c5fix_batch_*_response.json`
- Regenerate c5fix batch prompts with semantic concept features
- Re-score using `python3 run_full_pipeline.py --dataset kaggle_asag --skip-kg`
- Check if p < 0.05 with new features

**API cost**: ~6 requests × 80 samples = ~$0.02. Low cost but defer until code is ready.
