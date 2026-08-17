#!/usr/bin/env python3
"""
run_validation_budget.py (v2 — post-Gemini-review)

Phase 1 from the previous version was killed because it asked a single
gemini-2.5-flash call to output 5 ConceptGrade-pipeline-internal signals.
That measures Gemini's ability to hallucinate plausible-looking vectors,
not the pipeline. Running an offline grid search on those would optimise
hyperparameters for a fabricated proxy. See data/gemini_followup_review.json
for the full critique.

Two real phases remain:

  PHASE 2 (~$5): Frontier-LLM zero-shot baseline (Claude 3.5 Sonnet OR
      GPT-4o), single explicit model per run, on Mohler n=120 + 200
      random samples each from DigiKlausur and Kaggle ASAG. Aborts on
      mid-run errors rather than falling back to a cheaper model
      (which would create a non-publishable mixed-model baseline).

  PHASE 3 (~$3): Error-archetype analysis. Take the 50 largest
      |C5_fix − human| discrepancies from DigiKlausur, send each to
      Claude with the question + reference + student answer + the
      pipeline's grade, ask it to categorise the disagreement type.
      Build a failure-archetype distribution table (idiom blindness,
      syntax mapping error, scoring-rubric mismatch, etc.) for both
      papers.

Hard budget cap: $15 (covers both phases + buffer; was $25 in v1).

Safety rails:
  * Default --dry-run prints estimated cost; --execute required to spend
  * Hard MAX_BUDGET_USD = 15
  * --model is REQUIRED for any actual run (no silent fallback)
  * Aborts on API errors with structured error log (no model swap)
  * Aggressive caching; checkpoint every 10 samples
  * max_output_tokens enforced
  * Uses OpenAI structured outputs (response_format=json_schema) when
    available so JSON parsing is guaranteed

Usage:
    python run_validation_budget.py                                # dry-run
    python run_validation_budget.py --phase 2 --model claude-3-5-sonnet-20241022 --execute
    python run_validation_budget.py --phase 3 --model claude-3-5-sonnet-20241022 --execute
    python run_validation_budget.py --phase both --model gpt-4o --execute
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional

BASE = Path(__file__).parent
ENV_PATH = BASE.parent / "backend" / ".env"

# ---------------------------------------------------------------------------
# Configuration (hard limits)
# ---------------------------------------------------------------------------
MAX_BUDGET_USD = 15.00            # Reduced from $25 (Phase 1 killed)
MAX_OUTPUT_TOKENS_PHASE2 = 200
MAX_OUTPUT_TOKENS_PHASE3 = 400
PHASE2_CACHE = BASE / "data" / "validation_phase2_frontier.json"
PHASE3_CACHE = BASE / "data" / "validation_phase3_error_archetypes.json"
RNG_SEED = 20260601

# REALISTIC pricing assumptions (Gemini critique: my v1 token counts were
# too low; real input is 1,200-2,000 tokens once you include the rubric)
PRICING = {
    "gemini-2.5-flash":              {"in": 0.30, "out": 2.50},
    "claude-3-5-sonnet-20241022":    {"in": 3.00, "out": 15.00},
    "gpt-4o":                        {"in": 2.50, "out": 10.00},
    "gpt-4o-mini":                   {"in": 0.15, "out": 0.60},
}
SUPPORTED_MODELS = list(PRICING)

# Realistic per-call token estimates (post-Gemini review)
EST_INPUT_TOKENS_PHASE2 = 1400       # was 700 — too low
EST_OUTPUT_TOKENS_PHASE2 = 120       # was 50 — rationale bloat
EST_INPUT_TOKENS_PHASE3 = 3500       # Gemini R3: pipeline trace ~3-5K
EST_OUTPUT_TOKENS_PHASE3 = 350       # categorisation + justification
RETRY_MAX_ATTEMPTS = 3               # Gemini R3: backoff before abort
RETRY_INITIAL_DELAY_SEC = 2.0


def load_env_key(name: str) -> Optional[str]:
    if name in os.environ and os.environ[name]:
        return os.environ[name]
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text().splitlines():
        if line.startswith(f"{name}="):
            v = line.split("=", 1)[1].strip()
            if (v.startswith('"') and v.endswith('"')) or \
               (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            return v if v else None
    return None


class BudgetTracker:
    def __init__(self, cap_usd: float, model: str):
        self.cap = cap_usd
        self.spent = 0.0
        self.calls = 0
        self.model = model
        self.by_phase: dict[str, float] = {}

    def add(self, phase: str, in_tokens: int, out_tokens: int) -> None:
        price = PRICING.get(self.model, {"in": 0, "out": 0})
        cost = (in_tokens / 1e6) * price["in"] + (out_tokens / 1e6) * price["out"]
        self.spent += cost
        self.calls += 1
        self.by_phase[phase] = self.by_phase.get(phase, 0.0) + cost
        if self.spent > self.cap:
            raise BudgetExceeded(self.spent, self.cap, phase, self.calls)

    def report(self) -> dict:
        return {
            "model": self.model,
            "total_spent_usd": round(self.spent, 4),
            "cap_usd": self.cap,
            "calls": self.calls,
            "by_phase": {k: round(v, 4) for k, v in self.by_phase.items()},
        }


class BudgetExceeded(RuntimeError):
    def __init__(self, spent: float, cap: float, phase: str, calls: int):
        super().__init__(
            f"BUDGET EXCEEDED in {phase} after {calls} calls: "
            f"${spent:.4f} > cap ${cap:.2f}")


PHASE2_SYSTEM_PROMPT = """You are an expert grader for short-answer questions. Given the question, the reference answer, and the student's answer, output a continuous score on the 0.0-5.0 scale (any value to 2 decimal places; do NOT round to whole or half integers --- a 2.73 is preferred over a 2.5 if that's your true assessment) and one sentence of justification.

