# Research Review Request

**Instructions for the reviewer (please read first):**

You are acting as a PhD advisor / committee member evaluating this body of work. The student (me) is asking for an honest verdict: **approve or reject** this as a defensible PhD-level research contribution (or, if it is closer to "one strong paper" than "a completed dissertation," say that explicitly). Do not soften the verdict to be encouraging — the student has explicitly asked for rigor over reassurance, and has spent an entire research cycle correcting a previous fabricated-data incident specifically to avoid that trap again.

If you reject or partially reject, please give:
1. The **specific reason(s)** for the rejection (not just "needs more work" — name the exact gap).
2. **Concrete, actionable improvements** that would address each reason.
3. Whether each gap is a **methodological fix** (more analysis on existing data), a **resource fix** (needs new data/compute/human subjects), or a **framing fix** (needs different positioning, not new work).

All numbers below are drawn from real experimental data and cached predictions; the student has an internal automated verification script (300+ checks) that recomputes every claim from raw data, so numeric claims below should be taken as accurate to the source data, not as unverified assertions.

---

## 1. Research Question

Does grounding LLM-based automated short-answer grading (ASAG) in an explicit domain knowledge graph (KG) improve accuracy over an identical-model zero-shot LLM baseline, in Computer Science education?

## 2. System Under Test: ConceptGrade

A five-layer pipeline: (1) LLM concept extraction into a typed graph, (2) deterministic KG comparison (coverage/accuracy/integration scores), (3) Bloom's + SOLO cognitive-depth classification, (4) misconception detection against a 16-entry taxonomy, (5) an LLM Verifier that reviews the raw answer plus all KG evidence and produces the final grade. Baseline: **C_LLM**, the identical LLM model prompted zero-shot with only the question, reference answer, and student answer (no KG evidence) — isolates model capability as a confound.

Expert KG: 101 concepts, 138 typed relationships, Data Structures domain, hand-built and frozen before evaluation.

## 3. Data Integrity Background (relevant context, not a finding)

An earlier version of this project's headline results were computed against a **fabricated, hand-authored 120-sample fixture**, discovered mid-project via a docstring self-admission and confirmed against a real HuggingFace mirror. All work below is on the **real** Mohler et al. (2011) benchmark (`nkazi/MohlerASAG`, CC-BY-4.0): 46 questions / 1,262 responses filtered to the KG's topical coverage, later extended to 50 questions / 1,371 responses. Two additional real datasets provide cross-domain checks: DigiKlausur (Neural Networks, 17 questions / 646 responses) and Kaggle ASAG (Elementary Science, 150 questions / 368 deduplicated responses).

## 4. Headline Finding (single-call architecture)

| System | Pearson r | QWK | MAE | RMSE |
|---|---|---|---|---|
| C_LLM (baseline) | 0.7904 | 0.5005 | 1.2821 | 1.7243 |
| ConceptGrade (single call) | 0.7841 | 0.5237 | **1.1771** | **1.5326** |

- MAE improves 8.2%, response-level Wilcoxon p<0.0001.
- Question-clustered Wilcoxon (the more appropriate unit given non-independence within a question): p=0.111 two-tailed, p=0.056 one-tailed — **marginal, not robust**.
- Pearson correlation is **worse**, not better, for ConceptGrade.
- Post-hoc 5-fold cross-validated monotonic recalibration cuts MAE ~3x for both systems and **inverts** the comparison — after calibration, C_LLM has significantly lower MAE (p=0.017). Most of ConceptGrade's raw MAE edge is scale-bias correction, not ranking quality.

## 5. Ablation: what is actually driving the gain?

| Condition | MAE | r | vs. C_LLM |
|---|---|---|---|
| C_LLM (no KG) | 1.282 | 0.790 | — |
| KG-grounded score, no Verifier | 2.397 | 0.471 | **−86.9%** (much worse) |
| ConceptGrade (full, with Verifier) | 1.177 | 0.784 | +8.2% |

The knowledge graph comparison — the architecture's namesake mechanism — is **dramatically worse than the baseline in isolation**. Essentially all of the measured gain comes from the LLM Verifier's own holistic judgment, not from KG grounding. A leave-one-question-out cross-validation of the Verifier-weight hyperparameter confirms the deployed configuration (discard KG score entirely, w=1.0) is chosen on every fold — not an artifact of tuning on the evaluation data.

## 6. Self-Consistency Ensembling: the main proposed fix

Hypothesis: single-call judgments are noisy; averaging K=7 independent gradings (temperature=0.7, mean-aggregated) should reduce that noise.

**Against a single-call baseline**, this looked like the strongest result in the whole project: every leave-one-question-out fold significant at both tails on Mohler (50/50) and DigiKlausur (17/17), and Pearson correlation exceeding baseline on both.

