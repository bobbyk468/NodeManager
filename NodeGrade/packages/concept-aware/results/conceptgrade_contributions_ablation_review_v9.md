# ConceptGrade — Contributions & Ablation Readiness Review v9

**Date:** 2026-04-14  
**Context:** IEEE VIS 2027 VAST — pre-pilot, pre-writing  
**Prior reviews:** v1–v7 (ablation → gap moderator), v8 (figure trace, GEE logit, intro language)  
**This review:** (1) GEE logit-link correction verified; (2) formal contributions drafted; (3) DigiKlausur ablation command documented; (4) 5 open questions

---

## 1. What Was Completed Since v8

### 1.1 Moderation Analysis — Logit Link Corrected

Gemini v8 flagged that `mixedlm` (linear link) was incorrect for binary `within_30s`.

**Fix in `analyze_study_logs.py`:** Replaced `MixedLM` with `GEE + Binomial(logit) + Exchangeable`:

```python
model = GEE.from_formula(
    'within_30s ~ condition * trace_gap_count',
    groups='session_id',
    data=df,
    family=Binomial(),          # logit link — correct for binary outcome
    cov_struct=Exchangeable(),  # edits within participant share correlation ρ
).fit()
```

**Why GEE over true GLMM**: In Python statsmodels, mixed-effects GLM (GLMM) for binary outcomes requires `pymer4`/`rpy2` (R dependency). GEE is the accessible alternative: it handles clustered non-independence via working correlation, produces population-averaged estimates, and is widely accepted in HCI/VIS for analysing repeated-measures binary outcomes. For the paper, label this "GEE (Exchangeable, Binomial/Logit)" in the Methods.

**Output now includes odds ratios** (exp(coef)) alongside coefficients and p-values.

**Verified on dummy dataset**: 5 sessions × 4 edits = 20 edit records. GEE converges cleanly; extreme ORs in dummy data are expected from perfectly separable Condition A/B split — real study data will be moderate.

**Pre-registration tier**: Exploratory. p < 0.10 → "directional trend" in Discussion. Do not elevate to primary claim.

---

### 1.2 Formal Contributions (Locked v8+v9)

For Section 1 (Introduction), bulleted list preceded by "In summary, our contributions are:":

> **In summary, our contributions are:**
>
> 1. **Topological Reasoning Mapping (TRM)** — A formal technique that maps each step of a large reasoning model's chain-of-thought to nodes in a domain Knowledge Graph, classifies each step as SUPPORTS, CONTRADICTS, or UNCERTAIN, and evaluates *topological continuity* by detecting structural leaps between disconnected KG regions. TRM is the first approach to operationalize reasoning-chain continuity as a measurable, visualizable property (Section 3).
>
> 2. **Bidirectional Co-Auditing Interface** — A visual analytics system that links a TRM trace panel, a KG subgraph view, and a rubric editor through DashboardContext bidirectional brushing. The Click-to-Add interaction — where educators click CONTRADICTS chips directly — provides zero-ambiguity rubric attribution for causal proximity analysis (Section 4).
>
> 3. **Multi-Dataset ML Accuracy Evidence** — Our KG-grounded pipeline reduces Mean Absolute Error by 32.4% on the Mohler CS benchmark (Wilcoxon p=0.003, N=120) and achieves Fisher combined p=0.003 across 1,239 answers from three domain datasets. Non-significance on Kaggle ASAG (elementary science) defines the KG discriminability boundary condition (Section 5a).
>
> 4. **Controlled User Study with Pre-Registered Causal Metrics** — A two-condition study (N=X educators, CS/NN TAs with grading experience) using multi-window causal attribution (15 s/30 s/60 s windows, primary = 30 s), semantic alignment rate as the primary H2 metric, and trace_gap_count as a pre-registered exploratory moderator of H1 (Section 5b).

**Notes on wording for submission draft:**
- Contribution 1: "first approach to operationalize" — check prior work (trace-to-graph alignment exists in code-generation debugging; but not for reasoning-chain continuity in ASAG). Flag for Related Work cross-check.
- Contribution 4: fill in N after pilot; keep "X" as placeholder until study is complete.
- **Bold** contribution names match IEEE VIS convention.

---

### 1.3 DigiKlausur Gemini Flash Ablation — Not Yet Run (API Key Required)

**Why it's needed (Gemini v8 decisions Q1 + Q5):**
1. Paper figure: need a native Gemini Flash structured trace for Sample 0 where `CONTRADICTS` steps have `kg_nodes` populated (DeepSeek-R1 traces have empty `kg_nodes` in judgment steps)
2. Cross-model validation subsection (Section 5): paper must show TRM works across different LRMs
3. Pilot fallback: if DeepSeek traces are too verbose for the UI, Gemini Flash traces are the immediate alternative

**Command to run (Gemini Flash, DigiKlausur, full 646 samples):**
```bash
export GEMINI_API_KEY=your_key_here
cd packages/concept-aware
python run_lrm_ablation.py \
  --datasets digiklausur \
  --use-gemini \
  --gemini-key $GEMINI_API_KEY \
  --gemini-thinking-budget 8192 \
  --sample-n 646
```

**Expected cost:** ~$5–10 for 646 samples at Gemini 2.5 Flash pricing.  
**Expected output:** `data/digiklausur_lrm_traces_gemini.json` (new file, does not overwrite DeepSeek traces).  
**Status:** Blocked on `GEMINI_API_KEY` — neither `GEMINI_API_KEY` nor `DEEPSEEK_API_KEY` is currently set in the environment. Set the key and run the command above.

---

## 2. Open Questions for This Review

### Q1 — Cross-Model Validation Subsection Scope

