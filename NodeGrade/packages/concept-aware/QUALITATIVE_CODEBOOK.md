# Qualitative Coding Codebook

**Study:** ConceptGrade Dashboard - Educator Think-Aloud Analysis  
**Coding Scheme:** CA/SA/TC/II (4 themes)  
**Version:** 1.0  
**Date Created:** May 7, 2026  
**Last Updated:** _________________

---

## Overview

This codebook defines the four qualitative coding themes used to analyze think-aloud transcripts from the ConceptGrade user study. Each theme captures a distinct dimension of how educators engage with the system.

**Unit of Analysis:** Code segments (phrases, sentences, or short paragraphs expressing a single idea)

**Coding Approach:** Open coding with preset categories (deductive + inductive hybrid)

---

## Theme 1: Causal Attribution (CA)

### Definition
Explicit references to the system's reasoning traces, knowledge graph, or visualizations as a *reason* for an action or insight. The educator directly attributes their understanding to evidence from the system.

### Indicators
- Uses phrases like: "because I saw...", "the trace showed...", "the KG told me...", "the visualization made it clear..."
- Directly quotes or paraphrases system output
- Links system evidence to decision-making
- Shows causal inference: System output → Mental model update → Action

### Examples (Code)

**INCLUDE:**
1. "I noticed the reasoning trace showed a misconception about recursion, so I added that to the rubric."
   - Code: **CA** (attribution to trace)

2. "The KG visualization highlighted that students confuse linked lists with arrays. That's why I'm emphasizing the pointer concept."
   - Code: **CA** (attribution to KG viz)

3. "The system flagged zero-grounded steps, which means the student didn't justify their answer. That helped me see the gap."
   - Code: **CA** (attribution to system insight)

**DO NOT INCLUDE:**
1. "I think recursion is a hard concept anyway."
   - Code: None (no system attribution)

2. "I changed the rubric because it needed clarification."
   - Code: None (vague reasoning, no system reference)

3. "The colors made the interface look nice."
   - Code: None (aesthetic comment, not causal to task)

### Decision Rules
- If educator says "I think" or "I believe" without mentioning system evidence → NOT CA
- If educator refers to general teaching experience not tied to system → NOT CA
- If educator says "the system helped me understand X" → CA (even if indirect)
- Multiple CA codes allowed in one segment if multiple system references

---

## Theme 2: Semantic Alignment (SA)

### Definition
Evidence that the educator is refining, updating, or deepening their rubric/grading standards based on what they've learned. This includes recognizing previously missed concepts, reorganizing rubric categories, or strengthening rubric criteria.

### Indicators
- Mentions changes to rubric or grading approach
- Recognizes gaps or errors in original rubric
- Describes adding new concepts to rubric
- Reorders or restructures rubric elements
- Shows meta-awareness: "I didn't think about that before"
- Expresses alignment between student understanding and grading criteria

### Examples (Code)

**INCLUDE:**
1. "I realize I should add a section on state management to my rubric. Students are clearly struggling with that."
   - Code: **SA** (rubric enhancement)

2. "My original rubric didn't distinguish between computational thinking and algorithm design. I need to split that."
   - Code: **SA** (rubric restructuring)

3. "Seeing how the student explained their code, I now understand why clarity in variable names matters. I'll weight that higher."
   - Code: **SA** (rubric criteria strengthening)

4. "That's a valid approach I hadn't considered. I'm updating my rubric to accept this pattern as acceptable."
   - Code: **SA** (rubric expansion/flexibility)

**DO NOT INCLUDE:**
1. "This student explained it well."
   - Code: None (evaluation, not rubric refinement)

2. "The font size is easier to read now."
   - Code: None (UI feedback, not semantic content)

3. "I agree with the system's assessment."
   - Code: None (validation, not rubric change)

### Decision Rules
- If educator uses language like "I'll add", "I should include", "I need to emphasize" → SA
- If educator describes realizing something was missing from their original rubric → SA
- If educator only agrees with system but doesn't mention changing practice → NOT SA
- Multiple SA codes allowed if educator makes multiple rubric updates

