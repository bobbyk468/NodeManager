# Hardware & Software Test Checklist

**Date Tested:** _______________  
**Tested By:** _______________  
**Location:** _______________  
**Sign-Off:** _______________

---

## Audio Recording System

- [ ] **USB Microphone Connected**
  - Model: _________________
  - Tested Date: ___________
  - Status: ☐ Working ☐ Issues

- [ ] **Audio Levels Tested**
  - Recording app: _________________
  - Test recording duration: 2 minutes
  - Audio quality: ☐ Clear ☐ Acceptable ☐ Needs Adjustment
  - Background noise level: ☐ Low ☐ Moderate ☐ High
  - Recommendation: _________________

- [ ] **File Storage Verified**
  - Recording path: `data/recordings/`
  - Test file saved: ☐ Yes ☐ No
  - File size (2 min): _________________ MB
  - Playback quality: ☐ Excellent ☐ Good ☐ Acceptable

- [ ] **Backup Process Tested**
  - Backup directory: `data/backups/`
  - Test backup command: `tar -czf data/backups/test_backup.tar.gz data/recordings/`
  - Result: ☐ Success ☐ Failed
  - Backup integrity verified: ☐ Yes ☐ No

**Audio System Status:** ☐ PASS ☐ NEEDS FIX ☐ FAILED

---

## Screen Recording System

- [ ] **Screen Recording Software Installed**
  - Software: _________________ (e.g., OBS, Camtasia, ScreenFlow)
  - Version: _________________
  - Status: ☐ Installed ☐ Missing ☐ Outdated

- [ ] **Test Recording (20 min)**
  - Start time: ___________
  - End time: ___________
  - Duration: ___________
  - File size: _________________ MB
  - Quality: ☐ 1080p ☐ 720p ☐ Other: _________

- [ ] **Frame Rate Consistent**
  - Target FPS: 30 FPS
  - Actual FPS: _________________
  - Dropped frames: ☐ None ☐ Minimal ☐ Significant

- [ ] **Audio Sync Verified**
  - Audio lag: ☐ None ☐ <100ms ☐ >100ms
  - Synchronized: ☐ Yes ☐ No ☐ Minor drift

- [ ] **File Storage Location**
  - Default save path: _________________
  - Test file saved: ☐ Yes ☐ No
  - Playback working: ☐ Yes ☐ No

**Screen Recording Status:** ☐ PASS ☐ NEEDS FIX ☐ FAILED

---

## Backend Server

- [ ] **Backend Installation Verified**
  - Location: `packages/backend/`
  - Dependencies: `npm install`
  - Status: ☐ Complete ☐ Incomplete ☐ Errors

- [ ] **Backend Startup**
  - Command: `npm run dev` (or `npm start:dev`)
  - Port: 3001
  - Startup time: _________________
  - Status: ☐ Running ☐ Failed ☐ Timeout

- [ ] **API Endpoints Responding**
  - Test endpoint: `curl http://localhost:3001/health`
  - Response: ☐ 200 OK ☐ 500 Error ☐ Connection refused
  - Response time: _________________

- [ ] **Database Connection**
  - Database status: ☐ Connected ☐ Failed
  - Table verification: ☐ All tables present ☐ Missing tables

- [ ] **Session Logging Working**
  - Log directory: `data/session_logs/`
  - Test log created: ☐ Yes ☐ No
  - Sample log readable: ☐ Yes ☐ No

**Backend Status:** ☐ PASS ☐ NEEDS FIX ☐ FAILED

---

## Frontend Server

- [ ] **Frontend Installation Verified**
  - Location: `packages/frontend/`
  - Dependencies: `npm install`
  - Status: ☐ Complete ☐ Incomplete ☐ Errors

- [ ] **Frontend Build**
  - Build command: `npm run build`
  - Build status: ☐ Success ☐ Failed
  - Build time: _________________

- [ ] **Frontend Startup**
  - Dev command: `npm run dev`
  - Port: 5173
  - Startup time: _________________
  - Status: ☐ Running ☐ Failed

