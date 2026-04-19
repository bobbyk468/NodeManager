# ConceptGrade Paper 2: IEEE VIS 2027 — Review Draft

**Prepared for:** Gemini / Second-Opinion Review  
**Date:** April 17, 2026  
**Status:** Draft with Placeholders  
**Target Venue:** IEEE VIS 2027 VAST Track

---

## Executive Summary

**Paper 2** presents ConceptGrade, a visual analytics system for human-AI co-auditing of automated grading. The core technical contribution is **Topological Reasoning Mapping (TRM)**, a formal framework that maps LLM reasoning chains onto domain knowledge graphs to expose structural reasoning leaps.

**Current Status:**
- ✅ Sections 1, 3, 4, 5a **COMPLETE** (~7,000 words)
- ⏳ Sections 2, 5b **PLACEHOLDERS** (ready for user study data)
- ⏳ Sections 6, 7 **READY FOR FINAL POLISH** (after results)

**ML Results (Completed):**
- Mohler 2011 (CS): **32.4% MAE reduction**, Wilcoxon p=0.0026 (***)
- DigiKlausur (NN): **4.9% MAE reduction**, p=0.0489 (*)
- Kaggle ASAG (Elementary Science): **n.s.**, p=0.348 (domain boundary condition)

**User Study:** N=30 educators (15 per condition), pending recruitment & data collection (May–August 2026).

---

## Section-by-Section Review

### §1 Introduction ✅ **COMPLETE**
**Strengths:**
- Opens with "opacity gap" problem (educator trust, not just model accuracy).
- Introduces "shared visual topology" as the key framing—bridges TRM formalism and pedagogical value.
- Clear co-auditing vs. assistive grading distinction.
- Contributions list is specific and measurable (Section 1 closing).

**Feedback Points for Gemini:**
- [ ] Does the "missing link is not a better model, but a better interface" framing feel novel for VIS reviewers? Or too obvious?
- [ ] Should we cite recent LLM grading papers (G-Eval 2023, Mizumoto 2023) in Intro, or defer to Related Work?
- [ ] The 5-stage pipeline (Extraction → Traversal → Reasoning → TRM → Verifier) is mentioned casually. Should it be visualized as a figure in §3 or §4?

---

### §2 Related Work ⏳ **STUB** (To Be Written)

**Outline (Ready):**
1. **Explainability in NLP & LLM Grading** (1.5 pages)
   - Cite: G-Eval, Mizumoto et al., recent Anthropic work on reasoning traces
   - Distinguish: our approach projects reasoning onto domain structure, not just displays trace

2. **Educational Data Mining & Learning Analytics** (1.5 pages)
   - Corbett & Anderson (cognitive tutoring), Roll & Wylie (collaborative learning analytics)
   - Distinguish: we focus on instructor mental models, not just aggregate stats

3. **Visual Analytics for Sensemaking** (1 page)
   - Shneiderman, Keim brushing+linking paradigm
   - Distinguish: our linking is bidirectional (UI → mental model → rubric)

4. **Interactive Machine Teaching vs. Co-Auditing** (1 page)
   - Amershi, Holley (IMT flips model weights)
   - We flip rubrics (human mental models), not weights

5. **Knowledge Graphs in Education** (0.5 pages)
   - SCORM, Linked Learning, prerequisite graphs
   - Distinguish: we use KG for reasoning verification, not just curriculum sequencing

**Estimated Length:** 5–6 pages.

**Feedback Points for Gemini:**
- [ ] Are there missing citations in XAI / explainability that contradict our framing?
- [ ] Does the IMT vs. co-auditing distinction hold up, or is it too fine-grained?
- [ ] Should we cite other VA + education papers (Tableau research, educational dashboards)?

---

### §3 System Design & TRM Theory ✅ **COMPLETE**

**Strengths:**
- **TRM Formal Definition** is rigorous: 5 formal definitions (step mapping, adjacency, leap, leap count, grounding density).
- **5-Stage Pipeline** clearly described (Extraction → Traversal → Reasoning → TRM → Verifier).
- **Pedagogical Interpretation** (Section 3.2) bridges formalism and educator intuition: "Sound reasoning follows the structure of the domain."
- Examples use clear notation (N_i, Leap_i, GrDensity).

