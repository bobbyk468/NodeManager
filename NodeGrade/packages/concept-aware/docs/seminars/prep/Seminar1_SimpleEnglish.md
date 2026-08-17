# Seminar 1 — Simple English Walkthrough
## For a non-technical audience, slide by slide

No jargon left unexplained. Say this in your own words — it's written to be spoken, not read aloud verbatim.

---

## Slide 1 — Title

"Hi everyone. Today I'm going to explain a computer system I built that automatically grades short written answers — like the kind a Computer Science student writes when asked 'What is a stack?' or 'How does a queue work?' I called it ConceptGrade.

There are three talks in total. Today is just about *how the system is built* — the pieces inside it, and why I designed it this way. I'm not going to talk much today about *how well it actually performs* — that's a separate talk, because I want to give that its own proper time."

---

## Slide 2 — The Problem

"Imagine a teacher with 200 students. Each student writes a paragraph answering a question. Grading 200 paragraphs by hand takes a long time, and by the time the teacher finishes, the students have already moved on to new material — so the feedback comes too late to actually help them.

So people have tried to build computer programs that grade automatically. But those programs have two problems.

**Problem one: they only give a number.** Say a program gives a student '3 out of 5.' That number doesn't tell you *why*. Did the student get half the ideas right? Did they explain it in a confusing way? A plain number can't say.

**Problem two: they can't tell you what the student is confused about.** Imagine two students who both score low. One of them just didn't write much at all. The other one wrote a lot, but mixed up two ideas — like thinking a stack works one way when it actually works the opposite way. Those are two very different situations that need two very different kinds of help, and a plain number treats them exactly the same.

My idea to fix this: instead of just producing a number, treat grading like comparing two *maps of ideas*. Take everything the student wrote, and turn it into a map showing which ideas they mentioned and how those ideas connect to each other. Then compare that map to a map an expert made ahead of time, showing what a correct, complete answer should look like. When you compare maps instead of guessing a number, you automatically know exactly what's missing and what's wrong — because you can literally point at the difference between the two maps."

---

## Slide 3 — What Prior Approaches Miss

**Before touching any box:** "You'll see a few boxes with a letter 'r' and a number, like 'r = 0.493.' Just think of that as a trust score, from 0 to 1. It tells you how closely a computer's grading matched a real teacher's grading, when tested by researchers. Closer to 1 means the computer agreed with the teacher almost every time. Closer to 0 means it barely matched at all."

**Box 1 — Lexical / LSA (Mohler & Mihalcea):** "This is the oldest, simplest way people tried to build an automatic grader. It basically just checks: does the student's answer use the same *words* as the correct answer? If a student explains something correctly but uses different words, this method gets confused and marks them wrong, even though they understood it fine. Its trust score was 0.493 — the lowest of the three we're comparing. This comes from a real research paper — Mohler and Mihalcea, published in 2009. I checked it myself against the original paper online, and I've printed that source directly on the slide."

**Box 2 — Dependency Graphs (Mohler et al. 2011):** "This is a small improvement on the first idea. Instead of just checking whether the same words appear, it also looks at how the words in a sentence are connected — like, who's doing what to what. That gave a slightly better trust score, 0.518. It's better, but it's still just checking grammar, not actually understanding the ideas. This is from the same research group's follow-up paper, published in 2011 — also checked and sourced on the slide."

**Box 3 — Transformer Fine-Tuning (BERT-based):** "This box is a little different, and I want to explain why honestly, because it's actually a good story about doing this properly. BERT is a type of AI language model — an earlier relative of the kind of AI behind tools like ChatGPT. Researchers took that AI and trained it further to get better at grading — a more powerful approach than the first two boxes. Here's the honest part: while double-checking every source for this talk, I discovered the paper I originally had listed for this box didn't actually exist — I'd cited something wrong, and it didn't match any real published paper anywhere. So I tracked down the real paper this idea should be credited to and fixed it. That real paper measures success a different way than the other two boxes, so instead of forcing a number onto the slide that isn't actually true, this box honestly says what the real paper actually measured. I'd rather stand up here and say 'I found and fixed my own mistake' than present something I can't back up."

