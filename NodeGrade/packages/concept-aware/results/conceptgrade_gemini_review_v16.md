# Gemini Review Request v16
**Date:** 2026-04-17  
**Paper:** IEEE VIS 2027 VAST — "Co-Auditing as Epistemic Update"  
**Prior rounds:** v1–v15 (all decisions locked)  
**This round:** Prose quality review of §2, §4, §5a first drafts — final check before full paper assembly

---

## What Was Built Since v15

Three section drafts are now complete. All v15 decisions (Q1–Q10) have been applied:

| Section | File | Status |
|---------|------|--------|
| §2 Related Work | `conceptgrade_related_work_v1.md` | ~490 words, 4 paragraphs, v15 Q1–Q4 applied |
| §4 System Architecture | `conceptgrade_system_architecture_v1.md` | §4.1–§4.4 prose complete (~830 words), telemetry moved to Supplemental A |
| §5a ML Accuracy | `conceptgrade_ml_accuracy_v1.md` | Ablation table condensed to C1/C4/C5_fix; conditional §5a.3 placement |

One open [TODO] remains in §2 Para 4: `[TODO: cite]` for mixed-initiative grading.

---

## Section 1: §2 Related Work — Prose Review

**Full text of §2 Related Work v1:**

> Automated short-answer grading has progressed from rule-based pipelines [Mohler 2011] to transformer-based scoring engines [Liu 2024] that approach human-level inter-rater agreement on constrained benchmarks. More recently, LLMs have been applied as direct scoring engines [Zheng 2023, Mizumoto 2023] and as reasoning verifiers that produce natural-language rationale alongside a numeric score [Kojima 2022]. Despite this accuracy progress, accountability remains unresolved: none of these systems exposes why a particular reasoning path led to a particular score, limiting educator trust in high-stakes grading deployments.
>
> Post-hoc explainability methods such as LIME [Ribeiro 2016] and SHAP [Lundberg 2017] provide feature attribution over input tokens but cannot reveal whether the model's reasoning chain was topologically coherent with respect to a domain ontology. Chain-of-thought prompting [Wei 2022] improved the quality of LLM rationale, but subsequent work has shown that CoT explanations are frequently unfaithful — the stated reasoning does not always reflect the actual computation [Turpin 2023, Lanham 2023]. Faithfulness metrics measure alignment between rationale and output; ConceptGrade instead grounds the coherence question in KG topology: is the model's reasoning chain connected within the domain graph, regardless of whether it influenced the final score?
>
> Visual analytics has been applied to AI transparency in NLP [Vig 2019], model behavior exploration [Kahng 2018, Hohman 2019], and concept-based explanations [Kim 2018]. In educational contexts, learning analytics dashboards [Siemens 2013] and concept map visualizations [Novak 1984, Ruiz-Primo 2004] support instructors in reasoning about student knowledge structure. Recent work on VA for grading feedback [Chen 2020, Sinha 2021] addresses the presentation of scores and aggregated rubrics, not the topology of the AI's inference process. To our knowledge, ConceptGrade is the first visual analytics system to project an LRM's chain-of-thought onto a domain Knowledge Graph in real time, making its topological structure available for educator co-auditing.
>
> Human-AI collaboration in grading has been studied as mixed-initiative workflow integration [TODO: cite], while Interactive Machine Teaching (IMT) [Simard 2017] and explanatory debugging [Kulesza 2012] provide theoretical groundings for human-directed model updates. Research on human mental models of AI [Bansal 2019] and sensemaking frameworks [Pirolli & Card 2005] demonstrates that structured explanations facilitate schema updates in expert users. Co-auditing extends these frameworks: rather than updating the model (IMT) or overriding its output (assistive grading), the educator updates their explicit rubric representation in response to visual evidence from the AI's reasoning trace. Crucially, whereas explanatory debugging asks the human to adjust model parameters to fix the machine, co-auditing leverages the machine's reasoning trace to help the human externalize and refine their own evaluation criteria — the rubric itself, not the model's weights.

---

### Q1 — §2 Paragraph 4 Missing Citation

**Question:** The sentence "Human-AI collaboration in grading has been studied as mixed-initiative workflow integration [TODO: cite]" needs a specific citation. Candidates:

