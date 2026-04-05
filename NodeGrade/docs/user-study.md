# NodeGrade — User Study Preparation Guide

**Target participants:** University instructors + undergraduate/graduate students
**Study type:** Mixed-method (task completion + SUS questionnaire + semi-structured interview)
**Date drafted:** March 2026

---

## 1. Study Goals

| Goal | Measurement |
|------|-------------|
| G1 — Instructor usability | Can instructors build a working grading pipeline without help in under 15 minutes? |
| G2 — Student experience | Do students find the feedback clear and actionable? |
| G3 — Grade acceptance | Do instructors agree with ConceptGrade's output grades? |
| G4 — Efficiency | Time saved vs manual grading per assignment batch |

---

## 2. Participant Profiles

### 2.1 Instructor Cohort (target n = 10–15)

**Inclusion criteria:**
- University lecturer or TA in a CS or STEM discipline
- Has graded free-text or short-answer questions before
- No prior experience with NodeGrade required

**Recruitment channels:** Department mailing list, HASKI partner institutions

### 2.2 Student Cohort (target n = 30–50)

**Inclusion criteria:**
- Currently enrolled in a CS course that uses short-answer assessments
- Willing to submit one real assignment answer through NodeGrade

**Recruitment:** Via participating instructors after their pipeline is built

---

## 3. Study Protocol

### 3.1 Instructor Session (~75 minutes)

> **Design note:** An earlier 60-minute protocol was revised to 75 minutes after recognising that a 15-minute Task 1 with no buffer would cannibalise the semi-structured interview if any participant struggled with the graph editor. Task 1 has been simplified (load a pre-built template and connect one node, rather than building from scratch) so the 15-minute slot is realistic. The interview is protected at 15 minutes and treated as the highest-priority data source — it can absorb time from Task 3 if needed.

| Phase | Duration | Description |
|-------|----------|-------------|
| Briefing | 5 min | Study purpose, data usage, consent form |
| Onboarding | 5 min | Guided walkthrough: home page → template cards → editor overview (researcher-led) |
| Task 1 | 15 min | Load **"concept-grade-task1.json"** (study variant), connect the pre-placed `OutputNode` to the `ConceptGradeNode` score output, and save the graph — *one connection only; all other nodes and links are pre-wired* |
| Task 2 | 10 min | Submit a provided sample answer through the StudentView; observe the score and feedback |
| Task 3 | 10 min | Review two graded outputs (one clearly correct, one borderline); mark agree/disagree; explain why |
| Buffer | 5 min | Unstructured exploration or overflow from Task 1/3 |
| SUS questionnaire | 5 min | Standard 10-question System Usability Scale (paper or online form) |
| Semi-structured interview | 15 min | Open-ended feedback (see Section 5) — **protected; not shortened** |

**Success criteria for Task 1:** Instructor makes the single required connection and saves without researcher assistance.
**Success criteria for Task 2:** Instructor can locate and interpret score, Bloom's level, and at least one missed concept in the output.
**Time-at-risk:** If Task 1 exceeds 20 minutes despite simplification, researcher provides one hint (maximum) and records this as a partial completion. Interview time is never reduced below 10 minutes.

### 3.2 Student Session (~20 minutes)

| Phase | Duration | Description |
|-------|----------|-------------|
| Briefing + consent | 3 min | Explain that their answer will be auto-graded |
| Answer submission | 5 min | Submit answer via StudentView on a prepared question |
| Feedback review | 5 min | Read the score, Bloom's level, missed concepts, and feedback |
| Survey | 7 min | 5-point Likert scale questions (see Section 6) |

---

## 4. Grading Agreement Protocol

After the student cohort session, participating instructors will:

1. Receive a batch of 20 anonymised answers (10 graded by NodeGrade, 10 by Pure LLM)
2. Assign their own grades independently (double-blind)
3. Results compared: ConceptGrade vs human vs Pure LLM using MAE and QWK

**Target:** ConceptGrade grades within ±0.5 of instructor grades on ≥80% of answers.

---

## 5. Instructor Interview Questions

1. How easy or difficult was it to build your first grading pipeline?
2. Which part of the interface was most confusing?
3. Did the ConceptGrade output match your expectations? Were there surprising grades?
4. Would you use this for a real assignment? What would need to change?
5. What node types are missing that you would need for your subject area?
6. How do you feel about delegating grading to an AI system? What safeguards would you want?

---

## 6. Student Survey (Likert 1–5)

> **Design note:** An earlier draft included the item "I would prefer instant automated feedback over waiting for a human grader." This item is susceptible to a **ceiling effect** — students will almost universally prefer faster feedback regardless of quality, which would produce an artificially positive result that says nothing about ConceptGrade specifically. S4 has been redesigned to measure *quality trust* rather than *speed preference*, and two negatively-framed items (S4, S6) have been added to reduce acquiescence bias.

