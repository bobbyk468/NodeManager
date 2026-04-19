# ConceptGrade Educator User Study Protocol

**Version:** 1.0  
**Date:** April 2026  
**Study Title:** Evaluating Interactive Visual Analytics for Human-AI Co-Auditing of Automated Grading  
**Target N:** 30 educators (15 per condition)  
**Session Length:** 45–60 minutes

---

## 1. Participant Eligibility

### Inclusion Criteria
- **Teaching Experience:** Currently or recently taught (past 2 years) a course involving short-answer assessment in Computer Science, Engineering, Mathematics, or related STEM discipline.
- **Domain Expertise:** Comfortable evaluating student answers in their discipline without external aids.
- **Language:** Fluent in English (study materials and think-aloud protocol are in English).

### Exclusion Criteria
- Has participated in prior ConceptGrade pilot studies or has seen the system in detail.
- Unable to commit to a full 45–60 minute session.
- Is a co-author on ConceptGrade-related publications.

---

## 2. Recruitment Strategy

### Primary Channels
1. **University CS/Engineering Departments** — Direct outreach to department chairs and course coordinators; posted flyers in faculty lounges.
2. **Professional Networks** — SIGCSE, ACM ICER, IEEE FIE mailing lists; online teaching communities.
3. **Snowball Sampling** — Existing participants refer peers.

### Target Quotas
- **CS (50%):** Data Structures, Algorithms, OOP instructors.
- **Neural Networks / ML (30%):** Introductory ML, Deep Learning course instructors.
- **Math / Physics (20%):** Calculus, Physics instructors who grade short-form problem solutions.

### Recruitment Materials
- Email invitation with brief overview and $\$50$ Amazon gift card incentive.
- Study portal link (Calendly or similar) for self-scheduling.
- Informed consent form and IRB approval letter.

---

## 3. Session Structure

### 3.1 Pre-Session (5 minutes)
1. Participant arrives (online or in-person).
2. Researcher checks participant ID and consent form signature.
3. Brief orientation: "We're evaluating a dashboard for automated grading. We want to see if it helps instructors diagnose student misconceptions."
4. Audio/video recording consent confirmation.

### 3.2 Study Task (20 minutes)
1. **Condition Assignment:** Participant is randomly assigned to Condition A (Control) or Condition B (Treatment) via URL parameter.
   - **Condition A URL:** `http://localhost:5173/dashboard?condition=A&dataset=digiklausur&study=true`
   - **Condition B URL:** `http://localhost:5173/dashboard?condition=B&dataset=digiklausur&study=true`

2. **Dataset Context:** Researcher provides verbal summary:
   > "You are reviewing the DigiKlausur Neural Networks course exam dataset—646 real exam answers collected from a university course on neural network fundamentals. Each student answered 5–8 short-answer questions covering core concepts like backpropagation, gradient descent, and network optimization. The system has graded all answers. Your task: Based on the information available to you, identify one key concept that students struggle with the most. Which students would you prioritize for one-on-one office hours, and why?"

3. **Exploration Structure (20-minute window):**
   - **Minutes 0–5 (Overview):** Educator sees the dashboard's aggregate view: a heatmap showing error rates for each NN concept across all 646 students, plus a radar plot showing student performance cohorts.
   - **Minutes 5–20 (Drill-Down):** Educator clicks into 2–5 specific answers of interest to examine misconceptions in detail. For each answer, the dashboard displays:
     - Student's full answer text
     - LLM-assigned grade + confidence
     - Verifier Reasoning Trace: step-by-step explanation of the grade, with green/yellow/red indicators for grounded/ambiguous/ungrounded reasoning steps
     - Knowledge Graph Subgraph: prerequisite structure showing which NN concepts are connected to the student's response
   - **Researcher Role:** Observes and records think-aloud protocol (participant narrates their reasoning as they interact).
     - Researcher intervenes minimally ("Tell me what you're thinking now").
     - If participant gets stuck after 5 minutes without progress, researcher provides minimal guidance: "What are you trying to understand?"

