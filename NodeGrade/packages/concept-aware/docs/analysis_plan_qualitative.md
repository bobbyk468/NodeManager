# ConceptGrade User Study — Qualitative Analysis Plan

**Version:** 1.0  
**Date:** April 2026  
**Study:** IEEE VIS 2027 Educator User Study  
**Target N:** 30 educators (15 per condition, A and B)  
**Dataset:** Single-domain (DigiKlausur Neural Networks, 646 exam answers)  
**Rationale:** Focusing on a single domain where educators are domain experts maximizes **ecological validity** (participants evaluate their own subject-matter area) and **statistical power per condition** (N=15, sufficient for qualitative analysis with mixed-methods depth). This design choice prioritizes expert co-auditing over multi-domain generalization breadth.

---

## 1. Overview

This document specifies the qualitative analysis approach for think-aloud transcripts and post-session interviews conducted with educators evaluating the DigiKlausur Neural Networks dataset. The goal is to extract mechanistic evidence for **how** the interactive dashboard changes educator reasoning and decision-making, beyond what SUS scores alone can capture.

**Key Research Questions:**
- Does the ConceptGrade dashboard help educators **identify misconceptions faster**?
- Does the dashboard **increase confidence** in automated grades?
- Does the dashboard **change educators' mental models** of what students know?
- What **interaction patterns** (heatmap clicks, KG hovers, rubric edits) are associated with these changes?

---

## 2. Transcript Preparation

### 2.1 Recording & Transcription
1. **During Session:** Researcher records audio + screen capture via OBS (or similar).
2. **Within 7 Days:** Transcription contractor or research assistant manually transcribes audio verbatim.
3. **Anonymization:** Remove all PII (names, institution names, course codes). Replace with generic identifiers (P001, P002, etc.).
4. **Format:** Plain text with line numbers; timestamp markers (e.g., `[00:03:45]`) every 30 seconds.

**Transcription Accuracy Target:** 95% (rare names / domain jargon checked against video).

### 2.2 Segmentation by Phase
Split transcript into logical sections:
- **Pre-Task (0–5 min):** Consent, orientation.
- **Exploration Phase (5–25 min):** Think-aloud during data review.
- **Rubric Phase (25–35 min):** Discussing rubric edits.
- **Interview Phase (35–45 min):** Post-hoc reflections.

---

## 3. Coding Scheme (Primary)

### 3.1 Code 1: **Causal Attribution** (CA)

**Definition:** The participant explicitly links an observation from the system to a reasoning step or decision.

**Scope:** Only counts references to specific UI elements or data patterns.

#### 3.1.1 Sub-codes:

| Sub-code | Definition | Example |
|---|---|---|
| **CA-HM** | Reference to heatmap or misconception pattern | "The heatmap shows 40% of students missed sorting, so they're my target." |
| **CA-KG** | Reference to knowledge graph or prerequisite structure | "The graph showed me sorting needs quicksort first, which students didn't understand." |
| **CA-TR** | Reference to trace or reasoning chain | "I saw the verifier flagged a gap in the reasoning, so I don't fully trust that grade." |
| **CA-RD** | Reference to radar or student cohort comparison | "The radar shows this student is in the bottom quartile, so I'd check their work closely." |
| **CA-LACK** | Explicit absence: "If I had seen [visualization], I would have..." | "If I had a knowledge graph, I would've realized students don't understand recursion." |

**Coding Rules:**
- Count each sentence mentioning a UI element or visual pattern once.
- If a sentence mentions multiple UI elements, code each reference separately.
- Only code if the participant attributes the observation to the system (not prior knowledge).

**Example Transcript:**
```
[00:08:23] P005: "Looking at the heatmap, I see sorting has the highest error rate. 
           So I would definitely prioritize that in office hours. 
           The knowledge graph shows me that students need to understand time complexity 
           as a prerequisite. So I'd start there."
```

**Coding:**
- Line 1: CA-HM (heatmap → error rate observation)
- Line 3: CA-KG (knowledge graph → prerequisite discovery)

---

