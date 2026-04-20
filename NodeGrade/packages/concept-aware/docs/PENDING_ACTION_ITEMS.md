# Pending Action Items
**Date:** 2026-04-19
**Status:** All engineering infrastructure and evaluation scaffolding verified. No code gates remain.

This document tracks the final manual steps, administrative gates, and writing tasks required to complete both Paper 1 (EMNLP/BEA) and Paper 2 (IEEE VIS 2027).

---

## 1. Administrative & Setup (Hard Gates)

- [ ] **Submit IRB Application:** CRITICAL BLOCKER for Paper 2.
  - *Note:* Use the `E2E_VALIDATION_REPORT_APR19.md` (specifically the FERPA compliance, FNV-1a hashing, and lack of raw text in logs) as technical evidence for data anonymization and privacy.
- [ ] **Renew Gemini API Key:** Required to complete the final targeted rescore for Paper 1.

---

## 2. Paper 1: NLP/EdAI (EMNLP 2026 / BEA Workshop)

### Execution
- [ ] **Run Targeted Rescore:** Once API key is renewed, rescore the 8 pending Mohler samples (IDs: 37, 42, 112–118).

### Manuscript Drafting
- [ ] **Author Block:** Fill in `[University Name]`, `[City, Country]`, `b.katragadda@[university.edu]`.
- [ ] **Baseline Description (§4.2):** Clarify the description of the LLM baseline to accurately reflect whether it uses an LLM or is a rule-based proxy.
- [ ] **Page Limit Check:** Review the manuscript (currently 9+ tables and 6 figures) against the 8-page IEEEtran limit. Identify content to trim if necessary.
- [ ] **Remove `hyperref`:** Remove `\usepackage{hyperref}` from the camera-ready version if required by the specific conference.
- [ ] **Tone Calibration:** Vary paragraph lengths and remove repetitive "Finding 1 / Finding 2..." mechanical phrasing.

---

## 3. Paper 2: Visual Analytics (IEEE VIS 2027 - VAST)

### Data Collection (Blocked by IRB)
- [ ] **Recruit N=30 Educators:** 15 participants for Condition A, 15 for Condition B.
- [ ] **Conduct Study Sessions:** Execute the 60-minute think-aloud sessions.
- [ ] **Administer SUS Questionnaire:** Ensure participants complete the SUS post-task.

### Data Analysis
- [ ] **Qualitative Coding:** Transcribe and code the think-aloud sessions for Causal Attribution (CA), Semantic Alignment (SA), Trust Calibration (TC), and Interface Interaction (II). Target Cohen's Kappa (κ) ≥ 0.70.
- [ ] **Run Final Analysis Script:** Execute `analyze_study_results.py` on the real study logs (`data/study_logs/`).

### Manuscript Drafting
- [ ] **Add Figures:** Insert actual figures into the manuscript:
  - (a) Dashboard screenshot
  - (b) TRM pipeline diagram
  - (c) Study conditions figure (A vs B)
  - (d) Results figure (pending user study)
- [ ] **Update N-Values:** Replace `N=[pending]` with actual participant count (e.g., N=30) in abstract, §5.1, §6.2, §6.5.
- [ ] **Draft User Study Results (§5.2 & §5.3):** Populate the results sections with findings from the N=30 study.
- [ ] **Refine Related Work (§2.3):** Break down the long paragraphs in the "Sensemaking" subsection for better readability.
- [ ] **Tone Calibration:** Ensure varied paragraph lengths to sound more natural and less mechanical.
