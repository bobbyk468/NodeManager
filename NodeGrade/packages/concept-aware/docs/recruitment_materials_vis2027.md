# ConceptGrade User Study — Recruitment Materials

**Version:** 2.0 (post-Gemini review)  
**Date:** April 2026  
**Study:** IEEE VIS 2027 Educator User Study  
**Target N:** 30 educators (15 per condition)  
**Timeline:** May–July 2026

---

## 1. Email Invitation (Primary)

### Subject Line (CS / Neural Networks Instructors)
```
Research Invitation: Your Neural Networks expertise for AI grading study (VIS 2027)
```

### Email Body (Version A: CS & Neural Networks Instructors — v2.0)

```
Dear [Professor / Dr. Last Name],

I am a PhD researcher at [Institution] studying how educators evaluate AI reasoning.
I am reaching out because your experience teaching neural networks makes you an
ideal participant for our upcoming study.

We are investigating a core problem in automated grading:

    Can visualizing an AI's internal reasoning against a domain knowledge graph
    help expert instructors diagnose student misconceptions faster and more
    confidently than reading text alone?

To test this, we built a visual analytics dashboard loaded with 646 real
short-answer exam responses covering backpropagation, gradient descent, and
optimization. We are recruiting CS/ML instructors to evaluate this data, acting
as if they were prepping for a lecture or office hours.

The Details:
  * Task: Explore the exam data using the dashboard, "think aloud" through your
    reasoning process, and update a grading rubric based on your findings.
  * Commitment: 45 minutes via Zoom (flexible scheduling in May–July).
  * Compensation: $50 Amazon gift card.

The results will be submitted to IEEE VIS 2027 (VAST track). Your session data
will be fully anonymized. This study is approved by [Institution] IRB
(Protocol #[XXX]).

If you are willing to participate, please reply with 2 or 3 times you are free
next month, and I will send a calendar invite.

Thank you for your time and consideration. If you know a colleague who might be
interested, a quick forward would be greatly appreciated!

Best regards,

[Full Name]
[Title, e.g., PhD Candidate / Postdoctoral Researcher]
[Department] | [Institution]
[Email]
```

---

**Gemini review changes (v1.0 → v2.0):**

| # | Decision | v1.0 | v2.0 | Gemini Rationale |
|---|----------|------|------|-----------------|
| 1 | Subject line | "Research Participation: Neural Network Exam Data + AI Reasoning — 45 min study (IEEE VIS 2027)" | "Research Invitation: Your Neural Networks expertise for AI grading study (VIS 2027)" | "Invitation" is more collegial; expertise framing activates recipient identity; shorter |
| 2 | Research question | 4-sentence paragraph explaining chain-of-thought + KG mechanics | Single block-quoted sentence, jargon-free | Cold email hook needs the question, not the mechanism — de-jargonize |
| 3 | Office hours framing | "the same way they would before office hours" | "as if they were prepping for a lecture or office hours" | Softens assumption; covers lecture prep scenario too |
| 4 | Length | ~300 words | ~200 words | Trim to: what is this / why me / what do I do / what do I get |
| 5a | Controlled experiment disclosure | Not mentioned | Not mentioned | ✅ Confirmed: do not mention — adds cognitive load, risks priming bias |
| 5b | Think-aloud protocol | Not mentioned | Added: "think aloud through your reasoning process" | Sets expectation for active/conversational session vs. silent clicking |
| 5c | System name | Not mentioned | Not mentioned | ✅ Confirmed: "visual analytics dashboard" sufficient; "ConceptGrade" means nothing pre-session |
| 6 | Snowball ask | "a forward would be greatly appreciated" | Same, kept at end | ✅ Confirmed: soft, correctly placed, no friction added |

### Email Body (Version B: Math & Physics Instructors)

