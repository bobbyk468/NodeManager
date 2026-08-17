#!/usr/bin/env python3
"""
run_budget_matched_baseline.py — Experiment #1 of 4 decisive experiments
(independent review round 4): a call-budget-matched LLM baseline.

Motivation
----------
The evaluated C5_fix configuration issues 7 LLM calls per graded response
(3-way self-consistency concept extraction, cognitive-depth classification,
misconception detection, false-belief detection, verification), while the
C_LLM baseline issues exactly 1. This is a genuine, previously-undisclosed
confound on the reported 32.4%/34.0% MAE reduction: some of that gain could
simply reflect more inference compute, not KG-grounding specifically.

This script builds "C_LLM_x7": the IDENTICAL C_LLM zero-shot prompt,
independently sampled 7 times per response (mimicking C5_fix's true call
budget), with the median of the 7 scores taken as the final grade — a
standard self-consistency ensemble applied to the holistic-grading task
itself, directly analogous to what Layer 1's self-consistency already does
for concept extraction.

Design choices, stated explicitly for reproducibility
-------------------------------------------------------
- Sample set: the exact n=90 held-out TEST split (test_mask = i%12>=3),
  the same samples underlying the paper's primary result, so C_LLM_x7 can
  be directly paired against the existing cached C5_fix and C_LLM scores
  with no distributional shift.
- Independence: each of the 7 samples per response should be a genuinely
  independent LLM generation (varied reasoning path), not 7 copies of a
  single deterministic (T=0) output. Because the local API key is invalid
  (see REPRODUCIBILITY.md), this is executed via the same manual
  paste-to-Gemini workflow used for validate_fix1_mohler_c5fix.py and
  validate_fix2c_kaggle.py earlier in this project: the prompt explicitly
  instructs the model to produce 7 independently-reasoned attempts per
  sample rather than repeating the same deterministic judgment.
  LIMITATION (disclosed in the results writeup): this is not identical to
  7 genuinely separate API calls at elevated temperature, which is what
  C5_fix's own self-consistency layer actually does. If the paper reports
  this experiment, this limitation must be stated alongside the result.
- Aggregation: median of the 7 scores (robust to a single outlier
  generation), rounded to the nearest 0.25 to match the paper's score
  resolution.

Run:
    python3 run_budget_matched_baseline.py                 # dry-run, writes prompt
    python3 run_budget_matched_baseline.py --paste r.json  # post-paste analysis
    python3 run_budget_matched_baseline.py --live          # live API, 90x7 real calls

--live mode (added once a working GEMINI_API_KEY became available)
--------------------------------------------------------------------
Issues 630 genuinely independent API calls (90 samples x 7 attempts each,
gemini-2.5-flash, temperature=0.7, one call per attempt) via the project's
existing conceptgrade.llm_client.LLMClient wrapper. This supersedes the
manual-paste LIMITATION documented above: each of the 7 attempts is now a
genuinely separate generation, matching C5_fix's own self-consistency design
exactly, not 7 attempts requested within one shared generation. Progress is
checkpointed incrementally to data/budget_matched_baseline_live_raw.json so
an interrupted run can resume without re-billing completed calls.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"
OUT = BASE / "BUDGET_MATCHED_BASELINE_PROMPT_FOR_GEMINI.txt"
LIVE_RAW = DATA / "budget_matched_baseline_live_raw.json"
LIVE_MODEL = "gemini-2.5-flash"


def build_prompt(samples: list[dict]) -> str:
    guide = """SCORING GUIDE — based on proportion of reference answer content correctly demonstrated:
