# Phase 2 User Study: Dataset Selection Decision Brief for Gemini

**Context:** Phase 1 ML evaluation used 1,239 real student answers across 3 datasets (Mohler 120, DigiKlausur 646, Kaggle ASAG 473). Phase 2 user study will present these same datasets through the ConceptGrade dashboard to N=30 educators (15 per condition: A=control summary, B=treatment interactive).

**Question:** Which dataset(s) should educators interact with, and why?

---

## Three Options Under Consideration

### **Option A: Single Dataset (DigiKlausur)**
**Configuration:** All 30 educators see the same 646 Neural Networks student answers.

**Pros:**
- Largest sample size → rich heatmap patterns, statistically robust
- Mid-range KG signal (between CS "high specificity" and Science "low specificity")
- All educators see identical data → direct Condition A vs. B comparisons (no confound from dataset differences)
- Simplest analysis (no need to control for dataset effects)
- Educator-relatable domain (NN is widely taught)

**Cons:**
- Only tests generalization on one domain
- Doesn't validate whether VA helps in low-KG domains (Kaggle ASAG)
- Misses opportunity to test boundary conditions from Phase 1

**Narrative Implication:**
> "Educators using ConceptGrade on medium-specificity NN data showed X% improvement in SUS, Y causal reasoning statements, and Z rubric refinements compared to control."

---

### **Option B: Rotating Datasets (Stratified)**
**Configuration:** Stratify 30 educators across datasets.
- 10 educators → Mohler (120 answers, high-KG domain)
- 10 educators → DigiKlausur (646 answers, medium-KG domain)
- 10 educators → Kaggle ASAG (473 answers, low-KG domain)

**Pros:**
- Tests generalization across all three domains (matches Phase 1 narrative)
- **Validates key hypothesis:** Does VA help even in low-KG domains where ML accuracy plateaus?
- Enables within-condition comparison: Does Condition B advantage hold equally in Kaggle ASAG?
- Richer paper narrative: "System generalizes across vocabulary-rich (CS) → vocabulary-poor (Science) spectrum"
- Aligns with Phase 1 multi-domain evaluation philosophy

**Cons:**
- Smaller N per dataset (10 educators per condition per dataset = 5 per group; marginal statistical power)
- Between-subject confound: Can't tell if SUS differences are due to condition or dataset
- Analysis is more complex (need mixed-effects model or ANOVA with dataset as factor)
- Mohler sample size (120) may feel "small" to educators after DigiKlausur (646)

**Statistical Consideration:**
- Poisson GLM for causal attribution can handle this (condition + dataset as predictors; educator as random effect)
- GEE for task accuracy still works (repeated measures across datasets)
- But power is reduced (N=5 per group per dataset vs. N=15 per group)

**Narrative Implication:**
> "Across three distinct domains, educators using ConceptGrade (Condition B) reported X% higher SUS and Y more causal reasoning statements. Notably, the system's benefits persisted even in the low-specificity Science domain where ML accuracy gains disappeared, validating the VA interface as a domain-agnostic tool."

---

### **Option C: Sequential Multi-Domain (Each Educator Sees All Three)**
**Configuration:** Each of 30 educators explores Mohler → DigiKlausur → Kaggle ASAG in sequence (tabs).

**Pros:**
- Richest data per educator (sees domain diversity directly)
- Within-subject design (educator is their own control across domains)
- Tests whether educators **adjust mental models** when moving across domains
- Highest statistical power (30 educators × 3 datasets = 90 data points)

**Cons:**
- Session length balloons (45 min → 60–75 min minimum; fatigue risk)
- Order effects: does seeing Mohler first bias Kaggle ASAG perception?
- Priming/anchoring: educators may over-apply NN reasoning to Science data
- Cognitive load: processing 1,239 answers is unrealistic in one session
- Hard to isolate which domain drove insights (causal attribution gets muddled)

**Narrative Risk:**
> "Educators saw multiple domains but thought patterns became contaminated by prior domain knowledge; we cannot cleanly attribute insights to the VA system vs. domain switching."

---

## Gemini's Input Requested

**We need your judgment on:**

1. **Which option aligns best with IEEE VIS methodology standards?**
   - Single-dataset rigor (Option A) vs. multi-domain generalization (Option B)?
   - Is N=5 per group per dataset (Option B) acceptable for a VIS paper with qualitative think-aloud?

2. **Which option strongest supports the paper narrative?**
   - Option A: "ConceptGrade is effective on medium-complexity domains"
   - Option B: "ConceptGrade generalizes across domain specificity spectrum; VA utility is orthogonal to ML accuracy"
   - Option C: "Educators integrate multi-domain reasoning via VA exploration" (but risking cognitive overload)

3. **Which option de-risks the Kaggle ASAG null result?**
   - Option A avoids the question (doesn't test Kaggle ASAG)
   - Option B directly answers: "Does VA help even when ML fails?" (strongest redemption arc)
   - Option C introduces confounds (hard to isolate)

4. **Practical consideration:** Should we test the **hypothesis that VA utility is independent of ML accuracy**?
   - This is strategically important: if Condition B outperforms Condition A on Kaggle ASAG (where C5_fix shows no improvement), it validates that the dashboard has value beyond ML optimization
   - Only Option B tests this directly

---

## Our Preliminary Leaning

**Hypothesis:** Option B (Rotating Datasets) is best for a VIS paper because:

✅ **It matches Phase 1 narrative** (tested 3 domains; now validate user perception across them)  
✅ **It tests the hard question** (Does VA help when ML doesn't? → yes/no with real data)  
✅ **It's methodologically sound** (N=5 per subgroup is small, but GEE + qualitative coding compensates)  
✅ **It's the "honest" choice** (doesn't hide the Kaggle ASAG question; confronts it)  
✅ **The paper tells a stronger story** (generalization across domain boundaries)

**But we're uncertain:**
- Is N=5 per group × per dataset too small for VIS?
- Should we prioritize statistical power (Option A: N=15 per condition) over generalization (Option B: N=10 per condition)?

---

## Questions for Gemini

1. **For a top-tier VIS paper with mixed methods (quantitative SUS + qualitative think-aloud coding), is Option B's N=5 per subgroup acceptable?** Or should we choose Option A for statistical robustness?

2. **Does testing the hypothesis "VA helps even when ML fails" (Option B on Kaggle ASAG) justify the reduced statistical power?** VIS papers often value novel insights over statistical power.

3. **If we choose Option B, should we adjust the study design** (e.g., increase N to 45 educators, 15 per dataset; or use a different statistical approach)?

4. **How should we frame the limitation in the paper if we choose Option B?** E.g., "Smaller sample per domain, but qualitative findings provide compensatory depth."

---

**Your Recommendation?**

We're inclined toward **Option B** (rotating datasets) for the strategic value of testing generalization. But we defer to your judgment on whether the statistical trade-off is acceptable for VIS.

**If you recommend Option A**, we can still allude to Kaggle ASAG in Discussion as "future work" (test whether VA helps in low-specificity domains).

**If you recommend Option B**, we'll update the protocol to stratify N=30 educators and prepare mixed-effects analysis.

Please advise.