---

## Theme 3: Trust Calibration (TC)

### Definition
Statements about the educator's confidence in, skepticism of, or trust toward the system's assessments and recommendations. Includes both increasing and decreasing trust, and calibration (matching subjective confidence to objective accuracy).

### Indicators
- Expresses confidence or doubt in system accuracy
- Questions system reasoning or decisions
- Validates system judgments against own expertise
- Admits uncertainty or surprises about system performance
- Shows trust calibration: noticing when system is right vs. wrong
- Expresses hesitation or caution in following system recommendations

### Examples (Code)

**INCLUDE:**
1. "The system said the student didn't understand recursion, and when I looked at the answer, it's right. I trust its analysis."
   - Code: **TC** (increasing trust via validation)

2. "I was skeptical about the zero-grounding flag, but looking at the actual code comment, yeah, the student did hand-wave the explanation."
   - Code: **TC** (trust calibration - system caught what I missed)

3. "The system highlighted a misconception, but I know this student. They actually understand it and just explained it poorly. I don't fully trust the system's interpretation."
   - Code: **TC** (decreasing trust via domain expertise override)

4. "I'm not 100% confident the system caught all the misconceptions, so I'll do my own review too."
   - Code: **TC** (selective trust - use as aid, not oracle)

**DO NOT INCLUDE:**
1. "I found the interface intuitive."
   - Code: None (usability, not trust in accuracy)

2. "I completed the task in 15 minutes."
   - Code: None (metadata, not calibration)

3. "The student's answer was incomplete."
   - Code: None (task evaluation, not system trust)

### Decision Rules
- If educator uses language like "I trust", "I doubt", "I'm confident", "I'm unsure" → TC
- If educator explains why they agree or disagree with system → TC
- If educator expresses they will or won't follow system → TC
- Both positive and negative trust statements count as TC
- Multiple TC codes allowed if multiple trust judgments

---

## Theme 4: Interaction Insight (II)

### Definition
Emergent insights, realizations, or learning that arise from the educator's *interaction with the system*, but are not directly attributed to a specific system element (CA), not primarily about rubric change (SA), and not about trust (TC). These are "aha moments" or deeper pedagogical understandings.

### Indicators
- "I never thought about it this way before..."
- New understanding about student learning or misconceptions
- Realization about own teaching effectiveness
- Insight into learning patterns or cognitive gaps
- Pedagogical reflection prompted by system use
- Understanding of concept interconnections

### Examples (Code)

**INCLUDE:**
1. "Using this system really made me realize how much students struggle with the difference between reference and value semantics. I need to spend more time on that in my course."
   - Code: **II** (pedagogical insight - insight into learning gaps)

2. "I didn't fully understand why recursion is hard for students until I saw their traces in this system. Now I see the mental model mismatch."
   - Code: **II** (insight into student cognition)

3. "This experience showed me that my rubric assessment and my actual grading don't always match. I need to be more consistent."
   - Code: **II** (insight into self - grading consistency)

4. "Watching how different students approach the same problem made me realize there's no one 'right way' to think about algorithms."
   - Code: **II** (insight - flexible thinking, not single solution)

**DO NOT INCLUDE:**
1. "The system highlighted a misconception I already knew about."
   - Code: CA or nothing (system-specific, covered by CA if about traces)

2. "I'm changing my rubric to include this."
   - Code: SA (rubric-focused, covered by SA)

3. "I trust the system's assessment."
   - Code: TC (trust-focused, covered by TC)

### Decision Rules
- If the insight is primarily about the system's evidence → Use CA instead
- If the insight leads to rubric change → Use SA instead
- If the insight is about confidence in system → Use TC instead
- If the insight is about pedagogy/learning/teaching → II
- II is the "catch-all" for genuine learning that transcends the rubric/system/trust
- Multiple II codes allowed if educator has multiple insights

---

## Boundary Cases & Ambiguities

### Case 1: CA vs. SA
**Scenario:** "The system showed me a misconception about pointers. Now I'm updating my rubric to emphasize pointer dereferencing more."

