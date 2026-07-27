# Pilot Study Protocol — ConceptGrade Co-Auditing

**Purpose:** Validate the think-aloud protocol, task ordering, coding scheme,
and dashboard interactions before the main N=64 study. Pilot data are NOT
included in the main analysis.

**Target n:** 5 participants
**Duration per session:** 45-60 min
**When:** One week before main-study launch (target: week of May 25, 2026
for a June 1 main-study opening)
**Where:** Zoom, screen-share + audio recording (consent already gathered
under IRB Protocol \[PROTOCOL-NUMBER\] — pilot participants count under the
same protocol)
**Compensation:** USD 30 honorarium (same as main study)

---

## 1. Pilot-specific goals (logged as success criteria)

```yaml
goals:
  G1_task_clarity:
    target: all 5 pilots complete the 8-answer review with NO clarification
            questions about what they are supposed to do
    if_missed: revise the onboarding video / task instructions
  G2_think_aloud_volume:
    target: median think-aloud word count per answer >= 30
    if_missed: revise the prompt ("please narrate your reasoning out loud")
               and add a one-minute scripted practice example
  G3_protocol_time:
    target: 90% of sessions finish in <= 60 min (the time budget for main)
    if_missed: trim one of the 8 answers, or shorten the demographics section
  G4_coding_scheme_robustness:
    target: two coders code the same pilot transcript and reach Cohen's
            kappa >= 0.60 ("substantial-ish") on a first pass with the
            current codebook
    if_missed: codebook refinement; document each refined category boundary
               (especially CA vs II)
  G5_dashboard_no_show_stoppers:
    target: zero "I can't see" / "this looks broken" complaints during pilot
    if_missed: log the issue, file a UI bug, retest before main launch
```

Each goal has a binary "met / not met" outcome at the end of the pilot.
A goal-by-goal pilot summary report is added to the OSF pre-registration
addenda before main-study launch.

---

## 2. Participant flow

```
0. Recruit 5 educators matching the main-study inclusion criteria
   (Section 4 of IRB protocol). The same screening form is used.
1. Schedule a 60-min Zoom slot.
2. T-24h: send a one-page "what to expect" PDF and the consent form.
3. T-0: session.
4. T+7d: pilot debrief meeting (5 pilots over Zoom together, 30 min, optional)
5. T+10d: protocol addendum logged to OSF; main study opens.
```

---

## 3. Session script (use as-is; deviations logged)

### Section A — Welcome + re-consent (3 min)
> "Thanks for joining. This is a pilot of a study on grading dashboards. We'll
> record audio and your screen-share for analysis; no video of your face is
> recorded. You can stop at any time, no questions asked. Do you re-consent
> to participation?"

\[wait for verbal yes\]

> "I'll mostly stay quiet during the task. If you have a question, ask — but
> in the main study I'll only answer about logistics, not about how to grade.
> Ready?"

### Section B — Warm-up answer (Q0) (4 min)
\[Show the warm-up Mohler answer. Same UI as their assigned condition.\]

> "Here's a sample answer and an automated grade. Please walk me through how
> you would decide whether to agree, modify, or disagree, talking out loud.
> This one is just for practice — it doesn't get analysed."

\[Observe: do they actually verbalise? Note silence > 10 sec.\]

### Section C — 8 graded answers (32 min, 4 min each)
\[Rotate the 8 answers via the pilot Latin square (see §6).\]
For each answer:
1. Participant sees the question, the student's answer, and the ML grade.
2. Participant decides: \[agree / modify by ±0.5 / modify by ±1.0 / disagree\]
3. (Condition B only) Participant may add up to 3 rubric chips via Click-to-Add.
4. Participant rates self-confidence 0-100% via the on-screen slider.
5. Audio of their reasoning is recorded throughout.

Facilitator prompts (use sparingly):
- "Can you say a bit more about why?"
- "What were you looking at when you decided that?"
- "Anything you'd want the system to show you that it didn't?"

### Section D — SUS questionnaire (5 min)
\[10-item Brooke 1996 SUS, on-screen.\]

### Section E — Debrief (5 min)
> "Three quick questions:
> 1. Anything confusing or annoying in the interface?
> 2. Anything missing that you wished was there?
> 3. Was anything I asked unclear?"

Record verbatim notes.

### Section F — Thank-you + payment (1 min)
Confirm honorarium delivery; note any data-deletion requests.

---

## 4. Coding sheet (per-participant recording sheet, CSV-compatible)

`pilot_recording_sheet.csv` columns:

```
participant_pid           — anonymous code (P01..P05)
condition                  — A or B
session_date               — YYYY-MM-DD
session_start_utc          — ISO timestamp
warm_up_complete           — yes / no
warm_up_questions          — verbatim notes
answer_seq[1..8]_qid       — Mohler question ID for the i-th answer shown
answer_seq[1..8]_decision  — agree | modify_plus_05 | modify_plus_1 | modify_minus_05 | modify_minus_1 | disagree
answer_seq[1..8]_chips_added  — number of Click-to-Add chips (Condition B only)
answer_seq[1..8]_self_conf — integer 0..100
answer_seq[1..8]_seconds   — task latency
answer_seq[1..8]_thinkaloud_words  — word count from auto-transcript
sus_q1..sus_q10            — integer 1..5
session_end_utc            — ISO timestamp
debrief_confusing          — verbatim notes
debrief_missing            — verbatim notes
debrief_unclear            — verbatim notes
facilitator_flags          — any G1..G5 goals missed, with note
data_deletion_request      — yes / no
```

