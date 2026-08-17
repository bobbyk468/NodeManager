# Reproducibility Guide — ConceptGrade (Paper 1 + Paper 2)

This file maps every quantitative claim in either paper to the script that
produces it, the cached input it reads, and the exact command to re-run it.
Designed so a reviewer can verify any number in either paper in seconds.

---

## For editors and reviewers — start here

**In one paragraph:** during internal review on 2026-07-28, we discovered that
every quantitative result in an earlier draft of Paper 1 (ConceptGrade) —
including the headline Table 1 numbers — had been computed against a
hand-authored, fully synthetic 120-sample fixture masquerading as the real
Mohler et al. (2011) benchmark, not the real dataset. We found this
ourselves, before any external review flagged it. We re-ran the full
evaluation against the real, verified Mohler dataset (`nkazi/MohlerASAG` on
HuggingFace, 1,262 responses across 46 KG-aligned questions), and every
number in the current paper draft reflects that real-data re-evaluation. The
real effect is smaller and more fragile than the fabricated data implied
(8.2% MAE reduction vs. a fabricated 32.4%; see the "CRITICAL" section
immediately below for the full incident record). Retracted material is kept,
clearly labeled, in supplementary materials for the record — not deleted.

**Open items relevant to Paper 1's submission** (as of this writing; not
resolved, not claimed to be resolved elsewhere in this file):
- `compute_real_fixes.py`'s REAL-1 check (bootstrap CI, non-LLM baselines)
  has not been updated for real data — see the one-glance checklist near
  the end of this file.
- The `kg_weight` sensitivity sweep is explicitly unresolved (see "Offline
  KG-grounding failure-mode analysis" below) — not claimed as solved by any
  offline analysis performed so far.
- Kaggle ASAG's dataset provenance could not be independently verified
  despite a targeted audit; it is labeled provenance-unverified, not
  authenticated, and is kept in the evaluation on that basis (see "Dataset
  Provenance Audit" below).
- The expert knowledge graph and misconception taxonomy were built by a
  single author/research group; the machine-IRR self-check (κ ≈ 0.12 on
  real data, "slight agreement" — see the correction below) is weak even
  as a self-administered lower bound, not independent external validation.

**Second real-data correction, found and fixed 2026-08-17: machine-IRR
taxonomy kappa.** The paper's machine-IRR pilot for the misconception
taxonomy was reported as pooled micro-averaged κ=0.541, macro-averaged
κ=0.465 ("moderate agreement"), cached in `data/taxonomy_kappa_results.json`.
Running the authoritative command from this file's own checklist
(`compute_taxonomy_kappa.py --all`) live reproduced neither number: it gives
micro κ=0.116, macro κ=0.085 ("slight agreement"). We tried every plausible
`--n`/`--k-min` combination against the real 1,262-sample data and none
reproduces 0.541/0.465. Root cause (high confidence, not proven by version
control since this repo has no fine-grained history for these files):
`misconception_detection/detector.py`'s distinctive-phrase fix is dated
2026-06-15; `datasets/mohler_loader.py` was switched to the real,
KG-aligned 1,262-sample data on 2026-07-27, after that fix — the cached
0.541/0.465 was almost certainly computed before the loader switch and
never recomputed afterward, the same failure pattern as the original
Mohler-dataset fabrication, just undiscovered until this pass. **Paper 1
now reports the real, weaker number (κ_micro=0.116, κ_micro=0.085,
"slight agreement") in the Methodology, Limitations, and Conclusion,** in
both `paper/main.tex` and `docs/ConceptGrade_FullPaper.tex`.
`data/taxonomy_kappa_results.json` and `verify_all_paper_claims.py`'s
expected values were both regenerated/updated to match; `verify_all_paper_claims.py`
now passes 378/378 against the corrected numbers. This means the
machine-IRR pilot no longer supports even a "lower bound on human-coder
agreement" framing — it should be read as a taxonomy-authoring limitation,
not partial validation.

**Fixed during the 2026-08-17 publication-readiness pass:** `run_demo.py`
built the live v1.1-expert KG builder (`knowledge_graph/ds_knowledge_graph.py`,
currently 187 relationships) and saved its output directly to
`data/ds_knowledge_graph.json` — the exact path every evaluation script and
Paper 1's reported numbers treat as the FROZEN v1.0-expert snapshot (101
concepts, 138 relationships). Running the demo would have silently
overwritten the frozen snapshot with the wrong KG version. Fixed by
redirecting the demo's output to a separate, clearly-named file
(`data/ds_knowledge_graph_v1.1_demo_DO_NOT_USE_FOR_EVAL.json`); no other
script writes to `data/ds_knowledge_graph.json`, confirmed by a full-repo
grep. The frozen file's `version` field (`"1.0-expert"`) and stats
(101 concepts / 138 relationships) were re-verified intact after the fix.

**Quarantined 2026-08-17:** `data/mohler_eval_results.json` (the fabricated
120-sample fixture) was moved to
`archive/fabricated_fixtures/mohler_eval_results.json`, out of `data/`
where it could be mistaken for a current data file. The 9 scripts that
actively read it (`compute_real_fixes.py`, `compute_real_fixes_v2.py`,
`run_budget_matched_baseline.py`, `compute_clustered_significance.py`,
`validate_c5fix_prompt_fix.py`, `run_validation_budget.py`,
`compute_human_irr_and_per_question.py`, `validate_fix1_mohler_c5fix.py`,
and indirectly `run_lrm_ablation.py`) were updated to the new path (or, for
`run_lrm_ablation.py`, left pointing at the now-empty old path, since its
own fallback logic then correctly loads the real MohlerDataset instead —
confirmed by direct test: it now loads all 1,262 real samples). This also
surfaced a previously-unnoticed bug: `run_lrm_ablation.py`'s
`load_mohler_samples()` *preferred* the fabricated fixture whenever it was
present at `data/mohler_eval_results.json`, silently falling back to real
data only if the fixture was absent — moving the fixture out of `data/`
fixes this for good, not just for this session. `verify_all_paper_claims.py`
still passes (379/379, one check added for a stale Paper 2 kappa citation
caught in the same pass); `compute_solo_breakdown.py` and
`compute_cross_dataset_significance.py` (real data) and
`compute_clustered_significance.py` (legacy, default now points at the
archived fixture) were all re-run end-to-end and reproduce identical
numbers to before the move.

**Note (not yet actioned, flagged for a future pass):** three other
`data/*.json` files with `n=120` were noticed during this quarantine pass
and look like they may also be fabricated-fixture-era caches:
`ablation_component_results.json`, `exp2_final_aggregate.json`,
`gemini_pro_kg_results.json`. Auditing and (if warranted) quarantining
these was out of scope for this pass — see "Don't let scope creep turn a
trim-and-restructure pass into a new experiment cycle" — and is left as an
open item.

This file also documents a second, unrelated incident (the LAG/long-answer
evaluation retraction) that belongs to a separate paper track (Paper 3) and
does not block Paper 1's submission — see "the LAG (long-answer) evaluation
is retracted" below if relevant to that other paper.

Last full verification run referenced in this file: 2026-07-28. Paper-level
citation/table fixes made after that date (see the paper's own revision
history) were citation-accuracy corrections, not data corrections, and do
not change any number reported here.

---

## CRITICAL: the "Mohler dataset" was fabricated; real data now collected (2026-07-28)

**Every quantitative result in this project computed before 2026-07-28 —
Paper 1's Table 1 headline numbers, and the two decisive experiments run
earlier in this same review cycle (call-budget-matched baseline,
question-held-out CV retuning) — was evaluated against a hand-authored,
fully synthetic 120-sample fixture, not the real Mohler et al. (2011)
academic benchmark the paper cites.**

### What was found

`datasets/mohler_loader.py`'s `load_mohler_sample()` — called by every
evaluation script in this project — returned a fabricated array
(`MOHLER_SAMPLE_DATA`, since removed). The module's own docstring said so:
"a sample subset for testing (embedded)" and "synthetic generation for
evaluation pipeline testing." Its score-distribution comment
("targets: 0 (5%), 1 (15%), 2 (25%)...") described *designing* a
plausible-looking distribution, not transcribing real data. No code path
anywhere in the project downloaded or loaded the actual dataset.

### Verification

Confirmed by downloading the real dataset from `nkazi/MohlerASAG` on
HuggingFace (CC-BY-4.0, traceable to Mohler & Mihalcea 2011 ACL-HLT,
"Texas Extended" release) and comparing directly: the real dataset's
first question is "What is the role of a prototype program in problem
solving?", in a completely different format (`<STOP>`-delimited
sentences) from the fabricated fixture's invented Data Structures
questions ("Define a linked list...", "Explain how a stack works...").
No ambiguity — the fixture was never derived from real data.

### The real replacement dataset

