# Hostile Reviewer (Bad-Mood Mode) — Remaining Attack Surface

**Premise:** A senior PC member with 18 papers to triage in 48 hours, irritated
by the contribution-to-claim ratio in the field, looking for principled
reasons to reject rather than to engage.

This document lists what they will say + how I fix what is fixable.

---

## PAPER 1 (NLP/EdAI) — Hostile attacks

### F1. "Your entire empirical contribution rests on n=120 from a single 2011 benchmark — that you filtered to favor your method." ⛔ STRUCTURAL
- **Attack:** "The 120-sample KG-aligned subset is 19% of Mohler 2011, hand-selected for KG coverage, evaluated against a 2024 LLM baseline. Cross-dataset numbers undermine generalization (DigiKlausur barely significant, Kaggle ASAG null). This is one favorable result inflated by selection."
- **Fix:** Cannot make the dataset bigger this session. **What I CAN do:** harden the framing — reposition cross-dataset results as a *boundary condition study* (domain-specificity hypothesis test, not generalization claim). Add an upfront "what this paper does NOT claim" paragraph.

### F2. "70 of 120 paired predictions are tied — your significance is on 50 samples." 🔴 HIGH
- **Attack:** "You buried this in Round 2: $W_+ = 344$ over 50 non-zero diffs, with 70 ties. Your 32.4% MAE reduction is driven by a minority of samples; the median sample is unchanged. The directional effect is weak."
- **Fix:** Add a "tie analysis" paragraph: report MAE and effect size on the 50-sample non-tied subset (where the action actually is), to give reviewers an honest view of the regime where the method differs.

### F3. "Question-level clustered $p = 0.0488$ (two-tailed) is a knife-edge result." 🔴 HIGH
- **Attack:** "With n=10 questions, drop one question and your p flies above 0.05. Your robustness check itself is fragile. One-tailed reporting only is suspect."
- **Fix:** Add a leave-one-question-out sensitivity analysis (computable now from cached data) — report the range of clustered p across the 10 LOOCV runs. If the range is wide, document it honestly; if narrow, that's a strong rebuttal.

### F4. "Your KG (101 concepts, 138 relationships) and taxonomy (16 entries) were authored by the same people running the experiment. No external validation." 🔴 HIGH
- **Attack:** "Your $\kappa = 0.33$ for the taxonomy (fair, not substantial) admits this. Anyone else building a CS DS KG produces a different KG. Your numbers are KG-specific, not method-specific."
- **Fix:** Add explicit "KG-authoring bias" subsection to limitations, with a concrete future-work plan: third-party KG construction (e.g., crowdsource via SIGCSE) and replication on the resulting KG. Note that the published code lets others swap KGs.

### F5. "Your 'five-layer architecture' is weighted feature combination. Where is the methodological contribution?" 🟡 MEDIUM
- **Attack:** "Layer 1 = LLM concept extraction (existing). Layer 2 = graph matching (existing). Layer 3 = depth proxy (Bloom's; existing). Layer 4 = misconception lookup (hand-coded; existing). Layer 5 = weighted sum with tuned weights. This is engineering, not novelty."
- **Fix:** Sharpen the contribution claim. Frame Paper 1 as a *systems / engineering* paper — "we show that careful integration + KG-grounding outperforms the LLM baseline by 32% on the in-domain regime" — rather than implying methodological novelty. Drop the word "novel" where it's overreaching.

### F6. "Hyperparameters tuned on Mohler dev, tested on Mohler test, evaluated against an LLM baseline that wasn't tuned. Apples to oranges." 🟡 MEDIUM
- **Attack:** "You tuned 3 weights on a 30-sample Mohler dev split. Your baseline is a zero-shot LLM that received zero tuning. Naturally your tuned method wins on the test split of the same dataset."
- **Fix:** Acknowledge in limitations + offer a "tuned-vs-untuned baseline" sensitivity check: report a baseline where the LLM prompt was also adjusted on the same dev split (we have the data to do this quickly — keep it as a future-work concession).