| # | Statement | Rationale |
|---|-----------|-----------|
| S1 | The feedback I received was easy to understand. | Clarity measure |
| S2 | The score I received felt fair given my answer. | Acceptance measure |
| S3 | The feedback helped me identify a specific gap in my understanding. | Learning value measure — not just "I learned something" but actionability |
| S4 | I would feel comfortable if this score counted toward my final grade. | Trust measure — higher bar than speed preference; directly targets grade-stakes context |
| S5 | The feedback pointed out things I disagreed with or that seemed wrong. | *(Reverse-coded)* Catches over-trusting responses; high score = problem |
| S6 | I would rather wait for human feedback than receive this automated feedback. | *(Reverse-coded)* Speed-independent trust check; avoids ceiling effect of original S4 |

**Follow-up open question (mandatory):** "Describe one specific thing in the feedback you agreed with and one thing you disagreed with or found confusing."

> The mandatory disagreement prompt is intentional: it forces students to engage critically rather than deflect to "everything was fine", yielding richer qualitative data for thematic analysis.

---

## 7. System Usability Scale (SUS) — Instructor

Standard 10-item SUS (Brooke, 1996). Scoring: each item 1–5, alternating polarity, scaled to 0–100.

| # | Statement |
|---|-----------|
| 1 | I think that I would like to use this system frequently. |
| 2 | I found the system unnecessarily complex. |
| 3 | I thought the system was easy to use. |
| 4 | I think that I would need the support of a technical person to be able to use this system. |
| 5 | I found the various functions in this system were well integrated. |
| 6 | I thought there was too much inconsistency in this system. |
| 7 | I would imagine that most people would learn to use this system very quickly. |
| 8 | I found the system very cumbersome to use. |
| 9 | I felt very confident using the system. |
| 10 | I needed to learn a lot of things before I could get going with this system. |

**Target SUS score:** ≥ 68 (industry "good" threshold).

---

## 8. Data Collection & Storage

| Data type | Collection method | Storage |
|-----------|------------------|---------|
| Task completion times | Researcher observation log | Encrypted spreadsheet |
| SUS scores | Paper or Google Form | Anonymised by participant ID |
| Interview responses | Audio recording (with consent) → transcription | Encrypted, deleted after analysis |
| Student answers + grades | NodeGrade database export | Pseudonymised, no name linkage |
| Grading agreement matrix | Researcher comparison spreadsheet | Anonymised |

**IRB / Ethics note:** Obtain institutional ethics approval before recruitment. Informed consent must cover: data storage duration (5 years), right to withdraw, how results will be published (aggregated, no individual identification).

---

## 9. Pre-Study Checklist

### Platform Readiness

- [ ] Backend running and stable (`GET /health` returns `status: ok`)
- [ ] 3 starter templates verified loadable in editor
- [ ] `concept-grade.json` — fully wired, returns scores (used for Task 2 reference)
- [ ] `concept-grade-task1.json` — study variant: score OutputNode deliberately disconnected for Task 1
- [ ] StudentView accessible and auto-submitting correctly
- [ ] Validation dashboard at `/validation` shows 0 FAIL rows

### Study Materials

- [ ] Consent forms drafted — see `docs/consent-forms.md` (Form A: Instructor, Form B: Student); placeholders completed and reviewed by institution ethics board
- [ ] SUS questionnaire printed or linked (online form)
- [ ] Student survey created (Google Form or equivalent)
- [ ] Interview question guide printed for moderator
- [ ] Sample question + model answer prepared for Task 2 (instructor session)
- [ ] 20-answer grading batch prepared for grading agreement protocol

### Technical Setup

- [ ] Dedicated study server or local machine confirmed stable
- [ ] Screen recording software installed (for task analysis)
- [ ] Backup session URL prepared in case WebSocket drops
- [ ] LiteLLM proxy running with Gemini key (required for LLM grader template)

---

## 10. Analysis Plan

### Quantitative

| Measure | Method |
|---------|--------|
| Task completion rate | % of instructors completing Tasks 1–3 without assistance |
| Task time | Median + IQR per task |
| SUS score | Mean ± SD; compare against 68 (good) / 85 (excellent) thresholds |
| Student Likert | Mean per item; Cronbach's α for internal consistency. **Note:** S5 and S6 are reverse-coded — recode scores as (6 − raw) before computing item means and Cronbach's α so that high values uniformly indicate positive student experience |
| Grading agreement | MAE, QWK: ConceptGrade vs Human vs Pure LLM |

### Qualitative

- Thematic analysis of interview transcripts (open coding → axial coding)
- Key themes expected: trust in AI grading, transparency of feedback, pipeline authoring complexity

---

## 11. Timeline

| Milestone | Target date |
|-----------|-------------|
| Ethics approval submitted | April 2026 |
| Pilot session (1–2 instructors) | May 2026 |
| Full instructor cohort sessions | June 2026 |
| Student cohort sessions | June–July 2026 |
| Grading agreement analysis complete | July 2026 |
| Results written up for paper | August 2026 |