**Box 4 — LLM Zero-Shot (your own baseline):** "This is what happens when you just ask a modern AI directly, 'here's a student's answer, grade it' — no special training, no extra steps. Notice this box doesn't have a fixed trust score printed on it — that's on purpose. This is the one method I tested myself, on my own data, and that real number belongs in my next talk, not this one."

**Tying it together:** "So look at the pattern: as these methods get smarter, they generally get more accurate. But none of them keep a clear record of exactly which ideas a student got right or wrong — they just spit out a score. That's exactly the gap my system is built to close."

**Closing line:** "There's actually a much older idea in education that's similar to what I'm doing — teachers have long had students draw diagrams of how ideas connect, and graded the diagram. My system gets that same benefit, without asking students to draw anything — the AI reads their normal writing and builds that diagram automatically."

**If someone asks how you know these numbers are real:** "Every source is printed right there in small text under each box, and there's a full References page later in the deck with the complete details — I checked each one against the original published paper myself, and when I found one that didn't check out, I fixed it rather than leave it."

---

## Slide 4 — Five Contributions

"So here, briefly, are the five main things I actually built and found. I'll explain each one in much more depth in a minute — this is just the preview:

1. A five-step pipeline that reads an answer and produces both a score and an explanation.
2. A map of correct knowledge that I built by hand, covering the 'Data Structures' topic in Computer Science — think of it as an answer key, but shaped like a web of connected ideas instead of a single correct sentence.
3. An honest test of whether this actually helps — and I want to be upfront: the improvement I found is real, but it's small, and it doesn't hold up as strongly as I'd like under a stricter statistical test. I'll explain what that means later.
4. A test of a technique called 'asking the AI multiple times and taking the most common answer' — which looked very promising at first, but partly stopped looking as impressive once I tested it more fairly.
5. A system where I can double-check every single number in my results automatically, using scripts, rather than trusting my own memory or hand calculations.

And here's the one sentence I want you to remember above everything else today: **I'm not claiming this approach always works better — I'm studying exactly where it helps and where it doesn't.**"

---

## Slide 5 — System Architecture

"Now let's open up the system and look inside. Think of it as five workers on an assembly line. A question and a student's answer go in one end; a score and an explanation come out the other end. Here's what each of the five workers does, in one sentence each — I'll go much deeper on each one shortly:

1. Reads the answer and builds a map of what ideas the student mentioned.
2. Compares that map to the expert's map.
3. Judges how deep or sophisticated the student's understanding seems to be.
4. Checks whether the student has any well-known, common misunderstanding.
5. Makes the final decision on the grade.

I'll flag one thing now and come back to it later, because it's the most surprising thing I found in the whole project: that fifth worker — the one making the final decision — turns out to matter *far* more than I expected, compared to the other four."

---

## Slide 6 — The Live Application

"Before I explain each worker in detail, I want to show you this isn't just an idea on paper — it's a real, working piece of software. [pointing at screenshot] This is an actual screen from the real program running right now, not a drawing or a mockup. Everything I describe today is genuinely built and working."

---

## Slide 7 — Live Example

"Let me show you a real example. A student submitted this exact sentence to the live system: 'A stack is a data structure that uses FIFO order...' — pause for a second and think about that sentence.

A 'stack' is like a stack of plates — you can only take a plate off the top, and you can only add a plate to the top. That means the *last* plate you put on is the *first* one you take off. There's a name for that: 'last in, first out.' The student, in this example, wrote the opposite — 'first in, first out' — which is actually how a different structure, called a queue, works. Think of a queue like a line of people waiting — whoever got in line first gets served first.

So this student mixed up two ideas. And here's what the system does about it: [point at screenshots] it doesn't just give a low score — it specifically flags 'this student appears to be confusing these two ideas,' and gives them a hint to fix it. That specific, useful feedback is possible only because the system is comparing maps of ideas, not just producing a number."

---

## Slide 8 — Layer 1: Concept Extraction

"Let's go through the five workers one at a time, in more depth. Worker one reads the student's answer and turns it into a map of ideas.

How? It uses an AI language model — a system trained to read and understand text — and asks it: 'read this answer, and list out which ideas from this topic the student mentioned, and how they said those ideas connect.'

