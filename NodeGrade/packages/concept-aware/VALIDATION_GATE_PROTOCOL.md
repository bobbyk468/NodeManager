# Validation Gate Protocol

**Effective Date:** June 1, 2026  
**Last Updated:** May 30, 2026  
**Purpose:** Pre-commitment GO/NO-GO decision criteria for study continuation  
**Version:** 1.0

---

## Overview

Every 5 completed sessions, a **single latency-based metric** is computed to determine whether the system and protocol are functioning as intended. This gate is determined **before** analyzing answer quality or study outcomes to prevent researcher bias and ensure scientific integrity.

This protocol is **pre-registered** and committed to before study execution. No hidden stopping rules apply. Only the latency-based gate metric determines continuation.

---

## Definition: Task Completion Rate

**Metric:** Percentage of assigned grading decisions completed within the cognitive processing window.

**Formal Definition:**
```
Task_Completion_Rate = (Count of tasks with latency ≤ 30 sec) / (Total tasks assigned) × 100
```

### Key Terms

- **Task:** One complete grading decision (educator is presented with a student answer and submits a numerical rating using the system)
- **Latency:** Elapsed time from task presentation until educator clicks "Submit" button
- **Cognitive Processing Window:** 30 seconds
  - Based on cognitive science literature: typical professional decision-making for medium-complexity tasks (Just & Carpenter, 1980; Wickelgren, 1977)
  - Tasks requiring >30 seconds suggest: system confusion, unclear instructions, or task difficulty issues

### Example Calculation

**Scenario:** Session 5 assigned 5 grading tasks

| Task | Latency | Status | Reasoning |
|------|---------|--------|-----------|
| Task 1 | 12 sec | ✓ Completed | Within window |
| Task 2 | 18 sec | ✓ Completed | Within window |
| Task 3 | 65 sec | ✗ Exceeded | Over 30-second threshold |
| Task 4 | 22 sec | ✓ Completed | Within window |
| Task 5 | 28 sec | ✓ Completed | Within window |

**Calculation:**
```
Task_Completion_Rate = 4 completed / 5 total = 80%
Decision: GO (≥50% threshold met)
```

---

## GO / NO-GO Decision Criteria

### GO Decision: task_completion_rate ≥ 50%

**Action:** Continue to next 5-session cohort without modifications

**Rationale:** Indicates system is usable, protocol is clear, and educator is able to work at normal cognitive pace

**Documentation:** Record in VALIDATION_GATE_LOG.csv with notes

**Example Notes:**
- "Tasks 2,3 had extended pauses (expected for harder answers)"
- "System stable; educator confident"
- "One session had frontend lag but recovered"

### NO-GO Decision: task_completion_rate < 50%

**Action:** STOP all sessions immediately; debug before resuming

**Rationale:** Suggests system malfunction, unclear instructions, task difficulty issues, or protocol problems

**Debugging Required (24-48 hours):**

1. **Immediate actions (same day):**
   - Stop recruiting new participants
   - Halt current session if ongoing
   - Debrief participating educator (if no identifying info collected yet)
   - Archive all raw files (session logs, videos, system state)

2. **Root cause analysis (next day):**
   - Review session video for failure modes
   - Check system logs (backend errors, timeouts, connection issues)
   - Verify frontend/backend communication (API latency, response times)
   - Test with mock data locally to replicate issue
   - Examine if instructions were unclear (observer notes from facilitator)

3. **Fix & validation (2-3 days):**
   - Implement fix (code update, protocol clarification, hardware fix, or instruction revision)
   - Conduct internal pilot: facilitator self-tests mock session
   - Verify fix resolves issue in controlled environment
   - Document root cause and fix in VALIDATION_GATE_LOG.csv

4. **Resumption:**
   - Resume recruitment after fix validated
   - Restart from Checkpoint N (not previous sessions)
   - Example: If NO-GO at Checkpoint 2 (sessions 6-10), resume with Session 11 (not Session 6)

---

## Pre-Commitment Against Peeking

**CRITICAL SAFEGUARD:** This protocol prevents researcher bias through opportunistic stopping rules.

### Anti-Peeking Guarantees

1. **No answer quality inspection** 
   - Gate metric uses ONLY timestamp data from session logs
   - Do NOT look at rubric quality, misconception frequencies, or trust ratings

2. **No study outcome analysis** 
   - Do NOT examine: SUS scores, qualitative coding counts, pre/post rubric changes
   - Do NOT correlate: completion rate with study outcomes
   - Do NOT peek at results to justify early stopping

