# Hostile Reviewer (Bad-Mood Mode), Round 2 — Post-Cross-Dataset State

**New ground:** The papers now lead with a 1,239-sample / 177-question /
3-dataset story. That itself opens fresh attack surface that a hostile
reviewer in a bad mood will exploit. This document lists those attacks +
fixes.

---

## A. Statistical attacks (these are the serious ones)

### H1 (CRITICAL). Random-effects 95% CI INCLUDES ZERO
- **What the paper says now:** "Fixed-effects pool d_z = -0.07, 95% CI [-0.13, -0.02], p = 0.010" + "Random-effects pool d_z = -0.10, 95% CI [-0.21, 0.01]"
- **Attack:** "Your random-effects 95% CI [-0.21, 0.01] **includes zero**. Under the only methodologically defensible model for cross-study heterogeneity (random effects when I² is large), you cannot reject the null. The fixed-effects p=0.010 assumes a common true effect across the three datasets — directly contradicted by your own I²=70%. The honest pooled estimate fails to reach significance."
- **Severity:** This is publishable-paper-killing if not addressed.
- **Fix:** Reframe the cross-dataset narrative honestly. Lead with the random-effects estimate. Report the fixed-effects p-value but note it relies on a homogeneity assumption their I² rejects. Reposition the cross-dataset section as "boundary characterization" not "pooled confirmation."

### H2 (HIGH). I²=70% means pooling is methodologically inappropriate
- **Attack:** "Higgins et al. (2003) classify I² in [50%, 75%] as 'substantial heterogeneity'; > 75% as 'considerable.' Your I²=70% sits just below the considerable threshold. The Cochrane Handbook (§10.10.2) explicitly recommends against pooling at this level of heterogeneity. You should report three separate effect sizes, not a pooled one."
- **Fix:** Explicitly acknowledge the I²=70% in the paper text. Frame the pool as descriptive ("for completeness") not inferential. Per-dataset effects remain the primary report.

### H3 (HIGH). Pooled effect is SMALLER than single-dataset Mohler
- **What the paper does now:** Promotes the n=1,239 number, but the pooled d_z is roughly -0.07 to -0.10. Mohler alone gives d_z = -0.295.
- **Attack:** "Your pooled effect (d_z = -0.07 fixed, -0.10 random) is **less than one-third** of your single-dataset Mohler effect. Adding data has DECREASED your demonstrated effect. This is the opposite of what meta-analysis is supposed to do. The honest read is: ConceptGrade works in Mohler-like settings and approximately zero effect elsewhere."
- **Severity:** This is a narrative-killing attack.
- **Fix:** Stop framing the pool as a strengthened result. Acknowledge explicitly that the in-domain Mohler effect does not generalize uniformly. Lead with the boundary-characterization framing.

### H4 (HIGH). Including a known-null dataset in the pool is misleading
- **Attack:** "You include Kaggle ASAG (p_one = 0.170, n.s.) in your pooled effect. This drags the pool down and lets you claim a 'composite' significance the underlying data does not support. A hostile reading is that you knew Kaggle would weaken Mohler's effect and chose to dilute the headline rather than report Mohler alone."
- **Fix:** Report both a pooled-all-three and a pooled-significant-only (Mohler+DigiKlausur) sensitivity. The reader can see the comparison.

### H5 (MEDIUM). DigiKlausur d_z = -0.07 is below Cohen's small-effect threshold
- **Attack:** "Your DigiKlausur p_one = 0.024 is statistically significant only because n = 646 inflates power. The effect size d_z = -0.07 is well below Cohen's 'small effect' threshold of 0.2 — this is a negligible practical effect that achieves statistical significance through sample size alone."
- **Fix:** Report d_z alongside p for every cross-dataset comparison; explicitly distinguish statistical from practical significance.

