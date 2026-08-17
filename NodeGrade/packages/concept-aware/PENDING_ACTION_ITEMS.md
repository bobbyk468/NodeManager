# Pending Action Items for Dissertation

**Last Updated:** May 7, 2026  
**Current Status:** Papers Ready for Peer Review (88/100 defensible)

---

## 🔴 CRITICAL PATH (Must Do Before June 1)

### Phase 1: Pre-Study Setup (May 8-31)

- [ ] **Distribute papers to advisor**
  - Status: Ready
  - Papers: `ConceptGrade_FullPaper.pdf`, `paper_phase2_vis2027.pdf`
  - Action: Email both PDFs + `FINAL_READINESS_REPORT.txt`
  - Timeline: May 8
  - Owner: You
  - Outcome: Advisor sign-off or feedback

- [ ] **Review advisor feedback and incorporate changes**
  - Status: Pending
  - Effort: 2-4 hours depending on feedback
  - Timeline: May 9-15
  - Owner: You
  - Deliverable: Final paper versions approved by advisor

- [ ] **Confirm June 1 study start date with advisor**
  - Status: Pending
  - Action: Align on recruitment schedule, session capacity
  - Timeline: May 8-10
  - Owner: You
  - Outcome: Locked start date

- [ ] **Begin participant recruitment (N=64 target)**
  - Status: Pending
  - Target: 64 educators (32 per condition)
  - Recruitment channels: TBD (email lists, Prolific, university networks)
  - Timeline: May 15-31
  - Owner: You + recruitment team
  - Outcome: 64 confirmed participants with signed consent

- [ ] **Test study hardware setup**
  - Status: Pending
  - Items to test:
    - [ ] External USB microphone (audio levels)
    - [ ] Screen recording software (test 20-min session)
    - [ ] Kitchen timer (audible alarm)
    - [ ] Zoom/Meets room settings (if remote study)
    - [ ] Backend/Frontend servers (localhost:3001 + localhost:5173)
  - Timeline: May 20-27
  - Owner: You + facilitator
  - Deliverable: Hardware test log with all items passing

- [ ] **Print and laminate facilitator materials**
  - Status: Ready to print
  - Documents:
    - [ ] `FACILITATOR_COMMAND_CARD.md` (laminate for durability)
    - [ ] `STUDY_SESSION_FLOW_DIAGRAM.txt` (print 2 copies)
    - [ ] `SOP_INDEX.md` (quick reference)
  - Timeline: May 25-28
  - Owner: You
  - Deliverable: Laminated guides ready for use

- [ ] **Conduct facilitator training walkthrough**
  - Status: Pending (facilitator TBD)
  - Duration: 1-2 hours
  - Content: Review entire `STUDY_SESSION_SOP.md` line-by-line
  - Timeline: May 28-30
  - Owner: You + facilitator
  - Deliverable: Facilitator sign-off on SOP understanding

- [ ] **Prepare physical materials for sessions**
  - Status: Pending
  - Items:
    - [ ] Print consent forms (×64 + 10 extras)
    - [ ] Print SUS questionnaires (×64 + 10 extras)
    - [ ] Prepare task answer sheets (blank paper/forms)
    - [ ] Prepare participant contact cards (email/phone)
    - [ ] Set up session logs directory (data/session_logs/)
  - Timeline: May 28-31
  - Owner: You
  - Deliverable: All materials in organized bins, ready for daily use

---

## 🟠 STUDY EXECUTION (June 1 - July 31)

### Phase 2: Run N=64 Educator Study (Sessions 1-30)

- [ ] **Session 1 kickoff (June 1)**
  - Status: Pending
  - Preparation checklist:
    - [ ] Participant P01 confirmed and arrival time confirmed
    - [ ] Audio recorder tested and ready
    - [ ] Screen recorder tested and ready
    - [ ] Frontend (localhost:5173) running
    - [ ] Backend (localhost:3001) running
    - [ ] Facilitator materials on desk
    - [ ] Consent form signed
    - [ ] Pre-study questionnaires ready
  - Timeline: June 1
  - Owner: You + facilitator
  - Deliverable: Session 1 complete, data logged

