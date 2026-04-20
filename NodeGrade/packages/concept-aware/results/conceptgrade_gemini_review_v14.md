# Gemini Review Request v14
**Date:** 2026-04-17  
**Paper:** IEEE VIS 2027 VAST — "Co-Auditing as Epistemic Update — How Visual Trace Analytics Force Educators to Externalize Implicit Rubric Mental Models"  
**Prior rounds:** v1–v13 (all decisions locked)  
**This round:** (1) Introduction v13 quality check; (2) Related Work structure; (3) §4 System Architecture kickoff; (4) §5a ML Accuracy kickoff

---

## What Changed Since v12

All five Q1–Q5 edits applied to Introduction v13:

| Q | Decision (locked in v12) | Applied in v13 |
|---|--------------------------|----------------|
| Q1 | Add CoT concession sentence ("not that reasoning is wrong, but topological structure is invisible") | ✅ Para 2, sentence 3 |
| Q2 | Cite Kulesza 2012 + Bansal 2019 for "implicit mental models," not Norman 1988 | ✅ Para 3, end of sentence |
| Q3 | Use [TODO: X/Y/Z] placeholders with annotation | ✅ Eval paragraph |
| Q4 | Narrow "first approach" to "first VA approach in educational grading context" | ✅ Contribution 1 |
| Q5 | Cut LIME/SHAP paragraph, trim eval para, target 650 words | ✅ Result: ~640 words |

---

## Section 1: Introduction v13 Quality Check

**Please paste Introduction v13 text here before sending to Gemini:**

> [PASTE: contents of conceptgrade_introduction_draft_v13.md §1 Introduction]

---

### Q1 — Transition from Para 1 to Para 2

**Question:** Does the transition from para 1 ("we argue the missing link is not a better model, but a better interface") to para 2 ("the opacity problem is structural") feel direct and well-motivated? Or does it need a bridging sentence that explains why structural opacity requires an interface-level solution specifically?

**What we're watching for:** A reviewer might ask why a better *model* (e.g., more faithful CoT) wouldn't solve the problem. The concession sentence in para 2 gestures at this but may not fully close the gap.

**Please answer:** Is the para 1 → para 2 transition tight enough, or should we add one bridging sentence? If so, draft it.

---

### Q2 — Kulesza 2012 + Bansal 2019 Citations

**Question:** We now cite Kulesza 2012 ("Principles of Explanatory Debugging") and Bansal 2019 ("Updates in Human-AI Teams") for "implicit mental models." Are these the right citations here? Specifically:
- Kulesza 2012 is about explanatory debugging in interactive ML — does it match "implicit mental model" in the grading context?
- Bansal 2019 is about how AI updates change human mental models — does it support "educator refines their domain representation"?

**Fallback option:** If neither citation fits tightly, is "implicit mental models" sufficiently established in the HCI-VA community not to require a citation at all?

**Please answer:** Keep both citations, drop one, or drop both and treat as community jargon. Justify with reviewer risk analysis.

---

### Q3 — [TODO] Placeholder Optics

**Question:** The evaluation paragraph now reads: "a semantic alignment rate of [TODO: Y]% versus a hypergeometric null of [TODO: Z]%." This is appropriate for internal drafts but will need to be replaced before submission. Are there any other placeholder-like constructions in v13 (e.g., "Figure X", "N = X educators") that should be explicitly flagged with [TODO] for clarity?

**Please answer:** List all [TODO] markers that should be added to v13 before circulating to co-authors.

---

### Q4 — Contribution Bullet Ordering

**Question:** The four contribution bullets are currently ordered: TRM (formal) → Interface (system) → ML Accuracy (evidence) → User Study (evaluation). IEEE VIS VAST reviewers typically expect a "why should I care about this system?" argument early. Should we reorder to: Interface first, then TRM, then evidence? Or is the current order (technique → system → evidence) standard for VAST?

**Please answer:** Keep current order or reorder? Justify.

---

### Q5 — "Bidirectional Co-Auditing Interface" vs "Co-Auditing System"

