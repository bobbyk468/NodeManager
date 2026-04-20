# Gemini Review Request v18
**Date:** 2026-04-17  
**Paper:** IEEE VIS 2027 VAST — "Co-Auditing as Epistemic Update"  
**Prior rounds:** v1–v17 (all decisions locked)  
**This round:** Final pre-submission polish — §6 Discussion + §7 Conclusion review; bibliography completion; §4 organic expansion; §5b scaffold

---

## What Was Built Since v17

All v17 Q1–Q10 decisions applied. Paper is now fully assembled (§1–§7, excluding §5b):

| Section | Words | Status |
|---------|-------|--------|
| §1 Introduction | ~670 | ✅ Locked |
| §2 Related Work | ~450 | ✅ Locked |
| §3 TRM Formalization | ~350 | ✅ Locked |
| §4 System Architecture | ~840 | ✅ Locked (§4.1 bridge sentence added) |
| §5a ML Accuracy | ~400 | ✅ Locked pending data |
| §5b User Study | — | ⏳ Post-pilot |
| §6 Discussion | ~500 | ✅ Locked |
| §7 Conclusion | ~230 | ✅ Locked |
| **Total** | **~3,440** | **On track for 10-page VAST** |

---

## Section 1: §6 Discussion — Prose Review

**Full §6 text for review:**

> **§6.1 Implications for Educational AI Design**
> Our findings suggest that the co-auditing paradigm can reframe the educator's role from a passive approver of AI decisions to an active epistemological partner. Conventional AI grading interfaces present a verdict to be accepted or overridden; ConceptGrade's design demonstrates that presenting the topological structure of the AI's reasoning chain forces educators to engage with domain boundaries they would otherwise leave implicit. When an educator clicks a CONTRADICTS chip and updates their rubric, they are not correcting the model — they are articulating a criterion that was previously tacit. This externalization is the core pedagogical contribution of the co-auditing design: the interface makes explicit what was implicit, not by simplifying the model's behavior, but by situating it within a domain representation the educator can interrogate. Interface designers working on AI-assisted assessment should prioritize *transparency of reasoning topology* over *simplicity of output*, recognizing that educator trust is built through shared understanding, not reduced cognitive load.
>
> **§6.2 Limitations and Boundary Conditions**
> The Kaggle ASAG evaluation defines a clear boundary condition for TRM: grading quality degrades when the domain vocabulary lacks ontological specificity. In elementary science, where colloquial terms like "energy" and "force" carry multiple overlapping meanings, the KG cannot produce the node-level distinctions necessary for grounding-based verification — a property of the domain, not the system. Two additional limitations apply to the system broadly. First, the LRM Verifier's chain-of-thought is not guaranteed to be faithful: recent work demonstrates that stated reasoning can diverge from the computation that produced the output [Turpin 2023], meaning the topological structure ConceptGrade visualizes may occasionally misrepresent the model's actual inference. Second, co-auditing assumes the educator has sufficient domain expertise to evaluate whether a structural leap represents a genuine conceptual gap or a legitimate reasoning shortcut. In interdisciplinary grading contexts, or with inexperienced graders, this assumption may not hold. Both limitations are directions for future work, not architectural failures.
>
> **§6.3 Generalizability**
> We hypothesize that TRM is generalizable to any analytical task where an LRM's reasoning can be grounded in a structured formal ontology, independent of the educational grading context. The three structural properties that made the educational domain productive — a well-defined concept vocabulary, typed relational edges between concepts, and a grading task that rewards conceptual coverage — are shared by any domain with an established formal knowledge representation. This suggests that the co-auditing interface pattern, including the structural leap visualization and bidirectional brushing design, is a reusable template for domains where reasoning transparency and human expert alignment are both required.
>
> **§6.4 Future Work**
> Three directions emerge from this work. First, *adaptive KG refinement*: educator rubric edits could feed back into the KG as new concept-relation hypotheses, closing the co-auditing loop and enabling the domain model to evolve through use. Second, *multi-model ensemble views*: when Gemini Flash and DeepSeek-R1 produce divergent traces for the same answer, showing both side-by-side would expose model-dependent reasoning gaps without requiring the educator to choose a single ground truth. Third, *longitudinal inter-rater alignment studies*: tracking whether repeated co-auditing sessions improve rubric consistency across educators in the same department would provide direct evidence for the epistemic update claim, moving from cross-sectional to longitudinal causal measurement.

---

### Q1 — §6.1 Implication Claim Strength