```
Dear [Instructor Name],

You're invited to participate in a research study on AI-assisted grading for 
short-answer exams.

STUDY OVERVIEW:
You'll spend 45 minutes reviewing exam data (your choice of domain: Calculus, Physics, 
or Computer Science) using a new visual analytics dashboard. The system combines 
automated grading with interactive visualizations to help instructors identify patterns 
in student understanding.

WHY YOUR PARTICIPATION MATTERS:
- Test a cutting-edge tool designed by educators, for educators
- Real exam data from actual courses
- Your expertise helps us understand how visualization supports expert decision-making
- Participate in shaping the future of AI-assisted teaching tools

WHAT YOU'LL DO:
1. Review exam data using our interactive dashboard (20 min)
2. Rate the usability of the system (5 min)
3. Optionally refine your grading rubric (10 min)
4. Discuss your experience in a brief conversation (10 min)

COMPENSATION:
- $50 Amazon gift card
- Flexible scheduling
- Publication results shared with you

QUALIFICATION:
- Currently or recently taught a course with short-answer grading
- Comfortable evaluating student work
- English fluency
- 45–60 minutes available May–July 2026

SIGN UP:
[Calendly Link]

Questions? Contact: [PI Name] at [Email]

---

## 2. Recruitment Channels & Strategy

### Primary Channels (Priority Order)

| Channel | Target | Timeline | Expected Confirmations | Owner |
|---------|--------|----------|------------------------|-------|
| **CS Department Chairs (Direct Outreach)** | Data Structures, Algorithms, OOP instructors at ~15 universities | May 1–15 | 8 participants | Co-investigator 1 |
| **SIGCSE Mailing List** | Computer Science educators listserv (thousands of subscribers) | May 15–31 | 7 participants | Co-investigator 2 |
| **ACM ICER & IEEE FIE Online Forums** | Interaction, computing education communities | May 15–June 15 | 5 participants | Co-investigator 1 |
| **Professional Teaching Networks** | ASEE (American Society for Engineering Education), MAA (Math Assoc. of America) | June 1–15 | 5 participants | Co-investigator 2 |
| **Snowball Sampling** | Referrals from existing participants | May–July (parallel) | 5 participants | Lead Researcher |

### Secondary Channels (If Primary Falls Short)

- University faculty social media (Facebook groups for CS educators, LinkedIn)
- Online teaching communities (The Discipline of Teaching Algorithms)
- Direct LinkedIn/Twitter outreach to educators in target domains

---

## 3. Key Talking Points

### Primary Value Proposition
✅ **"Real data from your domain of expertise"**
- Participant will evaluate exam data from their own teaching area (NN, CS, Math, Physics)
- Authentic misconceptions from real students
- Relevance to their daily teaching practice

### Secondary Messaging
✅ **"Interactive exploration, not passive evaluation"**
- Participant actively uses a visual analytics system (not just surveys or questionnaires)
- Hands-on engagement with real student answers
- Opportunity to discover patterns they wouldn't see in summary statistics

✅ **"Flexible, low-commitment participation"**
- 45 minutes total (one session)
- Online or in-person options
- $50 compensation for time

✅ **"Help shape AI tools for educators"**
- Direct input on system design
- Rare opportunity to influence how AI grading tools integrate with teaching
- Results published and shared back to participants

### Objection Handling

**"I don't have time for an hour commitment."**
- "The session is structured to fit your schedule—early morning, lunch hour, or after class. Many educators complete it in 45 minutes."

**"Why should I trust an AI grading system?"**
- "This study asks *you* to evaluate whether the system is trustworthy and useful. We're not assuming you should trust it—we're testing whether it helps you make better decisions."

**"I'm not tech-savvy."**
- "No technical background required. The dashboard is designed for educators, not technologists. Most participants find it intuitive."

**"What happens with my data?"**
- "All responses are anonymized. You're identified by session ID, not your name. Results published in research papers, never sold or shared with third parties."

---

## 4. Recruitment Email Template (Department Chair Outreach)

### Subject
```
Invitation: Participate in AI-Assisted Grading Study ($50 Compensation)
```

### Body
```
Dear [Department Chair Name],

I am recruiting Computer Science educators for a research study on interactive 
dashboards for AI-assisted grading. I'm reaching out to [Department Name] to see 
if you or your colleagues might be interested in participating.

