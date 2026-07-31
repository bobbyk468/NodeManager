# Algorithm Fix Review Request

**Instructions for the reviewer (please read first):**

You are acting as a PhD advisor / senior engineer reviewing a proposed
*code* fix, not a paper. The student (me) found two real weaknesses in the
KG-grounded scoring algorithm through inductive failure-mode analysis of
worst-case errors, has a candidate fix for each, and wants a critical review
of the fix plan **before** touching the live source — specifically: is the
diagnosis actually correct, is the proposed fix the right one, what could go
wrong, and what should be checked before and after applying it. This is a
research codebase (`ConceptGrade`, an automated short-answer-grading system
that grades against an explicit knowledge graph plus an LLM Verifier); the
findings below come from offline analysis of already-cached real prediction
data (Mohler ASAG benchmark, 1,262 real student responses), zero new API
calls. All numbers are from an internal automated verification script (350+
checks) that recomputes claims from raw cached data, not from memory.

Context: the student's papers on this project have already been through
several rounds of external review (by you, in prior sessions) and self-
correction, including retracting an overclaimed finding after a fair-control
check and disclosing a mixed statistical-model-sensitivity result. That
review process is currently on pause — **the student explicitly does not
want paper-writing feedback in this round**, only feedback on whether the
two code-level findings below are correctly diagnosed and the proposed fixes
are sound engineering, before any code is changed.

---

## 1. System Recap (brief)

