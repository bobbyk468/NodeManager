#!/usr/bin/env python3
"""
Validation suite: Weight ablation + Kaggle ASAG re-run.

This script:
1. Tests different weight blends (50/50, 100% KG, 100% LLM) on Mohler
2. Re-runs Kaggle ASAG with cache clear to get fresh metrics
3. Generates comparison report
"""

import json
import os
import numpy as np
from scipy.stats import wilcoxon, pearsonr, spearmanr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def compute_metrics(h, pred):
    """Compute evaluation metrics."""
    r, _ = pearsonr(h, pred)
    rho, _ = spearmanr(h, pred)
    mae = float(np.mean(np.abs(h - pred)))
    rmse = float(np.sqrt(np.mean((h - pred) ** 2)))
    bias = float(np.mean(pred - h))
    return {"mae": mae, "rmse": rmse, "r": r, "rho": rho, "bias": bias}

def wilcoxon_p(h, pred, baseline):
    """Wilcoxon signed-rank test."""
    try:
        _, p = wilcoxon(np.abs(pred - h), np.abs(baseline - h))
        return float(p)
    except:
        return 1.0

def main():
    print("=" * 80)
    print("VALIDATION SUITE: Weight Ablation + Kaggle ASAG Re-run")
    print("=" * 80)
    print()

    # Load baseline Mohler data
    print("Loading baseline Mohler evaluation...")
    with open(os.path.join(DATA_DIR, "offline_eval_results.json")) as f:
        offline = json.load(f)
    
    h = np.array(offline["scores"]["human"])
    cllm = np.array(offline["scores"]["C_LLM"])
    c5_baseline = np.array(offline["scores"]["C5_fix"])
    
    print(f"  Loaded n={len(h)} Mohler samples")
    print()

    # Show current baseline
    print("BASELINE (5% KG, 95% LLM):")
    m_baseline = compute_metrics(h, c5_baseline)
    m_cllm = compute_metrics(h, cllm)
    p_baseline = wilcoxon_p(h, c5_baseline, cllm)
    mae_red = (m_cllm['mae'] - m_baseline['mae']) / m_cllm['mae'] * 100
    
    print(f"  C_LLM MAE:        {m_cllm['mae']:.4f}")
    print(f"  C5_fix MAE:       {m_baseline['mae']:.4f}")
    print(f"  MAE reduction:    {mae_red:.1f}%")
    print(f"  Wilcoxon p:       {p_baseline:.4f} (significance: {'YES ✓' if p_baseline < 0.05 else 'NO ✗'})")
    print()

    # Show Kaggle ASAG current state
    print("KAGGLE ASAG CURRENT STATE:")
    try:
        with open(os.path.join(DATA_DIR, "kaggle_asag_eval_results.json")) as f:
            ka = json.load(f)
        mc = ka["metrics"]["C_LLM"]
        m5 = ka["metrics"]["C5_fix"]
        ka_p = ka.get("wilcoxon_p", 1.0)
        ka_red = ka.get("mae_reduction_pct", 0)
        
        print(f"  n = {ka['n']}")
        print(f"  C_LLM MAE:        {mc['mae']:.4f}")
        print(f"  C5_fix MAE:       {m5['mae']:.4f}")
        print(f"  MAE reduction:    {ka_red:.1f}%")
        print(f"  Wilcoxon p:       {ka_p:.4f} (significance: {'YES ✓' if ka_p < 0.05 else 'NO ✗'})")
    except FileNotFoundError:
        print("  ⚠️  Kaggle ASAG eval results not found yet")
    print()

    # Instructions for ablation
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print()
    print("1. WEIGHT ABLATION (test different KG/LLM blends):")
    print("   Commands to run:")
    print("   ")
    print("   # 50/50 blend")
    print("   python3 run_evaluation.py --kg-weight 0.50 --holistic-weight 0.50")
    print("   ")
    print("   # 100% KG (no LLM)")
    print("   python3 run_evaluation.py --kg-weight 1.0 --holistic-weight 0.0")
    print("   ")
    print("   # 100% LLM (control, no KG)")
    print("   python3 run_evaluation.py --kg-weight 0.0 --holistic-weight 1.0")
    print()
    print("2. KAGGLE ASAG RE-RUN (fresh data with cache clear):")
    print("   ")
    print("   python3 run_full_pipeline.py --dataset kaggle_asag --clear-cache --force")
    print()
    print("3. RE-GENERATE PAPER REPORT:")
    print("   ")
    print("   python3 generate_paper_report_v2.py")
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
