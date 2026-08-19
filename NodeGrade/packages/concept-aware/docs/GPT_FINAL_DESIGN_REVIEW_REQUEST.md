# ConceptGrade architecture redesign — final design review request

You are reviewing a concrete architecture redesign for ConceptGrade, an
automated short-answer grading (ASAG) system, following up on an earlier
review round where you critiqued the problem diagnosis and proposed
solution. This document summarizes what was actually decided and
implemented as a result, plus two new empirical tests run specifically to
answer questions the earlier review raised — including a real
methodological weakness already caught in one of those tests, described
below rather than hidden. Please review the whole thing critically —
confirm what looks right, and push back hard on anything that doesn't.

## Recap: the diagnosis (from the previous review round)

ConceptGrade's original scoring formula — a hand-set weighted blend of
concept_coverage, relationship_accuracy, and integration_quality, further
blended with an LLM "holistic score" and then an LLM "verifier" score —
was shown, across 8 independent tests over two investigation rounds (five
formula-repair attempts on 1,156 real samples; then a backbone swap,
cross-validated weight tuning, and learned reweighting on ~300 samples
each on two different frontier LLM backbones, GPT-5.6-terra and
DeepSeek-chat-v3.1), to add no measurable scoring value and often hurt.
The one validated improvement was post-hoc affine recalibration of the
LLM verifier's raw score — but this only clearly beat zero-shot on one of
two backbones tested (GPT: yes, 10.6% MAE reduction, p<0.001; DeepSeek:
no, zero-shot was marginally better alone).

In that review, the recommendation was: (1) precise claim wording — say
"the composite formula adds no value" (replicated), not "KG evidence
improves verifier judgment" (didn't replicate) or "symbolic fusion is
unsalvageable" (too broad); (2) a hierarchical/shrinkage calibration
strategy (global/backbone prior + local deployment-specific adjustment,
shrunk toward the prior when local data is small) rather than one
universal constant or purely per-deployment fitting; (3) clipping
calibrated scores to [0,5]; (4) not claiming model-independence for the
KG-evidence-helps-verifier result given the DeepSeek non-replication; and
(5) flagged risks: false authority (verifier over-trusting wrong KG
evidence), feedback harm being worse than score error, prompt injection
from student text, leave-one-question-out CV not testing genuinely new
question families, nested-evaluation discipline, human-score reliability
ceiling, model drift on OpenRouter-routed backbones, and separating
grading from feedback as two different jobs for the KG evidence to serve.

## What we actually did in response

**Test 1 — does the recommended hierarchical/shrinkage calibration
strategy hold up empirically?** Rather than implement it on faith, we ran
a direct comparison (zero new API calls, reusing cached verifier scores):
fit a calibration on ALL of DeepSeek's Mohler data (n=298), apply it
UNMODIFIED to GPT's Mohler data (a "prior-only" strategy — the opposite
of what was recommended), versus local-only calibration on a small GPT
sample (n=10/20/30/50), versus a shrinkage blend of the two (weighted by
n_local/(n_local+20) toward local). Result, averaged over 200 random
splits per sample size: the prior-only strategy beat BOTH local-only and
shrinkage at every tested sample size. Shrinkage was consistently worse
than pure prior.

**⚠️ Known methodological weakness in Test 1, not yet resolved**: the
"prior" fit used ALL 298 of DeepSeek's samples, while the "local" fit
only got 10-50 GPT samples — an inherent, uncontrolled sample-size
advantage for the prior. This means Test 1 may be showing "more data
beats less data," not "cross-backbone transfer works" per se. We have
NOT yet re-run this with the comparison properly controlled (e.g.
matching sample sizes, or testing both directions: fit-on-GPT/apply-to-
DeepSeek in addition to the fit-on-DeepSeek/apply-to-GPT direction
already tested). This is flagged honestly as an open gap, not resolved.

**Test 2 — does calibration transfer across DATASETS the way it (may)
transfer across backbones?** Using a different, already-available
resource: Gemini's cached scores across all three datasets this project
evaluates on (Mohler n=1262, DigiKlausur n=646, Kaggle ASAG n=368,
backbone held fixed this time, dataset varied). Fit a calibration on one
dataset, apply it unmodified to another, in all 6 directions. Result:
transfer HURT in 5 of 6 directions tested, up to 38% worse MAE. One
direction "helped" but still left the target dataset far short of its
own achievable in-domain calibration ceiling (0.91 transferred vs. 0.43
in-domain-fit MAE).

