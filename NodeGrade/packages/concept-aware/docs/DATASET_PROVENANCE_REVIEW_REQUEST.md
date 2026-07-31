# Dataset Provenance Review Request — DigiKlausur (resolved) and Kaggle ASAG (unresolved)

**Instructions for the reviewer (please read first):**

Context: an earlier review round (`docs/RESEARCH_REVIEW_REQUEST.md`, §9)
flagged "DigiKlausur and Kaggle ASAG provenance were never independently
forensically verified the way the fabricated Mohler fixture was caught and
Mohler's real replacement was verified" as an open gap. Given this
project's history — its headline results were once computed against a
fabricated 120-sample fixture, caught mid-project via a docstring
self-admission — this gap was treated as serious enough to investigate
directly rather than leave open. The user explicitly rejected using
GPT/Gemini to *generate* synthetic test data as a way to address this
(correctly, in the student's and this document's view — that would
compound rather than resolve the underlying provenance concern). Instead,
real forensic web verification was attempted for both datasets, using the
same standard applied to Mohler's real replacement (`data/mohler_real/PROVENANCE.md`).

**One result is resolved and positive. The other could not be resolved and
needs your input on how to proceed.**

---

## DigiKlausur — CONFIRMED real, forensically verified

Fetched the actual public source directly: `raw.githubusercontent.com/DigiKlausur/ASAG-Dataset/master/asag_dataset.csv`
(repo: [DigiKlausur/ASAG-Dataset](https://github.com/DigiKlausur/ASAG-Dataset),
MPL-2.0 license, described as 38 graduate students, University of Applied
Sciences Bonn-Rhein-Sieg, neural networks course, 17 questions, 646
total responses, graded 0/1/2 by a single human judge).

The first row of the real CSV is **character-for-character identical** to
`data/digiklausur_dataset.json`'s first entry — question text, student
answer, and reference answer all match verbatim, and the source's
`grades_round=2` matches the cached `human_score_raw=2` field exactly (the
cached `human_score=5.0` is evidently a normalized 0-5 mapping of the
0/1/2 raw scale, consistent with how the rest of this codebase treats
scores). **Status: as solid as verification gets without contacting the
original researchers directly.**

## Kaggle ASAG — UNVERIFIED, real concern, not resolved

**What's missing**: unlike Mohler (`data/mohler_real/PROVENANCE.md` + a
loader script citing the exact HuggingFace mirror) and now-verified
DigiKlausur, there is **no file anywhere in this codebase** recording
where `data/kaggle_asag_dataset.json` (473 samples, later deduplicated to
368 for the paper's headline numbers) actually came from — no README, no
download script with a URL, no dataset slug, nothing.

**What was tried**:
1. Searched for the exact cached questions ("What is respiration in
   plants?", "What is a habitat?") and reference-answer text verbatim —
   no exact public match found.
2. Found a Kaggle dataset with a highly similar *description* (primary-
   school science, student/reference/teacher-mark schema) —
   [mubeenfurqanahmed/automatic-short-answer-grading-dataset](https://www.kaggle.com/datasets/mubeenfurqanahmed/automatic-short-answer-grading-dataset)
   — but it is **explicitly documented as synthetically generated using
   ChatGPT and Gemini**, and its stated size (4,000+ records) doesn't
   match the cached 473, so it is probably not literally this dataset —
   though that doesn't rule out a different, also-unverified, possibly
   non-real source.
3. Checked `nkazi`'s HuggingFace SciEntsBank mirror (the same curator
   already trusted for the verified real Mohler replacement) — real
   dataset, but its schema (categorical 5-way labels: correct/
   contradictory/partial/irrelevant/non-domain) doesn't match the cached
   data's numeric `human_score` field, and no topic/text match either.
4. Could not browse Kaggle's dataset pages directly (JS-rendered, tool
   access limited) to check candidate datasets more thoroughly.

**Net result**: genuinely unresolved. Not confirmed real, not confirmed
fabricated. The one concrete lead found (a topically-similar but
explicitly-synthetic dataset) is circumstantial, not conclusive, given the
size mismatch.

**Why this matters beyond box-checking**: Kaggle ASAG is used throughout
both papers as one of three "real" cross-dataset validation sets, and its
null result (no significant self-consistency or ConceptGrade benefit) is
currently narrated as a *positive, mechanistically-predicted finding* —
"concept extraction returns empty KG matches for 100% of samples,
consistent with the domain boundary between elementary science and a
Data-Structures KG" (§8 of the earlier review doc, echoed in both papers).
If the underlying student answers or scores turn out to be synthetic
rather than genuine human work, that specific narrative (a clean,
architecturally-predicted null result) would need re-examination — a
synthetic dataset's "null result" doesn't carry the same evidentiary
weight as a real one's.

---

## Review Questions

1. Given the search avenues already tried, are there other forensic
   techniques worth attempting before escalating this (e.g., specific
   phrase-matching strategies, checking Kaggle's dataset API/metadata
   endpoints directly rather than via search, reverse-searching a
   distinctive reference-answer sentence rather than a question)?
2. If the source genuinely cannot be identified through further search,
   what's the right disposition for the paper: retract Kaggle ASAG
   entirely, keep it but explicitly label its provenance as unverified
   (parallel to how the fabricated-Mohler retraction was handled — full
   disclosure rather than quiet removal), or something else?
3. Does an unresolved provenance question change how much weight the
   "architecturally-predicted null result" narrative for Kaggle ASAG can
   carry, even if the underlying data turns out to be real but just
   unidentified?
4. Is there a meaningfully different bar for provenance verification
   given Kaggle ASAG was never used for a *positive* headline claim (it's
   a null result throughout) versus Mohler, which carried the paper's
   primary positive findings — or should the same rigor apply regardless
   of which direction a dataset's result points?

---

## Student's Own Answers

**Q1.** I don't have a clearly better technique in reserve — I tried
exact-text search, description-based search, and checking a specific
already-trusted curator's alternative datasets. The main gap is that I
can't browse Kaggle's site directly (JS-rendered pages return no content
through my tools) and don't have a way to query Kaggle's dataset search
API. If the original download happened through a Kaggle account, checking
that account's download history would resolve this immediately and is
faster than any further search-based guessing.

**Q2.** My instinct is disclosure over removal, consistent with how this
project handled the original Mohler fabrication — but I recognize an
important difference: the Mohler incident had positive proof of
fabrication (a docstring self-admission), while this is an absence of
proof of authenticity, not evidence of fabrication. I don't think those
should be treated identically. Retracting a dataset because I *couldn't
verify* it, absent any actual sign it's fake, risks discarding real data
out of excess caution — but presenting it as equivalently verified to
Mohler and DigiKlausur when it isn't would be dishonest by omission. I'd
lean toward keeping it with an explicit, prominent provenance caveat
rather than retracting outright, but I'm not fully confident that's the
right call.

**Q3.** I think it weakens the narrative's evidentiary weight somewhat but
doesn't necessarily invalidate it — the mechanistic explanation (concept
extraction finds 100% empty KG matches on this data) is independently
verifiable from the extraction logs regardless of where the questions
originally came from; what's uncertain is whether the *student answers and
human scores* are genuine, not whether the domain-mismatch mechanism is
real. I'd want to phrase this distinction carefully rather than let the
provenance question quietly undermine a claim that's actually separately
supported.

**Q4.** I lean toward the same rigor should apply regardless of result
direction — a null result built on questionable data is still an
unreliable claim, even if it happens to be the "boring," expected
direction. I would be suspicious of my own reasoning if I found myself
wanting a lower verification bar specifically because this dataset's
result already looks the way I want it to look.