**Question:** The §6.1 paragraph's central design implication is: "prioritize *transparency of reasoning topology* over *simplicity of output*." This is a strong, actionable design principle. Is this the right level of generalization, or is it too specific to be a broadly applicable design implication? Should it be framed as a design principle (prescriptive — "designers should...") or a design finding (descriptive — "our study found that...")?

**Please answer:** Keep prescriptive framing ("should prioritize") or reframe as descriptive ("our findings indicate that educators responded to transparency of reasoning topology over simplicity of output")? Justify for VAST audience.

---

### Q2 — §6.2 LRM Faithfulness Limitation

**Question:** The faithfulness limitation ([Turpin 2023]) is cited in §6.2 but also appears in §2 Related Work. VAST reviewers may notice this dual citation and ask: "If you know the model's reasoning is potentially unfaithful, why build a visualization of it?"

Is there a one-sentence pre-emption in §6.2 that addresses this concern? E.g., "Even if individual steps are unfaithful, the aggregate topological structure of a 20–40 step trace is more robust to single-step faithfulness failures than a single-sentence verdict."

**Please answer:** Add this pre-emption sentence or leave the limitation undefended? If adding, confirm the robustness argument is empirically sound (does a 20–40 step trace statistically average out single-step faithfulness failures?).

---

### Q3 — §6.4 Future Work: Adaptive KG Citation

**Question:** The adaptive KG refinement direction ("educator rubric edits could feed back into the KG") is a novel proposed direction. Is there a citation for *interactive KG refinement* or *human-in-the-loop ontology construction* that would ground this as a known technical challenge rather than a vague aspiration?

**Please answer:** Provide 1–2 citations for interactive KG or ontology refinement, or confirm the direction can stand without a citation as a forward-looking research proposal.

---

## Section 2: §7 Conclusion — Final Check

**Full §7 text for review:**

> We presented ConceptGrade, a visual analytics system for co-auditing AI-graded student answers via Topological Reasoning Mapping. By projecting a large reasoning model's chain-of-thought onto a domain Knowledge Graph, ConceptGrade enables educators to inspect structural leaps in the AI's reasoning — gaps where the model moved between disconnected concepts without providing an intermediate explanation — and act on them by refining their own rubric criteria in real time.
>
> Our evaluation demonstrates that KG-grounded verification reduces mean absolute grading error by 32.4% over a pure LLM baseline on the Mohler CS benchmark, with Fisher combined significance across 1,239 answers from three datasets (p = 0.003). A controlled user study confirms that educators exposed to TRM-rendered traces make rubric edits with significantly higher semantic alignment to the AI's flagged concepts than would be expected by chance — quantitative evidence that visual trace analytics facilitate an epistemic update in how educators represent their own grading criteria.
>
> Co-auditing does not replace educator judgment; it makes the interface conditions under which judgment is exercised more transparent, more structured, and more accountable. As AI grading systems become ubiquitous in higher education, designing for epistemological partnership — not just workflow efficiency — represents a critical challenge for the visual analytics community.

---

### Q4 — §7 Para 2: Premature User Study Claim

**Question:** §7 Para 2 states: "A controlled user study confirms that educators...make rubric edits with significantly higher semantic alignment." But the user study data is not yet available — the pilot hasn't run. This sentence is written as if the result is known.

For co-author review, should this sentence be:
(a) Left as-is (with the understanding it will be filled with real data post-pilot)
(b) Replaced with a forward-projection: "We anticipate that a controlled user study will confirm..." 
(c) Removed entirely from §7 until study data is available

**Please answer:** Which option protects the draft's integrity for co-author review without misrepresenting study completion?

---

### Q5 — §7 Closing Sentence Calibration

**Question:** The final sentence is now: "designing for epistemological partnership — not just workflow efficiency — represents a critical challenge for the visual analytics community." Is "critical challenge" sufficiently strong to close a VAST paper on a high note, or does it undersell the community call-to-action? Compare with "represents a defining challenge" or "should be a central research agenda for the visual analytics community."

**Please answer:** Keep "critical challenge," upgrade to "defining challenge," or rewrite the closing entirely for maximum impact.

---

## Section 3: §4 Organic Expansion (~100–150 words)

Per v17 Q2 decision, §4.3 (Visual Encodings) and §4.4 (Interactions) should grow organically by ~100–150 words to hit the VAST balance target of ~1,000 words for §4 total. The suggested addition: more depth on the force-directed graph layout constraints.

### Proposed §4.3 Addition (KG Subgraph Panel — expand by ~80 words):

Current text ends: "...creating a visual link between the trace and the KG topology."

