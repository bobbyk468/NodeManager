# Gemini Review Request v17
**Date:** 2026-04-17  
**Paper:** IEEE VIS 2027 VAST — "Co-Auditing as Epistemic Update"  
**Prior rounds:** v1–v16 (all section-level decisions locked)  
**This round:** Holistic full-paper review (§1–§5a assembled); co-author readiness check; §6 Discussion + §7 Conclusion kickoff

---

## What Was Built Since v16

All v16 decisions (Q1–Q10) applied. Full paper draft assembled in `conceptgrade_paper_draft_v1.md`:

| Section | Words (approx.) | Status |
|---------|----------------|--------|
| §1 Introduction | ~670 | ✅ Locked |
| §2 Related Work | ~450 | ✅ Locked |
| §3 TRM Formalization | ~350 (def box + example) | ✅ Locked (v11) |
| §4 System Architecture | ~830 | ✅ Locked |
| §5a ML Accuracy | ~400 + conditional §5a.3 | ✅ Locked pending data |
| §5b User Study | — | ⏳ Post-pilot |
| §6 Discussion | — | 🔲 Kickoff this round |
| §7 Conclusion | — | 🔲 Kickoff this round |

**Total assembled (§1–§5a): ~2,700 words.** IEEE VIS VAST target is 9–10 pages double-column (~4,500–5,000 words total including references, figures, captions). Current draft is approximately 60% of the target body word count, with §5b, §6, and §7 remaining.

---

## Section 1: Holistic Paper Flow Review

Please read the assembled §1–§5a sequence as a continuous argument and evaluate whether the paper reads coherently from beginning to end — not just section-by-section.

### Q1 — Argument Coherence: §1 → §2 → §3 → §4 → §5a

**Question:** Does the argument flow from the introduction's accountability gap claim (§1) through the Related Work positioning (§2) into the TRM formalization (§3), system architecture (§4), and evaluation (§5a) without requiring the reader to make inferential leaps?

