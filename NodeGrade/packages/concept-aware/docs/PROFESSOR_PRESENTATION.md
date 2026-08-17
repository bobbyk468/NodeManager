# ConceptGrade — Professor Presentation Notes
## Two Papers, One System: From Automated Grading to Visual Understanding

**Prepared by:** Brahmaji Katragadda  
**Date:** April 2026 (Paper 1 numbers refreshed August 2026)  
**Audience:** Professor review / research discussion

---

**Note on this revision.** An earlier draft of Paper 1 (and this notes
document) reported headline numbers computed on a fabricated 120-sample
fixture, discovered and retracted mid-project. This document has been
updated to report only the real, corrected results (Mohler et al. 2011,
$n=1{,}262$ responses across 46 questions). The full incident record is
in `REPRODUCIBILITY.md`; the corrected numbers below are weaker and more
qualified than the originals, which is itself part of what I'd want to
walk the professor through.

---

## The Big Picture (One Paragraph)

When a student writes a short answer about how a binary search tree works, a human instructor reads it and immediately knows which concepts are there, which are missing, and whether the student actually *understands* the material or is just copying words. Current automated grading tools can give a score, but they cannot do this. They either count word matches (too shallow) or ask a large language model for a grade (accurate but a black box). My research builds a system that grades the way a knowledgeable instructor would — by explicitly checking which concepts the student demonstrated — and then shows the instructor a visual interface so they can audit, trust, and improve the grading themselves.

This work is split into two papers:
- **Paper 1** proves the underlying grading approach is accurate.
- **Paper 2** builds the visual interface on top of it and runs a user study with educators.

---

---

# PAPER 1 — Concept-Aware Automated Grading

## Why I Chose This Topic

When I started looking at automated short answer grading (ASAG) in Computer Science education, I noticed a gap that surprised me. There are decent systems for grading English essays, science questions, and even some CS quizzes. But when you look at what they actually do, they are measuring one thing: *how similar does the student's answer look to the model answer?*

This works reasonably well for factual questions. If the answer is "Paris," you only need to match "Paris." But CS education does not work like that. Consider these two student answers to the question *"What is a stack?"*

- **Student A:** "A stack is a data structure that uses last-in first-out ordering, where push adds to the top and pop removes from the top."
- **Student B:** "A stack is basically like a pile of dishes. You can only take from the top, and you add to the top too."

Both students understand stacks. Student A uses textbook vocabulary. Student B uses an analogy. A word-matching system scores Student B very low because there is no overlap with the model answer. An embedding-based system does better but still cannot tell you *which* concepts Student B demonstrated and which are missing.

More importantly, neither approach can answer the question an instructor actually needs answered: **"This student got a 2 out of 5 — what specifically do they understand and what don't they?"** Without that breakdown, automated grading is just a number, and instructors cannot act on it.

That is the gap my first paper targets.

---

## What I Built (Paper 1)

I built **ConceptGrade**, a five-layer system that grades CS short answers by explicitly representing and comparing *concepts* rather than words.

The core idea is simple: instead of comparing the student's answer directly to a model answer, I first convert both into a graph of concepts, and then compare those graphs. If the student's concept graph covers most of what the expert's concept graph contains, they get a high score.

### The Five Layers

Here is what the system does, step by step:

**Layer 1 — Concept Extraction:**
The student's free-text answer goes through a large language model (`gemini-2.5-flash`, via the Google Generative AI batch API — the same model used everywhere else in the pipeline and for the baseline, so model choice never confounds the comparison). The LLM's job is not to grade — it is to extract a structured list of concepts and relationships from the answer. For example, from Student B's "pile of dishes" answer, the LLM would extract: `stack`, `last-in-first-out`, `top`, `add-to-top`, `remove-from-top`. These become the nodes and edges of what I call the **Student Concept Graph**. The reported configuration runs this extraction three times with self-consistency majority-voting.