**This did not survive a fair-control check.** A single-call baseline is the wrong control for a 7x-resourced system. Re-running C_LLM with the identical 7x/temperature-0.7/mean-aggregation treatment and comparing head-to-head:

| Dataset | MAE gap | Cluster p (2-tailed) | LOOCV (1T/2T) | r vs. C_LLM×7 |
|---|---|---|---|---|
| Mohler (46q) | +7.0% (p<0.0001) | 0.256 (n.s.) | 0/46, 0/46 | 0.797 vs. 0.790 (holds, barely) |
| DigiKlausur (17q) | +6.4% (p=0.0006) | 0.089 (n.s.) | 5/17, 2/17 | 0.727 vs. **0.735** (reverses) |

The response-level MAE gap survives on both datasets. The question-level robustness that made this look like the paper's strongest result **collapses completely on Mohler and erodes substantially on DigiKlausur**, and on DigiKlausur the correlation advantage **reverses** — plain self-consistency on the baseline alone beats the full architecture on that metric.

This fair-control check was itself prompted by asking "what would a skeptical reviewer say" about the original claim — not discovered by extending the original experiment.

## 7. A further wrinkle: statistical model choice changes the verdict again

The above significance tests used a cluster-mean paired Wilcoxon test (collapse each question to one mean-error value, test on those means). This discards within-question sample size and variance. Re-running the same comparisons with a linear mixed-effects model (random intercept per question, using every response-level data point) gives a different picture:

| Comparison | Cluster-Wilcoxon p | **LMM (LRT) p** |
|---|---|---|
| Mohler headline | 0.111 (n.s.) | **0.0032 (significant)** |
| Mohler fair control | 0.256 (n.s.) | **0.0125 (significant)** |
| Mohler combined 50q headline | 0.0657 (n.s.) | **0.0023 (significant)** |
| **DigiKlausur headline** | **0.0489 (significant)** | **0.2471 (n.s.)** |
| DigiKlausur fair control | 0.089 (n.s.) | 0.1017 (n.s.) |
| Kaggle ASAG headline | 0.702 (n.s.) | 0.930 (n.s.) |

All six models converged cleanly (checked explicitly, not assumed). This is **not uniformly favorable**: Mohler's results become substantially more robust under the more appropriate statistical model, but DigiKlausur's headline result — one of only two "significant" cross-dataset findings in the project — **loses significance** under the same model choice. This has not yet been integrated into the two working papers as of this document's writing.

## 8. Cross-Dataset Boundary (Kaggle ASAG)

Concept extraction returns empty KG matches for 100% of Kaggle ASAG samples (elementary science vocabulary has essentially zero overlap with the Data-Structures KG). Self-consistency shows no benefit there under any test, at any K. This is treated as a mechanistically-predicted architectural boundary, not an unexplained failure — arguably the most scientifically clean finding in the project.

## 9. Known, Explicitly Undone Work

- **KG-grounding failure is diagnosed but not fixed.** No redesigned comparator (e.g., soft/semantic matching instead of rigid concept-ID matching) has been attempted, despite qualitative evidence (from a manually-identified Mohler question-extension exercise) that literal-keyword-based domain matching misses conceptually-relevant answers.
- **Single model family** (`gemini-2.5-flash`) throughout. No GPT-4/Claude/open-weight comparison.
- **No human/educator validation.** A companion paper's user study is placeholder/projected data, not real participant data.
- **DigiKlausur and Kaggle ASAG provenance** were never independently forensically verified the way the fabricated Mohler fixture was caught and Mohler's real replacement was verified.
- **Statistical framework choice (Wilcoxon vs. LMM) materially changes conclusions** and has not yet been resolved as the paper's primary reported test.
- **Underpowered question-level clusters**: 17–50 questions per dataset is thin for cluster-robust inference regardless of test choice.

## 10. What the Student Believes This Supports

A response-level-significant, mechanistically-explained, honestly-bounded improvement over an identical-model LLM baseline, driven by an LLM Verifier rather than the KG-grounding the architecture is named for, robust on Mohler under a more appropriate statistical model, weaker or reversed on a second dataset depending on test choice, and absent by architectural prediction on a third. The student does **not** believe this currently supports an unqualified "ConceptGrade beats LLM grading" claim, and has explicitly declined to state it that way even when it would have been easier.

---

## Review Request

Please give a direct verdict:
1. **As a single conference/workshop paper** (e.g., BEA, AIED, EDM, LAK, or a mid-tier NLP venue) — accept, reject, or major/minor revision? Why?
2. **As a PhD dissertation contribution (one chapter of several, or the core of the whole thesis)** — sufficient, insufficient, or "sufficient only if X is added"? Name X specifically.
3. **Rank the open items in Section 9** by which would most change your verdict if resolved, and which are optional polish.
4. Is there anything in Sections 4–7 that reads as **methodologically unsound**, as opposed to merely limited in scope? Please flag it specifically rather than generally.