1. **Kamar 2012** ("Combining Human and Machine Intelligence in Large-Scale Crowdsourcing") — general human-AI teaming, not grading-specific
2. **Nguyen 2022 or similar** — is there a CHI or EDM paper on mixed-initiative grading or co-grading workflows?
3. **Option C:** Remove the sentence and let the IMT/Kulesza citations carry the paragraph without a mixed-initiative grading citation.

**Please answer:** Provide the best citation for mixed-initiative grading, or confirm Option C (drop the sentence) if no strong grading-specific citation exists.

---

### Q2 — §2 Paragraph 3 "To our knowledge" Defensibility

**Question:** The claim "to our knowledge, ConceptGrade is the first visual analytics system to project an LRM's chain-of-thought onto a domain KG in real time" now rests on [Chen 2020, Sinha 2021] as the closest prior work. Is this "first" claim appropriately scoped and defensible, or does it need further hedging (e.g., "in the educational grading context" as we applied to Contribution 1)?

**Please answer:** Confirm the claim is defensible as written, or suggest the minimal hedging phrase needed to protect it against reviewer challenge.

---

### Q3 — §2 Word Count Check

**Question:** The current §2 draft is ~490 words. When the [TODO: cite] slot in Para 4 is filled with a citation, word count should remain under 500. However, Paragraph 3 (VA transparency) is the most reference-heavy (8 citations in ~110 words) and may look citation-dense to reviewers.

**Please answer:** Is 8 citations in Paragraph 3 appropriate for a VIS Related Work paragraph, or should 2–3 of the least-relevant ones (e.g., Vig 2019, Hohman 2019) be cut to reduce density?

---

## Section 2: §4 System Architecture — Prose Review

**Key sections to review (excerpts):**

> **§4.3 Trace Panel:** "...Color is used as a categorical channel for semantic class membership, following established conventions for nominal data encoding [Munzner 2014]. Between consecutive step cards where `hasTopologicalGap() = true`, a dashed amber connector signals the structural discontinuity: the LRM moved to a disconnected KG region without providing an intermediate explanation. This Gestalt-continuity violation is perceptible at a glance without reading the step text."
>
> **§4.3 Rubric Editor:** "The chips pulse three times upon mounting, utilizing pre-attentive motion processing [Ware 2004] to establish affordance without requiring intrusive tooltips."
>
> **§4.4 Click-to-Add:** "This sequence reduces co-auditing to a single click, eliminating the ambiguity that would arise if educators typed free-text concept names — the key distinction for H2 measurement (§5b). The interaction_source field precisely separates UI-assisted additions (Click-to-Add) from independently recalled additions (manual), enabling a clean split of the semantic alignment metric."

---

### Q4 — §4.3 Design Rationale Tone

**Question:** The design rationale in §4.3 uses technical language ("Gestalt-continuity violation", "pre-attentive motion processing") that positions the paper strongly as a visualization research paper. However, if primary reviewers are from the NLP/EdTech track rather than the VIS track, this language may read as overreach.

**Please answer:** Is the current tone appropriate for VAST, or should "Gestalt-continuity violation" be softened to something like "the visual discontinuity is perceptible without reading step text"? Specify which technical terms to retain (they signal VIS expertise) and which to soften.

---

### Q5 — §4.4 H2 Forward Reference

**Question:** The Click-to-Add paragraph ends with: "The interaction_source field precisely separates UI-assisted additions (Click-to-Add) from independently recalled additions (manual), enabling a clean split of the semantic alignment metric." This forward-references the H2 measurement design in §5b. Is this forward reference appropriate in §4, or should it be a back-reference to this sentence when writing §5b?

**Please answer:** Keep the forward reference ("The interaction_source field...enabling a clean split") in §4.4, or move it to §5b where the split is actually analyzed?

---

### Q6 — §4 Figure Captions

**Question:** We have two figures planned (pipeline figure + annotated UI screenshot). The caption for the UI screenshot is drafted in §4.3:
*"Figure X: The ConceptGrade interface during a co-auditing event. A structural leap (amber dashed line) in the Trace Panel reveals the LRM skipped the 'gradient_descent' concept. The educator uses the Click-to-Add interaction (pulsing chip) to instantly update the Rubric Editor, aligning their explicit evaluation criteria with the domain graph."*

Is this caption appropriately narrative for VAST, or is it too long? VAST caption style tends to be: (1) brief panel labels, then (2) one sentence of analytical framing. Should we restructure to: *(a) brief panel labels sentence + (b) "The amber dashed line signals a structural leap..."*?