- [ ] **Execute 5 sessions per week (June-July)**
  - Status: Pending
  - Timeline: Week 1 (June 1-7), Week 2 (June 8-14), ... Week 8 (July 22-28)
  - Sessions per condition: 32 (16 per condition)
  - Daily workflow:
    1. [ ] Prepare participant (consent, briefing)
    2. [ ] Run 20-min session following STUDY_SESSION_FLOW_DIAGRAM
    3. [ ] Collect SUS + task answer sheet
    4. [ ] Backup audio/screen recording immediately
    5. [ ] Log session JSON to data/session_logs/
    6. [ ] Run post-session validation
  - Owner: You + facilitator
  - Deliverable: 30 complete sessions with all data logged

- [ ] **Validation gates (every 5 sessions)**
  - Status: Pending (script exists)
  - Gate 1: After sessions 1-5 (June 7)
    - [ ] Run: `python3 analyze_study_logs.py --pilot`
    - [ ] Check: `task_completion_rate ≥ 0.5` (GO) or < 0.5 (NO-GO)
    - [ ] If NO-GO: Debug and fix before continuing
    - [ ] Owner: You
  - Gate 2: After sessions 6-10 (June 14)
  - Gate 3: After sessions 11-15 (June 21)
  - Gate 4: After sessions 16-20 (June 28)
  - Gate 5: After sessions 21-25 (July 5)
  - Gate 6: After sessions 26-30 (July 12)
  - Timeline: Weekly checks on Sundays
  - Owner: You
  - Deliverable: Validation report per gate, GO/NO-GO decision

- [ ] **Measure primary outcomes during sessions**
  - Status: Pending (SOP specifies logging)
  - Metrics:
    - [ ] Task Accuracy: % misconceptions correctly identified
    - [ ] Time-to-Decision: Seconds from "ready" to first answer (SOP line XXX)
    - [ ] Trust Calibration: Self-report confidence (0-100%) vs. actual accuracy
    - [ ] KG Coverage Feedback: Pre-exploration KG coverage rating (Condition B)
  - Logging: Automatic via session JSON + manual annotations
  - Timeline: All 30 sessions
  - Owner: Facilitator (automatic via app) + You (manual entries)
  - Deliverable: Complete metrics dataset in data/session_logs/

- [ ] **Collect and backup think-aloud audio**
  - Status: Pending
  - Method: External USB mic recording all 20-min sessions
  - Backup protocol: 
    - [ ] Copy audio to data/recordings/ immediately after session
    - [ ] Tar + gzip to data/backups/weekly_backup_YYYYWW.tar.gz every Sunday
  - Timeline: All 30 sessions (June 1 - July 31)
  - Owner: Facilitator (record) + You (backup)
  - Deliverable: 30 audio files (~20 min each) + weekly backups

- [ ] **Handle recruitment dropouts**
  - Status: Pending (contingency)
  - If participant cancels:
    - [ ] Record in `data/participant_assignment.csv`
    - [ ] Contact replacement from waitlist
    - [ ] Ensure N≥30 completes (target N=64)
  - Timeline: As needed
  - Owner: You
  - Outcome: Minimum N=30, target N=64

---

## 🟡 DATA PROCESSING & ANALYSIS (August 1-20)

### Phase 3: Transcribe & Code Qualitative Data

- [ ] **Transcribe think-aloud audio**
  - Status: Pending
  - Volume: ~30 sessions × 20 min = ~600 minutes = ~10 hours of audio
  - Method: Manual transcription or automated (Otter.ai, Rev.com)
  - Timeline: August 1-10
  - Owner: You (or outsource to transcription service)
  - Cost estimate: $300-500 if outsourced
  - Deliverable: 30 transcripts in data/transcripts/

- [ ] **Develop qualitative coding scheme**
  - Status: Partially done (CA/SA/TC/II mentioned in SOP)
  - Refine:
    - [ ] Causal Attribution (CA) - explicit "because I saw in the KG"
    - [ ] Semantic Alignment (SA) - rubric refinement evidence
    - [ ] Trust Calibration (TC) - confidence in grades
    - [ ] Interaction Insight (II) - other insights from interaction
  - Add examples and boundary cases to codebook
  - Timeline: August 1-3
  - Owner: You
  - Deliverable: Codebook with definitions, examples, decision rules

