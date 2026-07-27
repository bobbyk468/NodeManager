# ConceptGrade User Study SOP — Master Index

**Study:** IEEE VIS 2027 Paper 2 — Educator Validation of Co-Auditing Interface  
**Target:** N=30 domain-expert educators (15 per condition, 20-min sessions)  
**Timeline:** June 1 — July 31, 2026  
**Documents Created:** May 6, 2026

---

## 📚 SOP DOCUMENTS (Print These)

### 1. **STUDY_SESSION_SOP.md** (MAIN DOCUMENT)
**Purpose:** Complete operational procedure for running user study sessions  
**Length:** ~40 pages (comprehensive)  
**What to do with it:**
- [ ] Read completely before recruiting first participant
- [ ] Laminate and keep in testing room
- [ ] Reference during sessions for detailed guidance
- [ ] Use Part 7 (Troubleshooting) as emergency guide

**Key sections:**
- Part 1: Prerequisites & setup
- Part 2: Session startup
- Part 3: Session flow (20 minutes)
- Part 4: Session completion & data export
- Part 5: Validation gates (every 5 sessions)
- Part 6: Daily operations
- Part 7: Troubleshooting
- Part 8: Participant cards (print for them)
- Part 9: JSON session log template
- Part 10: Timeline & milestones

---

### 2. **FACILITATOR_COMMAND_CARD.md** (QUICK REFERENCE)
**Purpose:** One-page laminated command card for quick access  
**Length:** ~2 pages (condensed)  
**What to do with it:**
- [ ] Print and laminate
- [ ] Keep on desk during every session
- [ ] Reference for bash commands and scripts
- [ ] Use timings & checklists during session

**Contains:**
- Pre-session startup commands
- Condition A & B scripts
- Task execution timings
- Post-session export
- Emergency troubleshooting
- Daily checklist

---

### 3. **STUDY_SESSION_FLOW_DIAGRAM.txt** (VISUAL OVERVIEW)
**Purpose:** ASCII diagram showing complete session flow  
**Length:** 1 page  
**What to do with it:**
- [ ] Print and POST on wall (above desk)
- [ ] Reference when confused about which step you're on
- [ ] Show to participants to help them understand flow
- [ ] Use for quick-reference timings

**Contains:**
- Visual flow from start to finish
- Condition A vs B branches
- Time milestones
- Validation checkpoints
- Quick reference tables

---

### 4. **data/participant_assignment.csv** (TRACKING SHEET)
**Purpose:** Master list of all 30 participants with randomization  
**What to do with it:**
- [ ] Print at beginning of study
- [ ] Update after each session (mark status as COMPLETE)
- [ ] Track email sent, consent obtained, session completed
- [ ] Reference before each session to find next participant

**Randomization:** Block randomization, alternating conditions
- Sessions 1,3,5,...,29: Condition A (CA_P01 through CA_P15)
- Sessions 2,4,6,...,30: Condition B (CB_P01 through CB_P15)

---

## 🚀 HOW TO USE THESE DOCUMENTS

### Scenario 1: "I'm about to run my first session"
1. Read **STUDY_SESSION_SOP.md** completely (full 40 pages)
2. Print and laminate **FACILITATOR_COMMAND_CARD.md**
3. Print and post **STUDY_SESSION_FLOW_DIAGRAM.txt**
4. Print consent forms & task materials (see SOP Part 3)
5. Reference Quick Reference Card during session

### Scenario 2: "I'm in the middle of a session and something's wrong"
1. Check **FACILITATOR_COMMAND_CARD.md** Part 7 (Troubleshooting)
2. If not there, check **STUDY_SESSION_SOP.md** Part 7
3. Execute bash commands from the card
4. Document issue in session notes

### Scenario 3: "I'm about to start session #6 (validation gate)"
1. Check **FACILITATOR_COMMAND_CARD.md** end-of-day section
2. Run: `python3 analyze_study_logs.py --csv --pilot`
3. Check if task_completion_rate >= 0.5 (GO) or < 0.5 (NO-GO)
4. If NO-GO, see **STUDY_SESSION_SOP.md** Part 5.2 (Debugging)

### Scenario 4: "How do I update the participant tracking sheet?"
1. Open **data/participant_assignment.csv** in spreadsheet app
2. Find today's participant (check session_order)
3. Update columns: email_contacted, consent_obtained, session_completed
4. Change status: PENDING → COMPLETE
5. Add any notes

### Scenario 5: "I need to find the exact bash commands"
1. Check **FACILITATOR_COMMAND_CARD.md** (condensed)
2. For detailed explanation, see **STUDY_SESSION_SOP.md** relevant section

---

## 📋 BEFORE YOU START: CHECKLIST

One week before recruiting first participant:

### Documents:
- [ ] STUDY_SESSION_SOP.md read completely
- [ ] FACILITATOR_COMMAND_CARD.md printed & laminated
- [ ] STUDY_SESSION_FLOW_DIAGRAM.txt printed & posted
- [ ] participant_assignment.csv filled in with dates

