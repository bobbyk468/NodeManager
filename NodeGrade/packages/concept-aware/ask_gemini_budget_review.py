#!/usr/bin/env python3
"""
ask_gemini_budget_review.py — single consultation call to gemini-2.5-flash
asking for feedback on the proposed validation API budget.

Sends ONE prompt with full context (paper state, removed sensitivities,
proposed tier breakdown, cost estimates) and saves the structured
response. Estimated cost: ~$0.02-0.05 for a single rich call.

Run:
    python ask_gemini_budget_review.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
ENV_PATH = BASE.parent / "backend" / ".env"

# Load Gemini API key from backend .env (same as smoke_run_mohler.py)
if "GEMINI_API_KEY" not in os.environ and ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            val = line.split("=", 1)[1].strip()
            # Strip surrounding quotes if present
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            os.environ["GEMINI_API_KEY"] = val
            break

if "GEMINI_API_KEY" not in os.environ:
    print("ERROR: GEMINI_API_KEY not set", file=sys.stderr)
    sys.exit(2)


CONSULTATION_PROMPT = """\
You are advising a PhD student on a Gemini API budget for an academic-paper
validation exercise. The student wants your honest, critical, technical
feedback. Be specific. Be skeptical. Suggest cheaper alternatives where
they exist. Flag methodological problems.

# Context

We have two papers about ConceptGrade, a 5-layer ASAG (Automated Short
Answer Grading) pipeline using gemini-2.5-flash:

- **Paper 1 (NLP/EdAI venue):** ML accuracy results. Headline: 32.4% MAE
  reduction on Mohler 2011 (n=120, 10 questions × 12 responses).
  Cross-dataset: DigiKlausur (n=646, d_z=-0.07, marginal),
  Kaggle ASAG (n=473, d_z=-0.03, null). Random-effects pool d_z = -0.10
  with 95% CI [-0.21, +0.01] (CI crosses zero, I² = 70%).

- **Paper 2 (IEEE VIS 2027):** Visual analytics dashboard for educator
  co-auditing. Includes 5-section dashboard, pre-registered N=64 user study
  (not yet run; placeholders throughout).

# Real cached data we already have ($0 to use)

- Mohler n=120 with C_LLM (gemini-2.5-flash, no KG context) vs C5_fix
  (with KG context) scores per sample
- DigiKlausur n=646, Kaggle ASAG n=473 same comparison
- LRM (DeepSeek-R1) reasoning traces for all 1,239 samples
- Concept-only and taxonomy-only ablations (single Gemini calls with
  restricted context): MAE 0.217, 0.229
- Sentence-BERT (MiniLM and MPNet) frozen baselines on Mohler n=90

# What we had to REMOVE because we never actually computed them

(Each of these would need new API calls to add back honestly:)

1. **4-way pipeline-layer ablation** ("TRM-only" config, "Verifier-only"
   config with KG-vs-Verifier disambiguation). We currently only have
   C_LLM and C5_fix; no intermediate configurations.

2. **kg_weight sensitivity** (synthesis-step parameter, 4 values:
   0.01, 0.05, 0.10, 0.50). The cached batch responses are
   post-synthesis and the underlying signal-component vectors aren't
   stored, so we cannot reconstruct alternative kg_weight scores
   without re-querying the LLM.

3. **Ensemble weight sensitivity** (α, β, γ grid search over the
   simplex summing to 1.0, evaluated on 30-sample dev split). Same
   reconstruction barrier as kg_weight.

4. **Real human-IRR proxy on the 16-entry misconception taxonomy.**
   Currently we have a machine-IRR pilot with κ_macro=0.29, κ_micro=0.33
   using two heuristic coders (KG-rule and lexical-overlap). A
   different-LLM second-coder pass would give a tighter lower bound.

# Other validation work we could do but haven't

5. **Frontier LLM baseline** (GPT-4-turbo or Claude 3.5 Sonnet on
   Mohler n=120) to defuse the "controlled-LLM is an excuse not to
   compare to frontier" reviewer attack.

6. **Full Mohler 630-sample evaluation** (the 510 samples we didn't
   include because they fall outside our KG's coverage; would need
   KG extension).

7. **Cross-dataset Verifier ablation** (with/without DeepSeek-R1
   verifier on DigiKlausur and Kaggle ASAG).

8. **Paraphrase robustness** (3× paraphrase each Mohler answer, re-grade,
   check prediction stability).

