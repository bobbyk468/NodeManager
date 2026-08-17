# Seminar 1 — Presentation Script & Q&A Prep
## ConceptGrade: System Design & Motivation

**Slot:** 30–40 min, faculty + research committee, substantial open Q&A expected.
**Target talk length:** ~22–24 min, leaving 10–18 min for Q&A.
**Deck:** `Seminar1_SystemDesign.pptx` (16 slides).

---

## How to use this document

Each slide has: a **spoken script** (say it in your own words, don't read verbatim),
a **timing budget**, and a **transition line** into the next slide. Rehearse out loud
at least twice against a timer before the real thing — this script runs long on paper
and short in practice, or vice versa, and you won't know which until you say it out loud.

The committee already knows you found and fixed a fabrication issue somewhere in this
project (it's in your reproducibility record). Don't over-apologize for it if it comes
up — the honest framing throughout this deck (the "86.9% worse alone" finding on Slide 12,
the disclosed limitations on Slide 15) *is* the answer to "can I trust these numbers,"
so let the deck's own honesty do the work.

---

## Slide 1 — Title (0:30)

**Say:** State the title, that this is Seminar 1 of 3 (System Design), and one sentence
on what the other two cover — "Today is architecture and design decisions; Seminar 2 is
the empirical evaluation; Seminar 3 is a diagnostic deep-dive into where the system's
scoring broke and what we did about it." This sets committee expectations so nobody asks
"but does it work?" prematurely — you can point forward to Seminar 2 without dodging.

**Transition:** "Let me start with the problem this is actually solving."

---

## Slide 2 — The Problem (2:00)

**Say:**
- Manual grading of CS short-answers doesn't scale — large classes, delayed feedback,
  inconsistent graders.
- Two things prior automated approaches get wrong, not one:
  1. **Score without explanation** — lexical, embedding, and LLM zero-shot graders
     output a number, not *which concepts* were understood.
  2. **No record of misconceptions** — a grade alone can't tell an instructor a student
     confused LIFO with FIFO, versus never engaging with the concept at all.
- ConceptGrade's premise: treat grading as a **knowledge-graph matching task** — convert
  each free-text answer into a typed concept graph, compare it against an expert domain
  graph. That comparison is what makes the explanation and the misconception record
  possible — they're not bolted on afterward, they fall out of the representation choice.

**Anticipate:** "Why is this a graph problem and not just a classification problem?"
→ Because the *output* needs to be structured (which concepts, which relationships) for
the explanation to exist. A classifier gives you a label; a graph comparison gives you a
diff.

**Transition:** "This isn't a new idea in education research — it's called concept-map
assessment. Here's where ConceptGrade sits relative to what's been tried."

---

## Slide 3 — What Prior Approaches Miss (2:30)

**Framing to say before touching any box:** "r" is Pearson correlation — how closely a
grading system's scores track a real human grader's, from 0 (no relationship) to 1
(perfect match). Three of the four boxes carry an r-number; the fourth doesn't, and
I'll explain why when I get there.

**Box 1 — Lexical/LSA (Mohler & Mihalcea), r = 0.493.** The oldest, simplest automated
grader — checks whether the student's answer contains the same words as the reference
answer, plus LSA, a technique that can notice when different words tend to mean similar
things. 0.493 is the weakest of the three r-numbers on the slide: plain word-matching is
the least accurate approach. Caption — "Surface overlap only, no concept structure":
it only looks at which words show up, not the structure of the idea; a student who
explains something correctly in different words gets penalized unfairly.
*Source, printed on the slide:* Mohler & Mihalcea, EACL 2009, `[1]` — verified against
[ACL Anthology E09-1065](https://aclanthology.org/E09-1065/).

**Box 2 — Dependency Graphs (Mohler et al. 2011), r = 0.518.** A step up — looks at how
words grammatically connect in a sentence, and compares that structure to the reference
answer's structure. Small improvement over 0.493: structure helps a bit more than
word-matching alone. Caption — "Structural alignment, still no explicit KG": progress,
but it's comparing sentence grammar, not a map of ideas — no built expert knowledge
graph behind the comparison.
*Source, printed on the slide:* Mohler, Bunescu & Mihalcea, ACL 2011, `[2]` — verified
against [ACL Anthology P11-1076](https://aclanthology.org/P11-1076/).

**Box 3 — Transformer Fine-Tuning (BERT-based) — "F1 gain (SemEval)."** This box does
NOT show an r-number, and that's deliberate, not a gap to explain away. While verifying
every source on this slide, the citation originally behind this box turned out not to
exist — wrong title, wrong authors, wrong journal, unfindable anywhere (ACL Anthology,
IEEE Xplore, dblp, Semantic Scholar all came back empty). The real underlying paper is
Sung et al., *"Pre-training BERT on domain resources for short answer grading,"*
EMNLP-IJCNLP 2019 — verified at
[ACL Anthology D19-1628](https://aclanthology.org/D19-1628/). That real paper reports
its results as an F1 score on the SemEval-2013 benchmark, not a Pearson r on Mohler, so
the box says exactly that rather than forcing a number the paper doesn't report. If
asked what F1 means: it balances precision (when the system says "correct," how often
is it actually right) and recall (of all the truly correct answers, how many did it
catch) into one number — not directly comparable to r, which is exactly why the two
aren't shown side by side. Caption — "Different metric/dataset, fully opaque": still a
strong technique, still can't explain which concepts it saw.
*Source, printed on the slide:* Sung et al., EMNLP-IJCNLP 2019, `[4]`.

**Box 4 — LLM Zero-Shot (C_LLM baseline) — "Competitive."** Just asking a modern AI
model directly to grade the answer, no extra training. No fixed number here on purpose
— this is your own baseline, on your own dataset; the real figure belongs in Seminar 2.
Caption — "No explicit conceptual record kept": genuinely strong, but still only a score
and maybe a comment, no structured record of which concepts were present or missing.

**Say, tying the boxes together:** "Notice the pattern left to right: as methods get
more sophisticated, they generally get more accurate — though the third box shows we
can't put all four on one clean number, since they weren't all measured the same way.
Not one of them keeps a structured, inspectable record of what the student
demonstrated. That gap is what ConceptGrade is built to close."

**Say, the lineage sentence, close to verbatim:** "ConceptGrade extends concept-map
assessment — where students traditionally *draw* node-link diagrams that get graded
against an expert map — to free-text answers, by inferring an equivalent graph
automatically via LLM extraction." This is the one sentence that tells the committee you
know the education-research lineage, not just the ML side.

**Anticipate:** "How are these correlation scores actually derived?" → Three of the four
are Pearson correlation between each system's automated score and a human grader's
score, computed by the original authors on their own version of the Mohler benchmark —
you didn't recompute them, you're citing them for context. The fourth (BERT box) isn't
an r-value at all, for the reason above — say that plainly, don't hedge.

**Anticipate:** "Did you verify these against the original papers, or copy them from
someone else's related-work section?" → Yes, verified directly — full citations are on
the References slide (17), and each box on this slide now carries its own compact
citation tag so you don't have to take my word for it mid-talk.

**Anticipate:** "If BERT-based fine-tuning is the strongest recent direction, why not
just use that?" → Raw accuracy isn't the target metric here — inspectability is. A
fine-tuned BERT model that scores well still can't tell an instructor *why*. This paper
trades some of that ceiling for structure, and Seminar 2 is honest about what that trade
costs in practice.

**Transition:** "So — five things this work actually contributes, concretely."

---

## Slide 4 — Five Contributions (2:00)

**Say:** Go through the five briskly — this is a signpost slide, not a deep-dive slide.
Resist the urge to defend each one here; you'll do that on the layer-by-layer slides.
1. Five-layer pipeline (extraction → KG comparison → depth → misconceptions → verifier).
2. A hand-built Data Structures KG, frozen before evaluation — emphasize *frozen before
   evaluation*, it's a methodological safeguard, say it plainly.
3. An honest, real-data evaluation — "small, response-level-significant, but
   question-level-fragile gain, with the true source of the gain identified via
   ablation." This is your thesis statement for the whole three-seminar series — say it
   exactly like this every time it comes up.
4. Self-consistency ensembling, fairly tested — "a real robustness claim that partially
   collapses under an equally-resourced control, reported as found, not as hoped."
5. A reproducible, cost-transparent protocol — 300+ automated checks recompute every
   reported number from cached predictions.
- Close with the framing sentence on the slide: "We frame this as an empirical study of
  where and why KG-LLM hybrid grading helps — not a claim that it always does." This is
  your thesis. Say it slowly. It's the sentence that should survive if the committee
  remembers nothing else.

**Transition:** "Let's look at how the system actually works, end to end."

---

## Slide 5 — System Architecture (2:00)

**Say:**
- One pass left to right: Concept Extraction → KG Comparison → Cognitive Depth →
  Misconception Detection → Score Synthesis + Verifier. Question + student answer in;
  score + explanation out.
- Name the mechanism under each box in one breath: LLM (`gemini-2.5-flash`) with 3×
  self-consistency; deterministic LLM-free matching; Bloom's + SOLO; a 16-entry
  validated taxonomy; blend into an LLM Verifier at weight w=1.0.
- Don't over-explain any one box yet — flag that each gets its own slide shortly, and
  that Layer 5's `w=1.0` is the single most important number in the whole architecture
  diagram — "hold that thought, I'll come back to it."

**Anticipate:** "Why five layers instead of end-to-end fine-tuning?" → Same answer as
Slide 3: interpretability and structured feedback are the design goal, not raw accuracy
alone. Each layer produces an inspectable artifact (the concept graph, the depth label,
the misconception tag) that the final grade doesn't have to reconstruct after the fact.

**Transition:** "Before the layer-by-layer breakdown, I want to show this isn't a
diagram — it's a running system."

---

## Slide 6 — The Live Application (1:30)

**Say:** This is the real NodeGrade platform's node-graph editor, not a mockup. Point
out one or two concrete UI elements in the screenshot — the graph nodes, the editing
surface — and say plainly "everything I'm about to describe is implemented and running,
not a proposed design." If you can, have the actual app open as a backup in case someone
asks to see it live.

**Transition:** "Here's what a real graded answer looks like when submitted to this
system."

---

## Slide 7 — Live Example (2:00)

**Say:**
- Read the submitted answer aloud: "A stack is a data structure that uses FIFO order..."
  — pause after "FIFO" so the committee catches the error themselves before you name it.
- Walk the top screenshot (the score/explanation) then the misconceptions screenshot.
  Land on: this student would be flagged for confusing LIFO with FIFO — DS-STACK-01 —
  with a remediation hint, not just a low number.
- This slide is doing real work: it's proof that Layers 2 and 4 (KG comparison,
  misconception detection) produce something a human grader would actually find useful,
  independent of whether the final numeric score beats a baseline. Say that connection
  explicitly — it's your best defense against "but the accuracy gain is small" pushback
  later.

**Transition:** "Now let's go layer by layer through how that output gets built."

---

## Slide 8 — Layer 1: Concept Extraction (1:30)

**Say:**
- The LLM receives the question and student answer, returns a typed student concept
  graph $G_s = (V_s, E_s)$.
- Run 3× with self-consistency, majority-vote, min_votes = 2/3 — this reduces
  single-call extraction noise. (You'll revisit whether this actually helps, fairly
  tested, in Seminar 2 — you can foreshadow it here in one clause.)
- Question-focused ontology matching: a keyword matcher builds a focused ~10–20-concept
  subset of the 101-concept KG for the prompt, rather than always supplying the whole
  graph — this keeps the prompt tight and reduces spurious matches.
- Concepts below confidence τ=0.70 are filtered; surface forms resolve to canonical KG
  IDs via alias lookup.
- **Own the bug, briefly, don't dwell:** "What is a queue?" tokenized without stripping
  punctuation → "queue?" never matched "queue" in KG text → a false out-of-domain flag on
  106 of 1,262 samples. Found and fixed this year. One sentence, then move on — "more in
  Seminar 3" is written on the slide for a reason; let it do the deferring for you.

**Anticipate:** "Why threshold 0.70 specifically?" → If you don't have a principled
answer beyond "it was fixed before evaluation and not tuned on the real data," say
exactly that — it's honest and matches your own disclosed-limitations framing. Don't
invent a justification you don't have.

**Transition:** "Once we have that student graph, Layer 2 compares it against the
expert graph — deterministically, no LLM involved."

---

## Slide 9 — Layer 2: KG Comparison (1:30)

**Say:**
- Emphasize **deterministic, LLM-free, no model calls, fully reproducible** — this is
  the one layer in the whole pipeline that isn't a language-model call, and that's a
  deliberate design choice worth naming.
- Three scores, say the formulas plainly:
  - coverage = $|V_s \cap V_e| / |V_e|$ — fraction of expert concepts the student hit.
  - accuracy = correct edges / student edges — fraction of stated relationships that are
    right.
  - integration = connected nodes / student nodes — how structurally connected the
    student's graph is, versus a disconnected list of terms.
- These three feed directly into the interpretable diagnostics — missing concepts,
  incorrect relationships — that show up as feedback to the student.

**Transition:** "The mechanism behind that concept-alignment step is worth a moment on
its own — it's called Topological Reasoning Mapping."

---

## Slide 10 — Topological Reasoning Mapping / TRM (2:00)

**Say:**
- Name it clearly as **approximate subgraph matching, not NP-hard subgraph
  isomorphism** — this distinction matters if anyone in the room has a theory background,
  so make it explicit rather than let them wonder.
- Three phases:
  1. Concept alignment — each student concept matched to its nearest expert concept via
     BERT cosine similarity, threshold 0.70.
  2. Relationship matching — each student edge scored against the expert graph: 1.0 full
     match, 0.5 partial, 0.0 no match.
  3. Verifier confidence weighting — each matched concept weighted 1.0 if grounded in the
     answer text, 0.3 if it looks hallucinated.
- Complexity: $O(|V_s|\cdot|V_e| + |E_s|\cdot|E_e|)$ — polynomial, not NP-complete —
  roughly 2.3 seconds per answer on a standard CPU at batch scale. Have this number
  ready verbatim; it's the kind of thing a committee member will ask you to repeat.

**Anticipate:** "Why not exact subgraph isomorphism?" → Exact isomorphism is NP-hard and
brittle to any paraphrase — a student who says "push adds to the top" instead of the
exact KG phrasing would fail an exact match entirely. The approximate, threshold-based
matching is what makes free-text grading tractable at all; that's the whole point of the
cosine-similarity alignment step.

**Transition:** "Layers 3 and 4 run in parallel with that comparison — depth and
misconceptions."

---

## Slide 11 — Layers 3 & 4: Depth & Misconceptions (1:30)

**Say:**
- Layer 3: a hybrid classifier jointly assigns Bloom's level (1–6, Remember→Create) and
  SOLO level (1–5, structural complexity of the response). Combined into
  $\text{depth} = 0.55 \cdot \text{blooms}_{\text{norm}} + 0.45 \cdot
  \text{solo}_{\text{norm}}$.
- Worth one sentence of framing: SOLO has received far less attention than Bloom's in
  automated CS assessment — applying both jointly is a small but real contribution.
- Layer 4: a 16-entry *validated* error taxonomy checked against every response. Example:
  DS-STACK-01, confuses LIFO with FIFO ordering. Each entry carries a severity level and
  a remediation hint surfaced to the student — "not just wrong."

**Transition:** "All five signals converge in Layer 5 — and this is the slide I most
want the committee's attention on."

---

## Slide 12 — Layer 5: Score Synthesis & Verification (2:30 — the pivotal slide)

**Say, slowly, and don't rush the formulas:**
- knowledge = 0.45·cov + 0.35·acc + 0.20·int
- $s_{kg}$ = (0.60·knowledge + 0.40·depth) × (1 − p_misc)
- final = (1 − w)·$s_{kg}$ + w·verified, and **at the deployed configuration, w = 1.0.**
- Say what that number means in plain language, not just algebra: "At deployment, the
  Verifier's independent judgment entirely replaces the deterministic KG-formula score.
  The KG evidence still enters as *context* the Verifier reads — it's not thrown away —
  but arithmetically, it has zero weight in the final number."
- Then ask your own question out loud, exactly as written on the slide: "Is that an
  accident of tuning?" and answer it with the forward pointer: "Seminar 2 answers this
  with a real-data ablation and a call-budget-matched control — I'm not going to
  pre-empt that result today, but I want you to leave this room holding that question."
- This is deliberate suspense, not evasiveness — say so if it feels evasive in the room:
  "I'm choosing not to answer this today because the honest answer needs the evaluation
  data, which is Seminar 2's material, not System Design's."

**Anticipate (this slide will draw questions — expect them, don't be defensive):**
- "If w=1.0 discards the KG score, why build the KG-comparison layer at all?" → Two
  honest reasons: (1) the KG evidence is what the Verifier *reads* as context — it's not
  causally inert, it's just not arithmetically weighted; (2) Layer 2's coverage/accuracy/
  integration scores are what produce the structured student-facing feedback on Slide 14
  — that value exists independent of whether the *numeric* grade depends on it. If
  pressed further: "That tension — a component that's useful for explanation but not
  (yet) for accuracy — is precisely the finding Seminar 2 quantifies (86.9% worse alone).
  I'm not hiding that it's a real limitation."
- "Was w=1.0 tuned, or chosen a priori?" → Be precise and don't guess beyond what you
  know: if it was selected via a sweep on cached data before the real-data evaluation,
  say that plainly and point to Seminar 2's ablation as the place that's examined
  rigorously.

**Transition:** "Layer 2's comparisons are only as good as the expert graph they're
compared against — so let me show you that graph."

---

## Slide 13 — The Expert Domain Knowledge Graph (1:00)

**Say:**
- 101 concepts, 138 typed relationships, 8 semantic types. **Frozen before evaluation
  began** — say this again, it's the second time on the deck and that's intentional
  repetition, not an accident.
- Three design rules, one breath each: pedagogical coverage (every concept in a standard
  intro Data Structures course); canonical identifiers (unique ID plus alias surface
  forms, which is what makes Layer 1's alias-lookup step possible); typed relationships
  (semantically labeled directed edges, not generic "related-to" links).

**Transition:** "All of that authoring effort exists to produce one thing: what the
student actually sees."

---

## Slide 14 — What the Student Actually Sees (1:30)

**Say:** Walk the four feedback types with the example text on the slide, verbatim:
- Matched/missing concepts: "You mentioned stack and lifo, but missed push_operation and
  pop_operation."
- Incorrect relationships: "Stack uses FIFO is incorrect."
- Bloom's/SOLO level with justification — cognitive depth, not just correctness.
- Misconception + remediation: "DS-STACK-01: A stack uses LIFO, not FIFO. Review the
  push/pop mechanism."
- Close with the framing line on the slide: "The KG and misconception taxonomy carry this
  information cost at *authoring* time, not inference time." This is your answer to any
  "doesn't this all cost a lot to build?" pushback — the cost is paid once, up front, not
  per-student, per-answer.

**Transition:** "I want to close System Design with what I'm *not* claiming yet —
scope and limitations, stated up front."

---

## Slide 15 — Scope & Limitations (1:30)

**Say, plainly, no defensiveness — this slide is a strength, not an admission of
weakness:**
- Single model family: every LLM call uses `gemini-2.5-flash`; no cross-model validation
  yet.
- Single-author KG & taxonomy: 101 concepts, 16 misconceptions, one research group.
  Machine-IRR pilot: κ=0.54, moderate agreement — and say explicitly, "that's a
  self-administered lower-bound estimate, not external validation. I want to be precise
  about what it isn't."
- Domain specificity: the expert KG covers Data Structures only; cross-domain evaluation
  is future work.
- Close with: "These are disclosed up front, not discovered by a reader — and Seminar 3
  covers a deeper class of limitation found during the project's own internal audit."

**Anticipate:** "Given a single-author KG with only moderate machine-IRR, how much can
you trust the coverage/accuracy numbers at all?" → Answer honestly: they're conditional
on *this* KG; a different domain expert building an equivalent KG from the same source
material would likely produce something overlapping but not identical. That's exactly
why cross-KG / third-party construction (e.g., SIGCSE crowdsourcing) is named as future
work rather than treated as solved.

**Transition:** "That's the system. Here's exactly what Seminar 2 will put this design
to the test on."

---

## Slide 16 — Coming in Seminar 2 (0:30)

**Say:** Read the three forward-pointing questions as written — they work as written,
don't paraphrase them into something softer:
- Does ConceptGrade really beat a zero-shot LLM baseline?
- Why does the raw KG-grounded score perform 86.9% worse than baseline — alone?
- Self-consistency looked like the strongest result in the project — what happened when
  it was tested fairly?

**Transition:** "One more slide before questions — where Slide 3's numbers actually came
from."

---

## Slide 17 — References (0:20, optional — skip verbally if short on time, it speaks
for itself)

**Say, briefly, only if you pause here:** "Slide 3 cited four prior approaches — these
are the full sources, verified directly against the original papers, not copied from
someone else's related-work section. The fourth one is worth a half-sentence: the
citation originally behind the BERT box turned out to be unverifiable, so it's been
corrected to the real paper, which is why that box reports an F1 score rather than a
correlation — different metric, honestly labeled rather than forced to match the other
three."

**If asked to elaborate on the correction:** Give the short version from Slide 3's
"Anticipate" notes above — don't over-explain unless the committee asks a follow-up.

**Close:** Thank the committee, open the floor for questions.

---

## Timing summary

| Slides | Cumulative time |
|---|---|
| 1–4 (motivation) | ~7:00 |
| 5–7 (architecture + live demo) | ~5:30 |
| 8–12 (layer-by-layer, incl. the w=1.0 slide) | ~9:00 |
| 13–16 (KG detail, student view, limitations, close) | ~4:30 |
| **Total prepared talk** | **~26:00** |

That leaves 4–14 minutes of your 30–40 minute slot for Q&A depending on how the room
runs — tight but workable. If you're running long in rehearsal, the safest cuts are
trimming Slide 3's four-method walk to two sentences per method, and shortening Slide 13
(the KG stats are already reinforced from Slide 4 and Slide 5).

---

## Hardest questions the committee is likely to ask (defense prep)

These are ranked roughly by how likely and how sharp they are, based on where this deck
itself creates the opening.

### 1. "If the KG score alone is worse than baseline, isn't this really just an LLM
grading system with extra steps?"
**This is the sharpest question in the deck and it will probably come.** Don't get
defensive. Two-part answer:
- Not entirely — Layer 2's coverage/accuracy/integration scores are what generate the
  structured, per-concept feedback shown on Slide 14 (matched/missing concepts,
  incorrect relationships). That value is independent of whether the *numeric* grade
  the Verifier produces depends on it arithmetically.
- But it's a fair challenge to the paper's framing, and I'm not going to pretend
  otherwise — the honest reframe (which Seminar 2 makes explicit) is that the system's
  contribution right now is closer to *structured, KG-grounded explanation* than to
  *KG-driven accuracy*. Whether the KG-comparison score itself can be made more
  predictive is open future work.

### 2. "Your baseline and your system use the same model but ConceptGrade got tuning
the baseline didn't. Isn't that comparison unfair?"
- Yes, and it's disclosed rather than hidden (Slide 15's spirit, made concrete in
  Seminar 2's limitations section). Using the identical model for both sides rules out
  model-capability as a confound, but doesn't by itself rule out a tuning-budget
  asymmetry. Seminar 2 covers a call-budget-matched control specifically built to test
  this.

### 3. "A 2.3-second-per-answer TRM cost, plus multiple LLM calls per response (3×
self-consistency, depth, misconceptions, verifier) — what does this cost at scale for a
real class?"
- Be ready with the call count: the reported configuration issues roughly 7 LLM calls
  per graded response (3 for self-consistency extraction, 1 depth, 2 misconception, 1
  verifier), versus 1 for the baseline. That's a real, disclosed cost/latency tradeoff,
  not something to minimize if asked directly — Seminar 2 tests whether that extra
  compute budget alone (independent of the KG) explains part of the accuracy gain.

### 4. "How do you know your misconception taxonomy and KG are actually correct, given
one research group built both?"
- κ=0.54 machine-IRR is a self-administered lower bound, explicitly not external
  validation — say this exactly, don't round it up to sounding stronger than it is.
  Third-party KG construction (e.g., crowdsourced via SIGCSE) is named future work.

### 5. "Why gemini-2.5-flash specifically, and not a stronger frontier model?"
- Keeping the baseline and ConceptGrade on the identical model isolates model capability
  as a confound. Using a stronger frontier model for ConceptGrade only would make any
  gain ambiguous — is it the architecture, or just a better model? That comparison is
  deliberately deferred to future work, not an oversight.

### 6. "Are you claiming this generalizes beyond Data Structures?"
- No — explicitly not yet. The KG only covers Data Structures; a second
  Programming/OOP KG (62 concepts, 116 relationships) exists but hasn't been evaluated.
  Cross-domain evaluation is named future work on Slide 15.

### 7. "What happens if a student's phrasing doesn't match any KG concept at all —
does the system just fail silently?"
- No — this is exactly the out-of-domain / zero-grounding case surfaced explicitly
  (the "queue?" punctuation bug on Slide 8 is one concrete instance you already found and
  fixed). The system is designed to *flag* zero-grounding rather than produce a
  confident-looking wrong score — say this if it comes up, since it reinforces the
  disclosure-over-hiding theme running through the whole talk.

---

## One-line answers to keep in your back pocket

Use these if a question runs long and you need to land it fast, then offer to go
deeper if the committee wants:

- **"What's the headline result?"** → A small, real, response-level-significant gain
  over an identical-model baseline — but the gain comes mostly from the Verifier, not
  the KG-grounding the system is named for. Seminar 2 has the numbers.
- **"Is this ready to deploy in a real classroom?"** → Not yet — single model family,
  single-domain KG, single-author taxonomy are all disclosed, active limitations, not
  solved problems.
- **"What's the single most interesting finding in this whole project?"** → The
  KG-formula score alone is 86.9% worse than just asking the LLM directly — that's a
  genuine, disclosed architectural finding about where the accuracy in a KG-LLM hybrid
  system actually comes from.
