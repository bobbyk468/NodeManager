# ConceptGrade Evaluation Pipeline

## Overview

This pipeline automates the end-to-end evaluation of ConceptGrade across multiple datasets, generating knowledge graphs, scoring answers, computing metrics, and generating visualizations for the frontend dashboard.

## Five-Stage Pipeline

### Stage 1: Knowledge Graph (KG) Generation
- **Purpose**: Extract key domain concepts and relationships from question/reference answer pairs
- **Method**: Gemini API call with KG extraction prompt
- **Output**: `data/{dataset}_auto_kg.json`
- **Caching**: Persistent cache in `data/` + working cache in `/tmp/`
- **Cost**: ~$0.01 per dataset (30 questions per API call)
- **Skip with**: `--skip-kg`

### Stage 2: Batch Prompt Generation
- **Purpose**: Create batch scoring prompts for both C_LLM (LLM-only) and C5_fix (KG-augmented) systems
- **Method**: Split answers into batches, generate paired prompts with KG features
- **Output**: `data/tmp/{dataset}_cllm_batch_*.txt` + `{dataset}_c5fix_batch_*.txt`
- **Cost**: Zero (local computation)
- **Skip with**: `--metrics-only`

### Stage 3: Batch Scoring via Gemini
- **Purpose**: Score all answer batches using Gemini API
- **Method**: Submit batch prompts, cache responses by model+prompt hash
- **Output**: `data/tmp/{dataset}_*_response.json` + persistent backup in `data/batch_responses/`
- **Caching**: Automatic by prompt hash (disable with `GEMINI_SCORING_CACHE=0`)
- **Cost**: ~$0.02–0.05 per dataset depending on answer count
- **Skip with**: `--skip-scoring`

### Stage 4: Metrics Computation
- **Purpose**: Compare C_LLM vs C5_fix scores, compute MAE/Wilcoxon p-values, generate tables
- **Method**: Parse cached batch responses, run statistical tests
- **Output**: `data/{dataset}_eval_results.json`, table rows for paper
- **Cost**: Zero (local computation)
- **Always runs**: Even with `--metrics-only` (it's the computation step)

### Stage 5: Dashboard Extras (MANDATORY)
- **Purpose**: Generate radar charts and heatmaps for frontend dashboard visualization
- **Method**: Call `generate_dashboard_extras.py` for each dataset
- **Output**: `data/{dataset}_dashboard_extras.json` with radar data + heatmap indices
- **Cost**: Zero (local JSON generation)
- **Importance**: **REQUIRED** before frontend `npm start` — without it, dashboard charts are empty
- **Error handling**: Warns if generation fails but continues pipeline

## Usage

### Full Pipeline (All Stages)
```bash
python3 run_full_pipeline.py                          # All datasets (Stages 1–5)
python3 run_full_pipeline.py --dataset digiklausur    # One dataset
python3 run_full_pipeline.py --dataset kaggle_asag    # Another dataset
```

### Skip KG Generation (Use Cached KG)
```bash
python3 run_full_pipeline.py --skip-kg                # Stages 2–5 only
```

### Metrics & Dashboard Only (No API Calls)
```bash
python3 run_full_pipeline.py --metrics-only           # Stages 4–5 only (ZERO API cost)
```

### Skip Scoring (Recompute Metrics from Cached Responses)
```bash
python3 run_full_pipeline.py --skip-scoring           # Stages 2, 4–5 (no API scoring)
```

### Re-run with Fresh Data (Ignore Cache)
```bash
python3 run_full_pipeline.py --force                  # All stages, ignore all caches
```

### Score Only C5_fix (Useful When Tweaking KG Features)
```bash
python3 run_full_pipeline.py --only-system c5fix --skip-kg
```

## Replication Package Instructions

For users replicating results from cloned repo:

1. **Run the full pipeline** (generates metrics + dashboard data):
   ```bash
   cd packages/concept-aware/
   python3 run_full_pipeline.py --metrics-only        # Zero API cost, uses cached responses
   ```

2. **Start frontend dashboard**:
   ```bash
   cd packages/frontend/
   npm install
   npm start
   ```

The dashboard will display radar charts and heatmaps for all datasets. If charts are empty, ensure Stage 5 completed successfully:
```bash
python3 generate_dashboard_extras.py --dataset all
```

## Environment Variables

- `GEMINI_API_KEY` — API key for Gemini calls (or load from `packages/backend/.env`)
- `GEMINI_KG_MODEL` — Model for KG generation (default: `gemini-2.5-flash`)
- `GEMINI_SCORING_MODEL` — Model for scoring (default: `gemini-2.5-flash`)
- `GEMINI_RATE_SLEEP_SEC` — Wait time between API calls (default: `15`)
- `GEMINI_SCORING_CACHE` — Enable response caching by prompt hash (default: `1`, set to `0` to disable)
- `CONCEPTGRADE_BATCH_DIR` — Where to store batch files (default: `data/tmp/`)

## Output Files

After running the full pipeline:

```
data/
├── {dataset}_auto_kg.json                      # Stage 1: Knowledge graphs
├── {dataset}_eval_results.json                 # Stage 4: Metrics (MAE, p-values)
├── {dataset}_dashboard_extras.json             # Stage 5: Radar + heatmap data
├── gemini_scoring_cache/                       # Stage 3: Response cache (by prompt hash)
├── batch_responses/                            # Stage 3: Persistent backup of responses
└── paper_report_v2.txt                         # Final paper section (generated after all stages)

/tmp/
├── auto_kg_response_{dataset}.json             # Stage 1: Working copy of KGs
├── {dataset}_cllm_batch_*.txt                  # Stage 2: Batch prompts (C_LLM)
├── {dataset}_c5fix_batch_*.txt                 # Stage 2: Batch prompts (C5_fix)
└── {dataset}_*_response.json                   # Stage 3: Batch scoring responses
```

## Cost Estimates

- **Full pipeline (Stages 1–5)**: ~$0.03–0.08 per dataset
  - Stage 1 (KG): ~$0.01
  - Stage 3 (Scoring): ~$0.02–0.05 per dataset
  - Stages 2, 4, 5: $0 (local computation)

- **Metrics-only (Stages 4–5)**: $0 (uses cached Stage 3 responses)

## Troubleshooting

### "Dashboard extras generation failed"
**Problem**: Stage 5 failed or skipped.
```bash
# Run manually to see error details:
python3 generate_dashboard_extras.py --dataset digiklausur
```

**Solution**: Check that eval results exist:
```bash
ls -l data/digiklausur_eval_results.json
```

If missing, run `--metrics-only` first to recompute.

### "429: Quota exceeded" during Stage 3
**Problem**: API rate limit hit.
**Solution**: Wait 24 hours or adjust quota in Google Cloud console. Pipeline automatically retries with exponential backoff.

### Empty dashboard charts
**Problem**: Stage 5 didn't generate `*_dashboard_extras.json`.
**Solution**:
```bash
python3 generate_dashboard_extras.py --dataset all
```

Then restart frontend:
```bash
npm start  # Frontend will pick up new dashboard_extras.json files
```

## Next Steps

After pipeline completes:
1. Open `data/paper_report_v2.txt` to verify metrics match expected tables
2. Start frontend dashboard: `npm start`
3. Verify visualizations display correctly (radar charts, heatmaps)
4. Generate paper PDFs: `generate_paper_report_v2.py` (already run by pipeline)
