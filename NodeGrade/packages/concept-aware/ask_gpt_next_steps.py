#!/usr/bin/env python3
"""
ask_gpt_next_steps.py -- focused consult on the two remaining open
threads after Finding 5's skepticism fix: GPT's question-clustered
significance gap, and DeepSeek's tie (not a win). Single call.

Run:
    python3 ask_gpt_next_steps.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from conceptgrade.llm_client import LLMClient, load_openrouter_key

PROBLEM_STATEMENT = """
Quick follow-up consult on a specific, narrow question -- context first,
then the actual question, please be direct.

## Where things stand

ConceptGrade is an ASAG (automated short-answer grading) system. After a
long diagnosis-and-fix cycle (documented in REPRODUCIBILITY.md Findings
1-5, if that means anything to you -- summarizing the relevant parts
below), the current state on real Mohler dataset samples (n=300 GPT,
n=298 DeepSeek, both via OpenRouter, both fairly recalibrated with
leave-one-question-out cross-validated affine calibration, verifier
prompt includes a "treat KG evidence skeptically, read the student answer
yourself first" instruction added after evidence was found to actively
hurt DeepSeek when trusted uncritically):

- **GPT-5.6-terra**: ConceptGrade beats zero-shot at the response level
  (MAE 0.431->0.382, +11.5%, p=5.8e-7) but NOT at question-clustered level
  (p=0.10, wins 8 of 11 questions). Only 11 distinct questions are
  represented in this 300-sample subset (the samples are the first 300 of
  a 1,262-sample, 46-question dataset, in dataset order, so they only
  span 11 of the 46 questions).
- **DeepSeek-chat-v3.1**: statistically tied with zero-shot (MAE
  0.437 vs 0.438, p=0.38, wins only 4/11 questions) -- no longer losing
  (it was actively losing before the skepticism fix), but not winning either.

The project's own pre-registered success bar (set before any of this data
was collected, specifically to avoid a repeat of an earlier retracted
finding in this same project) was: beat zero-shot at BOTH response-level
AND question-clustered level, p<0.05. GPT clears one bar, not both.
DeepSeek clears neither.

## My hypothesis on the GPT question-clustered gap -- asking you to check it

Question-clustered testing averages error per question (11 questions
here), then runs a paired test on just those 11 values -- much lower
power than the 300-sample response-level test. My hypothesis: the
non-significance is a POWER problem (only 11 paired observations, 8/11
in the right direction is suggestive but underpowered), not evidence the
effect isn't real -- and the fix is to run on a sample spanning MORE of
the dataset's 46 questions, not necessarily more total responses, to give
the clustered test more paired observations to work with.

## Questions

1. Is that the right diagnosis, or is there a more likely explanation for
   8/11 with p=0.10 that I should consider before spending API budget on
   a broader-question-coverage re-run? (E.g., could this instead indicate
   the effect really is inconsistent/concentrated in a few questions, and
   more questions would just as likely dilute it further?)
2. If the power hypothesis is right, roughly how many distinct questions
   would give a paired Wilcoxon test reasonable power to detect an effect
   of this apparent size (8/11 win rate, moderate effect), assuming the
   true effect and win-rate pattern holds as more questions are added?
3. For DeepSeek: it's now tied, not losing. Given evidence-in-context with
   a skepticism instruction didn't produce a net win there (only parity),
   is there a specific, cheap-to-test next lever you'd try before
   accepting parity as the final honest result for that backbone? (For
   context: things already tried and closed off -- numeric KG-formula
   scoring in any blend weight; naive evidence trust; this skepticism
   instruction as currently worded.) Or would you say further
   backbone-specific prompt tuning here risks exactly the kind of
   post-hoc overfitting this project has already been burned by once
   (a retracted ensemble-blend finding) and isn't worth pursuing further?
4. Anything else you'd prioritize before either of these threads, given
   remaining budget is small (~$3)?

Be direct -- if you think either of these directions is a bad use of
remaining budget, say so plainly rather than being agreeable.
"""


def main():
    key = load_openrouter_key()
    client = LLMClient(api_key=key)
    print("Sending next-steps consult to GPT-5.6-terra...\n")
    resp = client.chat.completions.create(
        model="openai/gpt-5.6-terra",
        messages=[{"role": "user", "content": PROBLEM_STATEMENT}],
        temperature=0.2,
        max_tokens=4096,
    )
    text = resp.choices[0].message.content
    out_path = BASE / "data" / "gpt_next_steps_consult.md"
    out_path.write_text(text)
    print(text)
    print(f"\n\n[saved] {out_path}")
    try:
        print(f"[cost] ${resp.usage.cost}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
