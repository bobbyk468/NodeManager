#!/usr/bin/env python3
"""
Adversarial Evaluation — ConceptGrade vs Pure LLM on 100-scenario Vulnerability Matrix.

Runs both graders on data/adversarial_benchmark.json and produces:
  - Per-category MAE, bias, and Robustness Gain
  - Overall metrics table
  - Failure mode analysis (where each system struggles)

Usage:
  export GEMINI_API_KEY="your-key"
  python run_adversarial_evaluation.py [--model gemini-flash-latest-lite] [--n N]
"""

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── metrics helpers ───────────────────────────────────────────────────────────

def mae(xs, ys):
    return sum(abs(x - y) for x, y in zip(xs, ys)) / len(xs) if xs else 0.0

def rmse(xs, ys):
    return (sum((x - y) ** 2 for x, y in zip(xs, ys)) / len(xs)) ** 0.5 if xs else 0.0

def bias(xs, ys):
    return sum(x - y for x, y in zip(xs, ys)) / len(xs) if xs else 0.0

def pearson_r(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den if den else 0.0


# ── pure-LLM baseline ─────────────────────────────────────────────────────────

PURE_LLM_SYSTEM = (
    "You are an expert academic grader. "
    "Score the student answer on a scale of 0 to 5 (decimals allowed). "
    "Reply with ONLY a JSON object: {\"score\": <number>}"
)

PURE_LLM_SYSTEM_LAG = (
    "You are an expert academic grader evaluating a student's essay. "
    "Score the essay on a scale of 0 to 5 based on accuracy, depth, and coverage. "
    "Reply with ONLY a JSON object: {\"score\": <number>}"
)


def pure_llm_grade(client, model: str, question: str, reference: str,
                   answer: str, answer_type: str = "sag") -> float:
    system = PURE_LLM_SYSTEM_LAG if answer_type == "lag" else PURE_LLM_SYSTEM
    user_prompt = (
        f"Question: {question}\n\n"
        f"Reference answer: {reference}\n\n"
        f"Student answer: {answer}\n\n"
        "Score the student answer 0–5. Return ONLY: {\"score\": <number>}"
    )
    raw = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=200,   # Gemini can be verbose; give it room
        temperature=0.0,
    )
    text = raw.choices[0].message.content or ""
    # Try JSON parse first
    try:
        from conceptgrade.llm_client import parse_llm_json
        parsed = parse_llm_json(text)
        return min(5.0, max(0.0, float(parsed["score"])))
    except Exception:
        pass
    # Fallback: regex
    m = re.search(r'"score"\s*:\s*([0-9.]+)', text)
    if m:
        return min(5.0, max(0.0, float(m.group(1))))
    m = re.search(r'\b([0-9](?:\.[0-9])?)\b', text)
    if m:
        return min(5.0, max(0.0, float(m.group(1))))
    raise ValueError(f"Could not parse score from: {text[:100]}")


# ── category metadata ─────────────────────────────────────────────────────────

CATEGORY_META = {
    "mastery":            {"label": "Standard Mastery",   "advantage": "none (baseline)"},
    "prose_trap":         {"label": "Prose Trap",          "advantage": "KG finds zero concept matches"},
    "adjective_injection":{"label": "Adjective Injection", "advantage": "Misconception detection catches wrong claims"},
    "hallucination":      {"label": "Silent Hallucination","advantage": "KG finds zero valid concept matches"},
    "breadth_bluffer":    {"label": "Breadth Bluffer",     "advantage": "Bloom's level 1 caps score"},
    "code_logic_drift":   {"label": "Code-Logic Drift",    "advantage": "Integration score detects logic errors"},
    "structural_split":   {"label": "Structural Split",    "advantage": "Cross-paragraph coherence flags contradiction"},
}


# ── result persistence ────────────────────────────────────────────────────────

