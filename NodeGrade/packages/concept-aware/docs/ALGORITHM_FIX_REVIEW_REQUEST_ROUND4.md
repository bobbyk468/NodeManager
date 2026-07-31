# Algorithm Fix Review Request — Round 4 (reference-answer candidate: mixed result)

**Instructions for the reviewer (please read first):**

Same context as rounds 1-3. Status: with your approval, the user spent the
42 API calls to extract concepts from Mohler's reference answers
(one call per unique in-domain question, `run_reference_answer_extraction.py`
→ `data/reference_concepts_mohler.json`). The offline re-analysis
(`compute_reference_concepts_evaluation.py`) is done. **The result is
mixed, not a clean win** — this round reports it exactly as found and asks
what to do next.

---

## Premise check (free, done before spending) — passed

Manually inspected several Mohler reference answers before extraction:
concise (1-3 sentences), similarly dense to student answers (e.g., "by
reference.", "In the array declaration, or by using an initializer
list."). Confirmed reasonable to expect a small, answer-specific concept
set, not a repeat of round 3's topic-neighborhood problem.

## Extraction result

42/42 unique in-domain questions extracted successfully via the real
`ConceptExtractor.extract()` (same class/prompt/model —
`gemini-2.5-flash` — as every student-answer extraction this session,
reference answer passed in the `student_answer` slot). Mean 3.23 concepts
per reference answer (vs.\ round 3's seed_ids=narrow/expanded=broad
candidates, which were far larger and caused the 100% False Penalty Rate).
**One edge case**: 1 of 42 questions ("How are arrays passed to
functions?" → reference "by reference.") produced **zero** extracted
concepts — too terse for the extractor to map to any KG concept. This
affects 30/1,156 samples (2.6%) whose coverage is now forced to 0.0
regardless of student answer quality, since `weighted_coverage()` returns
0.0 when the expected set is empty (same defensive branch documented in
Finding 3's original write-up).

## Full result table

| Metric | current (self-referential) | reference-answer |
|---|---|---|
| Knowledge-component MAE (0-5 scale) vs.\ human | 1.164 | **1.384** (14% worse) |
| Pearson $r$ | 0.118 | **0.200** (70% better) |
| False Penalty Rate ($\text{human}\ge4.0$, new coverage $<0.5$) | 6.5% (846 samples) | **25.5%** (worse) |
| Low-quality-vacuous correction rate (of the 18 known-bad cases from Finding 3) | 0% | **72.2%** (much better) |
| Coverage mean / at-1.0 fraction | 0.876 / 34.9% | 0.633 / 20.8% (healthier spread) |

**Hard-case check** (GPT's round-3 suggestion, the test both of you agreed
would be most persuasive): does reference-derived coverage help
specifically on cases where C\_LLM (the independent, KG-free baseline) is
also wrong (`|cllm_score - human_score| > 1.0`, $n=517$) more than on easy
cases ($n=639$)?

| Subset | current knowledge-MAE | reference knowledge-MAE | Winner |
|---|---|---|---|
| Hard (C\_LLM wrong) | 1.066 | 1.189 | current |
| Easy (C\_LLM right) | 1.243 | 1.542 | current |

**This came back negative** — reference-derived coverage has *higher*
error than the current (buggy) version on both subsets, and doesn't
show the "helps most where it matters most" pattern either of you
predicted would be the strongest evidence in its favor.

## Honest summary of the tension

- Genuinely fixes the tautology in spirit (72.2% of the known-bad
  low-quality cases now show reduced coverage; correlation improves 70%).
- But costs real accuracy elsewhere (MAE up 14% in aggregate, FPR up
  ~4x on genuinely good answers), and fails the specific "does it help on
  hard cases" test that was supposed to be the deciding evidence.
- Part of the regression is attributable to the new empty-reference-concept
  edge case (2.6% of samples), which is arguably a separate, fixable
  sub-problem (e.g., fall back to something else when reference extraction
  is empty) rather than evidence against the core idea.

---

## Review Questions

1. Given the hard-case test came back negative, do you still consider
   reference-answer extraction a viable candidate, or does this result
   effectively fail it?
2. Is the empty-reference-concept edge case (2.6% of samples) enough to
   meaningfully change the verdict if handled separately (e.g., fall back
   to current self-referential behavior only for those 30 samples), or is
   the core candidate's problem bigger than that one edge case?
3. Pearson $r$ improved substantially (0.118→0.200) while MAE got worse
   (1.164→1.384) — how should these be weighed against each other when
   they disagree, especially combined with a worse FPR?
4. Given three candidates have now been tried (seed_ids, expanded,
   reference-answer) and none is a clean win, does this change your
   answer to round 2's Q3 (student's stated fallback: mark coverage
   "unvalidatable" / zero its weight rather than keep searching for a
   fourth automated candidate)? Is it time to invoke that stopping rule?
5. Is there a principled way to combine the reference-answer concept set
   with the current self-referential fallback (e.g., union or
   confidence-blend) that might capture reference's genuine improvements
   (correlation, low-quality correction) without its regressions (MAE,
   FPR), or would that just be curve-fitting to this one dataset?

---

## Student's Own Answers

**Q1.** My honest read is that this result does not clearly pass. The
hard-case test was the one both of you singled out as most persuasive,
and it came back the wrong way on both subsets, not just failing to help.
I don't think "genuinely fixes the tautology" is sufficient justification
on its own if it costs more accuracy than it buys, especially on exactly
the metric (hard cases) that was supposed to be the deciding factor.

**Q2.** Checked (free, offline, done before sending this round). Excluding
the 30 empty-reference-concept samples and recomputing on the remaining
1,126: current MAE=1.080/r=0.149/FPR=3.9%, reference MAE=1.304/r=0.231/
FPR=23.4%. **The same tension holds** — the edge case is not the
explanation. Reference-answer coverage's MAE/FPR regression is intrinsic
to the candidate itself, not an artifact of the 2.6% terse-reference edge
case. This strengthens the case that Q1's "does not clearly pass" reading
is correct, not just edge-case noise.

**Q3.** I lean toward MAE and FPR being the more decision-relevant metrics
here, because they're closer to the actual deployed quantity (kg_formula
feeds directly into the blended score) and because FPR getting worse means
concretely more real students would be under-scored on a dimension they
didn't actually fail on — a correlation improvement doesn't obviously
compensate for that in a system whose stated purpose is fair, students-
facing grading.

**Q4.** Given Q2's follow-up check (the regression survives excluding the
edge case), I'm now leaning toward yes, this is close to triggering the
stopping rule I proposed in round 3. It's not a clean failure — it does
fix part of the problem (72.2% of known-bad cases, real correlation gain)
— but it fails on the specific decisive test we agreed to trust most (hard
cases) and the edge-case exclusion just ruled out my own best alternative
explanation for that failure. I'd still want your read before formally
invoking it, since "mixed with the decisive test failing" is a judgment
call about whether that counts as "failed" under the rule as I originally
framed it.

**Q5.** I'm skeptical of blending largely because of exactly the risk
named: with only 42 questions and 1,156 samples, any blend weight I tune
to look good on this specific evaluation is at real risk of being an
artifact of this data rather than a real improvement, echoing this
project's own earlier retracted ensemble-blend-weight finding (caught by
leave-one-question-out cross-validation). I would only consider a blend if
it could be justified structurally (a clear reason X% reference + Y%
current should be better) rather than by grid-searching for the
best-looking weight on this dataset.