4. **Free-Response Answer:** Participant types their answer in the Study Task panel text area and rates confidence (1–5 slider).
   - Answer captured in localStorage + sent to backend POST `/api/study/log` with `event_subtype: 'main_task'`.

### 3.3 SUS Questionnaire (5 minutes)
1. Participant rates 10 standardized SUS items (Brooke, 1996) on 1–5 Likert scale.
2. System automatically computes SUS score and displays grade (A+, A, B, C, D, F).
3. Responses logged with timestamp and condition ID.

### 3.4 Rubric Refinement (10 minutes)
1. Participant uses the Rubric Editor to add or modify grading criteria based on what they learned.
2. Researcher explains: "You've now had a chance to review student answers. Would you refine your grading rubric based on what you discovered?"
3. Participant makes edits (or explicitly states "No changes needed").
4. All rubric edits logged with associated KG node IDs (if applicable) for causal tracing.

### 3.5 Post-Session Interview (10 minutes)
1. **Structured Questions:**
   - "Was there a moment when the visualizations (or lack thereof) helped you make a decision?"
   - "What did you notice about how students understood [key concept]?"
   - "Would you use this tool regularly to prepare for office hours? Why or why not?"
   - "On a scale of 1–5, how much do you trust the system's grades for this dataset?"

2. **Open-Ended:** "Anything else you'd like to share?"

3. Researcher probes for evidence of causal attribution:
   - "You mentioned editing the rubric for [concept]. What in the dashboard made you realize that was necessary?"

### 3.6 Debrief & Exit (5 minutes)
1. Researcher thanks participant.
2. Provides gift card / compensation.
3. Answers any participant questions.
4. Reminder: Results will be shared in publication (anonymized).

**Total Session Time:** 45–60 minutes.

---

## 4. Data Collection

### 4.1 Quantitative Data
| Data Point | Source | Timing |
|---|---|---|
| SUS Scores (0–100) | SUSQuestionnaire component | Post-task |
| Task Answer Quality | Free-response text + manual expert coding | Post-session |
| Confidence Self-Report | Slider (1–5) | During task |
| Time-to-Answer | Timestamp delta (task_start → task_submit) | During task |
| Interaction Counts | Event log (heatmap clicks, radar brushes, KG hovers) | During task |
| Rubric Edits | Edit log with KG node associations | During rubric phase |

### 4.2 Qualitative Data
| Data | Source | Processing |
|---|---|---|
| Think-Aloud Transcript | Audio recording → manual transcription | Full transcription + manual coding |
| Post-Session Interview | Audio recording → manual transcription | Coded for causal reasoning, semantic alignment, trust |
| Researcher Observations | Field notes during session | Coded for key moments of insight, hesitation, confusion |

### 4.3 Event Logging
All interactions are logged to localStorage (client-side) and POSTed to `POST /api/study/log` every 30 seconds or on task completion.

**Log Schema:**
```json
{
  "session_id": "c97a14d0-...",
  "timestamp_ms": 1713354000000,
  "condition": "A" | "B",
  "dataset": "digiklausur",
  "event_type": "task_start" | "task_submit" | "heatmap_click" | "radar_selection" | "kg_hover" | "rubric_edit" | "sus_questionnaire",
  "payload": {
    "answer": "string",
    "confidence": 1-5,
    "time_to_answer_ms": 1200000,
    "sus_responses": { "1": 4, "2": 3, ... },
    "sus_score": 75,
    "rubric_edits": [
      { "timestamp_ms": ..., "kg_node_id": "sorting", "text": "..." }
    ]
  }
}
```

---

## 5. Qualitative Coding Scheme

### 5.1 Causal Reasoning Attribution
**Definition:** Statements where the participant explicitly links a visualizationelement (or absence thereof) to a decision or insight.

