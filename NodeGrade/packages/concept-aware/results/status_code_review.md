# ConceptGrade Status — Code Review & Action Items

Based on the `conceptgrade_project_status.md` document, here is a structured code review identifying technical debt, bugs, and necessary implementation tasks before the full IEEE VIS 2027 user study.

---

### 🔴 Critical: Uncommitted Codebase (Data Loss Risk)
**Issue:** The entire LRM-era phase of the project (Trace Parser, LRM Verifier, GEE Analysis, React Study Components) exists *only* on the local machine and has never been pushed to a remote repository.
**Recommendation:** Immediately execute the 3-commit strategy outlined in Section 8.5 of the status document. 
*   **Commit 1:** LRM Core Pipeline (`lrm_verifier.py`, `trace_parser.py`)
*   **Commit 2:** Visual Analytics User Study Layer (React components, `studyLogger.ts`)
*   **Commit 3:** Study Analysis & Review Docs (`analyze_study_logs.py`, `/results/`)

---

### 🟡 Medium: Misleading Telemetry Field Name
**Location:** `packages/frontend/src/utils/studyLogger.ts` & `packages/concept-aware/analyze_study_logs.py`
**Issue:** The field `panel_focus_ms` records a Unix timestamp (`Date.now()` at component mount), but the `_ms` suffix typically implies a duration (e.g., "milliseconds spent focused"). This will cause confusion during data analysis.
**Action Required:** Rename the field from `panel_focus_ms` to `panel_mount_timestamp_ms` in the TypeScript interface, the payload constructor, and the Python analysis script.

---

### 🟡 Medium: Missing Telemetry Durability Endpoint
**Location:** `packages/backend/src/study/`
**Issue:** The frontend `studyLogger.ts` is configured to fire-and-forget events to `POST /api/study/log` for IRB-grade data durability (protecting against browser crashes). However, this backend endpoint does not exist yet.
**Action Required:** Implement a NestJS controller and service to accept the `StudyEvent` JSON payload and append it to a persistent log file or database. This must be completed *after* the pilot study confirms the event schema is stable, but *before* the full N=20 study.

---

### 🟢 Low: GEE Negative Correlation Fallback
**Location:** `packages/concept-aware/analyze_study_logs.py`
**Issue:** The Generalized Estimating Equations (GEE) model using an Exchangeable correlation structure yielded a negative working correlation (ρ = -0.308) during dummy testing. While possible, strong negative intra-participant correlation is unusual.
**Action Required:** Add logic to detect if ρ < 0 in the real study data. If it is, the script should cleanly fall back to an `Independence()` working correlation structure to avoid convergence issues.

---

### 🟢 Low: Hyphen Normalization Vulnerability
**Location:** `packages/frontend/src/utils/conceptAliases.ts` (`normalizeConceptId`)
**Issue:** The normalization function replaces underscores with spaces but ignores hyphens. Thus, `"chain-rule"` remains `"chain-rule"`. The system currently relies on the downstream Levenshtein distance (similarity = 0.9) to bridge the gap between `"chain-rule"` and `"chain rule"`. It works by accident.
**Action Required:** Either explicitly document this reliance on fuzzy matching, or update the regex to handle hyphens: `.replace(/[-_]/g, ' ')`.

---

### 🟢 Low: Redundant Map Rebuilding
**Location:** `packages/frontend/src/utils/conceptAliases.ts` (`matchesContradictsNode`)
**Issue:** The `aliasLookup` Map is rebuilt from scratch on every invocation of the function.
**Action Required:** Given the small N=20 study size and the fact this runs on user click, the performance impact is negligible. However, add a comment warning that if this function is ever moved into a hot path (like a React render loop), the Map instantiation must be hoisted outside the function or memoized.
