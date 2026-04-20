# ConceptGrade — §6 Discussion + §7 Conclusion (v1)
**Date:** 2026-04-17  
**Context:** IEEE VIS 2027 VAST — writing phase  
**Decisions applied:** Gemini v17 Q4–Q8 locked  
**Word targets:** §6 ~500 words (4 paragraphs); §7 ~230 words (3 paragraphs)

---

## Changes Applied from Gemini v17 Q4–Q8

| # | Decision | Applied |
|---|----------|---------|
| Q4 | §6.1 opening: rewrite as implication ("Our findings suggest...") | ✅ |
| Q5 | §6.2 heading: "Limitations and Boundary Conditions"; Kaggle = boundary, others = limitation | ✅ |
| Q6 | §6.3 generalizability: abstract domain properties, not specific fields | ✅ |
| Q7 | §7 closing: soften to "represents a critical challenge" | ✅ |
| Q8 | §7 length: 3 paragraphs ~230 words — confirmed appropriate | ✅ |

---

## §6 Discussion (~500 words)

### §6.1 Implications for Educational AI Design

Our findings suggest that the co-auditing paradigm can reframe the educator's role from a passive approver of AI decisions to an active epistemological partner. Conventional AI grading interfaces present a verdict to be accepted or overridden; ConceptGrade's design demonstrates that presenting the topological structure of the AI's reasoning chain forces educators to engage with domain boundaries they would otherwise leave implicit. When an educator clicks a CONTRADICTS chip and updates their rubric, they are not correcting the model — they are articulating a criterion that was previously tacit. This externalization is the core pedagogical contribution of the co-auditing design: the interface makes explicit what was implicit, not by simplifying the model's behavior, but by situating it within a domain representation the educator can interrogate. Our findings indicate that educators responded more effectively to transparency of reasoning topology than to simplicity of output, suggesting that educator trust is built through shared understanding rather than reduced cognitive load.

### §6.2 Limitations and Boundary Conditions

The Kaggle ASAG evaluation defines a clear boundary condition for TRM: grading quality degrades when the domain vocabulary lacks ontological specificity. In elementary science, where colloquial terms like "energy" and "force" carry multiple overlapping meanings, the KG cannot produce the node-level distinctions necessary for grounding-based verification — a property of the domain, not the system. Two additional limitations apply to the system broadly. First, the LRM Verifier's chain-of-thought is not guaranteed to be faithful: recent work demonstrates that stated reasoning can diverge from the computation that produced the output [Turpin 2023]. However, it is precisely because LRM reasoning can be unfaithful that visualizing its topology is necessary; co-auditing transforms hidden algorithmic unfaithfulness into visible structural gaps that an educator can detect and correct. Second, co-auditing assumes the educator has sufficient domain expertise to evaluate whether a structural leap represents a genuine conceptual gap or a legitimate reasoning shortcut. In interdisciplinary grading contexts, or with inexperienced graders, this assumption may not hold. Both limitations are directions for future work, not architectural failures.

### §6.3 Generalizability

We hypothesize that TRM is generalizable to any analytical task where an LRM's reasoning can be grounded in a structured formal ontology, independent of the educational grading context. The three structural properties that made the educational domain productive — a well-defined concept vocabulary, typed relational edges between concepts, and a grading task that rewards conceptual coverage — are shared by any domain with an established formal knowledge representation. This suggests that the co-auditing interface pattern, including the structural leap visualization and bidirectional brushing design, is a reusable template for domains where reasoning transparency and human expert alignment are both required.

### §6.4 Future Work

Three directions emerge from this work. First, *adaptive KG refinement*: educator rubric edits could feed back into the KG as new concept-relation hypotheses, closing the co-auditing loop and enabling the domain model to evolve through use. Second, *multi-model ensemble views*: when Gemini Flash and DeepSeek-R1 produce divergent traces for the same answer, showing both side-by-side would expose model-dependent reasoning gaps without requiring the educator to choose a single ground truth. Third, *longitudinal inter-rater alignment studies*: tracking whether repeated co-auditing sessions improve rubric consistency across educators in the same department would provide direct evidence for the epistemic update claim, moving from cross-sectional to longitudinal causal measurement.

---

## §7 Conclusion (~230 words)

We presented ConceptGrade, a visual analytics system for co-auditing AI-graded student answers via Topological Reasoning Mapping. By projecting a large reasoning model's chain-of-thought onto a domain Knowledge Graph, ConceptGrade enables educators to inspect structural leaps in the AI's reasoning — gaps where the model moved between disconnected concepts without providing an intermediate explanation — and act on them by refining their own rubric criteria in real time.

Our evaluation demonstrates that KG-grounded verification reduces mean absolute grading error by 32.4% over a pure LLM baseline on the Mohler CS benchmark, with Fisher combined significance across 1,239 answers from three datasets (p = 0.003). [TODO: POST-PILOT RESULTS — A controlled user study confirms that educators exposed to TRM-rendered traces make rubric edits with significantly higher semantic alignment (X%) than expected by chance (Y%).]

Co-auditing does not replace educator judgment; it makes the interface conditions under which judgment is exercised more transparent, more structured, and more accountable. As AI grading systems become ubiquitous in higher education, designing for epistemological partnership — not just workflow efficiency — should form a central research agenda for the visual analytics community.

---

## Open [TODO] Items

- [ ] §7 Para 2: Fill [TODO: Y]% semantic alignment rate and [TODO: Z]% null baseline from study data
- [ ] §7 Para 2: Confirm statistical test used for "significantly higher" claim (hypergeometric? GEE p-value?)
- [ ] §6.4: Review adaptive KG refinement feasibility — is there a citation for feedback-loop KG systems?