- 5.0: Student correctly explains virtually all key ideas (>=90% of reference content)
- 4.5: Student correctly explains the great majority (>=80%); only very minor omissions
- 4.0: Student correctly explains most key ideas (>=70%); one clear gap
- 3.5: Student correctly explains a solid majority (>=60%) with reasonable depth
- 3.0: Student correctly explains about half the reference content (~50%)
- 2.5: Student correctly explains several key ideas (30-50%); substantial content missing
- 2.0: Student correctly explains 1-2 key ideas accurately; most reference content missing
- 1.5: Student shows partial understanding of 1 concept but cannot explain mechanisms
- 1.0: Student shows awareness of the topic but no accurate explanations
- 0.5: Single marginally relevant statement; no explanation
- 0.0: No relevant content
Use 0.25 increments only."""

    system = f"""{guide}

You are an expert grader. This is a SELF-CONSISTENCY ENSEMBLE task: for each
student answer below, produce SEVEN independent grading attempts, as if you
were seven different graders (or the same grader re-reasoning from scratch
seven separate times) each reaching their own judgment without seeing the
others' scores. Each of the 7 attempts must involve genuinely
re-deriving the score from the question, reference answer, and student
answer -- do not just repeat the same number seven times, and do not let
attempt N be influenced by attempts 1..N-1. Some legitimate score variation
across the 7 attempts is expected and desired (this measures grading
uncertainty), but each individual attempt should still be a careful,
independent judgment using the scoring guide above -- vary your emphasis,
noticed details, or borderline calls across attempts the way independent
human graders would, not randomly.

For each sample, grade using ONLY the question, reference answer, and
student answer (no external knowledge graph or structured evidence).

Return a JSON object:
{{
  "scores": {{
    "<id>": [s1, s2, s3, s4, s5, s6, s7],
    ...
  }}
}}

Grade all {len(samples)} samples, 7 independent attempts each. Use 0.25 increments only.
Return ONLY the JSON object, no other text."""

    parts = []
    for r in samples:
        parts.append(
            f"--- SAMPLE ID: {r['id']} ---\n"
            f"QUESTION: {r['question']}\n\n"
            f"REFERENCE ANSWER:\n{r['reference_answer']}\n\n"
            f"STUDENT ANSWER:\n{r['student_answer']}"
        )
    header = f"{system}\n\n{'='*70}\n\n"
    body = "\n\n".join(parts)
    footer = f"\n\n{'='*70}\nGrade all {len(samples)} samples, 7 attempts each. Return only the JSON object."
    return header + body + footer


def build_single_prompt(sample: dict) -> str:
    """Single-sample C_LLM prompt, requesting exactly one score. Mirrors
    generate_batch_scoring_prompts.build_cllm_prompt's wording (the prompt
    that produced the cached C_LLM scores) so the live-API attempts are
    directly comparable, just issued one sample/one attempt per call."""
    guide = """SCORING GUIDE — based on proportion of reference answer content correctly demonstrated:
- 5.0: Student correctly explains virtually all key ideas (>=90% of reference content)
- 4.5: Student correctly explains the great majority (>=80%); only very minor omissions
- 4.0: Student correctly explains most key ideas (>=70%); one clear gap
- 3.5: Student correctly explains a solid majority (>=60%) with reasonable depth
- 3.0: Student correctly explains about half the reference content (~50%)
- 2.5: Student correctly explains several key ideas (30-50%); substantial content missing
- 2.0: Student correctly explains 1-2 key ideas accurately; most reference content missing
- 1.5: Student shows partial understanding of 1 concept but cannot explain mechanisms
- 1.0: Student shows awareness of the topic but no accurate explanations
- 0.5: Single marginally relevant statement; no explanation
- 0.0: No relevant content
Use 0.25 increments only."""

    system = f"""{guide}

You are an expert grader. Grade the student answer below using ONLY the question, reference answer, and student answer. Do NOT use any external knowledge graphs or structured evidence.