### 3.2 Code 2: **Semantic Alignment** (SA)

**Definition:** The participant articulates a change in their understanding of student knowledge or updates their mental model.

#### 3.2.1 Sub-codes:

| Sub-code | Definition | Example |
|---|---|---|
| **SA-MISCONCEPTION** | Insight into a specific student misconception | "I didn't realize students confuse sorting with searching." |
| **SA-RUBRIC-ADD** | Decision to add a rubric criterion | "I'm going to add 'justify your algorithm choice' to my rubric." |
| **SA-RUBRIC-REMOVE** | Decision to remove or loosen a rubric criterion | "I thought students didn't understand complexity, but most did, so I'll remove that penalty." |
| **SA-PREREQUISITE** | Realization about prerequisite structure | "Students can't explain recursion, which is a blocker for tree traversal." |
| **SA-TEACHING-CHANGE** | Plan to change how the concept is taught | "I'm going to spend more time on sorting before jumping to advanced algorithms." |

**Coding Rules:**
- Code if participant uses explicit language: "I didn't realize," "Now I see," "I'll change," "I didn't know."
- Code the shift from prior belief → new belief (or prior action → new action).
- Do not code vague generalizations ("Students struggle" without specificity).

**Example Transcript:**
```
[00:17:45] P012: "I thought most students understood sorting, but the data shows 
           they don't. I'm going to revise my rubric to give more partial credit 
           for explaining the approach, even if the implementation is wrong."
```

**Coding:**
- SA-MISCONCEPTION (underestimated sorting difficulties)
- SA-RUBRIC-ADD (partial credit for explanation)

---

### 3.3 Code 3: **Trust & Confidence** (TC)

**Definition:** Statements indicating the participant's belief in or skepticism about the system's grading.

#### 3.3.1 Sub-codes:

| Sub-code | Level | Definition | Example |
|---|---|---|---|
| **TC-DISTRUST** | 0 | Explicit doubt or refusal to rely on grades | "I wouldn't trust this without double-checking every answer." |
| **TC-SKEPTICAL** | 1 | Conditional trust; needs clarification | "I see the grade, but I'm not sure how it decided that." |
| **TC-NEUTRAL** | 2 | Acknowledges the grades without strong opinion | "The system seems reasonable." |
| **TC-TRUST** | 3 | Willingness to rely on the grade | "The reasoning makes sense, so I trust this grade." |
| **TC-STRONG-TRUST** | 4 | High confidence in the system | "I would use this for final grades without review." |

**Coding Rules:**
- Code once per session (ordinal: pick the highest level observed).
- If participant's trust shifts (e.g., starts skeptical, ends trusting), code the final level and note the shift in memos.

**Example Transcript:**
```
[00:35:12] P003: "At first, I was skeptical. But once I saw the knowledge graph 
           showing the reasoning chain, it clicked. I trust the grade now."
```

**Coding:**
- **TC-TRUST** (shift from skepticism to trust observed, final state is trusting)
- **Memo:** "Reasoning trace was key to building confidence."

---

### 3.4 Code 4: **Interaction Intensity** (II)

**Definition:** Frequency and duration of exploratory interactions (heatmap clicks, KG hovers, radar brushing).

**Scope:** Extracted from event logs, not from transcript.

| Sub-code | Metric | Threshold |
|---|---|---|
| **II-LOW** | Total interactions < 10 | Minimal exploration; limited engagement |
| **II-MEDIUM** | Total interactions 10–30 | Moderate exploration; focused on 2–3 UI elements |
| **II-HIGH** | Total interactions > 30 | Deep exploration; used all UI elements |

**Linkage to Transcript:**
- Cross-reference timing: if participant says "The heatmap showed me X" at 00:12:00, check event log for heatmap click at ~00:12:00.
- Summarize in session memo: "P007 had high interaction intensity; spent ~8 min on heatmap, 5 min on KG."

---

## 4. Coding Workflow