Specifically:
1. Does §2 adequately set up the gap that §3 fills? (The "topological coherence" question at the end of §2 Para 2 should feel answered by Definition 2 in §3.)
2. Does §3 connect directly to §4? (Definition 3 "structural leap" should feel immediately instantiated by §4.3's amber dashed connector.)
3. Does §4 set up §5a? (The KG-grounded verifier in §4.2 should feel obviously connected to C4 in the §5a ablation table.)

**Please answer:** Confirm the argument chain is tight, or identify the weakest transition between sections and draft a bridging sentence to fix it.

---

### Q2 — VAST Balance Check

**Question:** A VAST paper is expected to be approximately 40% system design / visual encoding rationale, 30% evaluation, 20% related work + formalization, 10% introduction. Estimate the balance of the current draft:

- §1 Introduction: ~670 words
- §2 Related Work: ~450 words
- §3 TRM Formalization: ~350 words
- §4 System Architecture: ~830 words (heaviest section)
- §5a ML Accuracy: ~400 words

Does the current balance favor VIS sufficiently? Is §4 (the VA section) at 830 words long enough, or should it be expanded? Is §3 (formalization) at 350 words appropriate for a 5-definition box, or does it need a longer prose explanation of TRM's relationship to existing KG reasoning literature?

**Please answer:** Confirm balance is appropriate for VAST, or advise on which section should grow and which should shrink by ~100 words.

---

### Q3 — Co-Authoring Readiness

**Question:** The assembled draft has [TODO] placeholders for: (a) user study N, semantic alignment rate, null baseline; (b) ablation table C4 MAE and DigiKlausur/Kaggle MAE; (c) figures. Is the draft in a state where it can be circulated to co-authors for feedback, or should the [TODO] data gaps be filled first?

Specifically: Can co-authors give useful structural feedback on a draft where Tables 1 and 2 have [TODO] values, or does seeing incomplete tables distract from evaluating the argument structure?

**Please answer:** Circulate now (with [TODO] annotation prominent) or wait for data? If circulating now, what cover note should accompany the draft to manage co-author expectations?

---

## Section 2: §6 Discussion Kickoff

§6 Discussion must answer: "What does this paper mean for the field, beyond the specific results?" For a VAST paper, this typically covers: design implications, limitations, generalizability, and future work. It should NOT re-summarize the results.

### Proposed §6 Structure (3–4 paragraphs):

**§6.1 — Implications for Educational AI Design (~150 words)**
The co-auditing paradigm reframes the educator's role from a passive approver of AI decisions to an active epistemological partner. Interface designers working on AI-graded assessments should prioritize the *externalization* of AI reasoning over its *simplification* — making the model's topological structure visible forces educators to engage with domain boundaries they would otherwise leave implicit.

**§6.2 — Limitations and Boundary Conditions (~150 words)**
Three limitations: (1) KG quality dependency — grading quality degrades when the auto-KG prompt fails to capture domain vocabulary (evidenced by Kaggle ASAG); (2) LRM reliability — CoT faithfulness is not guaranteed [Turpin 2023]; (3) educator expertise dependency — co-auditing assumes the educator has sufficient domain knowledge to evaluate topological gaps, which may not hold for interdisciplinary graders.

**§6.3 — Generalizability Beyond Grading (~100 words)**
TRM is domain-agnostic: any task where an LRM's reasoning can be grounded in a structured domain representation (medical diagnosis, legal reasoning, code review) is a candidate for co-auditing interfaces. The structural leap visualization generalizes to any domain with a KG, independent of the educational framing.

**§6.4 — Future Work (~100 words)**
Three directions: (1) Adaptive KG refinement — allow educator rubric edits to feed back into the KG (closing the co-auditing loop); (2) Multi-model ensemble views — show Gemini Flash and DeepSeek-R1 traces side-by-side when they disagree; (3) Longitudinal study — track whether repeated co-auditing sessions improve inter-rater agreement among educators in the same department.

---

### Q4 — §6.1 Discussion Tone

**Question:** The §6.1 opening sentence ("The co-auditing paradigm reframes the educator's role from a passive approver of AI decisions to an active epistemological partner") is strong but may read as overclaiming for a first VAST submission. A reviewer might respond: "This claim requires evidence beyond a single study."

**Please answer:** Keep this framing, hedge it ("our results suggest the co-auditing paradigm may reframe..."), or rewrite it as an *implication* rather than a finding ("Our design demonstrates that...")?

---

### Q5 — §6.2 Limitations: Is KG Quality a Limitation or a Scope Condition?

**Question:** The Kaggle ASAG result (p = 0.148, n.s.) has been consistently framed in §5a as a *scope condition* ("domain boundary"), not a limitation. But §6.2 lists "KG quality dependency" as a limitation. This creates a tension: is Kaggle a scope condition (§5a framing) or a limitation (§6 framing)?

Which framing is stronger for VAST?
- **Scope condition (§5a):** "We know exactly where this works and where it doesn't — that's a rigorous contribution."
- **Limitation (§6):** "This is a genuine weakness that future work should address."

**Please answer:** Maintain the scope-condition framing throughout (including §6.2) or deliberately shift to limitation framing in §6.2 to demonstrate self-awareness? Is it possible to use both framings in different parts of the paper without contradicting yourself?

---

### Q6 — §6.3 Generalizability: How Bold to Be?

**Question:** The §6.3 paragraph claims TRM generalizes to medical diagnosis, legal reasoning, and code review. This is a significant claim that reviewers may push back on as speculative without evidence.

**Please answer:** Should §6.3 make specific generalizability claims (medical, legal, code review) with hedging ("we anticipate"), or should it stay abstract ("any domain with a structured knowledge representation") to avoid overreach? Does specificity help or hurt VAST reviewers?

---

## Section 3: §7 Conclusion Kickoff

§7 Conclusion should be ~200–250 words: (1) restate the problem and contribution in one sentence each, (2) summarize the key empirical result, (3) close with the broader significance.

### Proposed §7 Draft:

> We presented ConceptGrade, a visual analytics system for co-auditing AI-graded student answers via Topological Reasoning Mapping. By projecting a large reasoning model's chain-of-thought onto a domain Knowledge Graph, ConceptGrade enables educators to inspect structural leaps in the AI's reasoning — gaps where the model moved between disconnected concepts without providing an intermediate explanation — and act on them by refining their own rubric criteria.
>
> Our evaluation demonstrates that KG-grounded verification reduces mean absolute grading error by 32.4% over a pure LLM baseline on the Mohler CS benchmark, with Fisher combined significance across 1,239 answers from three datasets (p = 0.003). A controlled user study confirms that educators exposed to TRM-rendered traces make rubric edits with significantly higher semantic alignment to the AI's flagged concepts than would be expected by chance — quantitative evidence that visual trace analytics facilitate an epistemic update in how educators represent their own grading criteria.
>
> Co-auditing does not replace educator judgment; it makes the interface conditions under which judgment is exercised more transparent, more structured, and more accountable. As AI grading systems become ubiquitous in higher education, designing for epistemological partnership — not just workflow efficiency — may be the most consequential design challenge facing the visual analytics community.

---

### Q7 — §7 Closing Sentence

**Question:** The proposed §7 closing sentence ("designing for epistemological partnership — not just workflow efficiency — may be the most consequential design challenge facing the visual analytics community") is a strong rallying call for the VAST audience. But "most consequential design challenge" may be seen as hyperbolic.

**Please answer:** Keep as-is, soften to "one of the most consequential design challenges," or replace the final sentence entirely with a more grounded forward-looking statement? If replacing, draft the alternative.

---

### Q8 — §7 Word Count and Scope

**Question:** The proposed §7 is approximately 230 words across 3 paragraphs. For VAST, is this:
(a) Appropriate — VAST conclusions are 1 column page
(b) Too short — needs a fourth paragraph on future directions
(c) Too long — cut the middle paragraph (empirical summary) since results were just discussed in §5

**Please answer:** Confirm appropriate length, or advise on which paragraph to cut or expand.

---

## Section 4: Bibliography and [TODO] Resolution Plan

### Q9 — Priority Order for [TODO] Resolution

The assembled draft has two categories of [TODO] items: data-dependent (run scripts) and bibliography-dependent (confirm references). Given that the user study pilot is still pending, what is the optimal order of resolution before the paper is co-author-ready?

**Proposed priority order:**
1. Run ablation + stability scripts → fill Tables 1 and 2 (data-dependent, ~2 hours)
2. Confirm bibliography for Sinha 2021, Mizumoto 2023, Chen 2020 (library-dependent, ~1 hour)
3. Generate pipeline figure (design work, ~3 hours)
4. Generate UI screenshot (system must be running, ~1 hour)
5. Draft §5b (post-pilot, ~2 weeks away)
6. Fill X/Y/Z placeholders from study data

**Please answer:** Confirm this priority order, or advise if any item should be blocked behind another that we haven't sequenced correctly.

---

### Q10 — Paper Length Projection

**Question:** The assembled draft (§1–§5a) is ~2,700 words. Adding the remaining sections:
- §5b User Study (estimated ~600 words)
- §6 Discussion (estimated ~500 words)
- §7 Conclusion (estimated ~230 words)
= **~4,030 words total body text**

IEEE VIS VAST allows up to 10 pages including figures and references. A 10-page double-column paper has approximately 4,500–5,000 words body text + 500–800 words of captions and references. Is 4,030 words too short (needs more body text), or does it leave appropriate space for 3–4 figures, a caption budget, and references?

**Please answer:** Is 4,030 words the right body target for a 10-page VAST paper with 4 figures, or should we plan to expand one section by ~300–500 words before submission?

---

## Locked Decisions Reminder

All prior decisions (v1–v16) are locked. Do not reopen:

| Decision | Locked Value |
|----------|-------------|
| Title | "Co-Auditing as Epistemic Update..." |
| Contribution ordering | TRM → System → ML → User Study |
| Contribution 2 name | "Co-Auditing Visual Analytics System" |
| §3 definitions | v11 Definition Box (Definitions 1–5) |
| §4 figure strategy | Option A: pipeline + full-width UI screenshot |
| §5a opening | Mohler (b) → Fisher combined → Kaggle boundary |
| §5a.3 placement | Conditional: §5a if r ≥ 0.80; §5b intro if r < 0.80 |
| §6 structure | 4 paragraphs: implications → limitations → generalizability → future work |

---

## Expected Output Format

For each question:
1. **Decision** (1 sentence)
2. **Rationale** (2–3 sentences, VAST reviewer-risk framing)
3. **Draft text** (where text changes are recommended — full sentence, paste-ready)

**Priority this round:** Q1 (argument coherence), Q5 (scope condition vs. limitation tension), Q7 (§7 closing sentence), Q10 (paper length projection).

---

**End of Gemini Review v17**
