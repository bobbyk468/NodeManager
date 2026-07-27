# Reproducibility Guide — ConceptGrade (Paper 1 + Paper 2)

This file maps every quantitative claim in either paper to the script that
produces it, the cached input it reads, and the exact command to re-run it.
Designed so a reviewer can verify any number in either paper in seconds.

---

## Environment

```bash
cd packages/concept-aware
# Python 3.11+ (tested on 3.14.2)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-frozen.txt   # exact paper-claim versions
```

The paper's reported $W_+$, $p$ values, $d_z$, and meta-analysis pool are
computed with `scipy 1.17.1` (Wilcoxon with `zero_method='wilcox'`). The
scripts pin `zero_method='wilcox'` explicitly so they are stable against
the scipy 1.9+ default change to `'auto'`.

A single API key is needed only for the optional live pipeline smoke test
(everything else uses cached eval results, $0 spend):

```bash
# Sourced from packages/backend/.env if present
GEMINI_API_KEY=...
```

---

## Master verification command (~5 seconds, $0)

```bash
.venv/bin/python -m pytest tests/ -q                          # 38/38 unit tests
.venv/bin/python compute_clustered_significance.py            # Paper 1 §4.2
.venv/bin/python compute_cross_dataset_significance.py        # Paper 1 §4.3
.venv/bin/python compute_solo_breakdown.py                    # Paper 1 §5
.venv/bin/python compute_taxonomy_kappa.py --all              # Paper 1 §3.4
.venv/bin/python smoke_run_mohler.py                          # pipeline smoke (cache hit)
.venv/bin/python compute_real_fixes.py                        # Paper 1 §5 + Table 2
.venv/bin/python compute_real_fixes_v2.py                     # Paper 1 §5 (cluster bootstrap + mpnet + BCa)
.venv/bin/python compute_human_irr_and_per_question.py        # Paper 1 §5 + §7 (human IRR + per-question)
.venv/bin/python verify_all_paper_claims.py                   # cross-checks 67 paper claims against cached data
```

The last script (`verify_all_paper_claims.py`) is the **single-shot
integrity check** for BOTH papers: it reproduces 97 separate quantitative
and structural claims (67 from Paper 1 + 30 from Paper 2) against the
cached metadata and source files, then exits non-zero on any mismatch.
Errors caught and fixed by this script include:
- `Llama-3.3-70b` → `gemini-2.5-flash` baseline naming (6 occurrences, P1)
- MiniLM Pearson r 0.301 → 0.649 (P1 Table 2 + text)
- κ cached file regenerated with wrong default n (n=30 → n=120)

Paper 2 coverage: shared ML numbers (1,239 / 177 / p=0.0026 / I²=70% /
473/473), Verifier-training math (630×3+217=2,107), study design
arithmetic (N=64=2×32, Holm-Bonferroni α₁=0.05/5=0.01), VGTC document
class, supplementary file existence (OSF/IRB/PILOT/VALIDATION_GATE docs),
explicit [TBD] placeholders, and PRE-SUBMISSION PLACEHOLDER labels on
mock figures. This script is the recommended pre-submission gate.

`compute_human_irr_and_per_question.py` computes two cached-data checks:
- Human IRR on the Mohler 2-rater ground truth (r=0.985, QWK=0.984)
- Per-question MAE breakdown (8/10 questions C5 wins)

`compute_real_fixes_v2.py` produces three additional numbers:
- REAL-5: all-mpnet-base-v2 (110M params, frozen) baseline on the same n=90 Mohler test split
- REAL-6: cluster bootstrap 95% CIs for all datasets, resampling at the question level
- REAL-7: BCa bootstrap sensitivity on the Mohler test-set MAE-reduction CI

`compute_real_fixes.py` produces four numbers used in the paper that
require either bootstrap resampling or a Sentence-BERT model load:

- REAL-1: Mohler n=90 test-split bootstrap 95% CI for MAE reduction
- REAL-2: misconception-module ablation (concepts_only vs C5_fix)
- REAL-3: local Sentence-BERT (all-MiniLM-L6-v2, frozen, no fine-tune)
  baseline on the same n=90 Mohler test split (replaces the historical
  published-on-different-split BERT row in Table~2)
- REAL-4: bootstrap 95% CIs for MAE reduction on all three datasets

If the eight commands above succeed, every cited statistic in the
ConceptGrade papers is verified against the cached real data.