- [ ] **Conduct Inter-Rater Reliability (IRR) pilot**
  - Status: Pending
  - Requirement: Cohen's κ ≥ 0.70 (from Paper 2)
  - Method:
    - [ ] Select 3-5 random transcripts (~20% sample)
    - [ ] Have two coders independently code
    - [ ] Calculate Cohen's κ
    - [ ] If κ < 0.70: Refine codebook and retry
    - [ ] If κ ≥ 0.70: Proceed to full coding
  - Timeline: August 4-7
  - Owner: You + second coder (could be advisor, colleague, or hired)
  - Deliverable: IRR pilot report with κ value

- [ ] **Perform full qualitative coding**
  - Status: Pending (after IRR approval)
  - Volume: 30 transcripts
  - Method: Two coders (or one with spot-check verification)
  - Code: CA, SA, TC, II frequencies per participant
  - Timeline: August 8-15
  - Owner: You + second coder
  - Deliverable: Coded dataset (CSV with frequencies per transcript)

- [ ] **Run statistical analyses**
  - Status: Pending
  - Tests:
    - [ ] Descriptive statistics (means, SDs, frequencies)
    - [ ] Task Accuracy: Mann-Whitney U test (Cond A vs B)
    - [ ] Time-to-Decision: Mann-Whitney U test
    - [ ] SUS Scores: Independent t-test
    - [ ] Qualitative coding frequencies: Chi-square or Fisher's exact
    - [ ] Semantic Alignment (pre-post): Paired t-test or Wilcoxon
    - [ ] Trust Calibration: Spearman ρ (confidence vs. accuracy)
    - [ ] Effect sizes: Cohen's d, r
  - Timeline: August 15-18
  - Owner: You (or statistics consultant)
  - Deliverable: Statistical results table (for Paper 2 Results section)

- [ ] **Create final figures from real data**
  - Status: Pending
  - Replace mock figures:
    - [ ] Figure 8: Real SUS scores (bar chart with means/SDs)
    - [ ] Figure 9: Real qualitative coding frequencies (CA/SA/TC/II)
    - [ ] Figure 10: Real semantic alignment pre/post
  - Timeline: August 18-19
  - Owner: You (Python + matplotlib or R)
  - Deliverable: Three PNG figures with real data

---

## 📝 REVISION & SUBMISSION (August 20+)

### Phase 4: Final Revision & Submission

- [ ] **Rewrite Paper 2 Results section**
  - Status: Pending
  - Replace mock results with real data
  - Structure:
    - [ ] Descriptive statistics (sample demographics, completion rates)
    - [ ] Primary outcomes (Task Accuracy, Time-to-Decision)
    - [ ] Secondary outcomes (SUS, qualitative themes)
    - [ ] Statistical tests and effect sizes
    - [ ] Trust calibration analysis
  - Timeline: August 19-21
  - Owner: You
  - Deliverable: Updated Results section with real data

- [ ] **Update Paper 2 Appendix A.4 (Study Metadata)**
  - Status: Pending
  - Include:
    - [ ] Participant demographics (age, experience, discipline)
    - [ ] Recruitment and retention rates
    - [ ] IRR pilot results (κ ≥ 0.70)
    - [ ] Descriptive statistics table
  - Timeline: August 21
  - Owner: You
  - Deliverable: Populated Appendix A.4

- [ ] **Incorporate all revisions into final PDFs**
  - Status: Pending
  - Recompile LaTeX:
    - [ ] Paper 1: Final check for consistency with Paper 2 empirical results
    - [ ] Paper 2: Recompile with new Figures 8-10 and Results section
  - Timeline: August 21-22
  - Owner: You
  - Deliverable: Final `ConceptGrade_FullPaper.pdf` and `paper_phase2_vis2027.pdf`