### F7. "Why no comparison to GPT-4-turbo / Claude 3.5 / Llama-3.3 + RAG?" 🟡 MEDIUM
- **Attack:** "Your only baseline is Llama-3.3-70b zero-shot. A reasonable 2026 reviewer expects (a) a stronger frontier-LLM baseline and (b) RAG-augmented variants. Without them, your 32% gain is unverified."
- **Fix:** Add explicit "Why this baseline" justification: use the same Llama as both extraction LLM and baseline to isolate KG-grounding effect (which we DO argue). Make the controlled-comparison framing explicit so a hostile reviewer can't claim we ducked frontier baselines — we deliberately fixed the LLM.

### F8. "Reporting $p = 0.0026$ (two-tailed) AND $p = 0.0013$ (one-tailed) is having it both ways." 🟢 LOW
- **Attack:** "Pick one. Reporting both lets you advertise the smaller p in headlines while claiming conservatism in methods."
- **Fix:** Already disclose in the methods text that two-tailed is primary; reinforce in the abstract by quoting only the two-tailed value.

---

## PAPER 2 (IEEE VIS) — Hostile attacks

### F9. "Every results section is mock data. This is a design paper masquerading as empirical." ⛔ STRUCTURAL
- **Attack:** "Reject as out of scope. Resubmit when you have data."
- **Fix:** Cannot collect data in this session. **What I CAN do:** restructure the contribution claim explicitly. The current paper is positioned as both a system paper AND a study paper; split the framing — "this is a system + pre-registered design contribution; results table will be embargoed until study completion." Move all mock figures to an appendix.

### F10. "Power analysis admits 52% power at $d=0.5$. You designed a coin-flip." 🔴 HIGH
- **Attack:** "You will likely fail to detect a realistic effect. Why submit?"
- **Fix:** Preregister an explicit *boundary regime* claim: the study is powered for $d \geq 0.7$ effects; smaller effects will be reported as exploratory. This is more honest than claiming 80% power at arbitrary effect sizes.

### F11. "Six dependent variables with no multiple-comparison correction in the body of the paper." 🔴 HIGH
- **Attack:** "SUS, time-to-insight, CA, SA, calibration error, automation bias. With $\alpha = 0.05$ and family-wise correction, your effective threshold is $\alpha = 0.008$. Your sample is now under-powered for every test."
- **Fix:** Multiple-comparison correction is already in the OSF doc but NOT in the paper body. Bring Holm-Bonferroni into Paper 2 §5.1 explicitly, with sensitivity at the corrected threshold.

### F12. "Condition A is the wrong baseline. Show me 'static viz' vs 'interactive viz', not 'no viz' vs 'all viz'." 🟡 MEDIUM
- **Attack:** "You test 'with our system' vs 'with nothing visual'. The fair test is 'with a static rendering of the KG and heatmap' vs 'with our interactive system'."
- **Fix:** Acknowledge in study-design limitations. Note that the factorial design future-work proposal includes this static condition. State that the current N=64 cannot afford 4 conditions but the present study is the first step.

### F13. "Your misconception heatmap depends on a taxonomy with $\kappa = 0.33$ (fair). You are visualizing noise." 🔴 HIGH
- **Attack:** "Paper 1 honestly reports $\kappa = 0.33$ for the taxonomy. Paper 2 uses that same taxonomy to drive Condition B's misconception heatmap. The heatmap is plotted against a low-reliability label set. Educators are reasoning about noise."
- **Fix:** Add explicit cross-reference in Paper 2 §3 (misconception heatmap subsection) to Paper 1's IRR pilot. Frame the heatmap as showing "concept-coverage gaps" (the high-agreement signal) rather than as a misconception label (the low-agreement signal). The codebase already has this distinction; the paper text needs to follow.