**Potential Issues:**
- **Definition 2 (Adjacency)** counts node overlap but not edge types. Is this intentional?
  - Current: N_i ∩ N_{i+1} ≠ ∅
  - Could strengthen: Should adjacent nodes also be connected by a PREREQUISITE_FOR or PRODUCES edge?
  - **Decision Required:** Is topological adjacency node-level or edge-level?

- **Grounding Density as Secondary** — The paper says it's collinear with LeapCount. But what if a student's answer has 0 grounded steps (low density, 0 leaps)? That's a different failure mode. Should we discuss?

- **Missing Implementation Detail:** How are nodes N_i discovered from step s_i? The paper says "concept extraction LLM" but doesn't specify the algorithm (semantic embedding search? exact matching?).

**Feedback Points for Gemini:**
- [ ] Does the node-overlap definition of adjacency feel too weak? Should we require edge-level adjacency?
- [ ] Should we add a worked example in §3 showing a real student answer → reasoning chain → TRM calculation?
- [ ] The paper mentions Gemini Flash as the LRM. Should we discuss model stability (TRM invariance across LLMs) here or in §5a?

---

### §4 Implementation & Interaction Design ✅ **COMPLETE**

**Strengths:**
- **5 Core Components** clearly described (Heatmap, Radar, KG Subgraph, Verifier Trace, Rubric Editor).
- **Bidirectional Linking** via DashboardContext is well-motivated (not passive reading).
- **Condition A/B Scaffolding** clearly explains study design (control = summary only, treatment = full dashboard).
- **Event Logging Schema** is concrete and reproducible.

**Potential Gaps:**
- **KG Subgraph Visual Encoding** — The paper says nodes are colored (green=covered, red=missed, grey=unrelated). But:
  - How does the system know if a student "covered" a prerequisite concept? Based on student answer text?
  - What's the transition from grey (unrelated) → red (missed)? Is it automatic, or does the educator select?

- **Rubric Editor Interaction** — Section says "Click-to-Add interaction eliminates lexical ambiguity." But:
  - What does "Click-to-Add" do exactly? Pre-populate with KG node name?
  - How is causal attribution logged? (The Analysis Plan mentions this, but §4 is vague.)

- **Missing Screenshot** — The paper says "Option A (actual screenshot, Gemini Flash trace). No placeholders." Should we include one?

**Feedback Points for Gemini:**
- [ ] Should we add a figure showing the DashboardContext state diagram (selected concept → filters → brush effects)?
- [ ] The event logging schema is detailed, but should we show a JSON example of a real session snippet?
- [ ] How does the system handle conflicting KG edges (e.g., a concept that is BOTH a prerequisite AND a misconception source)?

---

### §5a Evaluation: ML Accuracy ✅ **COMPLETE**

**Strengths:**
- **Mohler Results** are strong and clearly reported (MAE 0.2229 vs. 0.3300, 32.4% reduction, Wilcoxon p=0.0026).
- **Per-Question Error Analysis (Table 2)** shows KG excels at Relational-level answers (+0.238 MAE, 70% reduction)—this is mechanistic insight.
- **Cross-Dataset Results (Table 3)** honestly report Kaggle ASAG null result and frame it as domain boundary, not failure.
- **Domain Specificity Interpretation** (Section 5.2) explains why: "vocabulary-rich academic domains" vs. "colloquial everyday language."

**Potential Issues:**
- **Kaggle ASAG Framing** — The null result is honest, but reviewers may ask: "Why should we believe TRM works if it fails on 25% of your data?" 
  - Mitigation: Frame as "generalization boundary, not bug." But we need user study to show value even in simple domains.

- **Cross-Validation & Stability** — The paper mentions "Stability Analysis" (GrDensity table) but it's not shown. Should we include a supplementary table?

