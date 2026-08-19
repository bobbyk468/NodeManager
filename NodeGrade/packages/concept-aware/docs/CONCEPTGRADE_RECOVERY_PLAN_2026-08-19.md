# ConceptGrade Architecture Review and Recovery Plan

**Date:** 2026-08-19  
**Reviewed document:** `INVESTIGATION_REPORT_2026-08-18.md`

## Executive conclusion

The investigation supports a narrow but important conclusion:

> The current ConceptGrade architecture does not outperform strong direct
> LLM grading. Its fixed numeric KG formula adds no measurable value, and
> presenting the current KG-derived evidence to an LLM verifier ranges from
> harmful to approximately neutral across the tested backbones.

The central problem is not simply incorrect fusion weights. ConceptGrade
currently asks an LLM to extract concepts, relationships, cognitive depth,
and misconceptions from an answer, then asks an LLM from the same model
family to grade that answer using those model-generated annotations. These
annotations are mostly noisy transformations of information already
available in the answer; they do not provide sufficiently independent
grading evidence.

To outperform a strong direct LLM, ConceptGrade must introduce information
or constraints the baseline does not already infer reliably. The most
promising route is a **question-specific, expert-authored rubric graph**
combined with proposition-level evidence tracing and deterministic scoring.

## What the report establishes well

The report is unusually transparent about negative results and caught
several important confounds:

- Raw and recalibrated scores were eventually compared fairly.
- Calibration-transfer claims were retracted after a sample-size confound
  was identified.
- Both response-level and question-clustered significance were reported.
- Failed KG evidence mechanisms were documented rather than discarded.
- The investigation correctly concludes that the existing
  `0.45/0.35/0.20` numeric KG formula should not drive production grades.
- The strongest adequately powered result does not demonstrate a win.

These practices should be retained.

## Critical corrections and limitations

### 1. Targeted skepticism is not the current production prompt

The report repeatedly describes targeted skepticism as the current
production configuration. The current `conceptgrade/verifier.py` still
contains the generic skepticism paragraph.

The targeted instruction exists in
`run_gemini_targeted_skepticism_full.py`, whose documentation explicitly
states that it does not modify `verifier.py`. The experiment also declared
that the prompt would be adopted only if it beat both zero-shot and generic
skepticism. It did not beat zero-shot.

The report should therefore describe targeted skepticism as the
best-performing experimental variant, not as validated production behavior.

The GPT and DeepSeek rows in the report's cross-backbone
“targeted-skepticism” summary are also mislabeled: those backbones were tested
with generic skepticism. Targeted skepticism was tested only with Gemini.

### 2. Prompt selection and final evaluation reused Mohler

Five evidence-presentation mechanisms were developed, tested, and ranked on
the same 46-question Mohler dataset. Selecting the best variant and then
reporting its performance on the same dataset introduces model-selection
bias.

Stopping after five variants reduces further overfitting but does not undo
the selection already performed. The targeted result must be confirmed on
an untouched question-family test set or external dataset before it can be
called validated.

### 3. Failure to reject a difference does not establish a tie

The targeted condition is numerically worse than zero-shot
(`0.4142 -> 0.4220` MAE), with `p=0.094`. A nonsignificant difference does
not demonstrate equivalence, and ranking five point estimates does not show
that the first-ranked prompt is significantly better than the others.

If equivalence is the intended claim, define a practically meaningful MAE
margin before evaluation and run a question-clustered equivalence test with
confidence intervals. Until then, the correct wording is:

> Targeted skepticism did not show a statistically significant difference
> from zero-shot on this dataset; its point estimate was slightly worse.

### 4. “Better than LLM” needs an operational definition

A stable research objective should be:

> A question-specific rubric-graph system improves a predefined outcome over
> an equal-information, equal-budget direct LLM on unseen question families.

Possible predefined outcomes include:

- grading MAE or ordinal loss;
- quadratic weighted kappa;
- criterion-level diagnostic accuracy;
- feedback factuality and usefulness;
- consistency across repeated grading;
- adversarial and prompt-injection robustness;
- calibrated abstention and human-review efficiency;
- cost and latency.

Without an explicit outcome, model version, information budget, and compute
budget, “better than LLM” is not falsifiable and will become obsolete as
models change.

### 5. The reliability ceiling is overstated

The reported `r≈0.844` value is a classical-test-theory attenuation estimate
under assumptions such as independent rater errors and a single latent true
score. It is not a universal maximum that no model can exceed.

The calculation also derives a per-response scale factor from
`score_avg / mean(grader_1, grader_2)`. Reproducing `score_avg` after this
transformation is tautological because the target itself defines the scale.
The scaling materially changes the estimated inter-rater correlation.
Question-level scoring scales should instead be recovered from independent
dataset metadata or grading rubrics.

