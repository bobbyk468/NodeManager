# ConceptGrade User Study: Session Operation Procedure (SOP)

**Document Version:** 1.0  
**Date Created:** 2026-05-06  
**Study:** IEEE VIS 2027 Paper 2 — Educator Validation  
**Target:** N=30 domain-expert educators (15 per condition)  
**Session Duration:** 20 minutes per participant  
**Study Status:** Ready for participant recruitment and data collection

---

## EXECUTIVE SUMMARY

This SOP provides a **strict, reproducible protocol** for running individual user study sessions with ConceptGrade. Each session produces:
- ✅ Think-aloud audio transcript
- ✅ Screen recording
- ✅ System Usability Scale (SUS) score
- ✅ Rubric editor final state (JSON)
- ✅ Interaction event log (timestamps, heatmap clicks, KG hovers, rubric edits)

**Gating Criterion:** After every 5 sessions, run validation. Target: task_completion_rate ≥ 0.5 (GO). If < 0.5 (NO-GO), debug and retry.

---

## PART 1: PREREQUISITES & SETUP

### 1.1 System Requirements

**Hardware:**
- MacBook Pro (M1 or later) with 8+ GB RAM
- External microphone (USB, for think-aloud clarity)
- Screen recording software (built-in macOS + ScreenFlow or OBS)
- Reliable WiFi connection

**Software (must be pre-installed):**
```bash
# Verify installations
node --version          # v18.0+
npm --version          # v9.0+
python3 --version      # v3.10+
git --version          # v2.40+

# Frontend dependencies installed
cd packages/frontend && npm list react  # Should show react@latest

# Backend dependencies installed
cd packages/backend && npm list express  # Should show express@latest

# Python environment active
python3 -m venv venv && source venv/bin/activate
pip list | grep anthropic  # Should show anthropic>=0.7
```

### 1.2 Pre-Study Checklist (Complete 1 week before first session)

- [ ] IRB approval letter on file (screenshot in project folder)
- [ ] Recruitment emails sent to CS departments (target: N=30)
- [ ] Participant consent form printed (2 copies per session)
- [ ] Audio recording device tested (mic levels, 16-bit PCM)
- [ ] Screen recording software tested (capture at 1080p, ~50 MB per 20 min)
- [ ] Database backup created (`cp -r data/study_sessions data/study_sessions_backup_<date>`)
- [ ] Study task question printed and ready (see Section 3.1)
- [ ] SUS questionnaire forms printed (15 copies, Condition A + B each)
- [ ] Rubric editor template screenshot saved (baseline for comparison)
- [ ] Participant ID scheme assigned (`C<cond>_P<seq>`: CA_P01, CA_P02, ..., CB_P15)

### 1.3 Randomization & Participant Assignment

**Randomization Method:** Block randomization (alternating conditions, n=15 per condition)

**Sequence (fixed, do not deviate):**
```
Session 1:  CA_P01 (Condition A)
Session 2:  CB_P01 (Condition B)
Session 3:  CA_P02 (Condition A)
Session 4:  CB_P02 (Condition B)
... (repeat pattern for sessions 5-30)
```

**Store in:** `data/participant_assignment.csv`
```
participant_id,condition,session_order,scheduled_date,status
CA_P01,A,1,2026-06-XX,pending
CB_P01,B,2,2026-06-XX,pending
...
```

---

## PART 2: SESSION STARTUP (5 minutes before session)

### 2.1 System State Verification

Run this exact checklist **5 minutes before** each session:

```bash
# Step 1: Clear old sessions (if restarting after a failed session)
rm -f data/session_logs/*.lock 2>/dev/null || true
rm -rf /tmp/conceptgrade_session_* 2>/dev/null || true

# Step 2: Check ports are free
lsof -ti:5173 | xargs kill -9 2>/dev/null || echo "✓ Port 5173 free"
lsof -ti:3001 | xargs kill -9 2>/dev/null || echo "✓ Port 3001 free"
sleep 2

# Step 3: Verify database connection
sqlite3 data/study_sessions.db "SELECT COUNT(*) FROM study_sessions;" 2>/dev/null || echo "⚠ DB check failed; will retry on startup"

# Step 4: Create session directory
PARTICIPANT_ID="<INSERT_PARTICIPANT_ID>"  # e.g., CA_P01
mkdir -p data/session_logs/$PARTICIPANT_ID
mkdir -p data/recordings/$PARTICIPANT_ID

echo "✓ Pre-session verification complete"
```

