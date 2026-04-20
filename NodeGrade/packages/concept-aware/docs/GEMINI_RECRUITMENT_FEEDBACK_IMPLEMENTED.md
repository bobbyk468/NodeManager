# Gemini Recruitment Email Review — Implementation Status

**Date:** April 17, 2026  
**Review Status:** ✅ ALL FEEDBACK IMPLEMENTED  
**Email Status:** Ready for deployment (pending IRB protocol number)

---

## Executive Summary

Gemini's review identified one overarching structural problem in the v1.0 email — it was optimized for comprehensiveness rather than 15-second skim readability — and provided six specific, actionable decisions. All six have been implemented. The email is now approximately 200 words (trimmed from ~300), uses a block-quoted research question as the visual hook, and correctly omits both the controlled-experiment design and the system name.

---

## Feedback Items: Status Tracking

### 1. ✅ Subject Line — Revised to "Invitation + expertise framing + shorter"

**Feedback:** "Research Participation" reads as a generic psychology department blast. Adopt the alternative: "Research Invitation: Your Neural Networks expertise for AI grading study (VIS 2027)."

**Changes Made:**
- ✅ Changed "Research Participation" → "Research Invitation"
- ✅ Changed "Neural Network Exam Data + AI Reasoning — 45 min study" → "Your Neural Networks expertise for AI grading study"
- ✅ Retained "(VIS 2027)" as venue credibility signal
- **Location:** `recruitment_materials_vis2027.md`, Section 1, Subject Line

**Impact:** More collegial, expertise-activating, and shorter — reduces cognitive load at the subject line stage.

---

### 2. ✅ Research Question Block — De-jargonized and shortened

**Feedback:** The indented block visual pattern is correct, but the content is too dense — it explains TRM mechanics rather than presenting the scientific hook. Shorten to a single, jargon-free sentence.

**Changes Made:**
- ✅ Removed: 4-sentence paragraph explaining chain-of-thought reasoning chains, structural continuity, and domain knowledge graph projection
- ✅ Replaced with single block-quoted sentence: "Can visualizing an AI's internal reasoning against a domain knowledge graph help expert instructors diagnose student misconceptions faster and more confidently than reading text alone?"
- **Location:** `recruitment_materials_vis2027.md`, Section 1, Email Body

**Impact:** Hook reads in under 5 seconds. The question is genuinely interesting to CS/ML faculty without requiring them to understand TRM first.

---

### 3. ✅ Office Hours Framing — Softened to include lecture prep

**Feedback:** "The same way they would before office hours" presumes all instructors hold office hours as their primary prep activity. Soften to "as if they were prepping for a lecture or office hours."

**Changes Made:**
- ✅ Changed "the same way they would before office hours" → "acting as if they were prepping for a lecture or office hours"
- **Location:** `recruitment_materials_vis2027.md`, Section 1, Email Body, paragraph 3

**Impact:** Covers both lecturing faculty and office-hours-focused instructors; maintains professional-identity activation without the condescension risk.

---

### 4. ✅ Length — Trimmed from ~300 to ~200 words

**Feedback:** 300 words is too dense for cold faculty outreach. Trim ruthlessly to answer only: What is this? Why me? What do I have to do? What do I get?

**Changes Made:**
- ✅ Removed: "The study involves no technical setup on your end and can be conducted via Zoom at a time of your choosing" — redundant with "Commitment: 45 minutes via Zoom"
- ✅ Removed: Itemized time breakdown (20 min / 5 min / 10 min / 10 min) — replaced with task bullet that covers the essence
- ✅ Removed: "You will receive a summary of findings after publication" — implicit in "results will be submitted to IEEE VIS 2027"
- ✅ Removed: "I'm happy to answer any questions about the study or share the full protocol" — unnecessary in v2.0; reply-first scheduling handles this naturally
- ✅ Removed: Lab/Project URL from signature — optional detail that clutters the sign-off
- **Location:** `recruitment_materials_vis2027.md`, Section 1, Email Body (full)

**Impact:** Email now reads in approximately 60 seconds; passes the 15-second skim test for the key information.

---

### 5a. ✅ Controlled Experiment Disclosure — Confirmed: Do Not Mention

**Feedback:** Do not mention Conditions A and B. Adds cognitive load and risks biasing participant expectations before the session.

**Status:** ✅ Confirmed as correct in v1.0 — not added. This is pre-registered as a non-disclosure in the study protocol.