**Decision:** Code as **both CA + SA** (system attribution + rubric change). Educator is explicitly tying system evidence to rubric action.

### Case 2: SA vs. II
**Scenario:** "Seeing all these student answers made me realize I need a more sophisticated rubric, and also made me think about how I teach pointers."

**Decision:** Code as **both SA + II** (rubric change + pedagogical insight). Two distinct ideas in one statement.

### Case 3: TC Only
**Scenario:** "I'm a bit skeptical of this score. The student's explanation wasn't great, but they showed they understand the concept in their code."

**Decision:** Code as **TC** only. Educator is calibrating their trust (system says X, but domain knowledge says Y).

### Case 4: Ambiguous Statement
**Scenario:** "That's interesting."

**Decision:** **No code**. Single-word or vague reactions don't meet coding threshold. Require fuller context/elaboration.

---

## Coding Workflow

### Step 1: Transcript Preparation
- Number each line (speaker turn) in transcript
- Keep speaker labels (Educator, Facilitator, System_Output)
- Mark segment boundaries clearly

### Step 2: Segment Identification
- Read full transcript to get context
- Identify natural boundaries (speaker turn, topic shift, logical pause)
- One code per segment (if multiple themes, create sub-segments)

### Step 3: Code Assignment
- Assign one primary code (CA, SA, TC, or II)
- Add secondary codes only if segment truly contains 2+ distinct ideas
- Mark ambiguities with **[?]** and note reason

### Step 4: Frequency Tallying
- Count codes per participant (CA, SA, TC, II)
- Tally by condition (Condition A vs. B)
- Prepare summary table for analysis

### Step 5: Validation (IRR Pilot)
- Two coders independently code 20% of transcripts
- Compare code assignments
- Calculate Cohen's κ
- Refine codebook if κ < 0.70
- Document disagreements and resolutions

---

## Coding Standards

### Mandatory Requirements
- [ ] All segments must have one code or be marked "NO CODE"
- [ ] All codes must cite line numbers in transcript
- [ ] Ambiguous segments must include rationale note
- [ ] Track total segments vs. coded segments

### Quality Checks
- [ ] First 5 transcripts reviewed by both coders
- [ ] Coding consistency check after every 10 transcripts
- [ ] Final IRR validation on 20% sample
- [ ] Cohen's κ ≥ 0.70 required before full coding approved

### Coding Sheet Format
```
Transcript: P01_Condition_A.txt
Coder: [Name]
Date: [Date]

| Line | Speaker | Segment Text | Code | Notes |
|------|---------|--------------|------|-------|
| 1-3 | Educator | "I see the misconception..." | CA | References trace output |
| 4-5 | Educator | "So I'll add that concept" | SA | Rubric update |
| ... | ... | ... | ... | ... |

SUMMARY:
CA: [#], SA: [#], TC: [#], II: [#]
Total Coded: [#] / Total Segments: [#]
Intercoder Agreement (if applicable): κ = [value]
```

---

## Codebook Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | May 7, 2026 | Initial codebook created | [Name] |
| 1.1 | May [?] | IRR feedback, refined boundaries | [Name] |
| 1.2 (Final) | Aug [?] | Post-IRR pilot adjustments | [Name] |

---

## Questions & Support

If you encounter a segment you're unsure about:
1. Note the line number and segment text
2. Identify which theme it might fit (CA/SA/TC/II or multiple)
3. Check the "Boundary Cases" section above
4. If still unclear, mark with **[?]** and defer to consensus meeting
5. Document all edge cases for codebook v1.1

---

## IRR Pilot Timeline & Quality Gates

**IRR Pilot Phase:** August 1-3, 2026