---

## Per-claim mapping — Paper 1 (NLP/EdAI)

### Abstract / Intro headline numbers

| Claim in paper | Number | Script | Cached input |
|---|---|---|---|
| MAE C\_LLM → C5\_fix (Mohler) | 0.330 → 0.223 (32.4%) | `compute_clustered_significance.py` | `data/mohler_eval_results.json` |
| Wilcoxon $W_+$ (Mohler) | 344 | same | same |
| Wilcoxon two-tailed (Mohler) | $p = 0.0026$ | same | same |
| Wilcoxon one-tailed (Mohler) | $p = 0.0013$ | same | same |
| Paired Cohen's $d_z$ (Mohler) | $-0.295$ | same | same |
| Post-hoc power (Mohler, $\alpha=0.05$, one-tail) | $0.943$ | same | same |
| Non-tied subset Mohler MAE red. | 50.7% | same | same |
| LOOCV one-tail folds significant | 10/10 | same | same |
| Total samples across 3 datasets | 1,239 | `compute_cross_dataset_significance.py` | three eval JSONs |
| Total questions across 3 datasets | 177 | same | same + dataset JSONs |
| Fixed-effects pooled $d_z$ | $-0.0733$ | same | same |
| Fixed-effects 95% CI | $[-0.13, -0.02]$ | same | same |
| Fixed-effects $p$ (two-tail / one-tail) | $0.010 / 0.005$ | same | same |
| Random-effects pooled $d_z$ | $-0.10$ | same | same |
| Random-effects $p$ (two-tail / one-tail) | $0.078 / 0.039$ | same | same |
| Heterogeneity $I^2$ | $70\%$ | same | same |

### §3.4 Misconception taxonomy reliability

| Claim | Number | Script |
|---|---|---|
| Taxonomy entries | 16 | `misconception_detection/detector.py` (constant) |
| Machine-IRR pilot $\kappa_{\text{micro}}$ | 0.326 | `compute_taxonomy_kappa.py --all` |
| Machine-IRR pilot $\kappa_{\text{macro}}$ | 0.295 | same |
| Per-entry max ($\kappa$) | 0.57 (DS-LINK-03) | same |
| Per-entry min defined ($\kappa$) | 0.00 (DS-SORT-02) | same |

### §4.1 Dataset structure & partition

| Claim | Number | Source |
|---|---|---|
| Mohler subset (KG-aligned) | 120 = 10 × 12 | `datasets/mohler_loader.py` (literal) |
| Dev / test split | 30 / 90 | partition described in §4.1 |
| Question-level clusters | 10 | enumerated in loader |

### §4.3 Cross-dataset & per-SOLO

| Claim | Numbers | Script |
|---|---|---|
| DigiKlausur cluster structure | 17 × 38 = 646 | `compute_cross_dataset_significance.py` |
| Kaggle ASAG cluster structure | 150 × ~3.2 = 473 | same |
| DigiKlausur $d_z$ / $p_{\text{one}}$ | $-0.07$ / $0.024$ | same |
| Kaggle ASAG $d_z$ / $p_{\text{one}}$ | $-0.03$ / $0.170$ | same |
| Mohler Relational $\Delta$MAE | $+0.238$ ($+70\%$) | `compute_solo_breakdown.py` |
| Kaggle ASAG SOLO classifier collapse | 473/473 → Prestructural | same |

### §3.4 Pipeline smoke (Mohler, 5 samples)

| Claim | Result | Script |
|---|---|---|
| Pipeline init + 5 sample scoring | 5/5 ok | `smoke_run_mohler.py` |
| API spend | $0 (cache hits) | same |

---

## Per-claim mapping — Paper 2 (IEEE VIS)

