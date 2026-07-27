# OSF Pre-Registration — ConceptGrade Educator Co-Auditing Study

**Working title:** Effects of a Knowledge-Graph-Grounded Visual Analytics
Dashboard on Educator Co-Auditing of Automated Short-Answer Grading

**Target venue for results:** IEEE VIS / VAST 2027

**To paste into Paper 2 after upload:**
- OSF project URL: `https://osf.io/[PROJECT-ID]/`
- OSF registration URL: `https://osf.io/[REGISTRATION-ID]/`
- SHA-256 of this document at registration time: (computed by OSF on upload)

---

## 1. Authors & roles (fill in for non-blind copy)

- PI: \[NAME\], \[INSTITUTION\] — design, supervision, IRB lead
- Co-author A: \[NAME\] — implementation, data analysis
- Coder 1, Coder 2: (recruited; identities masked from PI during coding)

---

## 2. Hypotheses (locked)

```yaml
primary:
  H1_causal_attribution:
    description: |
      Educators in Condition B (full ConceptGrade dashboard) will produce
      a higher per-participant frequency of Causal Attribution (CA) codes
      in their think-aloud transcripts than educators in Condition A
      (text-summary-only baseline).
    operationalisation: |
      CA code := an utterance that references a specific visual artefact
      (KG node, gap badge, reasoning step, severity chip) as the reason
      for a grading decision or rubric edit.
    statistical_test: Mann-Whitney U (one-tailed, B > A)
    primary_alpha: 0.05
    minimum_detectable_effect: ratio_B_to_A >= 2.5

  H2_semantic_alignment:
    description: |
      Rubric edits made in Condition B will show higher Semantic Alignment
      (SA) with the KG topology than edits made in Condition A.
    operationalisation: |
      SA score per edit := 1 if the edit text refers to a KG node label
      verbatim or to a 1-hop neighbour concept, 0 otherwise. Aggregated to
      per-participant mean.
    statistical_test: Mann-Whitney U (one-tailed, B > A)
    primary_alpha: 0.05

secondary:
  H3_trust_calibration:
    description: |
      Calibration error |self_conf - accuracy| will be SMALLER in
      Condition B than in Condition A.
    statistical_test: Mann-Whitney U (one-tailed, A > B)
    primary_alpha: 0.05

  H4_automation_bias:
    description: |
      Rate of accepting INCORRECT system grades without modification will
      not be HIGHER in Condition B (test against equivalence margin 0.10).
    statistical_test: TOST equivalence test
    primary_alpha: 0.05

  H5_sus:
    description: |
      System Usability Scale score will be higher in Condition B.
    statistical_test: Mann-Whitney U (one-tailed, B > A)
    primary_alpha: 0.05
```

---

## 3. Design

```yaml
study_type: between-subjects, randomised, controlled
conditions:
  A_control:
    label: text-summary
    description: |
      Participant sees aggregate ML metrics (MAE, Wilcoxon p, total
      answers, domain insights) and a SUS questionnaire. No KG view, no
      reasoning trace, no editable rubric chips.
  B_treatment:
    label: conceptgrade-dashboard
    description: |
      Participant sees the full ConceptGrade dashboard: misconception
      heatmap, KG sub-graph, reasoning trace with gap badges, score
      samples table, and Click-to-Add rubric editor.

participants:
  target_n: 64
  per_condition: 32
  recruitment_pool: CS / EE / Math educators with >= 2 years' teaching
  recruitment_channels:
    - university CS department listservs (3 institutions)
    - SIGCSE / SIGGRAPH professional networks
    - paid Prolific panel (filter: technical-education experience)
  compensation: USD 30 honorarium per 60-min session
  exclusions:
    - no teaching experience in any conceptually-rich technical course
    - failed attention check during consent
    - participated in pilot
  randomisation:
    method: block randomisation (block size = 4) stratified by self-reported
            teaching experience (2-5 yr / 6-10 yr / >10 yr)
    seed: documented in supplementary `randomisation_seed.txt` AT
          registration time, NOT changed after recruitment opens
```

---

## 4. Materials

- Question set: 8 Mohler answers per participant, rotated using a Latin square
  to control for order/learning effects; same 8 answers across conditions.
- Both conditions present the same 8 answers with the same baseline ML grades.
- Code base version: git tag `study-v1.0`, SHA-256 commitment in §10.

---

## 5. Procedure

```
1. Consent (5 min, online via institutional consent platform)
2. Demographics + teaching-experience screener (3 min)
3. Onboarding video for the assigned condition (4 min)
4. Warm-up answer (Q0, not analysed) (3 min)
5. 8 graded answers, one at a time:
     - participant decides: agree / modify / disagree with ML grade
     - participant may add up to 3 rubric criteria using the Click-to-Add
       chip strip (Condition B only)
     - participant rates self-confidence (0-100%)
     - participant thinks aloud (audio recorded)
6. SUS questionnaire (10 items, 5 min)
7. Open debrief (5 min)
Total: 45-60 min
```