The frozen v1.0-expert KG (`data/ds_knowledge_graph.json`) genuinely
covers the real dataset's Data Structures questions in depth (linked
lists, stacks, queues, arrays, trees/BSTs, sorting, recursion — verified
by direct concept-ID lookup). Filtering the real 2,273-record open-ended
set to KG-matching questions yields **46 questions, 1,262 responses**
(`data/mohler_real/mohler_real_kg_aligned.json`; provenance in
`data/mohler_real/PROVENANCE.md`) — far larger and, unlike the fixture,
actually real and citable. No hash-table or BFS/DFS questions exist in
the real dataset (the fabricated fixture's Q5/Q6), so those topics are
absent from the real subset; this is a property of the real data, not a
selection choice.

### Re-evaluation (2026-07-28, 1,262/1,262 samples, zero errors)

Run via `run_real_eval_phaseA_signals.py` (live, per-sample: concept
extraction with 3x self-consistency, offline KG comparison, misconception
+ false-belief detection — ~5,700 calls) then
`run_real_eval_phaseB_batched.py` (batched, ~25 samples/call: C_LLM
baseline, cognitive depth, verifier — ~153 calls). Results:
`data/mohler_real_eval_results.json`; headline stats:
`data/mohler_real_headline_stats.json`.

| Metric | Fabricated data (old, retracted) | Real data (n=1,262) |
|---|---|---|
| C_LLM MAE | 0.3300 (n=120) | 1.2821 |
| C5_fix MAE | 0.2229 (n=120) | 1.1771 |
| MAE reduction | 32.4% | **8.2%** |
| C_LLM r | 0.9709 | 0.7904 |
| C5_fix r | 0.9820 | **0.7841 (worse than C_LLM)** |
| C5_fix QWK | — | 0.5237 (vs C_LLM 0.5005) |

The real effect is roughly 4x smaller than claimed, and C5_fix's
correlation is actually *worse* than the untuned baseline's — both facts
invisible in the fabricated data. Both systems also systematically
under-predict relative to real human graders (human mean 4.24/5 vs.
C_LLM 2.99, C5_fix 3.09) — real course grading is far more lenient than
either LLM grader, another fact the hand-designed fixture's score
distribution masked.

### Impact / what still needs doing

**Done (2026-07-28, this session, offline, zero further API spend):**
- Paper 1's Table 1, Results section, Abstract, Introduction's claim
  list, cross-dataset meta-analysis section + table, per-SOLO breakdown
  table, and Conclusion all now report the real, corrected numbers.
  (The Experiment #1 write-up was initially flagged as unverified
  pending re-run; it has since been re-run on real data — see below —
  and the paper updated accordingly.) Both retracted preliminary figures
  (`fig2_evaluation_results.png`, `fig4_score_analysis.png`) have
  explicit retraction captions rather than being silently left stale.
  Paper compiles clean (18 pages, 0 errors, 0 undefined refs).
- `compute_cross_dataset_significance.py` and `compute_solo_breakdown.py`
  both now load Mohler from the real re-evaluation instead of the
  fabricated fixture; DigiKlausur and Kaggle ASAG paths are untouched
  (unaffected by this incident).
- `verify_all_paper_claims.py` fully reconciled: every Mohler-dependent
  check (dataset structure, headline MAE/r/QWK/RMSE, ties, question-
  clustered/LOOCV, cross-dataset pool, per-SOLO, per-question wins,
  concept-extraction-collapse rate, human IRR) now checks against real
  values, with several checks that hard-coded a rigid
  "10 questions × 12 responses" shape (invalid for the real, variably-
  sized 46-question dataset) rewritten to group by real qid instead.
- **New finding: post-hoc recalibration** (`compute_calibration_analysis.py`,
  `data/calibration_analysis.json`). 5-fold cross-validated monotonic
  recalibration (isotonic + linear, out-of-fold predictions, zero new
  LLM calls) cuts MAE by ~3x for both systems (C_LLM: $1.282\to0.375$,
  $-70.8\%$; C5_fix: $1.177\to0.392$, $-66.7\%$), confirming most raw
  error was fixable scale/bias miscalibration rather than ranking error
  — a genuine, actionable, practically significant finding for
  deployment. It also **inverts the headline comparison**: once
  properly calibrated, C_LLM has significantly lower MAE than C5_fix
  (one-tailed $p=0.017$ isotonic, $p=0.0013$ linear), consistent with
  C5_fix's raw MAE edge being substantially a calibration artifact
  (its raw mean, 3.09, happened to sit closer to the true human mean,
  4.24, than C_LLM's 2.99) rather than better grading judgment — also
  consistent with C_LLM's already-better raw Pearson $r$. Added to
  Paper 1 as a new subsection (`subsec:calibration`) and to the Abstract;
  `verify_all_paper_claims.py` gained 7 new checks.
  **232/232 checks pass.**
- **New finding: offline verifier-weight sweep** (`compute_verifier_weight_sweep.py`,
  `data/verifier_weight_sweep.json`). Tested whether letting the
  deterministic KG-formula score (`pipeline.py`'s `_compute_overall_score()`)
  actually influence the final grade (`verifier_weight<1.0`) — currently
  `verifier_weight=1.0` discards it entirely — helps, using only
  already-collected Phase A/B data (zero new LLM calls; approximates the
  pipeline's true internal `kg_score`, which also blends a separate,
  not-yet-run holistic LLM call at 0.95 weight — disclosed in the
  script). Result: **negative**. MAE degrades monotonically as the
  KG-formula weight increases, from $1.1771$ at $w=1.0$ (current config)
  to $1.9004$ at $w=0.0$ (pure KG-formula, worse than even C\_LLM's
  $1.2821$). The current architecture's choice to let the verifier fully
  override the KG-formula score is empirically the best of the tested
  options, not an oversight — the deterministic formula alone is a weak
  predictor of real human grades.
- **Confirmed with the pipeline's TRUE internal `kg_score`**
  (`compute_holistic_score_batched.py` — 51 batched calls, ~3 min, zero
  errors, cached per-batch in `data/holistic_score_batches/`, combined
  in `data/holistic_score_real.json`; then
  `compute_verifier_weight_sweep_v2.py`,
  `data/verifier_weight_sweep_v2_true_kgscore.json`). This runs the
  pipeline's actual `0.05*KG-formula + 0.95*holistic-LLM-score` blend
  (the holistic scorer being a genuinely new, not-yet-run LLM call type
  distinct from C_LLM and the verifier) instead of the earlier
  approximation. Result: **even more decisively negative**. $w=1.0$
  (current config) remains strictly best across the full sweep; the
  holistic-LLM-only component is surprisingly the *worst* individual
  predictor tested (MAE=2.4003, worse than raw C\_LLM's 1.2821),
  plausibly because its rigid Bloom's-band score clamping is poorly
  calibrated to real (lenient) human grading. This closes off the
  verifier-weight lever as a promising direction — not yet added to
  either paper's text.
- **Experiment #1 (call-budget-matched baseline) re-run on real data**
  (`run_budget_matched_real_batched.py` — 357 batched calls across 7
  independent rounds of ~1,262 samples each, ~21.4 min, zero errors,
  every batch cached in `data/budget_matched_real_batches/`, combined in
  `data/budget_matched_real_results.json`). Unlike the fabricated-data
  version, on real data **budget alone genuinely helps** C\_LLM:
  C\_LLM$\times$7 MAE $=1.2314$ vs.\ single-call C\_LLM's $1.2821$
  ($+4.0\%$, one-tailed $p<0.0001$). **C5\_fix still beats the
  budget-matched baseline**: MAE $=1.1771$ vs.\ $1.2314$ ($+4.4\%$,
  two-tailed $p=0.0053$, one-tailed $p=0.0027$) — a genuinely positive,
  statistically significant response-level result, the first one this
  correction cycle has produced. Question-clustered check (following
  the same convention used throughout this session,
  46 real questions): **not significant** (two-tailed $p=0.4219$,
  one-tailed $p=0.2110$), and C5\_fix wins on only 25/46 questions
  ($54\%$, barely above chance) — the same response-level-vs-question-
  level divergence seen everywhere else in the real-data results. Not
  yet added to either paper's text.
- **Sentence-BERT baselines recomputed on real data**
  (`compute_sentence_bert_baseline.py`, `data/sentence_bert_baseline_real.json`).
  Local embedding inference only, zero LLM API calls. `all-MiniLM-L6-v2`:
  MAE=1.581, RMSE=1.879, r=0.416. `all-mpnet-base-v2`: MAE=1.479,
  RMSE=1.771, r=0.430. Both trail *both* LLM systems by a wide margin
  (C_LLM MAE=1.282, C5_fix MAE=1.177); C5_fix and C_LLM each beat both
  frozen embedding baselines with high significance (all p < 0.0002).
  Confirms the qualitative conclusion the retracted fixture-based numbers
  had also suggested. Added to Paper 1's "Non-LLM neural baselines"
  paragraph; `verify_all_paper_claims.py` gained 6 new checks.
  **241/241 checks pass.**
- **Paper 2** (`docs/paper_phase2_vis2027.tex`) fully reconciled: Abstract,
  Fig. 2 caption / contributions list, dataset description, main
  results table + per-SOLO table, cross-dataset table, bootstrap CIs
  (Mohler bootstrap recomputed offline: 8.2% [5.5%, 10.7%]), Conclusion,
  and the `concepts_only`-ablation cross-reference all now report real
  numbers. The component-ablation table and TRM grounding-density table
  (both require new pipeline/LRM-trace runs, not recomputable offline)
  are retained with explicit "retracted, pending re-verification"
  captions rather than deleted or silently left stale. Compiles clean
  (16 pages, 0 errors, only the same pre-existing cosmetic bibtex
  warning already documented).
- Experiments #1 (call-budget-matched baseline) and #2 (question-held-out
  CV retuning), run earlier in this cycle, were both evaluated against
  the fabricated data. Their qualitative findings (C5_fix survives
  budget-matching; C5_fix's advantage does *not* survive genuine
  question-level holdout) may or may not replicate on real data —
  re-running them requires new live API calls and has not been done, per
  the user's explicit instruction to stop spending API budget once the
  core re-evaluation finished.
- **Real-data 3-condition ablation** (`compute_ablation_three_condition_real.py`,
  `data/ablation_three_condition_real.json`), **zero new API calls**.
  Reconstructs the pipeline's exact pre-verifier `kg_score`
  (`0.05*KG-formula + 0.95*holistic-LLM-score`, same formula as the
  verifier-weight sweep above) per-sample from already-cached component
  scores and compares three conditions: C_LLM (no KG) / `kg_score`
  (KG-grounded, no verifier) / C5_fix (full pipeline). This is *not* an
  independent re-run of the pipeline in new configurations (that would
  still require new LLM calls) — it is exact arithmetic on already-cached
  real per-sample data, disclosed as such in both papers. Result:
  **`kg_score` alone is dramatically worse than C_LLM** (MAE 2.3968 vs.
  1.2821, $-86.9\%$, question-clustered $p<0.0001$, wins only 9/46
  questions); **C5_fix recovers essentially all of this loss and then
  some** via the verifier ($+50.9\%$ MAE improvement from `kg_score` to
  C5_fix, question-clustered $p<0.0001$, wins 41/46 questions). This
  overturns the original fabricated-data ablation's narrative that KG
  grounding (TRM) was the primary driver of accuracy gains — on real
  data, the opposite is true: the verifier's free-form judgment is doing
  essentially all the work, and the KG-grounded score is a net negative
  in isolation, consistent with the verifier-weight sweep's $w=1.0$
  finding above. Added to both papers (Paper 1 §6, Paper 2 §"Component
  Contribution Analysis") as the authoritative real-data ablation
  evidence, replacing the "pending re-verification" placeholder; the
  original fabricated six-condition table is retained in both papers,
  captioned "retracted... superseded," not deleted. `verify_all_paper_claims.py`
  gained 12 new checks in a new "2d" section. **253/255 checks pass**
  (2 pre-existing, unrelated failures — a stale `pipeline.py` root-path
  existence check; the file is at `conceptgrade/pipeline.py`, not
  something this ablation work touched).
- The original **six-condition** component ablation and `concepts_only`
  diagnostic (distinct from the 3-condition ablation above) still require
  new pipeline runs on real data in genuinely new intermediate
  configurations (not offline-recomputable) and remain open future work
  in both papers. (The frozen Sentence-BERT baselines, which needed only
  local embedding inference, have since been recomputed on real data —
  see above.)
- **Paper 1 architecture-description code-accuracy audit, resolved
  (2026-07-28), zero new API calls.** The formula discrepancy flagged
  above was investigated by directly reading `conceptgrade/pipeline.py`.
  Findings: (1) the "Overall Comparison Score" equation
  ($\alpha\,\text{cov}+\beta\,\text{acc}+\gamma\,\text{int}$,
  $\alpha{=}0.5,\beta{=}0.3,\gamma{=}0.2$, formerly `eq:overall`) does
  not correspond to any code path — Layer 2 emits the three raw
  component scores unweighted; they are combined only once, in Score
  Synthesis, with different weights ($0.45/0.35/0.20$). (2) The
  six-term composite equation ($w_1\cdot\text{cos}+\cdots+w_6\cdot\text{comp}$,
  including a TF-IDF cosine term and a "completeness heuristic" term
  that don't exist in the code) has been replaced with the exact
  formula `_compute_overall_score()` implements (Eq.~\eqref{eq:kgformula}:
  knowledge $=0.45$cov$+0.35$acc$+0.20$int, depth $=0.55$blooms$+0.45$solo,
  $s_{\text{kg}}=($knowledge$\times0.60+$depth$\times0.40)\times(1-p_{\text{misc}})$,
  then blended $0.05 s_{\text{kg}} + 0.95 s_{\text{holistic}}$ pre-verifier).
  (3) The "Ensemble Weight Selection" subsection, which claimed a
  grid-search-tuned $(\alpha,\beta,\gamma)=(0.5,0.3,0.2)$ yielding
  QWK$=0.9748$ (a fabricated-data-era number, inconsistent with the real
  QWK$=0.524$ headline), described a tuning procedure for weights that,
  per (1), are never combined that way in code — retracted in full
  rather than patched with plausible-sounding numbers for a nonexistent
  procedure. (4) The previously-unresolved `kg_weight` sensitivity gap
  turned out to be free to close: both endpoints (pure KG-formula, pure
  holistic) and every point in between were already reconstructable from
  cached per-sample data, same as the 3-condition ablation above.
  `compute_kgweight_sensitivity_real.py` sweeps `kg_weight`$\in[0,1]$ for
  the pre-verifier blend and finds MAE decreases monotonically as
  `kg_weight` increases — the pure-KG-formula endpoint ($1.9004$) beats
  the deployed default ($0.05\to2.3968$) significantly (one-tailed
  $p<0.0001$) — but **even the best point on this sweep remains far
  worse than C\_LLM ($1.2821$) or C5\_fix ($1.1771$)**, so this does not
  change the architectural conclusion from the ablation above: no
  `kg_weight` setting makes the pre-verifier score competitive; the
  verifier stage is what makes the system usable. All four fixes are in
  Paper 1 (§Knowledge Graph Comparison, §Score Synthesis, §Sensitivity
  Analysis, §Ensemble Weight Selection); `verify_all_paper_claims.py`
  gained 6 more checks (section "2e"). **260/262 checks pass** (same 2
  pre-existing unrelated `pipeline.py` path-check failures as before).
- **Tau (concept-confidence-filter) sensitivity, deterministic layer
  only, zero new API calls** (`compute_tau_sensitivity_deterministic_real.py`,
  `data/tau_sensitivity_deterministic_real.json`). Investigated whether
  Experiment #2's original intent (how does the confidence threshold
  affect grading quality?) could be partially answered offline before
  spending on the verifier-dependent part. Found: the deterministic
  KG-comparison layer (`graph_comparison/confidence_weighted_comparator.py`'s
  `ConfidenceWeightedComparator.compare()`) makes **zero LLM calls** —
  pure `networkx` graph matching against the frozen KG — so it can be
  re-run offline against Phase A's already-extracted concepts refiltered
  at any $\tau \geq 0.70$ (the extraction floor). Swept
  $\tau\in\{0.70,0.75,...,1.00\}$: MAE of the deterministic KG-formula
  score **increases monotonically** with $\tau$ ($1.9004\to2.0616$) —
  i.e., stricter confidence filtering discards net-helpful concepts, not
  net-harmful ones; $\tau=0.70$ (the deployed default) is empirically
  the best point swept, not an arbitrarily lax choice. The $\tau=0.70$
  endpoint reproduces the independently-computed kg_weight-sweep's
  pure-KG-formula MAE ($1.9004$) exactly, cross-validating that the
  offline reconstruction matches the live code path. **Important scope
  caveat, disclosed in the paper**: this only characterises the
  deterministic pre-verifier layer. Both the holistic-LLM score and the
  verifier score embed $\tau$-filtered concept evidence directly in
  their prompts, so a genuine test of how C5\_fix (the verifier-driven
  final score) responds to $\tau$ still requires new LLM calls for both
  stages at each additional $\tau$ tested — that part of Experiment #2
  remains open and is NOT claimed as resolved by this offline sweep.
  Added to Paper 1's Confidence Filtering paragraph;
  `verify_all_paper_claims.py` gained 6 more checks (section "2f").
  **265/267 checks pass** (same 2 pre-existing unrelated failures).
- **CRITICAL, found and fixed 2026-07-28: an orphaned ~300-line block of
  unlabeled fabricated-data content**, discovered while auditing the
  Verifier data-leakage discussion for internal consistency with the new
  real-data ablation. Two full subsections of Paper 1 --- "Statistical
  Significance" (`\label{subsec:significance}`) and "Confidence Interval
  Analysis" (`\label{subsec:ci_analysis}`), together spanning roughly
  lines 1112-1424 --- still presented the fabricated 120-sample fixture's
  numbers ($r=0.982$, QWK$=0.975$, $32.4\%$/$34.0\%$ MAE reduction, an
  $n=90$/$n=120$ Wilcoxon test, bootstrap CIs, a per-question table) as
  if they were current results, with **no retraction label whatsoever**
  -- unlike every other fabricated-data table/figure in the paper (which
  all carry explicit "Retracted... retained for the record only"
  captions). This block sat *directly between* the correctly-corrected
  real-data "Main Evaluation" subsection (Table~\ref{tab:main_results},
  real $r=0.7841$/QWK$=0.5237$) and the correctly-corrected "Cross-Dataset
  Boundary Characterisation" subsection, so a careful reader would hit
  an internal contradiction (Table 1 says QWK$=0.5237$; three pages
  later the text says QWK$=0.975$) with no explanation. This appears to
  have been missed during the original real-data reconciliation pass
  because attention was on the headline Table 1 / Abstract / ablation
  rather than a systematic per-subsection sweep. **Fixed**: added a
  prominent retraction banner immediately after each subsection's
  `\label`, "Retracted (fabricated-data)" captions on all 4
  affected tables/figures (`tab:significance`, `tab:bootstrap_test`,
  `tab:per_question`, `fig:ci`), and an explicit "End of retracted
  fabricated-data subsections" marker at the boundary with the (correctly
  real-data) Ablation Study section. Content was **not deleted**, per
  the paper's established retraction convention. Also separately fixed
  the "Verifier data-leakage discussion" paragraph (\S\ref{sec:ablation})
  and its earlier duplicate near the Verifier Confidence Weighting
  subsection, both of which had claimed the fabricated-data
  `concepts_only` ablation "directly defuses" the leakage concern --- an
  argument the real-data ablation actually **reverses** (the Verifier,
  the fine-tuned/potentially-leaky component, now accounts for
  essentially all of C5\_fix's accuracy), so leaving that claim
  uncorrected would have had the paper argue against its own new
  finding. `verify_all_paper_claims.py` gained 3 guard checks against
  this specific regression recurring silently.

  The same sweep found **two more unlabeled fabricated-data spots** later
  in the paper: (1) the "Human-rater ceiling" paragraph reported the
  fabricated fixture's implausibly clean inter-rater stats ($r=0.985$,
  QWK$=0.984$, $0$ samples with gap $\geq 1$) as current, even though the
  *real* human-IRR numbers were already computed and verified elsewhere
  in this same reconciliation effort (`verify_all_paper_claims.py`
  section 1, `_r_irr`) — they just hadn't been propagated into this
  paragraph. Recomputed directly from `data/mohler_real/mohler_real_kg_aligned.json`'s
  two grader-score columns: real $r=0.7833$, QWK$=0.7986$, mean
  $|\text{rater}_1-\text{rater}_2|=0.962$, and $545/1{,}262$ ($43.2\%$)
  samples disagree by $\geq 1$ point — a substantially noisier human
  ceiling than the fabricated fixture had concealed. (2) The "Signal-source
  ablation (REAL-2)" sub-ablation — misleadingly named as though it were
  real data — was still the fabricated $n=120$ `concepts_only`/`taxonomy_only`
  result, and its conclusion ("concept-coverage alone slightly *beats*
  the full system") directly contradicts the real 3-condition ablation
  a few paragraphs above it. (3) "Comparison to LLM-Only Approaches"
  opened with the fabricated $r=0.9709\to0.9820$/$32.4\%$ MAE reduction
  as if current; replaced with the real, more mixed picture (MAE and QWK
  improve, but Pearson $r$ is actually *worse* for ConceptGrade,
  $0.7904\to0.7841$). All three fixed with the same retraction-banner
  convention (content retained, not deleted); one edit
  (the Comparison-to-LLM-Only fix) initially introduced an unclosed
  `\textbf{}` brace that broke the LaTeX build — caught immediately by
  the routine post-edit `pdflatex` recompile (which is why every edit in
  this reconciliation effort is followed by a recompile, not just a
  final one) and fixed before proceeding.

  `verify_all_paper_claims.py` gained 8 more checks across these three
  fixes (3 label/content guards + 4 recomputed-from-source-data checks
  for the real IRR numbers + 1 recomputed-from-source-data check
  reusing the existing `_r_irr` variable). **278/280 checks pass**
  (same 2 pre-existing unrelated failures). Paper 1 recompiles clean (20
  pages, 0 errors, 0 undefined references).
- **CRITICAL, found and fixed 2026-07-28, same session: Paper 1 falsely
  claimed the Verifier was fine-tuned on Mohler data.** While writing
  the real-data-leakage discussion above (item 2 of the "kg_score vs
  Verifier" story), it cited the Verifier as "fine-tuned on an augmented
  2,107-instance expansion of the 630-sample full Mohler dataset
  (Paper~2 §A.2)" — treating this as an existing, established fact
  rather than checking it. This claim is **false**: (1) the actual
  implementation (`conceptgrade/verifier.py`, `conceptgrade/lrm_verifier.py`)
  is a prompted DeepSeek-R1/Gemini LLM call at inference time only, with
  no training step and no Mohler-specific training data — confirmed by
  `grep`-ing both files for any fine-tuning/training code (none found);
  (2) `verify_all_paper_claims.py` section 14 had *already*, in an
  earlier session, established this exact fact and added explicit
  checks that Paper 2 must **not** claim Verifier fine-tuning and must
  say "no fine-tuning / inference-only" — checks that were passing the
  whole time, meaning the correct answer was sitting one file-read away;
  (3) the citation "(Paper~2 §A.2)" itself was wrong even on its own
  terms — Paper 2's real §A.2 is "Knowledge Graph Coverage and Quality
  Metrics," unrelated to the Verifier; the actual Verifier section is
  §A.1 ("Verifier Implementation Details"), which correctly says
  "inference-only." This means an entire "data-leakage" framing
  introduced into Paper 1 during this same reconciliation session was
  built on a self-contradiction with already-established, already-checked
  project knowledge — a reminder that a plausible-sounding architectural
  detail should be checked against the code (or against existing
  automated checks) before being used as a premise for a new argument,
  not just carried forward from what a paper draft already says.
  **Fixed**: retracted the fine-tuning claim in both places it appeared
  (the Verifier Confidence Weighting caveat and the Ablation Study
  data-leakage discussion), replaced with the correct inference-only
  description, and kept the part of the finding that *is* real and
  survives the correction — the Verifier's own judgment, not KG
  grounding, drives essentially all of C5\_fix's real-data accuracy;
  this is an architectural finding about where accuracy comes from, not
  a data-leakage finding. `verify_all_paper_claims.py` gained 3 more
  guard checks (one needed a second pass: the first attempt's guard
  string literally appeared inside the correction text's own
  explanatory quote of the retracted claim, a false-positive caught by
  re-running the checker immediately after adding the guard — fixed by
  paraphrasing instead of literally quoting the retracted claim in the
  paper text). **283/285 checks pass** (same 2 pre-existing unrelated
  failures). Paper 1 recompiles clean (20 pages, 0 errors, 0 undefined
  references).
  **Process lesson**: after any large-scale "reconcile fabricated vs.
  real data" pass, do a systematic per-subsection sweep (not just
  headline numbers) before declaring a paper reconciled — isolated
  orphaned blocks, including ones with misleading names like "REAL-2",
  can survive multiple rounds of targeted fixes. Additionally: when
  writing a *new* correction that cites an architectural detail (e.g.
  "the Verifier is fine-tuned"), verify that detail against the code or
  existing checks before using it as a premise, even if it was already
  written elsewhere in the paper — don't assume prior paper text is
  correct just because it's already there.
- **Completed a full section-by-section sweep of Paper 1 (2026-07-28,
  same session), at the user's request ("Lets fix paper-1 first")
  before starting the equivalent sweep on Paper 2.** Beyond the items
  above, found and fixed 6 more spots:
  1. "Improvement Distribution" paragraph (Per-Question Error Analysis)
     — an unlabeled fabricated 120-sample win/loss/tie breakdown, sitting
     right before the correctly-real per-SOLO table in the same
     subsection. Retracted; pointed to the real question-clustered
     win count (27/46) already established elsewhere.
  2. Four paragraphs in the same subsection treated the retracted
     fabricated-data ablation table and figures as an established,
     current finding (e.g. "Concept Coverage removal drives QWK from
     0.721 down to 0.305," "cosine similarity becomes largely
     redundant") — directly contradicting the real 3-condition ablation
     two sections earlier in the same paper. Removed, with a retraction
     note explaining what was removed and why, rather than left standing
     next to a correctly-labeled real finding that says the opposite.
  3. "Grounding Density Analysis" — an entire subsection (TRM
     zero-grounding-frequency table, $n=120$) with no retraction label,
     unlike Paper 2's already-correctly-retracted equivalent table. This
     one genuinely cannot be recomputed offline (needs fresh LRM/TRM
     reasoning traces on real data, confirmed elsewhere as a real
     open item) — labeled retracted/pending, not deleted or silently
     left stale.
  4. "Evaluation scope" (Limitations) literally stated the paper's own
     dataset as "$n=120$ responses across 10 questions, test set
     $n=90$" — describing the *wrong, retracted dataset size* as the
     paper's current evaluation scope, contradicting Table 1's real
     $n=1{,}262$/46-question sample three sections earlier. This is a
     correctness bug, not just a stale statistic. Fixed to state the
     real scope.
  5. "Tuning asymmetry" (Limitations) cited the retracted
     "$32.4\%$/$34.0\%$ MAE reductions" and the retracted six-term
     $(w_1,\ldots,w_6)$ formula as the basis for its confound discussion.
     Updated to cite the real $8.2\%$ MAE reduction and the real
     Eq.~\eqref{eq:kgformula}/\eqref{eq:composite} formula.
  6. The Conclusion's closing sentence said "human IRR remains future
     work" despite this same reconciliation pass having just added real
     human-IRR numbers ($r=0.7833$, QWK$=0.7986$) to the Limitations
     section. Updated to state them.

  Two of the eight new guard checks added for these fixes needed
  rewording after tripping on their own explanatory text (same
  false-positive pattern noted above — quoting a retracted number
  verbatim inside the correction sentence that retracts it satisfies a
  naive substring-absence check); both were caught by re-running
  `verify_all_paper_claims.py` immediately after adding each guard, not
  discovered later. `verify_all_paper_claims.py` gained 8 more checks.
  **293/295 checks pass** (same 2 pre-existing unrelated failures).
  Paper 1 recompiles clean (20 pages, 0 errors, 0 undefined references)
  after every edit in this sweep — each edit was followed by an
  immediate recompile + re-verify, not batched to the end.

  **Paper 1 is now considered fully swept for this class of bug** (an
  unlabeled/incorrect leftover from the fabricated-data era standing
  uncorrected next to correctly-reconciled real content). The equivalent
  sweep has not yet been done on Paper 2 and is the natural next step.
- DigiKlausur and Kaggle ASAG provenance has not been independently
  re-verified the way Mohler was (circumstantial evidence looks
  legitimate — real-looking textbook content, non-round record counts,
  a previously-documented duplicate-record artifact — but unconfirmed).
- **Dataset expansion + C_LLM/C5_fix ensemble, 2026-07-28: promising
  positive result, held out of both papers pending further validation
  (explicit user instruction: "Lets not update the paper untill and
  unless we prove that our model is better than Mohler").**
  Two prior findings this session (the question-clustered significance
  test's low power at $n=46$ questions, and the C_LLM/C5_fix linear
  ensemble beating C5_fix alone on correlation) suggested two concrete,
  combinable fixes. Both were pursued:
  1. **Dataset expansion (real API spend, ~565 calls).** Found 35
     genuinely real, already-downloaded Mohler questions (1,011
     responses) sitting unused in `data/mohler_real/mohler_open_ended_raw.parquet`
     — the original keyword-matcher missed them because their question
     text doesn't literally contain a KG keyword (e.g. "What is a
     leaf?" doesn't say "tree"). Manually identified 4 genuinely
     in-domain questions (109 responses) missed this way:
     `build_mohler_real_extension_subset.py` freezes them to
     `data/mohler_real/mohler_real_kg_extension.json` (does **not**
     modify the original frozen 46-question file, which remains the
     reproducibility anchor for every number in both papers).
     `run_real_eval_phaseA_extension.py` (109 live extraction/misconception/
     false-belief calls) and `run_real_eval_phaseB_extension_batched.py`
     (batched C_LLM/depth/verifier, ~15 calls) graded them, writing
     `data/mohler_real_extension_phaseA_signals.json` and
     `data/mohler_real_extension_eval_results.json`. Notable finding
     mid-run: 2 of the 4 questions (E08.Q06 "infix expression
     evaluation," E10.Q03 "what is a leaf?") were flagged
     `out_of_kg_domain=True` by the pipeline's own domain-match
     heuristic despite being genuinely Data-Structures topics — the
     same vocabulary-literalism failure mode already documented for
     Kaggle ASAG, now shown to occur within Mohler itself. Kept all 109
     responses rather than excluding the flagged ones, consistent with
     how Kaggle's 100%-out-of-domain result was already handled as a
     legitimate finding, not an error to hide.
  2. **Combined-dataset significance** (`compute_combined_extended_significance.py`,
     `data/combined_extended_significance.json`): on the combined 50-question/
     1,371-response set (original 46q/1,262r + extension 4q/109r), the
     question-clustered significance that was marginal at $n=46$
     ($p=0.056$ one-tailed) **crosses the bar**: $p=0.033$ one-tailed,
     wins improve to 30/50 (60%).
  3. **Stacking the ensemble on top** (same script, sweeping
     $w_{\text{cllm}}$): at $w_{\text{cllm}}=0.45$, **every metric
     simultaneously beats C\_LLM** for the first time this session —
     MAE $1.2429$ vs.\ $1.3012$ ($-4.5\%$), Pearson $r=0.7961$ vs.\
     $0.7822$, Spearman $\rho=0.8277$ vs.\ $0.8213$, QWK $0.5149$ vs.\
     $0.4925$, RMSE $1.6103$ vs.\ $1.7412$, question-clustered
     $p_{\text{two}}=0.0433$ / $p_{\text{one}}=0.0217$ (both
     significant, not just one-tailed), and LOOCV one-tailed
     significance holds in all 50/50 leave-one-question-out folds
     (two-tailed: 30/50). This is the first configuration in this
     entire correction cycle where MAE, both correlation measures, and
     question-clustered significance (both tails) all favour
     ConceptGrade at once.
  **UPDATE 2026-07-28, same day: the ensemble finding does NOT survive
  cross-validation, and is retracted as a candidate paper addition.**
  Two of the three validation gaps above were closed immediately
  (`compute_ensemble_cv_and_sensitivity.py`,
  `data/ensemble_cv_and_sensitivity.json`), at the user's explicit
  request ("Lets close them") and with the explicit prior instruction
  not to touch either paper until the model is proven better:
  1. **Cross-validated weight selection**: genuine leave-one-question-out
     CV (select $w_{\text{cllm}}$ by minimizing MAE on the other 49
     questions only, apply to the held-out question, aggregate
     out-of-fold predictions across all 50 folds) picks
     **$w_{\text{cllm}}=0.0$ on every single fold** — i.e., no blending
     at all, pure C5\_fix. The out-of-fold result is therefore
     identical to plain C5\_fix: same MAE, same (still worse-than-baseline)
     Pearson/Spearman correlation, same marginal question-clustered
     significance. MAE is monotonically worse as $w_{\text{cllm}}$
     increases in every sweep run this session; only correlation and
     cluster-significance improve with blending. The earlier
     $w=0.45$ "all metrics beat baseline" result was a point that
     happened to satisfy several different metrics at once on the
     specific data being evaluated — exactly the
     garden-of-forking-paths risk already flagged, now confirmed via a
     principled, single-objective selection rule that a fair procedure
     would not have found that point.
  2. **Sensitivity check** (48-question set excluding the 2 out-of-domain
     extension questions E08.Q06/E10.Q03): identical conclusion, CV
     picks $w=0.0$ on every fold.
  3. Not pursued (would require new API spend for a genuine held-out
     data batch, and is moot now that (1)/(2) already retracted the
     underlying claim).

  **Conclusion: the ensemble idea is retracted; it must not be added to
  either paper.** The honest, validated real-data picture reverts to
  what was already established before this detour: C5\_fix alone gives
  an 8.0–8.2\% MAE reduction over C\_LLM (holds on both the 46- and
  50-question samples), with Pearson/Spearman correlation still worse
  than the baseline, and question-clustered significance marginal
  (46 questions: $p=0.056$ one-tailed, not significant two-tailed; 50
  questions: $p=0.033$ one-tailed, crosses one-tailed only, two-tailed
  $p=0.066$ still not significant). This CV check is itself a genuine
  contribution to record: it demonstrates that a plausible-looking,
  multi-metric-favourable result can fail a principled generalisation
  test, and that doing the check before writing anything up — exactly
  as instructed — caught it.
- **Verifier self-consistency (K=7, temperature=0.7, median-aggregated),
  2026-07-28: the strongest, most robust real-data result of this
  entire correction cycle. Real API spend (357 batched calls on the
  original 46-question set + 35 more on the 4-question extension = 392
  total), NOT yet added to either paper.** After the ensemble idea
  failed CV, this tests a different, previously-untried mechanism: the
  deployed Verifier currently runs ONCE per response at
  temperature=0.0; this instead resamples the Verifier's own holistic
  judgment 7 times independently at temperature=0.7 (identical KG
  evidence each round -- only the verifier's judgment is resampled) and
  aggregates via median, exactly mirroring the already-validated
  `C_LLM x7` budget-matched experiment's design
  (`run_budget_matched_real_batched.py`). Scripts:
  `run_verifier_selfconsistency_real_batched.py` (original 46q),
  `run_verifier_selfconsistency_extension_batched.py` (4q extension),
  `compute_verifier_x7_combined_significance.py` (combined 50q
  analysis). **Unlike the ensemble, this has no tuned hyperparameter --
  K=7 and temperature=0.7 were fixed in advance by copying an
  already-validated design, so there is no grid-search-on-the-same-data
  risk for cross-validation to catch; this is a point-estimate report,
  not a CV-checked one.**

  Results, combined 50-question/1,371-response set (also holds
  independently on the original 46-question set alone):

  | Metric | C\_LLM | C5\_fix (single call) | Verifier $\times$7 |
  |---|---|---|---|
  | MAE | 1.3012 | 1.1969 ($-8.0\%$) | **1.1714 ($-10.0\%$)** |
  | Pearson $r$ | 0.7822 | 0.7789 (worse) | **0.7863 (better)** |
  | Spearman $\rho$ | 0.8213 | 0.8077 | 0.8096 (still worse, gap narrowed) |
  | QWK | 0.4925 | 0.5154 | **0.5264 (better)** |
  | RMSE | 1.7412 | 1.5520 | **1.5173 (better)** |
  | Question-clustered $p$ (two-tailed) | -- | 0.0657 (n.s.) | **0.0297 (significant)** |
  | Question-clustered $p$ (one-tailed) | -- | 0.0329 | **0.0148 (significant)** |
  | LOOCV one-tailed significant folds | -- | 17/46 (orig.\ 46q) | **50/50** |
  | LOOCV two-tailed significant folds | -- | 0/46 (orig.\ 46q) | **50/50** |

  The LOOCV row is the headline: every single leave-one-question-out
  fold reaches significance at both tails, on both the original
  46-question set and the combined 50-question set independently --
  this directly resolves C5\_fix's single biggest documented weakness
  (question-level fragility). Verifier $\times$7 also beats single-call
  C5\_fix directly (response-level $p=0.0004$ one-tailed on the combined
  set), confirming the underlying hypothesis that the single-call
  verifier judgment was genuinely noisy and that averaging helps.

  **Honest remaining caveat**: Spearman rank correlation still trails
  C\_LLM's (gap narrowed from C5\_fix's $-0.0136$ to $-0.0117$ on the
  combined set, but not closed). This is disclosed, not hidden, and
  should be stated alongside the result if/when it is written up.

  **Status: awaiting explicit decision on whether to add this to either
  paper.** Both papers remain untouched as of this entry, per standing
  instruction not to update the paper until the model is proven better
  than the baseline. This result is the first candidate this session
  that plausibly clears that bar on principled (not curve-fit) grounds.
- **Cross-dataset generalisation check + aggregation refinement,
  2026-07-28, same session.** Two follow-ups closed the remaining gaps
  on the Verifier/C5fix self-consistency finding above.

  **(1) Cross-dataset check (real API spend: 182 batched calls on
  DigiKlausur, 105 on Kaggle ASAG deduped = 287 total).** Extended the
  same K=7/temperature=0.7/median design to DigiKlausur (via
  `run_c5fix_selfconsistency_digiklausur_batched.py`, reusing
  DigiKlausur's actual original C5\_fix prompt builder,
  `generate_batch_scoring_prompts.build_c5fix_prompt` -- a different
  code path than Mohler's `conceptgrade/verifier.py`, since that's what
  actually produced DigiKlausur's headline `c5_score`) and to Kaggle
  ASAG (via `run_c5fix_selfconsistency_kaggle_batched.py`, using the
  LLM-as-Judge prompt `build_c5fix_judge_prompt` that actually produced
  Kaggle's headline score, on the deduplicated $n=368$ set matching the
  established headline convention). Result: **robustly generalises to
  DigiKlausur** (MAE $-12.2\%$ vs C\_LLM, cluster $p=0.018$ two-tailed,
  Pearson/QWK both beat baseline, beats single-call C5\_fix directly
  too) but **does NOT generalise to Kaggle ASAG** (MAE $+1.7\%$ only,
  cluster $p=0.078$ two-tailed, not significant; barely beats
  single-call C5\_fix). This is the honest, expected boundary: Kaggle
  ASAG is the dataset with 100\% out-of-KG-domain concept extraction
  (already documented) -- there is no real KG-grounded signal for
  self-consistency to denoise, so averaging noisy copies of "no signal"
  produces no signal. The three-dataset picture is now a coherent,
  falsifiable story (works where the KG has real signal, doesn't where
  it doesn't) rather than a single-dataset result of unknown generality.

  **(2) Aggregation refinement (zero new API calls).** Every self-consistency
  result stores all 7 raw attempts per sample, not just the aggregate,
  so alternative aggregation functions were testable entirely offline
  (`compute_x7_aggregation_comparison.py`). Finding: **mean (or trimmed-mean)
  aggregation strictly dominates median** on Mohler and DigiKlausur --
  better Pearson $r$, better Spearman $\rho$ (gap to baseline nearly
  halved on Mohler: $-0.0117\to-0.0067$), comparable-or-better
  question-clustered significance -- and is no worse on Kaggle ASAG
  (still null, consistent with "no real signal regardless of
  aggregation"). A K-subset check (testing K=3/K=5 slices of the same
  7 already-collected attempts) additionally found K=7's significance is
  not just matched by fewer rounds on Mohler/DigiKlausur (more rounds
  keeps helping there), while on Kaggle the K=3/K=5/K=7 results are
  wildly unstable ($p$ ranging $0.03$ to $0.45$ depending on $K$) --
  further evidence of no real underlying effect there, not sensitivity
  to the wrong choice of $K$.

  **Final reference design: mean aggregation, K=7, temperature=0.7**
  (`compute_x7_mean_final_significance.py`,
  `data/x7_mean_final_significance.json`), full significance suite,
  supersedes the median version:

  | Dataset | MAE red.\ vs C\_LLM | Pearson $r$ (x7-mean vs C\_LLM) | Cluster $p$ (2-tailed) | LOOCV (1-tail / 2-tail) |
  |---|---|---|---|---|
  | Mohler (50q) | $-9.8\%$ | $0.7901$ vs $0.7822$ (better) | $0.026$ | $50/50$ / $50/50$ |
  | DigiKlausur (17q) | $-12.2\%$ | $0.7269$ vs $0.7006$ (better) | $0.017$ | $17/17$ / $17/17$ |
  | Kaggle ASAG (150q, deduped) | $-2.4\%$ | $0.6441$ vs $0.6663$ (still worse) | $0.092$ (n.s.) | $98/150$ / $0/150$ |

  **Status: this is now the most complete, most rigorously checked
  positive finding of the entire correction cycle.** It survived: a
  failed-and-retracted alternative (the C\_LLM/C5\_fix ensemble), a
  cross-validation check (on the ensemble, which killed it -- this
  design was never grid-searched, so had nothing to fail), a
  cross-dataset generalisation test (passed on 2/3, failed honestly on
  the 3rd with a mechanistic explanation), and an aggregation-function
  sensitivity check (mean beats median, found for free).

  **UPDATE 2026-07-28, same session: added to Paper 1.** At the user's
  explicit request, after they separately declined to state the claim
  with "100\% confidence" once it was explained that no statistical
  result ever licenses that framing, and asked instead for the
  strongest \emph{honest} version of the claim in writing. Added: a new
  subsection \S\ref{subsec:selfconsistency} ("Self-Consistency
  Ensembling: A Robust, Cross-Dataset-Validated Improvement") in
  Results, with the full three-dataset table, the LOOCV robustness
  headline, the Kaggle ASAG boundary explanation, the Spearman/$7\times$-cost
  caveats, and the validation-history paragraph explicitly describing
  the retracted ensemble alternative (disclosed as evidence of process,
  not reported as a finding); an Abstract paragraph and a new
  Introduction contribution item (v) stating the same, scoped result;
  and a Conclusion paragraph. `verify_all_paper_claims.py` gained 12
  new checks (section "2g"), all passing. **306/308 checks pass** (same
  2 pre-existing unrelated `pipeline.py` path-check failures as
  throughout this document). Paper 1 recompiles clean (22 pages, 0
  errors, 0 undefined references). Paper 2 was **not** updated in this
  pass and does not yet reflect this finding -- a natural next step if
  wanted.
- **Final confidence audit of Paper 1, 2026-07-28, same session**, at
  the user's explicit request ("I would like to be confident on
  paper-1 then i will move to paper-2"). Rather than re-running already-passing
  checks, did a fresh front-to-back grep sweep for fabricated-fixture
  numbers and phrases *outside* the blocks already known to be labeled
  retracted, on the theory that every previous sweep this session had
  been triggered by working on a specific section and might have missed
  sections not otherwise being edited. Found and fixed **4 more spots**,
  all previously missed:
  1. Related Work claimed the zero-shot baseline "achieves $r=0.971$ on
     the 10-question KG-aligned subset" -- the fabricated fixture's
     number, unlabeled. Fixed to state the real $r=0.790$.
  2. Related Work separately referred to "our $n=90$/$n=120$ KG-aligned
     subset" when introducing Sultan et al.\ (2016) for comparison --
     again presenting the retracted split as current. Fixed to reference
     the real $n=1{,}262$/46-question subset.
  3. **The entire "Dataset and Evaluation Protocol" methods subsection**
     (Experimental Setup, ~160 lines) described the fabricated
     120-sample/10-question fixture's partition protocol ($n=30$/$n=90$
     dev/test split), LOOCV claims (10/10 folds significant), tie
     decomposition, and sample-size/power rationale as the paper's
     current methodology -- with **zero retraction label**, positioned
     *before* the real-data Results section, so a linear reader would
     form an incorrect mental model of the dataset before ever reaching
     the correction. This is the largest single block of unlabeled
     fabricated content found in any audit pass this session. Labeled
     retracted in full (content retained for the record, not deleted),
     with an explicit pointer to \S\ref{sec:results} for the real
     dataset and protocol.
  4. Confirmed the one already-labeled fabricated $r=0.982$/QWK$=0.975$
     figure caption (inside the already-retracted CI Analysis
     subsection) needed no further change.

  `verify_all_paper_claims.py` gained 4 more guard checks.
  **310/312 checks pass** (same 2 pre-existing unrelated failures).
  Paper 1 recompiles clean (22 pages, 0 errors, 0 undefined references).

  **Paper 1 status: high confidence.** Across this entire correction
  cycle, Paper 1 has now been swept for this class of bug (unlabeled
  fabricated-fixture content standing uncorrected next to real-data
  content) at least four separate times, at increasing levels of
  thoroughness, each time by a different triggering question rather
  than a repeat of the same search -- and each pass after the first
  found progressively fewer, smaller issues (an orphaned ~300-line
  block, then 6 more spots, then a false architectural claim, then this
  pass's 4 spots including one large methods subsection). The
  diminishing-but-nonzero hit rate on each pass is itself informative:
  it suggests the paper is converging on fully clean but that a single
  audit pass, however careful, should not be assumed sufficient for a
  document this size and this heavily edited. Recommend treating any
  future edit to Paper 1 as an occasion for one more targeted sweep of
  the surrounding section, not just the lines directly touched.
- **CRITICAL, found and fixed 2026-07-28, same session: the
  self-consistency section's headline robustness claim (LOOCV 50/50
  both tails) does not survive a fair control, and both papers have
  been corrected.** Found via a different kind of check than every prior
  audit in this log: not a search for unlabeled fabricated content, but
  a request to review Paper 1 "as a reviewer," which surfaced that the
  self-consistency comparison (\S\ref{subsec:selfconsistency}) measured
  Verifier$\times7$ against a \emph{single-call} C\_LLM baseline, not an
  equally-resourced one -- an obvious-in-hindsight but previously
  unasked question: does self-consistency alone, with no KG evidence and
  no Verifier, already explain most of the gain?

  **Experiment** (`compute_cllm_x7_vs_verifier_x7_control.py`, **zero
  new API calls** -- reused the 7 independent C\_LLM attempts already
  collected for the call-budget-matched experiment, re-aggregated with
  mean instead of median, compared head-to-head against Verifier$\times7$
  on the identical 46-question Mohler sample): the MAE gap survives
  ($1.151$ vs.\ $1.238$, $+7.0\%$, response-level $p<0.0001$), but
  **question-clustered significance collapses ($p=0.256$ two-tailed,
  vs.\ $p=0.026$--$0.049$ against a single-call baseline) and LOOCV
  robustness collapses entirely (0/46 folds significant at either
  tail, vs.\ the originally-reported 50/50)**. The originally-reported
  "most robust positive result in this paper" claim was an artifact of
  comparing a $7\times$-resourced system against a $1\times$-resourced
  control, not evidence that the \emph{architecture} (KG evidence +
  Verifier) adds question-level-robust value beyond what plain
  self-consistency gives any noisy LLM grader.

  **What was NOT retracted**: the response-level MAE advantage of
  Verifier$\times7$ over a fairly-resourced C\_LLM$\times7$ is real,
  precisely estimated, and highly significant ($p<0.0001$) -- this
  experiment does not show the architecture is worthless, only that its
  demonstrated advantage is currently a response-level claim, not the
  question-level-robust claim originally made.

  **What remains open**: the equivalent fair-control check has not been
  run on DigiKlausur (would need a fresh $\sim$182-batched-call
  C\_LLM$\times7$ run there, since only single-call C\_LLM data exists
  for that dataset) or Kaggle ASAG. Both papers explicitly flag this as
  unverified rather than assuming the DigiKlausur LOOCV$=17/17$ figure
  would also survive the same correction -- it may or may not; we do not
  know yet.

  **Fixed in both papers**: `ConceptGrade_FullPaper.tex`
  (\S\ref{subsec:selfconsistency} rewritten with the correction
  prominently placed at the top of the subsection, not buried;
  Abstract, Introduction contribution (v), and Conclusion all updated
  to state the corrected, more qualified claim) and
  `paper_phase1_short.tex` (the condensed submission-format
  paper, same corrections applied throughout: Abstract, contributions
  list, Results subsection, Conclusion). `verify_all_paper_claims.py`
  gained 11 new checks (section "2h"), including an explicit guard that
  the paper no longer calls self-consistency "the most robust positive
  result" unqualified. **322/324 checks pass** (same 2 pre-existing
  unrelated failures). Both papers recompile clean (long paper: 22
  pages; standard/condensed paper: 5 pages, both 0 errors, 0 undefined
  references).

  **Process note, worth keeping**: this is the second time in this
  session that "ask a fresh, differently-framed question about
  already-reported work" (first the CV check that killed the ensemble
  idea, now a reviewer-perspective audit that caught this) found a real
  problem that a straightforward extension of prior work would not
  have. Neither the original self-consistency experiment design nor any
  of the subsequent aggregation/K-subset/cross-dataset checks would
  have surfaced this on their own -- it took someone asking "what would
  a skeptical reviewer say" specifically. This is worth doing as a
  standing practice before any claim is finalized, not just once at the
  end.
- **DigiKlausur fair-control check completed, 2026-07-28, same session
  -- closes the gap left open above. Real API spend: 182 batched calls
  (78 at K=3 as a cheap first look, then extended to the full K=7 by
  adding 104 more batches to the same cache directory -- batch-level
  caching meant the K=3 batches were reused automatically, not
  re-called).** Scripts:
  `run_cllm_selfconsistency_digiklausur_k3_batched.py` (initial cheap
  check), `run_cllm_selfconsistency_digiklausur_k7_batched.py`
  (completes to K=7 by reusing the K=3 batch cache). Result: **a
  materially different pattern from Mohler, not identical, but still a
  substantial erosion of the original claim**:

  | | Mohler (fair control) | DigiKlausur (fair control) |
  |---|---|---|
  | MAE gap | $+7.0\%$ ($p<0.0001$) | $+6.4\%$ ($p=0.0006$) |
  | Cluster $p$ (2-tailed) | $0.256$ (n.s.) | $0.089$ (n.s.) |
  | Cluster $p$ (1-tailed) | -- | $0.044$ (marginal) |
  | LOOCV 1-tailed | $0/46$ | $5/17$ |
  | LOOCV 2-tailed | $0/46$ | $2/17$ |
  | Pearson $r$ (architecture vs.\ C\_LLM$\times7$) | $0.797$ vs.\ $0.790$ (**holds**) | $0.727$ vs.\ $0.735$ (**reverses**) |

  Unlike Mohler, DigiKlausur's effect does not collapse to exactly
  zero -- it retains some one-tailed signal (LOOCV $5/17$, cluster
  $p=0.044$) -- but it is nowhere near the originally-reported $17/17$,
  and the two-tailed tests (the more conservative, arguably more
  appropriate standard) do not clear $\alpha=0.05$ on either dataset.
  The single most striking new finding is the **correlation reversal on
  DigiKlausur**: under fair control, plain self-consistency on C\_LLM
  alone (no KG evidence, no Verifier) achieves *higher* Pearson
  correlation ($r=0.735$) than the full C5fix$\times7$ architecture
  ($r=0.727$) -- independently recomputed from per-sample data by
  `verify_all_paper_claims.py`, not just read off a log line. On
  Mohler, by contrast, the architecture's correlation edge narrowly
  survives fair control ($0.797$ vs.\ $0.790$). This means the two
  datasets tell a genuinely different story under fair control, not
  just a weaker version of the same story -- worth keeping both numbers
  rather than averaging them into one summary claim.

  Both papers updated with the complete, final two-dataset picture
  (Table~\ref{tab:faircontrol} in each): the self-consistency
  subsection, Abstract, Introduction contribution (v), and Conclusion
  in `ConceptGrade_FullPaper.tex`; the equivalent sections in
  `paper_phase1_short.tex`. `verify_all_paper_claims.py` gained
  14 more checks (section "2i"), including a correlation-reversal check
  independently recomputed from joined per-sample data rather than
  trusted from the run's printed output. **336/338 checks pass** (same
  2 pre-existing unrelated failures). Both papers recompile clean (long
  paper: 23 pages; standard paper: 5 pages, both 0 errors, 0 undefined
  references).

  **No further generalisation gap remains open for this specific
  finding**: the fair-control check has now been run on both datasets
  where the original claim was made. Kaggle ASAG was never claimed to
  benefit from self-consistency in the first place (already null
  against even a single-call baseline), so no fair-control check is
  needed there.

---

## LMM reanalysis integrated into Paper 1 (2026-07-31, zero API calls)

`compute_lmm_reanalysis.py` (built and run earlier this session) fits
`abs_error ~ system + (1 | question_id)` linear mixed-effects models for the
six primary comparisons in this paper, as a response-level-power-preserving
alternative to the cluster-mean paired Wilcoxon test used everywhere else.
Both external reviewers (Gemini and ChatGPT, see
`docs/RESEARCH_QA_SELF_ASSESSMENT.md` responses) independently converged on
recommending this as a priority follow-up. It was computed but explicitly
flagged as "not yet integrated" as of the prior session checkpoint.

**Now integrated**: added as a new subsection,
"Statistical Model Sensitivity: Linear Mixed-Effects Reanalysis"
(`docs/ConceptGrade_FullPaper.tex`, immediately before §Ablation Study), reporting
the full 6-comparison table and an honest discussion of the mixed verdict —
Mohler's three comparisons all strengthen under the LMM (cluster-Wilcoxon
n.s. → LMM $p\le0.0125$ throughout), while the DigiKlausur headline result
(one of only two comparisons that reached cluster-level significance
anywhere in the paper) *loses* significance under the LMM
($p=0.0489\to0.2471$). Explicitly stated: neither test is treated as
unconditionally authoritative; the reanalysis is reported as widening, not
narrowing, the uncertainty band around the paper's already-weaker claims.
16 new independent checks added to `verify_all_paper_claims.py` (section
"2j"), each recomputed from `data/lmm_reanalysis.json` rather than trusted
from the subsection text; all pass. Paper recompiles clean (0 errors, 0
undefined references, 23 pages — reflowed, not lengthened, since the new
subsection displaced trailing whitespace elsewhere).

**Also added** to the condensed `docs/paper_phase1_short.tex`: a
short "Statistical model sensitivity" paragraph in
§Self-Consistency Ensembling stating the same mixed verdict in
space-constrained form (Mohler strengthens, DigiKlausur headline result
loses significance, fair-control unchanged). Compiles clean (0 new errors,
0 undefined references, still 5 pages).

---

## Offline KG-grounding failure-mode analysis (2026-07-31, zero API calls)

Following the ablation finding that the KG-grounded score is dramatically
worse than the baseline in isolation (§"Ablation" above, kg_score MAE=2.397
vs. C_LLM MAE=1.282 on the real 1,262-sample Mohler set), an inductive
(not predetermined-taxonomy) review of the 60 worst |kg_score−human_score|
cases (`sample_kg_failure_cases.py` → `data/kg_failure_case_sample.json`)
surfaced two distinct, mechanistically-explained failure patterns. Both were
diagnosed and offline-validated entirely from cached data — zero new LLM
calls.

### Finding 1 — domain-match tokenization bug (real code bug, fully fixed & validated)

**Root cause**: `_build_question_ontology()` in
`concept_extraction/extractor.py` tokenizes the question via
`question.lower().split()` without stripping trailing punctuation. For a
question like "What is a queue?", the token `"queue?"` never substring-matches
`"queue"` in the KG concept text, so `seed_ids=[]` →
`domain_match_score=0.0` → `StudentConceptGraph.out_of_kg_domain=True`
(threshold `<0.05`) → `ConfidenceWeightedComparator.compare()`'s
OUT_OF_KG_DOMAIN short-circuit returns an all-zero score, *regardless of
extraction quality*.

**Scope**: 106/1,262 real Mohler samples (8.4%), exactly 4 question IDs —
E08.Q01 ("What is a stack?"), E09.Q01/E12.Q06 ("What is a queue?"), E10.Q01
("What is a tree?") — all matching the "What is a `<KG-concept>`?" pattern
predicted by the bug.

**Validation** (`compute_domain_match_bug_fix_validation.py` →
`data/domain_match_bug_fix_validation.json`): reproduced the exact original
tokenization (`domain_match_score_ORIGINAL`) and confirmed it matches all
1,262 cached values (tolerance 5e-4, appropriate for the 4-decimal rounding
`self_consistent_extractor.py` applies when merging 3 self-consistency runs
— first attempt used too-tight a tolerance (1e-6), producing 989 false-alarm
mismatches; investigated by sorting diffs, found all ≈5e-05, i.e. pure
rounding, not a reproduction error — re-ran with the corrected tolerance,
1262/1262 match). Then applied the punctuation fix and re-ran the *real*
`ConfidenceWeightedComparator.compare()` on the already-extracted (unchanged)
concepts for the 106 affected samples:

| Scope | kg_formula MAE before | kg_formula MAE after fix | Change |
|---|---|---|---|
| 106 affected samples | 3.9623 | 1.3821 | **+65.1%**, now *better* than C_LLM's 1.7264 on the same samples |
| Full 1,262-sample dataset | 2.3968 | 2.2763 | **+5.03%** (Wilcoxon one-tailed p<0.0001) |

Pearson r on the full dataset moves from 0.4710 to 0.4521 (slightly worse) —
noted honestly, not cherry-picked; MAE and correlation don't have to move
together, and the samples fixed are a small (8.4%), non-representative slice.

**FIXED in the live source (2026-07-31)**, after external review
(`docs/ALGORITHM_FIX_REVIEW_REQUEST.md`, Gemini + ChatGPT responses).
`_build_question_ontology()` in `concept_extraction/extractor.py` now
tokenizes via `t.strip(string.punctuation)` per whitespace-split token
(Gemini's refined recommendation, adopted over the plain
`re.findall(r"[a-z']+", ...)` originally proposed) — this strips trailing
`?`/`.`/`,` while preserving short CS terms (`map`, `set`, `dag`) and
internal hyphens (`big-o`, `depth-first`) that a blunt regex-extract would
have dropped or split. Validated two ways before merging:

1. **Live regression test** (`verify_domain_match_fix_live.py`, imports the
   actual patched `ConceptExtractor` and calls the real
   `_build_question_ontology()` — not a standalone reproduction) across all
   1,262 cached samples, producing a full confusion matrix of
   `out_of_kg_domain` before vs.\ after (per ChatGPT's review suggestion
   #9): **exactly 106 OUT\_OF\_KG\_DOMAIN → IN\_DOMAIN flips (matches
   Finding 1's originally measured scope exactly), 0 unexpected
   IN\_DOMAIN → OUT\_OF\_KG\_DOMAIN flips, 0 remaining OUT\_OF\_KG\_DOMAIN
   samples in the dataset** (i.e. this bug was the sole cause of every
   out-of-domain misclassification observed in the real Mohler set).
2. **Full unit test suite**: `pytest --ignore=test_extensions.py` (the
   ignored file needs a live `GROQ_API_KEY` and isn't a unit test) —
   **63/63 pass**, no regressions elsewhere in the codebase.

The MAE impact numbers above (106-sample subgroup +65.1%, full-dataset
+5.03%) were already computed by re-running the real
`ConfidenceWeightedComparator.compare()`
(`compute_domain_match_bug_fix_validation.py`) on unchanged extracted
concepts, so they carry over unchanged now that the fix is live — the
comparator itself was not touched by this patch, only the upstream
domain-match gate that decides whether it runs at all.

### Finding 2 — relationship_accuracy=0.0-by-design penalizes correct single-concept answers (design tradeoff, not a bug; estimated, not exactly validated)

**Mechanism**: `_compute_relationship_accuracy()` in
`graph_comparison/comparator.py` (documented "Framework Fix #15,
2026-06-15") deliberately returns `0.0` accuracy when a student extracts zero
relationships, replacing an older "1.0 = vacuously perfect" default that gave
shallow keyword-dump answers a free accuracy credit. Side effect: any
genuinely correct short-fact answer that only needs one concept —
structurally incapable of expressing a relationship — is scored identically
to a keyword dump on this dimension.

**Scope** (`compute_relationship_accuracy_pattern.py` →
`data/relationship_accuracy_pattern.json`, in-domain n=1,156): 246/1,156
(21.3%) samples extract zero relationships; 216 of those (87.8%) have ≤1
extracted concept (structurally non-applicable, not a missed connection);
180/246 (73.2%) are human-graded correct/near-correct (human_score≥4.0). On
that correct-answer subgroup: kg_score MAE=3.044 vs. C_LLM MAE=0.906 — the
single largest MAE gap of any subgroup examined this session.

**Candidate fix, estimated impact** (`compute_relationship_accuracy_fix_estimate.py`
→ `data/relationship_accuracy_fix_estimate.json`): exclude the accuracy
dimension (rather than zeroing it) when ≤1 concept is expected, renormalizing
`pipeline.py`'s `knowledge = cov*0.45 + acc*0.35 + int*0.20` weights over
coverage+integration only. On the 216-sample structurally-non-applicable
subgroup, this is estimated (not exactly recomputed — see caveat below) to
improve kg_formula MAE from 2.688 to ≈2.140, still well behind C_LLM's 1.153
on the same subgroup.

**Caveat, stated explicitly**: this is a bounded estimate of the
knowledge-component effect only. Per-sample Bloom's/SOLO levels and
misconception-penalty values (needed for `pipeline.py`'s full
`kg_formula_score = (knowledge*0.60 + depth*0.40)*(1-misc_penalty)`) are not
present in the cached Phase A signals file, so the projected final-score MAE
assumes `misc_penalty=0` and depth held constant — reasonable for a
human-graded-correct subgroup, but not an exact end-to-end pipeline re-run
like Finding 1's validation. Treat as directional evidence that a fix would
help, not a precise number to cite as-is.

**Refinement discovered during the remaining case review** (cases 41-60 of
the 60-case sample): the "≤1 concept" heuristic used above to identify
structurally-non-applicable cases is a *lower bound*. The 30 "multi-concept
but zero-relationship" cases originally set aside as "real missed-connection
cases" turn out, on inspection, to cluster entirely on comparative /
definitional / enumerative question types — all 30 trace to just 14 distinct
questions, e.g. "What are the similarities between iteration and recursion?"
(7 instances), "What is the main difference between strings declared using
type string versus ...?" (6), "What is the advantage of linked lists over
arrays?" (3+2), "What are the two main functions defined by a queue?" (1,
e.g. case 41: concepts=[enqueue, dequeue, queue], relationship_accuracy=0.0
despite a perfect human_score=5.0 answer "The two main functions are enqueue
and dequeue."). None of these question types have a correct answer that
requires stating a KG-schema typed relationship (USES, CAUSES, etc.) between
the concepts mentioned — comparison/similarity/enumeration isn't the same
thing as the KG's directed relation types, so the extractor legitimately
returns multiple concepts with zero relationships even for a perfect answer.
This means Finding 2's true affected scope is larger than the 216-sample
concept-count-only estimate above; a tighter estimate would need to key off
question *type* (comparative/definitional/enumerative vs. relational), not
just concept count — flagged here as a natural next refinement, not yet
built into a script.

**STATUS (2026-07-31): fix HELD, not merged**, after external review
(`docs/ALGORITHM_FIX_REVIEW_REQUEST.md`) surfaced a more fundamental,
previously-unnoticed issue that makes shipping the narrow fix unsafe as-is
— see **Finding 3** immediately below, discovered specifically because both
external reviewers (Gemini, ChatGPT) independently demanded a
low-quality-answer sanity check before merging Finding 2's fix, and running
that check is what surfaced Finding 3.

### Finding 3 — `concept_coverage` is self-referentially vacuous in production (discovered 2026-07-31 while sanity-checking Finding 2's fix; more foundational than either Finding 1 or 2)

**Mechanism**: `KnowledgeGraphComparator.compare()`
(`graph_comparison/comparator.py`) accepts an optional `expected_concepts`
argument representing the question's gold-standard concept set. When it is
not supplied, the code falls back to
`expected_set = student_graph.concept_ids` — i.e., "expected" defaults to
whatever the student's own answer happened to extract.
**The only production call site**
(`conceptgrade/pipeline.py:476`, `self.comparator.compare(student_graph=...)`)
never supplies `expected_concepts`, so this fallback is active on
**100% of production comparisons**. `_compute_concept_coverage()` then
computes "matched" vs.\ "missing" among `expected_concepts`, which — being
identical to the student's own concept set — always matches completely:
**`concept_coverage=1.0` for any answer that extracts at least one concept,
regardless of whether that concept is actually relevant to the question or
whether the answer is otherwise correct.**

**Discovered via**: the pre-merge sanity check both external reviewers
independently demanded for Finding 2's candidate fix (GPT: "execute this
exact check... verify low-quality answers do not experience artificial
score inflation"; Gemini: same, phrased as a pre-commit checklist item).
Checking human-graded-poor (human_score≤2.0), single-concept,
zero-relationship samples for score inflation under Finding 2's proposed
fix surfaced that 10/21 such samples already have `concept_coverage=1.0`
**before any fix is applied** — the sanity check meant to validate Finding
2 instead surfaced a separate, pre-existing bug in the metric it was
checking.

**Concrete example**: sample `E07.Q05.A00`. Question: "What is the
difference between a circular linked list and a basic linked list?"
Student answer: "They are passed by reference because you want the
function to change the pointer" — entirely off-topic, does not address the
question. Human score: **0.5/5**. The extractor pulls one tangentially-related
concept ("pointer"); because `expected_concepts` was never supplied,
`concept_coverage=1.0` — a "perfect coverage" score on an almost-blank
wrong answer.

**Scope** (full in-domain dataset, n=1,156): 404/1,156 (35.0%) have this
self-referential `concept_coverage=1.0`; most are coincidentally on
genuinely correct answers (so the vacuity is invisible in aggregate), but
18/404 (4.5% of the trivially-1.0 group, 1.6% of the full dataset) are
low-quality answers (human_score≤2.0) receiving undeserved full coverage
credit purely because they extracted at least one — any — concept.

**Why this blocks Finding 2's fix specifically**: Finding 2's candidate fix
removes the `relationship_accuracy` dimension's zeroing for structurally
non-applicable cases, which currently acts as an (unintended) partial
counterweight to Finding 3's vacuous coverage on the same subgroup. Applying
Finding 2's fix on top of Finding 3, unfixed, would *amplify* rather than
correct the problem: on the 10 affected low-quality samples, the knowledge
component would jump from 0.550 to 0.846 (+0.296, ≈+0.9 on the 0–5
kg\_formula scale) — the exact keyword-dump-reward regression both external
reviewers warned about, now empirically confirmed rather than merely
hypothesized.

**Investigation history (2026-07-31, three rounds of external review +
offline experiments, all zero/minimal API cost):** three candidate
non-self-referential `expected_concepts` sources were evaluated and
rejected, per a pre-committed stopping rule (see
`docs/ALGORITHM_FIX_REVIEW_REQUEST_ROUND2/3/4.md` for full review
transcripts):

| Candidate | Source | Why it failed |
|---|---|---|
| `seed_ids` | Question-only keyword match against KG concept text (the same matcher Finding 1 fixed) | Models the question's *topic neighborhood* (10-30 concepts), not what a specific correct answer needs to state (1-3). 100% False Penalty Rate: every human-graded-excellent sample (846/846) scored coverage <0.5. |
| 1-hop expanded subgraph | `seed_ids` + one KG hop (the same set shown to the LLM as extraction context) | Same failure mode, worse: even larger expected set (mean 12.5 concepts), 100% FPR, mean coverage 0.077. |
| Reference-answer extraction | Real `ConceptExtractor.extract()` run on the 42 unique in-domain questions' `reference_answer` text (**42 live API calls, user-approved spend**, `run_reference_answer_extraction.py` → `data/reference_concepts_mohler.json`) | Answer-specific (mean 3.23 concepts/question, much closer to student density) and did fix 72.2% of the 18 known vacuous-low-quality cases with a real correlation gain ($r$ 0.118→0.200), but MAE worsened (+14%), False Penalty Rate worsened (6.5%→25.5%), and — decisively — it did *worse*, not better, on the pre-committed hardest test: cases where C\_LLM (the independent KG-free baseline) is also wrong (MAE 1.066→1.189 on hard cases, 1.243→1.542 on easy cases). Confirmed not an artifact of the 30 empty-reference-concept edge cases (2.6% of samples, "by reference." → 0 extracted concepts): excluding them, the regression persists (MAE 1.080→1.304, FPR 3.9%→23.4%). |

**Stopping rule invoked** (both external reviewers concurred, GPT
explicitly cautioning against over-claiming "coverage is permanently
uncomputable" — the evidence supports "these three automated methods
don't work," not "no automated method could ever work"): no fourth
automated candidate was attempted. Blending candidates was also
considered and rejected by both reviewers and the student as a high risk
of curve-fitting to 42 questions, echoing this project's earlier retracted
ensemble-blend-weight finding (caught by leave-one-question-out
cross-validation, see above).

**What WAS applied to the live source**: `ComparisonResult` gained a
`coverage_validated: bool` field (`graph_comparison/comparator.py`,
propagated through both `KnowledgeGraphComparator.compare()` and the
actually-deployed `ConfidenceWeightedComparator.compare()`,
`graph_comparison/confidence_weighted_comparator.py`) — set `False`
whenever `expected_concepts` isn't supplied (100% of production calls
today), exposed via `to_dict()`'s `scores["coverage_validated"]`. This is
purely diagnostic/informational and does not change any score — it lets
future consumers (dashboards, further analysis) distinguish validated from
unvalidated coverage without re-deriving the distinction each time.

**What was tried and RETRACTED**: `conceptgrade/pipeline.py`'s
`_compute_overall_score()` was changed to exclude `concept_coverage` from
the `knowledge` formula and renormalize onto `{relationship_accuracy,
integration_quality}` whenever `coverage_validated=False`. This is the
architecture both external reviewers converged on (Gemini: "set
$w_{\text{cov}}=0$"). **Offline end-to-end validation against the real,
patched `ConfidenceWeightedComparator` on all 1,156 in-domain real Mohler
samples** (`verify_finding3_fix_live.py`) found it made things
**measurably worse**, not better:

| Metric | before (coverage always trusted) | after (coverage excluded, renormalized) |
|---|---|---|
| Knowledge-component MAE (0-5) | 1.164 | **1.614** (+38.6%) |
| Pearson $r$ | 0.118 | **0.082** |
| False Penalty Rate (human$\ge$4.0) | 9.0% | **32.5%** |

**Root cause of the regression**: `relationship_accuracy` — the dimension
the renormalized formula now leans on more heavily — is *itself* still
broken (the unresolved, held Finding 2: zeroed by design for
structurally-relationship-free correct answers, ~21% of in-domain
samples). Renormalizing coverage's weight onto an already-compromised
dimension made the composite worse, not better. This is the exact
fix-interaction risk flagged (but not yet tested) in round 1's Q4 ("the
two fixes touch overlapping machinery... have not checked whether their
combined effect is additive, sub-additive, or interacts") — now
empirically confirmed as a real, negative interaction, not a hypothetical
one.

**Consistent with this project's standing practice of retracting findings
that fail their own validation** (cf. the ensemble-blend-weight
retraction), the `pipeline.py` formula change was reverted immediately
after this result — `knowledge` still uses the original, unmodified
`cov*0.45 + acc*0.35 + int*0.20` formula. `coverage_validated` remains
live as a diagnostic flag only.

### Round 5 (2026-07-31): the joint fix, and neutral-prior degradation, were also tested and rejected — investigation formally closed

Two further offline tests (`docs/ALGORITHM_FIX_REVIEW_REQUEST_ROUND5.md`),
both zero new API calls, both recomputed from the same cached, real,
unchanged `comparison_result.scores` across all 1,156 in-domain samples:

1. **Joint fix** (Finding 2's narrow ≤1-concept rule + Finding 3's
   coverage exclusion, applied together, renormalizing onto whichever
   dimensions remain active): beats the Finding-3-only fix (MAE
   1.614→1.446, FPR 32.5%→19.7%) but is **still worse than the original,
   bug-riddled baseline on every metric** (baseline MAE 1.164, $r$ 0.118,
   FPR 9.0%).
2. **Neutral-prior degradation** (0.5 instead of 0.0/exclusion when a
   dimension's ground truth is structurally unavailable, avoiding
   renormalization entirely): also worse than baseline in aggregate (MAE
   1.471, $r$ 0.097, FPR 19.6%) — but the first candidate across all five
   rounds to slightly beat baseline specifically on the pre-committed
   hard-case test (MAE 1.050 vs.\ baseline's 1.066), entirely offset by
   getting much worse on easy cases (1.811 vs.\ 1.243).

**Investigation formally closed after this round**, per convergent
external review (Gemini + ChatGPT, round 5). Both agreed: (a) the class of
intervention tested — binary include/exclude of a scoring dimension with
weight renormalization — has now failed in four distinct forms (exclude
coverage alone, exclude both via joint fix, neutral-prior degradation, and
implicitly the original per-finding candidates), which is evidence against
the *mechanism*, not just against specific trigger calibrations; (b) the
ablation's diagnostic value (two real, root-caused, evidenced scoring
defects) stands on its own without a working fix — a negative result
honestly reported, consistent with this project's standing practice of
retracting anything that fails its own validation (cf. the ensemble-blend
retraction, and this round's own retraction of the Finding-3-only fix);
(c) the neutral-prior hard-case fragment should NOT be chased further —
ChatGPT's specific reasoning, adopted here: it fails a decision-relevant
test regardless of its own significance, since a significant hard-case-only
win would still not justify deploying a fix that's worse in aggregate, and
a non-significant one changes nothing — so the analysis "could not alter
the conclusion" and is not worth running.

**On the causal explanation for why every fix underperforms**: Gemini
proposed a specific mechanism ("Bug A pushes +0.45, Bug B pulls −0.35, net
+0.10 accidental regularization"). ChatGPT pushed back, and that pushback
is adopted here as the more defensible framing: the experiments in rounds
1-5 establish *that* the tested fixes consistently underperform the
existing heuristic score, not a specific, uniquely-identified quantitative
mechanism for *why*. "Interacting deficiencies within a heuristic score
whose fixed weights (0.45/0.35/0.20) implicitly assume all three
dimensions carry comparable, independent signal" is the supported
description; a precise "+0.45/−0.35 cancellation" narrative is a plausible
but unproven hypothesis, not a demonstrated fact, and should not be cited
as more than that in any paper draft.

**Final status, all three findings:**

| Finding | Status | What's live in the source |
|---|---|---|
| Finding 1 (tokenization bug) | **Fixed, merged, regression-validated** | `concept_extraction/extractor.py`'s `_build_question_ontology()` |
| Finding 2 (relationship_accuracy=0.0-by-design side effect) | **Diagnosed, documented, NOT fixed** | Unchanged; no live code modification |
| Finding 3 (concept_coverage self-referential vacuity) | **Diagnosed, documented, NOT fixed** (3 automated ground-truth candidates + exclusion/renormalization + neutral-prior all evidence-rejected) | `coverage_validated` diagnostic flag only (`graph_comparison/comparator.py`, `confidence_weighted_comparator.py`); scoring formula unchanged |

One clarification on why the buggy formula is being left in place, phrased
carefully per ChatGPT's caution rather than as an endorsement of its
correctness: the deployed production grade already discards the raw
`kg_formula_score` in favor of the LLM Verifier (blend weight $w=1.0$,
independently cross-validated earlier in this project), so none of this
round's findings change the actual deployed grade. They affect only the
standalone ablation metric that isolates raw KG-grounding performance —
where the honest, now-closed conclusion is: KG-grounding in isolation
underperforms the baseline for two identified, evidenced reasons, and
straightforward repairs to either or both do not improve it under any
tested intervention.

**Net read**: three findings, in decreasing order of confidence and
increasing order of scope. Finding 1 (implementation bug) is fixed, merged,
and regression-validated — recovers part, not most, of the KG-grounded
score's overall gap vs.\ C\_LLM. Finding 2 (scoring-policy side effect) is
correctly diagnosed but its fix is unsafe to merge until Finding 3 is
addressed. Finding 3 (metric vacuity) is the most foundational of the
three — it undermines the validity of `concept_coverage` on 35% of
in-domain samples, though only ~1.6% of the full dataset shows a visibly
bad outcome from it today — but requires a real design decision, not a
quick patch. None of the three closes the full MAE gap on its own,
consistent with the existing paper conclusion that the Verifier — not raw
KG-grounding — remains
the primary source of the architecture's measured gain. **Not yet
integrated into either paper.**

---

## Dataset Provenance Audit (2026-07-31)

Prompted by a professor-style review of the whole project's research
integrity, which flagged (per `docs/RESEARCH_REVIEW_REQUEST.md`, §9) that
"DigiKlausur and Kaggle ASAG provenance were never independently
forensically verified the way the fabricated Mohler fixture was caught and
Mohler's real replacement was verified." Investigated directly rather than
left open, using the same standard applied to Mohler's real replacement
(`data/mohler_real/PROVENANCE.md`). Full external review transcripts in
`docs/DATASET_PROVENANCE_REVIEW_REQUEST.md`.

**Explicitly rejected approach**: using GPT/Gemini to *generate* synthetic
test data ("different expertise levels" answers) as a way to expand or
validate the evaluation data. This would compound rather than resolve any
provenance concern — it doesn't produce real human data, introduces
circularity (LLM-generated content graded by an LLM-based system), and
concentrates rather than removes partiality (the same model families
already used throughout the pipeline would also author the "ground
truth"). Documented here so the reasoning isn't lost: real forensic
verification of existing data, not synthetic data generation, is the
right response to a provenance gap.

### Provenance status, all three datasets

| Dataset | Source reconstructed | Verification method | Status |
|---|---|---|---|
| Mohler (real replacement) | Yes | `data/mohler_real/PROVENANCE.md`; verified against real HuggingFace mirror (`nkazi/MohlerASAG`, CC-BY-4.0) at the time of the original fabrication-incident correction | **Verified** |
| DigiKlausur | Yes | Fetched the actual public source (`raw.githubusercontent.com/DigiKlausur/ASAG-Dataset/master/asag_dataset.csv`, MPL-2.0, [DigiKlausur/ASAG-Dataset](https://github.com/DigiKlausur/ASAG-Dataset)) directly; row 0's question, student answer, and reference answer match the cached local data character-for-character, `grades_round=2` matches cached `human_score_raw=2`. Corroborated locally: `~/Downloads/asag_dataset.csv` (12.4MB, matching header/content) exists on disk with an April 5, 2026 timestamp, the same day as the repo's initial commit. | **Verified** |
| Kaggle ASAG | **No** | Exhausted both web-forensic and local-forensic avenues (below) | **Unverified** |

### Kaggle ASAG: what was tried, exhaustively, and found nothing

**Web forensics**: exact-text search on cached questions ("What is
respiration in plants?", "What is a habitat?") and reference-answer text —
no public verbatim match found. One topically-similar Kaggle dataset found
([mubeenfurqanahmed/automatic-short-answer-grading-dataset](https://www.kaggle.com/datasets/mubeenfurqanahmed/automatic-short-answer-grading-dataset))
is explicitly documented as synthetically generated via ChatGPT/Gemini,
but its stated size (4,000+ records) doesn't match the cached 473, so it
is probably not literally this dataset — this is circumstantial evidence
that synthetic ASAG datasets exist on Kaggle, **not** evidence that this
specific cached data is synthetic; those are different claims and are
kept separate here per external review (both reviewers independently
flagged the risk of conflating them). Checked `nkazi`'s HuggingFace
SciEntsBank mirror (the same curator trusted for the verified Mohler
replacement) — real dataset, but its categorical 5-way label schema
(correct/contradictory/partial/irrelevant/non-domain) doesn't match the
cached data's numeric `human_score` field, and no topic/text match either.

**Local forensics** (git history, shell history, filesystem, per both
reviewers' highest-priority recommendation — project's own chain of
custody is stronger evidence than web search):
- `git log --follow -p --all -- data/kaggle_asag_dataset.json`: the file
  appears already-complete in one large initial commit
  (`3024d89`, 2026-04-05), bundled with many unrelated changes. No earlier
  history.
- `git log --all -p -i -S"kaggle.com"`: **zero matches** — the string
  "kaggle.com" has never appeared in any commit diff across the entire
  repository history. No download command or source URL was ever
  committed.
- `~/.zsh_history`: no `kaggle`/`asag` references — inconclusive rather
  than a clean negative, since the history file's retained range postdates
  the April 5 commit.
- `~/Downloads/`: found `asag_dataset.csv` — but this is the **DigiKlausur**
  artifact (confirmed by content match), downloaded the same day as the
  initial commit. Nothing Kaggle-related found in Downloads or Desktop.
- `research/research_asag_taxonomies.md`: a general ASAG-literature survey
  mentioning a different, non-matching Kaggle-hosted dataset (Hewlett
  Foundation ASAP-SAS, ~2,200 answers, multi-topic) — not a record of
  which specific file became `kaggle_asag_dataset.json`.

**Conclusion: the original acquisition path for `data/kaggle_asag_dataset.json`
could not be reconstructed despite a targeted provenance investigation
across both web and local forensic avenues.** This is not evidence of
fabrication (no positive sign of synthetic origin was found, unlike the
Mohler fixture's docstring self-admission) — it is an absence of evidence
of authenticity. These are different evidentiary states and are not
conflated here.

### Disposition (Option 1 of 2 presented; selected 2026-07-31)

Two options were reviewed externally: (1) keep the dataset, label it
explicitly "provenance unverified," soften downstream claims accordingly,
zero further cost; (2) replace it with a freshly-verified public dataset
(e.g., real SciEntsBank) preserving the same architectural role, at the
cost of re-running live evaluation (new API spend) on entirely new data.
**Option 1 was selected** — no further live API spend, consistent with
this project's general preference for disclosure over quiet
replacement when the correction is cheap (cf. the Mohler retraction, the
fair-control corrections).

**What changes as a result:**
- Kaggle ASAG's provenance is henceforth described as **unverified**, not
  equivalent to Mohler/DigiKlausur's verified status. This document is the
  canonical record; any future paper-integration pass should carry this
  distinction through rather than presenting all three datasets as
  equally provenanced.
- The "architectural domain-boundary" finding for Kaggle ASAG needs to be
  narrated with the following distinction, per external review: **Claim A**
  ("ConceptGrade's concept extraction returns 0% KG matches on this cached
  data") is independently verifiable directly from extraction logs and
  does **not** depend on the data's provenance. **Claim B** ("elementary-
  science student answers in general behave this way") **does** depend on
  provenance and should be described as supporting evidence from a
  provenance-unverified sample, not an externally-validated generalization.
  Any future paper text should keep these two claims separated rather than
  letting the provenance gap silently undermine the (separately supported)
  extraction-level finding.
- Symmetry note, per explicit external agreement: this verification
  standard applies **regardless of whether a dataset's result is positive
  or null**. Kaggle ASAG produced a null/boundary result throughout this
  project; that is not a reason to hold it to a lower provenance bar than
  Mohler, which carried the positive headline findings.

**Not yet done**: integrating this distinction into the paper text itself
(out of scope for this pass, per standing instruction to keep algorithm/
data-integrity work separate from paper writing) and re-labeling Kaggle
ASAG's provenance status in `verify_all_paper_claims.py` or any
paper-facing table.

---

## CRITICAL: the LAG (long-answer) evaluation is retracted — test-set leakage + domain mismatch + unverifiable provenance (2026-07-31)

**The existing "long-answer grading" (LAG) system's headline result —
Pearson r = 0.967 on a 20-sample hand-crafted benchmark
(`data/lag_evaluation_results.json`) — is retracted. It should not be
cited, quoted, or built upon.**

**Retraction rationale, per external GPT review (2026-07-31,
`docs/PAPER3_LONGANSWER_REVIEW_REQUEST.md`) — the three problems found
are NOT treated as equally disqualifying, and provenance is deliberately
kept separate from the other two rather than folded into "this is
fabrication-equivalent":**

- **Test-set leakage → sufficient on its own to retract the performance
  claim.** The verifier prompt was iteratively tuned against this exact
  benchmark, then that same benchmark's score was reported as the result.
  This invalidates r=0.967 as an estimate of generalization regardless of
  where the data came from.
- **Domain mismatch → independently serious, supports the retraction.**
  The claimed contribution is KG-grounded grading, but the deterministic
  KG-comparison layer is structurally inert for 60% of the benchmark —
  substantially weakening any architectural conclusion drawn from it.
- **Missing provenance → does NOT by itself justify retraction.** Per
  this project's own three-tier standard established for Kaggle ASAG
  (Verified / Unverified / Invalid — see "Dataset Provenance Audit"
  below), an unresolved provenance question belongs in **Unverified**,
  not **Invalid**. Treated on its own, missing provenance alone would
  have warranted a caveat, not a retraction. Applying a stricter standard
  here than was applied to Kaggle ASAG would be inconsistent.

### What was found

The LAG pipeline (`conceptgrade/lag_pipeline.py`), its benchmark
(`data/lag_benchmark.json`), and its evaluation script
(`run_lag_evaluation.py`) were all added in a single commit (`714282b`,
2026-03-25) by an earlier session, before the research-integrity audits
that caught the Mohler fixture.

1. **No provenance (Unverified, not by itself disqualifying).**
   `lag_benchmark.json` is a flat JSON list of 20 `{question,
   reference_answer, student_answer, human_score}` records. There is no
   generation script anywhere in git history, no annotator identity, no
   rubric, no disclosure of how `student_answer` text or `human_score`
   labels were produced. The file appears fully-formed in the same commit
   that added the pipeline that scores it.

2. **Domain mismatch — the KG cannot see 60% of the benchmark
   (independently serious).** The 20 samples span 5 topics (4 samples
   each): `binary_search_tree`, `hash_table`, `virtual_memory`,
   `tcp_vs_udp`, `garbage_collection`. Checked directly against
   `data/ds_knowledge_graph.json` (the same 101-concept Data Structures
   graph used everywhere else in this project): only `binary_search_tree`
   and `hash_table` have any matching concept IDs. `virtual_memory`,
   `tcp_vs_udp`, and `garbage_collection` — 12 of the 20 samples — match
   **zero** KG concepts. The deterministic KG-comparison layer, the core
   claimed advantage of ConceptGrade over a plain LLM grader, is
   structurally meaningless for those 12 samples.

3. **Test-set leakage (sufficient on its own).** A same-day follow-up
   commit (`a92d5d4`, "Fix LAG over-estimation bias") shows explicit
   before/after metrics (`Before: Bias=+0.625, MAE=0.625 ... After:
   Bias=+0.350, MAE=0.400`) from directly editing the verifier's prompt
   (adding explicit score anchors) against this exact 20-sample set, then
   wiring the tuned prompt into `run_lag_evaluation.py` as the default.
   The system was calibrated on its test set, then that same test set's
   score was reported as the result — invalidating r=0.967 as an unbiased
   estimate independent of problems (1) and (2).

### Verification

- `git log --all --diff-filter=A -- data/lag_benchmark.json` → one commit,
  no precursor generation script found anywhere in `git log --all
  --pretty=format: --name-only | sort -u`.
- Concept-ID overlap check: loaded `data/ds_knowledge_graph.json`,
  matched each LAG benchmark topic string against all 101 concept IDs —
  `virtual_memory`, `tcp`/`udp`, `garbage_collection` return zero matches;
  `hash_table` and `binary_search_tree` (`bst` → `abstract_data_type`)
  match.
- `git show a92d5d4` — commit message itself states the before/after
  tuning metrics on the same benchmark used for the final reported score.

### Impact / what still needs doing

**Not done yet (this pass is documentation-only, zero API spend):**
- `docs/ConceptGrade_LongAnswer_Extension.md` should get a retraction
  notice on its Section 8 "Expected Impact" table and its Section 12
  comparison table — both already correctly hedge the numbers as
  "(projected)", so the doc is not itself making a false claim, but it
  should now also point at this retraction so a reader doesn't confuse
  "projected" with "later measured and confirmed."
- `data/lag_benchmark.json` / `data/lag_evaluation_results.json` are kept
  in place for the record (not deleted), per this project's established
  convention of retracting-not-deleting.
A new long-answer validation was built from scratch (Paper 3 /
"long-answer paper" track — see `[[project_paper3_longanswer]]` memory),
with: disclosed provenance (author-written, explicitly labeled synthetic,
matching how the DS misconception taxonomy is disclosed as
hand-authored), only KG-covered topics, and a fixed prompt/config decided
*before* looking at results (no post-hoc tuning against the eval set).
Results below.

---

## Paper 3 pilot: long-answer grading (2026-07-31, first honest measurement)

**Replaces** the retracted LAG evaluation above. Per external GPT review
(`docs/PAPER3_LONGANSWER_REVIEW_REQUEST.md`), this pilot is explicitly
framed as **hypothesis-driven stress testing of a predicted failure
mode**, not a representative evaluation — the 4 misconception-containing
samples were deliberately constructed to test whether the design doc's
own predicted weakness ("subtle errors buried in the middle paragraphs...
leading to under-detection," written before any measurement existed)
actually occurs. That is a different, narrower experiment than estimating
how often this happens on real, independently-written long answers, and
the results below should not be read as the latter.

**Scope disclosure (per review):** the same person designed the pipeline
being tested, wrote the 8 answers, and assigned the target scores. This
pilot should be read as **developer-authored functional validation**,
not an estimate of educational grading performance on a representative
population — that coupling is exactly why the numbers below are
reported as descriptive observations, not inferential statistics (see
below).

### Method

- `build_paper3_pilot_set.py` — 8 author-written (not real students, not
  LLM-generated), multi-paragraph answers (71–258 words) spanning 6
  topics, each checked against `data/ds_knowledge_graph.json` for KG
  coverage before inclusion (the retracted set's exact failure point: 3/5
  of its topics had zero KG overlap). 4 samples contain a deliberately
  embedded misconception from the existing taxonomy (DS-TREE-01,
  DS-HASH-01, DS-SORT-01, DS-STACK-01); 4 are clean, spanning shallow to
  excellent. Each sample is tagged with an author-intended score
  (0–5) **before** running the pipeline.
- `run_paper3_pilot.py` — runs all 8 through `LongAnswerPipeline` with a
  config fixed in the script header before any result was seen:
  `model=gemini-2.5-flash, use_sure=True, use_cross_para=True`. The
  verifier prompt is whatever `verifier.py`'s `mode='lag'` branch
  currently contains — i.e., the prompt previously calibrated against the
  now-retracted benchmark, reused as-is on this genuinely new data (not
  re-tuned). Raw output: `data/paper3_longanswer/pilot_run_v1_results.json`.

### Illustrative Pilot Observations (Not Performance Estimates)

**No inferential statistical claims are made from the descriptive values
below.** MAE, bias, and Pearson r are reported only because omitting them
entirely would make the per-sample pattern harder to see, not as
estimates of expected real-world performance — n=8 on
developer-authored, hypothesis-targeted samples cannot support that kind
of claim regardless of how it's phrased.

| id | topic | target | actual | diff | misconception designed? | detected? |
|---|---|---|---|---|---|---|
| recursion_excellent | recursion | 4.75 | 3.96 | −0.79 | no | — |
| queue_good_shallow_depth | queue | 3.25 | 3.46 | +0.21 | no | — |
| linked_list_surface_level | linked_list | 2.00 | 3.68 | **+1.68** | no | — |
| bst_tree_conflation | binary_search_tree | 2.25 | 3.35 | +1.10 | **yes** | **no** |
| hash_table_complexity_misconception | hash_table | 3.25 | 3.21 | −0.04 | **yes** | **no** |
| sorting_quicksort_mergesort_misconception | sorting | 3.00 | 3.88 | +0.88 | **yes** | **no** |
| stack_queue_conflation_longform | stack | 1.25 | 2.40 | +1.15 | **yes** | yes (2 flagged) |
| dynamic_array_excellent | array | 4.75 | 3.44 | **−1.31** | no | — |

**MAE = 0.895, bias = +0.360 (net over-scoring), Pearson r = 0.592**
against author-intended targets (n=8 — too small for a stable r estimate
on its own; reported for completeness, not as a headline claim).

**Misconception recall: 1/4 (25%).** Only the most literal restatement
(`stack_queue_conflation_longform`, which directly says "stacks use FIFO
order," near-identical in phrasing to the already-validated short-answer
case) was caught. The three misconceptions requiring the reader to
connect a claim to a fact stated *elsewhere in the same answer* — BST
ordering claimed for general binary trees, hash tables claimed always
O(1) two paragraphs after correctly explaining collisions, quicksort
claimed always faster with no worst-case mention — were all missed.

**Two independent problems visible in the same 8 samples:**
1. **Excellent long answers are penalized.** Both hand-designed "excellent"
   samples scored well below their intended range (recursion: 3.96 vs
   4.75; dynamic array: 3.44 vs 4.75 — the largest single miss). Both
   answers correctly explain amortized analysis / recursion-vs-iteration
   tradeoffs unprompted, exactly the kind of unprompted depth the
   short-answer system's Bloom's/SOLO layers are designed to reward.
2. **Fluency is rewarded over correctness at length.** The shallow,
   correct-but-thin `linked_list_surface_level` sample (target 2.0, meant
   to score low on depth alone) scored 3.68 — higher than three of the
   four misconception-containing samples. `bst_tree_conflation`, which
   states the mathematically backwards claim that ordering holds for
   *any* binary tree, scored 3.35 — above the honest shallow answer and
   above its own 2.25 target — because the misconception went undetected
   and the answer's fluent use of correct vocabulary (in-order traversal,
   O(log n)) was rewarded regardless.

### Why, mechanistically (consistent with the design doc's own predicted failure modes)

`docs/ConceptGrade_LongAnswer_Extension.md` §2.5 predicted exactly this
before any measurement existed: *"subtle errors buried in the middle
paragraphs may be overshadowed by correct framing in the opening and
closing, leading to under-detection."* All three missed misconceptions in
this pilot are stated in a middle paragraph, immediately preceded or
followed by correct, fluent technical content — the predicted failure
mode, now measured rather than projected.

### What this does and doesn't show

**Claim, stated at the precision the evidence supports (per external
review — "preliminary," "pilot," "evidence," not "demonstrates,"
"proves," or "establishes"):**

> The pilot provides preliminary evidence that distributed
> misconceptions — ones requiring the reader to connect two non-adjacent
> claims — are harder for the current architecture to detect than
> explicit, locally-stated misconceptions.

- **Does show:** on this specific hypothesis-driven stress test,
  `LongAnswerPipeline` as currently implemented missed all 3 designed
  non-adjacent misconceptions while catching the 1 locally-stated one,
  and showed a directional tendency to under-score two deliberately
  excellent answers while over-scoring a fluent-but-wrong one. This is
  consistent with, but does not on its own establish, the predicted
  mechanism generally — it is one reproducible run against one
  small, targeted, developer-authored set.
- **Does not show:** general long-answer performance at scale, prevalence
  of this failure mode on independently-written (non-adversarial) long
  answers, or anything about educational grading performance on a
  representative population (n=8, author-written, one model, one config,
  one run — no repeated sampling, no human inter-rater baseline, no
  independent authorship of the test items). Any future write-up must
  carry these caveats forward rather than generalizing from 8 samples.
- **Publication status:** per external review, a negative result with a
  demonstrated (if preliminary) mechanism is a legitimate, sufficient
  basis for a Paper 3 contribution on its own — attempting a fix is
  valuable future work, not a prerequisite. If a fix is attempted later,
  it must be evaluated on a *new* set, never re-using these same 8
  samples to both tune and report on (the exact mistake being corrected
  here).

---

## Embedded-Figure Audit (2026-07-31): a verification blind spot found and fixed

While adding new figures for the algorithm-investigation and provenance
content (user request), the six pre-existing embedded PNG figures in
`docs/ConceptGrade_FullPaper.tex` were inspected visually for the first time
this session. **This surfaced a real gap**: `verify_all_paper_claims.py`'s
375 checks only `grep` the `.tex` **text** — they have never had any
visibility into embedded image content, so a figure could silently
contradict the (extensively verified) surrounding text indefinitely
without any automated check catching it.

**Audit result**: 3 of 6 figures (`fig2_evaluation_results.png`,
`fig4_score_analysis.png`, `fig10_confidence_intervals.png`) were already
correctly captioned "Retracted ... figure, retained for the record only"
— these are fine, no action needed. **3 were not**:

- **`fig1_architecture.png`** (the paper's main current-system diagram,
  no retraction caveat applicable or present): stated the wrong model
  ("LLM (Llama-3.3-70b)" — the paper's own text and
  `verify_all_paper_claims.py` explicitly confirm the real model is
  `gemini-2.5-flash`, and separately verify the text contains no
  Llama-3.3-70b/Groq mention) and a stale, incorrect Layer-5 formula
  ("0.25×coverage + 0.20×depth + 0.20×SOLO + 0.15×accuracy" vs. the real,
  extensively-verified `knowledge = 0.45cov + 0.35acc + 0.20int`,
  `s_kg = (0.60·knowledge + 0.40·depth)(1-misc)`, deployed Verifier blend
  `w=1.0`). This is not a "retracted-and-labeled" issue like the others
  — it was presented as the current, correct architecture with no caveat
  at all. **Regenerated** (`generate_fig1_architecture_corrected.py`)
  with the real model and formula, same visual style (5-layer box-and-
  arrow diagram) as the original.
- **`fig3_ablation_study.png`** and **`fig9_component_importance.png`**:
  both visualize the same $n=30$ fabricated-fixture ablation as the table
  immediately above them in the paper (which *is* correctly labeled
  "Retracted (fabricated-data) table... retained for the record only"),
  but the retraction label was never carried into the figure captions
  themselves — a reader skimming figures (not reading table captions in
  full) would see these as valid current findings, including the
  now-retracted claim "confirming the primacy of knowledge-aware
  grading." **Fixed**: added matching "Retracted (fabricated-data)
  figure, retained for the record only" captions, consistent with the
  wording already used correctly on `fig10_confidence_intervals.png`.

**Verified after fix**: paper recompiles clean (0 errors, 0 undefined
references, 25 pages); `pdftotext` confirms all 5 fabricated/retracted
figures (`fig2`, `fig3`, `fig4`, `fig9`, `fig10`) now carry a "Retracted"
caption; 63/63 unit tests and 373/375 `verify_all_paper_claims.py` checks
pass (same 2 pre-existing unrelated failures). **Not yet checked**:
`paper_phase2_vis2027.tex`'s embedded figures were not audited this pass
— flagged as a follow-up, same blind spot could exist there.

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

## Master verification command (~10 seconds, $0)

**Read this before running the block below.** Not every script here operates
on the real data. Two of them (`compute_clustered_significance.py`,
`compute_human_irr_and_per_question.py`) still read the pre-2026-07-28
fabricated-fixture file (`data/mohler_eval_results.json`, 120 samples) by
default and were never migrated to the real dataset — their *default*
output (n=120, 32.4% MAE reduction, etc.) is the **retracted** historical
result, reproduced intentionally for the record, not the paper's current
claim. Running them unflagged and comparing their printed numbers against
the paper's real headline (8.2% MAE reduction, n=1,262) will look like a
mismatch; it is not — it's two different, clearly-labeled datasets. The
paper's real-data claims are independently verified by
`verify_all_paper_claims.py`, which reads
`data/mohler_real_eval_results.json` directly and is the authoritative
check. `compute_clustered_significance.py` does support pointing at the
real file via `--eval data/mohler_real_eval_results.json`, but its
fixed-block clustering (`--n-per-question`/`--n-questions`) assumes a
uniform responses-per-question count and cannot reproduce the paper's real,
variably-sized 46-question clustering that way — use
`verify_all_paper_claims.py` for the authoritative real-data
question-clustered numbers instead.

`compute_real_fixes.py` and `compute_real_fixes_v2.py` both currently crash
(`ValueError: Array shapes are incompatible for broadcasting`, inside their
Sentence-BERT / mpnet baseline Wilcoxon comparisons) when run as-is — this
is the same REAL-1/REAL-3 not-yet-updated-for-real-data gap already flagged
above, now confirmed by direct execution rather than only documented. Both
load the real dataset successfully and fail only at the final significance
test, where an array sized for the old n=90 fabricated test-split is
compared against one sized for the real data. Treat their output as
unavailable until fixed; do not rely on either for submission.

```bash
.venv/bin/python -m pytest tests/ -q                          # 63/63 unit tests
.venv/bin/python compute_clustered_significance.py             # RETRACTED historical result (n=120) -- reproduces the record, not the paper's current claim; see note above
.venv/bin/python compute_cross_dataset_significance.py        # Paper 1 §4.3 (Kaggle deduplicated) -- real data
.venv/bin/python compute_solo_breakdown.py                    # Paper 1 §5 -- real data
.venv/bin/python compute_taxonomy_kappa.py --all              # Paper 1 §3.4 -- real data
.venv/bin/python smoke_run_mohler.py                          # pipeline smoke (cache hit)
.venv/bin/python compute_real_fixes.py                        # BROKEN on real data -- crashes in real_3(); see note above
.venv/bin/python compute_real_fixes_v2.py                     # BROKEN on real data -- same crash as compute_real_fixes.py; see note above
.venv/bin/python compute_human_irr_and_per_question.py        # RETRACTED historical result (n=120) -- reproduces the record, not the paper's current claim; see note above
.venv/bin/python recompute_kaggle_dedup_stats.py               # Paper 1 §4.3 (Kaggle N=473 -> 368) -- real data
.venv/bin/python compute_calibration_analysis.py              # Paper 1 subsec:calibration -- real data
.venv/bin/python compute_kgweight_sensitivity_real.py         # Paper 1 §6 kg_weight sweep -- real data
.venv/bin/python compute_lmm_reanalysis.py                    # Paper 1 LMM reanalysis -- real data
.venv/bin/python verify_all_paper_claims.py                   # AUTHORITATIVE: cross-checks 378 paper claims against real cached data
```

The last script (`verify_all_paper_claims.py`) is the **single-shot
integrity check** for BOTH papers: it reproduces 219 separate quantitative
and structural claims against the cached metadata and source files, then
exits non-zero on any mismatch. As of 2026-06-15 this includes an explicit
section validating the primary $n=90$ held-out test-split headline numbers
(C\_LLM/C5\_fix MAE, Pearson $r$, QWK, RMSE, tie count, $d_z$, both
$p$-values) — previously only the Sentence-BERT baseline's sample count was
checked against $n=90$; the Mohler headline metrics were checked only
against the full $n=120$ sample, which silently permitted the exact
Table-1 mislabeling bug (caption said "$n=90$", values were $n=120$) that
an independent review caught. See "Independent-review remediation log"
below.

Errors caught and fixed by this script (cumulative, all sessions) include:
- `Llama-3.3-70b` → `gemini-2.5-flash` baseline naming (6 occurrences, P1)
- MiniLM Pearson r 0.301 → 0.649 (P1 Table 2 + text)
- κ cached file regenerated with wrong default n (n=30 → n=120)
- Taxonomy κ 0.326/0.295 (fair) → 0.541/0.465 (moderate) after a
  construct-validity fix to the two-coder matching method (2026-06-15)
- KG relationship count: paper text vs. live builder vs. frozen
  evaluation-snapshot JSON now explicitly distinguished (138 evaluated /
  187 current; see "KG version disclosure" below)
- Taxonomy κ cached file was regenerated with the wrong default `n` again
  (same failure mode as the n=30→n=120 entry above) at some point after the
  2026-07-27 real-data loader switch, and never re-run with `--all`
  afterward; 0.541/0.465 (moderate) → 0.116/0.085 (slight), corrected
  2026-08-17 — see the full discrepancy record above
- Table 1 caption/values mismatch: caption claimed $n=90$, values were
  $n=120$ (2026-06-15, caught by independent review)
- Cross-dataset pool computed on pre-deduplication Kaggle data (473
  records, 105 duplicates) instead of the corrected 368-unique set
  (2026-06-15)

Paper 2 coverage: shared ML numbers (now $n=1{,}134$ unique / 177
questions / $p=0.0053$ primary $n=90$ test / $I^2=73\%$ / $473\to368$
Kaggle dedup), Verifier-training math (630×3+217=2,107), study design
arithmetic (N=64=2×32, Holm-Bonferroni α₁=0.05/5=0.01), VGTC document
class, supplementary file existence (OSF/IRB/PILOT/VALIDATION_GATE docs),
explicit [TBD] placeholders, and PRE-SUBMISSION PLACEHOLDER labels on
mock figures. This script is the recommended pre-submission gate.

---

## KG version disclosure (read before citing "the KG")

Paper 1 references **two distinct, both-legitimate KG relationship
counts**, and conflating them was a real bug caught by independent
review (see remediation log below):

| Version | Relationships | Role |
|---|---|---|
| v1.0-expert | 138 | The exact snapshot the evaluation numbers (Table 1, §Results) were computed against. Frozen, unmodified, at `data/ds_knowledge_graph.json` (dated 2026-03-25). **Do not regenerate this file** — it is the reproducibility anchor for every reported metric. |
| v1.1-expert | 187 | The current repository state (`knowledge_graph/ds_knowledge_graph.py`, live builder), after a post-evaluation completion pass that wired 15 previously-isolated concepts and added missing operation-pair edges. **Not re-evaluated.** |

Paper 1's KG-construction section (§3.2) explicitly discloses both numbers
and states which one the evaluation numbers reflect. `verify_all_paper_claims.py`
independently checks both the frozen JSON (expects 138) and the live
builder (expects 187) so this distinction cannot silently drift again.

---

## Independent-review remediation log (2026-06-15)

An independent review (external model, adversarial pass) found 5 blocking
issues in the paper as of the prior revision. All were independently
re-verified against raw cached data (not just re-read) before fixing:

1. **Table 1 caption/values mismatch** — caption said "$n=90$ test
   samples," values were the full $n=120$ sample. Fixed: Table 1 now has
   two explicitly-labeled blocks (primary $n=90$ held-out, secondary
   $n=120$ full-sample-for-continuity). Confirmed independently: recomputing
   the $n=90$ split (`test_mask = (i % 12) >= 3` per
   `compute_real_fixes.py` REAL-1) reproduces MAE $0.3706\to0.2444$,
   $p=0.0053$, exactly.
2. **KG version mismatch** — paper said "138 relationships" in 5 places;
   live builder has 187. See "KG version disclosure" above.
3. **Stale pooled cross-dataset statistics** — abstract/intro cited
   $I^2=70\%$ while the table/conclusion (already dedup-corrected) said
   73%. Traced to the root cause: `data/cross_dataset_significance.json`
   predated the Kaggle deduplication fix. Fixed
   `compute_cross_dataset_significance.py`'s data loader to filter through
   `datasets/dataset_dedupe.py`'s index set, regenerated the JSON, and
   propagated the more-precise regenerated numbers ($d_z=-0.071$,
   $p_{\text{two}}=0.018$ fixed-effects; $d_z=-0.10$, $I^2=73\%$,
   $p_{\text{two}}=0.119$ random-effects) to all 7 locations in the paper
   that cite the pool.
4. **Tuning-asymmetry causal overclaim** — several passages (Introduction,
   Methodology, and the Limitations section itself) claimed the
   same-model design "isolates the architectural effect of KG-grounding,"
   which overclaims given C5\_fix's synthesis weights were tuned on a
   dev split and C\_LLM was not. Narrowed throughout: the design isolates
   *model capability* as a confound, not the KG-grounding/tuning-budget
   confound. No tuned baseline was added (would require new API-spend
   experiments); this remains open future work.
5. **`verify_all_paper_claims.py` had 8 of its own latent bugs** — stale
   hardcoded kappa expectations, a check that validated Paper 2's stale
   $\kappa=0.33$ citation as *correct*, and pooled-stat expectations that
   predated the dedup fix. All fixed; the script grew from 176 to 195
   checks (19 new checks explicitly validate the primary $n=90$ headline
   numbers, which had zero coverage before this pass).

A second review round confirmed the above and found 3 further gaps, also
fixed:
- This file (`REPRODUCIBILITY.md`) was stale relative to the corrected
  paper and verifier (this rewrite).
- The verifier didn't check the $n=90$ headline metrics themselves (only
  the Sentence-BERT baseline's $n=90$ sample count) — added 19 new checks.
- Fig. 2's caption claimed "$p<10^{-3}$" immediately after prose
  discussing the primary $p=0.0053$ result, reading as a contradiction;
  the figure is actually a separate, earlier $n=30$ preliminary
  validation. Caption and referring text now make this explicit.
  Conclusion and two Limitations passages still led with/retained the
  un-narrowed causal language from item 4 above; fixed.

A third review round found that Paper 2 (the companion VIS paper) had
never been reconciled with Paper 1's Kaggle-dedup and pooled-stat
corrections, and that Paper 1 itself still had unlabeled leftover
references:
- Paper 2 cited stale $I^2=70\%$ (3 places), $N=1{,}239$ (2 places),
  Kaggle $473/473$, and an unexplained $p=0.348$ that matched neither
  the pre- nor post-dedup value. All reconciled to the authoritative
  post-dedup numbers; `verify_all_paper_claims.py` gained 10 checks that
  assert both presence of the corrected values and absence of the stale
  ones (203 checks total after this round).
- Paper 1 itself had 4 remaining bare "$473/473$" mentions (not caught
  by the round-2 sweep, which focused on Paper 2) and one stale
  random-effects CI `[-0.23, +0.02]` that survived because the
  find-and-replace pass in round 2 missed this specific occurrence.
  Fixed; every remaining "$473/473$" mention is now paired with
  "$368/368$" or "pre-deduplication" within a 150-character window, and
  the check for this is a proximity check, not a bare presence check
  (207 checks total after this round).

A fourth review round moved from internal-consistency checking to
PhD-standard scientific-validity critique and found defects that text
edits alone could only partially address:
- **Confirmed and fixed (verifiable from code/cached data, no new
  experiments needed):** (a) the paper's claim that "only the shared
  concept-extraction call is the LLM call... everything else runs
  offline" was factually false — verified against source
  (`cognitive_depth_classifier.py`, `misconception_detection/detector.py`,
  `conceptgrade/verifier.py`) that Layers 3, 4 (two detectors), and 5 each
  make independent LLM calls, and the evaluated configuration
  (`use_self_consistency=True`, `use_sure_verifier=False` in
  `run_evaluation.py`) issues **7 LLM calls per response for C5\_fix vs.
  1 for C\_LLM**, an inference-compute confound that had never been
  disclosed; (b) the $n=90$ split is response-held-out, not
  question-held-out (every question contributes to both partitions) —
  disclosed explicitly; (c) recomputed the question-clustered Wilcoxon
  and LOOCV restricted to the true $n=90$ primary sample (not previously
  done — the existing LOOCV analysis covered only $n=120$): only **2 of
  10 LOOCV folds remain significant** at $n=90$ (vs. 10/10 at $n=120$),
  and the clustered test itself is only marginal ($p=0.094$ two-tailed).
  This is now reported as the strongest evidence in the paper against
  over-reading the $n=90$ response-level $p=0.0053$; (d) swapped which
  KG version is described as the primary artifact — Table 2 (relationship
  types) now shows the true v1.0-expert (138-relationship, evaluated)
  breakdown, with v1.1-expert (187, current, unevaluated) explicitly
  demoted to a secondary disclosure; (e) removed residual
  causal-overclaim language ("KG-grounded scoring outperforms...") from
  the Contribution-framing paragraph and added the missing random-effects
  null result and `concepts_only`-beats-full-system caveat to the
  Conclusion, which had previously stated only the more favorable
  fixed-effects/full-ablation framing. `verify_all_paper_claims.py` grew
  to 219 checks.
- **Not fixed — require new experiments, not text edits, and are an
  open decision for the paper's author:** (a) question-held-out
  cross-validation with retuning inside each fold (the current $n=90$
  split cannot answer this even with more analysis — it needs a
  redesigned tuning protocol and new predictions); (b) a tuned,
  call-budget-matched LLM baseline (e.g., C\_LLM given 7 independent
  samples with majority voting, to match C5\_fix's inference budget);
  (c) human validation of misconception labels, Bloom's/SOLO
  classifications, and remediation-hint usefulness — currently zero
  human evaluation exists for any diagnostic output, only
  machine-vs-machine "IRR"; (d) controlled domain/KG-matching
  experiments across more than one KG, to establish vocabulary
  specificity as a causal boundary rather than an observed correlation
  across three simultaneously-varying datasets. The paper's substantive
  scientific claim after this round is intentionally narrow:
  *"under favorable, question-overlapping, KG-aligned conditions, a
  tuned, higher-inference-budget concept-coverage system improves grades
  relative to an untuned, single-call, direct-prompt LLM baseline."*
  This is what the text now actually supports; a broader claim about the
  five-layer framework, KG-grounding in isolation, or a causal domain
  boundary is not yet supported and should not be inferred from the
  title or framing.

**2026-07-27 — Experiment #1 of the round-4 "not fixed" list executed
(call-budget-matched baseline)**, via `run_budget_matched_baseline.py
--live`: 630 genuinely independent `gemini-2.5-flash` API calls (90
samples from the same $n=90$ test split as section 2b $\times$ 7
independently-sampled attempts each, temperature $=0.7$), aggregated by
median, directly matching C5\_fix's 7-call inference budget. Two bugs
were found and fixed in the script before the result could be trusted:
(a) it paired each response with the wrong cached human/C\_LLM/C5\_fix
score, because the loader (`datasets/mohler_loader.py`) and
`data/mohler_eval_results.json` order each question's 12 responses in
opposite directions (descending vs. ascending score) — naive positional
zip silently cross-wired every pairing; (b) more seriously, the script's
`test_mask = (i % 12) >= 3` was applied to the *loader's* order instead
of the *cache's* order, which selects a $\sim$33%-different set of 90
responses than the paper's actual headline split (it dropped the 3
*highest*-scoring responses/question as train instead of the 3 *lowest*).
Both fixed in `_build_test_split_samples()`, which now reproduces
`verify_all_paper_claims.py`'s canonical n=90 split exactly (confirmed:
cached C\_LLM/C5\_fix MAE/r from the corrected script match the paper's
Table 1 numbers to 4 decimal places before any new API spend). Result:
C\_LLM$\times$7 achieves MAE $=0.3972$ ($r=0.9541$) — no better than,
and numerically slightly worse than, single-call C\_LLM (MAE $=0.3706$;
one-tailed $p=0.7457$, budget alone does not help); C5\_fix still beats
the budget-matched baseline by $38.5\%$ MAE (two-tailed $p=0.0005$,
one-tailed $p=0.0003$) — a larger, more significant margin than against
the single-call baseline. `verify_all_paper_claims.py` gained 13 checks
(section "2c"), recomputing MAE/r/p directly from
`data/budget_matched_baseline_results.json`'s per-sample data (232
checks total). Paper 1's "Compute/inference asymmetry," "Contribution
framing," Conclusion, and the Results-section correction paragraph were
updated to report this measured result instead of listing it as
unaddressed future work. The remaining three round-4 items — (b)
question-held-out CV with in-fold retuning, (c) human validation of
diagnostic labels, (d) controlled multi-KG domain matching — are still
open.

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

If the commands in the Master verification command block above succeed,
every cited statistic in the ConceptGrade papers is verified against the
cached real data.

---

## Per-claim mapping — Paper 1 (NLP/EdAI)

### Primary headline numbers: Mohler held-out test split ($n=90$)

This is the methodologically primary comparison (Table 1, top block).
Split: stratified, 9 responses/question (indices `i % 12 >= 3` within each
12-sample question block), never used for weight/threshold tuning.

| Claim in paper | Number | Script | Cached input |
|---|---|---|---|
| MAE C\_LLM → C5\_fix (Mohler test) | 0.3706 → 0.2444 (34.0%) | `compute_real_fixes.py` REAL-1, `verify_all_paper_claims.py` §2b | `data/mohler_eval_results.json` |
| Pearson $r$ C\_LLM / C5\_fix (test) | 0.9553 / 0.9808 | `verify_all_paper_claims.py` §2b | same |
| QWK C\_LLM / C5\_fix (test) | 0.9405 / 0.9700 | same | same |
| RMSE C\_LLM / C5\_fix (test) | 0.5077 / 0.3536 | same | same |
| Ties / non-tied (test) | 47 / 43 | same | same |
| Wilcoxon two-tailed (test) | $p = 0.0053$ | same | same |
| Wilcoxon one-tailed (test) | $p = 0.0027$ | same | same |
| Paired Cohen's $d_z$ (test) | $-0.32$ | same | same |

### Secondary headline numbers: full KG-aligned sample ($n=120$)

Reported for continuity with per-question and component-ablation analyses
elsewhere in the paper that use the full sample (includes the 30-response
development subset used to tune synthesis weights).

| Claim in paper | Number | Script | Cached input |
|---|---|---|---|
| MAE C\_LLM → C5\_fix (Mohler, full) | 0.330 → 0.223 (32.4%) | `compute_clustered_significance.py` | `data/mohler_eval_results.json` |
| Wilcoxon $W_+$ (Mohler, full) | 344 | same | same |
| Wilcoxon two-tailed (full) | $p = 0.0026$ | same | same |
| Wilcoxon one-tailed (full) | $p = 0.0013$ | same | same |
| Paired Cohen's $d_z$ (full) | $-0.295$ | same | same |
| Post-hoc power (full, $\alpha=0.05$, one-tail) | $0.943$ | same | same |
| Non-tied subset Mohler MAE red. | 50.7% | same | same |
| LOOCV one-tail folds significant | 10/10 | same | same |

### Cross-dataset meta-analysis

| Claim in paper | Number | Script | Cached input |
|---|---|---|---|
| Total unique samples across 3 datasets | 1,134 | `compute_cross_dataset_significance.py` | three eval JSONs, Kaggle deduplicated |
| Total questions across 3 datasets | 177 | same | same + dataset JSONs |
| Fixed-effects pooled $d_z$ | $-0.071$ | same | same |
| Fixed-effects 95% CI | $[-0.13, -0.01]$ | same | same |
| Fixed-effects $p$ (two-tail / one-tail) | $0.018 / 0.009$ | same | same |
| Random-effects pooled $d_z$ | $-0.10$ | same | same |
| Random-effects 95% CI | $[-0.22, +0.03]$ | same | same |
| Random-effects $p$ (two-tail / one-tail) | $0.119 / 0.059$ | same | same |
| Heterogeneity $I^2$ | $73\%$ | same | same |

### §3.4 Misconception taxonomy reliability

| Claim | Number | Script |
|---|---|---|
| Taxonomy entries | 16 | `misconception_detection/detector.py` (constant) |
| Machine-IRR pilot $\kappa_{\text{micro}}$ | 0.116 (real, corrected 2026-08-17) | `compute_taxonomy_kappa.py --all` |
| Machine-IRR pilot $\kappa_{\text{macro}}$ | 0.085 (real, corrected 2026-08-17) | same |
| Per-entry max ($\kappa$) | 1.00 (DS-HASH-01, DS-TREE-03) | same |
| Per-entry substantial ($\kappa$) | 0.66 (DS-LINK-03) | same |

Values above reflect the 2026-06-15 distinctive-phrase construct-validity
fix (both coders now additionally require a matched distinctive phrase,
not just concept/lexical overlap). Prior release: $\kappa_{\text{micro}}=0.326$,
$\kappa_{\text{macro}}=0.295$ (fair agreement) — superseded, do not cite.

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
| Kaggle ASAG cluster structure (deduplicated) | 150 × ~2.5 = 368 | same (was 473 pre-dedup, 105 duplicates removed) |
| DigiKlausur $d_z$ / $p_{\text{one}}$ | $-0.07$ / $0.024$ | same |
| Kaggle ASAG $d_z$ / $p_{\text{one}}$ | $-0.01$ / $0.351$ | same (was $-0.03$/$0.170$ pre-dedup) |
| Mohler Relational $\Delta$MAE | $+0.238$ ($+70\%$) | `compute_solo_breakdown.py` |
| Kaggle ASAG SOLO classifier (original run) | 473/473 → Prestructural | same; Framework Fix #8/#26 (2026-06-15) corrected the downstream cause — an OUT\_OF\_KG-domain signal was not yet threaded through the SOLO classifier, causing it to floor to Prestructural for every out-of-domain sample regardless of answer quality. The pipeline now explicitly abstains rather than floors. |

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
| `data/ds_knowledge_graph.json` | Frozen at evaluation time (2026-03-25) | the v1.0-expert (138-relationship) KG snapshot every reported metric was computed against — **do not regenerate**; see "KG version disclosure" |
| `datasets/dataset_dedupe.py` | Hand-curated module | Kaggle ASAG deduplication (473 → 368); used by `compute_cross_dataset_significance.py` |

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
[x] 63/63 unit tests pass
[x] compute_clustered_significance.py reproduces Mohler full-sample (n=120) stats
[ ] compute_real_fixes.py REAL-1 (bootstrap CI, non-LLM baselines) NOT yet updated for
    the real Mohler data / has not been re-run -- see "Still open" above; the
    n=90 held-out split it references no longer applies to real data
[x] compute_cross_dataset_significance.py reproduces 2,276-unique-sample meta-analysis
    (real Mohler n=1,262 + DigiKlausur + Kaggle ASAG deduplicated: 473 -> 368)
[x] compute_solo_breakdown.py reproduces per-SOLO MAE on all three datasets
[x] compute_taxonomy_kappa.py --all reproduces taxonomy machine-IRR kappa (0.116/0.085, real, corrected 2026-08-17)
[x] compute_validation_gate.py end-to-end runnable with synthetic sessions
[x] smoke_run_mohler.py exercises the live pipeline (cache hit, $0 spend)
[x] verify_all_paper_claims.py: 352/354 claims pass (2 pre-existing, unrelated
    failures -- stale pipeline.py root-path check, file is actually at
    conceptgrade/pipeline.py; reconciled to real Mohler data 2026-07-28 across
    BOTH papers plus the real 3-condition ablation, see "CRITICAL" section above)
[x] run_budget_matched_baseline.py --live: 630/630 live Gemini calls captured,
    checkpointed in data/budget_matched_baseline_live_raw.json
[x] Paper 1 compiles clean (0 errors, 0 overfull boxes, 0 undefined references)
[x] Paper 2 compiles clean (zero overfull warnings)
[x] Bibtex resolves on Paper 2 with only 1 cosmetic style warning
```

Last full verification run: 2026-07-28, following four rounds of
independent adversarial review (see remediation log above), the
round-4 call-budget-matched-baseline experiment, and the fabricated-Mohler-dataset
discovery/correction across both papers (see "CRITICAL" section at the
top of this file). All numbers in this file were re-derived from raw
cached data during that pass, not copied from the paper.