**Conclusion drawn from both tests (tentative, given Test 1's
weakness)**: calibration may be portable across LLM backbones on the
SAME dataset/domain, but is NOT portable across datasets/domains on the
same backbone (this second half IS well-controlled — Test 2 used the
same sample-size logic in both directions of each pair). Practical rule
tentatively adopted: fit one calibration per dataset/domain, reuse it
across whatever backbone is plugged into the verifier for that domain,
never reuse a calibration across domains. **This rule's cross-backbone
half rests on Test 1, which has the sample-size confound above — treat
that half as provisional.**

## What we implemented in the codebase

1. `ConceptGradePipeline.__init__`'s defaults changed from
   `use_llm_verifier=False, verifier_weight=0.25` (the old, discredited
   architecture) to `use_llm_verifier=True, verifier_weight=1.0` (the
   only configuration ever actually validated), so a caller who doesn't
   explicitly override these no longer silently gets the wrong setup.
2. The pipeline now SKIPS an entire extra LLM call (`_run_llm_holistic_score`)
   whenever verifier_weight=1.0, since that call's output is mathematically
   discarded by the blend formula at that weight — a real, provable
   cost/latency saving with zero effect on the final score.
3. A new `conceptgrade/calibration.py` module: a `Calibration` dataclass
   (affine a/b coefficients, a REQUIRED `domain` field naming the
   dataset/subject this was fit for, `n_fit`, and `fit_backbones` for
   provenance), `fit()`/`apply()`/`save()`/`load()` functions, clipping to
   [0,5] built into `apply()`. Wired into the pipeline as an OPTIONAL
   `calibration_path` constructor argument. When present, the calibrated
   value is stored in a NEW, additive field (`calibrated_score_0to5`) —
   it does NOT overwrite `overall_score`, which keeps its existing 0-1
   scale and meaning everywhere else in a large existing codebase, to
   avoid a silent breaking change.
4. One real calibration fit and saved for production use:
   `data/calibration_mohler_data_structures.json`, fit on GPT+DeepSeek
   scores pooled together (per the tentative cross-backbone-transfer
   rule — see the Test 1 caveat above), domain-tagged
   "mohler_data_structures".
5. All of this is documented as "Finding 4" in the project's
   REPRODUCIBILITY.md, in the same rigorous style as three prior
   documented findings (a tokenization bug, and two other diagnosed-but-
   unfixed formula defects from an earlier investigation round).

## Deliberately left open (not resolved, by choice)

Whether KG-evidence-in-context specifically (as opposed to a generically
longer/more-structured verifier prompt) causes GPT's residual edge over
zero-shot was left untested. Resolving it needs a new controlled ablation
(same verifier prompt template, KG evidence toggled on/off in stages)
that requires fresh API spend for an effect that (a) didn't replicate on
DeepSeek and (b) isn't the claim being carried forward as the headline
result. This was judged not worth the spend given it doesn't change the
production architecture either way.

## Questions

1. Given the sample-size confound in Test 1 (prior fit on n=298, local
   fit on n=10-50), how much of the "prior beats shrinkage" result should
   we actually trust? What's the minimal properly-controlled re-test that
   would resolve this (e.g. matched sample sizes, both transfer
   directions, confidence intervals across the 200 splits)?
2. Is `domain` (dataset/subject-level) the right granularity for when a
   calibration must be refit, or is that still too coarse — e.g. should
   question type, difficulty band, verifier prompt version, or answer
   length also gate reuse? Should the calibration artifact carry
   machine-checkable version/compatibility identifiers rather than a
   free-text domain string?
3. Cold-start problem: what should the pipeline do for a brand-new domain
   with zero calibration data yet — ship uncalibrated scores with an
   explicit status flag, refuse to score, or something else? Should this
   be a policy the deploying application configures rather than a single
   hard-coded default?
4. Is the pooled GPT+DeepSeek production calibration
   (`data/calibration_mohler_data_structures.json`) actually validated,
   or does it need its own held-out test (fit-on-one/test-on-other in
   both directions, backbone-specific vs. pooled comparison) before being
   called production-ready — especially given GPT and DeepSeek showed
   different underlying calibration behavior (GPT benefited clearly from
   calibration, DeepSeek's zero-shot was already close to calibrated)?
5. Any concerns with the specific code design (additive
   `calibrated_score_0to5` field vs. overwriting `overall_score`;
   `calibration_path` as an optional constructor arg loaded once at
   construction rather than per-call; no compatibility check preventing
   a Mohler calibration from being silently applied to, say, Kaggle
   answers)?
6. Of the risks flagged in the previous review (false authority, feedback
   harm, prompt injection, LOQO not testing new question families, human-
   score reliability ceiling), which would you prioritize addressing
   first, given the architecture changes made so far haven't touched any
   of them yet?
7. Is there anything about this redesign that would make you say it's NOT
   ready to be called "the model design" and move on to writing this up,
   versus what's still missing?

Be direct and critical — flag anything you'd push back on, not just what
already sounds right.
