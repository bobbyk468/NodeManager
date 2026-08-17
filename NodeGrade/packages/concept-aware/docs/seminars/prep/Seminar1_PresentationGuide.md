# Seminar 1 Presentation Guide
## ConceptGrade: System Design & Motivation — one running example, all 17 slides

**How to use this document:** this is one merged guide — the plain-English delivery for a non-technical audience, built around a single real example threaded through every slide, so you (and they) never lose the thread. Rehearse it out loud. Say it in your own words — this is a script to internalize, not read from at the podium.

---

## The one example you'll use all the way through

**Question asked:** "What is a stack, and how does it order operations?"

**Student's real answer (submitted live to the actual system):**
> "A stack is a data structure that stores items and uses FIFO order, first in first out, similar to a queue, so the first item pushed is the first one removed."

**Why this example carries the whole talk:** the student gets the *category* right — yes, it's a data structure — but gets the *rule* backwards. A stack works last-in-first-out (like a stack of plates — you take from the top); the student described first-in-first-out (like a line of people — first come, first served), which is actually how a *queue* works, not a stack. One confident, common mix-up. That's enough to illustrate almost everything in this talk.

**The real, verified results for this exact answer** (from your own screenshots — nothing here is invented):
- ConceptGrade's score: **0.75 / 5**
- A plain AI's score for the same answer, no special system: **1.00 / 5** — the plain AI actually scored it *higher*
- Depth: "surface" (Bloom's: Remember; SOLO: Unistructural)
- 8 concepts identified
- 1 misconception caught, marked **critical**: *"The student incorrectly states that a stack uses FIFO order. Stacks actually use LIFO order... The description provided accurately describes a queue, not a stack."*
- A specific hint given back: review how push/pop (stack) differs from enqueue/dequeue (queue).

**Say this once, early, to plant it (right after Slide 2):** "I'm going to use one real example the whole way through today — an actual answer submitted to the live system — so you can watch the same sentence move through every stage, instead of me describing each stage in the abstract."

**One honest thing to say yourself, before anyone else points it out:** this is one example, not proof. On this one answer, ConceptGrade scored more harshly than the plain AI did — which you can frame as ConceptGrade correctly catching a confident mistake. But that's a single data point. Your next talk (Seminar 2) shows what happens across 1,262 real answers, and that bigger picture is more mixed than this one favorable case suggests. Say that yourself — it's more convincing coming from you than being asked.

---

## Slide 1 — Title

"Hi everyone. Today I'm going to explain a computer system I built that automatically grades short written answers — like the kind a Computer Science student writes when asked 'What is a stack?' I called it ConceptGrade.

There are three talks in total. Today is just about *how the system is built*. I'm not going to talk much today about *how well it performs overall* — that's a separate talk, because I want to give that its own proper time.

And today, I'm going to use one real example the whole way through — an actual answer submitted to the live system — so you can watch it move through every stage."

---

## Slide 2 — The Problem

"Imagine a teacher with 200 students, each writing a paragraph. Grading that by hand takes a long time, and by the time it's done, students have moved on — feedback comes too late to help them.

Automated grading programs exist, but they have two problems. First, they only give a number — a '1 out of 5' doesn't tell you *why*. Second, they can't tell you *what specifically* a student is confused about.

Here's exactly what I mean, using the example I'll use all day: a student wrote, 'A stack is a data structure that stores items and uses FIFO order, first in first out.' A plain autograder might give that a low score. But a number alone can't tell you *why* it's low — did the student skip the idea entirely, or get it confidently backwards? In this case, the student didn't skip anything — they got the ordering rule exactly reversed. Those are very different problems needing very different feedback, and a bare score treats them identically.

My fix: instead of producing a number, treat grading like comparing two *maps of ideas* — turn what the student wrote into a map, and compare it to an expert's map of what the correct answer should contain."

---

## Slide 3 — What Prior Approaches Miss

**Before the boxes:** "You'll see a few boxes with 'r = a number.' Think of that as a trust score, 0 to 1 — how closely a computer's grading matched a real teacher's grading in past research. Closer to 1, closer to a human's judgment."

**Box 1 — Lexical/LSA (Mohler & Mihalcea), r = 0.493:** "The simplest approach — just checks if the same words appear. On our example, it would see 'stack,' 'data structure,' 'removed' overlapping with a correct answer and might give partial credit — even though the student is confidently wrong about the core rule. Trust score: 0.493, the lowest here. Verified against the real 2009 paper — printed right on the slide."

**Box 2 — Dependency Graphs (Mohler et al. 2011), r = 0.518:** "A step up — looks at how words connect grammatically, not just whether they match. Slightly better, 0.518. Still just grammar, not real understanding. From the same researchers' 2011 follow-up — also verified and printed on the slide."

**Box 3 — Transformer Fine-Tuning (BERT-based) — now says 'F1 gain (SemEval)':** "This one's worth pausing on honestly. BERT is an AI language model — an earlier relative of the tech behind tools like ChatGPT — specially trained to grade. More powerful than the first two. But while double-checking every source for this talk, I found the paper I'd originally cited for this box didn't actually exist — wrong title, wrong authors, unfindable anywhere. I tracked down the real paper and fixed it. That real paper measures success differently than the other boxes, so rather than force a number that isn't true, the box now honestly says what was actually measured. I'd rather show you I caught my own mistake than present something I can't back up."

**Box 4 — LLM Zero-Shot — 'Competitive':** "This is exactly what happened with our stack example: just asking a plain AI to grade it directly, no map, no special system — and remember, on our example, that plain AI gave a *higher* score (1.00) than my own system (0.75). No fixed number printed here on purpose — this is my own baseline, on my own data, and its real number belongs in the next talk."

**Tying it together:** "None of these four approaches keep a clear record of exactly what a student got right or wrong — they just produce a score. On our stack example, not one of them would tell you specifically: 'this student thinks a stack is FIFO — it's actually LIFO.' That's the gap I built ConceptGrade to close."

**Closing line:** "There's an older idea in education similar to this — students drawing diagrams of how ideas connect, graded against a model diagram. My system gets that same benefit without asking students to draw anything; the AI builds the diagram automatically from their normal writing."

---

## Slide 4 — Five Contributions

"Five things this project actually delivers:
1. A five-step pipeline — score plus explanation, not just a number.
2. A knowledge map I built by hand for Data Structures — 101 ideas, 138 connections — like an answer key shaped as a web instead of a sentence.
3. An honest evaluation — and here's where our example matters again: I just showed you a case where the plain AI scored *higher* than my system. I'm not hiding that. Contribution three is about finding out, honestly, when and where this approach actually helps.
4. A fair test of 'ask the AI multiple times, take the most common answer' — looked great at first, held up only partly under fairer testing.
5. A way to double-check every single number in my results with scripts, not memory.

Remember this one sentence above everything: **I'm not claiming this always works better — I'm studying exactly where it helps and where it doesn't.**"

---

## Slide 5 — System Architecture

"Five workers on an assembly line. A question and answer go in one end; a score and explanation come out the other. Let's trace our exact stack example through all five: Worker 1 will pull out the concepts it mentions — stack, FIFO, pushing, removing. Worker 2 compares that against the real rule. Worker 3 judges how deep the explanation is. Worker 4 catches the LIFO/FIFO mix-up specifically. Worker 5 decides the final grade — which, as we saw, came out to 0.75, lower than the plain AI's 1.00.

One thing to flag now and return to: Worker 5 turns out to matter far more than I expected."

---

## Slide 6 — The Live Application

"This is the actual screen this exact stack example was submitted to — a real, running program, not a mockup."

---

## Slide 7 — Live Example *(the anchor moment)*

Read it slowly, let it land: "A stack is a data structure that stores items and uses FIFO order, first in first out, similar to a queue, so the first item pushed is the first one removed." Pause.

"A stack is like a stack of plates — you only take from the top, so the *last* plate you added is the *first* one you remove. The student described the opposite — first come, first served — which is actually how a *queue* works, like a line of people. Everything from here on is me pulling apart exactly what the system did with this one sentence."

---

## Slide 8 — Layer 1: Concept Extraction

"An AI reads the answer and lists out the ideas it contains — for our example, it pulled out 8 distinct concepts: stack, data structure, FIFO, first item, removed, and a few more. It runs this three separate times and goes with whatever at least two agree on, since AI can be a little inconsistent — like getting three people to independently read the same paragraph and going with what most of them saw.

Notice: it extracts 'FIFO' as something the student *said* — it doesn't judge yet whether that's correct. That's the next worker's job.

Honest note: earlier this year I found a real bug — a question mark in 'What is a queue?' broke matching for over a hundred answers. Fixed now, but worth being upfront about."

---

## Slide 9 — Layer 2: KG Comparison

"Now compare the student's map to the expert's map — no AI here, just exact counting, same result every time. Three questions: how many important ideas did the student mention (coverage)? How many of the claimed connections are correct (accuracy)? Is it a connected web of ideas, or just a list (integration)?

For our example: coverage is decent — the student did mention stack, data structure, adding and removing from one end. But accuracy fails on the one relationship that matters most — the student says 'stack follows FIFO'; the real rule is LIFO. Good coverage, one critical wrong connection. That's the whole story of this answer in one sentence."

---

## Slide 10 — TRM (the matching mechanism)

"How does it match ideas when students never use the expert's exact words? It uses fuzzy matching — how *similar in meaning* two phrases are, not whether they're identical. For our example, the phrase 'first item pushed is the first one removed' doesn't say 'FIFO' outright, but the system still recognizes it describes a FIFO-style rule, checks it against the real stack-ordering rule, and finds a clear mismatch — not a partial one. This isn't a wording difference; it's a reversed fact, and the system treats it that way. All of this takes about two seconds per answer."

---

## Slide 11 — Layers 3 & 4: Depth & Misconceptions

"Worker 3 judges *how deep* the understanding is, not just whether it's right. For our example: classified as 'surface' — reciting a rule, not explaining or connecting it to anything else — and the rule itself is wrong.

Worker 4 checks against sixteen well-known CS misunderstandings. Our example triggers one directly, marked **critical**: the system's own words were, 'The student incorrectly states that a stack uses FIFO order. Stacks actually use LIFO order... The description provided accurately describes a queue, not a stack.' Plus a specific hint pointing back to how push/pop differs from enqueue/dequeue."

---

## Slide 12 — Layer 5: Score Synthesis & Verification *(slow down — this is the heart of the talk)*

"Here's where our example earns its keep. You'd expect the final grade to be a careful blend of everything the first four workers found. It is calculated — but then there's one more step: an independent AI review that makes its own final judgment, reading the raw answer plus everything found so far.

And here's the honest, surprising finding: in the version actually used, that final AI judgment **entirely replaces** the careful map-comparison score. The map-comparison score still gets computed, and the AI does read it as background — so it's not ignored — but mathematically, it contributes *zero* to the final number.

Now watch our example prove why that matters. ConceptGrade's final score: **0.75 out of 5**. The plain AI's score for the identical answer: **1.00 out of 5**. The AI, with no map, no comparison, no misconception check, scored this wrong answer slightly *higher* than my own system did.

On this one example, that's arguably ConceptGrade doing its job — correctly penalizing a confidently wrong claim more than an ungrounded guess did. But I want to be honest about limits: this is one data point. Next talk is where I show what happens across 1,262 real answers, not just this favorable case — and that bigger picture is more mixed than this one example suggests.

Separately: when we tested the map-comparison score entirely on its own, it actually did *worse* overall than just asking the AI directly. So most of this system's accuracy right now comes from the AI's own judgment, not the knowledge-graph comparison the system is named for. I'm not going to fully explain why today — that's next talk's material — but I want you to sit with that question."

---

## Slide 13 — The Expert Knowledge Graph

"Zoom into just the slice of the map relevant to our example: the 'stack' idea, connected by a labeled line to 'LIFO' — not FIFO. That one connection, sitting in a map of 101 ideas and 138 connections built and locked in *before* any testing, is exactly what Worker 2 checked the student's claim against."

---

## Slide 14 — What the Student Actually Sees

"This is the real feedback our example student received — not hypothetical. 'What you did well: covers multiple relevant concepts, identified 8 distinct concepts.' 'Gaps in understanding: stays at recall level, concepts listed but not connected, 1 critical misconception.' Plus the specific misconception explanation and hint we just walked through. That's genuinely useful to hand back to a student, regardless of whether the number above it is 0.75 or 1.00."

---

## Slide 15 — Scope & Limitations

"One limitation, using our same example: this question sits squarely inside the Data Structures topics my map covers, so the system had everything it needed already built in. A similarly-phrased question from outside that topic wouldn't get this same quality of feedback.

Other honest limits: only one AI model tested so far; I built the map and misconception list myself, with only a moderate self-check, not outside validation; and the map only covers one topic area. Said plainly, up front, rather than hoping nobody asks."

---

## Slide 16 — Coming in Seminar 2

"You just watched one answer move through the whole system. Next time: what happens when you run this same comparison — ConceptGrade versus the plain AI — across all 1,262 real answers, not just this one favorable case, and check whether the pattern holds up statistically."

---

## Slide 17 — References

"One last slide before questions — where the numbers on that earlier comparison slide actually came from. These are the real papers I checked myself, not copied from someone else's summary. And worth saying plainly: one of the four sources I'd originally written down turned out to be wrong — I found and fixed it rather than leave it. Thank you — happy to take questions."

---

## Quick-glance summary of the running example (for your own eyes, mid-talk)

| Stage | What happens to "FIFO stack" answer |
|---|---|
| Layer 1 | 8 concepts extracted, including the stated (wrong) "FIFO" claim |
| Layer 2 | Good coverage, accuracy fails on the ordering relationship |
| Layer 3 | Depth = surface, Bloom's Remember, SOLO Unistructural |
| Layer 4 | 1 critical misconception: LIFO/FIFO conflation, with remediation hint |
| Layer 5 | Final score 0.75/5 — plain AI alone gave 1.00/5 for the same answer |
| Feedback | Structured "what you did well" / "gaps" shown to student, regardless of score |

## If a non-technical audience member asks a fallback question

- **"What's an AI language model?"** → A program trained on huge amounts of text so it can read and write in a human-like way — same basic idea as tools like ChatGPT.
- **"What's a trust/correlation score?"** → A number from 0 to 1 showing how closely two sets of scores agree — 1 means always agree, 0 means no relationship.
- **"What's a knowledge graph / map of ideas?"** → A diagram where each idea is a box and lines show how ideas connect — like a mind-map, built and checked systematically.
- **"Why build the map before testing?"** → Same reason an exam's answer key gets locked in before students take the test — so nobody can be accused of quietly adjusting it afterward to make results look better.