The ceiling and model correlation are not calculated on the same population:
the ceiling uses all 46 questions, while the reported GPT correlation uses an
11-question subset. Any comparison must use matched samples and questions.

More importantly, a correlation ceiling does not establish an irreducible
MAE floor. The statement that most remaining MAE is irreducible human-label
noise is therefore stronger than the evidence supports.

The value should be replaced by an ICC or generalizability analysis with
question and rater effects, uncertainty intervals, and independently
recovered question scales. Future final evaluation should use at least three
blinded graders, retain individual ratings, and adjudicate large
disagreements.

### 6. Section 5.15 reports the wrong exclusion unit

The corrected-coverage experiment contains:

- 1,262 total responses across 46 questions;
- 1,126 usable responses across 41 questions;
- 136 excluded responses across 5 questions;
- 42 reference-concept entries, one of which did not provide a usable
  concept set.

The report's phrase “30 questions' worth of samples excluded” is incorrect.
The corrected-coverage condition must also be compared with other variants
on the common 41-question subset; ranking its 41-question result directly
against 46-question results is not fully comparable.

### 7. Calibration-transfer experiments are not question-independent

The controlled GPT/DeepSeek calibration-transfer experiment uses scores for
largely the same response IDs in both backbones. Source and target
calibration rows are sampled independently, so a target evaluation
response's human label can appear in source calibration. The split is also
response-level rather than question-level.

This does not estimate transfer to new questions. The reported intervals are
Monte Carlo variation across overlapping resamples, not uncertainty over a
new population of questions.

The transfer experiment should be rerun with:

- disjoint response IDs between source fitting and target evaluation;
- preferably disjoint question or exam families;
- shrinkage selection nested within training data;
- bootstrap or permutation at the question/exam-family level.

Until then, calibration transferability and the benefit of pooling remain
unvalidated.

### 8. The stated LOQO discipline is not consistently implemented

The report states that calibration and hyperparameter selection use
leave-one-question-out procedures. Some experiments instead use random
response-level five-fold splits, including verifier-weight tuning and
earlier Gemini calibration. Responses to the same question can therefore
appear in both training and evaluation.

All calibration, feature selection, prompt selection, and hyperparameter
tuning should be nested inside grouped outer folds. The group should be a
question family or exam where possible, not an individual response.

### 9. Frontier subsets are convenience slices with few clusters

The approximately 300-response GPT and DeepSeek subsets contain only the
first 11 questions in a question-grouped file, with the last question only
partially represented. The 150-response evidence ablation covers only the
first five questions.

These are convenience subsets rather than random samples of questions.
Power is determined mainly by the number of independent question or exam
clusters, not the number of responses. The report should disclose the
selection mechanism and avoid describing one backbone as materially better
powered when both use essentially the same 11 clusters.

Future pilots should randomly sample complete questions, stratified by
question type and exam, before any results are observed.

### 10. Question clustering may still be too fine

Questions appear nested within exams, and student responses may be repeated
across questions. Treating every question as independent can still
underestimate uncertainty.

The primary estimand must also be explicit: a response-weighted mean MAE and
a median question-level difference are not the same target. Where identities
permit, use a hierarchical model or cluster bootstrap at exam/question-family
level, with student clustering as an additional random effect.

### 11. Causal and “independent confirmation” language should be narrowed

The bare/full prompt comparison supports an observed prompt-condition effect,
but it reused historical cached outputs rather than concurrently randomized,
repeated calls against a fixed model snapshot. Model drift and run
stochasticity remain possible.

Claims that the concept list contains “weak-but-real signal” or explains why
targeted skepticism works are mediation claims not isolated by the current
ablation. A factorial experiment must independently vary:

- concept list;
- coverage percentage;
- chain/relationship evidence;
- misconception evidence;
- Bloom/SOLO evidence;
- warning wording.

Similarly, multiple analyses of the same samples, labels, and cached features
are dependent sensitivity analyses—not independent confirmations.
Independent replication requires untouched question families, exams,
datasets, or graders.

### 12. Reproducibility is not yet single-command complete

Later prompt-variant scripts generate scores, but the full chain that
produces every reported calibration, exclusion, subgroup result, table, and
p-value is not preserved in one immutable analysis program. At least one
promised backbone-specific tuning artifact is also absent.

Add a single analysis entry point that:

- verifies all required artifacts and prompt/configuration versions;
- logs response, question, and exam exclusions;
- regenerates every report table and statistic;
- fails when an artifact is missing or has an incompatible provenance;
- distinguishes exploratory analyses from the frozen confirmatory test.

## Important implementation problems

### 1. Class grading drops the reference answer

`assess_student()` accepts `reference_answer`, but `assess_class()` does not.
Its internal call invokes:

```python
self.assess_student(sid, question, ans)
```