### System Setup:
- [ ] Node.js v18+, npm v9+, Python 3.10+ installed
- [ ] Frontend dependencies: `cd packages/frontend && npm install`
- [ ] Backend dependencies: `cd packages/backend && npm install`
- [ ] Python venv created: `python3 -m venv venv && source venv/bin/activate`
- [ ] Database initialized: `sqlite3 data/study_sessions.db` ✓

### Hardware & Software:
- [ ] External microphone tested (16-bit PCM, 44.1kHz)
- [ ] Screen recording software tested (1080p, ~50 MB per 20 min)
- [ ] WiFi connection stable
- [ ] Backup system working: `tar -czf data/backups/...`

### IRB & Legal:
- [ ] IRB approval letter on file (screenshot in folder)
- [ ] Consent forms printed (2 copies × 30 = 60 forms)
- [ ] Study task question printed
- [ ] SUS questionnaires printed (30 forms)
- [ ] Participant info cards printed (30 cards)

### Recruitment:
- [ ] Recruitment emails sent to CS departments
- [ ] Signed commitment from department heads
- [ ] Backup recruitment channels identified (online CS communities, professional societies)

### Training:
- [ ] Facilitator (you) has read full SOP
- [ ] Backup facilitator (if applicable) has read full SOP
- [ ] Practice run with a volunteer (not counted as participant)

---

## 📊 DIRECTORY STRUCTURE

```
concept-aware/
├── STUDY_SESSION_SOP.md                 ← MAIN DOCUMENT (40 pages)
├── FACILITATOR_COMMAND_CARD.md          ← QUICK REFERENCE (laminated)
├── STUDY_SESSION_FLOW_DIAGRAM.txt       ← VISUAL FLOW (posted)
├── SOP_INDEX.md                         ← THIS FILE
│
├── data/
│   ├── participant_assignment.csv       ← TRACKING SHEET
│   ├── study_sessions.db               ← AUTO-GENERATED (SQLite DB)
│   ├── session_logs/                   ← AUTO-GENERATED (per session)
│   │   ├── CA_P01/
│   │   │   ├── final.json
│   │   │   ├── events.json
│   │   │   └── rubric_edits.json (if Condition B)
│   │   └── ...
│   └── backups/                         ← AUTO-GENERATED (daily backup)
│       └── session_logs_YYYYMMDD_HHMM.tar.gz
│
├── data/recordings/                     ← AUTO-GENERATED (audio & video)
│   ├── CA_P01/
│   │   ├── audio.wav
│   │   └── screen.mp4
│   └── ...
│
├── data/consent_forms/                  ← SAVE SCANNED/PHOTOS HERE
│   ├── CA_P01.pdf
│   └── ...
│
└── results/
    ├── gate_check_YYYYMMDD.csv         ← VALIDATION GATE RESULTS
    ├── daily_report_YYYYMMDD.txt       ← END-OF-DAY SUMMARY
    └── weekly_report_weekNN.csv        ← END-OF-WEEK SUMMARY
```

---

## 🎯 EXECUTION COMMANDS

### Start of Study
```bash
# First time setup
cd packages/frontend && npm install
cd ../backend && npm install
cd ../.. && python3 -m venv venv && source venv/bin/activate

# Backup before starting
tar -czf data/backups/baseline_$(date +%Y%m%d).tar.gz data/ results/
```

### Before Each Session
```bash
# Pre-session verification (Section 2.1 of SOP)
rm -f data/session_logs/*.lock 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
sleep 2
sqlite3 data/study_sessions.db "SELECT COUNT(*) FROM study_sessions;" || echo "⚠ DB check failed"
PARTICIPANT_ID="<INSERT_PARTICIPANT_ID>"  # e.g., CA_P01
mkdir -p data/session_logs/$PARTICIPANT_ID data/recordings/$PARTICIPANT_ID
echo "✓ Pre-session verification complete"
```

### During Session (Condition B)
```bash
# Terminal 1: Frontend
cd packages/frontend && npm run dev

# Terminal 2: Backend
cd packages/backend && npm run start:api

# Terminal 3: Event logger
python3 run_dashboard_session.py \
  --condition B \
  --participant $PARTICIPANT_ID \
  --output data/session_logs/$PARTICIPANT_ID/events.json
```

### After Each Session
```bash
# Post-session export
python3 run_dashboard_session.py \
  --finalize \
  --participant $PARTICIPANT_ID \
  --condition <A|B> \
  --output data/session_logs/$PARTICIPANT_ID/final.json

# Validate
python3 analyze_study_logs.py --participant $PARTICIPANT_ID --verbose
```

### Validation Gates (Every 5 Sessions)
```bash
# Check gate status
python3 analyze_study_logs.py --csv --pilot --output results/gate_check_$(date +%Y%m%d).csv

# Expected: task_completion_rate >= 0.5 (GO)
```