### 4.1 Codebook Preparation
1. **Codebook Document:** Expand Section 3 above into full codebook with 5–10 example transcripts for each code.
2. **Coder Training:** Both coders read codebook; practice coding 3 sample transcripts together until κ ≥ 0.80.
3. **Reconciliation:** Discuss disagreements and refine codebook (iterative until stable).

### 4.2 Independent Coding
1. **Coder A** — Codes all 30 transcripts using NVivo or QDA Miner (or manual spreadsheet).
2. **Coder B** — Independently codes a random 50% subsample (N=15).

### 4.3 Reliability Assessment
- **Inter-Rater Reliability (IRR):** Cohen's κ for the overlap sample (N=15).
  - Target: κ ≥ 0.70 for CA, SA, TC.
  - If κ < 0.70: Discuss disagreements, refine codebook, re-code full sample.

### 4.4 Final Coding
- **Coder A:** Applies final codebook to all 30 transcripts.
- **QA Review:** Spot-check 10% of final codes (supervisor review).

---

## 5. Analysis by Code

### 5.1 Causal Attribution (CA)

#### Quantitative Aggregation
```
CA_Frequency_A = count(CA codes | Condition A)
CA_Frequency_B = count(CA codes | Condition B)

Sub-code breakdown:
├─ CA_HM_A, CA_HM_B
├─ CA_KG_A, CA_KG_B
├─ CA_TR_A, CA_TR_B
├─ CA_RD_A, CA_RD_B
└─ CA_LACK_A, CA_LACK_B
```

#### Statistical Test
- **Hypothesis:** Condition B generates more causal attributions than Condition A.
- **Test:** Poisson GLM (event count data; condition as predictor).
  ```
  model = glm(CA_Frequency ~ Condition, family=poisson)
  ```
- **Expected:** β(Condition B) > 0, p < 0.05.
- **Effect Size:** Incidence Rate Ratio (IRR = exp(β)).

#### Qualitative Interpretation
- Extract top 3 quotes per condition exemplifying causal reasoning.
- Tabulate: does Condition B cite specific UI elements more often than Condition A?

### 5.2 Semantic Alignment (SA)

#### Quantitative Aggregation
```
SA_Frequency_A = count(SA codes | Condition A)
SA_Frequency_B = count(SA codes | Condition B)

Sub-code breakdown:
├─ SA_MISCONCEPTION_A, SA_MISCONCEPTION_B
├─ SA_RUBRIC_ADD_A, SA_RUBRIC_ADD_B
├─ SA_RUBRIC_REMOVE_A, SA_RUBRIC_REMOVE_B
├─ SA_PREREQUISITE_A, SA_PREREQUISITE_B
└─ SA_TEACHING_CHANGE_A, SA_TEACHING_CHANGE_B
```

#### Statistical Test
- **Hypothesis:** Condition B participants articulate more semantic insights.
- **Test:** Poisson GLM (as above).
- **Expected:** β(Condition B) > 0, p < 0.05.

#### Qualitative Interpretation
- List all rubric changes proposed in Condition B; cross-reference with event log (which KG node triggered the change?).
- Compare to Condition A: do control participants suggest rubric changes? If so, are they as specific?

**Example Synthesis:**
> Condition B educators refined rubrics 3.2× more often than Condition A (M_B=2.8, M_A=0.9, p=0.031). 
> When they did, 85% of changes were traceable to a specific KG node or misconception pattern observed on the heatmap 
> (vs. 30% in Condition A, which cited generic concerns like "students don't understand complexity").

---

### 5.3 Trust & Confidence (TC)

#### Quantitative Aggregation
```
TC_Distribution_A = [# at level 0, 1, 2, 3, 4] for Condition A
TC_Distribution_B = [# at level 0, 1, 2, 3, 4] for Condition B

TC_Mean_A = sum(level × count) / n_A
TC_Mean_B = sum(level × count) / n_B
```

#### Statistical Test
- **Hypothesis:** Condition B has higher mean trust level.
- **Test:** Mann-Whitney U test (ordinal data; non-parametric).
- **Expected:** U test p < 0.05, and median(Condition B) > median(Condition A).