def load_results(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_results(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── main evaluation ───────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-flash-latest")
    ap.add_argument("--benchmark", default="data/adversarial_benchmark.json")
    ap.add_argument("--results",   default="data/adversarial_evaluation_results.json")
    ap.add_argument("--n", type=int, default=10, help="Number of cases in this batch (default 10)")
    ap.add_argument("--offset", type=int, default=0, help="Start from this case index (0-based)")
    ap.add_argument("--category", default=None, help="Run only a specific category code")
    ap.add_argument("--skip-cache", action="store_true", help="Ignore cached results and re-run")
    args = ap.parse_args()

    # ── load benchmark ────────────────────────────────────────────────────────
    if not os.path.exists(args.benchmark):
        print(f"ERROR: benchmark not found at {args.benchmark}")
        print("Run: python generate_adversarial_suite.py first")
        sys.exit(1)

    with open(args.benchmark) as f:
        all_cases = json.load(f)

    if args.category:
        all_cases = [c for c in all_cases if c.get("category_code") == args.category]

    # Slice the batch window
    cases = all_cases[args.offset : args.offset + args.n]
    total_so_far = args.offset + len(cases)

    if not cases:
        print(f"No cases in range [{args.offset}, {args.offset + args.n}). Total available: {len(all_cases)}")
        sys.exit(0)

    print(f"Batch [{args.offset+1}–{total_so_far}] of {len(all_cases)} total cases")

    # ── API key ───────────────────────────────────────────────────────────────
    from conceptgrade.llm_client import LLMClient, detect_provider
    key_map = {"anthropic": "ANTHROPIC_API_KEY",
               "google":    "GEMINI_API_KEY",
               "openai":    "OPENAI_API_KEY"}
    provider = detect_provider(args.model)
    env_var = key_map.get(provider, "ANTHROPIC_API_KEY")
    api_key = os.environ.get(env_var, "")
    if not api_key:
        print(f"ERROR: set {env_var}", file=sys.stderr)
        sys.exit(1)

    # ── pipelines ─────────────────────────────────────────────────────────────
    from conceptgrade.pipeline import ConceptGradePipeline
    from conceptgrade.lag_pipeline import LongAnswerPipeline

    sag_pipeline = ConceptGradePipeline(
        api_key=api_key,
        model=args.model,
        rate_limit_delay=0.1,
        use_self_consistency=False,
        use_confidence_weighting=True,
        use_llm_verifier=True,
        use_sure_verifier=True,
        verifier_weight=1.0,
    )
    lag_pipeline = LongAnswerPipeline(
        api_key=api_key,
        model=args.model,
        use_sure=True,
        use_cross_para=True,
    )
    llm_client = LLMClient(api_key=api_key)

    # ── load cached results ───────────────────────────────────────────────────
    # Always load existing results so --skip-cache never destroys prior work.
    # --skip-cache only means: re-run this batch even if already cached.
    persisted = load_results(args.results)
    cached = dict(persisted)  # working copy (will be saved back)

    print()
    print("=" * 100)
    print(f"  Adversarial Evaluation — Pure LLM vs ConceptGrade")
    print(f"  Model: {args.model}  |  Batch [{args.offset+1}–{total_so_far}] of {len(all_cases)}")
    print("=" * 100)
    header = f"  {'#':<4} {'Category':<22} {'GT':>5} {'PureLLM':>8} {'CG/5':>6}  {'ΔLLM':>6} {'ΔCG':>5}  {'Adj':<10} {'Notes'}"
    print(header)
    print(f"  {'-'*95}")

    # Per-category accumulators
    cat_data: dict[str, dict] = {}

    for i, case in enumerate(cases, 1):
        cid = str(case.get("id", i))
        if cid in cached and not args.skip_cache:
            r = cached[cid]
            pure_5 = r.get("pure_score")
            cg_5   = r.get("cg_score")
            gt     = r.get("gt_score")
            adj    = r.get("adj", "confirm")
        else:
            gt     = float(case.get("ground_truth_score", 2.5))
            atype  = case.get("answer_type", "sag")
            q      = case["question"]
            ref    = case["reference_answer"]
            ans    = case["student_answer"]

            # Run Pure LLM grader and ConceptGrade pipeline in parallel
            from concurrent.futures import ThreadPoolExecutor
            t0 = time.time()

            def _run_pure():
                return pure_llm_grade(llm_client, args.model, q, ref, ans, atype)

            def _run_cg():
                if atype == "lag":
                    res = lag_pipeline.assess(question=q, student_answer=ans, reference_answer=ref)
                    # LAG returns a LongAnswerResult dataclass; score is 0-5 in aggregated.final_score
                    score_5 = res.aggregated.final_score
                    score_01 = score_5 / 5.0
                    v = res.verifier or {}
                    dirs = v.get("directions", [])
                    d = v.get("adjustment_direction", dirs[1] if len(dirs) > 1 else "confirm")
                else:
                    res = sag_pipeline.assess_student(
                        student_id=f"adv_{cid}", question=q, answer=ans, reference_answer=ref)
                    v   = res.verifier or {}
                    score_01 = v.get("final_score", res.overall_score)
                    dirs = v.get("directions", [])
                    d = v.get("adjustment_direction", dirs[1] if len(dirs) > 1 else "confirm")
                return round(score_01 * 5, 2), d

            pure_5 = cg_5 = adj = None
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_pure = pool.submit(_run_pure)
                f_cg   = pool.submit(_run_cg)
                try:
                    pure_5 = f_pure.result()
                except Exception as e:
                    print(f"  {i:<4} Pure-LLM ERROR: {e}")
                try:
                    cg_5, adj = f_cg.result()
                except Exception as e:
                    print(f"  {i:<4} ConceptGrade ERROR: {e}")
                    adj = "error"

            if pure_5 is None or cg_5 is None:
                continue

            # cache result
            cached[cid] = {
                "gt_score": gt, "pure_score": pure_5, "cg_score": cg_5,
                "adj": adj, "category": case.get("category_code"),
                "topic": case.get("topic"),
            }
            save_results(args.results, cached)

        if pure_5 is None or cg_5 is None:
            continue

        # Accumulate per-category
        cat_code = case.get("category_code", "unknown")
        if cat_code not in cat_data:
            cat_data[cat_code] = {"gt": [], "pure": [], "cg": []}
        cat_data[cat_code]["gt"].append(gt)
        cat_data[cat_code]["pure"].append(pure_5)
        cat_data[cat_code]["cg"].append(cg_5)

        arrow = {"confirm": "=", "increase": "↑", "decrease": "↓"}.get(adj, "?")
        cat_label = CATEGORY_META.get(cat_code, {}).get("label", cat_code)[:20]
        notes = case.get("generation_notes", "")[:35]

        print(f"  {i:<4} {cat_label:<22} {gt:>5.1f} {pure_5:>8.2f} {cg_5:>6.2f}  "
              f"{pure_5-gt:>+6.2f} {cg_5-gt:>+5.2f}  {adj:<10}{arrow}  {notes}")

    # ── Rebuild full stats from ALL cached results (not just this batch) ─────
    full_cat_data: dict[str, dict] = {}
    # Load updated benchmark to get GT
    benchmark_by_id = {str(c.get("id", i+1)): c for i, c in enumerate(all_cases)}
    for cid, r in cached.items():
        bcase = benchmark_by_id.get(cid, {})
        gt_full = float(bcase.get("ground_truth_score", r.get("gt_score", 0)))
        p = r.get("pure_score"); cg = r.get("cg_score")
        if p is None or cg is None:
            continue
        cc = r.get("category", bcase.get("category_code", "unknown"))
        if cc not in full_cat_data:
            full_cat_data[cc] = {"gt": [], "pure": [], "cg": []}
        full_cat_data[cc]["gt"].append(gt_full)
        full_cat_data[cc]["pure"].append(p)
        full_cat_data[cc]["cg"].append(cg)

    all_gt   = [v for d in full_cat_data.values() for v in d["gt"]]
    all_pure = [v for d in full_cat_data.values() for v in d["pure"]]
    all_cg   = [v for d in full_cat_data.values() for v in d["cg"]]

    n = len(all_gt)
    if n == 0:
        print("No results.")
        return

    print(f"\n  (Stats below are cumulative across all {n} evaluated cases so far)")

    print()
    print("=" * 100)
    print("  OVERALL RESULTS")
    print("=" * 100)
    print(f"  {'Metric':<30} {'Pure LLM':>12}  {'ConceptGrade':>14}  {'CG Better?':>12}")
    print(f"  {'-'*70}")

    o_mae_llm = mae(all_pure, all_gt)
    o_mae_cg  = mae(all_cg,   all_gt)
    o_rmse_llm = rmse(all_pure, all_gt)
    o_rmse_cg  = rmse(all_cg,   all_gt)
    o_r_llm   = pearson_r(all_gt, all_pure)
    o_r_cg    = pearson_r(all_gt, all_cg)
    o_bias_llm = bias(all_pure, all_gt)
    o_bias_cg  = bias(all_cg,   all_gt)

    robustness_gain = o_mae_llm - o_mae_cg
    pct_gain = 100 * robustness_gain / o_mae_llm if o_mae_llm else 0

    print(f"  {'MAE (0–5 scale)':<30} {o_mae_llm:>12.3f}  {o_mae_cg:>14.3f}  "
          f"{'✓ ' + f'{pct_gain:.1f}% better':>12}" if o_mae_cg < o_mae_llm else
          f"  {'MAE (0–5 scale)':<30} {o_mae_llm:>12.3f}  {o_mae_cg:>14.3f}  {'✗ worse':>12}")
    print(f"  {'RMSE':<30} {o_rmse_llm:>12.3f}  {o_rmse_cg:>14.3f}  "
          f"{'✓' if o_rmse_cg < o_rmse_llm else '✗':>12}")
    print(f"  {'Pearson r':<30} {o_r_llm:>12.4f}  {o_r_cg:>14.4f}  "
          f"{'✓' if o_r_cg > o_r_llm else '✗':>12}")
    print(f"  {'Bias (mean Δ)':<30} {o_bias_llm:>+12.3f}  {o_bias_cg:>+14.3f}  "
          f"{'✓ less biased' if abs(o_bias_cg) < abs(o_bias_llm) else '✗':>12}")
    print()
    print(f"  Robustness Gain = MAE_LLM − MAE_CG = {o_mae_llm:.3f} − {o_mae_cg:.3f} = {robustness_gain:+.3f}")
    print(f"  {'ConceptGrade BEATS Pure LLM ✓' if robustness_gain > 0 else 'ConceptGrade does NOT beat Pure LLM ✗'}")

    # ── Per-category breakdown ─────────────────────────────────────────────────
    print()
    print("=" * 100)
    print("  VULNERABILITY MATRIX — Per-Category Results")
    print("=" * 100)
    print(f"  {'Category':<25} {'n':>3}  {'MAE_LLM':>8}  {'MAE_CG':>8}  {'Gain':>7}  "
          f"{'Bias_LLM':>9}  {'Bias_CG':>8}  {'CG Advantage'}")
    print(f"  {'-'*95}")

    category_order = ["mastery", "prose_trap", "adjective_injection", "hallucination",
                      "breadth_bluffer", "code_logic_drift", "structural_split"]

    for cat_code in category_order:
        if cat_code not in full_cat_data:
            continue
        d = full_cat_data[cat_code]
        if not d["gt"]:
            continue

        c_mae_llm  = mae(d["pure"], d["gt"])
        c_mae_cg   = mae(d["cg"],   d["gt"])
        c_gain     = c_mae_llm - c_mae_cg
        c_bias_llm = bias(d["pure"], d["gt"])
        c_bias_cg  = bias(d["cg"],   d["gt"])

        label     = CATEGORY_META.get(cat_code, {}).get("label", cat_code)
        advantage = CATEGORY_META.get(cat_code, {}).get("advantage", "")
        status    = "✓" if c_gain > 0 else "✗"

        print(f"  {label:<25} {len(d['gt']):>3}  {c_mae_llm:>8.3f}  {c_mae_cg:>8.3f}  "
              f"{c_gain:>+7.3f}  {c_bias_llm:>+9.3f}  {c_bias_cg:>+8.3f}  {status} {advantage}")

    # ── Mathematical proof summary ─────────────────────────────────────────────
    print()
    print("=" * 100)
    print("  MATHEMATICAL PROOF OF ROBUSTNESS")
    print("=" * 100)
    n_wins = sum(
        1 for code in full_cat_data
        if mae(full_cat_data[code]["cg"], full_cat_data[code]["gt"]) <
           mae(full_cat_data[code]["pure"], full_cat_data[code]["gt"])
    )
    n_cats = len(full_cat_data)
    print(f"  ConceptGrade wins in {n_wins}/{n_cats} categories")
    print(f"  Overall Robustness Gain: {robustness_gain:+.3f} MAE points ({pct_gain:.1f}%)")
    print()

    if robustness_gain > 0:
        print("  ✓ VALIDATED: ConceptGrade outperforms pure LLM on adversarial test suite.")
        print("  ✓ The KG structure provides measurable robustness against adversarial patterns.")
    else:
        print("  ✗ NOT VALIDATED: Pure LLM performs better or equally on this suite.")
        print("  ✗ Review per-category breakdown to identify where CG underperforms.")

    # Save final summary
    summary = {
        "n_cases": n,
        "model": args.model,
        "overall": {
            "mae_llm": round(o_mae_llm, 4), "mae_cg": round(o_mae_cg, 4),
            "rmse_llm": round(o_rmse_llm, 4), "rmse_cg": round(o_rmse_cg, 4),
            "pearson_llm": round(o_r_llm, 4), "pearson_cg": round(o_r_cg, 4),
            "bias_llm": round(o_bias_llm, 4), "bias_cg": round(o_bias_cg, 4),
            "robustness_gain": round(robustness_gain, 4),
            "pct_gain": round(pct_gain, 1),
        },
        "per_category": {
            code: {
                "n": len(d["gt"]),
                "mae_llm": round(mae(d["pure"], d["gt"]), 4),
                "mae_cg":  round(mae(d["cg"],   d["gt"]), 4),
                "gain":    round(mae(d["pure"], d["gt"]) - mae(d["cg"], d["gt"]), 4),
                "bias_llm": round(bias(d["pure"], d["gt"]), 4),
                "bias_cg":  round(bias(d["cg"],   d["gt"]), 4),
            }
            for code, d in full_cat_data.items() if d["gt"]
        },
    }

    summary_path = args.results.replace(".json", "_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Full results: {args.results}")
    print(f"  Summary:      {summary_path}")
    print("=" * 100)


if __name__ == "__main__":
    main()