**Question:** Contribution 2 is currently titled "Bidirectional Co-Auditing Interface." The word "bidirectional" appears twice in the contribution list (also implicitly in contribution 1). Should contribution 2 be retitled to "Co-Auditing Visual Analytics System" to avoid redundancy and make the system-level contribution more prominent?

**Please answer:** Keep "Bidirectional Co-Auditing Interface" or rename to "Co-Auditing Visual Analytics System"?

---

## Section 2: Related Work Structure

We need to draft §2 Related Work next. The paper argues ConceptGrade is novel along three dimensions: (a) knowledge-grounded LRM grading, (b) topological reasoning visualization, (c) co-auditing paradigm. Each dimension needs a paragraph.

### Q6 — Related Work Paragraph Ordering

**Proposed §2 structure (3–4 paragraphs):**
1. **Automated short-answer grading** — Classic NLP → BERT → LRM approaches; performance ceiling reached; accountability gap introduced
2. **Explainable AI and reasoning transparency** — LIME/SHAP (token attribution), faithfulness [Lanham 2023], CoT evaluation [Wei 2022]; why these don't expose topological structure
3. **Visual analytics for AI transparency** — KG-grounded visualization, concept maps in education [Novak 1984], VA for NLP outputs; gap: none project LRM reasoning chains
4. **Human-AI collaboration models** — Assistive grading [cite], IMT [Simard 2017], explanatory debugging [Kulesza 2012]; co-auditing as a new paradigm

**Question:** Is this 4-paragraph structure appropriate for VAST? VAST papers typically have shorter Related Work (1–1.5 columns). Should any of these be merged or cut?

---

### Q7 — Key References to Add

**Question:** Are there any critical references missing from the proposed Related Work structure above? Specifically:

1. **LRM faithfulness:** We cite Lanham 2023. Should we also cite Turpin 2023 ("Language models don't always say what they think") on CoT unfaithfulness?
2. **KG-grounded NLG evaluation:** We reference Ji 2023 ("Survey of hallucination"). Should we also cite Mallen 2023 (PopQA) or Shi 2023 (FLARE) for grounding?
3. **Educational VA:** What are the 2–3 best citations for visual analytics in educational assessment contexts that we should position against?
4. **Co-auditing paradigm:** Is there any prior work that uses the term "co-auditing" or a close equivalent that we need to cite and distinguish from?

**Please answer:** For each of the 4 sub-questions, confirm the citation or suggest a better one. Flag any "must cite" papers that reviewers will expect to see.

---

## Section 3: §4 System Architecture Kickoff

We are ready to draft §4. The section must describe the end-to-end ConceptGrade pipeline and the three-panel UI.

### Q8 — §4 Subsection Structure

**Proposed §4 outline (one-pass draft input):**

```
§4.1  Pipeline Overview (figure + 1 paragraph)
        LRM → Trace Parser → TRM Projection → VisualizationSpec → React Dashboard
§4.2  LRM Verifier (Gemini Flash / DeepSeek-R1)
        Input: question + student answer + KG concept list
        Output: ParsedStep[] with kg_nodes, classification, step_id
§4.3  Knowledge Graph Construction
        Auto-KG prompt + REL_TYPE_REMAP + GENERIC_CONCEPT_STOPLIST
        Per-dataset statistics: #concepts, #edges, density
§4.4  TRM Projection & Gap Detection
        Definition 1–4 instantiated (φ, adjacency, structural leap, leap count)
        hasTopologicalGap() implementation detail
§4.5  Visual Analytics Interface
        Three linked panels (trace viewer, KG subgraph, rubric editor)
        Bidirectional brushing via DashboardContext
        Click-to-Add interaction (zero-lexical-ambiguity attribution)
§4.6  Study Instrumentation
        RubricEditPayload (17 fields), rolling 60-second CONTRADICTS window
        Condition A/B gating
```

**Question:** Is this 6-subsection structure appropriate for VAST, or is it too implementation-heavy? VAST reviewers want design rationale, not code-level detail. Which subsections should be compressed or moved to a supplemental?