#### Qualitative Interpretation
- Extract quotes showing trust transitions (skeptical → trusting).
- Identify which UI elements most strongly shifted trust.

**Example Synthesis:**
> All 15 Control participants (Condition A) remained at TC-level 1–2 (skeptical). 
> In Condition B, 10/15 reached TC-level 3–4 (trusting). The primary trust-builder was the Knowledge Graph: 
> 8/10 trusting participants explicitly mentioned "seeing the reasoning chain grounded to the graph" as crucial.

---

### 5.4 Interaction Intensity (II) vs. Performance

#### Cross-tabulation
```
            | Low II | Medium II | High II |
Cond A      |   x    |     y     |    z    |
Cond B      |   x'   |     y'    |    z'   |
```

#### Correlation (within Condition B only)
- **Hypothesis:** Interaction intensity correlates with SUS scores and task accuracy.
- **Test:** Spearman ρ (II rank vs. SUS score, II rank vs. Task Accuracy).
- **Expected:** ρ > 0.40, p < 0.10 (exploratory).

**Example Synthesis:**
> High interaction intensity (>30 clicks/hovers) in Condition B correlated with higher SUS scores (ρ=0.58, p=0.07). 
> This suggests the dashboard's value is proportional to exploratory engagement.

---

### 5.5 Answer Dwell Time vs. KG Coverage (New — Pre-Registered)

#### Overview and Data Sources

**Event types logged:** `answer_view_start` and `answer_view_end` (added to `studyLogger.ts`).

Each `answer_view_end` event contains:
- `student_answer_id` — opaque ID, joinable to `data/digiklausur_trm_cache.json`
- `dwell_time_ms` — milliseconds between view start and view end (captured via React `useEffect` cleanup + `navigator.sendBeacon()`)
- `chain_pct` — KG chain coverage for that answer (available at click time from `ConceptStudentAnswer`)
- `severity`, `solo_level`, `bloom_level` — supporting covariates
- `capture_method` — `'beacon'` (component unmount / tab close) vs. `'cleanup'` (normal navigation); use to flag incomplete dwell windows

#### Key Implementation Note: Zero-Grounding Degeneration in DigiKlausur

Pre-computation of TRM metrics (`generate_trm_cache.py`) revealed that **97.7% of DigiKlausur LRM traces are zero-grounding degenerate** (`grounding_density = 0`): the LRM parsed steps have empty `kg_nodes` arrays, so `topological_gap_count ≈ 0` across virtually all 300 answers. This is consistent with the paper's Section 3 prediction of zero-grounding as a false-negative case.

**Consequence for analysis:** `topological_gap_count` is a near-constant variable in DigiKlausur and cannot be used as a Spearman ρ predictor. The pre-registered substitute is **`chain_pct`** from `ConceptStudentAnswer`.

**Rationale for `chain_pct` as substitute:**
- `chain_pct` measures how much of the expected KG concept chain the student's answer covered (Stage 2 concept extraction — independent of Stage 3 trace parsing)
- It has meaningful variance across the 646 DigiKlausur answers (continuous, 0–100%)
- Low `chain_pct` = student answered fewer expected concepts = answer is harder for an LLM to grade → educator should investigate longer
- This tests a complementary hypothesis: **do educators spend more time on answers with low KG coverage?**

#### Pre-Registered Dwell-Time Hypotheses

| # | Hypothesis | Predictor | Outcome | Test |
|---|-----------|-----------|---------|------|
| H-DT1 | Educators dwell longer on answers with low KG chain coverage | `chain_pct` (from `ConceptStudentAnswer`) | `dwell_time_ms` | Spearman ρ (expected: ρ < −0.25, p < 0.10) |
| H-DT2 | Condition B educators dwell longer than Condition A educators (per answer) | `condition` | `dwell_time_ms` | Mann-Whitney U across per-answer median dwell times |
| H-DT3 | Answers with `severity = 'critical'` receive longer dwell times than `matched` answers | `severity` | `dwell_time_ms` | Kruskal-Wallis across severity groups |

#### Filter for Analysis