**Please answer:** Keep the current narrative caption or restructure to VAST standard label + frame format. If restructuring, provide the revised caption.

---

## Section 3: §5a ML Accuracy — Prose Review

**Key text to review:**

> **§5a.1 Ablation interpretation:** "The LRM Verifier (C4) provides the single largest accuracy jump — a statistically significant improvement even before the concept fix (p < 0.0001), confirming that KG-grounded chain-of-thought verification is the mechanistic driver of accuracy gains, not prompt engineering or surface string matching."
>
> **§5a.2 Kaggle framing:** "Non-significance on Kaggle ASAG (p = 0.148) reflects a domain boundary condition rather than a system failure. In colloquial domains, high lexical ambiguity and synonymy prevent precise ontological mapping [Guarino 1998], reducing the discriminative power of the knowledge graph..."
>
> **§5a.3 Stability (conditional):** "Variability in TRM topology across models is itself a finding: the LRM's choice of which domain concepts to surface varies with model architecture..."

---

### Q7 — §5a.1 Ablation Prose — "Mechanistic Driver" Claim

**Question:** The §5a.1 prose claims the LRM Verifier is "the mechanistic driver of accuracy gains, not prompt engineering or surface string matching." This is a strong causal claim from an ablation study. Is this claim defensible in a VAST context, or does it require additional hedging (e.g., "our ablation suggests the LRM Verifier contributes the largest marginal gain")?

**Please answer:** Keep "mechanistic driver" or hedge to "contributes the largest marginal gain." If hedging, provide the revised sentence.

---

### Q8 — §5a.2 Kaggle Scope Condition Presentation

**Question:** Should the Kaggle boundary condition get its own paragraph header in §5a, or is it better presented as a continuation of the generalization paragraph (§5a.2) without a header? Giving it a header ("§5a.2.1 Boundary Conditions") might make it look like a structural feature of the paper, strengthening the argument that this is a principled finding rather than buried bad news.

**Please answer:** Paragraph continuation (no sub-header) or explicit sub-header for the Kaggle boundary condition? Justify with VAST reviewer psychology.

---

### Q9 — §5a.3 Stability Framing if r < 0.80

**Question:** The §5a.3 paragraph includes conditional text for the r < 0.80 case: "Variability in TRM topology across models is itself a finding: the LRM's choice of which domain concepts to surface varies with model architecture, implying that any single model's trace is an incomplete and model-dependent projection." 

Before we know the r value: is this framing ("variability is a finding") strong enough to survive peer review, or does a low cross-model correlation genuinely threaten the validity of the TRM visualization as a research contribution?

**Please answer:** Confirm whether the "variability as a finding" framing is reviewer-proof for VAST, or advise on a stronger hedge/reframe if r < 0.80.

---

### Q10 — §5a Missing Data: Ablation C2/C3 and DigiKlausur MAE

The ablation table and Table 2 both contain [TODO] values that require running evaluation scripts. This is an action item for the researcher, not a Gemini question. However:

**Question:** Should Tables 1 and 2 be included in the paper with [TODO] placeholders until the scripts are run (appropriate for co-author drafts), or should we write prose descriptions of the tables without the actual table format until all values are confirmed?

**Please answer:** Keep tables with [TODO] for co-author review, or convert to prose-only until data is confirmed? Justify.

---

## Locked Decisions Reminder

| Decision | Locked Value |
|----------|-------------|
| §4 telemetry | In Supplemental A only; one sentence pointer at end of §4.4 |
| §4.2 word target | ~120 words |
| §4.3 word target | ~330 words |
| §5a opening | Mohler (b) → Fisher combined → Kaggle |
| §5a.3 placement | Conditional: §5a if r ≥ 0.80; §5b intro if r < 0.80 |
| "Co-auditing" | Novel paradigm — no prior citation required |
| Kaggle | Boundary condition with [Guarino 1998] domain vocabulary citation |

---

## Expected Output Format

For each question:
1. **Decision** (1 sentence)
2. **Rationale** (1–2 sentences)
3. **Draft text** (if any text changes needed — full sentence, ready to paste)

**Priority this round:** Q1 (§2 missing citation), Q4 (§4.3 tone), Q7 (§5a.1 causal claim), Q9 (stability analysis framing).

---

**End of Gemini Review v16**