A blank version of this CSV is checked in at `data/pilot/pilot_template.csv`
and the filled per-session sheet is committed to a private branch
(\[REPO\]/study-data/pilot/) for audit.

---

## 5. Pilot coding kit for G4 (coding-scheme robustness)

Two coders independently code the same pilot transcript using the codebook:

| Code | Definition (one-line) | Positive example | Boundary case |
|---|---|---|---|
| **CA** Causal Attribution | Utterance attributes a decision to a specific visual artefact | "I'm dropping this because the gap badge on `tree_height` made me notice the student missed depth." | Vague "the chart shows…" without a specific artefact → NOT CA |
| **SA** Semantic Alignment | Rubric edit text refers to a KG node label verbatim or a 1-hop neighbour | edit: "must mention time complexity" when `time_complexity` is a KG node | Edit refers to general topic ("be more detailed") → NOT SA |
| **TC** Trust Calibration | Self-confidence statement that references the system's reliability | "I'm 60% sure because the system can be wrong on edge cases" | Pure self-rating with no system reference → NOT TC |
| **II** Interaction Insight | Emergent insight from interacting (zoom, filter, hover) that was not in the question | "Oh wait — when I hover here I see this concept is shared by 3 students who failed" | First-impression observation, not interaction-driven → NOT II |

Output: `pilot_irr_coding.csv` with `(participant, utterance_id, coder, code)`
rows. The κ computation script is:

```
python compute_taxonomy_kappa.py --kit pilot_irr_coding.csv  # or equivalent
```

(For the misconception-taxonomy κ we already use
`compute_taxonomy_kappa.py`; a small wrapper `compute_pilot_kappa.py` can
reuse the same Cohen's κ function on the CA/SA/TC/II label vectors.)

---

## 6. Latin square for the 8 answers

Pilot uses Mohler questions Q1, Q3, Q5, Q7, Q9 (Data Structures), each
shown with two student answers (one high-score, one low-score) for 10
total. The 8 actually presented per participant are rotated as:

```
P01 (cond A):  Q1H Q3H Q5H Q7H Q9H Q1L Q3L Q5L
P02 (cond B):  Q3H Q5H Q7H Q9H Q1H Q3L Q5L Q7L
P03 (cond A):  Q5H Q7H Q9H Q1H Q3H Q5L Q7L Q9L
P04 (cond B):  Q7H Q9H Q1H Q3H Q5H Q7L Q9L Q1L
P05 (cond A):  Q9H Q1H Q3H Q5H Q7H Q9L Q1L Q3L
```

(H = high-grade student answer, L = low-grade. The five rotations form a
modular Latin square on (question × position).)

---

## 7. Pilot data deletion

Per IRB §6, pilot raw audio is deleted within 30 days of transcript
verification. Pilot transcripts are retained as de-identified text only,
flagged with `study_phase = "pilot"`, and excluded from the main analysis
filter (`study_phase == "main"`).

---

## 8. After the pilot: addendum template

When the pilot completes, file the following 1-page addendum to OSF
**before** main-study recruitment opens. To close the standard "addenda
are a backdoor for post-hoc revisions" loophole, this addendum is gated
by **three hard commitments**:

1. **Addendum window closes at T-24h** (24 hours before main-study
   recruitment opens). Any addendum filed inside the T-24h window is
   logged as a deviation, not as part of the pre-registration.
2. **Any addendum filed in the T-48h to T-24h window must include a
   SHA-256 of the addendum file at OSF upload time**, recorded in the
   OSF metadata `addendum_sha256` field. This timestamp + hash combination
   is independently verifiable by reviewers.
3. **Addenda cannot revise locked items.** The OSF document §2 hypotheses
   (H1-H5), §6 statistical tests (Mann-Whitney $U$, Holm-Bonferroni),
   §6 IRR target ($\kappa \geq 0.70$), and §7 power-analysis decision
   rule ($d \geq 0.7$ confirmatory boundary) are NOT addendable. They can
   only be revised by filing a full re-registration that supersedes the
   original (a public, auditable act).

Addenda may revise: codebook category boundaries (with positive examples),
task-instruction wording, Latin-square assignment if a pilot participant
withdraws, and the addendum-template text itself (the OSF doc's deviation
log).

```yaml
pilot_summary:
  n_pilots: 5
  dates: YYYY-MM-DD .. YYYY-MM-DD
  goals_met: [G1: yes/no, G2: yes/no, G3: yes/no, G4: yes/no, G5: yes/no]
  protocol_refinements:
    - description: ...
      change_made_to: [onboarding_video | task_script | codebook | UI ]
      rationale: ...
  codebook_changes:
    - code: CA  (or SA / TC / II)
      change: clarified boundary to ...
      rationale: ...
  irr_pilot_kappa: <number>
  decision: PROCEED  (or REPILOT)
```

This addendum is the gate before main-study recruitment opens.

---

## 9. Files this protocol commits to the repo

```
PILOT_PROTOCOL.md                  ← this document
data/pilot/pilot_template.csv      ← blank recording sheet (created on demand)
data/pilot/pilot_irr_coding.csv    ← per-utterance coding (after pilot)
compute_pilot_kappa.py             ← optional wrapper around κ computation
```
