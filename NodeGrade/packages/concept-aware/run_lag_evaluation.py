#!/usr/bin/env python3
"""
ConceptGrade — Long Answer Grading (LAG) Evaluation

Evaluates the LongAnswerPipeline against a hand-crafted benchmark of
multi-paragraph essay-style CS answers.

Usage:
  python run_lag_evaluation.py [--model MODEL] [--n-samples N] [--sure]

Options:
  --model MODEL     LLM model name (default: claude-haiku-4-5-20251001)
                    Provider auto-detected: claude-* → Anthropic,
                    gemini-* → Google, gpt-* → OpenAI
  --n-samples N     Evaluate only N samples, stratified across score range.
                    Default 0 = all 20 samples.
  --sure            Enable SURE (Selective Uncertainty-driven Review) flag.
                    Marks samples as requiring human review when the LAG
                    score confidence is low.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

# Add package root to path so relative imports work when running directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── API key detection (mirrored from run_sag.py) ─────────────────────────────

def get_api_key(model: str) -> str:
    """Return the correct API key from the environment for the given model."""
    from conceptgrade.llm_client import detect_provider
    provider = detect_provider(model)
    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "google":    "GEMINI_API_KEY",
        "openai":    "OPENAI_API_KEY",
    }
    env_var = key_map.get(provider, "ANTHROPIC_API_KEY")
    key = os.environ.get(env_var, "")
    if not key:
        print(f"ERROR: Set {env_var} for model '{model}'", file=sys.stderr)
        sys.exit(1)
    return key


# ── Pure LLM baseline grader ─────────────────────────────────────────────────

PURE_LLM_SYSTEM_LAG = (
    "You are an expert academic grader. "
    "Score the student essay answer on a scale of 0 to 5 (decimals allowed). "
    "Reply with ONLY a JSON object: {\"score\": <number>}"
)

def pure_llm_grade_lag(client, model: str, question: str, reference: str, answer: str) -> float:
    """Grade a long-form essay with no KG structure — pure LLM baseline."""
    user_prompt = (
        f"Question: {question}\n\n"
        f"Reference answer: {reference}\n\n"
        f"Student essay: {answer}\n\n"
        "Score the student essay 0–5."
    )
    raw = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PURE_LLM_SYSTEM_LAG},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=50,
        temperature=0.0,
    )
    text = raw.choices[0].message.content or ""
    m = re.search(r'"score"\s*:\s*([0-9.]+)', text)
    if m:
        return min(5.0, max(0.0, float(m.group(1))))
    m = re.search(r'[0-9]+(?:\.[0-9]+)?', text)
    if m:
        return min(5.0, max(0.0, float(m.group())))
    return 0.0


# ── QWK helper (uses sklearn when available, falls back to pure Python) ───────

def _qwk_manual(y_true_int: list, y_pred_int: list, min_val: int = 0, max_val: int = 5) -> float:
    """
    Quadratic Weighted Kappa computed from scratch.

    Identical result to sklearn.metrics.cohen_kappa_score(..., weights='quadratic')
    but has no external dependency.
    """
    n_classes = max_val - min_val + 1
    n = len(y_true_int)

    # Build observed matrix O and expected matrix E
    O = [[0] * n_classes for _ in range(n_classes)]
    for yt, yp in zip(y_true_int, y_pred_int):
        i = max(0, min(n_classes - 1, yt - min_val))
        j = max(0, min(n_classes - 1, yp - min_val))
        O[i][j] += 1

    # Marginals
    row_sum = [sum(O[i]) for i in range(n_classes)]
    col_sum = [sum(O[i][j] for i in range(n_classes)) for j in range(n_classes)]

    # Weight matrix W_ij = (i - j)^2 / (n_classes - 1)^2
    denom = (n_classes - 1) ** 2 if n_classes > 1 else 1

    # Weighted observed and expected
    num_w = 0.0
    den_w = 0.0
    for i in range(n_classes):
        for j in range(n_classes):
            w = (i - j) ** 2 / denom
            num_w += w * O[i][j] / n
            den_w += w * row_sum[i] * col_sum[j] / (n * n)

    if den_w == 0.0:
        return 1.0 if num_w == 0.0 else 0.0
    return float(1.0 - num_w / den_w)


def compute_qwk(y_true: list, y_pred: list) -> float:
    """
    Compute QWK, rounding continuous scores to nearest 0.5 then to integer.

    Uses sklearn when available for consistency with the SAG evaluator.
    """
    # Round to nearest 0.5 on the 0-5 scale, then to integer for kappa
    y_true_int = [max(0, min(5, int(round(v * 2) / 2 * 2) // 2 * 1 + round(v) % 1 >= 0.5)) for v in y_true]
    # Simpler: just round to nearest integer clamped to [0, 5]
    y_true_int = [max(0, min(5, round(v))) for v in y_true]
    y_pred_int = [max(0, min(5, round(v))) for v in y_pred]

    try:
        from sklearn.metrics import cohen_kappa_score
        return float(cohen_kappa_score(y_true_int, y_pred_int, weights="quadratic"))
    except ImportError:
        return _qwk_manual(y_true_int, y_pred_int, min_val=0, max_val=5)
    except Exception:
        return _qwk_manual(y_true_int, y_pred_int, min_val=0, max_val=5)


# ── Dataset loading ────────────────────────────────────────────────────────────

def load_benchmark(path: str) -> list[dict]:
    """Load the LAG benchmark JSON file and return a list of sample dicts."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    required = {"question", "reference_answer", "student_answer", "human_score"}
    for i, sample in enumerate(data):
        missing = required - set(sample.keys())
        if missing:
            raise ValueError(f"Sample {i} missing fields: {missing}")
    return data