### 2.2 Condition Assignment Verification

**Before inviting participant into testing area:**

1. Check `data/participant_assignment.csv` for next session order
2. Confirm condition (A or B)
3. Load appropriate study materials:
   - **Condition A**: Print summary statistics sheet (Section 3.2a)
   - **Condition B**: Do NOT print anything; dashboard only

---

## PART 3: SESSION FLOW (20 minutes total)

### 3.1 Minutes 0-2: Briefing & Consent (~2 minutes)

**Facilitator Actions:**

1. **Greet and Consent (1 min)**
   ```
   "Thank you for participating in our study on visual analytics for grading.
    This session will take about 20 minutes. We'll record your voice and screen
    so we can analyze how you interact with the system. All data is confidential
    and will be identified only by a participant ID. Do you have any questions
    before we begin?"
   ```

2. **Obtain Consent (1 min)**
   - [ ] Participant signs consent form (2 copies: 1 for them, 1 for us)
   - [ ] Confirm audio recording: "I'm going to start recording your voice now. Please think aloud as you work—tell me what you're looking at, what you're thinking, and why you're making decisions. Is that OK?"
   - [ ] Start audio recorder
   - [ ] Start screen recording

3. **Start Timers**
   - System clock: note exact start time in session log
   - Kitchen timer: set for 20 minutes (will chime at 18 min to warn participant)

**Facilitator Notes:**
- Do NOT coach participant
- Do NOT answer questions about the system ("What does this button do?")
- If participant asks for help, respond: "You can explore the interface however you'd like. There's no right or wrong way to use it."

---

### 3.2a: Minutes 2-7: CONDITION A (Control) — Task Presentation

**Materials Printed:**
```
╔═══════════════════════════════════════════════════════════════╗
║           CONDITION A: SUMMARY STATISTICS ONLY                ║
║                                                               ║
║  Dataset: CS Data Structures (120 student answers)            ║
║                                                               ║
║  Overall Performance:                                         ║
║  • Mean Absolute Error (MAE): 0.223 (on 0-1 grade scale)     ║
║  • Wilcoxon p-value: 0.003 (highly significant improvement)  ║
║  • Improvement over baseline LLM: 32.4%                      ║
║                                                               ║
║  Per-SOLO-Level Performance:                                 ║
║  • Prestructural: MAE = 0.375                                ║
║  • Unistructural: MAE = 0.333                                ║
║  • Multistructural: MAE = 0.228 (39% better)                 ║
║  • Relational: MAE = 0.080 (70% better)                      ║
║  • Extended Abstract: MAE = 0.167                            ║
║                                                               ║
║  TASK QUESTION:                                              ║
║  "Looking at this grading data for the class, which concept   ║
║   do students struggle with most? Which students would you    ║
║   prioritize for office hours, and why?"                      ║
║                                                               ║
║  Answer on provided form (5-minute time limit)               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Facilitator Script:**

"I'm going to show you some data from a real CS course where we used an AI grading system. Here are the results: [hand participant the summary sheet]. Take a moment to read this, and then I have a question for you."

*(Participant reads for ~1-2 minutes)*

"Based on this data, I'd like you to answer this question, and you can write your answer here [point to form]. The question is: 'Looking at this grading data for the class, which concept do students struggle with most? Which students would you prioritize for office hours, and why?' You have about 5 minutes."

*(Start 5-minute timer)*

**Data Capture:**
- [ ] Audio recorder running (capture think-aloud)
- [ ] Note on form when participant finishes (note time: ___:__)
- [ ] Collect written answer sheet

---

### 3.2b: Minutes 2-7: CONDITION B (Treatment) — Dashboard Welcome

**Facilitator Script:**

"I'm going to show you an interactive dashboard for analyzing student grades and identifying misconceptions. The dashboard is designed to help instructors quickly spot which concepts students are struggling with and understand why. Here's the interface [launch dashboard at http://localhost:5173]. Take a moment to explore it however you'd like. There's no right or wrong way to use it."

**System Startup (Condition B):**

```bash
# In Terminal Window 1 (Frontend)
cd packages/frontend
npm run dev
# Wait for: "Local: http://localhost:5173"

# In Terminal Window 2 (Backend)
cd packages/backend
npm run start:api
# Wait for: "Server running on http://localhost:3001"