---

## 6. Analysis plan (locked)

```yaml
primary_tests:
  software: Python 3.11+ / scipy.stats
  alternative: one-tailed where pre-registered direction is given
  multiple_comparison_correction:
    method: Holm-Bonferroni
    applied_to: [H1, H2, H3, H5]  # H4 is equivalence, separate family

sensitivity_tests:
  - parametric: two-sample t-test (Welch)
  - bayesian: BayesFactor (rscala) with default Cauchy prior, r = 0.707

qualitative_coding:
  scheme: {CA: Causal Attribution, SA: Semantic Alignment,
           TC: Trust Calibration, II: Interaction Insight}
  number_of_coders: 2
  blinding: coders blind to condition assignment
  irr_pilot:
    sample: 20% of transcripts (random)
    target: Cohen kappa >= 0.70 for the multi-category coding
    if_target_not_met: codebook refinement + second IRR pilot, repeat until
                       target met OR after 3 cycles drop to descriptive
                       reporting only (logged in addendum)

stopping_rule: |
  No interim analyses. Data collection runs to N = 64 OR the
  recruitment-cutoff date (July 16, 2026), whichever comes first. Validation
  gate metrics (compute_validation_gate.py) are outcome-blind and do NOT
  trigger inferential test re-runs.
```

---

## 7. Sample size justification

```yaml
power_target: 0.80
alpha: 0.05 (one-tailed for directional primary hypotheses)
primary_test: Mann-Whitney U
effect_sizes_considered:
  optimistic_d: 0.88
    citation: Amershi et al. 2014, ACM CHI - structured XAI vs. text-only
    n_per_cell_at_80_power: 21
  conservative_d: 0.50
    rationale: typical SUS-style effect across HCI dashboard studies
    n_per_cell_at_80_power: 64
  selected_n: 32 per cell  # midpoint, decision recorded at registration
selected_n_power_at_d_088: 0.93
selected_n_power_at_d_050: 0.52
qualitative_chi_square:
  expected_ratio_B_to_A: 2.5  # CA-code frequency
  n_per_cell_for_80_power: 28
```

---

## 8. Deviation reporting

Any deviation from this pre-registration (recruitment shortfall, protocol
refinement, analysis change) will be logged as a dated addendum on OSF
before any inferential test is run on the affected data. To prevent the
addendum mechanism from being used as a post-hoc revision channel, the
following items are **not addendable**: §2 hypotheses (H1-H5), §3 design
conditions, §6 primary statistical tests (Mann-Whitney $U$,
Holm-Bonferroni), §6 IRR target ($\kappa \geq 0.70$), and §7
power-analysis decision rule ($d \geq 0.7$ confirmatory boundary). These
can only be revised by filing a full superseding re-registration on OSF
(a public, auditable act, distinct from an addendum). Addenda may revise
codebook category boundaries, task-instruction wording, and Latin-square
assignment under pilot-participant withdrawal.

Pre-registered fallback (also in Paper 2 §5.1):

```yaml
recruitment_fallback:
  trigger: n < 64 by July 16, 2026
  step_1: extend recruitment up to 4 weeks
  step_2: relax minimum experience from 2 yrs to 1 yr (excluding undergrads)
  step_3: if final n < 50, downgrade primary hypotheses from confirmatory
          to exploratory; report Bayesian credibility intervals alongside
          frequentist p-values; flag clearly in abstract and limitations.
```

---

## 9. Data and code availability

```yaml
data:
  raw_audio: NOT shared (PII)
  de_identified_transcripts: OSF, embargo until publication
  coded_data_csv: OSF, embargo until publication
  analysis_outputs: OSF, public on publication
code:
  repository: github.com/[ANON]/conceptgrade  (anonymised mirror at submission)
  tag_at_study_start: study-v1.0
  license: MIT
  reproducibility_script: reproduce_study_analysis.py
```

---

## 10. Hash commitment

The SHA-256 of this document (Markdown text, UTF-8, LF line endings) is
computed at OSF upload time and recorded in the OSF registration metadata.
Any change to hypotheses, conditions, or analysis after that hash is set
must be logged as an addendum (see §8).

---

## 11. Conflicts of interest

\[Statement here at non-blind submission time.\]

---

## 12. Ethics

IRB Protocol \#: \[PROTOCOL-NUMBER\] — \[INSTITUTION IRB BOARD\]
Approval date: \[YYYY-MM-DD\]
Recruitment opens: \[YYYY-MM-DD\] (no recruitment before IRB approval)
