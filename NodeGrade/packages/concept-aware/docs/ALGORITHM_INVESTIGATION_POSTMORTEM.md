# Algorithm Investigation Post-Mortem — Final Review

**Instructions for the reviewer:** This consolidates a 5-round algorithmic
investigation (previously reviewed piecemeal across
`ALGORITHM_FIX_REVIEW_REQUEST.md` through `_ROUND5.md`) into one coherent
document, now that the investigation is closed. The request: does this
summary accurately and honestly represent what was actually established,
and is there anything about the *overall* arc — not any single round —
that reads differently once seen end to end? No new code changes are
planned from this round; the ask is a sanity check before this material
is used in paper writing.

---

## 1. What prompted this

An ablation in this project's existing paper work showed the KG-grounded
score (`kg_formula_score`, pre-Verifier) performing dramatically worse
than a KG-free LLM baseline (C_LLM) in isolation — MAE 2.397 vs.\ 1.282 on
the real 1,262-sample Mohler benchmark. Rather than accept that as an
unexplained result, an inductive failure-mode analysis (60 worst-case
samples by `|kg_score - human_score|`, no predetermined taxonomy) was run
to find out *why*, entirely offline, reusing already-cached predictions.

## 2. Finding 1 — tokenization bug (fixed, merged)

**Bug**: `_build_question_ontology()` in `concept_extraction/extractor.py`
tokenized questions via `.split()` without stripping punctuation. "What is
a queue?" produced the token `"queue?"`, which never substring-matched
`"queue"` in KG concept text — so every "What is a `<KG-concept>`?"
question found zero seed concepts, scored `domain_match_score=0.0`, and
was misclassified `out_of_kg_domain=True`, discarding otherwise-correct
extractions via an all-zero-score short-circuit.

**Scope**: 106/1,262 samples (8.4%), exactly 4 questions.

**Fix**: strip punctuation per-token (`t.strip(string.punctuation)`)
rather than a blunt regex-extraction, preserving short CS terms
("map", "set") and hyphenated terms ("big-o") a naive approach would drop.

**Validation**: live regression test against all 1,262 samples — exactly
106 expected flips, 0 unexpected regressions, 63/63 unit tests pass. MAE
on the 106 affected samples improves 65.1% (3.96→1.38, now beating C_LLM
on those samples); full-dataset MAE improves 5.03% (p<0.0001).

**Status: merged and live.**

## 3. Finding 2 — relationship_accuracy=0.0-by-design (diagnosed, not fixed)

**Mechanism**: `_compute_relationship_accuracy()` deliberately returns
0.0 when a student extracts zero relationships (a documented 2026-06-15
fix against a worse prior bug: rewarding keyword-dump answers with 1.0).
Side effect: any correct answer that is structurally incapable of
expressing a relationship — single-concept factual answers, or
comparative/definitional/enumerative questions regardless of concept
count ("What are the two functions of a queue?" → "enqueue and dequeue",
perfect answer, zero relationships) — is scored identically to a keyword
dump on this dimension.

**Scope**: 246/1,156 in-domain samples (21.3%) extract zero relationships;
180 of those (73.2%) are human-graded correct (≥4.0/5).

**Status: diagnosed and quantified, never merged.** A narrow candidate
fix (exclude the dimension when ≤1 concept is expected) was proposed but
never shipped in isolation — see §5.

## 4. Finding 3 — concept_coverage self-referential vacuity (diagnosed, not fixed)

**Discovered**: while sanity-checking Finding 2's candidate fix (both
external reviewers independently demanded checking for score inflation on
low-quality answers before merging) — that check surfaced a deeper,
pre-existing problem.

**Mechanism**: `compare()`'s `expected_concepts` parameter is never
supplied by the only production call site
(`conceptgrade/pipeline.py:476`). It silently falls back to
`expected_set = student_graph.concept_ids` — the student's own extracted
concepts — making `concept_coverage` trivially 1.0 for any answer
extracting ≥1 concept, regardless of correctness. Confirmed present in
**both** comparator classes, including the actually-deployed
`ConfidenceWeightedComparator` (`use_confidence_weighting=True` by
default).

