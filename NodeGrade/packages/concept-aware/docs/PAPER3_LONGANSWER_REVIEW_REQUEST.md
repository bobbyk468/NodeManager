# Paper 3 (Long-Answer Grading) Review Request — Retraction + First Honest Pilot

**Instructions for the reviewer (please read first):**

Context: this project's headline short-answer results were once computed
against a fabricated 120-sample fixture, caught mid-project via a
docstring self-admission and fully retracted (see
`REPRODUCIBILITY.md`, "CRITICAL: the 'Mohler dataset' was fabricated").
That incident set the project's standard: retract rather than quietly
fix, disclose rather than delete, and treat null/negative results with
the same rigor as positive ones.

This document covers a **second, independently-discovered incident of the
same shape**, found while investigating whether ConceptGrade (a
short-answer KG-grounded grading system) could be extended to long-form
(essay-style) answers — a new, separate paper track internally called
"Paper 3." Please review both the retraction reasoning and the
replacement pilot's methodology, and answer the questions at the end.
Push back on anything that looks like it's repeating the same mistake in
a new form, or overcorrecting into a different one.

---

## Part 1 — What was found and retracted

The codebase already contained a full long-answer grading (LAG) system
(`conceptgrade/lag_pipeline.py` — segmentation, wave-parallel scoring,
cross-paragraph integration, a 3-persona uncertainty check) with a
"measured" headline result: **Pearson r = 0.967** on a 20-sample
hand-crafted benchmark (`data/lag_evaluation_results.json`).

Audited the same way the Mohler fixture was audited, and found three
independent, each individually disqualifying, problems:

1. **No provenance.** The 20-sample benchmark (`data/lag_benchmark.json`)
   is a flat JSON list of `{question, reference_answer, student_answer,
   human_score}` records with no generation script anywhere in git
   history, no annotator identity, no rubric. It appears fully-formed in
   the same commit that added the pipeline scoring it.
