# Development & Testing Self-Assessment: Questions, Our Answers, and Offline Data Status

**Purpose of this document (for the reviewer):** Following your feedback on `RESEARCH_REVIEW_REQUEST.md`, we drilled into every aspect of development and testing with hard questions, answered them honestly, and — for every answer — stated explicitly whether it is backed by data we already have (offline, zero additional cost to verify) or requires work we have not done. Please read our answers and offline-status claims critically. Where you think an answer is incomplete, wrong, or where the "offline" claim doesn't actually support the answer, say so directly.

---

## Part A: Development Questions

### D1. Why `gemini-2.5-flash` and not a frontier model (GPT-4-class, Claude)?
**Our answer:** Deliberate design choice — using the identical model for both C_LLM and ConceptGrade isolates model capability as a confound, so any measured gap is attributable to the pipeline architecture, not model quality.
**Offline status:** N/A — no data exists on other models. This is a genuine, undone resource item, not something we can answer from cached data.

### D2. Was the Verifier's prompt iterated against this exact evaluation data during development?
**Our answer:** Yes. This is disclosed in the paper as a soft leakage risk we have not ruled out — distinct from classical train/test leakage (the Verifier has no fine-tuning step, confirmed by direct code inspection), but prompt engineering against the same data it's later evaluated on is a real, softer form of the same concern.
**Offline status:** We know *that* this happened (development history), but we have not quantified *how much* it affects the reported numbers, and doing so would require either a frozen-prompt replication on fresh data or a documented history of prompt versions we don't currently have organized.

### D3. Why these specific weights in the score-synthesis formula (0.45/0.35/0.20 coverage/accuracy/integration; 0.55/0.45 depth; 0.60/0.40 knowledge/depth; 0.05/0.95 KG-formula/holistic)?
**Our answer:** These are the values currently in the codebase. Their original derivation predates this session's real-data correction work and traces back to design decisions made when the project was still using the (later discovered to be fabricated) fixture. They have not been re-derived or re-tuned on real data.
**Offline status:** Partially addressed. We ran a `kg_weight` sensitivity sweep (the 0.05/0.95 split specifically) on real cached data at zero cost — found the deployed default is *not* MAE-optimal for that sub-component, though even the optimum stays far worse than baseline, so it doesn't change the architectural conclusion. The other weights (0.45/0.35/0.20, 0.55/0.45, 0.60/0.40) have not been swept on real data.

### D4. Why K=7 and temperature=0.7 for self-consistency ensembling?
**Our answer:** Copied directly from the already-validated call-budget-matched C_LLM×7 experiment's design, specifically to avoid introducing a new hyperparameter that could be tuned (even implicitly) on the evaluation data.
**Offline status:** Fully available. We additionally ran a K-subset check (K=3, K=5 slices of the same already-collected K=7 attempts, zero new cost) — found Mohler/DigiKlausur's significance strengthens with more rounds while Kaggle's is unstable across K, consistent with a real effect on the first two and noise on the third.