---

### Q9 — Figure Strategy for §4

**Question:** What figures should §4 contain? Options:

- **Option A (Recommended):** One high-level pipeline figure (boxes: KG → LRM → Trace Parser → TRM → Dashboard) + one annotated screenshot of the three-panel UI
- **Option B:** Separate figures for pipeline, KG subgraph, trace panel, rubric editor (4 figures total — likely too many for VAST's column budget)
- **Option C:** Single composite figure with pipeline on the left half and UI screenshot on the right half

**For the UI screenshot:** The most compelling frame to capture is a CONTRADICTS step (amber gap indicator visible) with the rubric editor chip pulsing. This directly illustrates the co-auditing moment described in the paper.

**Please answer:** Confirm Option A or choose Option C; and advise on the figure caption strategy (should the caption walk through the co-auditing flow step-by-step, or be brief with pointers to text?).

---

## Section 4: §5a ML Accuracy Kickoff

All accuracy data is available. We are ready to draft §5a without further experiments.

### Q10 — §5a Results Presentation

**Available numbers:**
- Mohler (CS): C5_fix MAE = 0.2229, C_LLM MAE = 0.3300, Wilcoxon p = 0.0013, N = 120
- DigiKlausur (NN): improvement p = 0.049, N = 646
- Kaggle ASAG (Science): p = 0.148 (n.s.), N = 473
- Fisher combined: p = 0.003 across 1,239 answers

**Component ablation available:** C1 (keyword) → C2 (+ chain) → C3 (+ bloom) → C4 (+ verifier, p < 0.0001) → C5 (+ fix)

**Stability analysis:** Gemini Flash vs DeepSeek-R1 cross-model TRM correlation (target r > 0.80; result pending run of stability_analysis.py)

**Question:** For §5a, should we:
(a) Lead with the Fisher combined p = 0.003 as the headline result, then break down by dataset?
(b) Lead with the Mohler ablation (strongest single-dataset result), then show generalization to other datasets?
(c) Lead with the Kaggle ASAG boundary condition ("where KG grading fails and why") to frame the scope of the contribution?

**Also:** The stability analysis result (cross-model TRM correlation) is currently pending. Should §5a include a "Stability Analysis" paragraph (§5a.3) showing TRM is model-independent? If so, should it report r even if < 0.80 (with explanation), or gate the paragraph on the result being significant?

**Please answer:** Choose (a), (b), or (c) for §5a opening; advise on stability analysis paragraph inclusion and gating strategy.

---

## Locked Decisions Reminder (Do Not Re-Open)

These are confirmed from v8–v13 and must not be re-litigated:

| Decision | Locked Value |
|----------|-------------|
| Primary causal window | 30 seconds |
| H2 primary metric | semantic_alignment_rate_manual |
| H2 UI-assisted | semantic_alignment_rate_cta (reported separately) |
| Condition A | Blank rubric panel (IRB amendment filed) |
| Node-only adjacency | Nᵢ ∩ Nᵢ₊₁ = ∅ only; edge type NOT a criterion |
| Grounding density | Secondary metric; not in GEE primary model |
| Alias dict scope | CS + NN only (not science) |
| Levenshtein threshold | 0.80 |
| GEE family | Binomial(Logit), Exchangeable working correlation |
| Kaggle ASAG | Boundary condition, not failure |
| Cross-model validation | "Stability Analysis" terminology (not "ablation") |
| Writing order | §1 → §3 → §4 → §5a → §5b |

---

## Expected Output Format

For each question, please provide:
1. **Decision** (1–2 sentences): What should we do?
2. **Rationale** (2–3 sentences): Why — specifically, what reviewer risk does this mitigate?
3. **Draft text** (if applicable): Suggested wording for any text changes

**Priority:** Q1, Q4, Q9, Q10 are highest priority for the next writing session. Q6 and Q7 can be deferred to the Related Work drafting session.

---

**End of Gemini Review v14**
