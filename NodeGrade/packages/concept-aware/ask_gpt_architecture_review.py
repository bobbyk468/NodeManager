#!/usr/bin/env python3
"""
ask_gpt_architecture_review.py -- one-shot consultation call to GPT
(via OpenRouter) with the full problem statement + proposed solution for
ConceptGrade's architecture redesign, asking for critique. Single call,
not a batch job.

Run:
    python3 ask_gpt_architecture_review.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from conceptgrade.llm_client import LLMClient, load_openrouter_key

PROBLEM_STATEMENT = """
You are being asked to critique a research/engineering decision for an automated
short-answer grading (ASAG) system called ConceptGrade. Please read the full
problem statement and proposed solution below, then give a direct, critical
review -- agree, disagree, or push back on any part, and flag anything we may
be missing. Be concise but substantive.

## Background

ConceptGrade grades free-text student answers to CS questions. Its original
architecture: (1) extract a concept graph from the student's answer via LLM,
(2) compare it against an expert-curated domain knowledge graph, (3) run
misconception/false-belief detection, (4) classify cognitive depth (Bloom's/SOLO),
(5) combine all of this into a single numeric score via a hand-set weighted
formula: knowledge = concept_coverage*0.45 + relationship_accuracy*0.35 +
integration_quality*0.20; depth = blooms*0.55 + solo*0.45; composite =
(knowledge*0.60 + depth*0.40) * (1 - misconception_penalty). This composite is
then blended with an LLM "holistic score" (5%/95%), and finally with an LLM
"verifier" score that re-reads all the evidence and gives its own 0-5 judgment,
via final = (1-w)*composite + w*verifier, with w (verifier_weight) currently
set to 1.0 in every deployed/reported configuration -- meaning the numeric
composite formula's contribution is, in practice, already fully zeroed out and
the verifier's LLM judgment is the only thing that reaches the final score.

## The problem

The original research goal was to show this KG-grounded pipeline beats plain
zero-shot LLM grading (question + reference answer + student answer, no KG,
one LLM call). Extensive testing says it doesn't, and the specific numeric
composite formula is the reason:

1. Two of the composite's three inputs are independently known-broken:
   `concept_coverage` is self-referentially tautological in production (the
   "expected concepts" ground truth silently defaults to the student's own
   extracted concepts, so it always scores near 1.0 for anyone who mentions
   at least one relevant-sounding term). `relationship_accuracy` is zeroed by
   design for ~21% of genuinely correct answers (ones that don't require
   stating a relationship between concepts).
2. FIVE separate fix attempts for these two defects (exclude the broken
   dimension and renormalize; three different automated "real" ground-truth
   sources for concept_coverage; a joint fix; a neutral-prior degradation)
   were tested end-to-end on 1,156 real graded samples. ALL of them made
   things measurably worse on aggregate metrics (MAE, correlation, false-
   penalty rate) than just leaving the known-broken formula alone.
3. On two different LLM backbones used as the pipeline's "brain" (OpenAI
   GPT-5.6-terra and DeepSeek-chat-v3.1, tested via OpenRouter, n=298-300 real
   samples each): swapping to a stronger backbone doesn't help -- the full
   pipeline (still at verifier_weight=1.0) underperforms that same backbone's
   own zero-shot judgment by 6-20% MAE, statistically significant.
4. 5-fold cross-validated tuning of the verifier_weight blend, on both
   backbones, converges on w=1.0 in every fold -- i.e., cross-validation
   itself confirms "don't blend the composite in at any weight" is already
   optimal. No tuning rescues it.
5. A supervised ridge-regression model, given all the individual raw
   sub-scores (concept_coverage, relationship_accuracy, integration_quality,
   Bloom's, SOLO, misconception count) PLUS the verifier's own score as
   features, with leave-one-question-out cross-validation, does not beat the
   verifier score alone -- adding the KG sub-scores as extra learned features
   makes predictions worse, not better, on both backbones.
6. HOWEVER: naive raw LLM scores (both zero-shot and verifier) turn out to
   have a large, generic scale/bias miscalibration relative to human scores.
   A simple affine recalibration (intercept + scale, fit via the same
   leave-one-question-out CV) closes most of this gap for BOTH zero-shot and
   verifier scores. Once both are fairly recalibrated: on GPT, the verifier
   (which sees KG-derived evidence -- concept coverage, misconceptions,
   Bloom's/SOLO -- as prompt CONTEXT, not as a blended number) beats
   recalibrated zero-shot by 10.6% MAE (p<0.001). On DeepSeek, this does NOT
   replicate cleanly -- recalibrated zero-shot is actually marginally BETTER
   than the recalibrated verifier alone; only a small ensemble of the two
   together gives a borderline-significant edge (+4.2%, p=0.048).

## What we currently believe, and want checked

- The numeric composite scoring formula (step 5 in the original architecture)
  is the specific broken piece, confirmed across 8 independent tests spanning
  two investigation rounds months apart. We plan to STOP trying to fix or
  tune it as a scoring mechanism.
- We plan to KEEP the knowledge graph, concept extraction, and misconception
  detection, but repurpose them purely as evidence generators fed to the
  LLM verifier's prompt as context (which the verifier already receives) and
  as user-facing feedback (matched/missing concepts, flagged misconceptions)
  -- NOT as separate numeric scores that get mathematically blended in.
- We plan to add a formal post-hoc calibration step (affine, intercept+scale)
  applied to the verifier's raw output, since this is the one intervention
  that has actually shown a real, validated improvement.
- Open question we have NOT resolved: should this calibration be (a) fit
  once per backbone model and reused across datasets/deployments, (b) fit
  once globally, pooled across backbones and datasets, on the theory that
  the miscalibration is a generic "LLM scoring compresses/biases the range"
  artifact rather than something backbone- or dataset-specific, or (c) fit
  per-deployment on a small operator-provided calibration set. We want the
  system to be model-independent/universal (not tuned to one specific LLM's
  quirks), given that most frontier LLMs already substantially agree with
  each other on holistic judgments.

## Question for you

1. Does the diagnosis (the numeric composite formula is unsalvageable; the
   value is in evidence-in-context + calibration, not symbolic score fusion)
   hold up, or do you see a hole in this reasoning?
2. Between the three calibration options (per-backbone, global/pooled,
   per-deployment), which is most defensible for a genuinely "universal"
   system, and why? Is there a better option we haven't considered (e.g.
   isotonic regression instead of affine, quantile mapping, no calibration
   at all and instead fixing the verifier's own scoring instructions)?
3. Given DeepSeek's result didn't clearly replicate GPT's "verifier beats
   zero-shot" finding, is it premature to call this "model-independent," or
   is the more conservative claim (the composite formula adds no value,
   which DID replicate) the right thing to lead with?
4. Any other structural risks you'd flag in this redesign before we
   implement it?

Please be direct and critical -- we would rather hear a hard "this doesn't
hold up" now than after implementing it.
"""


def main():
    key = load_openrouter_key()
    client = LLMClient(api_key=key)
    print("Sending architecture review request to GPT-5.6-terra...\n")
    resp = client.chat.completions.create(
        model="openai/gpt-5.6-terra",
        messages=[{"role": "user", "content": PROBLEM_STATEMENT}],
        temperature=0.2,
        max_tokens=4096,
    )
    text = resp.choices[0].message.content
    out_path = BASE / "data" / "gpt_architecture_review.md"
    out_path.write_text(text)
    print(text)
    print(f"\n\n[saved] {out_path}")
    try:
        cost = resp.usage.cost
        print(f"[cost] ${cost}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