**Concrete proof**: a student answer completely off-topic to its question
(human-graded 0.5/5) scored `concept_coverage=1.0` because it happened to
mention one tangentially-related concept.

**Scope**: 404/1,156 samples (35.0%) show this trivial 1.0; 18/1,156
(1.6%) are visibly bad (low-quality answers with undeserved full credit).

## 5. Five rounds of candidate fixes, all rejected by pre-committed evidence criteria

| # | Candidate | Result |
|---|---|---|
| 1 | `seed_ids` (question-keyword match) as `expected_concepts` | **Rejected**: 100% False Penalty Rate — every human-graded-excellent sample scored <0.5 coverage. Models the topic neighborhood, not answer content. |
| 2 | 1-hop expanded KG subgraph as `expected_concepts` | **Rejected**: same failure, worse (mean expected-set size 12.5 concepts). |
| 3 | Reference-answer concept extraction as `expected_concepts` (42 live API calls, user-approved) | **Rejected**: fixed 72.2% of known-bad cases and improved correlation (r 0.118→0.200), but MAE worsened (+14%), FPR worsened (6.5%→25.5%), and it failed the pre-committed decisive test — doing *worse*, not better, on cases where the independent C_LLM baseline is also wrong. Confirmed not an artifact of a terse-reference edge case. |
| 4 | Exclude unvalidated `concept_coverage`, renormalize onto `{accuracy, integration}` (the architecture both external reviewers converged on) | Implemented live, then **retracted same day**: end-to-end validation against the real, patched comparator on all 1,156 samples showed it measurably worse (MAE 1.164→1.614, r 0.118→0.082, FPR 9.0%→32.5%) — because it leans harder on `relationship_accuracy`, which Finding 2 shows is itself still broken. |
| 5a | Joint fix: Finding 2's narrow rule + Finding 3's exclusion, together | Better than #4 alone (MAE 1.446 vs.\ 1.614) but **still worse than the original buggy baseline** on every metric (baseline MAE 1.164). |
| 5b | Neutral-prior degradation (0.5 instead of 0.0/excluded) | Also worse in aggregate (MAE 1.471), but the first candidate to slightly beat baseline on the hard-case test specifically (1.050 vs.\ 1.066) — offset by getting much worse on easy cases. Not chased further (would not change the decision either way, per explicit decision-theoretic reasoning in the round-5 review). |

**Stopping rule invoked after round 5**, per convergent external review:
the tested *class* of intervention (binary include/exclude of a scoring
dimension with weight renormalization) failed to improve performance
under the evaluated benchmark and metrics in four distinct forms, not just
one miscalibrated trigger — treated as evidence against the mechanism,
not the specific parameters. This closes the investigation **with respect
to the tested intervention classes** — a narrower, more defensible claim
than declaring the underlying problem permanently unsolvable; a
differently-structured intervention (not binary include/exclude with
renormalization) remains an open question this investigation did not
address.

## 6. What's live in the source today

- `concept_extraction/extractor.py`: Finding 1's tokenization fix (merged).
- `graph_comparison/comparator.py` and `confidence_weighted_comparator.py`:
  a `coverage_validated: bool` diagnostic field, exposed via `to_dict()`,
  set `False` whenever `expected_concepts` isn't supplied. **Purely
  informational — does not change any score.**
- `conceptgrade/pipeline.py`'s `_compute_overall_score()`: unchanged
  formula (`knowledge = cov*0.45 + acc*0.35 + int*0.20`), with an inline
  comment documenting the retracted attempt and why.
- No change to `relationship_accuracy`'s zeroing logic (Finding 2 was
  never merged in any form).

## 7. What this does and doesn't mean for the deployed system