Consequently, class grading can send `"(not provided)"` to the verifier even
though the experiments used reference answers. The class API should require
and propagate a reference answer or rubric whenever the selected grading
configuration depends on one.

### 2. Cache keys do not encode semantic versions

The pipeline's cache keys omit several inputs that can change a result:

- verifier and extractor prompt versions;
- reference answer;
- KG identity and version;
- rubric identity and version;
- comparison evidence;
- extraction confidence threshold;
- calibration identity;
- domain configuration.

An old verifier result can therefore be reused after a prompt change and
then receive a calibration fitted for the new prompt. This defeats the
prompt-version compatibility protection added to calibration.

Every cache key should hash all semantic inputs and artifact versions.
Cached values should also store provenance and be rejected on mismatch.

### 3. Coverage and related topology features are vacuous

When `expected_concepts` is absent, the comparator uses the student's own
extracted concepts as the expected set. This makes coverage
self-referential.

It also causes matched concepts to equal student concepts, making the
anchor ratio effectively `1.0`. Missing-concept evidence is normally empty,
despite being presented to the verifier as additional reference topics.

These values should be removed from scoring, prompts, and instructor-facing
analytics until a real question-specific assessment specification defines
required, optional, alternative, and irrelevant concepts.

### 4. Relationship validation ignores edge direction

The comparator accepts both forward and reverse directions for every
relationship type. This is invalid for directed relations such as:

- `prerequisite_for`;
- `uses`;
- `produces`;
- `operates_on`;
- `implements`.

Unknown relationships may also be counted as correct rather than marked
unverified. Relationship evaluation should preserve edge direction and
return one of:

- supported;
- contradicted;
- not evidenced;
- outside the rubric;
- abstain.

### 5. The default confidence comparator omits chain coverage

`ConfidenceWeightedComparator.compare()` reimplements the parent comparison
flow but does not calculate chain coverage. Because confidence weighting is
enabled by default, production can show chain coverage as “not computed”
while the report discusses it as a normal evidence input.

### 6. Configuration drift prevents a single reproducible “architecture”

The documented architecture uses self-consistent extraction, while the
pipeline default has `use_self_consistency=False`. The default model is also
not one of the fully evaluated production/calibration pairs described in
the report.

Experiments and deployments should use immutable named configurations that
record:

- model and provider;
- prompt versions;
- KG version;
- rubric version;
- self-consistency settings;
- comparator;
- calibration;
- cache schema;
- code commit.

## Why the current KG features fail

The failures are structural:

1. **No question-specific ground truth.** A global curriculum graph does not
   identify which ideas a particular answer must contain.
2. **Schema mismatch.** Many questions are definitional, comparative, or
   enumerative and do not require the directed relationships represented by
   the KG.
3. **Extraction is not demonstrated understanding.** Mentioning or mapping a
   concept does not prove a correct claim about it.
4. **Reference answers are incomplete rubrics.** A terse model answer does
   not enumerate all valid alternatives or partial-credit paths.
5. **The evidence is not independent.** The same LLM family derives the
   intermediate labels and makes the final holistic judgment.
6. **Global topology is not question relevance.** Density, diameter, and
   graph centrality do not directly measure whether the student satisfied a
   grading criterion.
7. **The baseline is already strong.** Marginal improvements require
   targeting specific residual errors rather than adding broad heuristic
   features.

## Proposed architecture: Rubric-Anchored Claim Trace

### Offline question specification

For each assessment question, create an expert-reviewed specification with:

- atomic grading propositions;
- point weight for each proposition;
- required and optional propositions;
- acceptable alternative explanations;
- prerequisite relationships;
- mutually exclusive or contradictory claims;
- known misconceptions;
- evidence examples and counterexamples;
- rules for partial credit;
- question type: factual, definitional, comparative, procedural, causal,
  analytical, or design.

The global KG becomes a library from which the question specification is
constructed. It is no longer treated as the scoring rubric itself.

### Runtime assessment

```text
Question + rubric specification + student answer
  -> Extract atomic student claims with exact evidence spans
  -> Align claims to rubric propositions
  -> For each proposition:
       supported / partially supported / contradicted /
       not addressed / abstain
  -> Apply question-specific prerequisite and alternative-path rules
  -> Compute points using a deterministic, monotonic aggregator
  -> Calibrate only if held-out evidence supports calibration
  -> Route uncertain or high-impact disagreements to human review
  -> Generate feedback from the proposition trace, not from global KG scores
```

The LLM may perform extraction and entailment, but it should not silently
replace the deterministic rubric score with another holistic score.

### Appropriate uses of the KG

Retain the KG for:

- authoring question-specific rubrics;
- mapping equivalent terminology;
- identifying prerequisite concepts;
- checking directed conceptual claims;
- organizing misconception taxonomies;
- sequencing remediation;
- class-level diagnostic analytics.

