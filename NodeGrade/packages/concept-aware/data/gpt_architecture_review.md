1. **Diagnosis: mostly right operationally, but overstates causality and generality.**

   I agree with stopping work on the current numeric composite as a *production scoring mechanism*. The evidence is unusually consistent: the components are defective or structurally mismatched to the task; attempted repairs worsen outcomes; learned fusion adds nothing; and CV selects verifier weight \(w=1\) everywhere. Continuing to hand-tune weights would be hard to justify.

   Two important qualifications:

   - Since deployed configurations set `verifier_weight = 1.0`, the composite cannot literally be the cause of the deployed final score underperforming zero-shot. It is already absent from the final output. The defensible claim is: **the composite contributes no measurable predictive value and should not be used for scoring**, not that it explains all pipeline underperformance.
   - “Symbolic score fusion is unsalvageable” is too broad. What is unsalvageable is this feature set, these component definitions, and this style of fixed/learned fusion on this dataset. A well-defined rubric-aligned symbolic representation might still help in another setting. But that is a different research program, not a reason to keep repairing this one.

   The evidence-in-context redesign is sensible, but it needs a clean ablation: same verifier model, same question/reference/student answer, with and without KG evidence; then add concept evidence, relationship evidence, misconception evidence, and depth labels separately. Otherwise it will be unclear whether gains come from the KG evidence, extra prompt length, repeated restatement of the answer, or simply a stronger multi-pass judging prompt.

2. **Calibration: prefer per-deployment calibration with shrinkage, not one universal parameter set.**

   Of the three options, **per-deployment calibration** is most statistically defensible, provided the calibration set is representative and sufficiently large. LLM scoring bias is not merely a generic “LLMs compress the range” phenomenon. It depends on:

   - backbone and model version;
   - prompt template and verifier instructions;
   - grading scale and rubric;
   - subject/domain;
   - question difficulty and score distribution;
   - human annotator norms;
   - whether the deployment population differs from the evaluation set.

   A global pooled affine transform will likely be stable but biased; a per-backbone transform is better but still ignores dataset/rubric shift. The best practical option is a **hierarchical/shrinkage calibration strategy**:

   - Maintain a global prior calibration, possibly with backbone-specific parameters.
   - Fit a deployment-specific affine adjustment when local labeled data exist.
   - Shrink the local estimate toward the backbone/global estimate when the local calibration set is small.
   - Record calibration provenance, sample size, data age, and confidence intervals.

   This gives you a “universal calibration protocol,” rather than pretending there is a universal calibration coefficient.

   Affine calibration is a good default because it is low-variance and interpretable. I would not jump to isotonic regression or quantile mapping unless you have substantially more held-out labeled data per deployment and clear evidence of nonlinear residual bias. Isotonic can overfit badly with small calibration samples, especially on a discrete 0–5 target. A useful middle ground is to compare:

   - affine calibration;
   - constrained monotonic ordinal calibration / ordered-logit style mapping;
   - isotonic only with adequate sample size and nested validation.

   Ensure calibrated outputs are bounded or clipped to the valid score range, and evaluate both MAE and calibration diagnostics by score band. Affine transformations can produce implausible values below 0 or above 5.

   Improving verifier scoring instructions is not an alternative to calibration; it is a separate intervention worth testing. Better anchors, explicit score definitions, and few-shot exemplars may reduce calibration error, but should be evaluated under the same held-out protocol. If prompt changes alter raw-score scale, calibration must be re-estimated anyway.

3. **Do not call the verifier/KG-evidence result model-independent yet. Lead with the weaker replicated claim.**

   The GPT result is promising, but DeepSeek is a direct non-replication of the stronger claim. A marginal ensemble advantage at \(p=0.048\) is weak evidence, particularly if multiple configurations, metrics, or prompts were explored.

   The appropriate headline is:

   > Across two backbones, the numeric KG composite adds no value to grading and should not be fused into the final score. KG-derived evidence may improve an LLM verifier on some backbones, but this benefit is model-dependent and requires further replication.

   Do not claim that “KG evidence improves LLM grading” universally until you have more models, ideally multiple versions/providers, and a preregistered or frozen evaluation protocol. The fact that models agree on many holistic judgments does not imply they use structured evidence equally well. Some models may be helped by the evidence; others may be distracted by noisy, redundant, or overly authoritative-looking intermediate labels.

4. **Additional structural risks to address before implementation**

   - **Evidence quality and false authority.** A verifier may overweight extracted concepts or misconception flags even when they are wrong. Prompt the verifier explicitly that KG evidence is fallible, must be checked against the student answer, and is not itself ground truth.
   - **Feedback harm.** Incorrect “missing concept” or misconception feedback is more damaging than a modest grading error because it teaches the student the wrong thing. Measure false-positive rates for feedback separately from score MAE, and consider confidence thresholds or abstention for misconception claims.
   - **Prompt contamination / prompt injection.** Student free text is untrusted input. The verifier prompt should clearly delimit student content and prevent instructions in the answer from influencing grading behavior.
   - **Question-level generalization.** Leave-one-question-out is better than random sample splitting, but calibration and feature claims should be tested on genuinely new question sets, not merely new answers to known question families. Calibration often appears to work because it captures question-distribution effects.
   - **Nested evaluation.** Every choice—calibration method, prompt format, clipping rule, ensemble weight, and evidence selection—must be selected inside training folds. Otherwise the reported calibration gain may be optimistic.
   - **Human-score reliability ceiling.** Report inter-rater reliability and label uncertainty. If human grading is noisy, small MAE or correlation differences may not be practically meaningful.
   - **Versioning and drift.** “GPT-5.6-terra” or OpenRouter-routed models may change over time. Calibration should be invalidated or rechecked after backbone, provider, prompt, rubric, or extraction-model changes.
   - **Cost/latency justification.** If zero-shot plus calibration matches or beats verifier-with-KG on some backbones, the extra extraction/verifier pipeline needs to earn its cost through either accuracy, feedback quality, auditability, or educator value—not architecture complexity alone.
   - **Separate grading from explanation.** It may be rational to use zero-shot/calibrated verifier output for the grade while using KG evidence for feedback and audit trails, if evidence improves pedagogical feedback but not score prediction. Do not require one mechanism to serve both goals.

Overall: stop numerical fusion; retain KG outputs as fallible evidence and feedback; adopt calibrated verifier scores; and frame “universal” as a portable evaluation/calibration procedure, not a single global model-independent score transform.