**Examples:**
- **Coded:** "The heatmap shows that 40% of students missed the sorting concept, so I'd target them first."
- **Coded:** "The knowledge graph showed me that students need to understand time complexity before sorting, so I'd review that in class."
- **Not Coded:** "I'd prioritize students who got low scores" (no explicit link to visual element).

**Frequency Count:** Total causal statements per condition.  
**Effect Size:** Count(Causal Statements | Condition B) − Count(Causal Statements | Condition A).

### 5.2 Semantic Alignment
**Definition:** Evidence that the participant refined their understanding of student misconceptions or their own rubric criteria.

**Examples:**
- "I initially thought students understood prerequisites, but now I see they don't."
- "I'm going to add 'explain your reasoning' to my rubric because I see students skip justifications."

**Frequency Count:** Instances of explicit mental model updates per participant.

### 5.3 Trust in Automated Grades
**Definition:** Statements indicating confidence or skepticism about the system's grading.

**Examples (High Trust):**
- "The system's reasoning makes sense; I trust it got this right."

**Examples (Low Trust):**
- "I don't understand how it arrived at this grade; I'd double-check it manually."

**Coding:** Likert-like ordinal scale (0=Explicit Distrust, 1=Skeptical, 2=Neutral, 3=Trusting, 4=High Trust).

### 5.4 Task Accuracy
**Definition:** Does the misconception identified by the participant match ground truth (domain expert consensus or rubric guidelines)?

**Coding:**
- **Exact Match (2 points):** Participant identifies the same concept as the expert.
- **Partial Match (1 point):** Participant identifies a related or prerequisite concept.
- **Mismatch (0 points):** Participant identifies an incorrect or irrelevant concept.

---

## 6. Analysis Plan

### 6.1 Quantitative Analysis

#### SUS Scores
- **Between-Condition Comparison:** Independent-samples t-test comparing mean SUS(Condition B) vs. SUS(Condition A).
- **Effect Size:** Cohen's $d$ (medium effect $d \approx 0.5$ expected).
- **Hypothesis:** SUS(B) > SUS(A), $p < 0.05$.

#### Time-to-Answer
- **Within-Condition Median:** Report median and IQR for both conditions.
- **Interpretation:** If Condition B median < Condition A median, dashboard speeds up insight.

#### Task Accuracy
- **Logistic Model:** GEE (Generalized Estimating Equations) to account for multiple answers per session:
  - **Outcome:** Task Accuracy (0/1).
  - **Predictor:** Condition (A vs. B).
  - **Model:** `Accuracy ~ Condition | SessionID`.

#### Interaction Counts
- **Descriptive:** Mean interaction count by type (heatmap clicks, radar selections, KG hovers) for Condition B only.
- **Interpretation:** Interaction frequency as proxy for exploration depth.

### 6.2 Qualitative Analysis