# In Terminal Window 3 (Start session logger)
python3 run_dashboard_session.py \
  --condition B \
  --participant $PARTICIPANT_ID \
  --output data/session_logs/$PARTICIPANT_ID/events.json
```

**Facilitator Monitoring (Condition B):**
- [ ] Dashboard loads at http://localhost:5173
- [ ] Participant can click on heatmap cells
- [ ] Radar chart responds to selections
- [ ] KG subgraph displays
- [ ] Reasoning trace panel shows without errors
- [ ] Audio/screen recording capturing interactions

*(Let participant explore for 2-3 minutes with no guidance)*

---

### 3.3: Minutes 7-17: Task Execution (~10 minutes)

**Both Conditions — Same Task Question:**

**Present Verbally:**

"Now I have the same question for you: 'Looking at the data for this class, which concept do students struggle with most? Which students would you prioritize for office hours, and why?' Please answer on this form [provide written form + pencil]."

*(Start 10-minute timer)*

**Condition A Specific Notes:**
- Participant has only the printed summary sheet
- No follow-up visuals or interactions
- Facilitate re-reading the sheet if needed

**Condition B Specific Notes:**
- Participant has full dashboard access
- Encourage exploration: "You can click on the heatmap, drag the radar, look at the knowledge graph—whatever helps you answer the question."
- Monitor interactions (note in real-time if participant clicks heatmap cells, hovers KG nodes, etc.)
- Do NOT offer suggestions or point out features

**Monitor & Log:**
- [ ] Participant is actively engaged (eyes on screen/sheet)
- [ ] Thinking aloud continuously (remind if silent: "Keep talking; tell me what you're thinking")
- [ ] Time remaining: announce at 5 min (T=12), 2 min (T=15)
- [ ] Collect answer form at T=17 (note time participant finishes)

**Log in session file:**
```json
{
  "participant_id": "CA_P01",
  "condition": "A",
  "task_start_time": "10:00:15",
  "task_end_time": "10:10:42",
  "task_duration_seconds": 627,
  "answer_content": "[participant's written response]",
  "dashboard_interactions": []  // Condition A: empty
}
```

---

### 3.4: Minutes 17-20: SUS & Rubric Editor (~3 minutes)

**Step 1: System Usability Scale (1 minute)**

Hand participant SUS questionnaire (10 Likert items):

```
Strongly   Somewhat   Neutral   Somewhat   Strongly
Disagree   Disagree             Agree      Agree
(1)        (2)        (3)       (4)        (5)

1. I think I would like to use this system frequently.        [ ]
2. I found the system unnecessarily complex.                  [ ]
3. I thought the system was easy to use.                      [ ]
4. I think I would need support to use this system.           [ ]
5. I found the various functions well integrated.             [ ]
6. I thought there was too much inconsistency in this system. [ ]
7. I would imagine most people would learn to use quickly.    [ ]
8. I found the system very cumbersome to use.                 [ ]
9. I felt very confident using the system.                    [ ]
10. I needed to learn a lot before using this system.         [ ]

Total Score (0-100): ________
Grade: A (80-100) / B (70-79) / C (60-69) / D (50-59) / F (<50)
```

**Data Capture:**
- [ ] Collect completed SUS form
- [ ] Calculate score: `(sum of scores - 10) × 2.5`
- [ ] Record in session log

**Step 2: Rubric Editor (Condition B only) (2 minutes)**

*Condition A: Skip this step. Proceed to closing.*

**For Condition B Participants:**

"Now, based on what you learned from the dashboard, I'd like you to refine the rubric for this assignment. Here's the rubric editor [open interface]. You can add criteria that you think students should be evaluated on. Take 2 minutes to make any changes you'd like."

*(Monitor and log all edits)*

**Log all rubric edits:**
```json
{
  "rubric_edits": [
    {
      "timestamp": "10:15:23",
      "action": "click_to_add",
      "kg_node": "quicksort",
      "edit_text": "Explains time complexity of quicksort",
      "source": "reasoning_step_5"
    },
    {
      "timestamp": "10:16:01",
      "action": "manual_edit",
      "criterion": "Identifies sorting networks",
      "added": true
    }
  ]
}
```

---

## PART 4: SESSION COMPLETION (1 minute)

### 4.1 Closing Script

```
"Thank you so much for your time. Your insights are really valuable for
improving how we present AI grading to educators. All your data will be
kept confidential. If you'd like to see the results of this study when
it's complete, here's our contact info [provide card]."
```

**Final Checklist:**
- [ ] Stop audio recorder (save as: `data/recordings/$PARTICIPANT_ID/audio.wav`)
- [ ] Stop screen recording (save as: `data/recordings/$PARTICIPANT_ID/screen.mp4`)
- [ ] Collect consent forms (file: `data/consent_forms/$PARTICIPANT_ID.pdf`)
- [ ] Export session JSON (run command below)
- [ ] Ask: "Is it OK if we contact you if we have follow-up questions?" (note answer)

### 4.2 Post-Session Data Export

```bash
# Run immediately after session ends
PARTICIPANT_ID="<INSERT_PARTICIPANT_ID>"
CONDITION="<A|B>"

