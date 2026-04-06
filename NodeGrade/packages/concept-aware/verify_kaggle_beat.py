#!/usr/bin/env python3
"""Exit 0 if Kaggle ASAG C5_fix beats C_LLM with Wilcoxon p < 0.05; else exit 1."""

from __future__ import annotations

import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "data", "kaggle_asag_eval_results.json")


def main() -> int:
    if not os.path.isfile(PATH):
        print(f"Missing {PATH} — run score_batch_results.py --dataset kaggle_asag")
        return 2
    with open(PATH) as f:
        d = json.load(f)
    mc = d["metrics"]["C_LLM"]["mae"]
    m5 = d["metrics"]["C5_fix"]["mae"]
    p = float(d.get("wilcoxon_p", 1.0))
    win = m5 < mc and p < 0.05
    print(f"Kaggle ASAG: C_LLM MAE={mc:.4f}  C5_fix MAE={m5:.4f}  Wilcoxon p={p:.4f}")
    if win:
        print("Result: ConceptGrade beats C_LLM (MAE + p<0.05).")
        return 0
    if m5 < mc:
        print("Result: lower MAE but not significant at 0.05 — collect power or tune matching.")
        return 1
    print("Result: C_LLM MAE not exceeded.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