- [ ] **Submit Paper 1 to NLP/EdAI venue**
  - Status: Pending
  - Venue options: ACL, AIED, EMNLP, or similar
  - Submission checklist:
    - [ ] Choose venue (confirm deadline: usually Oct-Nov 2026)
    - [ ] Prepare author statement, abstract, keywords
    - [ ] Format according to venue guidelines
    - [ ] Submit via conference system
  - Timeline: August 23-25
  - Owner: You
  - Deliverable: Submission confirmation email

- [ ] **Submit Paper 2 to IEEE VIS 2027**
  - Status: Pending
  - Venue: IEEE VIS 2027 VAST track
  - Submission checklist:
    - [ ] Confirm deadline (usually July-August 2026, check vis.ieee.org)
    - [ ] Prepare supplementary materials (SOP, code, data)
    - [ ] Format according to IEEE VIS guidelines
    - [ ] Submit via IEEE Precision Conference system
  - Timeline: August 23-25
  - Owner: You
  - Deliverable: Submission confirmation email

---

## 🟢 OPTIONAL ENHANCEMENTS (Can Defer)

- [ ] **Run kg_weight sensitivity analysis verification**
  - Status: Script created but not run
  - Effort: 2-4 hours
  - Impact: Strengthens Paper 1 sensitivity claims
  - Timing: Can run post-submission if reviews request it
  - Owner: You
  - Deliverable: Sensitivity analysis verification report

- [ ] **Prepare response to reviewer feedback**
  - Status: Pending (after submission + review decision)
  - Timeline: 2-6 months after submission depending on venue
  - Owner: You

- [ ] **Prepare supplementary materials package**
  - Status: Pending (after Paper 2 acceptance)
  - Contents:
    - [ ] Full `STUDY_SESSION_SOP.md`
    - [ ] Code repository (GitHub link)
    - [ ] Data (anonymized participant responses)
    - [ ] Analysis scripts
  - Timing: Required before publication
  - Owner: You

---

## 📊 SUMMARY TABLE

| Phase | Timeline | Effort | Owner | Status |
|-------|----------|--------|-------|--------|
| Pre-Study Setup | May 8-31 | 30-40 hrs | You | 🔴 CRITICAL |
| Study Execution | June 1 - July 31 | 60-80 hrs | You + Facilitator | 🔴 CRITICAL |
| Data Processing | August 1-20 | 40-60 hrs | You + Coder | 🟠 MUST DO |
| Revision & Submit | August 21+ | 10-20 hrs | You | 🟠 MUST DO |
| Optional Enhancements | Anytime | 5-10 hrs | You | 🟢 OPTIONAL |

**Total Effort:** ~150-190 hours (3-4 months full-time equivalent)

---

## 📋 QUICK CHECKLIST

### This Week (May 7-13)
- [ ] Email papers to advisor
- [ ] Review advisor feedback
- [ ] Confirm June 1 start date
- [ ] Begin recruitment outreach

### Next 2 Weeks (May 14-28)
- [ ] Finalize 64 participants with signed consent
- [ ] Test all hardware
- [ ] Print & laminate materials
- [ ] Conduct facilitator training

### Study Month (June 1 - July 31)
- [ ] Run 30 sessions (1 per day)
- [ ] Weekly validation gates
- [ ] Backup data daily
- [ ] Monitor task_completion_rate ≥ 0.5

### Revision Month (August 1-25)
- [ ] Transcribe audio (10 hours)
- [ ] Code qualitative data (20 hours)
- [ ] Run statistical tests (10 hours)
- [ ] Rewrite Results + Figures (10 hours)
- [ ] Submit both papers (2 hours)

### Post-Submission (August 25+)
- [ ] Wait for reviewer feedback
- [ ] Prepare for optional revisions
- [ ] Begin next research direction

---

## 🎯 SUCCESS CRITERIA

- ✅ **Study Completion:** N ≥ 30 sessions completed (target N=64)
- ✅ **Data Quality:** task_completion_rate ≥ 0.5 at all validation gates
- ✅ **Coding Reliability:** Cohen's κ ≥ 0.70 in IRR pilot
- ✅ **Submission:** Both papers submitted by August 25, 2026
- ✅ **Acceptance:** Target 1 acceptance within 6 months of submission

---

**Last Updated:** May 7, 2026  
**Next Review:** May 15, 2026  
**Advisor Sign-Off:** _________________