Before running correlations, exclude:
1. Dwell times < 2,000 ms (accidental clicks; bounce events)
2. Sessions where the participant submitted the task answer within 5 minutes (likely protocol non-compliance)
3. Events with `capture_method = 'beacon'` AND `dwell_time_ms > 1,200,000` (20+ minutes = unrealistic; likely browser left open)

#### TRM Cache as Join Key

The static `data/digiklausur_trm_cache.json` (generated once by `generate_trm_cache.py`) provides:
- `topological_gap_count`, `grounding_density`, `verification_status` per answer
- Supporting metadata: `lrm_valid`, `lrm_model`, `human_score`, `c5_score`, `net_delta`

Join pattern in analysis:
```python
import pandas as pd, json

events = pd.read_json('data/study_logs/session_XYZ.jsonl', lines=True)
trm    = pd.DataFrame(json.load(open('data/digiklausur_trm_cache.json')).values())

dwell = events[events['event_type'] == 'answer_view_end'].copy()
dwell['student_answer_id'] = dwell['payload'].apply(lambda p: p['student_answer_id'])
dwell['dwell_time_ms']     = dwell['payload'].apply(lambda p: p['dwell_time_ms'])
dwell['chain_pct_raw']     = dwell['payload'].apply(lambda p: float(str(p.get('chain_pct', '0')).rstrip('%') or 0))

merged = dwell.merge(trm, on='student_answer_id', how='left')

# H-DT1: chain coverage vs. dwell time
from scipy.stats import spearmanr
rho, p = spearmanr(merged['chain_pct_raw'], merged['dwell_time_ms'])
print(f"H-DT1: ρ = {rho:.3f}, p = {p:.3f}")
```

#### Reporting

Report as secondary quantitative finding alongside CA, SA, TC, II:
> "Educators in Condition B spent M=X ms (Mdn=Y) on answers with low KG chain coverage (<33%) 
> vs. M=A ms (Mdn=B) on high-coverage answers (>66%), Spearman ρ=C, p=D. 
> This suggests the interactive trace visualization drew sustained attention to structurally 
> incomplete answers — a result not detectable from summary statistics alone."

---

## 6. Memo Writing

For each participant session, write a 1–2 paragraph memo capturing:

1. **Key Insight:** What was the participant's main takeaway?
2. **Interaction Pattern:** Did they use the dashboard systematically or exploratorily?
3. **Trust Arc:** How did confidence evolve during the session?
4. **Anomalies:** Any unexpected findings or technical issues?

**Memo Template:**
```
### Memo: P015 (Condition B, Session 05)

**Key Insight:** Participant discovered that students conflate "time complexity" 
with "number of operations," a misconception not obvious from summary stats alone. 
This realization prompted a rubric edit adding "explain complexity notation."

**Interaction Pattern:** High intensity (42 interactions over 18 min). 
Spent 6 min on heatmap (identifying sorting/complexity), 5 min on KG 
(understanding prerequisites), 3 min on trace (verifying reasoning).

**Trust Arc:** Started skeptical ("How does it know?"); became trusting after 
KG hover revealed connected reasoning steps. By rubric phase, stated "I would 
use this to prepare office hour agendas."

**Anomalies:** None. Session ran smoothly.
```

---

## 7. Thematic Analysis (Optional, Secondary)

If coding yields surprising patterns, conduct brief thematic analysis to surface higher-level themes.

**Steps:**
1. List all CA sub-codes and their frequencies.
2. Identify clusters: e.g., "KG-driven reasoning" (CA-KG + SA-PREREQUISITE) vs. "stat-driven reasoning" (CA-HM + CA-RD).
3. Ask: **Which UI affordances drove actionable insights?**

**Expected Themes:**
- **Theme 1: "The graph made prerequisite logic visible"** — KG hovers + SA-PREREQUISITE codes.
- **Theme 2: "The heatmap identified the _where_, the graph explained the _why_"** — CA-HM + CA-KG in sequence.
- **Theme 3: "Seeing reasoning gaps increased confidence"** — CA-TR + TC-TRUST shift.