3. **Automated metric computation** 
   - Use `compute_validation_gate.py` script (programmatic, no human discretion)
   - Cannot modify threshold or metric on the fly
   - Cannot use "close enough" judgments

4. **Decision before analysis** 
   - Gate decision must be committed to CSV log **before** any outcome analysis begins
   - Timestamp recorded: Date, Time, Decision
   - No retroactive adjustments

### Implementation

```bash
# Automated gate computation (no human interpretation)
python3 compute_validation_gate.py \
  --session-range 1-5 \
  --output-log data/session_logs/VALIDATION_GATE_LOG.csv

# Output example:
# Sessions: 1-5
# Completion_Date: 2026-06-03
# Completion_Rate: 78%
# Total_Tasks: 47
# Completed_Tasks: 37
# Decision: GO
# Timestamp: 2026-06-04 17:00 UTC
```

---

## Schedule & Timeline

| Checkpoint | Sessions | Expected Completion | Gate Decision By | Study Phase |
|------------|----------|---------------------|------------------|------------|
| 1 | 1-5 | ~June 3 | June 4, 5pm | Early pilot |
| 2 | 6-10 | ~June 7 | June 8, 5pm | Pilot wrap-up |
| 3 | 11-15 | ~June 10 | June 11, 5pm | Main study start |
| 4 | 16-20 | ~June 13 | June 14, 5pm | Main study |
| 5 | 21-25 | ~June 17 | June 18, 5pm | Main study |
| 6 | 26-30 | ~June 20 | June 21, 5pm | Mid-point |
| 7 | 31-35 | ~June 24 | June 25, 5pm | Main study |
| 8 | 36-40 | ~June 27 | June 28, 5pm | Main study |
| 9 | 41-45 | ~July 1 | July 2, 5pm | Late study |
| 10 | 46-50 | ~July 5 | July 6, 5pm | Late study |
| 11 | 51-55 | ~July 8 | July 9, 5pm | Late study |
| 12 | 56-60 | ~July 12 | July 13, 5pm | Closing |
| Final | 61-64 | ~July 15 | July 16, 5pm | Analysis prep |

---

## Logging & Documentation

### Create Session Log Files

Each session generates a JSON log file:

```
/data/session_logs/session_001.json
{
  "session_num": 1,
  "date": "2026-06-01",
  "educator_id": "P001",
  "condition": "A",
  "start_time": "2026-06-01T10:00:00Z",
  "end_time": "2026-06-01T10:20:00Z",
  "tasks": [
    {
      "task_num": 1,
      "question_id": "Q1",
      "presented_at": "2026-06-01T10:00:30Z",
      "submitted_at": "2026-06-01T10:00:42Z",
      "latency_sec": 12,
      "score_submitted": 3.5
    },
    { "task_num": 2, ... },
    ...
  ]
}
```

### Validation Gate Log

Create `/data/session_logs/VALIDATION_GATE_LOG.csv`:

```csv
Checkpoint,Sessions,Completion_Date,Completion_Time,Total_Tasks,Completed_Tasks,Completion_Rate,Decision,Root_Cause,Fix_Applied,Notes
1,1-5,2026-06-03,2026-06-04 17:00,47,37,78%,GO,N/A,N/A,Tasks 2,3 had extended pauses (expected for hard answers)
2,6-10,2026-06-07,2026-06-08 17:00,52,48,92%,GO,N/A,N/A,System stable; educator confident
3,11-15,2026-06-10,2026-06-11 17:00,48,41,85%,GO,N/A,N/A,One session had frontend lag but recovered quickly
...
```

### Columns Explained

- **Checkpoint:** Gate checkpoint number (1-13)
- **Sessions:** Session range (e.g., "1-5")
- **Completion_Date:** Date when 5 sessions completed
- **Completion_Time:** Time gate decision made (format: YYYY-MM-DD HH:MM UTC)
- **Total_Tasks:** Total tasks assigned in 5-session block
- **Completed_Tasks:** Tasks with latency ≤ 30 sec
- **Completion_Rate:** Percentage (Completed/Total × 100)
- **Decision:** GO or NO-GO
- **Root_Cause:** If NO-GO, what broke? (e.g., "Backend API timeout", "Unclear instructions")
- **Fix_Applied:** If NO-GO, what was fixed?
- **Notes:** Qualitative observations (do NOT include rubric quality, outcome data, or study hypotheses)