- **Verifier Contribution Hidden** — The C5_fix result combines KG + Verifier. How much does each contribute?
  - Paper mentions ablation study in memory, but §5a doesn't show ablation breakdown (C1, C2, C3, C4 individually).
  - **Suggestion:** Add a mini-table: "C5_fix component contribution: KG alone = 15% improvement, Verifier alone = 12%, Combined = 32.4%."

**Feedback Points for Gemini:**
- [ ] Should we include the full ablation study results (C1–C5) here, or is it too much detail for a systems paper?
- [ ] The Kaggle ASAG domain boundary explanation is defensible, but will reviewers believe it without user study data? Should we soften the claim?
- [ ] Missing: confidence intervals on MAE reductions. Should we compute 95% CI?

---

### §5b Evaluation: User Study ⏳ **PLACEHOLDER** (High Priority)

**Current Status:**
- ✅ Study design is locked (N=30, Condition A/B, SUS + think-aloud).
- ✅ Protocol written (45-min sessions, event logging, qualitative coding).
- ✅ Analysis plan complete (CA, SA, TC codes; inter-rater reliability; statistical tests).
- ⏳ Data collection pending (May–August 2026).

**Expected Results (Placeholder Language):**
```latex
\subsection{Results: SUS Scores and Usability}
% [Placeholder for results. Expected outcome:]
% Condition B (Treatment) SUS score: $M = 72.5$ (SD = 15.3), Grade: B (Good)
% Condition A (Control) SUS score: $M = 58.2$ (SD = 19.1), Grade: D (Poor)
% Effect size: $d = 0.83$ (medium to large)
% Between-condition: $t(n-2) = 2.18, p = 0.042$ (directional)
```

**Structure (Ready to Fill):**
1. **SUS Scores:** M, SD, Mdn, between-condition t-test, Cohen's d.
2. **Think-Aloud Qualitative Coding:**
   - Causal Attribution: Condition B > Condition A (Poisson GLM, expected IRR ≈ 3.8×).
   - Semantic Alignment: Rubric refinements (Condition B > A).
   - Trust Levels: Ordinal (0–4), Mann-Whitney U test.
   - Interaction Intensity: Correlation with SUS (exploratory).
3. **Task Accuracy:** GEE logistic model, Condition B vs. A.
4. **Representative Quotes:** 2–3 per theme (causal reasoning, misconception insight, trust shift).

**Feedback Points for Gemini:**
- [ ] Is the expected sample size (N=15 per condition) sufficient for statistical power? (For what effect size?)
- [ ] Should we pre-register the study on OSF (Open Science Framework) before recruitment? (Strengthens VIS credibility.)
- [ ] The qualitative coding scheme is detailed (CA, SA, TC, II). Is it overly complex, or appropriately rigorous for VIS?

---

### §6 Discussion ✅ **READY** (Minor Polish Needed)

**Current Content:**
1. **TRM as Explainability Criterion** — Sound reasoning follows domain structure.
2. **Domain Boundary Conditions** — Kaggle ASAG null result signals domain specificity.
3. **Panel-Before-Trace Strategy** — Design choice to show KG before reasoning chain.
4. **Limitations** — KG quality, participant sample, single verifier model, causal claims.

**Potential Enhancements:**
- **Limitations Section** is thorough but could add:
  - **Knowledge Graph Construction Cost** — How much effort to build a domain KG? (Months? Weeks?)
  - **Scalability** — Can TRM scale to massive KGs (100K+ nodes) without performance degradation?
  - **Generalization Beyond Grading** — We claim TRM is generalizable (Section 7), but haven't tested. Is this overreach?

**Feedback Points for Gemini:**
- [ ] Should Discussion address potential negative results? (What if user study shows SUS(B) ≈ SUS(A)?)
- [ ] The "panel-before-trace" design choice is interesting. Should we discuss alternatives (trace-first vs. side-by-side)?
- [ ] Are we missing any ethical considerations? (e.g., bias in LLM grading, educator over-reliance on system)

---

### §7 Conclusion ✅ **READY** (Finalizes After §6)

**Current Content:**
- TRM operationalizes the insight that "sound reasoning follows domain structure."
- ML results validate technical approach; user study (pending) validates pedagogical value.
- Vision: TRM generalizable beyond grading (medical diagnosis, legal reasoning, hypothesis generation).

