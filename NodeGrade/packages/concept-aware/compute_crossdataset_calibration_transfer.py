#!/usr/bin/env python3
"""
compute_crossdataset_calibration_transfer.py -- tests the calibration
question GPT's review actually raised (does calibration transfer across
DATASET/domain/rubric shift, not just across backbone), complementing
compute_hierarchical_calibration.py's cross-backbone-same-dataset test.

Uses Gemini's already-cached C5_fix scores on all three datasets this
paper evaluates on (Mohler n=1262, DigiKlausur n=646, Kaggle ASAG n=368)
-- one backbone held fixed, dataset varied. Zero new API calls.

For each (source, target) dataset pair: fit an affine calibration on the
FULL source dataset, apply it unmodified to the target dataset, and
compare against (a) no calibration and (b) an affine fit directly on the
target (the best-case in-domain ceiling, for reference only -- not a
fair deployment scenario since it uses target labels).

Run:
    python3 compute_crossdataset_calibration_transfer.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent


def fit_affine(y_true: np.ndarray, y_raw: np.ndarray) -> tuple[float, float]:
    A = np.column_stack([y_raw, np.ones_like(y_raw)])
    a, b = np.linalg.lstsq(A, y_true, rcond=None)[0]
    return float(a), float(b)


def apply_affine(y_raw: np.ndarray, coef: tuple[float, float]) -> np.ndarray:
    a, b = coef
    return np.clip(a * y_raw + b, 0.0, 5.0)


def load_mohler():
    d = json.loads((BASE / "data" / "mohler_real_eval_results.json").read_text())
    r = d["results"]
    return np.array([x["human_score"] for x in r]), np.array([x["c5_score"] for x in r])


def load_digiklausur():
    d = json.loads((BASE / "data" / "digiklausur_c5fix_selfconsistency_results.json").read_text())
    r = d["per_sample"]
    return np.array([x["human_score"] for x in r]), np.array([x["c5_fix_single"] for x in r])


def load_kaggle():
    d = json.loads((BASE / "data" / "kaggle_c5fix_selfconsistency_results.json").read_text())
    r = d["per_sample"]
    return np.array([x["human_score"] for x in r]), np.array([x["c5_fix_single"] for x in r])


def main() -> int:
    datasets = {
        "mohler": load_mohler(),
        "digiklausur": load_digiklausur(),
        "kaggle": load_kaggle(),
    }
    for name, (y, r) in datasets.items():
        print(f"{name}: n={len(y)}  raw MAE={np.abs(y-r).mean():.4f}  "
              f"human range=[{y.min():.1f},{y.max():.1f}]  score range=[{r.min():.1f},{r.max():.1f}]")

    print("\n=== Cross-dataset calibration transfer (Gemini C5_fix backbone, fixed) ===")
    results = {}
    for src_name, (y_src, r_src) in datasets.items():
        coef = fit_affine(y_src, r_src)
        for tgt_name, (y_tgt, r_tgt) in datasets.items():
            if src_name == tgt_name:
                continue
            mae_none = float(np.abs(y_tgt - r_tgt).mean())
            mae_transferred = float(np.abs(y_tgt - apply_affine(r_tgt, coef)).mean())
            tgt_coef = fit_affine(y_tgt, r_tgt)
            mae_indomain_ceiling = float(np.abs(y_tgt - apply_affine(r_tgt, tgt_coef)).mean())
            pct = (mae_none - mae_transferred) / mae_none * 100
            key = f"{src_name}->{tgt_name}"
            results[key] = {"mae_none": mae_none, "mae_transferred": mae_transferred,
                             "mae_indomain_ceiling": mae_indomain_ceiling, "pct_vs_none": pct}
            flag = "HELPS" if mae_transferred < mae_none else "HURTS"
            print(f"  {key:28s} none={mae_none:.4f}  transferred={mae_transferred:.4f} "
                  f"({pct:+.1f}%) [{flag}]  in-domain ceiling={mae_indomain_ceiling:.4f}")

    out_path = BASE / "data" / "crossdataset_calibration_transfer.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