### H6 (MEDIUM). Per-SOLO DigiKlausur: ConceptGrade is WORSE on 3 of 5 bands
- **What the paper shows:** Prestructural −9.1%, Unistructural −25.0%, Multistructural −8.1% (all negative, meaning C5 is worse than baseline).
- **Attack:** "Your own per-SOLO table shows your method is **worse than the baseline** on the bottom three SOLO bands in DigiKlausur. You frame this away by saying 'the lower bands are noise,' but combined they represent 141/646 = 22% of the sample. Your method makes 22% of DigiKlausur predictions **worse**."
- **Fix:** Honestly acknowledge this in the paragraph below the table. Add a sentence to the abstract about "domain-specific boundary conditions where ConceptGrade trades lower-band degradation for higher-band gains."

### H7 (MEDIUM). Kaggle ASAG SOLO collapse: classifier failure ≠ domain finding
- **What the paper says:** "Kaggle ASAG's SOLO classifier collapsed (all 473 → Prestructural), itself a useful diagnostic of low domain-specificity."
- **Attack:** "Your interpretation — that the SOLO collapse reveals domain-specificity — is **observationally equivalent** to your SOLO classifier being broken on Kaggle ASAG. You provide no falsification test. A reviewer cannot distinguish 'the dataset has low structural complexity' from 'the pipeline's SOLO module failed on out-of-distribution input.'"
- **Fix:** Add a falsification test: report the LLM extraction module's output distribution on Kaggle. If the LLM also produced empty matched_concepts on most samples, the failure cascade is upstream of SOLO. If matched_concepts are full but SOLO is empty, SOLO itself is the failure.

---

## B. Methodological attacks

### H8 (MEDIUM). Singleton "clusters" in Kaggle ASAG
- **Setup:** Kaggle has 150 unique question texts, but cluster sizes vary 1–10 (mean 3.2). A non-trivial number have **exactly 1 sample** — i.e., they are not clusters at all.
- **Attack:** "Your clustered analysis on Kaggle ASAG includes singleton 'clusters.' A cluster of n=1 contributes zero within-cluster variance — it's a single observation pretending to be a question-level mean. Your 150-cluster Wilcoxon is inflated by these singletons."
- **Fix:** Re-run the Kaggle clustered analysis dropping singleton clusters. Report both the all-clusters and ≥3-samples-per-cluster versions. Disclose how many singletons there are.

### H9 (MEDIUM). The F2 non-tied subset is post-hoc outcome conditioning
- **What the paper does:** Reports 50.7% MAE reduction on the 50 non-tied samples.
- **Attack:** "Your 'F2 non-tied subset' selects samples where the two methods produced different predictions. This is **conditioning on the outcome variable** (the prediction difference). Reporting an effect size on this hand-selected subset is methodologically suspect — you've selected exactly the cases where one method must have an error advantage over the other."
- **Severity:** Defensible if framed correctly.
- **Fix:** Reframe F2 explicitly as a "regime decomposition": the full-sample effect is the weighted mean of (50% ties, 0% effect) and (50% non-tied, 50.7% effect). This is a math identity, not a hand-selection. Make this transparent.

### H10 (MEDIUM). Variance approximation in the meta-analysis
- **What the script uses:** `var(d_z) ≈ 1/n + d_z²/(2n)` (Hedges & Olkin, unpaired d).
- **Attack:** "For paired Cohen's d_z, the variance depends on the within-subject correlation ρ. The formula you use is for an unpaired d. With paired data, the correct variance is roughly (2(1-ρ))/n + d_z²/(2n). For a typical ρ in grading tasks (correlation of paired errors), the actual variance is ~0.5–0.7× your approximation. Your inverse-variance weights, and therefore your pooled estimate, are slightly miscalibrated."
- **Fix:** Acknowledge the approximation in the script docstring + paper footnote. Test sensitivity by computing weighted means under ρ=0.3 and ρ=0.7; if the pooled estimate is stable, the approximation is fine.

---

## C. Narrative / scope attacks