2. **Domain mismatch.** The benchmark spans 5 topics (4 samples each):
   `binary_search_tree`, `hash_table`, `virtual_memory`, `tcp_vs_udp`,
   `garbage_collection`. Checked directly against the actual 101-concept
   Data Structures knowledge graph (`data/ds_knowledge_graph.json`) used
   everywhere else in this project: only 2 of the 5 topics have any
   matching concept ID. The other 3 — 12 of 20 samples, 60% — match
   **zero** KG concepts, meaning the deterministic KG-comparison layer
   (the system's core claimed advantage over a plain LLM grader) was
   structurally inert for most of the benchmark.
3. **Test-set leakage.** A same-day follow-up commit
   ("Fix LAG over-estimation bias") shows explicit before/after metrics
   from directly editing the verifier's prompt (adding score anchors)
   against this exact 20-sample set, then wiring the tuned prompt in as
   the default before the final r=0.967 was reported — i.e., the system
   was calibrated on its own test set.

Full writeup: `REPRODUCIBILITY.md`, "CRITICAL: the LAG (long-answer)
evaluation is retracted." The old files were kept (not deleted), with
retraction notices added to both `REPRODUCIBILITY.md` and
`docs/ConceptGrade_LongAnswer_Extension.md`.

---

## Part 2 — The replacement: a small, honestly-disclosed pilot

To avoid repeating the leakage mistake, a new pilot (n=8) was built and
run with the config decided **before** any result was seen, and never
retuned afterward:

- **`build_paper3_pilot_set.py`** — 8 answers, explicitly disclosed as
  author-written (not real students, not LLM-generated), multi-paragraph
  (71–258 words), spanning 6 topics. Every topic checked against the real
  KG for coverage before inclusion (the retracted set's exact failure
  point). 4 samples contain one deliberately embedded misconception from
  the *existing, already-validated* short-answer misconception taxonomy
  (DS-TREE-01, DS-HASH-01, DS-SORT-01, DS-STACK-01); 4 are clean, spanning
  deliberately shallow to deliberately excellent. Each sample carries an
  author-intended target score (0–5) assigned before running anything.
- **`run_paper3_pilot.py`** — runs all 8 through the unmodified
  `LongAnswerPipeline`, config fixed in the script: `model=gemini-2.5-flash,
  use_sure=True, use_cross_para=True`. Live API calls, ~116 seconds total
  for 8 samples. Raw output:
  `data/paper3_longanswer/pilot_run_v1_results.json`.

### Results (measured, not projected)

| id | target | actual | diff | misconception designed? | detected? |
|---|---|---|---|---|---|
| recursion_excellent | 4.75 | 3.96 | −0.79 | no | — |
| queue_good_shallow_depth | 3.25 | 3.46 | +0.21 | no | — |
| linked_list_surface_level | 2.00 | 3.68 | +1.68 | no | — |
| bst_tree_conflation | 2.25 | 3.35 | +1.10 | yes | **no** |
| hash_table_complexity_misconception | 3.25 | 3.21 | −0.04 | yes | **no** |
| sorting_quicksort_mergesort_misconception | 3.00 | 3.88 | +0.88 | yes | **no** |
| stack_queue_conflation_longform | 1.25 | 2.40 | +1.15 | yes | yes (2 flagged) |
| dynamic_array_excellent | 4.75 | 3.44 | −1.31 | no | — |

**MAE = 0.895, bias = +0.360, Pearson r = 0.592** (n=8, explicitly not
claimed as a stable estimate). **Misconception recall: 1/4 (25%)** — only
the misconception stated as one direct, literal claim was caught; the 3
requiring the reader to connect two claims stated in different parts of
the same answer were all missed. Genuinely excellent long answers were
under-scored (up to −1.31); a critical-misconception answer outscored an
honest shallow one.

This matches a failure mode the system's own (unvalidated-until-now)
design doc predicted in March 2026 ("subtle errors buried in the middle
paragraphs may be overshadowed by correct framing... leading to
under-detection") — now measured rather than merely projected.

Full writeup: `REPRODUCIBILITY.md`, "Paper 3 pilot: long-answer grading."

---

## Review Questions

1. **Is the retraction justified, or is this an overcorrection?** Given
   real API calls were made (this isn't literally fabricated the way the
   Mohler fixture's data was invented outright), is it right to treat
   test-set leakage + domain mismatch + missing provenance as
   disqualifying in the same way as outright fabrication, or does that
   conflate a methodology error with data fraud in a way that's unfair to
   whatever process produced the original benchmark?

2. **Is n=8, author-written, single-run pilot data defensible at all** as
   the basis for *any* reported finding (even one explicitly labeled
   "illustrative, not validation"), or does presenting specific numbers
   (MAE=0.895, r=0.592) risk the reader treating hedged numbers as real
   ones regardless of the caveats — i.e., is disclosure alone sufficient,
   or does responsible reporting require withholding numbers this small
   entirely and describing findings only qualitatively?

3. **Selection bias in the pilot's own design**: these 8 answers were
   written by the same person who designed the pipeline being tested, with
   full knowledge of its architecture and known weak points (e.g.,
   deliberately burying misconceptions non-adjacent to related correct
   content, specifically because that was predicted as a weak point).
   Does hand-crafting adversarial-ish examples targeting a predicted
   failure mode, then reporting that the failure mode occurs, constitute
   fair testing, or does it risk the inverse problem — an unrepresentative
   pilot that's *harder* than real long-form answers would typically be,
   making the system look worse than it would on a realistic distribution?

4. **What should Paper 3 actually claim, given this starting point?** Is
   "the long-answer extension has a specific, mechanistically-identified
   weakness in non-adjacent misconception detection" a legitimate,
   sufficient finding for a paper track on its own, or does a paper need
   to also attempt and report on a fix before this is publishable, rather
   than stopping at "here's what's broken and why"?

5. **Anything about the retracted benchmark's disposition** — kept
   in-repo with retraction notices, not deleted — that should be handled
   differently, given this is the second such incident in the same
   project?

---

## Student's Own Answers

**Q1.** I think the disqualification is justified but for a narrower
reason than "fabrication-equivalent" — the decisive problem isn't that I
can't prove where the data came from (that alone would warrant an
"unverified" label, not full retraction, per how Kaggle ASAG's ambiguous
provenance was handled elsewhere in this project). It's specifically the
test-set leakage: regardless of how the benchmark was created, tuning a
prompt against it and then reporting that same benchmark's score is
textbook invalid regardless of data provenance. I'd keep those two
problems analytically separate — leakage alone is sufficient grounds for
retraction; provenance alone might only have warranted a caveat.

**Q2.** I lean toward disclosure-with-numbers over withholding, mirroring
how this project handled Kaggle ASAG's uncertain provenance (labeled, not
hidden) — but I'm genuinely unsure this is right at n=8. My worry is that
a specific number like "Pearson r=0.592" has a way of getting cited later
stripped of its caveats, especially by anyone skimming rather than reading
the methodology section. I'd want a second opinion on whether the
qualitative finding (1/4 misconceptions caught, specific mechanism
identified) is actually the load-bearing result and the quantitative
metrics are decoration that should be cut entirely, not just caveated.

**Q3.** I think this is a real and correctly-identified risk, and I don't
think I've resolved it. I designed the misconceptions specifically to be
non-adjacent to the destabilizing correct content *because the design doc
already predicted that as a weak point* — so in one sense I was testing a
predicted hypothesis, which is legitimate, but in another sense I stacked
the deck. A fairer test would need misconceptions placed at random
positions in independently-written long answers, not ones I placed
deliberately. I don't currently have a way to source "independently
written" long CS answers without either using real students (not
available to me) or LLM-generated ones (which reintroduces a different
provenance problem this project has already flagged elsewhere as
something the user explicitly rejected as a fix for provenance gaps).