python3 run_dashboard_session.py \
  --finalize \
  --participant $PARTICIPANT_ID \
  --condition $CONDITION \
  --output data/session_logs/$PARTICIPANT_ID/final.json

# Verify files created
ls -lh data/session_logs/$PARTICIPANT_ID/
# Should show: events.json, rubric_edits.json (if Condition B), final.json
```

### 4.3 Quick Validation Check

```bash
# After every session, run
python3 analyze_study_logs.py --participant $PARTICIPANT_ID --verbose

# Expected output:
# ✓ Session complete: CA_P01
# ✓ Audio file: 20 min 42 sec
# ✓ Task answer recorded
# ✓ SUS score: 72
# ✓ Condition B: 8 rubric edits logged
# ✓ Ready for transcription
```

---

## PART 5: VALIDATION GATES (Every 5 sessions)

### 5.1 Gate Criteria

**After completing sessions for 5 participants, run:**

```bash
python3 analyze_study_logs.py --csv --pilot --output results/gate_check_<date>.csv
```

**SUCCESS (GO):** task_completion_rate ≥ 0.5
```
Condition,Sessions,Completed,Task_Completion_Rate,Status
A,3,2,0.67,GO ✓
B,2,2,1.00,GO ✓
Overall,5,4,0.80,GO ✓
```

**FAILURE (NO-GO):** task_completion_rate < 0.5
```
Condition,Sessions,Completed,Task_Completion_Rate,Status
A,3,1,0.33,NO-GO ✗ (debug)
B,2,1,0.50,MARGINAL
Overall,5,2,0.40,NO-GO ✗ (debug)
```

### 5.2 If NO-GO: Debugging Steps

**Issue 1: Missing audio files**
- [ ] Check microphone is connected and enabled
- [ ] Re-run `System Preferences → Sound → Input`, select correct device
- [ ] Test: `ffmpeg -i data/recordings/<participant>/audio.wav -f null -` (should show no errors)

**Issue 2: Task answer not recorded**
- [ ] Verify SUS form was collected
- [ ] Check that facilitator wrote down written response
- [ ] Confirm data entry in session log JSON

**Issue 3: Dashboard timeouts (Condition B)**
- [ ] Check backend logs: `tail -20 packages/backend/logs/server.log`
- [ ] Restart backend: `npm run start:api`
- [ ] Verify database is not full: `du -sh data/study_sessions.db`

**Issue 4: Interaction logging missing (Condition B)**
- [ ] Check that event logger started: `ps aux | grep run_dashboard_session`
- [ ] Verify `events.json` exists: `ls -lh data/session_logs/<participant>/events.json`
- [ ] If missing, manually tag in final.json: `"logging_issue": "true"` for reviewer notes

### 5.3 If GO: Continue to Next Batch

Once you hit 5 consecutive GO gates, you have validated the protocol. Continue with remaining participants (N=25 remaining). Repeat gates every 10 sessions.

---

## PART 6: DAILY OPERATIONS CHECKLIST

### Morning (Before first session)

```bash
# Update participant schedule
cat data/participant_assignment.csv | grep "status,pending" | head -4

# Backup previous session data
tar -czf data/backups/session_logs_$(date +%Y%m%d_%H%M).tar.gz data/session_logs/

# Verify systems are ready
npm --version && python3 --version && git --version
echo "✓ All systems ready"
```

### After Each Session

```bash
PARTICIPANT_ID="<ID from assignment sheet>"

# Rename files with participant ID
mv /tmp/audio_recording.wav data/recordings/$PARTICIPANT_ID/audio.wav
mv /tmp/screen_recording.mp4 data/recordings/$PARTICIPANT_ID/screen.mp4

# Validate session
python3 analyze_study_logs.py --participant $PARTICIPANT_ID --verbose

