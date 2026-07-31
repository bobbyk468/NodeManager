# Algorithm Fix Review Request — Round 2 (Finding 3: concept_coverage vacuity)

**Instructions for the reviewer (please read first):**

Same context as the prior round (`ALGORITHM_FIX_REVIEW_REQUEST.md`) — you
are reviewing a proposed *code* fix, not paper text, before it's written.
Quick status update on that round: Finding 1 (tokenization bug) is now
fixed, merged, and regression-validated (106/106 expected flips, 0
unexpected regressions, 63/63 unit tests pass). Finding 2 (relationship
accuracy zeroing) is **held, not merged** — the pre-merge sanity check both
of you independently recommended surfaced a more fundamental problem
(Finding 3, below), and fixing Finding 2 before Finding 3 would have made
things worse, not better. This round is about Finding 3 specifically: is
the proposed fix direction sound, and what's the right first step.

---

## Finding 3 recap

`KnowledgeGraphComparator.compare()` (`graph_comparison/comparator.py`)
takes an optional `expected_concepts` argument — the question's
gold-standard concept set. When not supplied, it falls back to
`expected_set = student_graph.concept_ids`, i.e., the student's *own*
extracted concepts. **The only production call site**
(`conceptgrade/pipeline.py:476`) never supplies `expected_concepts`, so
this fallback is active on 100% of production comparisons.
`concept_coverage` is then "matched expected concepts / total expected
concepts," which is trivially 1.0 whenever the student extracts ≥1
concept — coverage of a set against itself.

Concrete proof: question "What is the difference between a circular linked
list and a basic linked list?"; student answer "They are passed by
reference because you want the function to change the pointer" (does not
address the question at all); human score 0.5/5; extractor finds one
tangential concept ("pointer"); `concept_coverage=1.0`.

Scope: 404/1,156 in-domain samples (35.0%) have this self-referential
`concept_coverage=1.0`; mostly invisible because most such answers are
coincidentally on-topic, but 18/1,156 (1.6%) are low-quality
(human_score≤2.0) answers getting undeserved full coverage credit.

## Candidate fix direction (not yet implemented — this is what needs review)

Now that Finding 1 has fixed the question→KG keyword-matching tokenization,
`_build_question_ontology()`'s internal `seed_ids` (concepts whose id/name/
description/aliases share a keyword with the question text) are a
plausible non-self-referential candidate for `expected_concepts` — they
depend only on the question, not on what the student wrote. Two
sub-questions the student has not resolved:

1. **Granularity**: use `seed_ids` directly (concepts keyword-matched to
   the question, currently ~1-5 concepts per question typically), or the
   1-hop-expanded subgraph `_build_question_ontology()` already computes
   for the LLM's extraction prompt context (broader, includes
   prerequisite/related concepts)? The narrow version risks being *too*
   strict (a correct answer using a related-but-not-directly-keyword-matched
   concept would show as "missing"); the broad version risks reintroducing
   some of the current leniency, just less severely.
2. **Circularity risk**: `seed_ids` comes from the *same* keyword-matching
   machinery that Finding 1 just fixed. If that machinery has other,
   undiscovered false-negative gaps (a concept genuinely relevant to the
   question but whose alias text doesn't share a keyword with the question
   text), wiring `expected_concepts` to it would silently penalize correct
   answers that use that concept — a new, different failure mode replacing
   the old vacuity, not necessarily better.

## Proposed validation approach (offline, zero new API calls)

Recompute `concept_coverage` for all 1,262 cached samples using
`seed_ids` (or the expanded subgraph) as `expected_concepts` instead of the
self-referential default, reusing already-extracted concepts (unchanged —
this only changes what coverage is measured against, not what was
extracted). Compare: does the new coverage correlate better with
human_score than the current vacuous version? Does it fix the 18
low-quality-but-vacuous-coverage cases without breaking the 386 genuinely-
correct cases that happen to currently show coverage=1.0 for the right
reasons?

---

## Review Questions

1. Is tying `expected_concepts` to the question-only `seed_ids` (or its
   1-hop expansion) the right general direction, or is there a cleaner
   source of per-question ground truth already available elsewhere in the
   codebase (e.g., a curated concept-per-question map, if one exists) that
   would avoid the circularity risk in point 2 above entirely?
2. Narrow `seed_ids` vs.\ broader 1-hop-expanded subgraph — which would you
   start with, and why? Is there a way to test both offline and let the
   data decide rather than picking by intuition?
3. How would you specifically test for the circularity risk (a KG-matching
   gap silently penalizing correct answers) using only cached data, before
   this reaches production?
4. Given this is now the third distinct issue found in the same scoring
   subsystem in one session, is there a broader class of similar
   "un-parameterized ground truth" bugs worth auditing for systematically
   (e.g., checking every place a function signature has an optional
   "expected X" parameter that's never actually supplied by the real
   caller), rather than continuing to fix these one at a time as they're
   inductively discovered?
5. Should Finding 2's fix be revisited once Finding 3 has a real fix, or
   does fixing Finding 3 first change what the *right* fix for Finding 2
   even looks like (e.g., "expected concept count ≤1" becomes well-defined
   for the first time once `expected_concepts` is real, rather than being
   a proxy for "student extracted ≤1 concept")?

---

## Student's Own Answers

**Q1 (source of ground truth).** I checked and there is no existing
curated concept-per-question map in this codebase — `expected_concepts`
has always been an optional parameter that nothing in the production path
populates. `seed_ids` from `_build_question_ontology()` is the only
question-derived (non-self-referential) signal that already exists; the
alternative would be authoring a new per-question gold concept list by
hand for all 50 Mohler questions (and the DigiKlausur/Kaggle sets), which
is accurate but a manual-authoring effort disconnected from the "fix a
diagnosed bug" scope of this pass — more like a dataset-annotation task
than a code fix.

**Q2 (granularity).** I lean toward testing both offline and comparing,
per my own review question — I don't have a strong prior. My weak
intuition is the 1-hop-expanded version, since `_build_question_ontology()`
already uses that broader set as the LLM's actual extraction context (the
LLM was shown those concepts as candidates), so a correct answer's
concepts should already be drawn from that same expanded pool by
construction — using the narrower `seed_ids` as the coverage target could
penalize the extractor for finding concepts it was explicitly prompted to
consider.

**Q3 (circularity test).** Offline check I have not yet run: for the
386 samples with `concept_coverage=1.0` today that are ALSO human-graded
correct (human_score≥4.0), recompute coverage against `seed_ids`/expanded-
subgraph and confirm none of them newly show as "missing expected
concepts" — if the fix causes previously-correct-and-correctly-scored
answers to newly look incomplete, that's direct evidence of a
keyword-matching gap being exposed rather than fixed.

**Q4 (systemic audit).** I have not done this audit. A quick grep for
`Optional[...] = None` parameters named `expected_*` or `gold_*` across
`graph_comparison/` and `concept_extraction/` would surface any siblings
to this pattern cheaply, offline, before assuming Finding 3 is the only
instance.

**Q5 (interaction with Finding 2).** I think fixing Finding 3 first is
necessary before Finding 2 can be correctly scoped at all — Finding 2's
"≤1 expected concept" trigger is currently a proxy for "≤1 *extracted*"
concept (since expected==extracted today), which is exactly the same
self-referential problem Finding 3 describes. Once `expected_concepts` is
real, the correct Finding 2 trigger becomes "≤1 concept in the real
expected set" — a cleaner, non-proxy condition — so I'd revisit Finding 2
only after Finding 3 lands, not in parallel.