Gemini v8 recommended a "Cross-Model Validation" subsection in Section 5 comparing DeepSeek-R1 vs. Gemini Flash traces on DigiKlausur. This is a strong addition — it shows TRM is model-agnostic (the topological continuity measure works regardless of which LRM generates the trace).

**Questions:**
- Should this be a dedicated subsection (Section 5c) or folded into Section 5a as a secondary table?
- What is the right comparison metric? Options: (a) trace length (Gemini is more concise), (b) node coverage (fraction of steps with kg_nodes), (c) gap count distribution, (d) semantic alignment rate per model in the user study condition
- If Gemini Flash traces are shorter and more structured, does the paper claim that shorter traces are pedagogically better, or do we remain agnostic on trace length?

---

### Q2 — `POST /api/study/log` Backend: Build Before Pilot or Not?

Current status: `localStorage` fallback active. Risk assessment (unchanged from v5):
- **Pilot (2–3 participants):** localStorage loss risk is low — facilitator can export the log immediately after each session
- **Full study (N=20):** Losing 2 of 20 sessions = 10% data loss. With N=10 per condition, this reduces statistical power substantially

Gemini v8 confirmed: build before full study, not before pilot.

**Action needed**: After the pilot, build the NestJS `POST /api/study/log` endpoint before expanding to N=20. Estimated effort: ~2 hours. This is the only remaining infrastructure blocker for the full study.

---

### Q3 — Introduction Draft: Full Paragraph Feedback

The Introduction first paragraph (drafted in v8) needs one more revision pass before writing begins. Current draft:

> "Automated short-answer grading has reached human-level accuracy on structured benchmarks [Mohler 2011, Dzikovska 2016, G-Eval 2023], yet educators remain reluctant to rely on it in high-stakes assessments. The bottleneck is not performance — it is accountability: when a model downgrades a student's answer, the educator has no mechanism to inspect why. This opacity makes the system an oracle to be trusted or ignored, rather than a collaborator to be audited. We argue that the missing link is not a better model, but a better interface — one that projects the model's reasoning onto the educator's domain knowledge, creating a shared visual topology for co-auditing. We present **ConceptGrade**, a visual analytics system that implements this topology through **Topological Reasoning Mapping (TRM)**: a technique that projects a large reasoning model's chain-of-thought onto a domain Knowledge Graph, enabling educators to co-audit both machine reasoning and student knowledge gaps simultaneously."

**Questions:**
- Is the G-Eval 2023 citation the right one, or should we cite a more recent 2024/2025 LLM-grading result that shows accuracy is no longer the barrier?
- The transition "oracle to be trusted or ignored... collaborator to be audited" — should this be split into two sentences for clarity, or does the contrast land better as one?
- Should the final sentence of the paragraph introduce ConceptGrade, or save that for a "In this paper, we present..." opening of the second paragraph?

---

### Q4 — Paper Figure: Truncation Layout in the UI

The paper figure will show Sample 0 (DigiKlausur, ANN definition question) with steps 1–4 and 14–20 truncated via ellipsis. This requires a visual layout decision:

**Option A — Rendered screenshot**: Take a screenshot of the VerifierReasoningPanel with real Gemini Flash trace data and crop/annotate in Illustrator. Most authentic; shows the actual UI.

**Option B — Reproduced diagram**: Redraw the trace as a structured diagram (boxes for steps, dashed amber pill for gaps, color coding). More control over layout; standard in VIS papers for system figures.

**VIS convention**: For system figures showing a UI component, IEEE VIS typically expects a cropped screenshot of the actual running system (not a reproduction). A reproduced diagram is acceptable for the *architecture* figure but not the *visual encoding* figure.

**Question:** Given that we need a Gemini Flash trace with `kg_nodes` in CONTRADICTS steps (not yet available), should the paper figure be a placeholder screenshot of the current DeepSeek trace until the ablation is run?

---

### Q5 — Writing Kickoff: Section 1 or Section 3 First?

Gemini v6 and v8 both confirmed: write Introduction first. But the Introduction's contribution bullets (locked above) reference "Section 3 (TRM formal definition)" and "Section 4 (interface)". Writing the Introduction first means the contribution claims are stated before the technical sections are written — which is the correct IEEE VIS approach (top-down argument), but requires disciplined constraint not to overpromise.

**Proposed writing kickoff task:**
1. Write Section 1 (Introduction) — ~1,000 words, ends with the 4 contribution bullets above. Use the first-paragraph draft from v8.
2. Then write Section 3.1 (TRM formal definition) — formalize the definitions already in memory.
3. Then write Section 5a (ML accuracy evaluation) — data is final, write from the table.

**Question:** Is there any argument for writing Section 3 (System Design) before Section 1, so the formal definition is locked before contribution bullet 1 is written? Or does writing Introduction first force a productive constraint that prevents System Design from becoming a feature list?

---

## 3. Phase Checklist

### Immediate (before writing starts)
| Action | Owner | Blocker |
|--------|-------|---------|
| Set `GEMINI_API_KEY` and run DigiKlausur ablation | User | API key |
| File IRB amendment (expedited, hybrid framing from v8) | User | Admin |
| Send first TA outreach emails | User | None |

### Writing Phase (after ablation complete)
| Task | Status |
|------|--------|
| Introduction — full 1,000 words | ✗ |
| Section 3.1 — TRM formal definition | ✗ |
| Section 5a — ML accuracy table + narrative | ✗ |

### Infrastructure (before full study N=20)
| Task | Status |
|------|--------|
| `POST /api/study/log` NestJS endpoint | ✗ |
| Pilot study (2–3 participants) | ✗ |
| Cued Retrospective Think-Aloud script | ✗ |