# Update assignment sheet
# Change status from "pending" to "complete" for this participant
# Record completion time and any notes
```

### End of Day (After all sessions)

```bash
# Generate daily summary
python3 analyze_study_logs.py --daily-report --date $(date +%Y-%m-%d) \
  > results/daily_report_$(date +%Y%m%d).txt

# Example output:
# ========================================
# Daily Report: 2026-06-15
# ========================================
# Sessions Completed: 3
# Condition A: 2 (CA_P01, CA_P02)
# Condition B: 1 (CB_P01)
# All sessions: GO ✓
# 
# Action items:
# - None; all gates passing

# Backup all session data
tar -czf data/backups/daily_$(date +%Y%m%d_%H%M).tar.gz data/session_logs/ data/recordings/
```

### Weekly (Every Friday)

```bash
# Run comprehensive validation
python3 analyze_study_logs.py --csv --report --output results/weekly_report_$(date +%Y_week%V).csv

# Email summary to PI:
# - Sessions completed this week (X/30 total)
# - GO/NO-GO status
# - Any issues encountered
# - Timeline to completion

# Example: "As of Friday 2026-06-21: 12/30 sessions complete (40%), all gates passing"
```

---

## PART 7: TROUBLESHOOTING QUICK REFERENCE

### Dashboard Won't Load

```bash
# Check if frontend is running
curl -s http://localhost:5173/ | head -5

# If fails:
lsof -ti:5173 | xargs kill -9
cd packages/frontend && npm run dev

# Check browser console (Cmd+Option+J)
# Common errors: CORS, missing .env, port conflict
```

### Audio Recording Silent

```bash
# Test microphone
ffmpeg -f avfoundation -i :0 -t 5 /tmp/mic_test.wav
ffplay /tmp/mic_test.wav  # Should hear audio

# If silent:
System Preferences → Sound → Input
Select external microphone
Re-test above
```

### Session Crashes Mid-Run

```bash
# Kill lingering processes
pkill -f "npm run dev"
pkill -f "npm run start:api"
pkill -f "python3 run_dashboard_session"

# Wait 5 seconds
sleep 5

# Restart (see Section 4.2)
# Note in session log: "System restart at [time], session resumed"
```

### Database Lock (Condition B interaction logging fails)

```bash
# Check for locks
lsof | grep "study_sessions.db"

# If locked, close and remove lock
rm -f data/study_sessions.db.lock

# Verify database integrity
sqlite3 data/study_sessions.db "PRAGMA integrity_check;"
# Should output: ok
```

### Participant Didn't Answer Task Question

```
⚠ CRITICAL: This invalidates the session (task_completion_rate = 0)

Options:
1. Offer to re-run the task: "Let's try again. You have 10 minutes..."
2. Or mark as NO-GO and investigate why

Document in session log:
{
  "task_skipped": true,
  "reason": "participant_refused | ran_out_of_time | facilitator_error",
  "recovery_action": "none | re-run | excluded_from_analysis"
}
```

---

## PART 8: PARTICIPANT QUICK-START CARDS

Print and give to each participant (optional; helps them feel prepared):

```
╔═════════════════════════════════════════════════════════════╗
║         ConceptGrade Study — Participant Overview           ║
╚═════════════════════════════════════════════════════════════╝

Thank you for participating in our research!

WHAT: You'll use a visual analytics tool and answer questions
      about grading student work.

WHEN: 20 minutes total

WHAT WE'LL RECORD:
  • Your voice (think-aloud commentary)
  • Your screen (what you interact with)
  • Your written answers
  • Your ratings on a usability survey

WHY: We're studying whether visual tools help educators
     make better grading decisions.

CONFIDENTIALITY:
  Your responses are identified only by a participant ID.
  Your name won't appear in any reports or publications.

QUESTIONS? Ask the facilitator anytime.