---

## Contingency: Handling NO-GO

### If NO-GO occurs (completion_rate < 50%)

**Day 1 (NO-GO day):**
- ✓ Stop all recruitment
- ✓ Halt any ongoing sessions
- ✓ Archive raw files (session logs, videos, backend logs)
- ✓ Document failure in VALIDATION_GATE_LOG.csv

**Days 2-3 (Debugging):**
- ✓ Review session video: What was educator doing? Where did they pause?
- ✓ Check system logs: API errors? Timeouts? Frontend crashes?
- ✓ Test locally: Can you replicate the issue with mock data?
- ✓ Interview facilitator: Were instructions unclear? Was task too hard?

**Days 4-5 (Fix & Validation):**
- ✓ Fix identified issue (code, instructions, hardware, or task design)
- ✓ Conduct internal pilot: facilitator self-tests to verify fix
- ✓ Test with next participant if confident
- ✓ Document fix in git commit or VALIDATION_GATE_LOG.csv

**Day 6+ (Resumption):**
- ✓ Resume recruitment after fix validated
- ✓ Start from Checkpoint N+1 (NEW sessions, not repeating previous)
- ✓ No loss of previous data, just skip to next cohort

### If NO-GO occurs twice

If NO-GO decisions at two consecutive checkpoints:
- Escalate to dissertation advisor
- May indicate systemic issue (KG quality, task difficulty, protocol design)
- Consider redesign before continuing

---

## Post-Study Validation

**August 16-20 (after all 64 sessions):**
- Both coders analyze final 10% sample (new transcripts) to validate consistency
- Check completion rates across entire study for drift
- Verify no systematic decline in engagement over time
- Report final gate log in supplementary materials

---

## Ethics & Transparency

### Pre-Registration

This protocol is **pre-registered** and committed to in the IRB submission as a safeguard against researcher bias.

### No Hidden Stopping Rules

- Only latency-based gate metric applies
- No "optional stopping" rules
- No p-hacking or outcome-dependent adjustments
- All decisions documented transparently

### Outcome Blindness

Gate decisions do NOT depend on:
- Study hypothesis validation
- Effect size of treatment
- Qualitative coding frequencies
- Participant satisfaction (SUS scores)

### Audit Trail

All gate decisions logged with:
- Decision timestamp
- Metric values
- Root cause (if NO-GO)
- Fix applied (if NO-GO)

---

## References

- Just, M. A., & Carpenter, P. A. (1980). A theory of reading: From eye fixations to comprehension. *Psychological Review*, 87(4), 329-354.
- Wickelgren, W. A. (1977). Speed-accuracy tradeoff and information processing dynamics. *Acta Psychologica*, 41(1), 67-85.
- Lakens, D. (2014). Performing high-powered studies efficiently with sequential analyses. *European Journal of Social Psychology*, 44(7), 701-710.
- Higgins, J. P. T., & Altman, D. G. (Eds.). (2008). *Cochrane Handbook for Systematic Reviews of Interventions* (Version 5.0.0). The Cochrane Collaboration.

---

## Appendix: compute_validation_gate.py