### H11 (HIGH). Paper 2 abstract conflates scopes
- **What the abstract currently says:** "...evaluate ConceptGrade on 1,239 graded student answers from three domains... demonstrating 32.4% MAE reduction over an LLM baseline (Wilcoxon p=0.0026)."
- **Attack:** "Your abstract claims 32.4% MAE reduction on 1,239 samples. The 32.4% is the Mohler-only number; the cross-dataset average is much smaller (and the random-effects CI includes zero). A reader skimming the abstract will conclude 32.4% holds across all 1,239 samples, which is false."
- **Severity:** Easy to catch, easy to fix, embarrassing if a reviewer flags it.
- **Fix:** Rewrite the abstract sentence to explicitly attribute the 32.4% to Mohler and note the heterogeneous cross-dataset behavior.

### H12 (MEDIUM). The "1,239 samples" headline is rhetorical
- **Attack:** "Promoting n=1,239 in the abstract conveys 'more data = stronger evidence.' But your pooled effect is **smaller** and the random-effects CI **includes zero**. The larger n is being used to imply more, not less, certainty. This is a rhetorical move that won't survive close reading."
- **Fix:** Keep the n=1,239 / 3 datasets / 177 questions characterization (it IS more data), but in the SAME sentence acknowledge the heterogeneity ("with substantial between-dataset heterogeneity").

### H13 (LOW). OSF addendum mechanism is unfalsifiable as stated
- **Attack:** "Your pilot protocol §8 says 'protocol refinements will be logged in an addendum to OSF before main-study data collection begins.' Addenda are the standard backdoor for sneaking post-hoc revisions in while preserving the 'pre-registered' label. What concrete commitment prevents that?"
- **Fix:** Add to PILOT_PROTOCOL.md and OSF doc: the addendum window closes T-24h before main study opens, and any addendum filed within T-48h must include a SHA-256 of the addendum file at OSF upload time.

---

## D. Items I am NOT going to "fix" (defensible as-is)

- **IRB placeholder** — already correctly labelled as TBD pre-blind. Reviewer who attacks this is being unreasonable.
- **Single-author KG and taxonomy** — already in limitations with a future-work plan.
- **Mock data in Paper 2 user-study section** — already labelled `[PRE-SUBMISSION PLACEHOLDER]` upfront.
- **F2 sub-pixel hbox warning** — invisible in print.

---

## Summary table

| # | Severity | Attack | Fix-now? |
|---|---|---|---|
| H1 | CRITICAL | Random-effects CI includes zero | ✅ YES |
| H2 | HIGH | I²=70% inappropriate to pool | ✅ YES |
| H3 | HIGH | Pool is smaller than Mohler alone | ✅ YES (reframe) |
| H4 | HIGH | Including null Kaggle in pool | ✅ YES (sensitivity) |
| H5 | MED | DigiKlausur d_z < 0.2 (negligible) | ✅ YES |
| H6 | MED | Per-SOLO DigiKlausur 3/5 bands negative | ✅ YES |
| H7 | MED | Kaggle SOLO collapse interpretation | ✅ YES (add diagnostic) |
| H8 | MED | Singleton Kaggle clusters | ✅ YES (re-run sensitivity) |
| H9 | MED | F2 non-tied = outcome conditioning | ✅ YES (reframe as decomposition) |
| H10 | MED | Variance approximation | ✅ YES (acknowledge + sensitivity) |
| H11 | HIGH | Paper 2 abstract scope conflation | ✅ YES (rewrite sentence) |
| H12 | MED | n=1,239 headline rhetorical | ✅ YES (acknowledge heterogeneity) |
| H13 | LOW | OSF addendum loophole | ✅ YES (close it) |

**Estimated score impact if all fixes land:** Paper 1 99→99 (no point gain but
no point loss; the new attacks would have removed 2-3 points if unfixed).
Paper 2 98→98 (same).

The papers stay at the same score because the new fixes are *defensive* —
they prevent the cross-dataset upgrade from being used against us. Without
these fixes, the cross-dataset section actually creates new rejection risks.