Now, AI models can sometimes be a little inconsistent — ask the same question twice and you might get slightly different answers. So instead of asking once, I ask it three separate times, and go with whatever at least two out of the three agree on. It's like getting three different people to independently read the same essay and then going with whatever most of them agree they saw.

I also don't give the AI the *entire* list of possible ideas every time — I first narrow it down to just the roughly ten to twenty ideas that are actually relevant to the specific question being asked. That keeps things focused and reduces mistakes.

One honest thing I want to mention: earlier this year, I found and fixed a real bug. When a question like 'What is a queue?' was processed, the question mark at the end accidentally caused the AI's search to fail to match the word 'queue' properly, so it wrongly thought over a hundred answers were completely off-topic when they weren't. It's fixed now, but I mention it because I think it's important to be upfront about real mistakes we found and corrected — more on that in the third talk."

---

## Slide 9 — Layer 2: KG Comparison

"Worker two takes the student's map and compares it to the expert's map. Unlike worker one, this step doesn't use AI at all — it's just careful, exact counting, done the same way every single time. That matters because it means this particular step is completely predictable and fair — the same input always produces the same output.

It asks three simple questions:
- How many of the important ideas did the student actually mention? I call this 'coverage.'
- Of the connections the student claimed between ideas, how many are actually correct? I call this 'accuracy.'
- Is the student's map a genuinely connected web of ideas, or just a scattered list of buzzwords with no real connections between them? I call this 'integration.'

These three answers are exactly what let the system generate specific feedback like 'you mentioned this but missed that.'"

---

## Slide 10 — TRM (matching mechanism)

"I want to explain one clever piece of engineering hiding inside worker two — how it actually matches up ideas, since students never use the exact same words as the expert's map.

If I required an exact word-for-word match, a student who wrote 'adding to the top' instead of the expert's phrase 'push operation' would be marked wrong, even though they clearly understand the idea. That would be unfair and pretty useless.

So instead, the system uses a 'fuzzy' matching approach — it checks how *similar in meaning* two phrases are, not whether they're identical, and accepts a match if they're similar enough. It does this in three steps: first it lines up the student's ideas with the closest matching expert ideas; then it checks whether the *connections* between ideas the student described are correct, giving partial credit for partially-right connections; then it double-checks whether each idea is genuinely grounded in what the student actually wrote, versus something that might have been made up.

This whole comparison is very fast — about two seconds per answer — and it's not the kind of computationally impossible problem some similar tasks can be; it scales reasonably as the maps get bigger."

---

## Slide 11 — Layers 3 & 4: Depth & Misconceptions

"Worker three judges *how deep* the student's understanding is — not just whether they're right, but how sophisticated their explanation is. Two students can both technically get the right idea, but one just repeats a definition from memory, while the other explains it and connects it to related ideas in a richer way. This worker uses two well-established frameworks from education research to judge that difference — one is about the type of thinking involved (remembering versus applying versus creating something new), and the other is about how structurally complete and connected the answer is.

Worker four checks the answer against a list of sixteen well-known, common misunderstandings that CS students often have — things like mixing up 'last in, first out' and 'first in, first out,' which is exactly the mistake we saw in the live example earlier. If a match is found, the student doesn't just lose points — they get a specific note about what they got confused, plus a hint on how to think about it correctly."

---

## Slide 12 — Layer 5: Score Synthesis & Verification *(the important one, slow down)*

"Now here's worker five, and this is the part I most want everyone to really absorb, because it's the most honest and most surprising finding in this whole talk.

You'd expect the final grade to be a careful, balanced combination of everything the first four workers found. And that combination *is* calculated. But then there's one more step: an independent AI review. The system takes the raw student answer, plus everything the first four workers found, and asks the AI one more time to make its own final, holistic judgment.

And here's the honest, slightly uncomfortable finding: **in the version we actually use, that final AI judgment completely overrides everything else.** The careful map-comparison score still gets calculated, and the AI does get to *read* it as background information — so it's not entirely ignored — but mathematically, it contributes *zero* to the final number. The AI's own opinion, by itself, *is* the grade.

