"""
Score CoT baseline results and compare with C5_fix and C_LLM.

Expects: /tmp/cot_baseline_response.json
  {"scores": {"0": {"holistic_score": X.X, ...}, ...}}
  OR {"scores": {"0": X.X, ...}}

Usage:
    python3 score_cot_baseline.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr, wilcoxon
from sklearn.metrics import cohen_kappa_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

CHECKPOINT = os.path.join(DATA_DIR, "ablation_checkpoint_gemini_flash_latest.json")
DUAL_SCORES = os.path.join(DATA_DIR, "gemini_kg_dual_scores.json")
RESPONSE_PATH = "/tmp/cot_baseline_response.json"
N = 120
SEP = "─" * 78


def load_response(path):
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


def metrics(h, pred, label, baseline=None):
    r, _ = pearsonr(h, pred)
    rho, _ = spearmanr(h, pred)
    mae = float(np.mean(np.abs(h - pred)))
    rmse = float(np.sqrt(np.mean((h - pred) ** 2)))
    bias = float(np.mean(pred - h))
    prec = float(np.mean(np.abs(h - pred) <= 0.5))
    hi = np.round(h * 4).astype(int)
    pi = np.round(pred * 4).astype(int)
    qwk = float(cohen_kappa_score(hi, pi, weights="quadratic"))
    p_str = "—"
    if baseline is not None:
        try:
            _, p = wilcoxon(np.abs(pred - h), np.abs(baseline - h))
            p_str = f"{p:.4f}"
        except Exception:
            pass
    print(f"  {label:42} MAE={mae:.4f}  r={r:.4f}  rho={rho:.4f}  QWK={qwk:.4f}  bias={bias:+.4f}  p={p_str}")
    return dict(mae=mae, rmse=rmse, r=r, rho=rho, qwk=qwk, bias=bias, prec=prec)


def main():
    print(SEP)
    print("CoT Baseline Scoring vs C5_fix and C_LLM")
    print(SEP)

    if not os.path.exists(RESPONSE_PATH):
        print(f"ERROR: {RESPONSE_PATH} not found.")
        print("Send /tmp/cot_baseline_prompt.txt to Gemini, save response, then re-run.")
        sys.exit(1)

    with open(CHECKPOINT) as f:
        ckpt = json.load(f)
    with open(DUAL_SCORES) as f:
        dual = json.load(f)

    h = np.array(ckpt["human_scores"])
    cllm = np.array(ckpt["scores"]["C_LLM"])
    c5 = np.array([dual["holistic_scores"][str(i)] for i in range(N)])

    cot_raw = load_response(RESPONSE_PATH)
    if len(cot_raw) != N:
        print(f"WARNING: Expected {N} scores, got {len(cot_raw)}")
    cot = np.array([cot_raw.get(i, 0.0) for i in range(N)])

    print()
    m_cllm = metrics(h, cllm, "C_LLM (answer only, no KG)", None)
    m_cot = metrics(h, cot,  "CoT (step-by-step, no KG)",  cllm)
    m_c5 = metrics(h, c5,   "C5_fix / ConceptGrade (full KG)", cllm)

    print()
    print("KEY COMPARISON:")
    if m_c5["mae"] < m_cot["mae"]:
        delta = m_cot["mae"] - m_c5["mae"]
        print(f"  ✓ ConceptGrade BEATS CoT: ΔMAE = {delta:+.4f} ({delta/m_cot['mae']*100:.1f}% reduction)")
        print(f"    → The KG provides evidence BEYOND what step-by-step prompting achieves")
        print(f"    → Validates that the structured KG is the key driver, not CoT reasoning")
    else:
        delta = m_c5["mae"] - m_cot["mae"]
        print(f"  ✗ CoT matches or beats ConceptGrade: ΔMAE = {delta:+.4f}")
        print(f"    → KG may not add beyond CoT prompting — investigate which samples differ")
        # Find where they differ most
        diff = np.abs(cot - h) - np.abs(c5 - h)  # positive = CoT worse on that sample
        top_c5_wins = np.argsort(diff)[::-1][:5]
        print(f"    → Top 5 samples where C5 beats CoT:")
        for sid in top_c5_wins:
            print(f"       ID {sid}: human={h[sid]:.2f}, CoT={cot[sid]:.2f}, C5={c5[sid]:.2f}")

    # Per-question breakdown
    print()
    print("Per-question MAE:")
    q_labels = ["Linked List","Array vs LL","Stack","BST","BFS/DFS",
                "Hash Table","Recursion","Quicksort","Dyn.Prog.","Big-O"]
    cot_wins = c5_wins = 0
    for qi in range(10):
        ids = list(range(qi * 12, (qi + 1) * 12))
        mae_cllm = float(np.mean(np.abs(cllm[ids] - h[ids])))
        mae_cot = float(np.mean(np.abs(cot[ids] - h[ids])))
        mae_c5 = float(np.mean(np.abs(c5[ids] - h[ids])))
        best = min(mae_cllm, mae_cot, mae_c5)
        w_cot = "✓" if mae_cot == best else " "
        w_c5 = "✓" if mae_c5 == best else " "
        if mae_c5 < mae_cot: c5_wins += 1
        if mae_cot < mae_c5: cot_wins += 1
        print(f"  Q{qi+1:2} {q_labels[qi]:15}: LLM={mae_cllm:.3f}  CoT={mae_cot:.3f}{w_cot}  C5={mae_c5:.3f}{w_c5}")
    print(f"  C5_fix beats CoT: {c5_wins}/10 questions")
    print(f"  CoT beats C5_fix: {cot_wins}/10 questions")

    # Save CoT scores to data/
    out = {"scores": {str(i): float(cot[i]) for i in range(N)},
           "metrics": m_cot}
    out_path = os.path.join(DATA_DIR, "cot_baseline_scores.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nCoT scores saved → {out_path}")
    print(SEP)


if __name__ == "__main__":
    main()