### Daily & Weekly Reports
```bash
# End of day
python3 analyze_study_logs.py --daily-report --date $(date +%Y-%m-%d) \
  > results/daily_report_$(date +%Y%m%d).txt

# End of week (Friday)
python3 analyze_study_logs.py --csv --report --output results/weekly_report_$(date +%Y_week%V).csv
```

---

## 💡 TIPS FOR SUCCESS

1. **Randomization Matters**: Alternate conditions (A, B, A, B, ...). Don't skip or swap.
2. **Timing is Strict**: Use kitchen timer. Session should be ~20 min. Announce time prompts at 5-min and 2-min marks.
3. **Audio Quality**: Use external USB microphone. Test before first session.
4. **Think-Aloud Instructions**: Be explicit: "Tell me what you're thinking, what you're looking at, why you're clicking things."
5. **Don't Coach**: If participant asks "What does this button do?", say "Explore it however you'd like."
6. **Backup Everything**: Run daily backup. Upload to cloud if possible.
7. **Validation Gates**: Don't skip. If NO-GO, debug before continuing.
8. **Documentation**: Update tracking sheet immediately after each session.

---

## 📞 ESCALATION CONTACTS

If something goes wrong and the SOP doesn't cover it:

**Technical Issues:** [Engineering contact]  
**Recruitment Problems:** [Recruitment coordinator]  
**Data Loss / Emergency:** [PI name, email, phone]  
**IRB Questions:** [IRB coordinator, contact info]

---

## 📈 PROGRESS TRACKING

Print this table and fill in as you go:

```
Week    Target   Cumulative   Gate Status      Notes
─────   ──────   ──────────   ────────────────────────────────────
Week 1  5        5            Gate 1: GO/NO-GO  [date]
Week 2  5        10           Continue          [date]
Week 3  5        15           Gate 2: Check     [date]
Week 4  5        20           Continue          [date]
Week 5  5        25           Gate 3: Final     [date]
Week 6  5        30           COMPLETE ✓        [date]
```

---

## ✅ FINAL CHECKLIST FOR COMPLETION

When all N=30 sessions are complete:

- [ ] All 30 participant records in participant_assignment.csv marked COMPLETE
- [ ] All 30 consent forms scanned & filed in data/consent_forms/
- [ ] All 30 audio files recorded & stored in data/recordings/
- [ ] All 30 screen recordings stored in data/recordings/
- [ ] All 30 session JSONs exported to data/session_logs/
- [ ] All validation gates passed (task_completion_rate >= 0.5)
- [ ] Weekly reports generated (6 weeks × 1 report = 6 files)
- [ ] Daily backups completed (30+ backup files)
- [ ] Ready for qualitative analysis (transcription + coding)

---

## 🎉 WHAT'S NEXT AFTER USER STUDY

Once all 30 sessions complete (targeting July 31):

1. **Weeks 1-2 (Aug 1-14):** Transcribe think-aloud audio (6-10 hours per 15 participants)
2. **Weeks 2-3 (Aug 14-28):** Code qualitative data (CA, SA, TC, II schemes)
3. **Weeks 3-4 (Aug 28-Sept 4):** Statistical analysis (Mann-Whitney U, Spearman ρ, effect sizes)
4. **Week 4 (Sept 4-11):** Generate real Figures 8, 9, 10 with actual data
5. **Week 5 (Sept 11-18):** Update paper with results, finalize PDF
6. **Week 6 (Sept 18-25):** Peer review & final edits
7. **Week 7+ (Sept 25+):** Submit to IEEE VIS 2027

---

## 📝 DOCUMENT HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-06 | Initial SOP creation |
| | | - STUDY_SESSION_SOP.md (40 pages) |
| | | - FACILITATOR_COMMAND_CARD.md (2 pages) |
| | | - STUDY_SESSION_FLOW_DIAGRAM.txt (1 page) |
| | | - participant_assignment.csv (30 rows) |
| | | - SOP_INDEX.md (this document) |

---

## 📚 RELATED DOCUMENTS (For Context)

These explain the research motivation and background:

- **PAPER2_FINAL_SUMMARY.md** — Paper 2 status (85% complete, 37 pages)
- **FINAL_STATUS.md** — Paper 2 rescue mission summary
- **EXECUTION_CHECKLIST.md** — Original 4-phase checklist (superseded by this SOP)

---

## 🚀 YOU'RE READY TO START

You now have:
✅ Complete SOP (40 pages)
✅ Quick reference card (laminated)
✅ Visual flow diagram (posted)
✅ Participant tracking sheet (ready to fill)
✅ All bash commands documented
✅ Troubleshooting guide
✅ Validation checkpoints every 5 sessions

**Next action:** Recruit your first participant and schedule Session 1.

Good luck! 🎓

---

**For questions or updates, see STUDY_SESSION_SOP.md**  
**Last Updated: 2026-05-06**
