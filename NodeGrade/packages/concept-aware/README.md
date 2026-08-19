# ConceptGrade

A knowledge-graph-driven automated short-answer grading (ASAG) system for
Computer Science education. ConceptGrade extracts a concept graph from a
student's free-text answer, compares it against an expert-curated domain
knowledge graph, and combines that comparison with cognitive-depth
assessment (Bloom's/SOLO), misconception detection, and an LLM verifier
into a final score plus structured, actionable feedback.

This repository backs two papers:

- **Paper 1** (`paper/main.tex`, submission version; full historical draft
  in `docs/ConceptGrade_FullPaper.tex`) — the grading-accuracy evaluation.
- **Paper 2** (`docs/paper_phase2_vis2027.tex`) — the visual-analytics
  dashboard and educator user study.

## Important: read this before trusting any number in Paper 1

An earlier draft of Paper 1 reported results computed against a
hand-authored, fabricated 120-sample fixture rather than the real Mohler
et al. (2011) benchmark. We found this ourselves during internal review,
corrected every affected number, and documented the full incident —
including a second, independently-found correction (a stale machine-IRR
kappa value) — in **[REPRODUCIBILITY.md](REPRODUCIBILITY.md)**. Start
there, not here, if you want the full record of what changed and why.

## Reproducing this paper's results

**Setup:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-concept-aware.txt
```

**Fastest path — verify every numerical claim in Paper 1 at once (~10
seconds, $0, no API calls):**

```bash
python3 verify_all_paper_claims.py
```

This reads cached evaluation results and the paper's own `.tex` source and
checks every reported number against them directly. It is the
authoritative check — if you only run one thing, run this. A passing run
ends with `PASS: all 378 claims verified against cached data`.

**Reproducing individual results:** every number in Paper 1 maps to a
specific script and cached input in the reproducibility table in
[REPRODUCIBILITY.md](REPRODUCIBILITY.md#master-verification-command-10-seconds-0).
A few of the most commonly-needed ones:

```bash
python3 compute_cross_dataset_significance.py   # cross-dataset meta-analysis (Table: crossdataset_sensitivity)
python3 compute_solo_breakdown.py               # per-SOLO-band MAE, all three datasets
python3 compute_calibration_analysis.py         # post-hoc recalibration (Table: calibration)
python3 compute_lmm_reanalysis.py               # linear mixed-effects sensitivity analysis
python3 compute_taxonomy_kappa.py --all         # machine-IRR pilot for the misconception taxonomy (use --all, not the n=30 default)
python3 compute_frontier_baselines_significance.py  # frontier-model comparison (Table: frontier); needs the cached data/mohler_real_eval_results_{claude,gpt,deepseek}.json files, no API calls
```

To reproduce the frontier-model comparison's underlying data from scratch (real API calls, ~$0.50 total via OpenRouter, needs `OPENROUTER_API_KEY` in `packages/backend/.env`):

```bash
python3 run_frontier_baselines_batched.py --model claude
python3 run_frontier_baselines_batched.py --model gpt
python3 run_frontier_baselines_batched.py --model deepseek
```

**Before running anything else in this repo**, note two things
REPRODUCIBILITY.md explains in more detail:

- `compute_clustered_significance.py` and `compute_human_irr_and_per_question.py`
  default to the old, retracted 120-sample fixture, quarantined at
  `archive/fabricated_fixtures/mohler_eval_results.json`. Their unflagged
  output reproduces the **retracted** historical result (32.4% MAE
  reduction, n=120), not the paper's current real-data claim (8.2%,
  n=1,262). This is intentional — they exist to reproduce the
  historical/retracted record for the supplementary materials — but do not
  mistake their default output for a current claim.
- `data/ds_knowledge_graph.json` is the **frozen v1.0-expert** knowledge
  graph snapshot every evaluation number in Paper 1 was computed against
  (101 concepts, 138 relationships). The live builder in
  `knowledge_graph/ds_knowledge_graph.py` now produces a newer v1.1-expert
  version (187 relationships) that is **not** the evaluated snapshot —
  never overwrite `data/ds_knowledge_graph.json` with its output.

## Repository layout

| Path | What it is |
|---|---|
| `paper/` | Submission-ready version of Paper 1 (`main.tex`) and its figures |
| `docs/` | Full historical draft of Paper 1, Paper 2, and generated documentation |
| `supplementary/` | Retracted fabricated-data analysis and relocated secondary analyses, kept for the record |
| `conceptgrade/` | The production grading pipeline (`pipeline.py`, verifier) |
| `knowledge_graph/` | Domain knowledge graph builders (Data Structures, Programming, Algorithms) |
| `concept_extraction/`, `graph_comparison/`, `misconception_detection/` | The five-layer pipeline's component modules |
| `datasets/` | Dataset loaders (real Mohler, DigiKlausur, Kaggle ASAG) |
| `data/` | Cached evaluation results and frozen data snapshots that every reported number is reproducible from |
| `REPRODUCIBILITY.md` | The authoritative record: every claim, its script, its cached input, and the full fabrication-correction incident report |

## License / data

**Mohler dataset** (`data/mohler_real/`, and every `*_phaseA_signals.json`/
`*_eval_results.json`/etc. derived from it): sourced from the
`nkazi/MohlerASAG` mirror on Hugging Face
(https://huggingface.co/datasets/nkazi/MohlerASAG), licensed **CC-BY-4.0**
(license confirmed directly against the Hugging Face dataset page,
2026-08-19). CC-BY-4.0 permits redistribution and derivative works of the
underlying student responses, with attribution. Attribution:

> Mohler, M., & Mihalcea, R. (2011). Learning to Grade Short Answer
> Questions using Semantic Similarity Measures and Dependency Graph
> Alignments. *Proceedings of the 49th Annual Meeting of the Association
> for Computational Linguistics: Human Language Technologies*, Portland,
> Oregon. Data accessed via the `nkazi/MohlerASAG` processed mirror on
> Hugging Face (https://huggingface.co/datasets/nkazi/MohlerASAG), per
> that repository's citation request.

See `data/mohler_real/PROVENANCE.md` for the full download/selection
record.

**DigiKlausur dataset**: `DigiKlausur/ASAG-Dataset`, MPL-2.0.

**Kaggle ASAG dataset**: see REPRODUCIBILITY.md and
`docs/DATASET_PROVENANCE_REVIEW_REQUEST.md` for the provenance note
(acquisition path unverified, kept in the evaluation as
provenance-unverified, not authenticated -- a separate, still-open
question from the resolved Mohler licensing question above).
