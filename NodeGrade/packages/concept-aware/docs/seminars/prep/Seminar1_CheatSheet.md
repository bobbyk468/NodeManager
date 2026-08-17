# Seminar 1 Cheat Sheet — ConceptGrade System Design
*One page. Glance during Q&A, don't read from it.*

## Thesis (say this exactly, more than once)
"An empirical study of where and why KG-LLM hybrid grading helps — not a claim
that it always does."

## The five layers, one line each
1. **Concept Extraction** — `gemini-2.5-flash`, 3× self-consistency, min_votes 2/3,
   confidence τ=0.70, alias lookup to canonical KG IDs.
2. **KG Comparison** — deterministic, LLM-free, no model calls.
   coverage = |Vₛ∩Vₑ|/|Vₑ|  ·  accuracy = correct edges/student edges  ·
   integration = connected nodes/student nodes.
3. **Cognitive Depth** — Bloom's (1–6) + SOLO (1–5).
   depth = 0.55·blooms_norm + 0.45·solo_norm.
4. **Misconception Detection** — 16-entry validated taxonomy, severity + remediation
   hint per entry (e.g. DS-STACK-01: LIFO/FIFO confusion).
5. **Score Synthesis + Verifier**:
   knowledge = 0.45·cov + 0.35·acc + 0.20·int
   s_kg = (0.60·knowledge + 0.40·depth) × (1 − p_misc)
   **final = (1−w)·s_kg + w·verified, w = 1.0 at deployment**
   → the Verifier's judgment fully drives the score; s_kg is context, not arithmetic.

## Expert KG
101 concepts · 138 typed relationships · 8 semantic types · **frozen before evaluation**.
Design rules: pedagogical coverage, canonical IDs + aliases, typed (not generic) edges.

## TRM (Topological Reasoning Mapping)
Approximate subgraph matching, **not** NP-hard subgraph isomorphism.
Concept alignment (BERT cosine, τ=0.70) → relationship matching (1.0/0.5/0.0) →
verifier confidence weighting (1.0 grounded / 0.3 hallucinated-looking).
Complexity: O(|Vₛ|·|Vₑ| + |Eₛ|·|Eₑ|) — polynomial. **~2.3 sec/answer**, standard CPU, batch.

## Prior-work landmarks (Slide 3)
Lexical/LSA r=0.493 [1] · Dependency graphs r=0.518 [2] · BERT fine-tune F1 gain on
SemEval, not a Mohler r (Sung et al. 2019 [4]) · LLM zero-shot: competitive but no
explicit conceptual record. Full citations verified + printed on Slide 17.

## If asked about the BERT box specifically
The original citation there was unverifiable (wrong paper, didn't exist) — found and
corrected to the real Sung et al. 2019 paper, which reports F1 on SemEval, not a
Mohler r. Say this plainly if asked; it's a disclosed correction, not a gap to hide.

## Cost / call count
**~7 LLM calls per graded response** (3 extraction + 1 depth + 2 misconception +
1 verifier) vs. **1 call** for the zero-shot baseline. Disclosed tradeoff, not hidden.

## Disclosed limitations (say plainly, no hedging)
- Single model family (`gemini-2.5-flash` only, no cross-model validation).
- Single-author KG + taxonomy. Machine-IRR κ=0.54 (moderate) — **self-administered
  lower bound, not external validation.**
- Domain specificity — Data Structures only. A second Programming/OOP KG exists
  (62 concepts, 116 relationships) but is unevaluated.

## The one hard question you WILL get
**"KG score alone is worse than baseline — is this just an LLM grader with extra
steps?"**
→ No, not entirely: Layer 2's scores drive the structured feedback (Slide 14),
independent of the numeric grade. But yes, it's a fair challenge to the paper's
framing — the honest reframe is *KG-grounded explanation*, not yet *KG-driven
accuracy*. Whether kg_score can be made more predictive is open future work.

## Forward pointers (use these to defer results questions cleanly)
- "That's the evaluation — Seminar 2." (any accuracy/significance question)
- "That's the diagnostic deep-dive — Seminar 3." (any bug/audit-process question)
- Three questions Seminar 2 explicitly answers (read verbatim if useful):
  1. Does ConceptGrade really beat a zero-shot LLM baseline?
  2. Why does the raw KG-grounded score perform 86.9% worse than baseline alone?
  3. Self-consistency looked strongest — what happened when tested fairly?

## Numbers to never round up
- κ = 0.54 → say "moderate," not "good."
- w = 1.0 → say "entirely replaces," not "mostly."
- Machine-IRR → say "self-administered lower bound," never "validated."
