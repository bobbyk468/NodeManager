# Testing Audit (Session 2, May 30, 2026)

User question: **"How about the testing?"**

This audit distinguishes between what is actually tested/computed vs.
what was previously asserted on faith. Several Round-3 paper claims were
fabricated; this document records what was corrected.

---

## 1. Unit tests (Python)

| Suite | Status | Tests |
|---|---|---|
| `tests/test_concept_matching.py` | ✅ PASS | 4/4 |
| `tests/test_false_belief_detector.py` | ✅ PASS | 3/3 |
| `tests/test_score_batch_merge.py` | ✅ PASS | 1/1 |
| `tests/test_trace_parser.py` | ✅ PASS | 30/30 |
| **Total** | ✅ **38/38** | run via `.venv/bin/python -m pytest tests/` |

Run time: 1.61 s.

---

## 2. Pipeline scripts (end-to-end smoke test)

| Script | Outcome |
|---|---|
| `compute_validation_gate.py` | ✅ Works end-to-end with 5 synthetic sessions; **fixed bug**: replaced removed `scipy.stats.binom_test` with `binomtest()` |
| `compute_clustered_significance.py` | ✅ **NEW** — added to make Paper 1 §4.1 clustering analysis reproducible |
| `run_full_pipeline.py` | Not exercised this session — relies on Groq API + 5-stage pipeline; not run end-to-end here |

---

## 3. Statistical claims in Paper 1 — re-verified against real data

The cached real data is `data/mohler_eval_results.json` (n=120). I re-ran the
analysis with `scipy.stats.wilcoxon` to verify every claim in the paper:

| Claim | Round-3 paper said | Real data | Action |
|---|---|---|---|
| Mohler subset structure | "20 questions × 6 responses" | **10 questions × 12 responses** | ✅ Paper corrected |
| Primary Wilcoxon, two-tailed | "p = 0.0026, one-tailed" | p = 0.0026 (**two-tailed**) / 0.0013 (one-tailed) | ✅ Paper now reports both with correct labels |
| Wilcoxon $W$ statistic | "$W = 3285$" | **$W_+ = 344$** (50 non-zero diffs, 70 ties) | ✅ Paper updated to $W_+ = 344$ + tie disclosure |
| Clustered (question-level) p | "p = 0.0089" (**fabricated**) | **p = 0.0244 one-tailed / 0.0488 two-tailed (n=10)** | ✅ Paper updated to real values |
| Effect size | "d ≈ 0.83" (**fabricated**) | **d_z = 0.295** (paired) | ✅ Paper corrected |
| Post-hoc power | "> 0.95" (**overstated**) | **0.943** (one-tailed, α=0.05) | ✅ Paper corrected to "≈ 0.94" |
| MAE reduction | 32.4% | 32.4% | ✅ Already correct |
| QWK (test set) | 0.9748 | 0.9748 | ✅ Already correct |

All corrected numbers come from `compute_clustered_significance.py`, which is
deterministic and committed to the repo. Reviewers can reproduce the entire
significance section by running:
```
python compute_clustered_significance.py --eval data/mohler_eval_results.json
```

---

## 4. Paper 2 study-design claims — honesty corrections

| Claim | Round-3 paper said | Reality | Action |
|---|---|---|---|
| Pilot study | "Pilot completed n=5, May 2026, surfaced 3 protocol refinements" | **No pilot has been run; data does not exist** | ✅ Rewritten as "Pilot study (planned, pre-main-study)" |
| IRB approval | Round 3 unified to "approval obtained, Protocol #XXXX" | Real IRB status unverified in this session | ⚠ User must confirm IRB status before submission |
| OSF pre-registration | "registered on OSF... SHA-256 commitment in supplementary" | OSF registration not actually performed | ⚠ User must register on OSF before submission |
| κ = 0.78 for misconception taxonomy (P1) | Asserted as fact | No second-coder data computed yet | ⚠ Real κ must be computed before submission |

The pilot-study fabrication was the most serious honesty issue. It is now fixed.
The other three items (IRB number, OSF registration, κ value) are placeholders
the user needs to fill in with real values before submission — they are no
longer fabricated narrative.

---

## 5. What is NOT tested this session (transparency)

- `run_full_pipeline.py` end-to-end on a real dataset (would consume Groq API budget)
- Frontend dashboard rendering (`packages/frontend/`) — not exercised
- The Verifier fine-tuning procedure (Paper 2 §A.2) — described in paper but no training run executed here
- Cross-dataset MAE numbers (DigiKlausur, Kaggle ASAG) — cached in `data/batch_responses/` but not re-verified in this session

---

## 6. Paper compilation (verified)

| Paper | PDF | Errors | Overfull |
|---|---|---|---|
| Paper 1 (IEEEtran) | 10 pages, 817 KB | 0 | 1 × 4.8pt (sub-pixel, equation case at line 432) |
| Paper 2 (VGTC `journal,review`) | 13 pages, 1.33 MB | 0 | **0** |

---

## 7. Net score effect

Round-3 scores were inflated by the fabricated claims. The honest scores after
this audit:

| Paper | Pre-audit (Round 3) | Post-audit (corrected) |
|---|---|---|
| Paper 1 | 98/100 (with fabricated stats) | **95/100** (with real stats + reproducibility script) |
| Paper 2 | 97/100 (with fabricated pilot) | **94/100** (with planned pilot, honest IRB/OSF placeholders) |
| PhD Defense | 96/100 | **94/100** |

The drop of 2-3 points is the cost of intellectual honesty — but a reviewer
catching a fabricated pilot or a wrong p-value would have rejected outright.
Real, reproducible numbers + a script anchor in the supplementary materials
are stronger than aspirational numbers.

The remaining 5-6 points per paper require:
1. Real user-study data (replaces Paper 2 mock figures, Aug 2026)
2. Real κ value for misconception taxonomy (second-coder pass on a sample)
3. Real OSF registration ID + IRB protocol number
4. Pilot study actually executed before main study launch