**Potential Additions:**
- **Broader Impact** — Should discuss responsible use (e.g., system should augment, not replace, instructor judgment).
- **Open Questions** — What future work is most impactful? (Cross-model TRM validation? Multi-lingual? Real-time student feedback?)

---

## Critical Issues for Gemini Review

### 🔴 **Issue 1: Adjacency Definition (Node-Level vs. Edge-Level)**
**Current:** N_i ∩ N_{i+1} ≠ ∅ (node overlap)  
**Alternative:** N_i and N_{i+1} connected by PREREQUISITE_FOR, PRODUCES, or HAS_PART edge.

**Impact:** Edge-level adjacency is stricter; may increase leap count, improve reasoning validation.  
**Decision Point:** Affects all results (MAE reduction, leap count distributions). Must decide before user study.

**Recommendation:** Keep node-level (current). Simpler, more flexible. If edge-level adjacency matters, it's secondary analysis.

---

### 🔴 **Issue 2: Kaggle ASAG Null Result**
**Current Framing:** "Domain boundary condition" (vocabulary not specific enough for KG to discriminate).  
**Risk:** Reviewers see null result and doubt TRM validity.

**Mitigation:**
1. User study should test whether educators find value **even in low-vocabulary domains**.
2. If Condition B outperforms Condition A on Kaggle ASAG data (in user study), it validates dashboard utility independent of ML accuracy.
3. Add Discussion paragraph: "While ML accuracy plateaus in low-specificity domains, the VA system may still help educators via interactive exploration, independent of TRM precision."

**Recommendation:** Accept null result honestly. User study is the redemption arc.

---

### 🟡 **Issue 3: Verifier Model Contribution Not Isolated**
**Current:** C5_fix (KG + Verifier) shows 32.4% improvement. But how much is KG alone?

**Risk:** Reviewers ask "Is TRM doing the work, or is the fine-tuned Verifier?"

**Recommendation (Post–User Study):**
- Add brief ablation subsection: "KG component contributes X%, Verifier Y%, interaction Z%."
- Claim: TRM (knowledge graph grounding) is the conceptual novelty; Verifier is engineering.

---

### 🟡 **Issue 4: Missing Recruitment Timeline**
**Current:** User study protocol specifies timeline (April recruitment → May–August sessions → September analysis).  
**Risk:** If recruitment slips, entire paper slips. No buffer.

**Recommendation:**
- Begin recruitment **this week** (April 2026).
- Aim for 20 participants confirmed by May 31 (buffer for no-shows).
- Run sessions 2–3 per week July–August.
- Complete transcription by Sept 15 (allows 2 weeks for Paper 2 writeup).

---

## Strengths Summary ✅

1. **Novel Framing** — TRM + co-auditing paradigm is distinct from prior XAI work.
2. **Rigorous Formalism** — 5 formal definitions with clear notation.
3. **Honest Cross-Dataset Reporting** — Didn't hide Kaggle ASAG null result.
4. **Complete Study Design** — Protocol, analysis plan, qualitative coding scheme all locked.
5. **Implementable** — React dashboard fully built; event logging infrastructure ready.
6. **Mechanistic Insights** — Per-question error analysis (70% improvement at Relational level) shows where KG excels.

---

## Weaknesses & Open Questions ⚠️

1. **Causality Claim Risk** — "TRM exposes hallucinations" is strong. Null result on Kaggle ASAG complicates this.
2. **Generalization Claim** — Vision of TRM beyond grading is speculative (Section 7). Needs grounding.
3. **Node vs. Edge Adjacency** — Definition is underspecified. Impacts all metrics.
4. **Verifier Black Box** — Fine-tuned LLM's contribution not isolated. Is TRM or Verifier doing the work?
5. **Educator Sample Concerns** — N=15 per condition is small. Need representativeness statement (domain experts, diverse institutions).

---

## Checklist for Final Submission