#### Thematic Coding
1. **Prepare:** Transcribe all think-aloud and post-session interviews.
2. **Code Independently:** Two researchers independently code transcripts using the scheme above (inter-rater reliability: target Cohen's κ ≥ 0.70).
3. **Resolve Disagreements:** Discuss and reach consensus.
4. **Aggregate:** Count frequencies and extract illustrative quotes.

#### Causal Reasoning Extraction
- **Primary Claim:** Condition B participants generate more causal statements than Condition A.
- **Test:** χ² test of independence (Causal Attribution Rate vs. Condition).
- **Hypothesis:** Causal(B) > Causal(A), $p < 0.05$.

---

## 7. IRB Considerations

### Informed Consent
- Participants sign consent form before session begins.
- Explicitly approve audio/video recording for transcription purposes.
- Confidentiality guaranteed (data identified by session ID, not name).

### Data Security
- Audio recordings stored on encrypted server; deleted after transcription (if not needed for archival).
- Transcripts and logs identified by session ID.
- Access restricted to research team members.

### Compensation
- $\$50$ gift card (Amazon or institution-specific) provided after session completion.
- No penalty for early withdrawal (participant can leave at any time).

### Mandatory Reporting
- If participant discloses concerns about student harm or misconduct, researcher reports to appropriate office (Title IX, Dean of Students, etc.).

---

## 8. Timeline & Responsibilities

| Phase | Timeline | Owner |
|---|---|---|
| IRB Submission | April 2026 | PI |
| IRB Approval | May 2026 | IRB |
| Recruitment Launch | May 2026 | Co-investigators |
| Sessions 1–15 (Pilot) | May–June 2026 | Lead Researcher |
| Pilot Debrief & Refinement | June 2026 | Team |
| Sessions 16–30 (Main) | June–July 2026 | Lead Researcher |
| Transcription & Coding | July–August 2026 | Co-investigators |
| Analysis & Write-Up | August–September 2026 | PI + Lead Researcher |

---

## 9. Contingency Plans

### Low Recruitment
- **Plan:** Extend recruitment window; increase incentive to $\$75$.
- **Minimum N:** 10 per condition (feasible for qualitative analysis, though statistical power reduced).

### Participant No-Show
- **Plan:** Automatically reassign to next available slot (Calendly reminder sent 24h before).
- **Max Wait:** Recruit replacement participant within 1 week.

### Technical Failure (System Crashes During Session)
- **Plan:** Researcher restarts frontend server; participant rejoins with fresh session ID.
- **Data Loss:** Any interactions logged to localStorage are preserved; only server-side POST is lost (recoverable from localStorage dump).

### Ethical Concerns (Participant Distress)
- **Plan:** Researcher pauses session, offers break, allows participant to withdraw without penalty.
- **Escalation:** If concern involves student harm, follow mandatory reporting protocol.

---

## 10. Post-Study Communication

### Participant Feedback
- Within 1 week of study completion, send brief summary of findings (aggregate SUS scores, key themes) to all participants.
- Offer optional 30-minute debrief call with PI.

### Publication & Dissemination
- Results will be submitted to IEEE VIS 2027.
- All data will be anonymized; no individual participant is identifiable in any publication.
- Findings shared at conferences and posted on project website.

---

## Appendix A: Study Task Question

> **Scenario:**  
> You are a CS instructor reviewing data from your Data Structures exam. The system has graded all 646 student short-answer responses. Looking at this dataset, **which concept do students struggle with the most?** Which students would you prioritize for office hours? Why?
>
> You have up to 20 minutes. When you're ready, type your answer below and rate your confidence (1–5).

---

## Appendix B: SUS Items (Brooke, 1996)

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

**Scoring:**
- Odd items (1, 3, 5, 7, 9): contribution = rating − 1
- Even items (2, 4, 6, 8, 10): contribution = 5 − rating
- SUS Score = (sum of contributions) × 2.5 (range 0–100)

---

## Appendix C: Post-Session Interview Questions

1. **Sense-Making:** "What was your biggest takeaway from the data review?"

2. **Causal Attribution:** "Was there a specific moment when [a visualization / the summary] helped you understand the data differently?"

3. **Trust:** "On a scale of 1–5, how much do you trust the system's grades for this dataset? Why?"

4. **Rubric Refinement:** "You edited / didn't edit the rubric. Why?"

5. **Generalization:** "Would you use a tool like this to prepare for office hours or to refine your rubric? Why or why not?"

6. **Open-Ended:** "Anything else you'd like to share about your experience?"

---

## Appendix D: Data Export & Backup

After each session, researcher manually exports:

1. **Study Log JSON** — Exported from dashboard Export button; saved to `data/user_study_logs/session_[ID].json`.
2. **Task Answer & SUS Responses** — Manually copied from browser console or backend logs.
3. **Audio Recording** — Saved to secure server with restricted access.
4. **Researcher Notes** — Field notes from observation session, written immediately post-session.

**Weekly Backup:** All data synced to encrypted cloud storage (Google Drive with 2FA, or institutional Sharepoint).

---

## End of Protocol

**Approved by:** [PI Signature]  
**Date:** [Date]  
**IRB Protocol Number:** [Number, once approved]
