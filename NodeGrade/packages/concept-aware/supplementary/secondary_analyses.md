# Secondary Analyses (relocated from `paper/main.tex` for length, 2026-08-17)

This file holds real, non-retracted secondary/robustness analyses that were
moved out of the main paper body during the length-reduction pass (per the
publication-readiness checklist, Task 9/15) to bring `paper/main.tex` toward
its 6,000-8,000 word journal target. Unlike `retracted_analysis.md`, nothing
here is retracted or fabricated-data-derived — it is real analysis, kept
here as full supporting detail behind a short pointer in the main text.

---

## -1. Diagnostic Failure Analysis: Full Five-Candidate-Repair Detail

*(Originally the full text of Table `tab:diagnostic_candidates` in
`\subsection{Diagnostic Failure Analysis: KG-Grounding Scoring Defects and
Rejected Repairs}`, Ablation Study section. The main paper keeps the two
root-cause findings, the stopping rule, and a condensed summary table in
full — this is the per-candidate detail behind that condensed table, plus
Fig. 11 which visualizes the same MAE numbers.)*

Candidate repairs for the two root-cause findings (`relationship_accuracy`
zeroed for structurally relationship-free correct answers;
`concept_coverage` self-referentially vacuous in production), all rejected
by pre-committed evidence. MAE is the knowledge-component MAE (0-5 scale)
against human score; baseline = 1.164. All were evaluated offline against
the real, unchanged extraction and comparison outputs for the full real
Mohler sample; where a live comparator code change was involved (rows 4-5),
it was implemented, end-to-end validated, and reverted within the same
development cycle when it failed its own validation.

1. **`seed_ids` (question-keyword match) as `expected_concepts`.**
   Rejected: 100% False Penalty Rate — every human-graded-excellent sample
   scored <0.5 coverage. Models the topic neighborhood, not answer content.
2. **1-hop expanded KG subgraph as `expected_concepts`.** Rejected: same
   failure, worse (mean expected-set size 12.5 concepts).
3. **Reference-answer concept extraction as `expected_concepts`.**
   Rejected: fixed 72.2% of known-bad cases and improved correlation
   (r 0.118→0.200), but MAE worsened (+14%), FPR worsened (6.5%→25.5%),
   and it failed the pre-committed decisive test — worse, not better, on
   cases where the independent C_LLM baseline is also wrong.
4. **Exclude unvalidated coverage, renormalize onto {accuracy,
   integration} (live code change).** Implemented, then retracted same
   day: end-to-end validation on all 1,156 in-domain samples showed it
   measurably worse (MAE 1.164→1.614, r 0.118→0.082, FPR 9.0%→32.5%) — it
   leans harder on `relationship_accuracy`, itself still broken.