---

## 8. Reporting Standards

### 8.1 Quantitative Results (in Paper)

**SUS Scores (primary):**
```
Condition A: M = 58.2, SD = 19.1, Mdn = 62
Condition B: M = 72.5, SD = 15.3, Mdn = 75
t(28) = 2.18, p = 0.042, d = 0.83
```

**Causal Attribution Frequency:**
```
Condition A: M = 2.3 causal statements per participant (SD = 1.8)
Condition B: M = 8.7 causal statements per participant (SD = 3.1)
IRR = 3.8, 95% CI [2.1, 6.9], p = 0.003
```

**Trust Levels:**
```
Condition A: Mdn = 1.5 (Skeptical), IQR = [1, 2]
Condition B: Mdn = 3.0 (Trusting), IQR = [3, 4]
U = 45, p = 0.008
```

### 8.2 Qualitative Results (in Paper)

**Format:** Narrative + exemplary quotes.

**Example:**
> Our qualitative analysis of think-aloud transcripts revealed that Condition B 
> participants engaged in more mechanistic reasoning about misconceptions. 
> For instance, P007 noted: 
> 
> > "The knowledge graph showed me that students understand sorting but fail on 
> > time complexity analysis. That's the gap to target." 
> 
> This type of structurally-grounded causal reasoning appeared 3.8× more often 
> in Condition B (M = 8.7 statements/participant) than in Condition A (M = 2.3, 
> p = 0.003). Moreover, 10/15 Condition B participants edited their rubrics to 
> target prerequisite concepts identified via the graph, compared to 2/15 in 
> Condition A.

### 8.3 Appendix (Supplementary Material)

- **Appendix Table:** Full coding frequency by sub-code (CA-HM, CA-KG, etc.) for all participants.
- **Appendix Figure:** Distribution of trust levels (0–4 ordinal) by condition (box plot).
- **Appendix Quotes:** 1–2 exemplary quotes per major code (2–3 pages).

---

## 9. Timeline

| Task | Timeline | Owner |
|---|---|---|
| Codebook Drafting | July 2026 (Week 1) | PI + Lead Analyst |
| Coder Training & Pilot | July 2026 (Weeks 2–3) | Both Coders |
| Independent Coding (50% sample for IRR) | July 2026 (Week 4) | Both Coders |
| IRR Assessment & Codebook Refinement | August 2026 (Week 1) | PI + Lead Analyst |
| Full Coding (Coder A, all transcripts) | August 2026 (Weeks 2–3) | Coder A |
| Memo Writing & Thematic Synthesis | August 2026 (Week 4) | Lead Analyst |
| Results Writeup (Paper Section 5b) | September 2026 | PI |

---

## 10. Software & Tools

| Task | Tool |
|---|---|
| Transcription | Rev.com, otter.ai, or manual |
| Coding & IRR | NVivo 14, QDA Miner, or Google Sheets (manual) |
| Statistical Analysis | R (irr package, glm, Mann-Whitney) or SPSS |
| Memo Writing | Google Docs or Notion |

---

## 11. Sensitivity & Ethical Considerations

### PII Protection
- Codebook and memos refer to participants by session ID (P001, P002, ...), not names.
- Direct quotes in memos replace institution names with "[University]" or "[School]".

### Rigor & Bias Mitigation
- **Double-coding:** 50% overlap ensures independent verification (reduces coder drift).
- **Codebook Evolution:** Document all codebook changes (versions v1.0 → v1.1, etc.) with rationale.
- **Memo Transparency:** Memos include uncertainties: "P009 statement is ambiguous; coded as CA-HM, but could be CA-RD."

### Qualitative Validity Checks
- **Member Checking (Optional):** Share preliminary findings with 2–3 willing participants; ask: "Does this match your experience?"
- **Triangulation:** Cross-reference transcript findings with event logs (e.g., "participant said they clicked the heatmap" ↔ check event log timestamp).

---

## End of Analysis Plan

**Prepared by:** [PI Name]  
**Date:** April 2026  
**Version:** 1.0