def stratified_subsample(samples: list[dict], n: int, seed: int = 42) -> list[dict]:
    """
    Pick n samples from the benchmark, evenly spaced across the human_score range.
    This preserves coverage of the full 0-5 score distribution.
    """
    import random
    random.seed(seed)
    sorted_samples = sorted(samples, key=lambda s: s["human_score"])
    if n >= len(sorted_samples):
        return sorted_samples
    step = len(sorted_samples) / n
    return [sorted_samples[int(i * step)] for i in range(n)]


# ── SURE (Selective Uncertainty-driven Review) ────────────────────────────────

def requires_human_review(lag_score: float, sure_threshold: float = 1.5) -> bool:
    """
    Simple SURE heuristic: flag for human review when the LAG score is in the
    ambiguous middle region (1.5 – 3.5) where automated grading is least certain.
    """
    return 1.5 <= lag_score <= 3.5


# ── Core metrics ──────────────────────────────────────────────────────────────

def compute_metrics(human_scores: list[float], lag_scores: list[float]) -> dict:
    """
    Compute Pearson r, RMSE, MAE, QWK, and Bias for a set of predictions.
    Returns a dict of metric name → value.
    """
    from evaluation.metrics import evaluate_grading
    result = evaluate_grading(human_scores, lag_scores, task_name="LAG Pipeline")
    bias = sum(p - h for p, h in zip(lag_scores, human_scores)) / len(human_scores)
    return {
        "pearson_r": result.pearson_r,
        "pearson_p": result.pearson_p,
        "rmse":      result.rmse,
        "mae":       result.mae,
        "qwk":       compute_qwk(human_scores, lag_scores),
        "bias":      bias,
    }


# ── Progress display ──────────────────────────────────────────────────────────

_WAVE_ICONS = {
    "cache":    "CACHE",
    "segment":  "SEG  ",
    "wave1":    "W1   ",
    "wave2":    "W2   ",
    "score":    "SCORE",
    "verify":   "W4   ",
    "feedback": "W5   ",
}

def make_progress_callback(sample_idx: int, n_total: int, verbose: bool = True):
    """Return a progress callback suitable for LongAnswerPipeline.on_progress."""
    prefix = f"  [{sample_idx:>2}/{n_total}]"
    def _cb(stage: str, detail: str):
        if not verbose:
            return
        tag = _WAVE_ICONS.get(stage, stage[:5].upper().ljust(5))
        print(f"{prefix} [{tag}] {detail}", flush=True)
    return _cb