STUDY: Evaluating Visual Analytics for Automated Short-Answer Grading
- 45-minute session (flexible scheduling, online or in-person)
- Participants review real neural network exam data using a new dashboard
- $50 Amazon gift card compensation
- IRB-approved (Protocol #[XXX])

IDEAL CANDIDATES:
- Computer Science educators (Data Structures, Algorithms, OOP, ML/NN courses)
- 2+ years teaching experience
- Currently grading short-answer exams

RECRUITMENT TIMELINE: May–July 2026

Would you be willing to:
1. Forward this invitation to your faculty?
2. Allow me to present the opportunity at a department meeting?
3. Suggest 2–3 colleagues who might be interested?

I'm happy to accommodate your department's schedule. The more we can learn from 
actual educators, the better the tool design will be.

Please let me know if you have any questions or would like to discuss further.

Best regards,
[PI Name]
[Title]
[Institution]
[Email]
[Phone]
```

---

## 5. Recruitment Flyer (Print & Digital)

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║  📊 PARTICIPATE IN RESEARCH STUDY 📊                            ║
║                                                                  ║
║  Evaluating AI-Assisted Grading Dashboards                      ║
║                                                                  ║
║  ✅ 45 minutes                  ✅ Real student data             ║
║  ✅ $50 compensation            ✅ Your expertise needed         ║
║  ✅ Flexible scheduling         ✅ Change education tools        ║
║                                                                  ║
║  WHO WE'RE LOOKING FOR:                                         ║
║  • Computer Science, Math, Physics, or Engineering instructors  ║
║  • Currently teach short-answer assessment courses              ║
║  • 2+ years teaching experience                                 ║
║                                                                  ║
║  WHAT YOU'LL DO:                                                ║
║  Review real exam data using an interactive dashboard           ║
║  Answer questions about usability and effectiveness             ║
║                                                                  ║
║  📅 SIGN UP:                                                    ║
║  [Calendly QR Code] or                                          ║
║  [URL Link]                                                     ║
║                                                                  ║
║  ❓ QUESTIONS? Email: [PI Email]                               ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 6. Scheduling & Logistics

### Calendly Setup
- **Event Title:** "ConceptGrade User Study Session"
- **Duration:** 60 minutes (includes 5-min buffer)
- **Availability:** May 1 – July 31, 2026 (multiple time slots per day)
- **Time Zones:** Accommodate multiple zones (EST, CST, MST, PST)
- **Locations:** Online (Zoom link auto-generated) or In-Person [City] (if applicable)
- **Reminder:** Auto-send 24 hours before session

### Confirmation Email (Auto-Sent After Scheduling)

```
Subject: Your ConceptGrade Study Session Confirmed

Dear [Participant Name],

Thank you for signing up for our research study on AI-assisted grading dashboards!

SESSION DETAILS:
Date & Time: [Date] at [Time] [Timezone]
Duration: 45–60 minutes
Location: [Zoom Link] or [In-Person Address]

BEFORE YOUR SESSION:
1. Review the Informed Consent form (attached)
2. Test your internet connection (if participating online)
3. Have a notebook handy if you'd like to take notes

WHAT TO EXPECT:
- Brief intro (3 min)
- Explore real neural network exam data using our dashboard (20 min)
- Answer a usability questionnaire (5 min)
- Discuss your experience (10 min)
- Debrief and compensation (5 min)

QUESTIONS OR NEED TO RESCHEDULE?
Reply to this email or contact [PI Name] at [Email] / [Phone]

We appreciate your time and expertise!

Best,
[Research Team]
```

---

## 7. Informed Consent & IRB Documentation

### Informed Consent Form (1-Page Summary)

```
INFORMED CONSENT FORM
ConceptGrade User Study

STUDY TITLE: Evaluating Interactive Visual Analytics for Human-AI Co-Auditing 
of Automated Grading

PRINCIPAL INVESTIGATOR: [PI Name], [Institution]

PURPOSE:
This study investigates whether an interactive visual analytics dashboard helps 
educators identify student misconceptions and evaluate automated grading systems 
more effectively than traditional summary statistics.

PROCEDURES:
You will:
- Review anonymized exam data (646 student short-answer responses) using our dashboard
- Explore the data for up to 20 minutes, thinking aloud about your observations
- Answer a 10-item usability questionnaire
- Optionally refine a grading rubric
- Participate in a brief post-session interview (10 minutes)

TOTAL TIME: 45–60 minutes

RISKS:
Minimal. The study involves no physical risk or significant psychological stress. 
If at any time you feel uncomfortable, you may pause or withdraw without penalty.

BENEFITS:
- $50 Amazon gift card
- Opportunity to influence the design of AI-assisted teaching tools
- Findings shared back to you after publication

CONFIDENTIALITY:
- All data identified by session ID, not your name
- Audio recordings stored securely and deleted after transcription (unless archived 
  for research purposes)
- Findings published in anonymized form only
- Access restricted to research team members

VOLUNTARY PARTICIPATION:
Participation is entirely voluntary. You may withdraw at any time without penalty 
or loss of compensation.

QUESTIONS?
Contact [PI Name] at [Email] or [Phone]
For questions about your rights as a research participant, contact [IRB Office] 
at [IRB Phone].

─────────────────────────────────────

By signing below, you acknowledge:
- I have read and understood this consent form
- I agree to participate in this study
- I consent to audio/video recording for transcription purposes
- I understand my data will be kept confidential and anonymized

Signature: _____________________   Date: _______________
Printed Name: ____________________
```

---

## 8. Recruitment Timeline & Targets

### Phase 1: Announcement (May 1–15)
- Email department chairs (~15 universities)
- Post SIGCSE listserv announcement
- Set up Calendly scheduling portal
- **Target:** 8 confirmations

### Phase 2: Social Proof & Amplification (May 15–June 15)
- Share preliminary participant testimonials / interest levels
- Post to ACM ICER, IEEE FIE forums
- Snowball sampling (early participants refer peers)
- **Target:** 10 additional confirmations (total: 18)

### Phase 3: Final Push (June 15–July 1)
- Targeted LinkedIn/Twitter outreach to educators in target domains
- Extended deadline announcement
- Increased incentive offer ($75 gift card) for quick signup
- **Target:** 12 more confirmations (total: 30)

### Contingency (If N < 20 by July 1)
- Extend recruitment to mid-July
- Increase compensation to $75
- Recruit replacement participants as no-shows occur

---

## 9. Retention & Follow-Up

### Session Reminder (24 Hours Before)
```
Calendly auto-sends reminder with Zoom link and quick checklist.
```

### Post-Session (Within 1 Week)
- Thank-you email with brief findings summary
- Optional: 30-minute debrief call with PI
- Publication updates when paper is submitted/accepted

### Long-Term
- Participant newsletter (annual): Share results and future studies
- Invite to future ConceptGrade research (if ongoing)

---

## 10. Tracking & Reporting

### Recruitment Tracker Spreadsheet
| Date | Channel | Name | Email | Condition | Session Time | Confirmed | Status |
|------|---------|------|-------|-----------|--------------|-----------|--------|
| 5/3  | SIGCSE  | Jane Doe | jane@cs.edu | A | 5/21 10:00am | Y | Completed |
| ...  | ...     | ...  | ...   | ... | ... | ... | ... |

### Weekly Status Report
```
Week of May 3–7:
- Confirmations: 3 (target: 6)
- No-shows: 0
- Completed sessions: 1
- Action: Increase SIGCSE outreach, contact 5 more department chairs
```

---

## 11. Participant Testimonial Examples (Post-Participation)

*To be collected and used in future recruitment cycles:*

- "The dashboard helped me spot patterns in student reasoning I wouldn't see from final scores alone." — Dr. Jane Smith, CS Educator
- "The interactive visualization made the AI's decision-making process transparent. I appreciated seeing the reasoning breakdown." — Dr. Robert Lee, ML Instructor
- "Participating was quick and the researchers were professional. Would recommend to colleagues." — Dr. Sarah Chen, Data Structures Instructor

---

## End of Recruitment Materials

**Prepared by:** [PI Name]  
**Date:** April 2026  
**Version:** 1.0  
**Status:** Ready for Deployment (IRB Approval Pending)