5. **Joint fix (both findings' repairs together) and neutral-prior
   degradation (0.5 instead of 0/excluded).** Both still worse than
   baseline on every metric (MAE 1.446 and 1.471 respectively).
   Neutral-prior is the only candidate to slightly beat baseline on the
   hard-case test specifically, entirely offset by getting worse on easy
   cases; not chased further per explicit decision-theoretic reasoning (a
   significant result would not change the deployment decision, so it
   does not warrant a dedicated significance check).

---

## 0. Cross-Dataset LOOCV Cluster-Size Sweep

*(Originally part of `\subsection{Cross-Dataset Boundary Characterisation}`,
"LOOCV evidence quality" paragraph, in Results.)*

Restricting Kaggle ASAG's clustered Wilcoxon test to clusters with at least
3 samples (N=115) gives d_z=-0.08, p(one-tailed)=0.15 — unchanged from the
full-sample result. Restricting further to clusters with at least 5 samples
(N=22) gives d_z=-0.02, a null result. Cluster-size filtering does not
rescue the Kaggle ASAG result at any threshold tested.

---

## 1. Confidence Interval Analysis (Test Set + All 3 Datasets)

*(Originally `\subsection{Confidence Interval Analysis (Test Set + All 3
Datasets)}`, `\label{subsec:ci_analysis}`, in Results.)*

We recomputed bootstrap 95% CIs (5,000 resamples, seed 20260531, script
`compute_real_fixes.py`) on the real Mohler test split (N=90 responses / 10
questions, stratified question-wise as defined in the Statistical
Significance section): point estimate 34.0% MAE reduction, sample-level 95%
CI [15.1%, 49.7%], cluster-level (question-resampled) 95% CI [2.5%, 56.0%],
and BCa sensitivity [14.1%, 49.8%] (virtually identical to the percentile
method).

*The Mohler-all, DigiKlausur, and Kaggle ASAG rows previously shown
alongside this real Mohler-test row were computed on the fabricated
120-sample fixture (Mohler-all) or on data whose sample size here predates
deduplication (DigiKlausur, Kaggle); they are retracted and moved to
`retracted_analysis.md` for the record, kept separate from this real
result rather than mixed in the same table.*

**Honest disclosure (sample-level CI).** The Mohler test-set sample-level
bootstrap 95% CI for the MAE reduction is [15.1%, 49.7%], excluding zero by
a comfortable margin. The DigiKlausur and Kaggle ASAG sample-level CIs
cross zero.

**Honest disclosure (cluster-level CI, the harder test).** Cluster-level
bootstrap that resamples *questions* rather than individual responses is
more conservative at small Q. The Mohler test cluster-CI widens to [2.5%,
56.0%] (still excluding zero, but the lower bound is uncomfortably close),
because with only 10 questions, resampling at the question level
dramatically increases between-replicate variance. The Mohler all-data
cluster-CI [8.4%, 49.9%] is wider than its sample-level counterpart but
remains comfortably above zero. The DigiKlausur and Kaggle cluster-CIs
also cross zero. **Conservative reading: the in-domain Mohler result is
bootstrap-robust at the cluster level only with the full n=120, marginal
on the n=90 test split; the cross-dataset results are not bootstrap-robust
at either level.** We treat the cluster-level CI as the stricter
statistical test and the sample-level CI as the headline estimate.

BCa sensitivity (Mohler test, sample-level): [14.1%, 49.8%] (bias
correction z0=0.014, acceleration a=0.007), virtually identical to the
percentile-method CI, so the choice of bootstrap method is not the binding
step.

**Honest disclosure (clustered Wilcoxon and LOOCV at n=90 — the headline
result is more fragile than the response-level p-value suggests).** The
LOOCV robustness claim (all 10 questions removable without losing
one-tailed significance) is computed on the full n=120 sample. Re-running
the identical question-clustered Wilcoxon and leave-one-question-out
procedure restricted to the *primary* n=90 held-out responses (9
responses/question) gives a substantially weaker picture: the
question-clustered test itself is only marginal (two-tailed p=0.094,
one-tailed p=0.047), and only **2 of 10 LOOCV folds remain significant at
one-tailed alpha=0.05** (one-tailed p range [0.004, 0.094]; two-tailed
range [0.008, 0.188]), compared to 10/10 folds at n=120. **We report this
because it is the single strongest piece of evidence in this paper against
over-reading the headline n=90 response-level p=0.0053: at only 10
question clusters, the primary result is not robust to which question is
examined most closely, even though the response-level test is
significant.** Combined with the response-vs-question-generalization
caveat (the n=90 split holds out responses, not questions), the honest
summary is that this evidence supports improvement on *known questions
with new student responses*, and much weaker evidence about robustness
across *different questions* within the same KG-aligned domain.

*A per-question robustness check and a Pearson r/QWK bootstrap-CI figure
previously appeared here. Both were computed on the fabricated 120-sample
fixture (the r=0.982/QWK=0.975 figures that originally accompanied that
figure were fabricated-data-era numbers; the main paper's Table of results
reports the real r=0.7841/QWK=0.5237). Both are retained in
`retracted_analysis.md` for the record, not as evidence.*

---

## 2. Statistical Model Sensitivity: Linear Mixed-Effects Reanalysis

*(Originally `\subsection{Statistical Model Sensitivity: Linear
Mixed-Effects Reanalysis}`, `\label{subsec:lmm}`, in Results.)*

Every significance claim in the main paper uses a question-clustered
paired Wilcoxon test: each question's per-response errors are collapsed to
a single mean value, then compared across the resulting Q paired means.
This discards within-question sample size and variance, a real power loss
at 17-50 question clusters. We re-ran the six primary comparisons of this
paper with a linear mixed-effects model (LMM) instead — `abs_error ~
system + (1 | question_id)`, fit by maximum likelihood via `statsmodels`,
with significance from a likelihood-ratio test (full vs. system-free
model) — which uses every response-level data point while still modelling
the non-independence of responses within a question through a random
intercept. All six models converged cleanly (checked explicitly, not
assumed); full output is in `data/lmm_reanalysis.json`, reproducible via
`compute_lmm_reanalysis.py`.

**The verdict is not uniformly favourable, and we report it exactly as
found.** On Mohler, all three comparisons that were marginal or
non-significant under the cluster-mean test become clearly significant
under the LMM (p <= 0.0125 throughout) — consistent with the LMM
recovering statistical power the cluster-collapse step discards. But on
DigiKlausur, the direction reverses: the headline result, one of only two
cross-dataset comparisons in this paper that reached cluster-level
significance at all, *loses* significance under the LMM (p=0.0489 ->
p=0.2471). The fair-control comparisons on both datasets are essentially
unchanged in verdict (already non-significant under both tests), and
Kaggle ASAG's headline comparison likewise stays non-significant under
both (p=0.702 cluster-Wilcoxon vs. p=0.930 LMM).

We do not treat either test as unconditionally authoritative. The
cluster-mean Wilcoxon is conservative and distribution-free but wastes
information; the LMM uses all response-level data but its likelihood-ratio
test relies on an asymptotic chi-squared reference that can be
anti-conservative at 17-50 clusters, a caveat we state once here rather
than re-deriving per result. What both tests agree on: the fair-control
comparisons remain non-significant at the question level under either
method, and Kaggle ASAG remains null under either method. Where they
disagree is exactly where this paper's evidence was already thinnest — the
single-dataset DigiKlausur headline result and the marginal Mohler
comparisons — so the practical effect of this reanalysis is to widen, not
narrow, the honestly-reportable uncertainty band around this paper's
weaker claims, while strengthening its strongest dataset's (Mohler)
statistical case.
