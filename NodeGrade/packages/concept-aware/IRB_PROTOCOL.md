# IRB Protocol — ConceptGrade Educator Co-Auditing Study

**Working title:** Educator Use of a Visual-Analytics Dashboard for Co-Auditing
of Automated Short-Answer Grading

**Submission target:** \[YOUR INSTITUTION\] IRB — Expedited review
(Category 7: research employing survey, interview, or observation of
public behaviour of adults), low risk.

---

## 1. Investigators

```
Principal Investigator: [NAME, TITLE], [DEPARTMENT], [INSTITUTION]
                        Email: [EMAIL]   Office: [PHONE]
Co-Investigator(s):     [NAME, TITLE], [DEPARTMENT]
Faculty Sponsor:        [If PI is a student, list sponsor here]
```

---

## 2. Study summary (lay language, ≤ 250 words)

This study evaluates whether an interactive dashboard helps university-level
instructors and teaching assistants understand and audit grades produced by
an automated short-answer grading system. Participants are randomly assigned
to one of two interface conditions: a text-only summary or a full interactive
visual dashboard. Each participant reviews 8 pre-graded student answers,
decides whether to agree with or modify the automated grade, and may add
rubric criteria. We collect the participant's grade decisions, rubric edits,
self-reported confidence, and an audio recording of their think-aloud
narration. After the task, participants complete a 10-item System Usability
Scale (SUS) questionnaire and a brief open-ended debrief. The session takes
45-60 minutes and is conducted remotely via Zoom. Participants receive a
$30 honorarium.

The study addresses a published research question: does grounding an
automated grader's reasoning in a structured knowledge graph, and making
that grounding visually explorable, change how educators audit and revise
grades? Findings inform both educational technology design and human-AI
co-auditing theory.

---

## 3. Risks and benefits

```yaml
risks:
  physical: none (remote, screen-based task)
  psychological: minimal - participants discuss familiar professional tasks
  privacy:
    - audio recording: stored locally on encrypted institutional drive
    - transcripts: de-identified before any analysis (PII scrub: names,
      institution names, specific course numbers, email addresses)
    - direct identifiers stored separately in a locked file accessible only
      to the PI, destroyed 12 months after publication
  professional: none (no employer notified, no performance evaluation)

benefits:
  to_participant: $30 honorarium; exposure to a research tool relevant to
                  teaching practice
  to_society: improved design of human-AI educational tools; published
              findings inform automated-grading deployment guidelines
```

Risk level: **MINIMAL** — research involves no more than the risks of daily
life or of routine professional teaching activity.

---

## 4. Recruitment

```yaml
target_n: 64 (32 per condition)
recruitment_channels:
  - department listserv announcement (text in Appendix A)
  - SIGCSE / SIGGRAPH professional Slack workspaces (with moderator approval)
  - Prolific panel filtered for "tertiary educator + technical subject"
inclusion_criteria:
  - 18+ years old
  - at least 2 years of teaching experience in a technical course (CS,
    EE, math, physics, engineering)
  - functional English proficiency (study materials in English)
  - reliable internet connection (videoconference + screen sharing)
exclusion_criteria:
  - inability to provide informed consent
  - participated in the pilot study
  - direct conflict of interest with PI (current or recent student,
    co-author, family member)
```

---

## 5. Consent process

- Online consent form (Appendix B) hosted on the institutional consent
  platform; participant ticks each comprehension check before "I agree."
- An additional check ("Please describe in one sentence what data will be
  recorded") gates entry; non-responsive participants are excluded with
  no penalty and no honorarium claim.
- Participants may withdraw at any time without giving a reason; if they
  withdraw, recorded audio is deleted on request and the honorarium is
  paid pro-rata.
- Re-consent is requested at the start of the Zoom session (verbal).

---

## 6. Data management

```yaml
collection:
  what: grade decisions, rubric edits, mouse/click logs (no keystroke
        capture), audio of think-aloud, SUS responses, debrief responses
  where: participant's machine -> Zoom recording -> downloaded same day
         to institutional encrypted drive
storage:
  raw_audio: encrypted institutional drive, access limited to PI and one
             approved transcriber under non-disclosure
  transcripts: de-identified before any analysis runs
  identifiers: separate locked file, paired by anonymous participant code
retention:
  raw_audio: deleted 30 days after transcript verification (typical:
             6-8 weeks)
  de_identified_transcripts: retained 5 years post-publication (per
                             institutional research-records policy)
  identifier_file: destroyed 12 months after final publication
sharing:
  - de-identified transcripts: deposited to OSF, embargoed until
    publication, then open under CC-BY 4.0
  - raw audio: NEVER shared
  - identifier file: NEVER shared
```

---

## 7. Compensation

- USD 30 per completed 60-min session, paid via the institutional honorarium
  workflow (preferred) or Prolific (for Prolific-recruited participants).
- Participants who withdraw mid-session receive USD 15 (pro-rata).
- No bonus for "good" or "fast" performance — no performance-contingent
  compensation.

---

## 8. Conflicts of interest

The PI is an author on the publications that will report these results.
The dashboard under evaluation is also developed by the PI's group; this
is disclosed to participants in the consent form (Appendix B §3).

No financial conflicts; no industry funding for the dashboard or the
study. All compute and honorarium costs from institutional/grant funds.

---

## 9. Reporting

Adverse events: PI to report to IRB within 5 business days of awareness,
with mitigation steps for already-collected participants.

Annual continuing review: filed with IRB per institutional policy.

---

## 10. Appendices to attach to IRB submission

```
A. Recruitment text (email + flyer + Prolific advertisement)
B. Informed consent form (online + Zoom-session verbal script)
C. Demographic questionnaire (anonymous, age range / experience years /
   discipline / dashboard familiarity / accessibility needs)
D. SUS questionnaire (standard 10-item, Brooke 1996)
E. Debrief script
F. Data Management Plan (institutional standard form)
G. CV of PI
H. Letter of support from department chair
```

---

## 11. To paste back into Paper 2 after IRB approval

```
IRB approval status: APPROVED
Institution        : [INSTITUTION]
IRB Board name     : [BOARD]
Protocol number    : [PROTOCOL-NUMBER]
Approval date      : [YYYY-MM-DD]
Expiry date        : [YYYY-MM-DD]
```
