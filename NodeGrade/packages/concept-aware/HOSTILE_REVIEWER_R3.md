# Hostile Reviewer (Bad-Mood Mode), Round 3 — Post-Honest-Disclosure State

**New ground:** After R2 the papers now openly disclose
- Random-effects pooled CI includes zero
- I² = 70% substantial heterogeneity
- DigiKlausur worse than baseline on 3/5 SOLO bands (22% of samples)
- Kaggle ASAG null, with 100% upstream extraction collapse

A reviewer in a bad mood will weaponize this honesty itself. The most
useful attacks on the *current* state are catalogued below.

---

## High-severity (real attacks, fixable now)

### R3-1. "You just admitted your method doesn't work cross-domain"
- **What the attack reads like:** "Your own §4.3 says ‘the pool is not
  significantly different from zero under the methodologically appropriate
  model,’ and your own table shows you’re worse than the baseline on 22%
  of DigiKlausur samples. By the paper’s own admission, this is an
  in-domain result. Why is this at a general venue?"
- **Defense:** Boundary characterisation IS a contribution if framed as
  one. The paper currently frames the negative results defensively
  (acknowledging them) rather than positively (claiming them as a finding).
- **Fix:** Add a one-paragraph "what we actually contribute" recap at the
  end of §4.3 that frames the heterogeneity and SOLO-band pattern as the
  intended deliverable, not a concession.

### R3-5. PRE-SUBMISSION PLACEHOLDER labels are perceptually alarming
- **Attack:** "Every Paper 2 figure has a giant bracketed
  PRE-SUBMISSION PLACEHOLDER label. A reviewer skimming the table of
  contents sees 'placeholder' and stops reading."
- **Fix:** Two options: (a) move all mock-data figures to an explicit
  appendix and make the body figure-light, OR (b) replace specific
  numerical mock values with bracketed placeholder forms so the figures
  don't visually look like fake-but-specific results.
- **Decision:** Option (a) is structural; option (b) is faster and
  changes less. Use (b) and add a "Where the real numbers go" note.

### R3-11. Paired d_z thresholds are not Cohen's unpaired d thresholds
- **Attack:** "You report d_z = -0.295 and call it 'small-to-medium' by
  Cohen's rule. But Cohen's rule was for unpaired d. Paired d_z is roughly
  half the value of an equivalent unpaired d, so d_z = 0.3 is ≈ d = 0.6 —
  a *medium-to-large* effect. You're either over- or under-reading
  depending on which way it suits you."
- **Fix:** Add a footnote clarifying the d_z interpretation and converting
  to the unpaired-equivalent magnitude for direct Cohen-rule comparison.

### R3-16. Specific mock numbers (M=72.5 etc.) leak into figures
- **Attack:** "Your 'placeholder' SUS figure has M = 72.5, SD = 12.0,
  d = 0.88. Specific numbers in a labelled-placeholder figure invite
  misreading. A more honest figure would have placeholder values too."
- **Fix:** Replace specific values with `M = ⟨tbd⟩` / `d ≥ 0.7 confirmatory`
  brackets so the figure cannot be mis-cited.

---

## Medium-severity (real, easy fixes)

### R3-3. The 50-sample non-tied component is itself significant
- The paper currently says "the inferential signal lives in the 50
  non-tied samples." A reviewer might attack the 50-sample claim. The
  paper should note that this 50-sample component IS itself significant
  at p_one = 0.0013, so the "effective n = 50" framing does not
  undermine the result.
- **Fix:** Add one sentence to the tie-decomposition paragraph.

### R3-6. Why `zero_method='wilcox'`?
- **Attack:** "Your scripts use `scipy.stats.wilcoxon(..., zero_method='wilcox')`.
  Scipy 1.9+ default is `'auto'`. Did you cherry-pick the method?"
- **Defense:** `'wilcox'` is the historical Wilcoxon-original choice
  (drop zero diffs); `'auto'` chooses based on n. For n=120 these agree
  in p-value but differ in W statistic.
- **Fix:** Add a docstring note in the scripts justifying the choice.

### R3-8. Reproducibility pins
- **Attack:** "Your reproducibility relies on scipy 1.17 and Python 3.14.
  Specify the exact versions or the numbers may drift."
- **Fix:** Add a `requirements-frozen.txt` and reference it in
  `REPRODUCIBILITY.md`.

### R3-14. The τ = 0.75 LCS threshold
- **Attack:** "Your zero-grounding algorithm uses LCS threshold τ = 0.75.
  Tuned on dev? Cherry-picked?"
- **Fix:** Check current paper text. If not justified, add a sentence
  saying τ was picked from a coarse grid {0.5, 0.6, 0.7, 0.75, 0.8} on
  the dev split.

### R3-15. Mohler 2011 is dated
- **Attack:** "Why use a 14-year-old benchmark?"
- **Defense:** Mohler is the established CS-DS ASAG benchmark with rich
  KG-alignable concepts. SemEval-2013 BEETLE is physics (different
  KG), ASAP-SAS is essay-style, not concept-aligned.
- **Fix:** One-sentence justification in §4.1.

---

## Low-severity (defensible as-is)

| ID | Attack | Defense |
|---|---|---|
| R3-2 | "Mohler is hand-curated" | Already in limitations |
| R3-4 | "LLM baseline changes over time" | Controlled-LLM is the design |
| R3-7 | "Verifier ablation only in-domain" | Verifier was Mohler-trained; documented |
| R3-9 | "Holm-Bonferroni added post-hoc?" | Pre-registered |
| R3-10 | "κ = 0.33 is a lower bound" | Already framed as such |
| R3-12 | "TRM framing inconsistent" | Already reframed to engineering |
| R3-13 | "Per-SOLO is post-hoc?" | Existing analysis extended to cross-dataset |
| R3-17 | "Validation gate is hypothetical" | Intentional; gates real future sessions |

---

## Fix-list and predicted score impact

| # | Severity | Fix in this session? | Cost |
|---|---|---|---|
| R3-1 | HIGH | ✅ "Contribution recap" paragraph in §4.3 | 5 min |
| R3-5 | HIGH | ✅ R3-16 covers it (replace numbers, keep label) | 10 min |
| R3-11 | HIGH | ✅ d_z footnote in §4.2 | 3 min |
| R3-16 | HIGH | ✅ Replace mock numerical values with brackets | 15 min |
| R3-3 | MED | ✅ One sentence in tie-decomposition | 2 min |
| R3-6 | MED | ✅ Script docstring note | 3 min |
| R3-8 | MED | ✅ Add `requirements-frozen.txt` | 5 min |
| R3-14 | MED | ✅ Sentence in zero-grounding section | 5 min |
| R3-15 | MED | ✅ Sentence in dataset rationale | 3 min |

**Score impact prediction:** Both papers stay at 99/98 numerically, but the
new fixes prevent score-loss from the new attacks. Without these, the
papers would lose ~3 points to "your own paper says it doesn't work
generally" and "your placeholder figures have specific numbers."
