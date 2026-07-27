# ConceptGrade Study — Facilitator Quick Reference

**Print this card. Keep it during sessions. Laminate for durability.**

---

## BEFORE SESSION (5 min before)

```bash
# Clear old sessions
rm -f data/session_logs/*.lock 2>/dev/null || true
rm -rf /tmp/conceptgrade_session_* 2>/dev/null || true

# Free ports
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
sleep 2

# Check DB
sqlite3 data/study_sessions.db "SELECT COUNT(*) FROM study_sessions;" || echo "⚠ DB check failed"

# Create session dir
PARTICIPANT_ID="<FILL_IN>"  # e.g., CA_P01
mkdir -p data/session_logs/$PARTICIPANT_ID
mkdir -p data/recordings/$PARTICIPANT_ID

echo "✓ Pre-session ready"
```

---

## START SESSION (T=0 min)

### Checklist:
- [ ] Consent form signed (2 copies)
- [ ] Audio recorder START
- [ ] Screen recorder START
- [ ] Kitchen timer START (20 min)

### Script:
```
"Thank you for participating. We'll record your voice and
screen. Please think aloud as you work. Ready? Starting now."
```

---

## CONDITION A (Minutes 2-7) — TEXT SUMMARY

```bash
# Print summary sheet (Section 3.2a of SOP)
# Hand to participant
# Say: "Read this, then answer the question below."

# Set 5-min timer after they read
# Collect answer form
```

---

## CONDITION B (Minutes 2-7) — DASHBOARD WELCOME

```bash
# Terminal 1 (Frontend)
cd packages/frontend && npm run dev
# Wait for: "Local: http://localhost:5173"

# Terminal 2 (Backend)
cd packages/backend && npm run start:api
# Wait for: "Server running on :3001"

# Terminal 3 (Logger)
python3 run_dashboard_session.py \
  --condition B \
  --participant $PARTICIPANT_ID \
  --output data/session_logs/$PARTICIPANT_ID/events.json
```

### Script:
```
"Here's the dashboard. Explore however you'd like.
No right or wrong way to use it. Go ahead."
```

---

## TASK EXECUTION (Minutes 7-17) — BOTH CONDITIONS

### Script:
```
"Now I have a question for you: Which concept do students
struggle with most? Which students would you prioritize for
office hours, and why? You have 10 minutes. Start whenever
ready."
```

### Timers:
- **T=12 min (5 min remaining):** "You have 5 minutes left."
- **T=15 min (2 min remaining):** "2 minutes left. Wrap up your answer."
- **T=17 min:** "Time's up. Let me collect your form."

---

## SUS QUESTIONNAIRE (Minutes 17-18)

```bash
# Hand SUS form to participant
# Say: "Rate your experience on these 10 items, 1-5."
# Collect after ~1 minute
```

---

## RUBRIC EDITOR (Minutes 18-20) — CONDITION B ONLY

```bash
# Condition B: Show Rubric Editor interface
# Say: "You can add criteria you think students should be graded on.
#       Take 2 minutes to make any changes."

# Condition A: SKIP. Say "Thank you, you're done!"
```

---

## SESSION END (T=20 min)

### Checklist:
- [ ] Stop audio recorder (save to: `data/recordings/$PARTICIPANT_ID/audio.wav`)
- [ ] Stop screen recorder (save to: `data/recordings/$PARTICIPANT_ID/screen.mp4`)
- [ ] Collect consent forms
- [ ] Collect SUS form
- [ ] Collect task answer sheet

### Script:
```
"Thank you! Your insights are really valuable. All data is
confidential. If you'd like results when we're done, here's
our contact info [card]."
```

---

## POST-SESSION EXPORT (Immediately after)

```bash
PARTICIPANT_ID="<FILL_IN>"
CONDITION="<A|B>"

python3 run_dashboard_session.py \
  --finalize \
  --participant $PARTICIPANT_ID \
  --condition $CONDITION \
  --output data/session_logs/$PARTICIPANT_ID/final.json

# Verify
python3 analyze_study_logs.py --participant $PARTICIPANT_ID --verbose
```

---

## VALIDATION GATE (After every 5 sessions)

```bash
python3 analyze_study_logs.py --csv --pilot --output results/gate_check_$(date +%Y%m%d).csv

# If task_completion_rate >= 0.5: GO ✓
# If task_completion_rate < 0.5: NO-GO ✗ Debug!
```

---

## EMERGENCY TROUBLESHOOTING

### Audio Silent?
```bash
System Preferences → Sound → Input → Select external mic
ffmpeg -f avfoundation -i :0 -t 5 /tmp/test.wav
ffplay /tmp/test.wav  # Hear audio?
```

### Dashboard Won't Load?
```bash
curl http://localhost:5173/  # Should see HTML
lsof -ti:5173 | xargs kill -9
cd packages/frontend && npm run dev
```

### Database Locked?
```bash
rm -f data/study_sessions.db.lock
sqlite3 data/study_sessions.db "PRAGMA integrity_check;"  # Should say "ok"
```

### Session Crashed?
```bash
pkill -f "npm run dev"
pkill -f "npm run start:api"
pkill -f "python3 run_dashboard_session"
sleep 5
# Restart (see above)
# Note in log: "System restart at [time]"
```

---

## DAILY CHECKLIST

### Morning:
```bash
tar -czf data/backups/session_logs_$(date +%Y%m%d_%H%M).tar.gz data/session_logs/
npm --version && python3 --version && git --version
echo "✓ Ready"
```

### End of Day:
```bash
python3 analyze_study_logs.py --daily-report --date $(date +%Y-%m-%d) \
  > results/daily_report_$(date +%Y%m%d).txt
tar -czf data/backups/daily_$(date +%Y%m%d_%H%M).tar.gz data/session_logs/ data/recordings/
```

### End of Week:
```bash
python3 analyze_study_logs.py --csv --report --output results/weekly_report_week$(date +%V).csv
# Email summary to PI
```

---

## PARTICIPANT ASSIGNMENT SEQUENCE

```
Session 1:  CA_P01 (Condition A)
Session 2:  CB_P01 (Condition B)
Session 3:  CA_P02 (Condition A)
Session 4:  CB_P02 (Condition B)
...
Session 29: CA_P15 (Condition A)
Session 30: CB_P15 (Condition B)
```

Update `data/participant_assignment.csv` after each session:
```
participant_id,condition,session_order,scheduled_date,status
CA_P01,A,1,2026-06-15,COMPLETE
CB_P01,B,2,2026-06-16,COMPLETE
CA_P02,A,3,2026-06-17,PENDING
...
```

---

## KEY CONTACT INFO

**PI:** [Name, email, phone]  
**IRB Contact:** [IRB coordinator, phone, email]  
**Technical Support:** [Backend contact or debugging resource]

---

## TIMELINE TARGET

- **Week 1-2:** Sessions 1-5 (Gate 1 check)
- **Week 3-4:** Sessions 6-15 (halfway)
- **Week 5-6:** Sessions 16-30 (complete by end of July)
- **Week 7-8:** Data analysis + figure generation

---

**PRINT & LAMINATE THIS CARD**

Keep it visible during all sessions.

Last Updated: 2026-05-06
