# ConceptGrade Architecture Investigation — Full Report (2026-08-18)

This document is the complete, single-source narrative of a one-day
investigation into whether ConceptGrade's knowledge-graph-grounded
architecture beats plain LLM zero-shot grading. It covers the research
question, the methodology and discipline used throughout, every code
change made, every experiment run (with exact purpose, method, and
result), and a full inventory of where every cached result lives.

It complements, rather than replaces, `REPRODUCIBILITY.md`'s Finding 4/5
entries (the terse, audit-style record). This document is the readable,
chronological version — read this first to understand *why* things
happened in this order; read REPRODUCIBILITY.md for the compact,
citable, per-finding record.

**Total cost this session**: ~$11.85 of $15 OpenRouter budget (GPT-5.6-terra
and DeepSeek-chat-v3.1, via OpenRouter) + an unmetered number of Gemini
2.5 Flash calls (Google AI Studio billing, tracked separately by the
project owner, not through this session's OpenRouter budget).

---

## 1. Research question

> Does ConceptGrade's architecture — extract a concept graph from a
> student's answer, compare it against an expert knowledge graph, detect
> misconceptions, classify cognitive depth, and combine all of this into
> a score — produce a *better* grade than simply asking an LLM to grade
> the answer directly (question + reference answer + student answer, one
> call, no KG)?

This was the paper's original hypothesis. This investigation set out to
either validate it properly (it had never been tested against frontier
LLM zero-shot baselines, only against the same backbone's own zero-shot)
or find out precisely why it fails.

---

## 2. Methodology and discipline

Several conventions were used consistently throughout, established
either earlier in the project's history or introduced this session in
direct response to a mistake being caught:

- **Fair comparison discipline**: any comparison between two scoring
  approaches must give both the *same* treatment. The single most
  important instance of this: comparing a *calibrated* score against a
  *raw* one is invalid — it was the exact confound that produced a false
  "47% improvement" early in this session (Section 5.4), caught by testing
  whether the same trick applied to the control condition (zero-shot)
  showed the same gain. It did, proving the "improvement" was generic
  recalibration, not real signal.
- **Leave-one-question-out cross-validation (LOQO CV)** for both
  calibration fitting and significance testing: any weight, calibration
  coefficient, or hyperparameter is selected using only training
  questions, never the held-out question being scored. Nested LOQO CV
  (an inner LOQO loop within the outer training fold) is used when a
  hyperparameter like a ridge penalty or shrinkage strength also needs
  selecting.
- **Response-level AND question-clustered significance**, both required.
  Response-level Wilcoxon (paired, per-sample) has high power but treats
  correlated answers to the same question as independent. Question-
  clustered Wilcoxon (paired, per-question mean error) is the more
  conservative, correct-per-question test. A pre-registered success bar
  (set before this session's data collection) requires **both** at
  p<0.05 to call something a validated "win" — set specifically to avoid
  repeating an earlier retracted finding in this project (an ensemble-
  blend result that only held at the response level).
- **Pilot before full run**: every new experiment was piloted on 20-25
  samples first, output inspected for correctness, before committing to
  a full run — this caught several real bugs (see Section 4).
- **Every negative result reported, not discarded.** Five variants of
  "how should the verifier use KG evidence" were tested; four failed.
  All five are documented with their exact numbers, not just the winner.
- **External review**: two rounds of consultation with an independent
  GPT-5.6-terra instance (no shared context with this session), asked to
  critique the diagnosis and proposed fixes. Both rounds caught real
  issues (Section 5.6, 5.7) that were then fixed and re-validated, not
  just noted.

---

## 3. System architecture — before and after

### Before this session

```
Student answer
  -> Concept extraction (LLM, self-consistency N=3)
  -> KG comparison (algorithmic: concept_coverage, relationship_accuracy,
     integration_quality -- combined via fixed weights 0.45/0.35/0.20)
  -> Misconception/false-belief detection (LLM)
  -> Cognitive depth classification (LLM: Bloom's + SOLO)
  -> kg_score = 0.60*knowledge + 0.40*depth, knowledge penalized by misconceptions
  -> holistic_score = separate LLM call, reference-anchored
  -> pipeline_score = kg_weight*kg_score + holistic_weight*holistic_score (0.05/0.95)
  -> LLM Verifier (sees all of the above as evidence, produces its own score)
  -> final = (1-verifier_weight)*pipeline_score + verifier_weight*verifier_score
     (verifier_weight=1.0 in every deployed/reported config, so final ==
     verifier_score -- the entire chain above the verifier was already
     provably irrelevant to the reported number, just not removed)
```

`use_llm_verifier` defaulted to `False` and `verifier_weight` defaulted
to `0.25` at the class level -- meaning a caller who didn't know to
override these got the *wrong*, never-validated configuration.

### After this session

```
Student answer
  -> Concept extraction (unchanged)
  -> KG comparison (unchanged, still computed -- but only used as
     evidence text, never as a blended score)
  -> Misconception/false-belief detection (unchanged)
  -> Cognitive depth classification (unchanged)
  -> [holistic_score LLM call SKIPPED -- provably discarded downstream,
      pure wasted cost]
  -> LLM Verifier, prompt now includes a GENERIC skepticism instruction
     (live in `conceptgrade/verifier.py`) telling the verifier all KG
     evidence may be unreliable and must be cross-checked against the
     student's actual answer. A TARGETED variant (naming the two
     specific unreliable evidence types) was tested separately and
     scored best among 5 evidence-presentation variants on Mohler, but
     it did NOT beat zero-shot (no statistically significant difference
     detected, p=0.094 response-level) -- it failed its own
     pre-declared adoption bar and was correctly NOT merged into
     production. Treat it as the best-performing exploratory variant on
     one repeatedly-reused dataset, not as validated or deployed
     behavior, until confirmed on unseen question families (see Section
     6 and Section 11 for the corrected framing).
  -> final = verifier_score (verifier_weight=1.0 is now the class default,
     not just the deployed convention)
  -> OPTIONAL: post-hoc affine calibration, fit per (dataset/domain,
     backbone) pair, with compatibility checking that fails closed
     (falls back to uncalibrated) rather than silently applying a
     mismatched or stale calibration
```

---

## 4. Code changes

All changes are in `packages/concept-aware/`.

### 4.1 `conceptgrade/pipeline.py`

- `ConceptGradePipeline.__init__` defaults changed:
  `use_llm_verifier: bool = False` → `True`;
  `verifier_weight: float = 0.25` → `1.0`.
  Docstring updated to explain why, citing the evidence trail.
- The `holistic_score` computation (`_run_llm_holistic_score`, one full
  LLM call) is now skipped whenever `self.verifier is not None and
  self.verifier.verifier_weight == 1.0`, since its output is
  mathematically discarded by the blend formula at that weight. Verified
  this doesn't change any score (only removes dead computation) before
  landing it.
- `StudentAssessment` gained two new fields: `calibrated_score_0to5`
  (float | None, additive, does NOT overwrite `overall_score`'s existing
  0-1 scale) and `calibration_status` (`"uncalibrated"` / `"calibrated"`
  / `"incompatible"`).
- `__init__` gained `calibration_path: Optional[str] = None` and
  `domain: str = ""` constructor arguments. If `calibration_path` is
  given, the calibration is loaded once at construction and checked for
  domain/backbone/prompt-version compatibility before being applied to
  each assessment (fails closed to the raw score on mismatch).

### 4.2 `conceptgrade/verifier.py`

- Added `VERIFIER_PROMPT_VERSION_SAG = "sag_v2_skepticism_2026-08-18"` --
  a version constant bumped whenever the prompt changes in a way that
  could shift the raw-score distribution, so a calibration fit under an
  old prompt can be detected as stale rather than silently misapplied.
- `VERIFIER_USER` (SAG/short-answer mode) template now includes a
  **generic** skepticism instruction ahead of the KNOWLEDGE GRAPH
  EVIDENCE block: tells the verifier all KG evidence may be incomplete,
  wrong, or misleading, and to cross-check it against the student's
  actual answer rather than trusting it as ground truth. This is the
  variant actually live in production, validated to recover DeepSeek
  from a significant loss to no statistically significant difference
  detected vs. bare-verifier (+19.7% MAE improvement, p=1.8×10⁻⁷ for the
  bare-vs-skeptical recovery itself) with no downside on GPT (p=0.87).
- A **targeted** variant (naming `concept_coverage` and chain/relationship
  coverage specifically, rather than warning generically) was tested as
  a standalone experiment (`run_gemini_targeted_skepticism_full.py`,
  which explicitly does not modify `verifier.py`) and scored best of 5
  evidence-presentation variants on the Mohler set (-1.9%, p=0.094 vs.
  zero-shot). It did **not** beat zero-shot, so it did not meet its own
  pre-declared adoption bar and was **not merged**. It should be
  described as the best-performing exploratory variant, not as deployed
  or validated behavior -- see Section 6, and Section 11's note on
  dataset-reuse selection bias.
- `VERIFIER_USER_LAG` (long-answer mode) was **not** touched by either
  variant.

### 4.3 `conceptgrade/calibration.py` (new file)

- `Calibration` dataclass: `a`, `b` (affine coefficients), `domain`
  (required), `fit_backbone` (required), `n_fit`, `rubric_id` (optional),
  `verifier_prompt_version` (optional), `fit_date`.
- `check_compatible(domain, backbone, verifier_prompt_version="",
  strict=True)`: raises `IncompatibleCalibrationError` (or returns
  `False` if `strict=False`) on domain, backbone, OR prompt-version
  mismatch. Version check is skipped only when either side leaves it
  unset (empty string means "unknown," never treated as an automatic
  match).
- `fit()`, `apply()` (clips to [0,5]), `save()`, `load()`.
- The module docstring documents, in detail, why domain AND backbone
  both must match (an earlier version of this module claimed backbone
  didn't matter -- that claim was retracted the same day after a
  properly controlled re-test found the transfer is asymmetric; see
  Section 5.6-5.7).

### 4.4 Production calibration artifacts

- `data/calibration_mohler_data_structures_gpt.json` and
  `..._deepseek.json` -- one per backbone, NOT pooled (pooling was
  tested and found to help GPT while measurably hurting DeepSeek --
  Section 5.7). Refit a second time same-day after the verifier prompt
  changed (Section 5.8), to avoid the exact staleness bug the new
  `verifier_prompt_version` check now catches automatically.

---

## 5. Experiments and testing scenarios, in order run

Each entry: **purpose**, **method**, **script**, **result**.

### 5.1 Frontier zero-shot baselines (Claude, GPT, DeepSeek via OpenRouter)

**Purpose**: establish how plain zero-shot grading performs on frontier
models, as a baseline for everything downstream.
**Method**: batched (chunk size 25) zero-shot scoring, question +
reference + student answer only, no KG, on the full real Mohler set
(n=1,262).
**Script**: `run_frontier_baselines_batched.py` (writes
`data/mohler_real_eval_results_{claude,gpt,deepseek}.json`).
**Result**: all three beat both Gemini's own zero-shot C_LLM and
ConceptGrade's C5_fix pipeline, response-level p<10⁻²⁷, question-
clustered p<0.001. Cost: ~$0.51 total. See
`data/frontier_baselines_significance.json`
(`compute_frontier_baselines_significance.py`).

### 5.2 Option A: backbone swap (full pipeline on GPT/DeepSeek)

**Purpose**: does the full, untuned ConceptGrade pipeline (still at
verifier_weight=1.0) beat that same backbone's own zero-shot, when the
backbone is a frontier model instead of Gemini?
**Method**: full Phase A (extraction, self-consistency N=3, misconception/
false-belief detection) + Phase B (depth classification, verifier
scoring), batched, on 300 (GPT) / 298 (DeepSeek) real Mohler samples,
parallelized (ThreadPoolExecutor, rate-limited).
**Scripts**: `run_frontier_pipeline_phaseA_batched.py`,
`run_frontier_pipeline_phaseB_batched.py` →
`data/{gpt,deepseek}_pipeline_phaseA_signals.json`,
`data/{gpt,deepseek}_pipeline_eval_results.json`.
**Result** (`compute_pipeline_backbone_significance.py`): both backbones
**underperform their own zero-shot** -- GPT: +6.1% worse, p=0.04
response-level, p=0.15 question-clustered (not significant). DeepSeek:
+20.5% worse, p=5×10⁻⁶ response-level, p=0.05 question-clustered.
Pre-registered criterion (beat zero-shot at both levels): **FAIL**, both
backbones.

### 5.3 Option C: cross-validated weight tuning

**Purpose**: is verifier_weight=1.0 actually optimal, or would a properly
tuned blend with the KG-formula score do better?
**Script**: `compute_pipeline_weight_tuning.py`. 5-fold CV sweeping
verifier_weight ∈ [0,1] in steps of 0.1, both backbones.
**Result**: every fold, both backbones, selects w=1.0 as optimal --
cross-validation itself confirms "don't blend the KG formula in at any
weight" is already the best available choice. No held-out fold improves
on the untuned result.

### 5.4 Option B: learned reweighting -- a confound caught before it became a false finding

**Purpose**: could a supervised model (ridge regression on all raw
sub-scores + verifier score, leave-one-question-out CV) beat the
verifier alone?
**Script**: `compute_pipeline_learned_reweighting.py`.
**What happened**: a naive first pass showed an apparent 47% MAE
improvement. Before accepting it, the same treatment was tested on the
**control condition** (recalibrating raw zero-shot the same way) — it
showed a comparable gain (0.92→0.43), proving the "improvement" was a
generic affine-recalibration artifact available to *any* raw 0-5 LLM
score, not evidence the pipeline architecture adds value. This is
documented in the script's own docstring as the confound it exists to
avoid repeating.
**Corrected result** (fair, both sides recalibrated): GPT verifier alone
beats recalibrated zero-shot by 10.6% (p=5×10⁻⁹). DeepSeek: recalibrated
zero-shot is *marginally better* than the recalibrated verifier alone
(no win). Adding the raw KG sub-scores on top of the recalibrated
verifier makes things **worse** on both backbones (confirmed via
`compute_pipeline_diagnostic_stepwise.py`'s systematic single-signal and
pairwise-combination sweep) — an exploratory observed difference
consistent with (not an independent confirmation of; see
REPRODUCIBILITY.md Finding 6 on dependent sensitivity checks sharing a
single underlying dataset) Findings 2/3's five prior repair attempts,
that the KG-formula sub-scores carry no usable signal.

### 5.5 First external GPT review

**Purpose**: independent critique of the diagnosis and proposed
redesign, before implementing anything.
**Script**: `ask_gpt_architecture_review.py` → `data/gpt_architecture_review.md`.
**Result**: confirmed the composite-formula diagnosis; recommended
precise claim wording (don't over-generalize "symbolic fusion is
unsalvageable"); recommended a hierarchical/shrinkage calibration
strategy (tested, see 5.6-5.7); flagged model-independence overclaiming;
flagged prompt injection, feedback-harm, and question-family
generalization as unaddressed risks.

### 5.6 Calibration transfer, round 1 -- confounded, later retracted

**Purpose**: test whether calibration is portable across LLM backbones.
**Script**: `compute_hierarchical_calibration.py`.
**What happened**: compared a "prior" calibration fit on all 298 of
DeepSeek's samples against a "local" calibration fit on only 10-50 GPT
samples. Prior beat local/shrinkage at every tested size -- but this
gave the prior an inherent, uncontrolled sample-size advantage,
unrelated to genuine backbone transferability. This confound was caught
by a **second external GPT review** (Section 5.8), not found
internally first.

### 5.7 Calibration transfer, round 2 -- an improved but still exploratory re-test, retracts round 1

> ⚠️ **2026-08-19 correction**: "properly controlled" overstated this
> re-test's status. It fixed the specific sample-size confound the
> external review caught in round 1 (Section 5.6) -- a real
> improvement -- but it remains an exploratory observed difference: the
> source and target samples are still not response-ID- or
> question-disjoint (REPRODUCIBILITY.md Finding 6's convenience-subset
> disclosure applies here too), so "controlled" should be read as
> "controlled for the one confound identified so far," not as a fully
> controlled experiment.

**Purpose**: redo the test with matched sample sizes, both transfer
directions, a shrinkage-strength sweep, and confidence intervals, per
the external review's exact specification.
**Script**: `compute_controlled_calibration_transfer.py`.
**Result**: transfer is **asymmetric**. DeepSeek→GPT transfer holds up
(prior/shrinkage beats local at every size). GPT→DeepSeek transfer is
**worse than local-only at every size**. A direct pooled-vs-backbone-
specific test (500 resamples, 70/30 split) confirmed the same asymmetry
with non-overlapping 95% CIs: pooling slightly helped GPT (0.379→0.367)
but measurably hurt DeepSeek (0.447→0.464). **This retracted round 1's
"calibration transfers across backbones" claim** -- the corrected rule
is: fit one calibration per (domain, backbone) pair, never pool, never
assume transfer without testing the specific direction.

Complementary test, same day, different question --
**`compute_crossdataset_calibration_transfer.py`**: does calibration
transfer across *datasets* (Mohler/DigiKlausur/Kaggle ASAG), same
backbone (Gemini)? Result: transfer **hurt in 5 of 6 directions**, up to
38% worse MAE -- calibration is domain-specific, confirmed independently
of the backbone question.

### 5.8 Second external GPT review, and the staleness bug it indirectly caused to be caught

**Purpose**: review the concrete architecture changes made in response
to round 1, before calling the design final.
**Script**: `ask_gpt_final_design_review.py` → `data/gpt_final_design_review.md`
(one call cut off by the 4096-token limit; the full, final review was
obtained by the project owner separately and pasted into the
conversation -- see `docs/GPT_FINAL_DESIGN_REVIEW_REQUEST.md` for the
exact request sent).
**Result**: identified the Test-1 sample-size confound (Section 5.6),
specified the exact controlled re-test design (implemented as 5.7),
challenged the pooled-calibration decision (validated as wrong in 5.7),
recommended `verifier_prompt_version` as a compatibility check (see 4.3)
-- **which then caught a real bug same-day**: after the verifier prompt
changed for Finding 5 (Section 5.9), the two calibration artifacts
(fit under the *old* prompt) were stale. Refit against the new prompt's
scores and the version check now prevents this recurring silently.

### 5.9 Inter-rater reliability estimate (Mohler) -- RETRACTED as a "ceiling" claim, 2026-08-19

**Purpose (as originally framed)**: how much of the remaining MAE gap to
human scores is model error vs. irreducible human-label noise?
**Method**: Mohler retains both individual grader scores
(`score_grader_1`, `score_grader_2` in `data/mohler_real/mohler_real_kg_aligned.json`).
Different questions use different raw point scales in the source
dataset; each row's own scale factor was recovered via
`score_avg / mean(grader_1, grader_2)`.
**Original result, as reported**: inter-rater r=0.554 (MAE=0.78). Via
Spearman-Brown, the 2-rater average's reliability ≈0.713, implying a
"theoretical ceiling of r≈0.844." Raw, uncalibrated GPT verifier
achieves r=0.824 -- reported as "97.6% of that ceiling."

**Retraction (2026-08-19, external review)**: this calculation is
methodologically circular and should not have been reported with the
confidence it was given. The per-row scale factor was derived from
`score_avg / mean(grader_1, grader_2)` -- i.e. from the *same two values*
whose disagreement was then measured. This is not independent scale
recovery; the "sanity check" that it reproduces `score_avg` exactly is
tautological (true by construction, not a validation of anything). The
r≈0.844 figure is a classical-test-theory attenuation estimate under
strong assumptions (independent rater errors, one latent true score,
correctly-recovered per-question scale) that were not actually verified.
It is not a proven maximum any model must respect, and a correlation
estimate does not establish an irreducible MAE floor regardless. The
comparison also mixed populations inconsistently across different parts
of this investigation (the ceiling used all 46 questions; several
model-correlation numbers elsewhere used an 11-question subset).

**Corrected position** (further corrected 2026-08-19, fourth review
round): some inter-rater disagreement clearly exists in this dataset,
but the specific MAE=0.78/r=0.554 figures previously cited for it are
NOT clean or independent of the retracted derivation -- both graders'
scores were put on the common 0-5 scale using the same disputed
`score_avg / mean(grader_1, grader_2)` per-row factor before those
numbers were computed, so they carry the identical circularity the
"ceiling" derivation is retracted for. *Some* portion of remaining
model-vs-human error is still plausibly irreducible, but this
investigation does not have a rigorous, non-circular estimate of how
much -- not even the raw disagreement figures. Establishing
one would require question-level scale metadata recovered independently
of the grader scores themselves (not derived from them), and ideally a
proper generalizability/ICC analysis with question and rater random
effects. Every claim elsewhere in this investigation that leaned on "most
remaining error is irreducible noise" should be read as an unconfirmed
hypothesis, not an established finding.

### 5.10 Evidence ablation (isolating "evidence content" from "prompt template")

> ⚠️ **2026-08-19 correction**: "causal" below (and this section's
> original title) refers specifically to this ablation's own internal
> design (prompt template held fixed, only evidence toggled -- a
> legitimate way to isolate evidence content from prompt wording
> *within this sample*). It is not a claim that this generalizes beyond
> the convenience-subset samples tested (first ~5-11 questions in
> dataset order, not a random/representative sample -- see
> REPRODUCIBILITY.md Finding 6). See the identical precision note
> already applied to REPRODUCIBILITY.md's Finding 5.

**Purpose**: does KG-evidence-in-context help the verifier within this
controlled within-sample ablation, or is the earlier GPT-vs-zero-shot gap
just from a longer/more-structured prompt?
**Method**: three conditions, verifier's own system prompt held fixed:
zero-shot (different prompt entirely, no evidence -- existing baseline),
bare-verifier (verifier's prompt/instructions, KG evidence block
removed), full-verifier (verifier's prompt, evidence included --
existing deployed condition). n=150 per backbone, identical samples.
**Script**: `run_verifier_evidence_ablation.py` →
`data/{gpt,deepseek}_verifier_ablation_bare.json`.
**Result**: prompt-template effect alone (bare vs. zero-shot, both no
evidence) is negligible on both backbones (GPT p=0.42, DeepSeek p=0.76)
-- no statistically significant difference detected, consistent with
"just a longer prompt" not being the explanation, within this sample.
Evidence effect (full vs. bare, same prompt): GPT +4.8% (p=0.10, not
significant at this n). **DeepSeek: -24.3%, p=0.0005 -- within this
controlled within-sample ablation, evidence-in-context significantly
HURTS DeepSeek**, not merely "doesn't help" -- scoped to this sample, not
a general claim about DeepSeek or KG evidence.

### 5.11 Skepticism fix, round 1 -- generic

**Purpose**: fix the harm found in 5.10 -- test whether telling
the verifier the KG evidence is fallible and must be cross-checked
against the student's actual answer eliminates the harm.
**Script**: `run_verifier_skeptical_evidence_test.py` (standalone test,
did not modify `verifier.py` yet) → tested on n=150 then full n=300/298
per backbone.
**Result**: DeepSeek MAE 1.418→1.140 (+19.7%, p=1.8×10⁻⁷) -- recovers
essentially all the harm, no longer significantly different from having
no evidence at all. GPT: 0.833→0.837 (p=0.87) -- no downside. **Adopted
into production** (`conceptgrade/verifier.py`'s `VERIFIER_USER`), then
immediately caused the calibration-staleness issue described in 5.8,
fixed same day.

### 5.12 Fair re-check with the fixed pipeline, and Gemini's founding claim doesn't survive it

**Purpose**: re-test "does ConceptGrade beat zero-shot" with the
skepticism-fixed pipeline, fairly (both sides recalibrated), at whatever
statistical power is available per backbone.
**Result on GPT (n=300, 11 questions -- least powered)**: response-level
win, +11.5%, p=5.8×10⁻⁷; question-clustered not significant, p=0.10,
8/11 questions.
**Result on DeepSeek (n=298, 11 questions)**: no statistically
significant difference detected, p=0.38 response-level, p=0.70
question-clustered (nonsignificance is not equivalence -- this sample is
underpowered to rule out a real difference either way).
**Result on Gemini, full 46-question, n=1,262 dataset (best-powered --
reused already-cached Phase A extraction + depth classification, only
re-ran the verifier stage)**: this is where the paper's *original*
founding claim was tested fairly for the first time. Old (pre-Finding-5)
architecture: **significant loss**, -5.7% response-level (p=0.0003),
-question-clustered p=0.0048 (15/46 wins). This means the original
paper's positive result likely never survived a fair (both-sides-
calibrated) comparison -- it just was never tested that way before.
Script for the full-dataset Gemini verifier re-run:
`run_gemini_skeptical_verifier_full.py` →
`data/mohler_real_verifier_skeptical.json`.

### 5.13 Skepticism fix, round 2 -- targeted (exploratory only; not adopted, did not beat zero-shot)

**Purpose**: the generic instruction treats all evidence uniformly
suspect; test naming the *specific* known-broken evidence types
(concept_coverage -- Finding 3; chain/relationship coverage -- Finding 2)
instead, while leaving misconceptions/Bloom's/SOLO at normal trust.
**Script**: `run_gemini_targeted_skepticism_full.py` →
`data/mohler_real_verifier_targeted.json`. Full 1,262-sample, 46-question
Gemini run.
**Result**: MAE 0.4142→0.4220 (only -1.9%; response-level p=0.094 --
**no statistically significant difference detected**, nonsignificance is
not equivalence), question-clustered p=0.39 (21/46, weaker still --
the response-level p=0.094 is the less conservative of the two tests;
see REPRODUCIBILITY.md Finding 6 for both numbers and why the
question-clustered test should be read as primary). Correlation actually
improved past zero-shot (r=0.803 vs 0.793). **Best-ranked of 5
exploratory evidence-presentation variants tested on the same
repeatedly-reused Mohler set -- not a validated result; it did not beat
zero-shot and was never adopted into production (see REPRODUCIBILITY.md
Finding 6).**

### 5.14 Subgroup analysis -- another confound caught before reporting

**Purpose**: does the aggregate "tie" hide a real, larger win in a
specific subgroup (e.g. partial-credit answers, human score 2-4)?
**What happened**: a first pass using **raw, uncalibrated** scores
showed a large apparent gain concentrated in the score-2-to-4 band
(mean gain up to +0.42). Before reporting this, the same fair
(LOQO-recalibrated) methodology used everywhere else was applied to the
subgroup specifically -- **the effect vanished** (p=0.42 response-level,
p=0.46 question-clustered within the subgroup). This was the same
raw-vs-calibrated confound as Section 5.4, caught a second time by
insisting on the same discipline before reporting. No real subgroup
advantage found.

### 5.15 Corrected concept-coverage evidence -- a genuine architecture-level fix, tested and failed

**Purpose**: rather than warn about broken evidence, actually *fix* it --
replace the tautological concept_coverage (student's concepts compared
against themselves) with real reference-answer-grounded coverage,
reusing `data/reference_concepts_mohler.json` (42 questions, extracted
via a real `ConceptExtractor.extract()` call on each question's
reference answer, cached from Finding 3's original investigation --
zero new cost to reuse). Fed as verifier evidence-in-context (never
tried before -- Finding 3 only tested this as input to the now-dead
numeric formula).
**Script**: `run_gemini_corrected_coverage_full.py` →
`data/mohler_real_verifier_corrected_cov.json`. **Corrected exclusion
accounting (2026-08-19; the original write-up mislabeled this)**: of
1,262 total responses across 46 questions, 42 of the 46 questions have a
reference-concept entry, 41 of those 42 are non-empty and usable. This
yields **1,126 usable responses across 41 questions**, and **136
excluded responses across the remaining 5 questions** (`E04.Q03`,
`E08.Q01`, `E09.Q01`, `E10.Q01`, `E12.Q06`) where the reference answer
itself produced no extractable concepts. The original text's "30
questions' worth of samples excluded" was wrong on both the excluded-
question count (5, not 30) and what "30" actually referred to.
Because this condition runs on a 41-question subset, its numbers are
**not directly comparable** to the other four variants' 46-question
results without restricting all five to the common 41-question subset
first -- this was not done, so the -13.0%/p=6.6×10⁻⁷ figure below should
be read as indicative, not as a clean apples-to-apples ranking entry.
**Result**: **significantly worse than everything else tried** --
MAE 0.4058→0.4587 (-13.0%, p=6.6×10⁻⁷), question-clustered p=0.0004
(8/41 wins). Confirms and extends Finding 3's original warning (which
showed the same reference-grounded coverage hurt the numeric formula) --
the failure isn't specific to the numeric-fusion mechanism, it's that
reference-answer-extracted "expected concepts" are themselves too
narrow/strict a ground truth (terse reference answers don't capture
every valid way a student can correctly phrase the same idea).

### 5.16 Evidence removal -- third exploratory mechanism tested, also failed

**Purpose**: instead of warning about broken evidence (5.13) or trying to
fix it (5.15), just remove it from the prompt entirely -- keep only
misconceptions and Bloom's/SOLO (the evidence types that haven't shown
defects).
**Script**: `run_gemini_evidence_removed_full.py` →
`data/mohler_real_verifier_evidence_removed.json`. Full n=1,262.
**Result**: MAE 0.4142→0.4369 (-5.5%, p=0.0002), question-clustered
p=0.016 (14/46) -- nearly as bad as the original, untouched pipeline
(5.12's -5.7%). **Correction (2026-08-19)**: the original write-up
described this as showing the concept list "isn't pure noise" and
explaining *why* targeted skepticism scored best. That's a mediation
claim this single ablation doesn't isolate -- concept list, coverage
percentage, chain/relationship evidence, misconceptions, Bloom's/SOLO,
and warning wording were never independently varied in a factorial
design. All that can honestly be said: in this same exploratory,
dataset-reused comparison, outright evidence removal scored worse than
targeted skepticism. Whether that's *because* the concept list orients
the verifier, or some other reason, is an untested hypothesis.

---

## 6. Full ranked comparison -- EXPLORATORY, all 5 variants developed and ranked on the same reused Mohler dataset

**Correction (2026-08-19)**: every row below was generated by testing a
prompt variant, observing its result on Mohler, and moving to the next
variant informed by that result -- this is standard iterative
development, but it also means selecting "the best of 5" on this table
and reporting that variant's own performance on the same data is
model-selection bias. None of these numbers should be read as a
validated, held-out result. All five rows are exploratory. The ranking
itself (which variant performed best) is a reasonable guide for what to
try in a properly held-out confirmation, not a conclusion in its own
right. Row 5's n differs from rows 1-4 (see Section 5.15) and is not
directly comparable without restricting to the common question subset.

| Rank | Approach | Response-level | Question-clustered | Status |
|---|---|---|---|---|
| 1 | Targeted skepticism (exploratory only -- NOT in production) | -1.9%, p=0.094 | p=0.39, 21/46 | Did not beat zero-shot; best of 5 exploratory variants |
| 2 | Generic skepticism (**this is what's live in `verifier.py`**) | -3.6%, p=0.0048 | p=0.18, 19/46 | Adopted for reducing DeepSeek's harm (Section 5.11), not because this Gemini test showed a win |
| 3 | Evidence removed entirely | -5.5%, p=0.0002 | p=0.016, 14/46 | Exploratory, not adopted |
| 4 | Original (trust evidence blindly, pre-Finding-5) | -5.7%, p=0.0003 | p=0.0048, 15/46 | Superseded |
| 5 | Corrected (reference-grounded) coverage | -13.0%, p<0.001 | p<0.001, 8/41 | Exploratory, not adopted, n not directly comparable (see above) |

## 7. Cross-backbone summary -- CORRECTED labeling (2026-08-19)

**The original version of this table mislabeled all three rows as
"targeted-skepticism."** GPT and DeepSeek were tested with the
**generic** skepticism prompt (the one actually live in production) --
targeted skepticism was tested on Gemini only, and only as an
exploratory variant (see Section 6). Corrected (note the Gemini row below
is **targeted**, not generic -- this is the same mislabeling this
section's original correction pass in 2026-08-19 missed on the Gemini
row specifically, found during a further review round):

| Backbone | Prompt variant tested | n / questions (power) | Response-level | Question-clustered |
|---|---|---|---|---|
| GPT-5.6-terra | Generic skepticism | 300 / 11 (low; convenience subset, not a random question sample -- see Section 11) | Win, p<10⁻⁶ | Not significant, p=0.10, 8/11 |
| DeepSeek-chat-v3.1 | Generic skepticism | 298 / 11 (low; same caveat) | No sig. diff., p=0.38 | No sig. diff., p=0.70, 4/11 |
| Gemini 2.5 Flash | **Targeted** skepticism (exploratory only, NOT what's live in production) | 1,262 / 46 (nominally higher question count) | No sig. diff., p=0.094 | No sig. diff., p=0.39, 21/46 |

Even with the labeling fixed, GPT's row is the only one showing a
response-level win, and it's on the smallest, least-diverse question
sample of the three (see Section 11 on why "46 questions" doesn't
straightforwardly mean "well-powered" here either). Do not read this
table as establishing model-independence or a validated win on any
backbone.

---

## 8. Full data/cache file inventory

All paths relative to `packages/concept-aware/`.

### 8.1 Source datasets and pre-existing baselines (not created this session)

| File | Contents |
|---|---|
| `data/mohler_real/mohler_real_kg_aligned.json` | Frozen real Mohler dataset, 46 questions, 1,262 responses, both individual grader scores |
| `data/mohler_real_phaseA_signals.json` | Cached Gemini extraction/comparison/misconceptions, all 1,262 samples (reused extensively, zero re-extraction cost this session) |
| `data/mohler_real_eval_results.json` | Original paper result: Gemini zero-shot (`cllm_score`) + old pipeline (`c5_score`), all 1,262 samples, plus `blooms_level`/`solo_level` (reused for all Gemini re-verification runs) |
| `data/reference_concepts_mohler.json` | 42 questions' real reference-answer-extracted expected concepts (Finding 3's original investigation; reused zero-cost in Section 5.15) |
| `data/mohler_real_eval_results_{claude,gpt,deepseek}.json` | Frontier zero-shot baselines, full n=1,262, all 3 models (Section 5.1) |

### 8.2 Option A/B/C data (GPT/DeepSeek full pipeline, n≈300, Sections 5.2-5.4)

| File | Contents |
|---|---|
| `data/{gpt,deepseek}_pipeline_phaseA_signals.json` | Full Phase A output (extraction, comparison, misconceptions) |
| `data/{gpt,deepseek}_pipeline_eval_results.json` | Full Phase B output (depth, verifier score) |
| `data/{gpt,deepseek}_pipeline_backbone_significance.json` | Option A significance results |
| `data/{gpt,deepseek}_pipeline_weight_tuning.json` | Option C CV-tuning results |
| `data/gpt_pipeline_learned_reweighting.json` | Option B ridge-regression results (with the caught confound documented in the script) |
| `data/{gpt,deepseek}_pipeline_diagnostic_stepwise.json` | Systematic single-signal/combination sweep |

### 8.3 Calibration experiments (Sections 5.6-5.8)

| File | Contents |
|---|---|
| `data/hierarchical_calibration_test.json` | Round 1 (confounded, retracted) |
| `data/controlled_calibration_transfer.json` | Round 2 (sample-size confound fixed; still an exploratory observed difference, not a controlled experiment -- source/target remain non-disjoint, see Section 5.7's 2026-08-19 correction) |
| `data/crossdataset_calibration_transfer.json` | Cross-dataset transfer test (Mohler/DigiKlausur/Kaggle) |
| `data/calibration_mohler_data_structures_{gpt,deepseek}.json` | **Live production calibration artifacts**, backbone-specific, refit after the Finding-5 prompt change |

### 8.4 External review transcripts

| File | Contents |
|---|---|
| `data/gpt_architecture_review.md` | First review (Section 5.5) |
| `data/gpt_final_design_review.md` | Second review, partial (cut off by token limit) (Section 5.8) |
| `docs/GPT_FINAL_DESIGN_REVIEW_REQUEST.md` | The exact request sent for the second review (the full response was obtained by the project owner separately) |
| `data/gpt_next_steps_consult.md` | Third, shorter consult on question-coverage power and DeepSeek's tie |

### 8.5 Causal ablation and skepticism-fix data (Sections 5.9-5.13, best results)

| File | Contents |
|---|---|
| `data/{gpt,deepseek}_verifier_ablation_bare.json` | Bare-verifier (no evidence) condition, n=150 |
| `data/{gpt,deepseek}_verifier_skeptical_evidence.json` | Generic-skepticism condition, full n |
| `data/mohler_real_verifier_skeptical.json` | Gemini, generic skepticism, full n=1,262 (Section 5.12) |
| `data/mohler_real_verifier_targeted.json` | Gemini, TARGETED skepticism (exploratory variant, NOT in production -- see Section 6/7), full n=1,262, best of 5 exploratory variants but did not beat zero-shot (Section 5.13) |

### 8.6 Failed architecture-level fixes (Sections 5.14-5.16)

| File | Contents |
|---|---|
| `data/mohler_real_verifier_corrected_cov.json` | Reference-grounded coverage evidence, n=1,126 (failed, Section 5.15) |
| `data/mohler_real_verifier_evidence_removed.json` | Evidence entirely removed, n=1,262 (failed, Section 5.16) |

### 8.7 Batch caches (raw LLM responses, not summary data)

Every experiment above that made real API calls also has a matching
`data/*_batches/` directory containing the raw, per-chunk cached LLM
responses (e.g. `data/mohler_real_verifier_targeted_batches/verifier_c0.json`
... `verifier_c50.json`). These are what make every experiment
instantly re-runnable at zero cost if the summary JSON is ever deleted
or needs re-deriving.

---

## 9. Scripts inventory (all in `packages/concept-aware/`, all new this session unless noted)

| Script | Purpose |
|---|---|
| `run_frontier_baselines_batched.py` | Zero-shot baselines, 3 frontier models (5.1) |
| `compute_frontier_baselines_significance.py` | Significance testing for 5.1 |
| `run_frontier_pipeline_phaseA_batched.py` | Full pipeline extraction+misconceptions, GPT/DeepSeek (5.2), later parallelized |
| `run_frontier_pipeline_phaseB_batched.py` | Full pipeline depth+verifier, GPT/DeepSeek (5.2), later parallelized, later hardened against a real key-corruption bug found on DeepSeek |
| `compute_pipeline_backbone_significance.py` | Option A significance (5.2) |
| `compute_pipeline_weight_tuning.py` | Option C CV tuning (5.3) |
| `compute_pipeline_learned_reweighting.py` | Option B ridge regression, documents the caught confound (5.4) |
| `compute_pipeline_diagnostic_stepwise.py` | Systematic per-signal/combination sweep (5.4) |
| `ask_gpt_architecture_review.py` | First external review call (5.5) |
| `compute_hierarchical_calibration.py` | Calibration transfer round 1 -- confounded (5.6) |
| `compute_crossdataset_calibration_transfer.py` | Cross-dataset transfer test (5.7) |
| `compute_controlled_calibration_transfer.py` | Calibration transfer round 2 -- corrected (5.7) |
| `ask_gpt_final_design_review.py` | Second external review call (5.8) |
| `run_verifier_evidence_ablation.py` | Evidence ablation (within-sample, controlled prompt-template), GPT/DeepSeek n=150 (5.10) |
| `run_verifier_skeptical_evidence_test.py` | Generic skepticism fix, tested (not "validated") on GPT/DeepSeek (5.11), later extended to full n |
| `ask_gpt_next_steps.py` | Third external consult (question-coverage power, DeepSeek tie) |
| `run_gemini_skeptical_verifier_full.py` | Generic skepticism, Gemini full-dataset re-verification (5.12) |
| `run_gemini_targeted_skepticism_full.py` | Targeted skepticism, Gemini full-dataset (5.13) -- exploratory only; its own docstring states it does not modify `verifier.py`, and it was correctly not merged since it didn't beat zero-shot |
| `run_gemini_corrected_coverage_full.py` | Reference-grounded coverage fix, Gemini full-dataset (5.15) |
| `run_gemini_evidence_removed_full.py` | Evidence-removal fix, Gemini full-dataset (5.16) |

Every script above is self-contained and re-runnable: each reads only
already-cached upstream data (extraction/depth) and re-runs only the
specific stage it's testing, using its own dedicated batch-cache
directory so it can never collide with or silently reuse another
experiment's cached responses.

---

## 10. Where this leaves the project (corrected 2026-08-19)

**The one claim in this document that survives independent, careful
re-checking**: the original numeric KG-comparison composite scoring
formula provides no benefit and should not be used for scoring --
observed consistently across 3 backbones (Gemini, GPT, DeepSeek) and 8+
related sensitivity checks (5 formula-repair attempts in an earlier
investigation round, plus backbone-swap, CV-tuning, and
learned-reweighting this session), all against the same underlying
Mohler dataset and therefore dependent, not independent, confirmations
(see REPRODUCIBILITY.md Finding 6 on why repeated tests against one
reused dataset don't accumulate as independent evidence). This part is
not in dispute from the 2026-08-19 review, but should be read as one
well-corroborated observation, not 8+ separate pieces of evidence.

**Everything downstream of that needs to be read more cautiously than
the original version of this document presented it.** The generic
skepticism instruction (what's actually live in production) reduced
DeepSeek's evidence-caused harm to a non-significant difference from
zero-shot and showed no downside on GPT -- that specific claim holds.
Beyond that:

- The "targeted skepticism, best-ranked of 5, no significant difference
  detected vs. zero-shot" result is an
  **exploratory, unvalidated finding** from selecting the best of 5
  variants developed on the same repeatedly-reused dataset. It is not
  in production and should not be adopted without confirmation on
  unseen question families.
- The "97.6% of the reliability ceiling, most remaining error is
  irreducible" claim is **retracted** (Section 5.9) -- the underlying
  calculation was circular.
- The GPT/DeepSeek 300/298-sample subsets and the 150-sample evidence
  ablation are convenience slices (first N samples in dataset order --
  effectively the first 11 or 5 questions), not random question
  samples, so "46 questions = well-powered" does not straightforwardly
  transfer to claims about generalization across question types.
- The calibration-transfer "controlled" re-test (Section 5.7) still
  isn't response-ID- or question-disjoint between source and target, so
  calibration transferability and the value of pooling remain
  unvalidated, not merely "asymmetric but understood."

**What this investigation actually established with confidence**: the
symbolic KG-formula scoring approach doesn't work, and a full,
independent architectural review is warranted before pursuing further
prompt-level fixes on this same dataset. See
`docs/CONCEPTGRADE_RECOVERY_PLAN_2026-08-19.md` for that review's
proposed redesign and phased validation plan, which this project is
treating as the roadmap going forward, alongside a Phase 0
integrity-fix pass on this codebase's cache-key versioning, reference-
answer propagation, and named experiment configurations.

---

## 11. Known limitations (added 2026-08-19, after external review)

Consolidated here rather than only inline, so they can't be missed:

1. **Dataset-selection bias.** All 5 evidence-presentation variants
   (Section 6) were developed and ranked on the same 46-question Mohler
   set. Picking the best-ranked one and reporting its own performance on
   that same data is model selection, not confirmation. Stopping after
   5 variants limits further overfitting but doesn't undo the selection
   already done.
2. **Convenience subsets, not random question samples.** The GPT/
   DeepSeek 300/298-sample pipeline runs (Section 5.2 onward) are the
   first N responses in a question-grouped file -- the first 11
   questions only, with the last partially represented. The 150-sample
   evidence ablation (Section 5.10) covers only the first 5 questions.
   Statistical power in a question-clustered test is driven by the
   number of independent question clusters, not response count -- these
   subsets should not be described as well-powered relative to Gemini's
   46-question run without that caveat, and future work should randomly
   sample complete questions before observing any results.
3. **Calibration-transfer tests are not question- or response-
   independent.** Section 5.7's "controlled" re-test fixed the original
   sample-size confound but source and target rows can still share
   response IDs and are split at the response level, not the question
   level -- so it does not estimate transfer to genuinely new questions.
   Calibration transferability and the value of pooling backbones
   remain unvalidated, not merely "asymmetric but understood."
4. **LOQO discipline was not applied everywhere it's claimed.** Some
   experiments (e.g. an earlier Gemini calibration pass, some weight-
   tuning runs) used random response-level k-fold splits instead of
   leave-one-question-out, meaning responses to the same question could
   appear in both a training and evaluation fold in those specific
   experiments. Every calibration, hyperparameter, and prompt-selection
   procedure should be nested inside grouped, question-level outer
   folds going forward.
5. **Mediation and causal-independence claims should be narrowed.**
   Statements that "the concept list carries weak-but-real signal" or
   that this explains why targeted skepticism outperforms removal
   (Section 5.16) are mediation claims a simple ablation doesn't
   isolate -- a factorial design varying concept list, coverage
   percentage, chain/relationship evidence, misconceptions, Bloom's/
   SOLO, and warning wording independently would be needed. Likewise,
   the multiple analyses in Section 5 mostly reuse the same cached
   samples/labels/features -- they are dependent sensitivity checks on
   one dataset, not independent replications. Independent replication
   requires untouched question families, exams, datasets, or graders.
6. **This document is not yet reproducible from a single command.** The
   full chain from cached artifacts to every reported statistic, table,
   and exclusion count is not preserved in one script that also
   verifies artifact/prompt/configuration provenance and fails loudly on
   a mismatch. This is one of the Phase 0 integrity items now in
   progress (see `docs/CONCEPTGRADE_RECOVERY_PLAN_2026-08-19.md`).

See `docs/CONCEPTGRADE_RECOVERY_PLAN_2026-08-19.md` for the full external
review this section summarizes, and for the broader architectural
critique (why the KG-derived evidence is structurally unlikely to help
regardless of prompt wording, and a proposed rubric-anchored redesign)
that this document's Section 5 experiments did not have.
