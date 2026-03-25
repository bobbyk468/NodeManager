#!/usr/bin/env python3
"""
ConceptGrade Score Comparison — Pure LLM vs KG-only vs ConceptGrade vs Ground Truth

Shows side-by-side how a naive LLM grader, the KG algorithm, and the full
ConceptGrade pipeline compare against human ground-truth (Mohler 2011).

Usage:
  python run_score_comparison.py [--model MODEL] [--n-samples N]
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── helpers ──────────────────────────────────────────────────────────────────

def get_api_key(model: str) -> str:
    from conceptgrade.llm_client import detect_provider
    key_map = {"anthropic": "ANTHROPIC_API_KEY",
               "google":    "GEMINI_API_KEY",
               "openai":    "OPENAI_API_KEY"}
    env = key_map.get(detect_provider(model), "ANTHROPIC_API_KEY")
    key = os.environ.get(env, "")
    if not key:
        print(f"ERROR: set {env}", file=sys.stderr)
        sys.exit(1)
    return key

def pearson_r(xs, ys):
    n = len(xs)
    mx, my = sum(xs)/n, sum(ys)/n
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    den = (sum((x-mx)**2 for x in xs) * sum((y-my)**2 for y in ys)) ** 0.5
    return num/den if den else 0.0

def mae(xs, ys):
    return sum(abs(x-y) for x,y in zip(xs,ys)) / len(xs)

def rmse(xs, ys):
    return (sum((x-y)**2 for x,y in zip(xs,ys)) / len(xs)) ** 0.5

def bias(xs, ys):          # mean(prediction - ground_truth)
    return sum(x-y for x,y in zip(xs,ys)) / len(xs)


# ── pure-LLM baseline grader ─────────────────────────────────────────────────

PURE_LLM_SYSTEM = (
    "You are an expert academic grader. "
    "Score the student answer on a scale of 0 to 5 (decimals allowed). "
    "Reply with ONLY a JSON object: {\"score\": <number>}"
)

def pure_llm_grade(client, model: str, question: str, reference: str, answer: str) -> float:
    """Ask the LLM to grade with no KG structure — pure baseline."""
    user_prompt = (
        f"Question: {question}\n\n"
        f"Reference answer: {reference}\n\n"
        f"Student answer: {answer}\n\n"
        "Score the student answer 0–5."
    )
    raw = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PURE_LLM_SYSTEM},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=50,
        temperature=0.0,
    )
    text = raw.choices[0].message.content or ""
    # extract first number found
    m = re.search(r'"score"\s*:\s*([0-9.]+)', text)
    if m:
        return min(5.0, max(0.0, float(m.group(1))))
    m = re.search(r'[0-9]+(?:\.[0-9]+)?', text)
    if m:
        return min(5.0, max(0.0, float(m.group())))
    return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model",     default="gemini-2.5-flash-lite")
    ap.add_argument("--n-samples", type=int, default=15)
    args = ap.parse_args()

    API_KEY  = get_api_key(args.model)
    MODEL    = args.model
    N        = args.n_samples

    from datasets.mohler_loader import load_mohler_sample
    from conceptgrade.pipeline  import ConceptGradePipeline
    from conceptgrade.llm_client import LLMClient

    # ── load dataset ─────────────────────────────────────────────────────────
    dataset = load_mohler_sample()
    samples = sorted(dataset.samples, key=lambda s: s.score_avg)
    if N and N < len(samples):
        step    = len(samples) / N
        samples = [samples[int(i * step)] for i in range(N)]

    # ── pipelines ─────────────────────────────────────────────────────────────
    pipeline = ConceptGradePipeline(
        api_key=API_KEY,
        model=MODEL,
        rate_limit_delay=0.1,
        use_self_consistency=False,
        use_confidence_weighting=True,
        use_llm_verifier=True,
        use_sure_verifier=True,
        verifier_weight=1.0,
    )

    # Standalone LLMClient for the pure-LLM baseline
    llm_client = LLMClient(api_key=API_KEY)

    print("=" * 95)
    print(f"  ConceptGrade Score Comparison — Pure LLM vs KG vs ConceptGrade vs Ground Truth")
    print(f"  Model: {MODEL}  |  n={len(samples)} stratified samples from Mohler 2011")
    print("=" * 95)
    print(f"  {'#':<3} {'Q':<4} {'GT':>5} {'PureLLM':>8} {'KG/5':>6} {'CG/5':>6}  "
          f"{'Δ Pure':>7} {'Δ KG':>6} {'Δ CG':>6}  {'Adj':<8}")
    print(f"  {'-'*85}")

    gt_scores, pure_scores, kg_scores, cg_scores = [], [], [], []
    confirms = increases = decreases = 0

    for i, s in enumerate(samples, 1):
        t0 = time.time()

        # 1. Pure LLM baseline
        try:
            pure_5 = pure_llm_grade(llm_client, MODEL, s.question, s.reference_answer, s.student_answer)
        except Exception as e:
            print(f"  {i:<3} Pure-LLM ERROR: {e}")
            pure_5 = None

        # 2. ConceptGrade (KG + verifier)
        try:
            result = pipeline.assess_student(
                student_id=f"s{i}",
                question=s.question,
                answer=s.student_answer,
                reference_answer=s.reference_answer,
            )
        except Exception as e:
            print(f"  {i:<3} ConceptGrade ERROR: {e}")
            continue

        if pure_5 is None:
            continue

        gt    = round(s.score_avg, 2)
        ver   = result.verifier or {}
        kg_01 = ver.get("kg_score", result.overall_score)
        fn_01 = ver.get("final_score", result.overall_score)
        # SURE uses directions list; single verifier uses adjustment_direction
        dirs  = ver.get("directions", [])
        adj   = ver.get("adjustment_direction", dirs[1] if len(dirs) > 1 else "confirm")

        kg_5  = round(kg_01 * 5, 2)
        cg_5  = round(fn_01 * 5, 2)

        gt_scores.append(gt)
        pure_scores.append(pure_5)
        kg_scores.append(kg_5)
        cg_scores.append(cg_5)

        if adj == "confirm":    confirms   += 1
        elif adj == "increase": increases  += 1
        else:                   decreases  += 1

        arrow = {"confirm": "=", "increase": "↑", "decrease": "↓"}.get(adj, "?")
        dt = time.time() - t0
        print(f"  {i:<3} {s.question_id:<4} {gt:>5.1f} {pure_5:>8.2f} {kg_5:>6.2f} {cg_5:>6.2f}  "
              f"{pure_5-gt:>+7.2f} {kg_5-gt:>+6.2f} {cg_5-gt:>+6.2f}  {adj:<8}{arrow}  ({dt:.1f}s)")

    n = len(gt_scores)
    if n == 0:
        print("No results.")
        return

    print()
    print("=" * 95)
    print("  STATISTICS")
    print("=" * 95)
    print(f"  {'Metric':<30} {'Pure LLM':>10}  {'KG-only':>10}  {'ConceptGrade':>13}")
    print(f"  {'-'*70}")
    print(f"  {'Pearson r':<30} {pearson_r(gt_scores,pure_scores):>10.4f}  "
          f"{pearson_r(gt_scores,kg_scores):>10.4f}  {pearson_r(gt_scores,cg_scores):>13.4f}")
    print(f"  {'MAE (0–5 scale)':<30} {mae(gt_scores,pure_scores):>10.3f}  "
          f"{mae(gt_scores,kg_scores):>10.3f}  {mae(gt_scores,cg_scores):>13.3f}")
    print(f"  {'RMSE':<30} {rmse(gt_scores,pure_scores):>10.3f}  "
          f"{rmse(gt_scores,kg_scores):>10.3f}  {rmse(gt_scores,cg_scores):>13.3f}")
    print(f"  {'Bias (mean Δ)':<30} {bias(pure_scores,gt_scores):>+10.3f}  "
          f"{bias(kg_scores,gt_scores):>+10.3f}  {bias(cg_scores,gt_scores):>+13.3f}")
    print()
    print(f"  Verifier decisions ({n} samples):")
    print(f"    Confirm   : {confirms}  ({100*confirms//n}%)")
    print(f"    Increase  : {increases}  ({100*increases//n}%)")
    print(f"    Decrease  : {decreases}  ({100*decreases//n}%)")
    print("=" * 95)

if __name__ == "__main__":
    main()