ConceptGrade layer 2 (KG comparison) computes three sub-scores per response:
`concept_coverage`, `relationship_accuracy`, `integration_quality`, combined
into `knowledge = cov*0.45 + acc*0.35 + int*0.20`
(`conceptgrade/pipeline.py:_compute_overall_score`). This "knowledge" score
is 60% of the pre-Verifier `kg_formula_score`; depth (Bloom's/SOLO) is the
other 40%. Deployed production blends this with an LLM Verifier at weight
`w=1.0` (i.e., the final grade uses the Verifier, not the raw KG score,
confirmed as the correct choice by leave-one-question-out cross-validation
in prior work) — so these bugs affect a *diagnostic/intermediate* signal,
not the deployed grade directly. They matter because (a) the raw KG-only
score is reported and analyzed in the paper as a standalone finding
("KG-grounding is dramatically worse than baseline in isolation, MAE
+86.9%"), and (b) fixing structural bugs in it is a prerequisite to ever
testing whether a *better* KG-grounding design could close some of that gap
mechanistically, rather than only being rescued by the Verifier.

## 2. Finding 1 — domain-match tokenization bug (clear bug, high confidence)

**Code location**: `concept_extraction/extractor.py`,
`_build_question_ontology()`.

**Bug**: the question text is tokenized via
`question.lower().split()` — no punctuation stripping. For "What is a
queue?", the token `"queue?"` (with trailing `?`) is checked via substring
match against KG concept id/name/description/alias text. `"queue?"` never
appears as a substring of `"queue"`'s KG text, so it fails to match even
though `"queue"` obviously would. Result: `seed_ids = []` →
`domain_match_score = 0.0` → `StudentConceptGraph.out_of_kg_domain` property
(`domain_match_score < 0.05`) evaluates `True` → the comparator's
OUT_OF_KG_DOMAIN short-circuit
(`graph_comparison/confidence_weighted_comparator.py`) returns an
all-zero score, discarding whatever the (otherwise correct) concept
extraction found.

**Measured scope**: 106/1,262 real Mohler samples (8.4%), exactly 4
question IDs, all matching the "What is a `<concept>`?" pattern: E08.Q01
("What is a stack?"), E09.Q01 & E12.Q06 ("What is a queue?"), E10.Q01
("What is a tree?").

**Validated impact of the fix** (offline, re-running the real
`ConfidenceWeightedComparator.compare()` on unchanged extracted concepts
with corrected tokenization — not simulated):

| Scope | kg_formula MAE before | after fix | Change |
|---|---|---|---|
| 106 affected samples | 3.9623 | 1.3821 | **+65.1%**, now *beats* C_LLM's 1.7264 on the same samples |
| Full 1,262-sample dataset | 2.3968 | 2.2763 | **+5.03%** (Wilcoxon one-tailed $p<0.0001$) |

Pearson $r$ on the full dataset moves slightly the *wrong* way (0.4710 →
0.4521) — disclosed honestly, not hidden; a small, non-representative
(8.4%) slice moving doesn't have to help correlation even while it helps
MAE.

**Proposed fix**: tokenize with a word-boundary regex that strips
punctuation, e.g. `re.findall(r"[a-z']+", question.lower())`, filtered to
length > 3 as the original does. Regression-validated against all 1,262
cached `domain_match_score` values (tolerance 5e-4, appropriate for the
existing 4-decimal rounding in `self_consistent_extractor.py`'s
multi-run merge step) — reproduction matches cache exactly (1262/1262) both
before and after the fix is conceptually applied (the fix only changes
behavior on the 106 affected samples, where the *old* tokenization was
simply wrong).

**Not yet applied to the live source.**

## 3. Finding 2 — relationship_accuracy=0.0-by-design penalizes structurally-relationship-free correct answers (design tradeoff with a real side effect, lower confidence on "the right fix")

**Code location**: `graph_comparison/comparator.py`,
`_compute_relationship_accuracy()`, documented inline as "Framework Fix #15
(2026-06-15)": when a student extracts zero relationships, the function
returns `0.0` accuracy (previously it returned `1.0`, "vacuously perfect,"
which gave shallow keyword-dump answers a free accuracy credit — the `0.0`
default was a deliberate, documented correction to that problem).

**Side effect discovered**: a large class of genuinely correct answers is
*structurally incapable* of expressing a scored relationship, and gets the
same `0.0` as a keyword dump:

- **Single-concept factual answers.** E.g., "What is the height of a
  tree?" → "The height of a tree is the number of nodes on the longest path
  from the root to a leaf." (`human_score=5.0`) extracts one concept
  (`tree_height`), zero relationships, `relationship_accuracy=0.0`.
- **Comparative / definitional / enumerative questions**, regardless of how
  many concepts get extracted. E.g., "What are the two main functions
  defined by a queue?" → "The two main functions are enqueue and dequeue."
  (`human_score=5.0`) extracts *three* concepts (`enqueue`, `dequeue`,
  `queue`) but still zero relationships — enumerating two operations isn't
  the same as stating a KG-schema typed relationship (USES, CAUSES, etc.)
  between them, so there is nothing correct to extract. Traced across the
  full dataset: 30 such "multi-concept, zero-relationship" cases cluster
  entirely on 14 distinct questions, all comparative/definitional/
  enumerative in phrasing (e.g. "What are the similarities between
  iteration and recursion?", "What is the main difference between strings
  declared using type string versus...?", "What is the advantage of linked
  lists over arrays?").

**Measured scope** (in-domain samples only, n=1,156, i.e. excluding
Finding 1's cases): 246/1,156 (21.3%) extract zero relationships; 216 of
those (87.8%) have ≤1 extracted concept (structural non-applicability by
the simplest measure); 180/246 (73.2%) are human-graded correct/near-correct
(human_score≥4.0). On that correct-answer, zero-relationship subgroup:
kg_score MAE=3.044 vs. C_LLM MAE=0.906 — the single largest MAE gap of any
subgroup found in this analysis. The comparative-question refinement above
means the true structurally-affected count is larger than 216, but has not
been precisely re-measured by question type (only qualitatively confirmed
on the 30 multi-concept cases).

**Candidate fix, estimated (not exactly validated) impact**: when the
*expected* concept set has ≤1 member (i.e., a relationship is not
achievable in principle for this question), exclude the accuracy dimension
from `knowledge = cov*0.45 + acc*0.35 + int*0.20` rather than zeroing it —
renormalize to `knowledge = cov*(0.45/0.65) + int*(0.20/0.65)`. On the
216-sample subgroup this is estimated to improve kg_formula MAE from 2.688
to ≈2.140 (still well behind C_LLM's 1.153 on the same subgroup) — this
estimate assumes `misc_penalty=0` and holds depth constant, because
per-sample Bloom's/SOLO/misconception values aren't in the cached analysis
file, so it is directional, not an exact pipeline re-run like Finding 1's
validation.

**Two open design questions the student has not resolved:**

1. **What should trigger the exclusion?** "≤1 expected concept" is a clean,
   simple rule but (per the comparative-question refinement) undercounts
   real cases. A question-type classifier (definitional/comparative/
   enumerative vs. relational) would catch more cases but is a new
   component with its own error surface, and risks becoming exactly the
   kind of hand-tuned-to-the-eval-set fix this project's methodology has
   been careful to avoid (cf. the retracted ensemble-blend finding, caught
   by leave-one-question-out cross-validation).
2. **Is "exclude and renormalize" the right response at all**, vs. leaving
   `0.0` as a legitimate score component and instead only changing how it's
   *interpreted downstream* (e.g., surfacing "relationship: not applicable"
   in feedback rather than "relationship: 0/1 correct")? The current
   `_compute_relationship_accuracy` docstring makes clear the `0.0` default
   was already a deliberate fix for a prior bug (rewarding keyword dumps)
   — changing it again risks reopening that exact problem for a different
   subset of cases if the "not applicable" detection is imperfect.

## 4. What the student proposes to do next (pending this review)

1. Fix Finding 1 in the live source (`extractor.py` tokenization) — high
   confidence this is a strict improvement, low risk, already validated.
2. For Finding 2, start with the *narrow, high-confidence* version only:
   exclude relationship_accuracy when the expected/extracted concept count
   is ≤1 (the clearly structural case), leave the comparative-question
   refinement as documented-but-not-implemented until it can be validated
   the same rigorous way (real code re-run, not an estimate) — to avoid
   shipping a fix broader than what's actually been validated.
3. Re-run the full offline evaluation pipeline (ablation, cross-dataset
   significance, LOOCV) after both code changes to get exact (not
   estimated) numbers, and re-run `verify_all_paper_claims.py` to confirm
   nothing downstream silently broke.
4. Explicitly NOT touch paper text in this pass — that will be a separate,
   later step once the fixes are validated end-to-end.

## Review Questions

1. Is Finding 1's diagnosis and fix sound? Any edge case the tokenization
   regex (`[a-z']+`, length>3) might mishandle that `.split()` didn't (or
   vice versa)?
2. For Finding 2 — do you agree with starting narrow (≤1-concept rule only)
   and leaving the question-type refinement for later, or is that overly
   conservative given the evidence already gathered?
3. Is there a risk that "fixing" relationship_accuracy's zero-default for
   structurally-inapplicable cases reintroduces the keyword-dump-reward
   problem the `0.0` default was originally created to prevent? How would
   you test for that specifically?
4. What is the single most important validation step before considering
   either fix "done," beyond re-running the existing ablation/significance
   scripts?
5. Anything about this two-finding failure-mode analysis itself (the
   sampling method, the inductive-not-predetermined-taxonomy approach, or
   the offline-estimate caveat on Finding 2) that reads as methodologically
   weak, independent of whether the fixes themselves are correct?

---

## Student's Own Answers (for the reviewer to check, not just prompt)

**Q1 (tokenization edge cases).** The regex `[a-z']+` (applied after
`.lower()`) will keep apostrophes (so "don't" tokenizes as one word, matching
prior behavior reasonably) and split on all other punctuation/digits/
whitespace. One risk: hyphenated compound terms in the KG (e.g. if any
concept id or alias contains a hyphen, like "big-O" or "depth-first") would
now split into two tokens where `.split()` might have kept a
punctuation-attached variant as a single non-matching token anyway — net
effect is neutral-to-positive (more tokens to try matching, never fewer),
so I don't think this introduces a new failure mode, only removes the
`?`/`.`/`,`-at-the-end failure. I have not exhaustively checked whether any
KG concept alias itself contains a hyphen or apostrophe that could match
*differently* under the new tokenization (e.g. a spurious match that wasn't
there before) — this is worth an explicit check before merging: diff
`domain_match_score` and `out_of_kg_domain` for all 1,262 samples under old
vs. new tokenization, not just confirm the 106 known cases improve.

**Q2 (scope of Finding 2's fix).** I lean toward starting narrow (≤1-concept
rule) because it's the only version I've validated against real code
behavior at all rigorously (still only an estimate, per the caveat above,
but grounded in cached real scores, not a hypothetical). The
comparative-question rule would require either (a) a new classifier with
its own precision/recall to evaluate, or (b) a hand-authored keyword list
("similarities between," "advantage of," "difference between") that is a
textbook case of overfitting to the exact 14 questions observed in a
1,262-sample, 50-question dataset — the kind of eval-set-shaped fix this
project's methodology has explicitly guarded against elsewhere (LOOCV on
the ensemble-blend retraction). I'd want a held-out or synthetic check
(e.g., invented comparative questions not in Mohler) before trusting a
keyword-list version, which is more work than I've committed to doing
"before touching code" in this pass.

**Q3 (regression risk on the keyword-dump problem).** The specific risk is:
if the "structurally inapplicable" detection (≤1 expected concept) is ever
wrong — e.g., a question the system judges as single-concept but a strong
answer legitimately could relate that concept to something outside the
strict expected set — a keyword-dump answer with exactly 1 matched concept
would get the "excused" treatment (accuracy dimension dropped, not zeroed)
even though it demonstrated nothing. I'd test this by checking, among
*already-cached* low-quality answers (human_score≤2) that happen to have
≤1 expected concept, whether the fix changes their kg_score materially
upward — if it does, that is direct evidence of the regression the Q3
concern describes, computable offline with no new API calls, and I have
NOT yet run this specific check.

**Q4 (most important validation step).** Beyond re-running the existing
ablation/significance suite: recomputing the full-dataset kg_formula MAE
and correlation with BOTH fixes applied together (not just each fix's
isolated subgroup impact, which is what's measured so far) — the two fixes
touch overlapping machinery (both flow through `_compute_overall_score`'s
knowledge term) and I have not checked whether their combined effect is
additive, sub-additive, or interacts in some unexpected way. This is fully
offline and should be done before any paper or deployment decision.

**Q5 (methodology self-critique).** The 60-case sample was selected purely
by `|kg_score - human_score|` (worst-first), which is good for finding
failure modes but means I have no denominator-matched control group of
*correctly-scored* cases with the same structural properties (single
concept, comparative question type) to confirm the pattern is specific to
the worst-case sample and not just a base rate across the whole dataset.
I partially addressed this for Finding 2 by computing dataset-wide
(not just sample-restricted) counts — 246/1,156, not just "cases found in
the 60-sample review" — but I did not do the equivalent broader check for
Finding 1 beyond the exact-match regression test, and I did not check
whether single-concept/comparative-question cases that *aren't* in the
worst-60 also show the same MAE pattern (i.e., is the effect uniform across
that subgroup, or concentrated in a worse-scoring tail within it — the
216-sample subgroup MAE numbers already answer this at the aggregate level,
but I haven't looked at the distribution shape).