The production grade already discards the raw `kg_formula_score` in favor
of the LLM Verifier at blend weight $w=1.0$ (independently cross-validated
earlier in this project via leave-one-question-out CV on the blend
weight). **None of Findings 1-3 change the actual deployed grade** except
Finding 1, which does affect what the Verifier sees as KG evidence for the
106 previously-misclassified samples. Findings 2 and 3 affect only the
standalone ablation metric that isolates raw KG-grounding performance from
the Verifier's contribution.

## 8. Honest characterization of the causal story

Two independently diagnosed, evidenced scoring defects (vacuous coverage;
zeroed-by-design accuracy) appear to interact with the formula's fixed
weights (0.45/0.35/0.20) in a way where naive point-fixes to either or
both consistently underperform leaving both in place. One external
reviewer (Gemini) proposed a specific quantitative mechanism ("+0.45
cushion, −0.35 penalty, net +0.10 accidental regularization"); the other
(ChatGPT) pushed back that this is a plausible hypothesis, not something
the experiments actually isolate or prove — the experiments establish
*that* the fixes underperform, not a uniquely identified *why*. This
document adopts ChatGPT's more conservative framing as the one to carry
into any future paper text: "interacting deficiencies within a heuristic
score whose fixed weights implicitly assume comparable, independent
signal across dimensions" — not a proven cancellation mechanism.

## 9. Process note

Every round in this investigation followed the same discipline: diagnose
→ propose a fix → pre-commit success/failure criteria before running the
experiment → test offline against real cached data → report the result
exactly as found, including when it contradicted the hypothesis → retract
anything that failed its own validation, live-merged or not. Two findings
(the earlier ensemble-blend-weight result, and this session's Finding-3
exclude-and-renormalize fix) were retracted after failing validation
despite initially looking promising. No algorithmic modification was
retained unless it improved performance under the pre-defined validation
criteria.

The investigation's contribution is not limited to the findings
themselves — the process also validated the evaluation methodology it
ran on: candidates were chosen and success criteria defined *before*
each experiment, negative results were reported rather than
reframed, sensitivity/edge-case checks were run before trusting a result
(e.g., the empty-reference-concept exclusion check in round 4, the
tolerance-rounding false alarm in Finding 1's regression test), and live
changes were reverted within the same session when they failed their own
validation rather than left in place on the strength of prior confidence.
That discipline is what makes the final negative results credible rather
than merely asserted.

**Synthesis.** The investigation produced one validated implementation
improvement (Finding 1: the tokenization fix, merged and regression-
validated), two diagnosed but unresolved heuristic limitations (Findings
2 and 3: relationship-accuracy zeroing and coverage vacuity, both
root-caused and quantified but with every tested repair strategy
rejected by pre-committed evidence), and a reproducible evaluation
framework — cached data, regression scripts, and this document —
demonstrating specifically why five plausible-looking repair strategies
did not hold up. These results informed the final system design — the
investigation provides additional empirical support for the existing
design choice of relying primarily on the LLM Verifier rather than the
standalone raw KG score, though it does not by itself establish that the
deployed blend weight is globally optimal — while
preventing unsupported algorithmic changes from entering the pipeline.

---

## Review Questions

1. Does this summary honestly represent what was established across all
   five rounds, or does consolidating it into one document make anything
   look more (or less) conclusive than the individual rounds supported?
2. Section 8's causal framing — is "interacting deficiencies" adopted over
   Gemini's specific cancellation-mechanism hypothesis the right call for
   what eventually goes in a paper, or is there a middle-ground phrasing
   neither reviewer proposed?
3. Anything in the "what's live in the source" (§6) or "deployed system
   impact" (§7) sections that undersells or oversells the practical
   consequence of this investigation?
4. Is there anything about this closed investigation that should change
   how it's positioned when it moves into paper writing — e.g., as a
   dedicated failure-analysis subsection, an appendix, or folded into the
   existing ablation discussion?