# Proposed budget tiers

**Tier 1 (~$15):**
- Items 1-4 above
- Estimated ~2,160 grading calls

**Tier 2 (~$50):**
- Tier 1 + items 5, 7, 8
- Estimated ~5,400 calls (mix of grading + LRM)

**Tier 3 (~$150-300):**
- Tier 2 + SciEntsBank (SemEval-2013, ~10k samples) + BEETLE + multiple
  frontier LLMs

# What we want from you

Be specific, concrete, and skeptical. Address each of the following:

1. **Cost estimates.** Are our per-call cost assumptions right
   (gemini-2.5-flash ~$0.001-0.002/call, DeepSeek-R1 ~$0.003-0.015/call
   for LRM trace)? Where are we likely undercounting?

2. **Call-count estimates.** Is "2,160 calls" actually reasonable for
   Tier 1? What hidden multipliers are we missing (retries, cache
   misses, multi-stage pipelines)?

3. **Tier choice.** The student thinks $150 is too much. What does the
   minimum genuinely-useful budget look like? Where does adding $5 more
   stop helping?

4. **Cheaper alternatives.** What can we do with the cached data alone
   (without new API calls) that we haven't thought of?

5. **Methodological issues.** Are any of items 1-8 above poorly
   designed? Would a reviewer have a counter-attack even if we ran
   them?

6. **Hidden risks.** Where are we most likely to overspend by 2-5x
   without realizing it?

7. **One concrete recommendation.** If you had to pick the single most
   useful $20 of API spend, what would it be?

Respond as structured JSON with these keys:
{
  "cost_assumption_review": "...",
  "call_count_review": "...",
  "tier_recommendation": "tier1" | "tier1plus" | "tier2" | "skip",
  "cheaper_alternatives": [...],
  "methodological_concerns": [...],
  "overspend_risks": [...],
  "single_best_20_dollar_spend": "...",
  "overall_advice_summary": "..."
}
"""


def main() -> int:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Installing google-genai…", flush=True)
        os.system(f"{sys.executable} -m pip install google-genai")
        from google import genai
        from google.genai import types

    print("[gemini-budget] Initialising client (gemini-2.5-flash)…", flush=True)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    print(f"[gemini-budget] Prompt: {len(CONSULTATION_PROMPT)} chars "
          f"(~{len(CONSULTATION_PROMPT) // 4} input tokens)", flush=True)

    t0 = time.time()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=CONSULTATION_PROMPT,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )
    latency_ms = round((time.time() - t0) * 1000, 1)

    raw = response.text
    print(f"[gemini-budget] Response: {len(raw)} chars in {latency_ms} ms",
          flush=True)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[gemini-budget] WARNING: response not valid JSON — saving raw")
        parsed = {"_raw": raw, "_parse_error": str(e)}

    # Estimate actual cost
    usage = getattr(response, "usage_metadata", None)
    if usage:
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        cand_tokens = getattr(usage, "candidates_token_count", None)
        # gemini-2.5-flash pricing (as of mid-2026):
        # input $0.30/1M, output $2.50/1M
        cost = ((prompt_tokens or 0) / 1e6) * 0.30 + ((cand_tokens or 0) / 1e6) * 2.50
        print(f"[gemini-budget] Token usage: "
              f"in={prompt_tokens}, out={cand_tokens}, "
              f"cost ≈ ${cost:.4f}")
        parsed["_meta"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": cand_tokens,
            "actual_cost_usd_est": round(cost, 4),
            "latency_ms": latency_ms,
            "model": "gemini-2.5-flash",
        }

    out_path = BASE / "data" / "gemini_budget_review.json"
    out_path.write_text(json.dumps(parsed, indent=2))
    print(f"\n[gemini-budget] Saved: {out_path}")

    # Pretty-print summary
    print("\n" + "=" * 70)
    print("GEMINI'S RESPONSE")
    print("=" * 70)
    if "_raw" in parsed:
        print(parsed["_raw"][:3000])
    else:
        for k in ["overall_advice_summary", "tier_recommendation",
                  "single_best_20_dollar_spend",
                  "cost_assumption_review",
                  "call_count_review",
                  "cheaper_alternatives",
                  "methodological_concerns",
                  "overspend_risks"]:
            v = parsed.get(k)
            if v is None:
                continue
            print(f"\n## {k}")
            if isinstance(v, list):
                for item in v:
                    print(f"  - {item}")
            else:
                print(f"  {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
