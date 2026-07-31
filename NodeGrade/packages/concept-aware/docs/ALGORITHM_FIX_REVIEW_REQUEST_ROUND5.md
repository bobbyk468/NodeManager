# Algorithm Fix Review Request — Round 5 (Finding 2 x Finding 3 interaction: neither fix, alone or together, beats the buggy baseline)

**Instructions for the reviewer (please read first):**

Same context as rounds 1-4. Status: with your round-4 agreement, the
stopping rule was invoked for Finding 3's `expected_concepts` search
(3 candidates rejected). The architecture you both converged on next —
exclude unvalidated `concept_coverage` from the knowledge formula,
renormalize onto `{relationship_accuracy, integration_quality}` — was
implemented live, end-to-end validated against the real comparator on all
1,156 in-domain samples, and **failed its own validation** (MAE
1.164→1.614, worse on every metric). It was reverted immediately, same
day. This round reports a follow-up test — fixing Finding 2 and Finding 3
*together* rather than Finding 3 alone — and the result is more decisive
than expected: **nothing tried so far beats the original buggy baseline.**

---

## What was tested this round

Hypothesis: Finding 3's fix failed because it leaned harder on
`relationship_accuracy`, which is itself broken (Finding 2, held).
Natural next test: exclude *both* dimensions where they're each
individually invalid — `concept_coverage` always (Finding 3: never
validated in production) and `relationship_accuracy` when the sample has
≤1 extracted concept (Finding 2's originally-proposed narrow rule,
`compute_relationship_accuracy_fix_estimate.py`'s trigger) — renormalizing
onto whatever remains (`integration_quality` alone when both are
excluded; `{accuracy, integration}` when only coverage is excluded).

All three scenarios recomputed from the same cached, real, unchanged
per-sample `concept_coverage` / `relationship_accuracy` / `integration_quality`
values (`comparison_result.scores`, real `ConfidenceWeightedComparator`
output already validated live in round 4/5's `verify_finding3_fix_live.py`)
across all 1,156 in-domain real Mohler samples:

| Scenario | Knowledge MAE (0-5) | Pearson $r$ | FPR (human$\ge$4.0) | Hard-case MAE (C\_LLM wrong) | Easy-case MAE |
|---|---|---|---|---|---|
| **baseline** (both bugs live, current deployed formula) | **1.164** | **0.118** | **9.0%** | **1.066** | **1.243** |
| Finding 3 only (retracted last round) | 1.614 | 0.082 | 32.5% | 1.436 | 1.757 |
| **Joint** (Finding 2 narrow rule + Finding 3 exclusion, together) | 1.446 | 0.109 | 19.7% | 1.267 | 1.590 |

The joint fix is a real improvement *over* the Finding-3-only fix (MAE
1.614→1.446, FPR 32.5%→19.7%) — fixing both together is better than
fixing one alone, consistent with round 1's original interaction concern.
**But it is still worse than the original, bug-riddled baseline on every
single metric measured**, including the hard-case test both of you
identified as most decisive.

## The uncomfortable interpretation

Two documented, independently-diagnosed bugs (vacuous coverage inflation;
zeroed-by-design accuracy) appear to be **partially cancelling each other
out** in the aggregate composite score today. Naively excluding either or
both — the only fix strategy attempted across rounds 1-5 — consistently
underperforms just leaving the bugs in place, because the bugs are not
independent noise; they interact with the specific weight structure
(`0.45/0.35/0.20`) in a way that a simple "trust it or exclude it"
per-dimension toggle doesn't capture.

Practically, none of this affects the *deployed* production grade, since
the Verifier is blended in at weight $w=1.0$ (raw `kg_formula_score` is
discarded in the deployed configuration, per the existing, separately
cross-validated ablation finding). This affects only the standalone
"KG-grounding is worse than baseline in isolation" ablation analysis and
any future work that wants to *improve* raw KG-grounding rather than route
around it via the Verifier.

---

## Review Questions

1. Given exclude-and-renormalize (alone or combined) consistently
   underperforms the buggy baseline, is this strong evidence the *class*
   of fix (binary include/exclude per dimension, weight renormalization)
   is fundamentally the wrong approach, rather than evidence that the
   specific triggers (≤1 concept, `expected_concepts` unsupplied) are
   miscalibrated?
2. Is there value in continuing to chase a fix for the raw, pre-Verifier
   `kg_formula_score` at all, given (a) it's not the deployed score, and
   (b) every attempted fix so far has made the isolated ablation metric
   worse, not better? Or does the ablation's scientific value (showing
   *why* raw KG-grounding underperforms) stand on its own without needing
   a working fix?
3. If there IS a fix worth pursuing, what class of intervention would you
   try next that isn't "exclude and renormalize a dimension" — e.g.,
   reweighting (not zeroing) unreliable dimensions by a continuous
   confidence/reliability score, or a completely different formula
   structure, rather than binary applicability gating?
4. Given three rounds of rejected fixes and now a fourth (joint exclusion)
   also failing, does this warrant a second stopping rule — i.e., close
   out Finding 2 and Finding 3 as "diagnosed, evidenced, but currently
   unfixed" in the reproducibility record and move on to other work,
   rather than attempting a fifth candidate?

---

## Student's Own Answers

**Q1.** I lean toward "the class of fix is wrong," not just miscalibrated
triggers, because the joint fix used what should be the best available
version of each individual trigger (Finding 1's validated tokenizer
underlies both; Finding 2's trigger is the only version I'd previously
validated at all) and still lost on every metric, not just some. If
miscalibration were the issue I'd expect it to win on some metrics and
lose on others depending on where the miscalibration bites; losing
uniformly looks more like the wrong mechanism entirely.

**Q2.** I think the ablation's scientific value stands independently. The
finding "KG-grounding in isolation is dramatically worse than baseline,
and here are two specific, evidenced, root-caused reasons why (vacuous
coverage, zeroed-by-design accuracy), neither of which has a working fix
under the tested approaches" is itself a complete, honest, defensible
research contribution — arguably more defensible than a "we fixed it"
claim would have been, given how many attempted fixes failed their own
validation in this project already (the ensemble blend, now this).

**Q3.** My best untested idea (now tested, free, offline, before sending
this round): instead of binary applicability gating, make
`relationship_accuracy` and `concept_coverage` degrade toward a neutral
prior (0.5, "no evidence either way") rather than toward 0.0 (current) or
excluded-with-renormalization (tested, worse) when their ground truth is
structurally unavailable — no renormalization needed, so no interaction
with the other dimension's weight. Result: MAE=1.471, $r$=0.097,
FPR=19.6% — **still worse than baseline in aggregate**, same pattern as
every prior attempt. But it is the first candidate across all five rounds
to slightly *beat* baseline on the specific hard-case test (MAE
1.050 vs.\ baseline's 1.066), at the cost of getting much worse on easy
cases (1.811 vs.\ 1.243) — the aggregate loss is driven entirely by
over-penalizing already-easy, already-correctly-scored samples, not by
failing on hard ones. I don't know whether that's meaningful signal (a
neutral prior may specifically help exactly where the current formula's
overconfident 0/1 defaults hurt most) or noise from a small hard-case
subgroup — I haven't checked significance on this split.

**Q4.** Now that Q3's idea is tested rather than hypothetical, I'm more
inclined to say yes, invoke the stopping rule — the neutral-prior result
doesn't clear the bar either (worse in aggregate, same pattern as
everything before it), and its one genuinely novel result (a small
hard-case win) is exactly the kind of narrow, unreplicated,
significance-unchecked signal this project's methodology has learned to
be suspicious of rather than chase. I'd want your read on whether that
hard-case fragment is worth a dedicated significance check before closing
the book, or whether five negative-to-mixed rounds is sufficient grounds
to stop regardless.