# ── Main evaluation loop ──────────────────────────────────────────────────────

def run_lag_evaluation(
    model: str = "claude-haiku-4-5-20251001",
    n_samples: int = 0,
    use_sure: bool = False,
    verbose: bool = True,
):
    """
    Full LAG evaluation pipeline.

    Steps:
      1. Load benchmark
      2. Run LongAnswerPipeline.assess() on each sample
      3. Compute and print metrics
    """
    root = os.path.dirname(os.path.abspath(__file__))
    benchmark_path = os.path.join(root, "data", "lag_benchmark.json")

    # ── Banner ──────────────────────────────────────────────────────────────
    print("=" * 72)
    print("  ConceptGrade — Long Answer Grading (LAG) Evaluation")
    print(f"  Benchmark  : {benchmark_path}")
    print(f"  Model      : {model}")
    sure_label = "ON (flagging ambiguous samples for human review)" if use_sure else "OFF"
    print(f"  SURE mode  : {sure_label}")
    print("=" * 72)
    print()

    # ── API key ─────────────────────────────────────────────────────────────
    api_key = get_api_key(model)

    # ── Load benchmark ──────────────────────────────────────────────────────
    print("[1/3] Loading LAG benchmark...")
    samples = load_benchmark(benchmark_path)
    if n_samples and n_samples < len(samples):
        samples = stratified_subsample(samples, n_samples)
        print(f"  Sub-sampled to {len(samples)} samples (stratified by score).")
    else:
        print(f"  Loaded {len(samples)} samples.")

    score_dist = {}
    for s in samples:
        bucket = f"{int(s['human_score'] * 2) / 2:.1f}"
        score_dist[bucket] = score_dist.get(bucket, 0) + 1
    dist_str = ", ".join(f"{k}:{v}" for k, v in sorted(score_dist.items()))
    print(f"  Score distribution (bucket:count): {dist_str}")
    print()

    # ── Initialise pipelines ────────────────────────────────────────────────
    print("[2/3] Initialising LongAnswerPipeline + Pure LLM baseline...")
    from conceptgrade.lag_pipeline import LongAnswerPipeline
    from conceptgrade.llm_client import LLMClient
    pipeline = LongAnswerPipeline(
        api_key=api_key,
        model=model,
        max_workers=8,
        use_sure=True,
    )
    llm_client = LLMClient(api_key=api_key)
    print("  Pipeline ready.")
    print()

    # ── Per-sample evaluation ───────────────────────────────────────────────
    print("[3/3] Evaluating samples...")
    print()

    human_scores: list[float] = []
    lag_scores:   list[float] = []
    pure_scores:  list[float] = []
    sure_flags:   list[bool]  = []
    rows: list[dict] = []

    total = len(samples)
    eval_start = time.time()

    for idx, sample in enumerate(samples, start=1):
        sid = str(sample.get("id", idx))
        q_snippet = sample["question"][:45] + ("..." if len(sample["question"]) > 45 else "")
        gt = float(sample["human_score"])

        print(f"  Sample {idx:>2}/{total}  GT={gt:.1f}  Q: {q_snippet}", flush=True)

        cb = make_progress_callback(idx, total, verbose=verbose)
        t0 = time.time()

        # Pure LLM baseline
        try:
            pure_raw = pure_llm_grade_lag(
                llm_client, model,
                sample["question"], sample["reference_answer"], sample["student_answer"]
            )
        except Exception as e:
            print(f"    Pure-LLM ERROR: {e}", file=sys.stderr)
            pure_raw = 0.0

        # ConceptGrade LAG pipeline
        try:
            result = pipeline.assess(
                question=sample["question"],
                student_answer=sample["student_answer"],
                reference_answer=sample["reference_answer"],
                student_id=f"s{sid}",
            )
            lag_raw = float(result.aggregated.final_score)  # already 0-5
        except Exception as e:
            print(f"    ERROR on sample {idx}: {e}", file=sys.stderr)
            lag_raw = 0.0

        elapsed = time.time() - t0
        lag = round(lag_raw, 2)
        pure = round(pure_raw, 2)
        delta = round(lag - gt, 2)
        delta_pure = round(pure - gt, 2)

        sure_flag = requires_human_review(lag) if use_sure else False
        sure_str  = "REVIEW" if sure_flag else "ok    "

        # Feedback one-liner
        try:
            fb_snippet = (result.feedback.one_line_summary or "")[:60]
        except Exception:
            fb_snippet = ""

        human_scores.append(gt)
        lag_scores.append(lag)
        pure_scores.append(pure)
        sure_flags.append(sure_flag)

        rows.append({
            "idx":        idx,
            "id":         sid,
            "topic":      sample.get("topic", ""),
            "gt":         gt,
            "pure":       pure,
            "lag":        lag,
            "delta":      delta,
            "delta_pure": delta_pure,
            "sure":       sure_str,
            "elapsed":    round(elapsed, 1),
            "feedback":   fb_snippet,
        })

        print(
            f"    → PureLLM={pure:.2f}  LAG={lag:.2f}  "
            f"Δ_pure={delta_pure:+.2f}  Δ_lag={delta:+.2f}  "
            f"SURE={sure_str}  ({elapsed:.1f}s)  \"{fb_snippet}\"",
            flush=True,
        )
        print()

    total_elapsed = time.time() - eval_start

    # ── Per-sample table ─────────────────────────────────────────────────────
    print("─" * 100)
    print("  PER-SAMPLE RESULTS")
    print("─" * 100)
    sure_col = "  SURE  " if use_sure else ""
    header = f"  {'#':>3}  {'ID':<6}  {'Topic':<22}  {'GT':>5}  {'LAG':>5}  {'Δ':>6}{sure_col}  Feedback"
    print(header)
    print("  " + "-" * 97)
    for r in rows:
        sure_part = f"  {r['sure']:<6}" if use_sure else ""
        fb = r["feedback"][:40] if r["feedback"] else ""
        print(
            f"  {r['idx']:>3}  {r['id']:<6}  {r['topic']:<22}  "
            f"{r['gt']:>5.1f}  {r['lag']:>5.2f}  {r['delta']:>+6.2f}"
            f"{sure_part}  \"{fb}\""
        )
    print()

    # ── Aggregate metrics ────────────────────────────────────────────────────
    metrics_lag  = compute_metrics(human_scores, lag_scores)
    metrics_pure = compute_metrics(human_scores, pure_scores)
    review_rate  = sum(sure_flags) / len(sure_flags) if sure_flags else 0.0
    # alias for backward compat in prints below
    metrics = metrics_lag

    print("=" * 80)
    print("  LAG EVALUATION SUMMARY — ConceptGrade vs Pure LLM vs Ground Truth")
    print("=" * 80)
    print(f"  Samples evaluated      : {len(human_scores)}")
    print(f"  Total wall time        : {total_elapsed:.1f}s  "
          f"({total_elapsed / len(human_scores):.1f}s/sample avg)")
    print()
    print(f"  {'Metric':<30} {'Pure LLM':>10}  {'ConceptGrade':>13}")
    print("  " + "-" * 58)
    print(f"  {'Pearson r':<30} {metrics_pure['pearson_r']:>10.4f}  "
          f"{metrics_lag['pearson_r']:>13.4f}")
    print(f"  {'RMSE':<30} {metrics_pure['rmse']:>10.4f}  "
          f"{metrics_lag['rmse']:>13.4f}")
    print(f"  {'MAE':<30} {metrics_pure['mae']:>10.4f}  "
          f"{metrics_lag['mae']:>13.4f}")
    print(f"  {'QWK (quadratic weighted κ)':<30} {metrics_pure['qwk']:>10.4f}  "
          f"{metrics_lag['qwk']:>13.4f}")
    print(f"  {'Bias (mean Δ - GT)':<30} {metrics_pure['bias']:>+10.4f}  "
          f"{metrics_lag['bias']:>+13.4f}")
    if use_sure:
        print(f"  {'requires_human_review rate':<30} {'':>10}  {review_rate:>13.1%}")
    print()

    # Interpretation guide
    print("  INTERPRETATION")
    print("  ─────────────────────────────────────────────────────")
    r = metrics["pearson_r"]
    if r >= 0.80:
        r_interp = "Excellent agreement with human graders"
    elif r >= 0.65:
        r_interp = "Good agreement with human graders"
    elif r >= 0.45:
        r_interp = "Moderate agreement — review systematic errors"
    else:
        r_interp = "Low agreement — pipeline needs recalibration"
    print(f"  Pearson r  = {r:.3f}  → {r_interp}")

    q = metrics["qwk"]
    if q >= 0.80:
        q_interp = "Near-human ordinal agreement"
    elif q >= 0.60:
        q_interp = "Substantial ordinal agreement"
    elif q >= 0.40:
        q_interp = "Moderate ordinal agreement"
    else:
        q_interp = "Fair / poor ordinal agreement"
    print(f"  QWK        = {q:.3f}  → {q_interp}")

    bias = metrics["bias"]
    if abs(bias) < 0.15:
        b_interp = "Unbiased"
    elif bias > 0:
        b_interp = f"System over-estimates by {abs(bias):.2f} pts on average"
    else:
        b_interp = f"System under-estimates by {abs(bias):.2f} pts on average"
    print(f"  Bias       = {bias:+.3f}  → {b_interp}")
    print()

    # ── Save results ─────────────────────────────────────────────────────────
    output_dir = os.path.join(root, "data")
    os.makedirs(output_dir, exist_ok=True)
    results = {
        "meta": {
            "framework":    "ConceptGrade LAG Evaluation",
            "benchmark":    "lag_benchmark.json (hand-crafted, 5 CS topics)",
            "num_samples":  len(human_scores),
            "model":        model,
            "sure_enabled": use_sure,
            "timestamp":    datetime.now().isoformat(),
            "total_elapsed_seconds": round(total_elapsed, 2),
        },
        "metrics_lag":  {k: round(v, 6) for k, v in metrics_lag.items()},
        "metrics_pure": {k: round(v, 6) for k, v in metrics_pure.items()},
        "requires_human_review_rate": round(review_rate, 4),
        "samples": rows,
        "human_scores": human_scores,
        "lag_scores":   lag_scores,
        "pure_scores":  pure_scores,
    }
    out_path = os.path.join(output_dir, "lag_evaluation_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"  Results saved → {out_path}")
    print()
    print("  LAG evaluation complete.")
    print("=" * 72)


# ── CLI entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "ConceptGrade Long Answer Grading (LAG) Evaluation.\n"
            "Evaluates LongAnswerPipeline against data/lag_benchmark.json."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model", default="claude-haiku-4-5-20251001",
        help=(
            "LLM model name. Provider auto-detected:\n"
            "  claude-*  → Anthropic  (ANTHROPIC_API_KEY)\n"
            "  gemini-*  → Google     (GEMINI_API_KEY)\n"
            "  gpt-*     → OpenAI     (OPENAI_API_KEY)\n"
            "Default: claude-haiku-4-5-20251001"
        ),
    )
    parser.add_argument(
        "--n-samples", type=int, default=0,
        help=(
            "Evaluate only N samples (stratified across score range). "
            "Default 0 = all samples. Use 5 for a quick sanity check."
        ),
    )
    parser.add_argument(
        "--sure", action="store_true",
        help=(
            "Enable SURE (Selective Uncertainty-driven Review). "
            "Marks samples scoring 1.5-3.5 as requiring human review."
        ),
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-wave progress output; only print the final table.",
    )
    args = parser.parse_args()

    run_lag_evaluation(
        model=args.model,
        n_samples=args.n_samples,
        use_sure=args.sure,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
