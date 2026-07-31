# Algorithm Fix Review Request — Round 3 (Finding 3 offline experiment results: both candidates rejected)

**Instructions for the reviewer (please read first):**

Same context as rounds 1-2. Quick status: Finding 1 is fixed and merged.
Finding 2 remains held. For Finding 3 (concept_coverage vacuity), both of
you recommended testing candidate `expected_concepts` sources offline
before picking one — that experiment is done, and **both candidates you
converged on (seed_ids, 1-hop expanded subgraph) failed decisively**. This
round reports the result and asks what to do next, including whether to
spend a small, explicit amount of new API budget.

---

## Systemic audit result (per both reviewers' round-2 recommendation)

`grep -rn "Optional\[" ... | grep "= None"` across `conceptgrade/`,
`graph_comparison/`, `concept_extraction/` confirmed the self-referential
`expected_concepts` fallback is **not isolated to one class**: both
`KnowledgeGraphComparator.compare()` (`graph_comparison/comparator.py`) and
`ConfidenceWeightedComparator.compare()`
(`graph_comparison/confidence_weighted_comparator.py`) contain the
identical `expected_set = student_graph.concept_ids` fallback. Confirmed
`ConfidenceWeightedComparator` is the one actually deployed
(`conceptgrade/pipeline.py`: `use_confidence_weighting: bool = True`,
default). No other `expected_*`/`gold_*`-flavored optional parameter in
the audited modules showed the same "declared but never supplied by the
real caller" pattern — this one is confirmed duplicated across exactly two
sibling classes (same inheritance lineage), not a wider systemic issue.

## Offline experiment result: negative for both candidates

Reproduced the LIVE (Finding-1-fixed) question→KG keyword matcher to
derive `seed_ids` (question-only keyword match) and the 1-hop expanded
subgraph (`domain_graph.get_subgraph_for_question(seed_ids, depth=1)`,
the same set already shown to the LLM as extraction context), then
recomputed `ConfidenceWeightedComparator`'s confidence-weighted coverage
formula against real, unchanged, already-extracted student concepts for
all 1,156 in-domain samples (`compute_expected_concepts_candidates.py`).
Evaluated on GPT's broader criteria, not coverage-only Pearson r:

| Candidate | Knowledge-component MAE (0-5 scale) vs.\ human | Pearson $r$ | False Penalty Rate ($\text{human}\ge4.0$ scoring new coverage $<0.5$) | Fixes the 18 known-bad low-quality-vacuous cases? |
|---|---|---|---|---|
| current (self-referential) | 1.164 | 0.118 | 6.5% (of 846) | 0% |
| seed_ids (narrow) | 2.254 | 0.123 | **100%** (846/846) | 100% |
| expanded (1-hop) | 2.355 | 0.102 | **100%** (846/846) | 100% |

Coverage distribution collapses under both candidates: mean coverage drops
from 0.876 (current) to 0.126 (seed_ids) / 0.077 (expanded), with 0% of
samples at coverage=1.0 under either candidate (vs.\ 34.9% today) — i.e.
both candidates fix the vacuity but by *catastrophically over-penalizing*,
scoring every answer, including the 846 human-graded-excellent ones, as
low coverage. GPT's prediction was correct: `seed_ids`/the expanded
subgraph represent the question's whole topic neighborhood (for a queue
question: `queue`, `enqueue`, `dequeue`, `fifo`, `array`, `linked_list`,
...), not what a specific correct short answer needs to state (typically
1-3 concepts) — neither is a usable grading rubric on its own.

## What this suggests

The two zero-cost candidates are ruled out empirically, as both of you
recommended testing for rather than assuming. The remaining untested idea
is GPT's round-2 suggestion #9: extract concepts from the **reference
answer** itself (already present in the dataset, `reference_answer` field)
using the same extractor, and use those as `expected_concepts` — this is
answer-specific rather than topic-general, which is exactly the property
seed_ids/expanded lack. This has NOT been tried because it requires new
LLM calls: **42** (one call per unique in-domain Mohler question in this
analysis, reusable across all responses to that question — not
per-response), a small, explicit, boundable spend.

---

## Review Questions

1. Given both zero-cost candidates failed for the predicted reason (topic-
   general, not answer-specific), does reference-answer concept extraction
   look like the right next (and possibly final) candidate to test, or is
   there a cheaper offline alternative neither of us has considered yet?
2. Is 42 calls (one per unique question) an acceptable, well-scoped spend
   for this specific test, or would you want a smaller pilot first (e.g.,
   5-10 questions) before committing to all 42?
3. If reference-answer extraction also turns out too strict/lenient, what
   would be the fallback — abandon a fully-automated `expected_concepts`
   and treat Finding 3 as unfixable without manual annotation, or is there
   a middle ground (e.g., a lower coverage-membership threshold, or
   confidence-weighted partial credit for expected concepts that are
   "nearby" in the KG rather than exact matches)?
4. Any concern that reference-answer-derived concepts will trivially
   correlate too well with kg_formula_score (since the same LLM/extractor
   family generated both), producing an overfit-looking result that
   doesn't reflect real-world robustness?

---

## Student's Own Answers

**Q1.** I don't have another zero-cost candidate in mind beyond what's
already been ruled out. The reference-answer path is the natural next
step precisely because it's the only remaining data source in the dataset
that is both (a) not derived from the student's own answer (avoiding
Finding 3's tautology) and (b) answer-specific rather than topic-general
(avoiding the over-penalization just observed).

**Q2.** I'd lean toward running all 42 in one batch rather than piloting a
subset first — the marginal cost difference between 5 calls and 42 is
small in absolute terms, and a 5-10 question pilot risks a noisy read
(could look good or bad by chance on a small, non-representative slice of
question types). But I'd want to confirm this reasoning with you before
spending, since "the marginal cost is small so just do the whole thing" is
exactly the kind of reasoning that got this project into trouble with
uncontrolled API spend earlier in the project's history — I'd rather ask
than assume.

**Q3.** I would treat a second failure as a genuine signal that
fully-automated `expected_concepts` derivation may not be tractable with
the current KG-keyword-matching-based architecture, and would want to
step back rather than keep inventing new automated candidates indefinitely
(there's a real risk of never stopping this search). A middle ground I
would consider: instead of a hard set-membership match, keep the current
architecture but change what "expected" *means* — e.g., report coverage
transparently as "unvalidatable" (similar to the OUT_OF_KG_DOMAIN marker
already used elsewhere in this codebase for a different failure mode)
rather than force a numeric 0-1 coverage score when no non-circular ground
truth is available, and let the Verifier (which already carries most of
the deployed system's grading weight, per the existing ablation finding)
handle those cases instead of the raw KG formula.

**Q4.** This is a real concern I had not previously named. My mitigation
would be to check whether reference-answer-derived coverage predicts
human_score *better* specifically among samples where C_LLM (the
independent, KG-free zero-shot baseline) is ALSO wrong by a large margin —
if reference-answer coverage only "looks good" on the easy majority where
every method already agrees, that's weaker evidence than if it
specifically helps disambiguate the hard cases where C_LLM itself
disagrees with the human grader. I have not run this check yet since the
underlying reference-answer extraction hasn't been done.