### Coder Assignment
- **Two independent coders** (minimum Master's-level training in qualitative methods)
- Both blind to hypothesis and study condition (coding reference numbers, not condition labels)

### Sample Selection
- **20% of completed transcripts** (n = ~13 transcripts, approximately 2,600 words each)
- **Random selection** from across both conditions
- **Representative of answer complexity:** short (5 min), medium (10 min), long (15 min) sessions
- **Stratified:** ~6 from Condition A, ~7 from Condition B

### Coding Protocol
- Both coders independently apply codebook to same 13 transcripts
- **No discussion between coders** until after coding complete
- Record code assignments in identical format (see Coding Sheet Format above)
- **Note any ambiguities** or boundary cases encountered
- Estimated effort: ~40 minutes per transcript × 2 coders = 26 hours total

### Comparison & Calculation: August 3, 2pm–3pm
- Compare code assignments across all 13 transcripts
- For each theme (CA, SA, TC, II), calculate **Cohen's κ**:
  $$\kappa = \frac{p_o - p_e}{1 - p_e}$$
  where $p_o$ = observed agreement, $p_e$ = expected agreement by chance
- Review disagreements to identify patterns
- Interpretation:
  - κ ≥ 0.70: Substantial agreement (✓ APPROVED)
  - 0.40–0.70: Moderate agreement (⚠ REQUIRES REFINEMENT)
  - κ < 0.40: Poor agreement (✗ CODEBOOK BROKEN)

### Decision Point: August 3, 5:00 PM

#### IF κ ≥ 0.70 for ALL themes:
- **Status:** ✅ APPROVED
- **Action:** Proceed to full coding phase (August 4)
- **Documentation:** Record κ values in Revision History (add row for v1.1)

#### IF κ < 0.70 for ANY theme:
- **Status:** ⚠️ REQUIRES REFINEMENT
- **Action:** Emergency codebook refinement meeting (August 3, 5:30 PM)
  - **Attendees:** Both coders + dissertation advisor
  - **Duration:** 1.5 hours (90 minutes)
  - **Agenda:**
    1. Review disagreements for low-κ themes
    2. Identify ambiguous boundary cases
    3. Clarify specific rules or add examples
    4. Update QUALITATIVE_CODEBOOK.md with refined definitions
    5. Revisit decision rules (Section "Decision Rules" for each theme)
  - **Output:** Updated codebook (v1.1 draft)

- **Re-Pilot:** August 4, 9 AM–12 PM
  - Both coders re-code a **NEW sample** (20% of different transcripts)
  - Calculate κ again
  - **If κ ≥ 0.70:** APPROVED (proceed to full coding Aug 5)
  - **If κ < 0.70:** Escalate to advisor; may delay full coding to August 6-7

---

## Full Coding Window

**Start:** August 4, 2026, 9:00 AM (if IRR pilot passes on first attempt)  
**OR** August 5-6, 2026 (if re-pilot required)

**Deadline:** August 15, 2026, 5:00 PM (**STRICT — non-negotiable**)

**Pace Target:** ~13 transcripts per day across 2 coders working in parallel

**Quality Gates During Full Coding:**
- **Every 5 transcripts:** Spot-check 1 random transcript against both coders
- **If agreement drops:** Pause coding, clarify codebook with both coders, resume
- **Daily check:** Track κ on rolling 5-transcript window to detect drift

---

## Contingency: If Full Coding Falls Behind

If full coding is not complete by August 13:
1. **Prioritize complete coding** of randomly selected 50% of transcripts (ensures representative sample)
2. **Exclude partial codings** from analysis (do NOT include "partially coded" transcripts)
3. **Report in limitations:** "Qualitative analysis conducted on [n] of [N] transcripts due to timeline constraints"
4. **Do NOT fake codes** for uncoded transcripts — removing them from dataset is more defensible than guessing

---

## Post-Coding Validation: August 16-20

- Both coders code **final 10% sample** (NEW transcripts, different from IRR pilot)
- Calculate final **κ for audit trail**
- Verify consistency hasn't drifted over 2 weeks of continuous coding
- Report in Appendix: "Final IRR validation on [n] transcripts: κ = [value]"

---

**Codebook Created:** May 7, 2026  
**IRR Pilot:** August 1-3, 2026  
**Decision Point:** August 3, 5:00 PM  
**Full Coding Window:** August 4-15, 2026  
**Coding Deadline:** August 15, 2026, 5:00 PM (**HARD STOP**)