Why does this matter? Because when we tested that careful map-comparison score *on its own* — without the AI's final judgment — it actually did *worse* than just asking the AI to grade the answer directly, with no map-comparison at all. Meaningfully worse. So right now, most of this system's accuracy comes from the AI's own judgment, not from the clever knowledge-graph comparison the whole system is named after. That doesn't mean the knowledge graph is useless — it still produces the detailed, specific feedback students see — it just means that feedback-generation and score-accuracy are, right now, two separate jobs, and only one of them is being pulled off by the knowledge graph.

I'm choosing not to fully explain why that happens today — that requires actual test results, which is next talk's material — but I wanted you to sit with that question, because it's the central tension in this whole project."

---

## Slide 13 — The Expert Knowledge Graph

"Layer two's comparisons are only as good as the expert map behind them. I built this map by hand — 101 different ideas, and 138 labeled connections between them, covering eight different types of relationships. And importantly, I finished building this map *before* I ran any tests on it — so I couldn't accidentally shape the map to make my results look better after the fact.

Three rules I followed while building it: it needed to cover every concept a normal intro Data Structures course would teach; every idea needed one official name plus a list of other common ways people phrase it; and every connection between ideas had to have a specific, meaningful label — not just a vague 'these are related' link."

---

## Slide 14 — What the Student Actually Sees

"All of that work exists for one reason: to give the student something genuinely useful, not just a number. Here's what they actually see: which ideas they got right and which they missed, written out plainly. Which connections they claimed that are actually wrong. A note on how deep or sophisticated their thinking was, not just whether it was correct. And if they hit one of those sixteen common misunderstandings, a specific explanation of exactly what they got confused, plus a hint on how to think about it correctly.

One more honest note: building the expert map and the misunderstanding list took real time and effort *up front*. But it's a one-time cost — once it's built, it can be reused for every single student's answer after that, without extra effort."

---

## Slide 15 — Scope & Limitations

"I want to be honest about what this system can't do yet, rather than let someone discover it themselves later.

First: I've only tested this with one specific AI model so far. I don't yet know if it works the same way with a different AI.

Second: I built the expert map and the misunderstanding list by myself, as one person. I did a small self-check to see how consistent the system's own judgments are, and got a 'moderate' agreement result — but I want to be precise: that's just me checking my own work, not an outside expert independently confirming it's correct.

Third: the expert map only covers one specific topic — Data Structures. I haven't tested whether this approach works for other Computer Science topics yet.

I'm telling you these limitations up front, on purpose, rather than hoping nobody asks."

---

## Slide 16 — Coming in Seminar 2

"That's the full picture of how the system is built. Next time, I'll answer the questions this talk deliberately leaves open: Does this system actually beat a plain AI grader in a fair test? Why does the careful map-comparison score, on its own, actually perform worse than just asking the AI directly? And that promising 'ask three times and take the most common answer' technique I mentioned — what happened when we tested it more fairly?"

---

## Slide 17 — References

"One last slide before questions — where the numbers on that earlier comparison slide actually came from. These are the real, published research papers I checked those numbers against myself — not something I copied from someone else's summary of them. And worth mentioning plainly: one of the four sources I originally had written down turned out to be wrong — I couldn't find any real paper matching it, so I tracked down the correct paper and fixed it here. I'd rather show you I caught and corrected my own mistake than quietly hope nobody checks."

**Close:** "Thank you — happy to take questions."

---

## If someone asks something technical mid-talk and you need a simple-English fallback

- **"What's an AI language model?"** → A computer program trained on huge amounts of text so it can read and write in a very human-like way — the same basic kind of technology behind tools like ChatGPT.
- **"What's a correlation score / trust score?"** → A number from 0 to 1 showing how closely two sets of scores agree with each other — 1 means they always agree, 0 means there's no relationship at all.
- **"What's a knowledge graph / map of ideas?"** → A diagram where each idea is a box, and lines between boxes show how those ideas connect — like a mind-map, but built and checked systematically rather than drawn freehand.
- **"Why does it matter that the map was built before testing?"** → It's the same reason a test's answer key gets locked in before students take the exam — so nobody can be accused of quietly adjusting the answer key afterward to make the results look better.