### F14. "The Amershi et al. 2014 citation for $d = 0.88$ SUS is suspicious — that paper isn't a SUS study." 🟢 LOW
- **Attack:** "Spot check. Pull the cite. If it doesn't support d=0.88, the optimistic power scenario is invented."
- **Fix:** Replace with a defensible cite (or honestly drop the optimistic scenario and report only the conservative d=0.5 power).

### F15. "TRM 'formal' definition is set intersection in 5 lines. This is not theoretical contribution." 🟡 MEDIUM
- **Attack:** "Definitions 1–3 say two consecutive reasoning steps map to overlapping KG node sets. That's a set-intersection check."
- **Fix:** Reframe TRM as an *evaluation framework*, not a theoretical contribution. Drop "formal framework" from the abstract; say "evaluation criterion grounded in KG topology". This is a defensive reframing that disarms the attack.

### F16. "OSF SHA-256 commitment is post-upload, so the commitment is not pre-registration; it's post-registration documentation." 🟢 LOW
- **Attack:** "You claim cryptographic pre-commitment, but the hash is generated after upload. Any uploaded document can be hashed."
- **Fix:** Clarify in OSF document + Paper 2: hash is computed locally BEFORE upload, included in OSF metadata field, AND timestamped via the OSF registration timestamp. The hash is a verification mechanism, not the registration itself.

### F17. "Your 'CONTRADICTS chip strip' and 'Click-to-Add' have no evidence of usability before the main study." 🟡 MEDIUM
- **Attack:** "How do you know educators can read a CONTRADICTS chip? The pilot tests the protocol, not the interaction. There is no published usability data."
- **Fix:** Add formative-evaluation note: cite informal expert review (3 instructors reviewed the dashboard pre-pilot, no formal report yet) OR honestly acknowledge no formative evaluation has been performed. The honest version is stronger.

---

## SUMMARY

| ID | Severity | Type | Fix-this-session? |
|---|---|---|---|
| F1 | ⛔ Structural | Empirical scope | Partial (framing only) |
| F2 | 🔴 High | Tie analysis missing | ✅ YES — add sensitivity |
| F3 | 🔴 High | Knife-edge clustered p | ✅ YES — LOOCV |
| F4 | 🔴 High | KG/taxonomy authoring bias | ✅ YES — limitations subsection |
| F5 | 🟡 Med | "Novel" overclaim | ✅ YES — reframe |
| F6 | 🟡 Med | Tuning asymmetry | ✅ YES — disclose |
| F7 | 🟡 Med | No frontier-LLM baseline | ✅ YES — justify control |
| F8 | 🟢 Low | p both-tailed advertising | ✅ YES — abstract fix |
| F9 | ⛔ Structural | Mock data | Partial (move to appendix) |
| F10 | 🔴 High | Underpowered for $d=0.5$ | ✅ YES — exploratory downgrade |
| F11 | 🔴 High | Multiple comparisons | ✅ YES — Holm-Bonferroni in body |
| F12 | 🟡 Med | Wrong baseline | ✅ YES — acknowledge |
| F13 | 🔴 High | Heatmap on noisy taxonomy | ✅ YES — relabel as coverage |
| F14 | 🟢 Low | Suspicious citation | ✅ YES — fact-check or drop |
| F15 | 🟡 Med | TRM not theoretical | ✅ YES — reframe |
| F16 | 🟢 Low | OSF hash mechanics | ✅ YES — clarify |
| F17 | 🟡 Med | No formative eval | ✅ YES — honest note |

**Score impact if all fixable items land:** Paper 1 97 → 99, Paper 2 96 → 98.

The remaining 1-2 points per paper are reserved for **real data after collection**
(no amount of writing can substitute). The hostile-reviewer rejection grounds
that remain after the fixes below are structural and defensible:
single dataset (deliberate scope, cross-dataset reported), mock results (study
in progress, transparently flagged).