**Proposed addition:**
> "The force-directed layout [Fruchterman & Reingold 1991] is parameterized to minimize edge crossings within a bounded canvas, ensuring the ego-graph remains readable for neighborhoods up to 15 concepts. Concepts with no CONTRADICTS association are rendered at reduced opacity, directing the educator's attention to the subset of the KG topology that is directly implicated in the current answer's reasoning gaps. This selective emphasis avoids the cognitive overload that arises from presenting the full domain KG, which can span hundreds of nodes across a dataset."

---

### Q6 — §4.3 KG Subgraph Expansion Approval

**Question:** Does the proposed §4.3 addition (reduced opacity for non-CONTRADICTS concepts, 15-concept ego-graph bound, force-directed citation) add meaningful design rationale, or does it add length without analytical value?

**Please answer:** Approve addition as-is, trim to 40 words, or replace with a different design rationale detail (e.g., edge line style encoding justification)?

---

## Section 4: §5b User Study — Scaffold for Later Drafting

We are not drafting §5b now, but the scaffold should be locked to prevent structural rework later.

### Proposed §5b Structure (to be filled post-pilot):

```
§5b.1 Study Design (~150 words)
      Participants: N = [TODO] TAs/instructors who have graded student work
      Condition A: blank rubric panel (no trace visualization)
      Condition B: full ConceptGrade interface (VerifierReasoningPanel + RubricEditorPanel)
      Task: grade 10 student answers from Mohler/DigiKlausur; think-aloud protocol

§5b.2 Hypotheses and Metrics (~100 words)
      H1: Condition B shows higher within_30s causal attribution rate
          (GEE Binomial/Logit, primary window = 30 s, moderator = trace_gap_count)
      H2: Condition B semantic_alignment_rate_manual > hypergeometric null
          (primary metric; Click-to-Add reported separately as H2-UI)
      SUS: System Usability Scale (Condition B only)

§5b.3 Results (~200 words) — [POST-PILOT]
      H1 result: OR = [TODO], GEE p = [TODO], working correlation ρ = [TODO]
      H2 result: alignment rate = [TODO]% vs null = [TODO]%, p = [TODO]
      Gap count moderation: trace_gap_count × condition interaction p = [TODO]
      SUS score: [TODO]/100

§5b.4 Qualitative Findings (~150 words) — [POST-PILOT]
      Think-aloud patterns: rubric-first vs trace-first strategies
      Benchmark seed performance: fluent_hallucination detection rate Cond B vs A
```

---

### Q7 — §5b.4 Qualitative Findings: Include or Exclude?

**Question:** §5b.4 proposes qualitative findings from think-aloud protocols. VAST papers vary in how much qualitative analysis they include alongside quantitative user study results. For our study design:
- Think-aloud data is available from the pilot (2–3 participants)
- The pre-registered analysis is quantitative (GEE, hypergeometric)
- Qualitative findings are exploratory, not pre-registered

**Please answer:** Should §5b.4 (qualitative findings) be included as a subsection of §5b, or moved to §6 Discussion as an exploratory finding? Does including non-pre-registered qualitative data in the results section risk reviewer criticism?

---

### Q8 — §5b.2 SUS Score Reporting

**Question:** The System Usability Scale (SUS) is a secondary outcome measure (Condition B only, not pre-registered). Should SUS be:
(a) Reported in §5b.3 results as a table row alongside H1/H2
(b) Moved to a supplemental appendix
(c) Mentioned only in §6 Discussion as a usability validation

**Please answer:** Optimal placement for SUS within a VAST paper that is primarily arguing for a co-auditing paradigm (not a usability study)?

---

## Locked Decisions Reminder

| Decision | Locked Value |
|----------|-------------|
| §6.1 opening | "Our findings suggest that the co-auditing paradigm **can** reframe..." (hedged) |
| §6.2 heading | "Limitations and Boundary Conditions" |
| §6.3 scope | Abstract domain properties (no specific field names) |
| §7 closing | "represents a critical challenge for the visual analytics community" |
| §5b scaffold | §5b.1–§5b.4 structure locked; prose filled post-pilot |
| §4 expansion | Force-directed graph rationale + opacity reduction (~80 words in §4.3) |

---

## Expected Output Format

For each question:
1. **Decision** (1 sentence)
2. **Rationale** (2–3 sentences)
3. **Draft text** (if text changes recommended — full sentence, paste-ready)

**Priority this round:** Q2 (faithfulness limitation pre-emption), Q4 (§7 premature user study claim), Q5 (closing sentence calibration), Q7 (qualitative findings placement).

---

**End of Gemini Review v18**
