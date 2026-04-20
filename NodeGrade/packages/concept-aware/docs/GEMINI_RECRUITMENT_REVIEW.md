# Phase 2 User Study: Recruitment Email Review Brief for Gemini

**Context:** ConceptGrade is a visual analytics system for human-AI co-auditing of automated grading. Phase 2 requires a controlled user study with N=30 domain-expert educators (15 per condition: A=control summary, B=treatment interactive dashboard). The target dataset is DigiKlausur — 646 real Neural Networks course exam answers. Sessions are 45 minutes via Zoom. The study result will be submitted to IEEE VIS 2027 (VAST track).

**Recruitment Stage:** We are preparing to send cold outreach emails to CS and ML instructors at ~15 universities, followed by SIGCSE mailing list posts. IRB approval is pending (expected May 2026). The first recruitment batch targets Neural Networks and introductory ML instructors with 2+ years teaching experience.

**Question:** Does the email below strike the correct tone for academic cold outreach to CS faculty? Does it successfully avoid the "generic UX study" trap while conveying genuine scientific rigor?

---

## The Recruitment Email Under Review

### Subject Line
```
Research Participation: Neural Network Exam Data + AI Reasoning — 45 min study (IEEE VIS 2027)
```

### Body

```
Dear [Professor / Dr. Last Name],

I'm a PhD researcher at [Institution] studying how educators evaluate AI reasoning 
in automated grading systems. I'm reaching out because your work in neural networks 
or machine learning makes you an unusually well-positioned participant for this study.

Here is the core research question we're investigating:

    When an AI system grades a student's short-answer exam response, it produces a 
    step-by-step reasoning chain. That chain may—or may not—follow the conceptual 
    structure of the domain. Does visualizing the alignment between the AI's reasoning 
    and a neural networks knowledge graph help expert instructors diagnose student 
    misconceptions faster and with greater confidence than reading a text summary alone?

To test this, we built a visual analytics dashboard and loaded it with 646 real 
short-answer responses from a neural networks course exam—covering backpropagation, 
gradient descent, loss landscapes, and optimization. We are recruiting CS and ML 
instructors to spend 45 minutes working through that data the same way they would 
before office hours: identifying which students are struggling, with which concepts, 
and why.

The study involves no technical setup on your end and can be conducted via Zoom 
at a time of your choosing between May and July 2026.

What participants do:
  - Review student exam data using the dashboard (20 minutes)
  - Rate the system's usability on a standardized scale (5 minutes)
  - Revise a grading rubric based on what you discovered (10 minutes)
  - Debrief with me about your reasoning process (10 minutes)

The results will be submitted to IEEE VIS 2027 (VAST track). Your session data 
will be anonymized; you will receive a summary of findings after publication.

Compensation is a $50 Amazon gift card, sent within 48 hours of your session.

This study has been approved by [Institution] IRB (Protocol #[XXX]).

If you're willing to participate, please reply to this email with two or three 
times you're free in May or June, and I'll send a calendar invite. If you know 
a colleague who teaches neural networks or introductory ML and might be 
interested, a forward would be greatly appreciated.

Thank you for considering this. I'm happy to answer any questions about the study 
or share the full protocol.

Best regards,

[Full Name]
[Title, e.g., PhD Candidate / Postdoctoral Researcher]
[Department] | [Institution]
[Email] | [Lab/Project URL (optional)]
```

---

## Design Decisions Already Made (Do Not Revisit)

The following choices are pre-committed and should be treated as constraints:

1. **Dataset:** DigiKlausur only (Option A). 646 NN answers, N=15 per condition. Rotating datasets (Option B) was ruled out for statistical power and ecological validity reasons.
2. **Session length:** 45 minutes maximum. Not negotiable due to faculty time constraints.
3. **Scheduling approach:** Reply-first (ask for availability by email), Calendly link sent in follow-up response. Avoids cold-email → automated scheduling pipeline feel.
4. **Compensation:** $50 Amazon gift card. IRB-compliant, appropriate for 45-minute expert session.
5. **Venue signal:** IEEE VIS 2027 (VAST track) included in the email body and subject line.

---

## Specific Questions for Gemini