Do not use global KG coverage, graph density, or generic relationship counts
as direct grade components.

## Baselines required to isolate graph value

All comparison arms should receive the same authoritative content:

1. **Direct rubric LLM:** question, answer, reference, and rubric rendered as
   text.
2. **Budget-matched direct LLM:** same calls/tokens as ConceptGrade, including
   self-check or independent samples.
3. **Rubric propositions without graph rules:** criterion-wise entailment and
   weighted summation.
4. **Rubric graph system:** identical propositions plus typed prerequisite,
   alternative, and contradiction edges.

Comparing arms 3 and 4 isolates graph reasoning. Comparing the graph system
only against a weaker prompt would measure an information or compute
advantage rather than an architectural contribution.

## Evaluation protocol

### Data partition

- Split by question family, instructor, and domain—not by student response.
- Prevent sibling or paraphrased questions from crossing partitions.
- Use nested question-family CV for development.
- Freeze the final test set before prompt or architecture iteration.
- Evaluate the selected system once on the frozen test.

### Human labels

- Use at least three blinded graders for the final test.
- Preserve individual scores rather than only their mean.
- Adjudicate major disagreements.
- Label criterion satisfaction and misconception correctness on a
  stratified subset.

### Primary and secondary outcomes

Choose one primary scoring outcome before testing:

- MAE;
- ordinal log loss;
- or QWK.

Secondary outcomes should include:

- criterion-level precision, recall, and F1;
- score calibration;
- exact and within-tolerance agreement;
- performance by score band and question type;
- false penalties on high-quality answers;
- misconception precision;
- feedback factuality and instructor preference;
- repeated-run consistency;
- prompt-injection and evidence-poisoning robustness;
- abstention coverage and human-review workload;
- cost and latency.

### Statistical requirements

- Report cluster bootstrap confidence intervals resampled at the highest
  defensible independent level, preferably exam or question family.
- Use exam/question-family-clustered paired tests as the primary significance
  analysis.
- Treat response-level tests as secondary when responses share questions.
- Correct for multiple comparisons when testing several architectures or
  prompts.
- Predefine a minimum practically meaningful effect, not merely `p<0.05`.
- If claiming equivalence, predefine an equivalence margin and test it
  directly; nonsignificance is not equivalence.

## Gated recovery plan

### Phase 0: integrity

Actions:

- Correct the report/source mismatches.
- Fix reference propagation in `assess_class()`.
- Version every prompt, KG, rubric, cache schema, and calibration.
- Fix cache invalidation.
- Add regression tests for directed relationships.
- Remove invalid graph values from user-facing outputs.

Gate:

> A reproduced score must provably use the intended question, reference,
> rubric, prompt, model, graph, evidence, and calibration.

### Phase 1: diagnostic validity

Create a stratified pilot with human labels for:

- proposition satisfaction;
- contradiction;
- evidence-span correctness;
- misconception correctness;
- feedback validity.

Gate:

> Each feature used for scoring must meet a predeclared criterion-level
> accuracy threshold. High-impact contradiction flags should prioritize
> precision.

### Phase 2: rubric-scoring pilot

Build expert-authored rubrics for a small set of question families. Compare:

- direct rubric LLM;
- proposition scorer;
- graph-enhanced proposition scorer.

Use nested question-family CV.

Suggested gate:

> Do not scale unless the graph-enhanced system improves held-out MAE by at
> least 5% over the strongest equal-information baseline, without increasing
> false penalties or reducing diagnostic validity.

### Phase 3: frozen external validation

Evaluate once on unseen:

- question families;
- instructors;
- answer styles;
- domains;
- adversarial answers;
- prompt-injection attempts.

Suggested gate for the claim “better than a strong LLM”:

> The predeclared primary metric improves by a practically meaningful amount
> and its question-family-clustered confidence interval excludes zero.

### Phase 4: feedback and human-review study

If score accuracy does not improve, independently evaluate:

- instructor preference;
- feedback actionability;
- misconception detection;
- review-time reduction;
- uncertainty triage.

A system without a demonstrated MAE improvement can still be valuable, but
only if these benefits are validated. In that case, the research claim
should be “better diagnostic support” rather than “better grader.”

## Immediate recommendation

Do not spend more evaluation budget tuning evidence-warning prompts on
Mohler. The dataset has already been repeatedly used for architecture and
prompt selection.

The next investment should be:

1. fix integrity and provenance defects;
2. freeze a new external test set;
3. author question-specific rubric propositions for a small pilot;
4. collect human criterion-level labels;
5. compare text rubric, proposition decomposition, and graph constraints
   under equal information and compute;
6. stop if the graph adds no held-out value.

This approach either provides a credible path toward the original aim or
produces a defensible boundary result showing that ConceptGrade's value lies
in diagnostics and feedback rather than point-score accuracy.