```python
#!/usr/bin/env python3
"""
compute_validation_gate.py — Automated validation gate metric computation.

Outcome-blind, pre-registered gate decision logic.
Prevents researcher bias through opportunistic stopping rules.

Usage:
    python3 compute_validation_gate.py --session-range 1-5 --output-log data/session_logs/VALIDATION_GATE_LOG.csv
"""

import argparse
import json
import csv
from datetime import datetime
from pathlib import Path

def compute_gate(session_range_start: int, session_range_end: int, 
                 log_dir: Path = None) -> dict:
    """
    Compute task completion rate for a session range (outcome-blind).
    
    Args:
        session_range_start: First session number (e.g., 1)
        session_range_end: Last session number (e.g., 5)
        log_dir: Directory containing session JSON logs (default: data/session_logs/)
    
    Returns:
        {
            "sessions": "1-5",
            "completion_date": "2026-06-03",
            "completion_time": "2026-06-04T17:00:00Z",
            "completion_rate": 78,  # percentage
            "total_tasks": 47,
            "completed_tasks": 37,
            "decision": "GO",
            "session_details": [...]
        }
    """
    if log_dir is None:
        log_dir = Path(__file__).parent / "data" / "session_logs"
    
    total_tasks = 0
    completed_tasks = 0
    session_details = []
    
    # Process each session in range
    for session_num in range(session_range_start, session_range_end + 1):
        log_file = log_dir / f"session_{session_num:03d}.json"
        
        if not log_file.exists():
            print(f"  Warning: Session {session_num} log not found at {log_file}")
            continue
        
        # Load session data
        with open(log_file) as f:
            session_data = json.load(f)
        
        # Count tasks with latency <= 30 seconds
        tasks = session_data.get("tasks", [])
        session_completed = sum(
            1 for task in tasks 
            if task.get("latency_sec", 999) <= 30
        )
        
        total_tasks += len(tasks)
        completed_tasks += session_completed
        
        session_details.append({
            "session": session_num,
            "total_tasks": len(tasks),
            "completed_tasks": session_completed,
            "completion_rate": round((session_completed / len(tasks) * 100) if tasks else 0, 1),
        })
    
    # Compute overall completion rate
    if total_tasks == 0:
        completion_rate = 0.0
        print(f"  ERROR: No task data found for sessions {session_range_start}-{session_range_end}")
    else:
        completion_rate = (completed_tasks / total_tasks) * 100
    
    # Decision logic
    decision = "GO" if completion_rate >= 50 else "NO-GO"
    
    return {
        "sessions": f"{session_range_start}-{session_range_end}",
        "completion_date": datetime.utcnow().date().isoformat(),
        "completion_time": datetime.utcnow().isoformat() + "Z",
        "completion_rate": round(completion_rate, 1),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "decision": decision,
        "session_details": session_details,
    }

def append_to_log(result: dict, log_file: Path, root_cause: str = "N/A", 
                  fix_applied: str = "N/A", notes: str = ""):
    """Append gate decision to CSV log."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if file exists; if not, write header
    file_exists = log_file.exists()
    
    with open(log_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Checkpoint', 'Sessions', 'Completion_Date', 'Completion_Time',
            'Total_Tasks', 'Completed_Tasks', 'Completion_Rate', 'Decision',
            'Root_Cause', 'Fix_Applied', 'Notes'
        ])
        
        if not file_exists:
            writer.writeheader()
        
        # Determine checkpoint number (1 + sessions_completed / 5)
        sessions_str = result['sessions']
        start, end = map(int, sessions_str.split('-'))
        checkpoint = (start - 1) // 5 + 1
        
        writer.writerow({
            'Checkpoint': checkpoint,
            'Sessions': result['sessions'],
            'Completion_Date': result['completion_date'],
            'Completion_Time': result['completion_time'],
            'Total_Tasks': result['total_tasks'],
            'Completed_Tasks': result['completed_tasks'],
            'Completion_Rate': f"{result['completion_rate']}%",
            'Decision': result['decision'],
            'Root_Cause': root_cause,
            'Fix_Applied': fix_applied,
            'Notes': notes,
        })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute outcome-blind validation gate metric")
    parser.add_argument("--session-range", required=True, help="Session range (e.g., 1-5)")
    parser.add_argument("--output-log", default="data/session_logs/VALIDATION_GATE_LOG.csv",
                       help="Output CSV log file")
    parser.add_argument("--log-dir", help="Directory containing session JSON logs")
    parser.add_argument("--root-cause", default="N/A", help="Root cause if NO-GO")
    parser.add_argument("--fix-applied", default="N/A", help="Fix applied if NO-GO")
    parser.add_argument("--notes", default="", help="Additional notes")
    
    args = parser.parse_args()
    
    start, end = map(int, args.session_range.split("-"))
    log_dir = Path(args.log_dir) if args.log_dir else None
    
    # Compute gate
    result = compute_gate(start, end, log_dir)
    
    # Print result
    print(f"\nValidation Gate: Sessions {result['sessions']}")
    print(f"  Completion Rate: {result['completion_rate']}%")
    print(f"  Tasks Completed: {result['completed_tasks']} / {result['total_tasks']}")
    print(f"  Decision: {result['decision']}")
    
    # Append to log
    append_to_log(
        result,
        Path(args.output_log),
        root_cause=args.root_cause,
        fix_applied=args.fix_applied,
        notes=args.notes
    )
    
    print(f"  Logged to: {args.output_log}\n")
    
    # Exit code: 0 for GO, 1 for NO-GO
    exit(0 if result['decision'] == 'GO' else 1)
```

---

**Document Version:** 1.0  
**Last Revised:** May 30, 2026  
**Status:** Ready for IRB submission