### 1. Subject Line Effectiveness
The current subject line is:
```
Research Participation: Neural Network Exam Data + AI Reasoning — 45 min study (IEEE VIS 2027)
```
- Is "Research Participation" as an opener too generic, or does it accurately signal the nature of the email and reduce spam classification?
- Does "(IEEE VIS 2027)" in the subject line increase or decrease open rates with CS faculty? Some may find venue-namedropping off-putting in a subject; others may find it credibility-signaling.
- Alternative tested: "45-minute study on AI grading — your neural networks expertise needed (VIS 2027)"
  - Is this better or worse, and why?

### 2. The Research Question Block
The verbatim research question is presented as an indented block in the middle of the email. This is unusual for recruitment emails.
- Does foregrounding the research question (rather than the study task or compensation) increase or decrease engagement for an academic audience?
- Is the question itself stated at the right level of specificity? Too technical ("knowledge graph") or appropriately precise for a CS/ML audience?
- Should the question be shortened or split into two sentences?

### 3. "The same way they would before office hours"
This phrase is intended to reframe the task from "evaluating a system" to "doing your actual job." 
- Does this land as intended for a CS instructor, or does it risk sounding presumptuous (implying all CS instructors hold office hours)?
- Is there a sharper formulation that preserves the professional-identity activation without the potential condescension?

### 4. Tone and Length
The email is approximately 300 words (body only), which is longer than a typical cold-outreach email but shorter than a full study invitation.
- For a busy CS faculty member, is 300 words the right length? Or should this be trimmed to ~200 words with a link to a full information sheet?
- Is the overall tone appropriately collegial (peer-to-peer researcher) without being either too casual or too formal?
- Any phrases that trigger "UX study" or "product evaluation" associations that should be reworded?

### 5. Missing Elements
- Should the email explicitly mention that this is a **controlled experiment** (participants are randomized to Condition A or B)? Or does disclosing the experimental design risk biasing the participant before the session?
- Should the email mention the **think-aloud protocol** (participants narrate their reasoning aloud)? This is non-trivial time/effort for the participant and could affect their willingness to participate — but omitting it feels like a disclosure gap.
- Should the email include a **one-line system description** ("ConceptGrade links an AI grading system to a prerequisite knowledge graph for Neural Networks")? Or does this over-define the system and prime the participant before the session?

### 6. The Snowball Ask
The email ends with: "If you know a colleague who teaches neural networks or introductory ML and might be interested, a forward would be greatly appreciated."
- Is this ask appropriately placed (end of email) and calibrated (soft, not pushy)?
- Would adding "I can send you a separate, shorter forwarding message if that would be easier" make the snowball ask more actionable?

---

## Contextual Background for Your Assessment

**Who we are recruiting:** CS and ML instructors at research universities and teaching colleges. Likely 50% tenure-track faculty, 50% lecturers/instructors. Most have taught neural networks, deep learning, or introductory ML. Median teaching load: 2 courses per semester. They receive ~10–15 unsolicited study invitations per semester.

**The risk we are trying to avoid:** The email reading as a user-testing request for a commercial or institutional AI product, rather than as a legitimate peer-research invitation on a question that is genuinely relevant to their teaching practice.

**The conversion target:** 8 confirmed participants from this first batch of ~20 targeted CS department emails. Acceptable response rate: 40%. If the email generates replies asking for more information, that is a success indicator even before scheduling.

**Institutional context:** This is academic research conducted under IRB approval. The participant's name and institution will not appear in any publication. The study is genuinely exploratory — we do not know whether the dashboard helps or not, and the email should honestly reflect that uncertainty.

---

## Gemini's Input Requested

Please advise on:

1. **Subject line:** Keep current, adopt the alternative, or propose a third option?
2. **Research question block:** Keep the verbatim indented format, shorten, or move to a linked information sheet?
3. **"Same way they would before office hours":** Keep, rephrase, or cut?
4. **Length:** 300 words is correct, trim to 200, or expand to 400 with an info-sheet link?
5. **Missing elements:** Should controlled-experiment design, think-aloud protocol, or system name be added?
6. **Snowball ask:** Acceptable as-is, strengthen, or cut?
7. **Overall verdict:** Is this email ready to send to CS department chairs and the SIGCSE mailing list, or does it need another revision pass?

Please advise. We will implement your recommendations before the first send.