**IRB Note:** The informed consent form (Appendix of `user_study_protocol_vis2027.md`) covers disclosure of the experimental design *before the session begins*. The recruitment email is not the appropriate venue for this disclosure.

---

### 5b. ✅ Think-Aloud Protocol — Added to task description

**Feedback:** Yes, briefly mention the think-aloud protocol. It sets the expectation that this is an active, conversational session, not a passive clicking task. Faculty who are uncomfortable narrating their reasoning should self-select out at this stage.

**Changes Made:**
- ✅ Added to task bullet: "Explore the exam data using the dashboard, **'think aloud' through your reasoning process**, and update a grading rubric based on your findings."
- **Location:** `recruitment_materials_vis2027.md`, Section 1, Email Body, "The Details" section

**Impact:** Accurate expectation setting; reduces mid-session dropout from faculty who weren't prepared for the think-aloud requirement.

---

### 5c. ✅ System Name ("ConceptGrade") — Confirmed: Do Not Mention

**Feedback:** "ConceptGrade" means nothing to a participant who has never seen it. "Visual analytics dashboard" is sufficient and avoids priming. The system name is revealed during the session orientation.

**Status:** ✅ Confirmed as correct in v1.0 — not added. "ConceptGrade" remains absent from the recruitment email.

---

### 6. ✅ Snowball Ask — Confirmed: Keep As-Is

**Feedback:** Soft ask is correctly placed (end of email) and correctly calibrated (not pushy). No changes needed.

**Status:** ✅ Confirmed and retained: "If you know a colleague who might be interested, a quick forward would be greatly appreciated!"

**Note:** The alternative (offering a shorter forwarding blurb) was considered but not implemented — the current soft ask already enables snowball without adding another action item for the recipient.

---

## What Was Not Changed (Confirmed Correct in v1.0)

| Element | Status | Rationale |
|---------|--------|-----------|
| Reply-first scheduling (no Calendly in email) | ✅ Kept | Human exchange before automation; increases conversion from "interested" to "confirmed" |
| Compensation ($50) placed after scientific rationale | ✅ Kept | Avoids transactional framing; compensation last signals academic research, not product incentive |
| IRB protocol number in body | ✅ Kept | Institutional credibility signal; FERPA/data protection concern for faculty handling student-adjacent data |
| IEEE VIS 2027 in both subject and body | ✅ Kept | Venue credibility is a high-value trust signal for CS/HCI faculty |
| Peer-to-peer opening ("I am a PhD researcher") | ✅ Kept | Faculty respond to researchers, not organizations |

---

## Outstanding Pre-Send Checklist

Before the first email is sent, the following placeholders must be populated:

| Placeholder | Required Value | Status |
|-------------|---------------|--------|
| `[Full Name]` | Legal name of PI/sender | ⏳ Pending |
| `[Title]` | Current academic title | ⏳ Pending |
| `[Department] \| [Institution]` | Full institutional affiliation | ⏳ Pending |
| `[Email]` | Institutional `.edu` email address | ⏳ Pending |
| `[Institution] IRB (Protocol #[XXX])` | IRB protocol number after approval | ⏳ **Gating — do not send before IRB approved** |

---

## Send Order and Timing

| Batch | Channel | Target | Send Date |
|-------|---------|--------|-----------|
| 1 | CS Department Chairs (direct email) | 15 institutions → 8 confirmations | May 1–15, 2026 |
| 2 | SIGCSE Mailing List | Broadcast → 7 confirmations | May 15–31, 2026 |
| 3 | ACM ICER / IEEE FIE Forums | Online posts → 5 confirmations | June 1–15, 2026 |
| 4 | Snowball from Batches 1–3 | Referrals → 5 confirmations | May–July (parallel) |
| 5 | Final push (if N < 20 by July 1) | LinkedIn / Twitter targeted outreach | July 1–15, 2026 |

---

## Implementation Summary

**Total Feedback Items:** 6 (+ 3 confirmations of correct v1.0 decisions)  
**Implemented:** 6/6 ✅  
**Confirmed unchanged:** 3/3 ✅  
**Word count reduction:** 300 → ~200 words (33% reduction)  
**Email version:** v2.0 (final, pending IRB number)

---

**Document Prepared By:** Claude (implementing Gemini feedback)  
**Feedback Received From:** Gemini  
**Timestamp:** April 17, 2026
