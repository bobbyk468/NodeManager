"""
Score the targeted 8-sample re-score response (Q4 BST + Q10 Big-O).

Expects:
  /tmp/rescore_targeted_response.json  — Gemini response in format:
    {"scores": {"37": {"holistic_score": X.X, ...}, "42": {...}, ...}}
  OR
    {"scores": {"37": X.X, "42": X.X, ...}}

Updates C5_fix scores for the targeted IDs and shows whether
Q4 (IDs 36-47) and Q10 (IDs 108-119) flip to ConceptGrade wins.

Usage:
    python3 score_targeted_rescore.py
"""

import json
import os
import sys

import numpy as np
from scipy.stats import wilcoxon

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

CHECKPOINT = os.path.join(DATA_DIR, "ablation_checkpoint_gemini_flash_latest.json")
DUAL_SCORES = os.path.join(DATA_DIR, "gemini_kg_dual_scores.json")
RESPONSE_PATH = "/tmp/rescore_targeted_response.json"

TARGETED_IDS = [37, 42, 112, 113, 114, 116, 117, 118]

SEP = "─" * 72
N = 120


def load_response(path: str) -> dict[int, float]:
    with open(path) as f:
        raw = json.load(f)
    sc = raw.get("scores", raw)
    result = {}
    for k, v in sc.items():
        if isinstance(v, dict):
            result[int(k)] = float(v.get("holistic_score", v.get("score", 0.0)))
        else:
            result[int(k)] = float(v)
    return result


def per_question_mae(errors: np.ndarray, q_ids: range) -> float:
    return float(np.mean(np.abs(errors[list(q_ids)])))


def main() -> None:
    print(SEP)
    print("Targeted Re-score Analysis (Q4 BST + Q10 Big-O)")
    print(SEP)

    if not os.path.exists(RESPONSE_PATH):
        print(f"ERROR: {RESPONSE_PATH} not found.")
        print("Paste Gemini's response to /tmp/rescore_targeted_response.json first.")
        sys.exit(1)

    # Load baseline
    with open(CHECKPOINT) as f:
        ckpt = json.load(f)
    with open(DUAL_SCORES) as f:
        dual = json.load(f)

    h = np.array(ckpt["human_scores"])
    cllm = np.array(ckpt["scores"]["C_LLM"])
    c5_orig = np.array([dual["holistic_scores"][str(i)] for i in range(N)])

    # Load targeted rescore
    new_scores = load_response(RESPONSE_PATH)
    print(f"Loaded {len(new_scores)} re-scored samples: {sorted(new_scores.keys())}")

    # Build updated C5 array
    c5_new = c5_orig.copy()
    for sid, score in new_scores.items():
        c5_new[sid] = score

    # Show per-sample changes for targeted IDs
    print(f"\n{'ID':>4}  {'Human':6}  {'Old_C5':6}  {'New_C5':6}  {'C_LLM':6}  {'Old_e':5}  {'New_e':5}  {'LLM_e':5}  {'Δe':6}")
    print("─" * 72)
    for sid in TARGETED_IDS:
        old_e = abs(c5_orig[sid] - h[sid])
        new_e = abs(c5_new[sid] - h[sid])
        llm_e = abs(cllm[sid] - h[sid])
        delta_e = new_e - old_e
        q_tag = "Q4" if sid < 100 else "Q10"
        win = "✓" if new_e < llm_e else ("=" if new_e == llm_e else "✗")
        print(f"{sid:>4}[{q_tag}] h={h[sid]:.2f}  c5_old={c5_orig[sid]:.2f}  "
              f"c5_new={c5_new[sid]:.2f}  llm={cllm[sid]:.2f}  "
              f"e_old={old_e:.2f}  e_new={new_e:.2f}  e_llm={llm_e:.2f}  "
              f"Δe={delta_e:+.2f}  {win}")

    # Per-question analysis
    questions = {
        "Q1": range(0, 12),   "Q2": range(12, 24),  "Q3": range(24, 36),
        "Q4": range(36, 48),  "Q5": range(48, 60),  "Q6": range(60, 72),
        "Q7": range(72, 84),  "Q8": range(84, 96),  "Q9": range(96, 108),
        "Q10": range(108, 120),
    }

    print(f"\n{'Q':3}  {'MAE_C5_old':10}  {'MAE_C5_new':10}  {'MAE_LLM':7}  {'Old':5}  {'New':5}")
    print("─" * 60)
    wins_old = wins_new = 0
    for qname, ids in questions.items():
        mae_old = per_question_mae(np.abs(c5_orig - h), ids)
        mae_new = per_question_mae(np.abs(c5_new - h), ids)
        mae_llm = per_question_mae(np.abs(cllm - h), ids)
        old_win = "WIN" if mae_old < mae_llm else "LOSE"
        new_win = "WIN" if mae_new < mae_llm else "LOSE"
        wins_old += int(mae_old < mae_llm)
        wins_new += int(mae_new < mae_llm)
        change = " ← FLIPPED!" if old_win != new_win else ""
        print(f"{qname:3}  {mae_old:10.4f}  {mae_new:10.4f}  {mae_llm:7.4f}  {old_win:5}  {new_win:5}{change}")

    print(f"\nPer-question wins: {wins_old}/10 → {wins_new}/10")

    # Overall metrics
    mae_orig = float(np.mean(np.abs(c5_orig - h)))
    mae_new_all = float(np.mean(np.abs(c5_new - h)))
    mae_llm_all = float(np.mean(np.abs(cllm - h)))

    print(f"\nOverall MAE: C5_orig={mae_orig:.4f}  C5_new={mae_new_all:.4f}  C_LLM={mae_llm_all:.4f}")
    print(f"C5_new improvement vs C_LLM: {(mae_llm_all - mae_new_all)/mae_llm_all*100:.1f}%")

    # Wilcoxon test on new scores
    ae_c5_new = np.abs(c5_new - h)
    ae_cllm = np.abs(cllm - h)
    try:
        stat, p = wilcoxon(ae_c5_new, ae_cllm)
        print(f"Wilcoxon p (C5_new vs C_LLM): {p:.4f} {'*** SIGNIFICANT' if p < 0.01 else ''}")
    except Exception as e:
        print(f"Wilcoxon test error: {e}")

    # Save updated C5 scores for reference
    out = {
        "holistic_scores": {str(i): float(c5_new[i]) for i in range(N)},
        "targeted_rescored_ids": TARGETED_IDS,
        "mae_c5_orig": mae_orig,
        "mae_c5_new": mae_new_all,
        "mae_cllm": mae_llm_all,
        "per_question_wins_orig": wins_old,
        "per_question_wins_new": wins_new,
    }
    out_path = os.path.join(DATA_DIR, "gemini_kg_dual_scores_rescored.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved updated scores → {out_path}")
    print(SEP)


if __name__ == "__main__":
    main()