**Layer 2 — Knowledge Graph Comparison:**
I manually built an expert **Domain Knowledge Graph (KG)** for Computer Science Data Structures. It has 101 concepts (like `stack`, `queue`, `binary_search_tree`, `merge_sort`) and 138 relationships between them (like *"stack has\_property LIFO"*, *"heap\_sort uses heap"*). The system compares the Student Concept Graph against this expert KG and computes three scores:
- **Coverage** — what fraction of the relevant expert concepts did the student mention?
- **Integration** — are the student's concepts connected to each other, or just a list?
- **Accuracy** — are the relationships the student stated actually correct?

**Layer 3 — Cognitive Depth:**
Using Bloom's Taxonomy (Remember → Understand → Apply → Analyze → Evaluate → Create) and SOLO Taxonomy (from fragmented responses to fully integrated responses), the system classifies how deeply the student understands the topic — not just whether they mentioned the right words.

**Layer 4 — Misconception Detection:**
The system checks the student's concept graph against a taxonomy of 16 known CS misconceptions. For example, *"confusing LIFO with FIFO in a stack"* (DS-STACK-01) or *"thinking BST search is O(n²)"*. If detected, the student gets a flag and a specific remediation hint.

**Layer 5 — Score Synthesis and Verification:**
The coverage/accuracy/integration scores and the depth scores are first combined into a deterministic KG-formula score ($s_{\text{kg}}$: 45% coverage + 35% accuracy + 20% integration, blended 60/40 with a Bloom's/SOLO depth score, then discounted by a misconception penalty). This is blended with a holistic, KG-evidence-informed LLM score at a 5%/95% weight — so $s_{\text{kg}}$ already has only a small mathematical say. That blended score is then passed to an independent LLM-as-judge **Verifier**, and in the deployed configuration the Verifier's own score entirely replaces it ($w=1.0$). I want to flag this plainly rather than bury it: **the KG-grounded formula score, on its own, turns out to be a substantially worse predictor than the zero-shot baseline** (see the ablation finding below). Almost all of ConceptGrade's real accuracy comes from the Verifier stage, not from the deterministic KG-comparison the system is named for.

### The Knowledge Graph — Why I Built It Manually

I want to be honest here: building the expert KG took significant effort. I did not generate it automatically. I curated 101 concepts and 138 typed relationships by hand, following CS education ontology principles. This was intentional. Automatically generated KGs from text tend to be noisy and inconsistent. For grading to be trustworthy, the reference KG needs to be correct. The KG covers eight concept types (algorithms, data structures, abstract concepts, properties, operations, complexity classes, programming constructs, design patterns) and nine relationship types (is-a, has-property, uses, has-complexity, prerequisite-for, variant-of, implements, contrasts-with, has-part). Every edge has a semantic type, not just a generic "related to" link.

---

## How I Evaluated It

**Dataset:** I use the Mohler et al. (2011) benchmark, the standard dataset for CS short-answer grading. The full benchmark has 630 responses across 87 questions; I evaluate on the KG-aligned subset my expert Data Structures knowledge graph actually covers — 1,262 responses across 46 questions, each graded by two human annotators on a 0–5 scale, evaluated as one full sample (no held-out split; the pipeline's hyperparameters were fixed before I touched this data).

**Comparison:** I compared ConceptGrade against an LLM zero-shot baseline using the *identical* underlying model (`gemini-2.5-flash`, same temperature, same rubric) — asking it directly "grade this answer from 0–5" with no concept extraction or KG comparison. Using the same model for both sides rules out model capability as a confound, but it does not by itself rule out a tuning-budget asymmetry: ConceptGrade's synthesis weights were tuned on a development split, and the baseline received no equivalent tuning. I disclose this openly in the paper's limitations rather than let the headline number imply a cleaner comparison than it is.

**Results:**

| What I Measured | LLM Baseline | ConceptGrade | Change |
|-----------------|-------------|--------------|--------|
| Mean Absolute Error (MAE) | 1.282 | 1.177 | **↓ 8.2%** (response-level $p<0.0001$) |
| Pearson correlation (r) | 0.790 | 0.784 | **worse**, not better |
| Quadratic Weighted Kappa | 0.501 | 0.524 | ↑ |
| Question-clustered significance | — | $p = 0.111$ two-tailed / $0.056$ one-tailed | marginal, not clean |

I want to be direct with the professor about how to read this table: an 8.2% MAE reduction is real and significant at the response level, but once responses are grouped by question (46 clusters, since answers to the same question aren't independent draws), the result only reaches one-tailed significance, and only 17 of 46 leave-one-question-out folds hold up. Pearson correlation is actually *worse* for ConceptGrade than for the plain baseline. This is a genuinely mixed, modest result — not the clean win an earlier, since-retracted version of this analysis reported.

**The most important finding** came from a real-data 3-condition ablation, not from removing components one at a time. Isolating the deterministic, pre-verifier KG-formula score (`kg_score`) and comparing it against both the full pipeline and the zero-shot baseline shows: `kg_score` alone has MAE $= 2.397$ — **86.9% *worse* than the zero-shot baseline's $1.282$**, question-clustered $p<0.0001$. The full pipeline's accuracy (MAE $=1.177$) is recovered almost entirely by the Verifier stage, not by the knowledge-graph grounding the system is named for. This is the single most important thing I'd want the professor to take away from Paper 1: it's an honest architectural finding about *where the accuracy actually comes from*, and it complicates the paper's own framing.

I also compared against a call-budget-matched baseline (`C_LLM×7`, giving the baseline the same 7 LLM calls per response that the full ConceptGrade pipeline uses): ConceptGrade still wins by 4.4% MAE at the response level ($p=0.0053$), but that result is *not* significant once clustered by question ($p=0.4219$, winning only 25 of 46 questions — barely above chance).

I also tested ConceptGrade on two other datasets:
- **DigiKlausur** (646 neural network exam answers from Germany): smaller but real improvement, 4.9% MAE reduction, $p = 0.049$
- **Kaggle ASAG** (368 elementary science answers): no significant gain, $p = 0.702$ — concept extraction returns zero KG matches for 100% of these samples, because the KG's vocabulary doesn't cover elementary-science phrasing at all

The Kaggle null result is not a failure — it's diagnostic. It tells me KG-based grading works only when the domain vocabulary is actually covered by the knowledge graph (CS, neural networks); when students write in vocabulary the KG was never built for, there's nothing for the system to anchor to. That's the honest boundary of where this approach applies, and it's a boundary the effect size tracks cleanly across all three datasets (8.2% → 4.9% → 0.6%, roughly tracking domain overlap with the KG).

---

## What I Proved (Paper 1 Conclusion)

1. A concept-aware grading system gives a small, response-level-significant but question-level-fragile improvement over an identical-model LLM zero-shot baseline on real Mohler data (8.2% MAE reduction, $p<0.0001$ response-level / $p=0.056$ one-tailed question-clustered) — not the clean, strongly significant result an earlier, retracted analysis reported.
2. That gain comes almost entirely from the Verifier's holistic LLM judgment, **not** from the deterministic KG-comparison score — which, tested alone, is 86.9% worse than the baseline. This is a real limitation of the current architecture, disclosed rather than hidden.
3. The system produces structured, actionable feedback ("You demonstrated: stack, LIFO. Missing: push_operation, pop_operation, time complexity") that no score-only system can provide, independent of whether the numeric score itself beats the baseline by a wide margin.
4. KG-based grading generalizes to adjacent domains (neural networks, smaller effect) but reaches a hard boundary at domains outside the KG's vocabulary (elementary science, no effect) — the effect size tracks how well the KG covers the domain.

Paper 1's real-data results, the fabrication incident, and the full validation history are documented in `REPRODUCIBILITY.md`. The manuscript (`ConceptGrade_FullPaper.tex`) is drafted and compiles cleanly; I'd frame it to the professor as an honest, boundary-finding paper rather than a clean accuracy win.

---
---

# PAPER 2 — Visual Analytics Dashboard for Human-AI Co-Auditing

## Why I Chose This Topic

After building Paper 1, I had a working grading system. But I ran into a practical problem: **instructors do not trust it.**

This is not an irrational position. Here is how an instructor typically sees an automated grading system: a student submits an answer, a black box produces a number, and the instructor is supposed to accept it. Even if the system is accurate on average, the instructor has no way to verify whether a specific grade is correct. Was the grade low because the student missed a key concept, or because the LLM misread the answer? There is no way to know.

This is a genuine problem for adoption in real classrooms. Instructors want to be in control. They want to be able to audit the system, override grades they disagree with, and most importantly, understand *why* a student got a particular score so they can give meaningful feedback.

I also noticed something deeper: even when I show an instructor the LLM's chain-of-thought reasoning (the step-by-step explanation the model generates), they cannot easily audit it. An LLM reasoning chain is a paragraph of text. It does not map clearly onto what the instructor knows about the domain. A CS instructor looking at an LLM's explanation of why a student got 2/5 on a BST question cannot easily see: "Did the model's reasoning follow the logical structure of CS knowledge? Did it check prerequisites? Did it correctly identify which concepts the student missed?"

The gap is not a model accuracy problem — it is a *visualization* problem. The instructor needs to see the model's reasoning projected onto their own mental map of the domain (the knowledge graph), not as a wall of text.

That is the motivation for Paper 2.

---

## What I Built (Paper 2)

I built **ConceptGrade Dashboard**, an interactive visual analytics system that lets instructors co-audit both the AI's reasoning and the student's conceptual gaps simultaneously.

The key technical concept I introduced is **Topological Reasoning Mapping (TRM)**. The idea is: when an LLM generates a reasoning chain ("The student mentions sorting, so I check whether they covered time complexity, then whether they connected it to the algorithm they described..."), each step in that chain should map to adjacent concepts in the knowledge graph. If the LLM jumps from "sorting" to "memory allocation" without a logical connection in the KG, that is a **structural leap** — a warning sign that the reasoning may be flawed or hallucinated.

TRM gives instructors a way to check: does this AI reasoning follow the logical structure of CS, or is it jumping around?

### The Dashboard — Five Panels

When an instructor opens the dashboard, they see five linked panels:

**Panel 1 — Misconception Heatmap:**
A grid where rows are concepts (like "binary search tree," "time complexity") and columns are types of errors. Brighter cells mean more students struggled with that concept. This is the instructor's starting point — a class-level overview of where students are falling behind.

**Panel 2 — Student Radar Chart:**
A radar plot showing how student performance distributes across concepts. The instructor can drag to select a group of low-performing students, and the other panels automatically filter to show only those students.

**Panel 3 — Knowledge Graph Subgraph Panel:**
When the instructor clicks a concept in the heatmap, this panel shows that concept's neighborhood in the expert KG — prerequisites, related concepts, common misconceptions. Nodes are color-coded: green if the student covered them, red if the student missed them. This directly answers: *"What did the student need to know?"*

**Panel 4 — Verifier Reasoning Trace:**
This is where TRM shows up. For the selected student, this panel shows the AI's step-by-step reasoning. Each step is a card. Between cards, if the AI jumped between two unrelated parts of the KG, an amber "structural leap" badge appears. Hovering over a step highlights the corresponding KG nodes in Panel 3. The instructor can literally follow the AI's reasoning through the knowledge graph.

**Panel 5 — Rubric Editor:**
The instructor can add or refine grading criteria. The key interaction: when the instructor sees a CONTRADICTS step in Panel 4 — meaning the AI found a concept in the student's answer that the rubric did not anticipate — they can click "Add to Rubric" and the rubric is automatically populated with that concept's exact KG label. No typing, no ambiguity. This is called **Click-to-Add**.

### Why This Matters: The Epistemic Update

The most important moment in the dashboard interaction is this sequence:
1. Instructor sees a student who got a low grade.
2. Instructor looks at the Verifier Trace and spots a "CONTRADICTS" step — the AI found that the student mentioned a concept that *conflicts* with the rubric's expected answer.
3. Instructor thinks: "Wait, this student is actually right. My rubric didn't account for this approach."
4. Instructor clicks "Add to Rubric."

When this happens, the instructor has not just validated a grade. They have **updated their own understanding** of what students know and how they reason. Their rubric becomes richer, more precise, and better calibrated to actual student thinking. I call this a *bidirectional epistemic update*: the AI's reasoning changes the instructor's model of the domain, not just their confidence in a single grade.

### What Makes This a Visual Analytics Problem

The dashboard is not just a reporting tool. All five panels are linked. Clicking anything in one panel filters all other panels. This is called **bidirectional brushing**:
- Click a concept in the heatmap → all student answers filter to those who missed that concept
- Drag a region in the Radar → the answer panel shows only those students
- Click a KG node → the Verifier Trace highlights only steps that reference that node
- Click a step in the Trace → the KG panel highlights the corresponding nodes

No single panel is sufficient. The power comes from exploring across panels together. An instructor looking only at the heatmap sees *where* students struggle. Looking at the KG panel adds *why* (the prerequisite structure). Looking at the Verifier Trace adds *how* the AI evaluated the specific student's reasoning. The rubric editor turns insight into action.

### How I Handle the AI's Failure Mode

One important design decision: I do not hide the AI's limitations. When the AI's reasoning chain has zero concept anchors — meaning it generated a reasoning chain that does not reference any node in the KG — I show a prominent warning banner: *"No Domain Grounding — All reasoning steps lack KG concept anchors. Structural leap detection is disabled for this trace."*

In fact, I discovered that 97.7% of traces from one of the LLMs I tested (DeepSeek-R1 on neural network questions) had zero grounding. Rather than showing a misleadingly clean interface, I surface this degeneracy explicitly. Instructors should know when the AI is reasoning in a domain-irrelevant way.

This is a deliberate design philosophy: an XAI system should expose its limits as clearly as its strengths.

---

## How I'm Evaluating It (User Study Design)

Paper 2 includes a controlled user study with N=30 domain-expert educators. The study is IRB-pending; this section explains the design.

**Two Conditions:**
- **Condition A (Control):** The instructor sees summary statistics (total answers graded, MAE, statistical significance p-value). They know the AI system is accurate. What they do *not* have is any visual reasoning evidence — no Trace panel, no KG panel, no Click-to-Add.
- **Condition B (Treatment):** The instructor has access to the full five-panel dashboard.

**Why this design?** A common flaw in XAI user studies is comparing "AI with explanation" to "no AI at all." That is not a fair test — of course people do better when they have more information. In my design, both conditions get the same quantitative AI evidence (the p-value and MAE). The only difference is whether they have *visual reasoning evidence* or not. This means any performance difference between conditions is attributable specifically to the visual design — not just to AI being present.

**What I Measure:**
- **H1 — Causal Attribution (CA):** Did the instructor trace their rubric change to a specific visual artifact? (e.g., "I added this criterion because I saw the CONTRADICTS step at the time-complexity node")
- **H2 — Semantic Alignment (SA):** How closely does the rubric the instructor wrote match the concepts actually in the KG?
- **H3 — Trust Calibration (TC):** After seeing the dashboard, do instructors express more accurate confidence in their grade assessments?
- **SUS Score:** Is the system usable? (Standard System Usability Scale questionnaire)
- **Dwell time:** How long do instructors spend on benchmark "trap" answers — student responses I injected silently into the study that represent known edge cases (Fluent Hallucination, Unorthodox Genius, Lexical Bluffer, Partial Credit Needle).

**Benchmark Trap Cases:** I selected 8 student answers from the dataset that represent pedagogically tricky situations where an instructor is likely to misjudge without visual support. These are silently seeded into the study — the instructor does not know which answers are "traps." I measure whether Condition B instructors spend more time on these answers and make more accurate judgments than Condition A instructors.

---

## Technical Architecture

The system is built as a web application:
- **Backend:** NestJS (TypeScript) — serves the dataset, manages event logs, handles API calls to the analysis pipeline
- **Frontend:** React + Vite (TypeScript) — the interactive dashboard
- **Analysis Pipeline:** Python — runs ConceptGrade scoring, TRM computation, and statistical analysis
- **Event Logging:** Every interaction (heatmap click, rubric edit, time spent on an answer) is logged to JSONL files with millisecond timestamps for the user study analysis

The event logging is FERPA-compliant: student answer text is never stored in the logs. Only an FNV-1a hash of the text is recorded, which is non-reversible and serves only for deduplication.

---

## Current Status of Paper 2

Everything is built and tested:
- ✅ Dashboard functional with all five panels and bidirectional brushing
- ✅ TRM logic implemented, zero-grounding warning added
- ✅ Event logging with FERPA-compliant hashing
- ✅ Analysis pipeline ready (8 pre-registered hypotheses tested)
- ✅ LaTeX draft complete (methodology, system design, related work, evaluation design)
- ⏳ IRB approval pending — this is the only blocker for running the study
- ⏳ N=30 user study data collection (May–August 2026 target)
- ⏳ Writing §5.2 and §5.3 (results sections, after data collection)

---

## What I Will Prove (Paper 2 Expected Contribution)

1. TRM is a new technique for auditing AI reasoning chains against domain structure — it detects hallucinations and ungrounded reasoning in a way that text alone cannot.
2. The bidirectional brushing interface enables instructors to locate misconceptions, trace them to specific student answers, and understand the AI's reasoning — all in a single workflow.
3. The Click-to-Add interaction operationalizes "epistemic update" as a measurable event — it is the moment when the AI changes the instructor's model of the domain, not just their confidence in a grade.
4. Condition B will outperform Condition A on causal attribution and semantic alignment — proving that the visual reasoning components specifically (not just AI awareness) drive the improvement.

---

---

# Connecting the Two Papers

The relationship between the papers is important to state clearly for a professor:

**Paper 1** answers the question: *Can a knowledge graph–driven system grade CS answers better than an LLM alone, and where does that break down?* The answer is: a small, real, response-level-significant gain (8.2% MAE reduction, $p<0.0001$) that is only marginal once question-clustering is accounted for, and that comes mostly from the Verifier stage rather than the KG-grounding itself. This establishes what the system can and can't yet claim — not a clean "the model is sound" result.

**Paper 2** answers a different question: *Given that the model is accurate, how do you get instructors to actually use and trust it?* The answer is: give them a visual interface that projects the model's reasoning onto their own domain knowledge, so they can audit it, understand it, and improve it.

Paper 2 explicitly relies on Paper 1's result. By citing Paper 1 in the related work section of Paper 2, I can tell IEEE VIS reviewers: "The underlying ML accuracy is established elsewhere. This paper is about the human-computer interaction problem — not whether the model is right, but whether instructors can audit, understand, and act on what it produces."

This separation is intentional. ASAG accuracy and VA system design are different research questions, and they belong in different venues:
- Paper 1 → NLP / Educational AI venue (e.g., AIED, ACL-EdNLP, EMNLP)
- Paper 2 → IEEE VIS 2027 VAST track

---

# Key Numbers to Remember

| Metric | Value |
|--------|-------|
| KG size (Data Structures) | 101 concepts, 138 relationships |
| Benchmark size (real, KG-aligned) | 1,262 responses, 46 questions (Mohler 2011) |
| MAE reduction vs. LLM baseline | **8.2%** (response-level $p<0.0001$; question-clustered $p=0.111$ two-tailed / $0.056$ one-tailed) |
| Pearson r vs. baseline | 0.784 vs. 0.790 — **worse**, not better |
| Where the gain actually comes from | The Verifier stage; the deterministic KG-formula score alone is 86.9% *worse* than baseline |
| Cross-dataset: DigiKlausur (NN) | Significant, smaller effect (4.9% MAE reduction, p = 0.049) |
| Cross-dataset: Kaggle ASAG (Science) | Not significant (p = 0.702) — 0% KG concept matches, boundary condition |
| Call-budget-matched comparison | ConceptGrade still wins response-level (+4.4%, p=0.0053), not question-clustered (p=0.4219) |
| User study size (Paper 2) | N = 30 educators, 2 conditions |
| Zero-grounding rate (DeepSeek-R1) | 97.7% of traces |
| Fabrication incident | Retracted; see `REPRODUCIBILITY.md` for the full record |

---

# Questions I Expect From the Professor

**Q: If the KG-formula score alone is worse than the baseline, what is the knowledge graph actually contributing?**
A: Right now, less than the paper's title implies — this is the finding I'd lead with, not bury. The KG-comparison score feeds into the pipeline as evidence for the Verifier's holistic judgment (and produces the structured, per-concept feedback instructors see — Layer 2's output, not its numeric score, is what's useful downstream), but as a standalone predictor it's 86.9% worse than just asking the LLM directly. I see two honest paths forward: reframe the contribution around structured feedback and interpretability rather than raw accuracy, or invest in making the deterministic KG score itself more predictive before claiming an accuracy win from it.

**Q: An earlier version of this work used fabricated data — what happened, and why should I trust the new numbers?**
A: I found, during a routine reproducibility check, that some headline numbers had been computed on a fabricated 120-sample fixture instead of the real Mohler dataset. I retracted every affected claim rather than quietly replacing it, re-ran everything on the real 1,262-sample data, and kept the retracted material in the paper's appendix — labeled, not deleted — as part of the record. The new numbers are weaker and more heavily caveated than the originals, which is itself evidence they weren't picked to look good; the full incident timeline and verification scripts are in `REPRODUCIBILITY.md`.

**Q: Why not just fine-tune an LLM on the grading dataset instead of building all this?**
A: Fine-tuning can improve accuracy, but it makes the system even more opaque — you get a number with no explanation of *why*. My approach sacrifices some raw accuracy potential in exchange for interpretability and structured feedback. For educational applications, interpretability is not a nice-to-have; it is the whole point.

**Q: The KG is manual — doesn't that limit scalability?**
A: Yes, and I acknowledge this in the paper. Building the KG took time. But the cost is one-time, and the KG is reusable across all questions in the same domain. I have already built a second KG for Object-Oriented Programming (62 concepts, 116 relationships). Automated KG construction is future work, but for a published system, the accuracy of a manually-curated KG is worth the construction cost.

**Q: Why IEEE VIS for Paper 2 — isn't this more of an HCI or education paper?**
A: IEEE VIS VAST track specifically focuses on visual analytics systems — AI-human collaboration through visualization. The bidirectional brushing architecture, the TRM formal model, and the coordinated multiple views design are all standard VA contributions. The education domain is the application, but the visual design and interaction model are the research.

**Q: The user study hasn't run yet — can you submit Paper 2?**
A: Not yet. The user study results are clearly marked as pending in the current draft. The submission timeline is: IRB approval → data collection (May–August 2026) → analysis and writing → IEEE VIS 2027 deadline (typically October–November 2026). I have roughly 18 months from now, which is enough time.

**Q: What happens if the user study doesn't show significant results?**
A: The null result would still be publishable with the right framing. If Condition B does not outperform Condition A, that tells us the visual design specifically does not add value beyond knowing the AI is accurate — which is itself a useful finding for the VA and educational AI communities. The pre-registered analysis plan ensures the study is scientifically valid regardless of outcome.

---

*End of presentation notes.*