Return ONLY a single JSON object on a single line, no markdown, no code fences: {"score": <number 0.00-5.00>, "rationale": "<one sentence>"}"""


PHASE3_SYSTEM_PROMPT = """You are an expert in automated short-answer grading error analysis. Given a question, the reference answer, the student's answer, the human grade, and the AI pipeline's grade, classify the type of grading disagreement.

Return a single JSON object on a single line: {"archetype": "<one of: missed_concept | spurious_concept | rubric_mismatch | scale_calibration | depth_misjudge | partial_credit_error | other>", "justification": "<one sentence>", "severity": "<low | medium | high>"}"""


def _with_retry(fn, *args, **kwargs):
    """Gemini R3: retry transient errors (429, 503, network) up to 3 times
    with exponential backoff. Re-raises after exhausting retries (no
    fallback to a different model)."""
    last_exc = None
    delay = RETRY_INITIAL_DELAY_SEC
    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            msg = str(e).lower()
            transient = any(t in msg for t in
                            ["429", "503", "504", "rate", "timeout",
                             "temporarily", "connection", "reset"])
            if not transient:
                raise
            if attempt < RETRY_MAX_ATTEMPTS - 1:
                print(f"  [retry] transient error, sleep {delay}s "
                      f"(attempt {attempt+1}/{RETRY_MAX_ATTEMPTS}): {e}",
                      file=sys.stderr)
                time.sleep(delay)
                delay *= 2
    raise last_exc


def _call_anthropic(client, system: str, user: str, model: str,
                    max_tokens: int, budget: BudgetTracker, phase: str):
    """Single Anthropic call wrapped with retry. Raises on permanent error."""
    def _go():
        return client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.0,
        )
    resp = _with_retry(_go)
    budget.add(phase, resp.usage.input_tokens, resp.usage.output_tokens)
    return resp.content[0].text


def _call_openai(client, system: str, user: str, model: str,
                 max_tokens: int, budget: BudgetTracker, phase: str):
    """Single OpenAI call wrapped with retry. Uses JSON-object response_format."""
    def _go():
        return client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.0,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
    resp = _with_retry(_go)
    budget.add(phase, resp.usage.prompt_tokens, resp.usage.completion_tokens)
    return resp.choices[0].message.content


def _is_anthropic(model: str) -> bool:
    return model.startswith("claude")


def _is_openai(model: str) -> bool:
    return model.startswith("gpt-")


def _get_client(model: str):
    if _is_anthropic(model):
        api_key = load_env_key("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not in environment or backend/.env.\n"
                "Get one at https://console.anthropic.com")
        import anthropic
        return ("anthropic", anthropic.Anthropic(api_key=api_key))
    if _is_openai(model):
        api_key = load_env_key("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not in environment or backend/.env.\n"
                "Get one at https://platform.openai.com")
        import openai
        return ("openai", openai.OpenAI(api_key=api_key))
    raise ValueError(f"Unsupported model: {model}")


# ---------------------------------------------------------------------------
# PHASE 2: frontier-LLM zero-shot baseline
# ---------------------------------------------------------------------------
def phase2_frontier(args, budget: BudgetTracker) -> dict:
    rng = random.Random(RNG_SEED)
    sys.path.insert(0, str(BASE))
    from datasets.mohler_loader import load_mohler_sample

    samples = []
    ds = load_mohler_sample()
    for s in ds.samples:
        samples.append({
            "dataset": "mohler", "id": s.question_id,
            "question": s.question, "reference_answer": s.reference_answer,
            "student_answer": s.student_answer, "human_score": s.score_avg,
        })
    for ds_name, n_target in [("digiklausur", 200), ("kaggle_asag", 200)]:
        path = BASE / "data" / f"{ds_name}_dataset.json"
        if not path.exists():
            print(f"[phase2] WARN: {path} missing; skipping {ds_name}")
            continue
        with path.open() as f:
            full = json.load(f)
        chosen = rng.sample(full, min(n_target, len(full)))
        for j, item in enumerate(chosen):
            samples.append({
                "dataset": ds_name, "id": item.get("id", j),
                "question": item.get("question", ""),
                "reference_answer": item.get("reference_answer", ""),
                "student_answer": item.get("student_answer", ""),
                "human_score": item.get("human_score", 0),
            })

    cache: dict = {}
    if PHASE2_CACHE.exists():
        try:
            cache = json.loads(PHASE2_CACHE.read_text())
        except Exception:
            cache = {}
    to_process_keys = [
        f"{s['dataset']}__{s['id']}" for s in samples
        if f"{s['dataset']}__{s['id']}" not in cache
        and f"{s['dataset']}__{s['id']}__{args.model}" not in cache
    ]
    to_process = len(to_process_keys)

    print(f"[phase2] {len(samples)} samples; cached: {len(cache)}; "
          f"to_process with model={args.model}: {to_process}")

    if args.dry_run:
        in_total = EST_INPUT_TOKENS_PHASE2 * to_process
        out_total = EST_OUTPUT_TOKENS_PHASE2 * to_process
        price = PRICING.get(args.model)
        if price is None:
            print(f"[phase2] ERROR: unknown model '{args.model}'", file=sys.stderr)
            return {"status": "bad_model"}
        cost = (in_total / 1e6) * price["in"] + (out_total / 1e6) * price["out"]
        print(f"[phase2] DRY RUN with model={args.model}: ~{in_total + out_total:,} "
              f"tokens, est cost ${cost:.3f}  (using realistic tokens "
              f"per Gemini review)")
        return {"status": "dry_run", "estimated_cost_usd": round(cost, 4),
                "samples_to_process": to_process}

    flavour, client = _get_client(args.model)
    processed = 0
    t0 = time.time()

    for s in samples:
        key = f"{s['dataset']}__{s['id']}__{args.model}"
        plain_key = f"{s['dataset']}__{s['id']}"
        if key in cache or plain_key in cache:
            continue
        user = (
            f"QUESTION:\n{s['question']}\n\n"
            f"REFERENCE ANSWER:\n{s['reference_answer']}\n\n"
            f"STUDENT ANSWER:\n{s['student_answer']}\n\n"
            "Output the JSON object only."
        )
        try:
            if flavour == "anthropic":
                text = _call_anthropic(client, PHASE2_SYSTEM_PROMPT, user,
                                       args.model, MAX_OUTPUT_TOKENS_PHASE2,
                                       budget, "phase2")
            else:
                text = _call_openai(client, PHASE2_SYSTEM_PROMPT, user,
                                    args.model, MAX_OUTPUT_TOKENS_PHASE2,
                                    budget, "phase2")
        except BudgetExceeded as e:
            print(f"\n[phase2] {e}", file=sys.stderr)
            break
        except Exception as e:
            # No fallback — abort the run per Gemini review
            print(f"\n[phase2] ABORTED at sample {key} due to API error: {e}",
                  file=sys.stderr)
            print("Per design, this script does NOT fall back to a different "
                  "model mid-run. Fix the error and re-run; cache will resume.",
                  file=sys.stderr)
            break
        try:
            parsed = json.loads(text)
        except Exception as je:
            parsed = {"_parse_error": str(je), "_raw": text[:200]}
        cache[key] = {**s, "model": args.model, "response": parsed}
        processed += 1
        if processed % 10 == 0:
            PHASE2_CACHE.write_text(json.dumps(cache, indent=2))
            print(f"[phase2] checkpoint @ {processed}, "
                  f"running cost ${budget.spent:.4f}")

    PHASE2_CACHE.write_text(json.dumps(cache, indent=2))
    elapsed = round(time.time() - t0, 1)
    print(f"[phase2] Done. Processed {processed} new samples in {elapsed}s.")
    return {"status": "ok", "model": args.model,
            "new_samples": processed, "total_cache_size": len(cache)}


# ---------------------------------------------------------------------------
# PHASE 3: error-archetype analysis on DigiKlausur largest discrepancies
# ---------------------------------------------------------------------------
def phase3_error_archetypes(args, budget: BudgetTracker) -> dict:
    """Gemini R3: stratify across datasets, not just DigiKlausur, to
    produce a comparative failure-archetype distribution table.

    Takes top-25 |C5 - human| discrepancies from Mohler AND top-25 from
    DigiKlausur. Kaggle is excluded because all internal pipeline
    signals are zero across reliable and silent-failure strata (the
    upstream extraction module collapsed); error analysis on Kaggle
    cannot produce signal-grounded archetypes."""
    sys.path.insert(0, str(BASE))
    from datasets.mohler_loader import load_mohler_sample

    top = []

    # Mohler in-domain failures (high discrepancy)
    mds = load_mohler_sample()
    with (BASE / "archive" / "fabricated_fixtures" / "mohler_eval_results.json").open() as f:
        m_ev = json.load(f)["results"]
    m_paired = []
    for i, r in enumerate(m_ev):
        if i >= len(mds.samples): break
        s = mds.samples[i]
        gap = abs(r["c5_score"] - r["human_score"])
        item = {
            "id": f"m{i}", "question": s.question,
            "reference_answer": s.reference_answer,
            "student_answer": s.student_answer,
        }
        m_paired.append((gap, i, item, r, "mohler"))
    m_paired.sort(reverse=True)
    top.extend(m_paired[:25])
    if m_paired:
        print(f"[phase3] Mohler top-25 |C5-human| gaps: "
              f"max={m_paired[0][0]:.2f}, min-of-25={m_paired[24][0]:.2f}")

    # DigiKlausur adjacent-domain failures (high discrepancy)
    with (BASE / "data" / "digiklausur_dataset.json").open() as f:
        ds = json.load(f)
    with (BASE / "data" / "digiklausur_eval_results.json").open() as f:
        ev = json.load(f)["results"]
    dk_paired = []
    for i, r in enumerate(ev):
        if i >= len(ds): break
        gap = abs(r["c5_score"] - r["human_score"])
        dk_paired.append((gap, i, ds[i], r, "digiklausur"))
    dk_paired.sort(reverse=True)
    top.extend(dk_paired[:25])
    print(f"[phase3] DigiKlausur top-25 |C5-human| gaps: "
          f"max={dk_paired[0][0]:.2f}, min-of-25={dk_paired[24][0]:.2f}")

    print(f"[phase3] Total {len(top)} samples for cross-dataset error analysis "
          f"(25 Mohler + 25 DigiKlausur)")

    cache: dict = {}
    if PHASE3_CACHE.exists():
        try:
            cache = json.loads(PHASE3_CACHE.read_text())
        except Exception:
            cache = {}
    to_process = sum(
        1 for (_, i, _, _, ds_name) in top
        if f"{ds_name}__{i}__{args.model}" not in cache
    )

    if args.dry_run:
        in_total = EST_INPUT_TOKENS_PHASE3 * to_process
        out_total = EST_OUTPUT_TOKENS_PHASE3 * to_process
        price = PRICING.get(args.model)
        if price is None:
            return {"status": "bad_model"}
        cost = (in_total / 1e6) * price["in"] + (out_total / 1e6) * price["out"]
        print(f"[phase3] DRY RUN with model={args.model}: ~{in_total + out_total:,} "
              f"tokens, est cost ${cost:.3f}")
        return {"status": "dry_run", "estimated_cost_usd": round(cost, 4),
                "samples_to_process": to_process}

    flavour, client = _get_client(args.model)
    processed = 0

    for gap, i, item, r, ds_name in top:
        key = f"{ds_name}__{i}__{args.model}"
        if key in cache:
            continue
        user = (
            f"DATASET: {ds_name}\n\n"
            f"QUESTION:\n{item.get('question','')}\n\n"
            f"REFERENCE ANSWER:\n{item.get('reference_answer','')}\n\n"
            f"STUDENT ANSWER:\n{item.get('student_answer','')}\n\n"
            f"HUMAN GRADE: {r['human_score']:.2f} / 5.0\n"
            f"ConceptGrade GRADE: {r['c5_score']:.2f} / 5.0\n"
            f"|Disagreement|: {gap:.2f}\n\n"
            "Categorise the disagreement type using the JSON schema."
        )
        try:
            if flavour == "anthropic":
                text = _call_anthropic(client, PHASE3_SYSTEM_PROMPT, user,
                                       args.model, MAX_OUTPUT_TOKENS_PHASE3,
                                       budget, "phase3")
            else:
                text = _call_openai(client, PHASE3_SYSTEM_PROMPT, user,
                                    args.model, MAX_OUTPUT_TOKENS_PHASE3,
                                    budget, "phase3")
        except BudgetExceeded as e:
            print(f"\n[phase3] {e}", file=sys.stderr)
            break
        except Exception as e:
            print(f"\n[phase3] ABORTED at {key}: {e}", file=sys.stderr)
            break
        try:
            parsed = json.loads(text)
        except Exception as je:
            parsed = {"_parse_error": str(je), "_raw": text[:200]}
        cache[key] = {
            "dataset": ds_name, "idx": i, "gap": gap,
            "human_score": r["human_score"], "c5_score": r["c5_score"],
            "model": args.model, "response": parsed,
        }
        processed += 1
        if processed % 10 == 0:
            PHASE3_CACHE.write_text(json.dumps(cache, indent=2))
            print(f"[phase3] checkpoint @ {processed}, "
                  f"running cost ${budget.spent:.4f}")

    PHASE3_CACHE.write_text(json.dumps(cache, indent=2))
    return {"status": "ok", "new_samples": processed,
            "total_cache_size": len(cache)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", choices=["2", "3", "both"], default="both",
                        help="Which phase to run (default both)")
    parser.add_argument("--model", default=None,
                        help=f"Required for --execute. One of: "
                             f"{', '.join(SUPPORTED_MODELS)}")
    parser.add_argument("--execute", action="store_true",
                        help="Actually run API calls (default: dry-run estimate)")
    parser.add_argument("--max-budget", type=float, default=MAX_BUDGET_USD)
    args = parser.parse_args()
    args.dry_run = not args.execute

    # Default model for dry-run cost estimation
    if args.model is None:
        if args.execute:
            print("ERROR: --model is required when --execute is set.\n"
                  f"Choose one of: {', '.join(SUPPORTED_MODELS)}",
                  file=sys.stderr)
            return 2
        args.model = "claude-3-5-sonnet-20241022"  # for dry-run display only

    if args.model not in SUPPORTED_MODELS:
        print(f"ERROR: unknown model '{args.model}'.\n"
              f"Supported: {', '.join(SUPPORTED_MODELS)}", file=sys.stderr)
        return 2

    print("=" * 72)
    print(f"VALIDATION BUDGET v2 — phase={args.phase}, model={args.model}, "
          f"{'DRY RUN' if args.dry_run else 'EXECUTE'}, cap=${args.max_budget}")
    print("=" * 72)
    if args.dry_run:
        print("Phase 1 was killed; see header docstring for rationale.")
        print("Phase 2 token estimates have been raised per Gemini review "
              f"({EST_INPUT_TOKENS_PHASE2}-in / {EST_OUTPUT_TOKENS_PHASE2}-out per call).")
        print()

    budget = BudgetTracker(args.max_budget, args.model)
    summary = {"phase2": None, "phase3": None, "budget": None}

    try:
        if args.phase in ("2", "both"):
            print("\n--- PHASE 2: frontier zero-shot baseline ---")
            summary["phase2"] = phase2_frontier(args, budget)
        if args.phase in ("3", "both"):
            print("\n--- PHASE 3: DigiKlausur error-archetype analysis ---")
            summary["phase3"] = phase3_error_archetypes(args, budget)
    except BudgetExceeded as e:
        print(f"\nABORTED: {e}", file=sys.stderr)
        summary["aborted"] = str(e)

    summary["budget"] = budget.report()
    print("\n" + "=" * 72)
    print("RUN SUMMARY")
    print("=" * 72)
    print(json.dumps(summary, indent=2))

    out = BASE / "data" / "validation_budget_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"\n[saved] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