### Before Writing §2 (Related Work)
- [ ] Identify 15–20 key citations (XAI, VA, Educational Analytics, IMT).
- [ ] Read recent LLM grading papers (G-Eval, Mizumoto 2023, Anthropic reasoning traces).
- [ ] Finalize IMT vs. co-auditing distinction (get consensus from team).

### Before Recruitment Starts
- [ ] Decide: Node-level or edge-level adjacency in TRM definition.
- [ ] Decide: How to frame potential Kaggle ASAG null result in Discussion (already done; stick with "domain boundary").
- [ ] Recruitment materials ready (email, Calendly, consent form).

### While User Study Runs
- [ ] Monitor SUS scores (spot-check every 5 sessions for unrealistic outliers).
- [ ] Verify event logs (POST /api/study/log receiving data).
- [ ] Check transcription quality (accuracy ≥ 95%).

### After User Study Data Collected
- [ ] Code transcripts (inter-rater reliability κ ≥ 0.70).
- [ ] Write §5b (SUS + think-aloud results).
- [ ] Finalize §6 Discussion (address user study findings).
- [ ] Write §2 Related Work.
- [ ] Polish §1, §7 (conclusion).
- [ ] Generate figures (SUS distribution, causal attribution frequency, example quotes).

### Final QA
- [ ] All tables formatted consistently.
- [ ] All citations complete (no "[Author, Year]" stubs).
- [ ] Figure captions include data source (e.g., "N=30 educators, Condition B").
- [ ] Word count ≤ 7,500 (VIS page limit).

---

## Recommendations for Gemini / Second Reviewer

1. **Read Sections 1, 3, 4 first** — Core framing and system design.
2. **Scrutinize §3 Formal Definitions** — Are the 5 definitions sufficient? Is adjacency well-defined?
3. **Challenge the Kaggle ASAG Framing** — Is "domain boundary" a credible explanation, or a retreat?
4. **Assess Causal Claims** — Does the paper overstate TRM's role in "exposing hallucinations"?
5. **Evaluate Study Design** — Is the qualitative analysis plan rigorous enough for VIS?

---

## File Structure

```
packages/concept-aware/docs/
├── paper_phase2_vis2027.tex          ← Main submission
├── PAPER2_REVIEW_DRAFT.md            ← This file
├── user_study_protocol_vis2027.md    ← Study execution guide
├── analysis_plan_qualitative.md      ← Qualitative analysis scheme
├── paper_phase1_ieee.tex             ← Paper 1 (ML accuracy)
├── paper_multidataset_table.tex      ← Supplementary ML results
└── references.bib                     ← BibTeX (to be populated)
```

---

## Next Steps (Action Items)

**This Week (April 17–24):**
- [ ] **Get Gemini feedback** on Sections 1, 3, 4 (TRM formalism + adjacency definition).
- [ ] **Finalize recruitment** (email draft, Calendly setup).
- [ ] **Submit Paper 1** to NLP/EdAI venue.

**Next Week (April 24–May 1):**
- [ ] **Launch recruitment** (send emails, post on SIGCSE list).
- [ ] **Implement backend logging** (POST /api/study/log endpoint).
- [ ] **Write §2 Related Work** (while recruitment runs asynchronously).

**May–August 2026:**
- [ ] **Conduct 30 user study sessions** (2–3 per week).
- [ ] **Transcribe & code** qualitative data (mid-August).
- [ ] **Run statistical analysis** (Mann-Whitney, Poisson GLM).

**September 2026:**
- [ ] **Write §5b** (User Study Results).
- [ ] **Finalize §6, §7** (Discussion, Conclusion).
- [ ] **Generate figures** (SUS distributions, causal attribution plots).
- [ ] **Target: Paper 2 ready for IEEE VIS 2027 submission** (hard deadline: TBD).

---

**END OF REVIEW DRAFT**

---

## How to Share This with Gemini

Copy the file path below and paste into a Claude session or use the link:

```
File: /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/PAPER2_REVIEW_DRAFT.md
```

Or open directly: **[PAPER2_REVIEW_DRAFT.md](file:///Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/PAPER2_REVIEW_DRAFT.md)**