Return a JSON object: {{"score": X.X}}
Use 0.25 increments only. Return ONLY the JSON object, no other text."""

    body = (
        f"QUESTION: {sample['question']}\n\n"
        f"REFERENCE ANSWER:\n{sample['reference_answer']}\n\n"
        f"STUDENT ANSWER:\n{sample['student_answer']}"
    )
    return f"{system}\n\n{'='*70}\n\n{body}"


def _build_test_split_samples(dataset, cached) -> list[dict]:
    """Build the canonical n=90 held-out test split exactly as
    verify_all_paper_claims.py (section 2b) and compute_real_fixes.py's
    REAL-1 define it: test_mask = (cache_pos % 12) >= 3 applied DIRECTLY to
    the cache/results array order (12-record blocks, ASCENDING score per
    question), keeping the 9 highest-scoring responses/question and
    dropping the 3 lowest as train.

    Earlier versions of this script applied that same test_mask to
    dataset.samples (loader order) instead, which is sorted DESCENDING per
    question -- see validate_fix1_mohler_c5fix.py's comment. That selects
    ranks 4-12 (drops the 3 *highest* scores) rather than ranks 1-9 (drops
    the 3 *lowest*): a ~33%-different sample set from the paper's actual
    n=90 headline split, not just a mislabeling. This function reproduces
    the paper's exact split and then locates each record's underlying
    loader sample (for question/reference/student text) via the
    (question_id, human_score) bijection between the two orderings.
    """
    loader_by_qid_score: dict = {}
    for i, s in enumerate(dataset.samples):
        key = (s.question_id, round(float(s.score_avg), 3))
        loader_by_qid_score.setdefault(key, []).append(i)

    out = []
    for cache_pos, r in enumerate(cached):
        if (cache_pos % 12) < 3:
            continue  # train, not in the n=90 test split
        qid_str = f"Q{cache_pos // 12 + 1}"
        key = (qid_str, round(float(r["human_score"]), 3))
        matches = loader_by_qid_score.get(key, [])
        if not matches:
            print(f"[warn] no loader match for cache_pos={cache_pos} "
                  f"qid={qid_str} human={r['human_score']}")
            continue
        loader_idx = matches.pop(0)
        s = dataset.samples[loader_idx]
        out.append({
            "id": str(r["id"]), "loader_idx": str(loader_idx), "qid": qid_str,
            "question": s.question,
            "reference_answer": s.reference_answer,
            "student_answer": s.student_answer,
            "human_score": r["human_score"],
            "cached_cllm": r["cllm_score"],
            "cached_c5": r["c5_score"],
        })
    return out


def _load_gemini_key() -> str:
    import re
    env_path = BASE.parent / "backend" / ".env"
    with env_path.open() as f:
        for line in f:
            m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
            if m:
                return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def run_live(resume: bool = True) -> int:
    """Issue 90x7=630 genuinely independent live Gemini calls and score."""
    from conceptgrade.llm_client import LLMClient, parse_llm_json

    from datasets.mohler_loader import load_mohler_sample
    dataset = load_mohler_sample()

    with (BASE / "archive" / "fabricated_fixtures" / "mohler_eval_results.json").open() as f:
        cached = json.load(f)["results"]

    samples = _build_test_split_samples(dataset, cached)
    print(f"Total n=90 test-split samples: {len(samples)}")

    raw: dict = {}
    if resume and LIVE_RAW.exists():
        raw = json.loads(LIVE_RAW.read_text())
        print(f"Resuming: {len(raw)} samples already have complete attempts.")

    key = _load_gemini_key()
    client = LLMClient(api_key=key)

    def save():
        LIVE_RAW.write_text(json.dumps(raw, indent=2))

    for n, s in enumerate(samples, 1):
        sid = s["loader_idx"]  # stable key: tied to dataset.samples position,
                                # unaffected by the cache-id matching bug
        attempts = raw.get(sid, [])
        while len(attempts) < 7:
            prompt = build_single_prompt(s)
            for attempt_try in range(3):
                try:
                    resp = client.chat.completions.create(
                        model=LIVE_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=256,
                    )
                    parsed = parse_llm_json(resp.choices[0].message.content)
                    score = float(parsed["score"])
                    attempts.append(score)
                    break
                except Exception as e:
                    print(f"  [sample {sid} attempt {len(attempts)+1}] "
                          f"retry {attempt_try+1}/3 after error: {e}")
                    time.sleep(2 * (attempt_try + 1))
            else:
                raise RuntimeError(f"Sample {sid}: failed 3 retries on one attempt")
            raw[sid] = attempts
            save()
            time.sleep(0.5)
        print(f"[{n}/{len(samples)}] sample {sid}: {attempts}")

    print(f"\nAll {len(samples)} samples complete ({len(samples)*7} total live calls).")

    rows = []
    for s in samples:
        attempts = raw[s["loader_idx"]]
        median_score = round(statistics.median(attempts) * 4) / 4
        rows.append({
            **{k: v for k, v in s.items() if k not in ("question", "reference_answer", "student_answer")},
            "cllm_x7_attempts": attempts,
            "cllm_x7_median": median_score,
        })
    compute_stats(rows)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paste", type=str, default=None,
                    help="Path to the JSON response from Gemini after pasting")
    ap.add_argument("--live", action="store_true",
                    help="Run 90x7 genuinely independent live Gemini API calls")
    ap.add_argument("--batch", type=int, default=0,
                    help="If splitting into batches (0=all 90 in one prompt, "
                         "1/2=first/second half of 45)")
    args = ap.parse_args()

    if args.live:
        return run_live()

    if args.paste:
        return analyse(args.paste, args.batch)

    from datasets.mohler_loader import load_mohler_sample
    dataset = load_mohler_sample()

    with (BASE / "archive" / "fabricated_fixtures" / "mohler_eval_results.json").open() as f:
        cached = json.load(f)["results"]

    matched = _build_test_split_samples(dataset, cached)
    samples = [{"id": m["id"], "question": m["question"],
                "reference_answer": m["reference_answer"],
                "student_answer": m["student_answer"]} for m in matched]
    sidecar_rows = [{"id": m["id"], "qid": m["qid"], "human_score": m["human_score"],
                      "cached_cllm": m["cached_cllm"], "cached_c5": m["cached_c5"]}
                     for m in matched]

    print(f"Total n=90 test-split samples found: {len(samples)}")

    if args.batch in (1, 2):
        half = len(samples) // 2
        if args.batch == 1:
            samples = samples[:half]
        else:
            samples = samples[half:]
        out_path = OUT.with_name(f"{OUT.stem}_batch{args.batch}{OUT.suffix}")
    else:
        out_path = OUT

    prompt = build_prompt(samples)
    header = (
        "# Experiment #1 (of 4 decisive experiments) — Call-budget-matched baseline\n"
        "# Purpose: test whether C5_fix's advantage over C_LLM survives once C_LLM\n"
        "# gets the same inference budget (7 LLM calls) that C5_fix actually uses.\n"
        "# Paste everything below the dashes into aistudio.google.com,\n"
        "# gemini-2.5-flash, temperature 0.7 (NOT 0.0 -- we need variation across\n"
        "# the 7 attempts), response format JSON.\n"
        "# ------------------------------------------------------------\n\n"
    )
    out_path.write_text(header + prompt + "\n")
    (BASE / "BUDGET_MATCHED_BASELINE_PROMPT_FOR_GEMINI.samples.json").write_text(
        json.dumps({"samples": sidecar_rows}, indent=2)
    )
    print(f"Wrote: {out_path}")
    print(f"Wrote: BUDGET_MATCHED_BASELINE_PROMPT_FOR_GEMINI.samples.json")
    print(f"\nPrompt covers {len(samples)} samples requesting 7 scores each "
          f"({len(samples)*7} total judgments).")
    return 0


def analyse(paste_path: str, batch: int) -> int:
    with Path(paste_path).open() as f:
        paste = json.load(f)
    new_scores = paste.get("scores", paste)

    sidecar_path = BASE / "BUDGET_MATCHED_BASELINE_PROMPT_FOR_GEMINI.samples.json"
    sidecar = json.loads(sidecar_path.read_text())["samples"]

    rows = []
    for row in sidecar:
        sid = row["id"]
        raw = new_scores.get(sid)
        if raw is None:
            continue
        try:
            attempts = [float(x) for x in raw]
        except (TypeError, ValueError):
            continue
        median_score = statistics.median(attempts)
        median_score = round(median_score * 4) / 4  # nearest 0.25
        row = dict(row)
        row["cllm_x7_attempts"] = attempts
        row["cllm_x7_median"] = median_score
        rows.append(row)

    print(f"Parsed {len(rows)} samples with 7-attempt ensembles\n")
    return compute_stats(rows)


def compute_stats(rows: list[dict]) -> int:
    import numpy as np
    from scipy.stats import wilcoxon

    human = np.array([r["human_score"] for r in rows])
    cllm1 = np.array([r["cached_cllm"] for r in rows])
    c5 = np.array([r["cached_c5"] for r in rows])
    cllm_x7 = np.array([r["cllm_x7_median"] for r in rows])

    def mae(pred):
        return float(np.mean(np.abs(human - pred)))

    def report(name, pred):
        m = mae(pred)
        r = float(np.corrcoef(human, pred)[0, 1])
        print(f"  {name:20s}  MAE={m:.4f}  r={r:.4f}")
        return m

    print("=== Point estimates (n={}) ===".format(len(rows)))
    mae_cllm1 = report("C_LLM (1 call)", cllm1)
    mae_cllm7 = report("C_LLM_x7 (7 calls)", cllm_x7)
    mae_c5 = report("C5_fix (7 calls)", c5)

    print(f"\n=== Key comparisons ===")
    err_cllm1 = np.abs(human - cllm1)
    err_cllm7 = np.abs(human - cllm_x7)
    err_c5 = np.abs(human - c5)

    # Does budget-matching help C_LLM at all?
    _, p_budget_helps = wilcoxon(err_cllm7, err_cllm1, alternative="less", zero_method="wilcox")
    red_budget = (mae_cllm1 - mae_cllm7) / mae_cllm1 * 100
    print(f"C_LLM_x7 vs C_LLM (1 call): {red_budget:+.1f}% MAE change, "
          f"one-tailed p={p_budget_helps:.4f} (does budget alone help?)")

    # Does C5_fix still beat the budget-matched baseline?
    _, p_c5_vs_x7_two = wilcoxon(err_c5, err_cllm7, alternative="two-sided", zero_method="wilcox")
    _, p_c5_vs_x7_one = wilcoxon(err_c5, err_cllm7, alternative="less", zero_method="wilcox")
    red_c5_vs_x7 = (mae_cllm7 - mae_c5) / mae_cllm7 * 100 if mae_cllm7 > 0 else 0.0
    print(f"C5_fix vs C_LLM_x7 (budget-matched): {red_c5_vs_x7:+.1f}% MAE change, "
          f"two-tailed p={p_c5_vs_x7_two:.4f}, one-tailed p={p_c5_vs_x7_one:.4f}")
    print(f"  (THIS is the decisive test: if p > 0.05 here, C5_fix's advantage")
    print(f"   does not survive budget-matching -- the original gain may be")
    print(f"   substantially attributable to inference compute, not KG-grounding.)")

    out = {
        "experiment": "budget_matched_baseline",
        "n": len(rows),
        "mae_cllm_1call": mae_cllm1,
        "mae_cllm_x7": mae_cllm7,
        "mae_c5fix": mae_c5,
        "budget_alone_reduction_pct": red_budget,
        "budget_alone_p_one_tailed": float(p_budget_helps),
        "c5fix_vs_budget_matched_reduction_pct": red_c5_vs_x7,
        "c5fix_vs_budget_matched_p_two_tailed": float(p_c5_vs_x7_two),
        "c5fix_vs_budget_matched_p_one_tailed": float(p_c5_vs_x7_one),
        "per_sample": rows,
    }
    out_path = DATA / "budget_matched_baseline_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