### D5. Why mean aggregation over median for combining the K independent gradings?
**Our answer:** Found empirically, offline, to strictly dominate median on Mohler and DigiKlausur (better correlation, comparable-or-better significance) and be no worse on Kaggle.
**Offline status:** Available, but this is itself a disclosed methodological caveat: the choice was made by comparing aggregation functions *on the evaluation data*, which is a real (if minor, since it's a simple, interpretable, pre-specifiable choice rather than a multi-parameter search) researcher-degrees-of-freedom exposure. We have not held out a separate dataset to confirm mean generalizes as the better choice.

### D6. How was the expert KG (101 concepts, 138 relationships) built and validated?
**Our answer:** Hand-built by a single author/research group, following stated design rules (pedagogical coverage, canonical IDs with aliases, typed relationships). No independent inter-builder reliability measure exists.
**Offline status:** The KG itself is frozen and fully available for inspection. No independent reconstruction or cross-author agreement study has been done — explicitly disclosed as a limitation, not something offline analysis can resolve.

### D7. How does the pipeline handle questions genuinely outside the KG's domain?
**Our answer:** An explicit `domain_match_score` signal (threshold <0.05) marks samples `OUT_OF_KG_DOMAIN` rather than silently defaulting to a vacuous score. Validated on Kaggle ASAG (100% correctly flagged, given elementary-science vocabulary has zero overlap with the CS Data Structures KG).
**Offline status:** Available, but with an important known failure mode also discovered offline: on the Mohler dataset extension, 2 of 4 genuinely in-domain questions (e.g., "how are infix expressions evaluated" — a stack topic) were *incorrectly* flagged out-of-domain, because the domain-match heuristic is keyword-literal on the question text, not semantic. This is a real, disclosed false-negative failure mode of the same mechanism that works correctly on Kaggle.

### D8. Why is misconception detection retained in the pipeline if the (fabricated-data-era) ablation showed it doesn't move the score?
**Our answer:** Design rationale is interpretability (feedback surfaced to students/instructors), not score accuracy.
**Offline status:** The specific ablation number supporting "doesn't move the score" is from the retracted fabricated-data era. It has not been re-tested on real data. This is an open item, not currently backed by real-data evidence either way.

### D9. Is the deployed `verifier_weight=1.0` (fully discard the KG-grounded score, use only the Verifier's judgment) actually justified, or just what happened to work?
**Our answer:** Justified — genuinely cross-validated.
**Offline status:** Fully available and, we believe, methodologically sound: leave-one-question-out CV, selecting the weight on training folds only (never the held-out fold), picks w=1.0 on every single fold (46/46). This is one of the few hyperparameter choices in this project that has survived a real CV check rather than being validated against the same data it's applied to.

### D10. Is the deployed extraction confidence threshold (τ=0.70) actually justified?
**Our answer:** Partially. A real-data sensitivity sweep (offline, zero cost) on the deterministic KG-comparison layer shows τ=0.70 is empirically near-optimal among tested values (0.70–1.00) for that layer specifically — stricter filtering monotonically hurts.
**Offline status:** This result is real but incomplete in an important way: we confirmed the extraction process discarded all concepts below confidence 0.70 *before saving*, so we cannot test τ<0.70 from existing data — that data is gone, not hidden. We also have not tested how τ affects the holistic-score and Verifier stages (only the deterministic comparator), since those stages' prompts embed the τ-filtered concept list directly and would need fresh calls at each τ to test properly.

---

## Part B: Testing & Methodology Questions

### T1. Is the real Mohler dataset actually real, and how do we know?
**Our answer:** Yes. A prior fabricated 120-sample fixture was discovered via a docstring self-admission of synthetic generation, then confirmed against the public `nkazi/MohlerASAG` HuggingFace mirror (CC-BY-4.0). Full incident record in `REPRODUCIBILITY.md`.
**Offline status:** Fully verified and documented, including provenance files (`data/mohler_real/PROVENANCE.md`).

### T2. Are DigiKlausur and Kaggle ASAG independently verified as real, to the same standard as Mohler?
**Our answer:** No. Circumstantial evidence looks legitimate (real-seeming content, non-round record counts, a previously-caught duplicate-record artifact in Kaggle), but neither has had the same direct source-mirror forensic cross-check that caught the Mohler fabrication.
**Offline status:** This is an honestly open gap, not something we can currently resolve from cached data — it needs the same kind of investigative work (tracing to an original public source and comparing) that was done for Mohler, which is possible without new API spend but has not been done.

### T3. What is the primary significance test — response-level Wilcoxon, question-clustered Wilcoxon, or the linear mixed-effects model (LMM)?
**Our answer:** Historically, question-clustered Wilcoxon was treated as the de facto primary test throughout most of this project. A subsequent LMM re-analysis (using every response-level data point with a random intercept per question, rather than collapsing to per-question means) gives materially different results — stronger significance for Mohler, weaker (non-significant) for DigiKlausur's headline result.
**Offline status:** Fully computed and available (`data/lmm_reanalysis.json`), but **not yet adopted as the primary reported test in either paper** — this is the single most concrete unresolved item from both external reviews, and we agree it needs to be resolved (with a stated justification), not left as two competing tests.

### T4. Is the 3-condition ablation (C_LLM / pre-Verifier KG score / full ConceptGrade) sufficient, or is the original 6-condition design still needed?
**Our answer:** The 3-condition version is a legitimate decomposition of the *deployed* scoring formula, reconstructed exactly from already-cached component scores — it is not an approximation. It is not, however, equivalent to re-running the pipeline in genuinely different intermediate configurations (e.g., a `concepts_only` variant that never sees the Verifier's holistic reasoning, `taxonomy_only`, etc.), which would need fresh LLM calls in each configuration.
**Offline status:** The 3-condition version is fully available and, we believe, sound. The 6-condition version remains untested on real data and would need new API spend.

### T5. Was the "fair control" (equally-resourced baseline, not just a single call) tested everywhere the original robustness claim was made?
**Our answer:** Yes, as of the most recent work — initially only Mohler was checked (an oversight caught by a reviewer-perspective self-audit), then DigiKlausur was completed after the gap was flagged. Kaggle ASAG was never claimed to benefit from self-consistency in the first place (null even against a single-call baseline), so no fair control was needed there.
**Offline status:** Mohler: zero new API cost (reused already-collected attempts). DigiKlausur: required 182 new batched calls (no prior multi-call C_LLM data existed for that dataset). Both fully documented with real, converged results.

### T6. Did the idea of blending C_LLM and C5_fix scores directly (a linear ensemble) hold up?
**Our answer:** No — it failed a genuine leave-one-question-out cross-validation (selecting the blend weight on training folds only picked w=0, i.e., "no blending," on every fold). The earlier appearance that a specific blend weight improved multiple metrics simultaneously was an artifact of selecting a favorable point on the same data being evaluated.
**Offline status:** Fully tested and retracted; not carried forward as a finding in either paper, with the full incident documented in `REPRODUCIBILITY.md` as evidence of the validation process, not hidden.

### T7. Is there a genuine held-out or blind test set anywhere in this body of work?
**Our answer:** No. Every dataset has been used across multiple rounds of analysis (kg_weight sweep, verifier_weight sweep, τ sweep, aggregation-method comparison, K-subset checks) even though no single choice was selected via a formal grid search directly against the final headline metric each time. This is a real, if soft, researcher-degrees-of-freedom exposure across the project as a whole, not just within any single experiment.
**Offline status:** This is a structural property of the work, not something offline analysis can fix — it would require a genuinely fresh dataset, collected and evaluated only once, at the end, as a final confirmatory check.

### T8. Has multiple-comparisons correction been applied across the many statistical tests run in this project?
**Our answer:** No formal family-wise error correction (Bonferroni, FDR, or similar) has been applied across the full set of tests conducted (response-level, cluster-level, LMM, K-subsets, per-dataset, per-aggregation-method, per-hyperparameter-sweep).
**Offline status:** This is a real, disclosed gap. It could in principle be addressed offline (recomputing adjusted thresholds/p-values doesn't need new data), but has not been done, and we do not currently have a canonical list of "which tests count as the family" to correct over.

### T9. Do the 300+ automated verification checks actually provide independent verification, or could they be checking the same underlying bug twice?
**Our answer:** They recompute every claim directly from cached raw prediction data (not from the paper text), so they genuinely catch drift between what a paper says and what the underlying data shows. They do **not** protect against a systematic error in the data-collection step itself — if a batched-scoring script had a consistent bug, every downstream check would agree with the wrong number, because they're all computed from the same (wrong) source file.
**Offline status:** The checks themselves are fully available and passing (336/338 at last count, 2 pre-existing unrelated failures). This is an honest epistemic limit of the approach, not a flaw we've found evidence of, but also not something we can rule out purely offline.

### T10. Has model/API version drift been controlled for?
**Our answer:** All live calls used the fixed model string `gemini-2.5-flash` throughout the session. We have not pinned to a specific dated model version beyond that string, and providers can update what a model string resolves to over time without notice.
**Offline status:** Not resolvable offline — would require either provider-side version pinning (if available) or a documented re-run at a later date to check for drift, neither of which we've done.

---

## Part C: What We Actually Have Offline (Complete Inventory)

For every dataset, the following per-sample prediction data is cached and available for any further offline analysis, at zero additional API cost:

| Dataset | Single-call C_LLM | Single-call ConceptGrade/C5fix | 7× self-consistency (C_LLM, K=7) | 7× self-consistency (Verifier/C5fix, K=7) | Question IDs for clustering |
|---|---|---|---|---|---|
| Mohler (46q, 1,262r) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mohler extension (+4q, 109r) | ✅ | ✅ | ❌ (not collected) | ✅ | ✅ |
| DigiKlausur (17q, 646r) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kaggle ASAG (150q, 368r deduped) | ✅ | ✅ | ❌ (never needed — null result) | ✅ | ✅ |

Also cached and available: full concept-extraction output (matched/missing concepts, confidence scores) for Mohler and its extension; the deterministic KG-formula component score separable from the holistic-LLM component score; human inter-rater data (both original graders) for Mohler; the complete verifier-weight and kg_weight sensitivity sweeps; the τ-sensitivity sweep for the deterministic layer; the retracted-ensemble CV results; the LMM re-analysis; and an automated script (`verify_all_paper_claims.py`) that recomputes 338 specific claims directly from this data.

**What is explicitly not available offline, for any dataset:** a second model family's predictions; a redesigned KG-comparator's predictions; human educator ratings of the system's usefulness; independent provenance verification for DigiKlausur/Kaggle; τ<0.70 concept extractions for Mohler (permanently discarded at collection time, not just unrun).

---

## Review Request

Given the specific answers and offline-data status above:
1. Does the offline evidence for D9 and T5–T6 (the CV-validated verifier weight, the completed fair-control checks, the retracted ensemble) change your view of the project's overall rigor, or were these already priced into your prior verdict?
2. For T3 (Wilcoxon vs. LMM): given the specific numbers now available, would you recommend LMM as primary with Wilcoxon reported as a secondary/robustness check, or a different resolution?
3. Given the full offline inventory in Part C, is there a mechanistic-failure-analysis (per your earlier "why does KG-grounding fail" request) that could be done entirely from this cached data, without new experiments — or does answering that question fundamentally require new data collection (e.g., a redesigned comparator)?