**Q4.** My instinct is that "here's what's broken and why, measured
rather than assumed" is a legitimate contribution on its own — negative
results with a mechanistic explanation are exactly what this project's
short-answer paper (Paper 1) already argues is undervalued, and it would
be inconsistent to hold Paper 3 to a different standard. But I recognize
I might be reaching for this conclusion partly because attempting a fix
is more work than I've done so far, and I'd want that checked rather than
taken at face value.

**Q5.** No strong opinion — I followed the established convention
(retract-not-delete, explicit notice at the point of use) because it
worked before, not because I independently re-derived that it's the right
call here too. Open to being told a different disposition fits better the
second time this has happened in one project.

---

## Resolution (GPT review received, 2026-07-31)

**Scores given:** Scientific reasoning 10/10, Methodological rigor
9.8/10, Research integrity 10/10, Reviewer readiness 9.7/10.

**Verdict on each question:**

- **Q1 (retraction justified?)** Yes, but the three problems should not
  be treated as equally disqualifying. Test-set leakage alone is
  sufficient to retract the performance claim. Domain mismatch
  independently supports retraction. Missing provenance, on its own,
  should not — per this project's own Verified/Unverified/Invalid
  standard (established for Kaggle ASAG), it belongs in "Unverified,"
  not "Invalid." Applying a stricter bar here than was applied to Kaggle
  ASAG would be inconsistent.
- **Q2 (n=8 defensible?)** Yes for mechanistic claims, no for performance
  estimates — MAE/r/bias are statistically meaningless as performance
  estimates at this n and should be presented as descriptive, not
  inferential.
- **Q3 (selection bias from targeting a predicted weakness?)** Yes, but
  not necessarily a flaw — it depends on the claim. Testing a specific
  predicted mechanism is a legitimate, different experiment from
  estimating prevalence on representative answers; the pilot should be
  explicitly labeled "hypothesis-driven stress testing," not
  "representative evaluation."
- **Q4 (does Paper 3 need a fix before publishing?)** No — a negative
  result with a demonstrated (even if preliminary) mechanism is
  sufficient. The claim should be phrased at "preliminary evidence"
  strength, not "demonstrates"/"establishes."
- **Q5 (retracted benchmark disposition)** Current retract-not-delete
  policy confirmed as correct, no change needed.
- **Additional concern raised (not in the original questions):** the same
  person designed the pipeline, wrote the answers, and set the target
  scores — this coupling should be explicitly named as defining the
  pilot's scope ("developer-authored functional validation"), not
  treated as invalidating it.

**Changes made in response (all in this same pass):**

1. `REPRODUCIBILITY.md`'s retraction section rewritten to separate the
   three problems by disqualifying weight (leakage = sufficient alone;
   domain mismatch = independently serious; provenance = Unverified, not
   Invalid), explicitly citing the Kaggle ASAG consistency argument.
2. The pilot's "Results" section renamed to "Illustrative Pilot
   Observations (Not Performance Estimates)" with an explicit "no
   inferential statistical claims are made" disclaimer.
3. Pilot reframed throughout as "hypothesis-driven stress testing of a
   predicted failure mode," not a representative evaluation — in
   `REPRODUCIBILITY.md` and in `build_paper3_pilot_set.py`'s docstring
   and JSON `meta.purpose`.
4. The headline claim rewritten to GPT's exact suggested wording:
   *"The pilot provides preliminary evidence that distributed
   misconceptions... are harder for the current architecture to detect
   than explicit, locally-stated misconceptions"* — replacing stronger
   causal language.
5. Added an explicit scope-limiting disclosure — "developer-authored
   functional validation, not an estimate of educational grading
   performance" — to both `REPRODUCIBILITY.md` and the pilot script's
   provenance field.
6. Confirmed: no fix attempted before publication is required; retained
   files kept in place (no deletions).