- [ ] **UI Accessible**
  - URL: `http://localhost:5173`
  - Page loads: ☐ Yes ☐ No
  - Load time: _________________ seconds
  - All components visible: ☐ Yes ☐ No (missing: _________)

- [ ] **Interactivity Test**
  - Click buttons: ☐ Working ☐ Issues
  - Form input: ☐ Working ☐ Issues
  - Navigation: ☐ Working ☐ Issues
  - Charts/visualizations: ☐ Working ☐ Issues

- [ ] **Browser Console**
  - Errors: ☐ None ☐ Minor warnings ☐ Critical errors
  - Network requests: ☐ All successful ☐ Some failures
  - Performance: ☐ Good (< 3s load) ☐ Acceptable ☐ Slow

**Frontend Status:** ☐ PASS ☐ NEEDS FIX ☐ FAILED

---

## Network & Connectivity

- [ ] **Both Servers Running Simultaneously**
  - Backend (3001): ☐ Running ☐ Failed
  - Frontend (5173): ☐ Running ☐ Failed
  - Both responding: ☐ Yes ☐ No

- [ ] **Cross-Server Communication**
  - Frontend → Backend API calls: ☐ Working ☐ Issues
  - API response time: _________________
  - Error rate: _________________

- [ ] **Network Stability (20 min test)**
  - Duration: 20 minutes
  - Disconnections: ☐ None ☐ 1-2 ☐ >2
  - Latency spikes: ☐ None ☐ Occasional ☐ Frequent
  - Overall stability: ☐ Excellent ☐ Good ☐ Concerning

**Network Status:** ☐ PASS ☐ NEEDS FIX ☐ FAILED

---

## Timing & Alerts

- [ ] **Kitchen Timer**
  - Device: _________________
  - Tested: ☐ Yes ☐ No
  - Alarm audible: ☐ Yes ☐ No
  - Audible at distance: ☐ Yes ☐ No
  - Backup timer ready: ☐ Yes ☐ No

- [ ] **System Clock Synchronized**
  - Server time: _________________
  - Local time: _________________
  - Difference: _________________
  - NTP sync: ☐ Yes ☐ No

**Timing Status:** ☐ PASS ☐ NEEDS FIX ☐ FAILED

---

## Session Simulation (Full Dry Run)

- [ ] **Simulate 20-Minute Session**
  - Start all systems (backend, frontend, audio, screen recorder)
  - Navigate to http://localhost:5173
  - Perform test interactions (load a sample answer, interact with UI)
  - Record screen + audio for full 20 minutes
  - Stop recording and backup files

  Results:
  - All systems stable: ☐ Yes ☐ No
  - Audio/video synchronized: ☐ Yes ☐ No
  - Data logged correctly: ☐ Yes ☐ No
  - No errors encountered: ☐ Yes ☐ No
  - Session can be analyzed: ☐ Yes ☐ No

**Dry Run Status:** ☐ PASS ☐ NEEDS FIX ☐ FAILED

---

## Issues Encountered

| Issue | Severity | Status | Resolution |
|-------|----------|--------|-----------|
| | ☐ Critical ☐ Major ☐ Minor | ☐ Open ☐ Fixed | |
| | ☐ Critical ☐ Major ☐ Minor | ☐ Open ☐ Fixed | |
| | ☐ Critical ☐ Major ☐ Minor | ☐ Open ☐ Fixed | |

---

## Final Approval

**Overall Status:** ☐ **READY FOR STUDY** ☐ **NEEDS FIXES** ☐ **NOT READY**

**Critical Issues Blocking Study:**
- Issue 1: _________________
- Issue 2: _________________
- Issue 3: _________________

**Recommendations:**
_______________________________________________________________________

**Date Approved:** _______________

**Approved By:** _________________

**Sign-Off:** _________________

---

**Test Duration:** _________________ minutes  
**Next Test Date:** _________________  
**Notes:** _________________________________________________________________

---

*Save this checklist and repeat before each week of study (daily verification not required if all systems remain unchanged)*
