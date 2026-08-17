# Seminar 1 — One Example, Threaded Through Every Slide

## The example (introduce once, up front — real, from your own screenshots)

**Question:** "What is a stack, and how does it order operations?"

**Student's answer (verbatim, submitted live to the real system):** "A stack is a data structure that stores items and uses FIFO order, first in first out, similar to a queue, so the first item pushed is the first one removed."

**Why this example is good to use:** the student gets the *category* right (it is a data structure) but the *ordering rule* backwards — they describe a queue (first in, first out) while confidently calling it a stack (which is actually last in, first out). That single, common mix-up is enough to illustrate almost every idea in this talk: coverage vs. accuracy, misconception detection, depth, and the Verifier's role — all from one sentence.

**Say this once, near Slide 2, to plant it:** "I'm going to use one real example the whole way through today — an actual answer submitted to the live system — so you can watch the same sentence move through every stage instead of me describing each stage in the abstract."

**The real, verified output for this exact answer (screenshots on Slide 7):**
- ConceptGrade (KG-grounded) score: **0.75 / 5**
- Pure LLM (zero-shot) score: **1.00 / 5** — the plain AI actually scored it slightly *higher*
- Depth category: **surface**; Bloom's: **Remember (L1)**; SOLO: **Unistructural (L2)**
- 8 concepts identified
- 1 misconception detected: **critical**, tagged "conflation" — the system's own wording: *"The student incorrectly states that a stack uses FIFO order. Stacks actually use LIFO order... The description provided accurately describes a queue, not a stack."*
- Remediation hint given: *"Review the fundamental principles of stacks and queues... how items are added (pushed/enqueued) and removed (popped/dequeued)."*
- "What you did well": covers multiple relevant concepts, identified 8 distinct concepts.
- "Gaps in understanding": stays at recall level, concepts listed but not connected, 1 critical misconception.

**One honest caveat to say out loud if you use the exact score comparison:** this is a single example, not a statistical result — on this one answer ConceptGrade scored more harshly (arguably more correctly) than the plain LLM, but Seminar 2's aggregate numbers across 1,262 answers tell a more mixed story. Don't let one favorable example imply more than it proves — say that yourself before someone else points it out.

---

## Slide 1 — Title

Just plant the promise: "Today, I'll use one real submitted answer — about stacks and queues — and walk it through the whole system, step by step, so you can see exactly what happens to it."

---

## Slide 2 — The Problem

Use the example to make the abstract problem concrete: "If a plain autograder saw this student's answer, it might give a low score. But a low score alone doesn't tell you *why* — is the concept missing, or is it wrong? In this exact case, the student didn't skip the idea — they got the ordering rule backwards, confidently. A number can't tell those two situations apart. My system is built to tell them apart."

---

## Slide 3 — What Prior Approaches Miss

Tie each historical method back to this one sentence: "A word-matching system would see 'stack,' 'data structure,' 'first,' 'removed' overlapping with a correct reference answer and might give partial credit — even though the student is confidently wrong about the core rule. A plain AI grader, as we just saw, actually gave this answer a *slightly higher* score than my system did. None of these approaches would tell you, specifically, 'this student thinks a stack is LIFO — I mean FIFO' the way my system does."

---

## Slide 4 — Five Contributions

"Contribution three — an honest, real-data evaluation — is exactly what that 0.75 vs. 1.00 comparison you just saw is about. I'm not going to hide that on this metric, on this single answer, the plain AI actually scored closer to what a lenient human might give. Watch how the rest of the system still produces something more useful than either number alone."

---

## Slide 5 — System Architecture

"Let's trace this exact sentence through all five workers: Layer 1 will pull out the concepts it mentions — stack, FIFO, pushing, removing. Layer 2 will compare that against the real rule. Layer 3 will judge how deep the explanation is. Layer 4 will catch the LIFO/FIFO mix-up specifically. Layer 5 will decide the final grade — and, as we already saw, that final grade (0.75) is lower than what the plain AI gave (1.00)."

---

## Slide 6 — The Live Application

"This is the actual screen this exact answer was submitted to — not a mockup."

---

## Slide 7 — Live Example

This slide *is* the source of the running example — deliver it as the anchor moment: "A stack is a data structure that stores items and uses FIFO order, first in first out, similar to a queue, so the first item pushed is the first one removed." Pause. "Everything after this slide is me pulling apart exactly what the system did with this one sentence."

---

## Slide 8 — Layer 1: Concept Extraction

