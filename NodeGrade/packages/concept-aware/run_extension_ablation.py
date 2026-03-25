"""
ConceptGrade Extension Ablation Study.

Evaluates the contribution of each research extension to grading performance
on the Mohler et al. (2011) CS Short Answer dataset.

Configurations compared
-----------------------
  C0  Cosine-Only Baseline          — TF-IDF cosine similarity only
  C1  ConceptGrade Baseline         — standard extractor + standard comparator
  C2  ConceptGrade + SC             — + Self-Consistent Extraction (Ext 1)
  C3  ConceptGrade + CW             — + Confidence-Weighted Comparison (Ext 2)
  C4  ConceptGrade + Verifier       — + LLM-as-Verifier (Ext 3)
  C5  ConceptGrade + All Extensions — C2 + C3 + C4 (full research system)

Two modes
---------
  --mode heuristic  Fast (~5s). Uses rule/TF-IDF components to SIMULATE
                    extension effects. Use for quick iteration and paper
                    layout testing. No API calls.

  --mode llm        Slow (~30 min, 30 samples × 3-4 LLM calls).
                    Uses the real ConceptGrade pipeline for each config.
                    Requires GROQ_API_KEY. Produces publishable results.

Usage
-----
    python3 run_extension_ablation.py --mode heuristic
    python3 run_extension_ablation.py --mode llm --n_samples 30

Output
------
    data/extension_ablation_results.json
    data/extension_ablation_summary.txt
    data/extension_ablation_latex.tex   ← ready to paste into paper
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
from scipy.stats import pearsonr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datasets.mohler_loader import load_mohler_sample, MohlerSample
from evaluation.metrics import (
    evaluate_grading,
    add_bootstrap_cis,
    wilcoxon_significance,
    format_comparison_table,
    format_significance_table,
    EvaluationResult,
)

# ─── Configuration names ────────────────────────────────────────────────────

CONFIGS = [
    ("C0", "Cosine-Only Baseline"),
    ("C1", "ConceptGrade Baseline"),
    ("C2", "ConceptGrade + SC"),
    ("C3", "ConceptGrade + CW"),
    ("C4", "ConceptGrade + Verifier"),
    ("C5", "ConceptGrade + All Extensions"),
]

# ─── Heuristic feature extraction ───────────────────────────────────────────

CONCEPT_KEYWORDS = {
    "linked list": ["linked list","node","pointer","head","tail","traversal","insertion","deletion","o(1)","o(n)","linear"],
    "arrays":      ["array","contiguous","index","random access","shifting","o(n)","memory","insertion"],
    "stack":       ["stack","lifo","last in first out","push","pop","peek","undo","recursion","backtrack"],
    "binary search tree": ["bst","binary search tree","binary tree","left subtree","right subtree","o(log n)","balanced","skewed","ordering","search"],
    "bfs":         ["bfs","breadth","queue","level","shortest path","neighbor"],
    "dfs":         ["dfs","depth","stack","recursion","backtrack","topological","cycle detection"],
    "hash table":  ["hash","hash function","hash table","collision","chaining","open addressing","probing","bucket","o(1)","key","value"],
}

DEPTH_MARKERS = {
    "because":0.15,"therefore":0.15,"since":0.10,"however":0.12,"although":0.10,
    "for example":0.15,"such as":0.10,"e.g.":0.10,"compared to":0.12,"in contrast":0.12,
    "unlike":0.10,"worst case":0.15,"best case":0.12,"average case":0.12,
    "o(":0.15,"time complexity":0.15,"space complexity":0.12,"complexity":0.10,
}

MISCONCEPTION_PATTERNS = [
    ("linked list","o(1)","access"),
    ("always o(1)","hash"),
    ("first in first out","stack"),
    ("always o(log n)","bst"),
    ("stack","bfs"),
    ("queue","dfs"),
]


def _heuristic_features(sample: MohlerSample) -> dict:
    """Extract scoring components without any LLM calls."""
    answer = sample.student_answer.lower()
    reference = sample.reference_answer.lower()

    # Cosine similarity (TF-IDF)
    try:
        vec = TfidfVectorizer(lowercase=True, stop_words="english",
                              ngram_range=(1, 3), max_features=5000)
        tfidf = vec.fit_transform([reference, answer])
        cosine = float(sk_cosine(tfidf[0:1], tfidf[1:2])[0][0])
    except Exception:
        cosine = 0.0

    # Concept coverage
    relevant = set()
    for topic, kws in CONCEPT_KEYWORDS.items():
        if any(kw in sample.question.lower() for kw in [topic] + kws[:2]):
            relevant.update(kws)
    if not relevant:
        relevant = set(reference.split())
    found = sum(1 for c in relevant if c in answer)
    coverage = min(1.0, found / max(len(relevant) * 0.6, 1))

    # Depth score (SOLO / Bloom's proxy)
    depth = min(1.0, sum(v for k, v in DEPTH_MARKERS.items() if k in answer))

    # SOLO approximation
    sentences = [s.strip() for s in answer.replace(".", ".\n").split("\n") if s.strip()]
    n = len(sentences)
    if n >= 4 and depth > 0.3:
        solo = min(1.0, 0.6 + depth * 0.4)
    elif n >= 3:
        solo = min(0.8, 0.3 + n * 0.1 + depth * 0.2)
    elif n >= 2:
        solo = min(0.5, 0.15 + n * 0.1)
    else:
        solo = 0.1

    # Accuracy (penalise misconceptions)
    accuracy = max(0.0, 1.0 - 0.15 * sum(
        all(t in answer for t in m) for m in MISCONCEPTION_PATTERNS
    ))

    # Completeness
    completeness = min(1.0, len(answer) / max(len(reference), 1))

    # Simulated extraction confidence (correlated with depth and coverage)
    # A student who shows more depth extracts concepts more confidently
    simulated_confidence = min(1.0, 0.5 + 0.3 * depth + 0.2 * coverage)

    return dict(
        cosine=cosine,
        coverage=coverage,
        depth=depth,
        solo=solo,
        accuracy=accuracy,
        completeness=completeness,
        confidence=simulated_confidence,
    )


def _heuristic_score(f: dict, config: str) -> float:
    """
    Compute 0-5 score from heuristic features under each ablation config.

    Extension simulation:
      SC  (+0.03 to coverage for high-depth answers) — SC reduces false negatives
          so high-depth answers get slightly better coverage credit.
      CW  (multiply coverage by confidence) — low-confidence extractions
          contribute less to coverage.
      Ver (post-blend: 15% LLM correction pulling toward extremes) — the verifier
          increases high scores and decreases low scores based on cosine+depth.
    """
    c = dict(f)

    use_sc  = "SC"  in config or "All" in config
    use_cw  = "CW"  in config or "All" in config
    use_ver = "Ver" in config or "All" in config

    # Extension 1: Self-Consistency — reduces false negatives for deep answers
    # In real mode, SC reduces hallucinated concepts (false positives) and
    # catches missed concepts (false negatives) via majority voting.
    # Simulated: small coverage boost proportional to depth.
    if use_sc:
        sc_boost = min(0.10, f["depth"] * 0.18)  # deeper → fewer missed concepts
        c["coverage"] = min(1.0, c["coverage"] + sc_boost)

    # Extension 2: Confidence-Weighted — blend coverage with extraction confidence
    # alpha=0.5: partial weighting (full weighting alpha=1.0 was too aggressive
    # for heuristic simulation; real LLM confidences are typically 0.75-0.95).
    if use_cw:
        alpha = 0.5
        c["coverage"] = c["coverage"] * (alpha * c["confidence"] + (1.0 - alpha))

    if config == "C0":  # Cosine-only
        raw = c["cosine"]
    elif config == "C1":
        # Baseline ConceptGrade: concept-aware, slightly better calibrated than cosine
        # Adding coverage and depth provides incremental gains over raw cosine.
        raw = (
            c["cosine"]       * 0.05 +
            c["coverage"]     * 0.30 +
            c["depth"]        * 0.22 +
            c["solo"]         * 0.22 +
            c["accuracy"]     * 0.13 +
            c["completeness"] * 0.08
        )
    else:
        raw = (
            c["cosine"]       * 0.05 +
            c["coverage"]     * 0.30 +
            c["depth"]        * 0.22 +
            c["solo"]         * 0.22 +
            c["accuracy"]     * 0.13 +
            c["completeness"] * 0.08
        )

    # Extension 3: Verifier — blend with LLM correction signal
    # LLM verifier is most helpful for answers that rely on vocabulary not in
    # the KG ontology. Simulated: 20% blend toward a "holistic" cosine+depth signal.
    if use_ver:
        holistic = (c["cosine"] * 0.6 + c["depth"] * 0.25 + c["accuracy"] * 0.15)
        raw = 0.80 * raw + 0.20 * holistic

    score = round(max(0.0, min(5.0, raw * 5.0)), 2)
    return score


# ─── Heuristic mode ─────────────────────────────────────────────────────────

def run_heuristic(samples: list[MohlerSample]) -> dict[str, list[float]]:
    """Run all configs using heuristic scoring (no LLM)."""
    features = [_heuristic_features(s) for s in samples]
    config_scores = {}
    for cid, cname in CONFIGS:
        config_scores[cid] = [_heuristic_score(f, cname) for f in features]
    return config_scores


# ─── LLM mode ────────────────────────────────────────────────────────────────

def run_llm_config(
    samples: list[MohlerSample],
    config_id: str,
    config_name: str,
    api_key: str,
) -> list[float]:
    """Run a single config using the real ConceptGrade pipeline."""
    from conceptgrade.pipeline import ConceptGradePipeline

    use_sc  = "SC"  in config_name or "All" in config_name
    use_cw  = "CW"  in config_name or "All" in config_name
    use_ver = "Ver" in config_name or "All" in config_name

    if config_id == "C0":
        # Cosine-only: pure TF-IDF, no pipeline
        scores = []
        for s in samples:
            try:
                vec = TfidfVectorizer(lowercase=True, stop_words="english",
                                      ngram_range=(1,3), max_features=5000)
                tfidf = vec.fit_transform([s.reference_answer, s.student_answer])
                cosine = float(sk_cosine(tfidf[0:1], tfidf[1:2])[0][0])
            except Exception:
                cosine = 0.0
            scores.append(round(cosine * 5.0, 2))
        return scores

    pipeline = ConceptGradePipeline(
        api_key=api_key,
        use_self_consistency=use_sc,
        use_confidence_weighting=use_cw,
        use_llm_verifier=use_ver,
        verifier_weight=0.25,
        rate_limit_delay=2.0,
    )

    scores = []
    for i, sample in enumerate(samples):
        print(f"    [{config_id}] sample {i+1}/{len(samples)}: {sample.question_id}...")
        try:
            result = pipeline.assess_student(
                student_id=f"s{i}",
                question=sample.question,
                answer=sample.student_answer,
            )
            # Map 0-1 overall score to 0-5 scale
            score = round(result.overall_score * 5.0, 2)
        except Exception as e:
            print(f"      ERROR: {e} — using 0")
            score = 0.0
        scores.append(score)
        time.sleep(0.5)

    return scores


def run_llm(samples: list[MohlerSample], api_key: str) -> dict[str, list[float]]:
    """Run all configs using the real pipeline (slow)."""
    config_scores = {}
    for cid, cname in CONFIGS:
        print(f"\n  Running config {cid}: {cname}")
        config_scores[cid] = run_llm_config(samples, cid, cname, api_key)
    return config_scores


# ─── Evaluation & reporting ──────────────────────────────────────────────────

def evaluate_all(
    human: list[float],
    config_scores: dict[str, list[float]],
) -> dict[str, EvaluationResult]:
    results = {}
    for cid, cname in CONFIGS:
        scores = config_scores[cid]
        ev = evaluate_grading(human, scores, task_name=cname)
        add_bootstrap_cis(ev, human, scores)
        results[cid] = ev
    return results


def print_main_table(results: dict[str, EvaluationResult]) -> str:
    header = (
        f"{'Config':<4}  {'System':<32}  {'Pearson r':>9}  {'QWK':>7}  "
        f"{'RMSE':>7}  {'MAE':>7}"
    )
    sep = "─" * 72
    rows = [header, sep]
    for cid, cname in CONFIGS:
        ev = results[cid]
        ci_r = ev.pearson_r_ci
        rows.append(
            f"{cid:<4}  {cname:<32}  "
            f"{ev.pearson_r:>9.4f}  {ev.qwk:>7.4f}  "
            f"{ev.rmse:>7.4f}  {ev.mae:>7.4f}"
        )
    rows.append(sep)
    txt = "\n".join(rows)
    print(txt)
    return txt


def print_delta_table(results: dict[str, EvaluationResult]) -> str:
    base = results["C1"]
    header = (
        f"{'Config':<4}  {'System':<32}  {'ΔPearson r':>11}  "
        f"{'ΔQWK':>7}  {'ΔRMSE':>7}  Impact"
    )
    sep = "─" * 80
    rows = [header, sep]
    for cid, cname in CONFIGS[1:]:
        ev = results[cid]
        dr   = ev.pearson_r - base.pearson_r
        dq   = ev.qwk       - base.qwk
        drmse = ev.rmse     - base.rmse
        impact = "HIGH" if abs(dr) > 0.05 else ("MED" if abs(dr) > 0.02 else "LOW")
        sign_r = f"{dr:+.4f}"
        rows.append(
            f"{cid:<4}  {cname:<32}  {sign_r:>11}  "
            f"{dq:>+7.4f}  {drmse:>+7.4f}  {impact}"
        )
    rows.append(sep)
    txt = "\n".join(rows)
    print(txt)
    return txt


def print_significance(
    human: list[float],
    config_scores: dict[str, list[float]],
    results: dict[str, EvaluationResult],
) -> str:
    tests = []
    for cid, cname in CONFIGS[1:]:
        t = wilcoxon_significance(
            human,
            config_scores[cid],
            config_scores["C1"],
            cname,
            "ConceptGrade Baseline",
        )
        tests.append(t)
    txt = format_significance_table(tests)
    print(txt)
    return txt


def generate_latex_table(results: dict[str, EvaluationResult]) -> str:
    """
    Generate a LaTeX booktabs table for the paper.

    Example output:
    \\begin{table}[h]
    \\caption{...}
    \\begin{tabular}{llrrrr}
    ...
    \\end{tabular}
    \\end{table}
    """
    lines = [
        "% ConceptGrade Extension Ablation — auto-generated",
        "\\begin{table}[h]",
        "\\centering",
        "\\caption{Ablation study on the Mohler et al. (2011) dataset ($n=30$). "
        "SC = Self-Consistent Extraction, CW = Confidence-Weighted Comparison, "
        "Ver = LLM Verifier. Bold = best per column.}",
        "\\label{tab:ablation}",
        "\\begin{tabular}{@{}llrrrr@{}}",
        "\\toprule",
        "\\textbf{ID} & \\textbf{System} & \\textbf{Pearson $r$} & "
        "\\textbf{QWK} & \\textbf{RMSE} & \\textbf{MAE} \\\\",
        "\\midrule",
    ]

    # Find best values per metric (excluding C0 for best detection)
    full_results = [results[cid] for cid, _ in CONFIGS]
    best_r    = max(ev.pearson_r for ev in full_results)
    best_qwk  = max(ev.qwk      for ev in full_results)
    best_rmse = min(ev.rmse     for ev in full_results)
    best_mae  = min(ev.mae      for ev in full_results)

    def fmt(val, best, higher_better=True):
        bold = (higher_better and abs(val - best) < 1e-4) or \
               (not higher_better and abs(val - best) < 1e-4)
        s = f"{val:.4f}"
        return f"\\textbf{{{s}}}" if bold else s

    for cid, cname in CONFIGS:
        ev = results[cid]
        r_str    = fmt(ev.pearson_r, best_r,    higher_better=True)
        q_str    = fmt(ev.qwk,       best_qwk,  higher_better=True)
        rmse_str = fmt(ev.rmse,      best_rmse, higher_better=False)
        mae_str  = fmt(ev.mae,       best_mae,  higher_better=False)
        lines.append(
            f"{cid} & {cname} & {r_str} & {q_str} & {rmse_str} & {mae_str} \\\\"
        )
        if cid == "C1":
            lines.append("\\midrule")

    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ]
    return "\n".join(lines)


def print_per_question(
    dataset,
    config_scores: dict[str, list[float]],
) -> str:
    print(f"\n{'─'*72}")
    print("  Per-question Pearson r: Baseline vs Full Extensions")
    print(f"{'─'*72}")
    rows = [f"{'QID':<5}  {'Question (truncated)':<50}  {'C1 r':>6}  {'C5 r':>6}  Δ"]
    rows.append("─" * 72)
    for qid in sorted(dataset.questions.keys()):
        q_samples = dataset.get_by_question(qid)
        if len(q_samples) < 3:
            continue
        q_human = [s.score_avg for s in q_samples]
        q_idx   = [i for i, s in enumerate(dataset.samples) if s.question_id == qid]
        for cfg in ("C1", "C5"):
            q_pred = [config_scores[cfg][i] for i in q_idx]
            r, _ = pearsonr(q_human, q_pred)
            if cfg == "C1":
                r_c1 = r
            else:
                r_c5 = r
        delta = r_c5 - r_c1
        q_text = dataset.questions[qid][:50]
        rows.append(f"{qid:<5}  {q_text:<50}  {r_c1:>6.4f}  {r_c5:>6.4f}  {delta:+.4f}")
    txt = "\n".join(rows)
    print(txt)
    return txt


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ConceptGrade Extension Ablation Study")
    parser.add_argument(
        "--mode", choices=["heuristic", "llm"], default="heuristic",
        help="heuristic=fast/no-LLM (default), llm=real pipeline"
    )
    parser.add_argument(
        "--n_samples", type=int, default=30,
        help="Number of Mohler samples to evaluate (LLM mode only)"
    )
    parser.add_argument(
        "--api_key", type=str,
        default=os.environ.get("GROQ_API_KEY"),
        help="Groq API key (LLM mode only, or set GROQ_API_KEY env var)"
    )
    args = parser.parse_args()

    print("=" * 72)
    print("  ConceptGrade Extension Ablation Study")
    print("  Mohler et al. (2011) CS Short Answer Dataset")
    print(f"  Mode: {args.mode.upper()}")
    print("=" * 72)

    dataset = load_mohler_sample()
    samples = dataset.samples[:args.n_samples]
    human   = [s.score_avg for s in samples]
    print(f"\nLoaded {len(samples)} samples across {len(dataset.questions)} questions.")
    print(f"Score distribution: {dataset.score_distribution()}\n")

    # ── Run scoring ──────────────────────────────────────────────────────────
    t0 = time.time()
    if args.mode == "heuristic":
        print("Running heuristic feature extraction (no LLM)...")
        config_scores = run_heuristic(samples)
    else:
        print("Running real ConceptGrade pipeline (LLM mode)...")
        print("NOTE: This will consume Groq API tokens. Estimated time: 20-40 min.\n")
        config_scores = run_llm(samples, args.api_key)
    elapsed = time.time() - t0
    print(f"\nScoring complete in {elapsed:.1f}s.\n")

    # ── Evaluate ─────────────────────────────────────────────────────────────
    results = evaluate_all(human, config_scores)

    # ── Print results ─────────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print("  MAIN RESULTS TABLE")
    print(f"{'='*72}\n")
    main_table = print_main_table(results)

    print(f"\n{'='*72}")
    print("  DELTA vs BASELINE (C1)")
    print(f"{'='*72}\n")
    delta_table = print_delta_table(results)

    print(f"\n{'='*72}")
    print("  STATISTICAL SIGNIFICANCE vs BASELINE (Wilcoxon Signed-Rank)")
    print(f"{'='*72}\n")
    sig_table = print_significance(human, config_scores, results)

    per_q = print_per_question(dataset, config_scores)

    # ── 95% CI detail ─────────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print("  95% BOOTSTRAP CONFIDENCE INTERVALS")
    print(f"{'='*72}")
    for cid, cname in CONFIGS:
        ev = results[cid]
        ci_r = ev.pearson_r_ci
        ci_q = ev.qwk_ci
        print(f"  {cid}  {cname:<32}  r={ev.pearson_r:.4f} [{ci_r[0]:.4f},{ci_r[1]:.4f}]"
              f"  QWK={ev.qwk:.4f} [{ci_q[0]:.4f},{ci_q[1]:.4f}]")

    # ── LaTeX ────────────────────────────────────────────────────────────────
    latex = generate_latex_table(results)

    # ── Save outputs ─────────────────────────────────────────────────────────
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)

    json_path  = os.path.join(out_dir, "extension_ablation_results.json")
    txt_path   = os.path.join(out_dir, "extension_ablation_summary.txt")
    latex_path = os.path.join(out_dir, "extension_ablation_latex.tex")

    output = {
        "meta": {
            "study": "ConceptGrade Extension Ablation Study",
            "mode": args.mode,
            "dataset": f"Mohler et al. (2011) n={len(samples)}",
            "timestamp": datetime.now().isoformat(),
        },
        "configs": {cid: cname for cid, cname in CONFIGS},
        "scores": config_scores,
        "metrics": {cid: results[cid].to_dict() for cid, _ in CONFIGS},
        "human_scores": human,
    }
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    summary_lines = [
        "ConceptGrade Extension Ablation Study",
        "=" * 72,
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Mode: {args.mode.upper()}",
        f"Dataset: Mohler et al. (2011) — {len(samples)} samples",
        "",
        "MAIN RESULTS TABLE:", main_table,
        "",
        "DELTA vs BASELINE:", delta_table,
        "",
        "SIGNIFICANCE TESTS:", sig_table,
        "",
        "PER-QUESTION BREAKDOWN:", per_q,
        "",
        "LATEX TABLE:", latex,
    ]
    with open(txt_path, "w") as f:
        f.write("\n".join(summary_lines))

    with open(latex_path, "w") as f:
        f.write(latex)

    print(f"\n{'='*72}")
    print("  OUTPUT FILES")
    print(f"{'='*72}")
    print(f"  JSON:    {json_path}")
    print(f"  Summary: {txt_path}")
    print(f"  LaTeX:   {latex_path}")
    print()
    print("Ablation study complete.")


if __name__ == "__main__":
    main()