Paper 2's empirical claims about ML grading accuracy share the per-claim
table above (it cites the companion paper's numbers). Paper 2's *user-study*
claims are all design-and-projection — pre-registration and pilot are real
documents, but observed effect sizes are projected:

| Claim | Type | Document |
|---|---|---|
| Pre-registered hypotheses (H1–H5) | Real, locked | `OSF_PREREGISTRATION.md` |
| IRB protocol | Real, ready to submit | `IRB_PROTOCOL.md` |
| Pilot study (5-participant) | Planned, runnable | `PILOT_PROTOCOL.md` + `data/pilot/pilot_template.csv` |
| Holm-Bonferroni correction | Pre-registered | OSF doc §6 |
| Mann-Whitney $U$ primary test | Pre-registered | OSF doc §6 |
| Cohen's $\kappa \geq 0.70$ IRR target | Pre-registered | OSF doc §6 |
| Power analysis $d=0.7$ boundary | Pre-registered | Paper 2 §5.1 |
| Recruitment 3-tier fallback | Pre-registered | Paper 2 §5.1 / OSF doc §8 |
| Mock SUS / CA-rate / SA values | Projection only | Paper 2 §5.2, labelled `[PRE-SUBMISSION PLACEHOLDER]` |

---

## Cached input files (do not modify)

| File | Source | Used by |
|---|---|---|
| `data/mohler_eval_results.json` | Live Gemini pipeline run, pre-session | clustered, cross-dataset, SOLO, κ |
| `data/digiklausur_eval_results.json` | Live Gemini pipeline run, pre-session | cross-dataset, SOLO |
| `data/kaggle_asag_eval_results.json` | Live Gemini pipeline run, pre-session | cross-dataset, SOLO |
| `data/digiklausur_dataset.json` | Pre-session | cluster recovery |
| `data/kaggle_asag_dataset.json` | Pre-session | cluster recovery |
| `data/mohler_lrm_traces.json` | Live LRM run, pre-session | TRM trace examples |
| `datasets/mohler_loader.py` | Hand-curated module | embedded 120-sample subset |
| `misconception_detection/detector.py` | Hand-curated module | 16-entry CS-DS taxonomy |

---

## Output files written by the verification scripts

| File | Producer | Contents |
|---|---|---|
| `data/cross_dataset_significance.json` | `compute_cross_dataset_significance.py` | per-dataset F2/F3 + pooled meta-analysis |
| `data/taxonomy_kappa_results.json` | `compute_taxonomy_kappa.py` | per-entry κ + macro/micro pool |
| `data/solo_breakdown.json` | `compute_solo_breakdown.py` | per-SOLO MAE per dataset |
| `data/smoke_5_results.json` | `smoke_run_mohler.py` | per-sample pipeline output |
| `data/taxonomy_kappa_results.json` | `compute_taxonomy_kappa.py` | per-entry κ |
| `data/session_logs/VALIDATION_GATE_LOG.csv` | `compute_validation_gate.py` | when real sessions exist |

---

## Hidden / external dependencies (declared honestly)

These are NOT reproducible in this repo without external action:

| Item | Real / placeholder | Where it lands |
|---|---|---|
| OSF registration ID | placeholder `[OSF-ID-TBD]` | paste into Paper 2 §5.1 + supplementary |
| IRB protocol number | placeholder `[IRB-PROTOCOL-TBD]` | paste into Paper 2 §5.1 + supplementary |
| Pilot study outcomes (G1–G5) | not run yet | OSF addendum (template in `PILOT_PROTOCOL.md` §8) |
| Main study data | not collected yet | replaces Paper 2 §5.2 mock figures |
| Human-coder $\kappa$ (taxonomy) | not done | future-work item declared in Paper 1 §3.4 limitations |
| Cross-author KG construction | not done | future-work item declared in Paper 1 limitations |

---

## What this guide does NOT cover

- Frontend dashboard (`packages/frontend/`): tested via its own pipeline; not
  exercised in this session.
- LRM trace generation (deepseek-reasoner): used cached traces in
  `data/mohler_lrm_traces.json`.
- Verifier fine-tuning procedure: described in Paper 2 §A.2 but not run
  end-to-end in this session.

---

## Reproducibility checklist (one-glance)

```
[x] 38/38 unit tests pass
[x] compute_clustered_significance.py reproduces Mohler stats
[x] compute_cross_dataset_significance.py reproduces 1,239-sample meta-analysis
[x] compute_solo_breakdown.py reproduces per-SOLO MAE on all three datasets
[x] compute_taxonomy_kappa.py reproduces taxonomy machine-IRR κ
[x] compute_validation_gate.py end-to-end runnable with synthetic sessions
[x] smoke_run_mohler.py exercises the live pipeline (cache hit, $0 spend)
[x] Paper 1 compiles clean (1 × 4.8pt sub-pixel warning only)
[x] Paper 2 compiles clean (zero overfull warnings)
[x] No undefined LaTeX references in either paper
[x] Bibtex resolves on Paper 2 with only 1 cosmetic style warning
```