Let's get started!
```

---

## PART 9: SESSION LOG TEMPLATE (JSON)

Each session auto-generates a JSON file. Example:

```json
{
  "session_metadata": {
    "participant_id": "CA_P01",
    "condition": "A",
    "session_date": "2026-06-15",
    "session_time_start": "10:00:15",
    "session_time_end": "10:20:58",
    "session_duration_seconds": 1243,
    "facilitator_name": "Alice",
    "version": "1.0"
  },
  "consent": {
    "consent_form_signed": true,
    "audio_recording_approved": true,
    "screen_recording_approved": true,
    "future_contact_ok": true,
    "future_contact_email": "participant@university.edu"
  },
  "task_response": {
    "task_question": "Which concept do students struggle with most? Which students prioritize for office hours?",
    "response_text": "Based on the data shown, students seem to struggle with time complexity analysis. I would prioritize students whose answers show gaps in understanding Big-O notation, particularly in the relational-level SOLO category where the error rate is highest.",
    "response_time_seconds": 627,
    "response_complete": true
  },
  "sus_score": {
    "raw_scores": [4, 1, 4, 1, 5, 2, 4, 1, 5, 2],
    "total_raw": 29,
    "sus_score": 72.5,
    "grade": "B",
    "interpretation": "Good usability"
  },
  "condition_a_only": {
    "summary_sheet_provided": true,
    "dashboard_access": false,
    "interactions": []
  },
  "condition_b_only": {
    "dashboard_access": true,
    "rubric_edits": [
      {
        "timestamp": "10:15:23",
        "action": "click_to_add",
        "kg_node_id": "quicksort",
        "kg_node_label": "quicksort",
        "edit_text": "Student must explain time complexity of quicksort",
        "source_reasoning_step": 5
      }
    ],
    "dashboard_interactions": {
      "heatmap_clicks": 3,
      "radar_drags": 2,
      "kg_hovers": 7,
      "trace_steps_examined": 12
    }
  },
  "audio_files": {
    "path": "data/recordings/CA_P01/audio.wav",
    "duration_seconds": 1243,
    "format": "WAV 16-bit PCM 44.1kHz",
    "transcription_status": "pending"
  },
  "screen_files": {
    "path": "data/recordings/CA_P01/screen.mp4",
    "duration_seconds": 1243,
    "resolution": "1080p",
    "framerate": 30,
    "file_size_mb": 47.2
  },
  "validation": {
    "task_completed": true,
    "audio_recorded": true,
    "screen_recorded": true,
    "sus_collected": true,
    "task_completion_rate": 1.0,
    "status": "GO"
  },
  "notes": {
    "facilitator_notes": "Participant was engaged throughout. Asked clarifying questions about the task but did not ask for help with the system.",
    "issues_encountered": "none",
    "recovery_actions": "none"
  }
}
```

---

## PART 10: TARGET TIMELINE & MILESTONES

**Target: Complete N=30 by end of July 2026**

| Week | Target Sessions | Cumulative | Gate Status | Action |
|------|-----------------|-----------|------------|--------|
| Week 1 (Jun 1-7) | 5 | 5 | Gate 1: GO/NO-GO | Debug if NO-GO |
| Week 2 (Jun 8-14) | 5 | 10 | Continue | Monitor |
| Week 3 (Jun 15-21) | 5 | 15 | Gate 2: Check | Assess recruitment |
| Week 4 (Jun 22-28) | 5 | 20 | Continue | Ramp up recruiting if needed |
| Week 5 (Jun 29-Jul 5) | 5 | 25 | Gate 3: Final | Wrap up recruiting |
| Week 6 (Jul 6-12) | 5 | 30 | COMPLETE | Begin data analysis |

**July 13-20:** Transcribe think-aloud + code qualitative data (CA/SA/TC/II)  
**July 21-27:** Statistical analysis, generate real Figures 8-10  
**July 28-31:** Final PDF revision, submit to IEEE VIS 2027

---

## PART 11: EMERGENCY CONTACTS & ESCALATION

**If session fails catastrophically:**

1. **System crash:** Restart backend/frontend (Section 7)
2. **Participant discomfort:** Pause, ask if they want to continue or reschedule
3. **Data loss:** Restore from backup: `tar -xzf data/backups/daily_*.tar.gz`
4. **Unable to debug:** Contact PI: [insert email]

---

## SIGN-OFF

**Prepared By:** Claude (Anthropic), on behalf of [Your Name, PI]  
**Date:** 2026-05-06  
**Approval:** [PI signature / email approval]

**Facilitator Acknowledgement:**

I have read and understand this SOP. I will follow it exactly for all participant sessions.

Name (print): ___________________  
Signature: ___________________  
Date: ___________________

---

**END OF SOP**

**To use this SOP:**
1. Print this document
2. Read carefully before first session
3. Keep a checklist printout during each session
4. Reference troubleshooting section (Part 7) if issues arise
5. Complete daily and weekly checklists (Part 6)

**Questions? Review the relevant section or contact the PI.**