"For this exact sentence, Layer 1 pulled out 8 distinct concepts — things like 'stack,' 'data structure,' 'FIFO,' 'first item,' 'removed.' Notice it extracts 'FIFO' as a concept the student *stated* — it doesn't judge yet whether that's correct. That judgment is Layer 2's job. This step just builds the honest map of what the student actually said, mistakes included."

---

## Slide 9 — Layer 2: KG Comparison

"Now compare that map to the expert's map. Coverage is reasonably good — the student did mention 'stack,' 'data structure,' the idea of adding and removing from one end. But accuracy fails on the one relationship that matters most: the student says 'stack has-ordering FIFO.' The expert map says the real relationship is 'stack has-ordering LIFO.' That single wrong edge is the whole story of this answer — good coverage, one critical wrong connection."

---

## Slide 10 — TRM (matching mechanism)

"Watch how the matching handles this: the phrase 'first item pushed is the first one removed' doesn't use the word 'FIFO' or 'LIFO' directly in that clause, but the system's fuzzy matching still recognizes it describes a FIFO-style rule, and checks it against the expert graph's actual stack-ordering edge. That check comes back as a clear mismatch, not a partial one — this isn't a phrasing difference, it's a factually reversed claim, and the system treats it that way."

---

## Slide 11 — Layers 3 & 4: Depth & Misconceptions

"Layer 3 classified this answer's depth as 'surface' — Bloom's Remember (L1), SOLO Unistructural (L2). In plain terms: the student is reciting a rule, not explaining or connecting it to anything else, and the rule itself is wrong. Layer 4 is where the specific catch happens — flagged as a **critical** misconception, tagged 'conflation,' with this exact system-generated explanation: 'The student incorrectly states that a stack uses FIFO order... The description provided accurately describes a queue, not a stack.' Plus a remediation hint pointing the student back to how push/pop versus enqueue/dequeue actually differ."

---

## Slide 12 — Layer 5: Score Synthesis & Verification *(the pivotal slide — use the real numbers here deliberately)*

"Here's the moment this example earns its keep. ConceptGrade's final score for this answer: **0.75 out of 5**. The plain zero-shot AI's score for the exact same answer: **1.00 out of 5**. The AI, with no map, no structured comparison, no misconception check, actually scored this wrong answer slightly *higher* than my system did.

On this one example, that's arguably ConceptGrade doing its job well — correctly penalizing a confidently-wrong core claim more than an ungrounded AI guess did. But I want to be honest about the limits of a single example: this is one data point, not a statistical result. Seminar 2 is where I show what happens across 1,262 answers, not just this one — and that overall picture is much more mixed than this one favorable case suggests. I'm showing you this example because it's real and it's illustrative, not because it proves the system works better on average."

---

## Slide 13 — The Expert Knowledge Graph

"Zoom into just the small slice of the 101-concept map relevant to this one answer: the 'stack' node, connected to a 'has-ordering' edge pointing to 'LIFO' — not FIFO. That one edge, sitting in a map built and frozen before any evaluation, is what Layer 2 checked this student's claim against."

---

## Slide 14 — What the Student Actually Sees

"This is the exact, real feedback this student received — not a hypothetical: 'What you did well — covers multiple relevant concepts, identified 8 distinct concepts.' 'Gaps in understanding — answer stays at recall level, concepts listed but not connected, 1 critical misconception.' Plus the specific misconception explanation and remediation hint we just walked through. That's a genuinely useful thing to hand back to a student — regardless of whether the single number above it is 0.75 or 1.00."

---

## Slide 15 — Scope & Limitations

"One limitation worth noting using this same example: this question sits squarely inside the Data Structures topics my expert map covers, so the system had every concept it needed already built in. A similarly-phrased question from a topic outside that map wouldn't get this same quality of feedback — that's the domain-specificity limitation stated plainly here."

---

## Slide 16 — Coming in Seminar 2

"You just watched what happens to one answer. Seminar 2 is what happens when you run this same comparison — ConceptGrade versus the plain AI — across all 1,262 real answers, not just this one favorable case, and check whether the pattern holds up statistically."

---

## Slide 17 — References

No natural tie-in to the running example — deliver as written in the main script.

---

## Why this works as a teaching device (for your own prep, not to say aloud)

Every slide from 8–14 is describing one stage of a pipeline that's otherwise abstract — "concept extraction," "graph comparison," "depth classification" — and abstract descriptions are exactly what a non-technical audience tunes out on. Anchoring every stage to the same real sentence means each new technical idea has something concrete to attach to, and by Slide 12 the audience has enough context to actually feel the weight of "the AI alone scored this wrong answer higher than my system did" — which is the whole point of the talk.
