#!/usr/bin/env python3
"""
compute_hierarchical_calibration.py -- tests GPT's recommended hierarchical
/shrinkage calibration design against the simpler alternatives (no
calibration, local-only, global-only), rather than implementing it on
faith. Zero new API calls -- reuses cached verifier scores from the GPT
and DeepSeek pipeline runs.

Setup: simulates a "new deployment" by holding out a small calibration
set (n_local) from one backbone's data, fitting several calibration
strategies using only that small set (plus, for shrinkage, a "prior" fit
on the OTHER backbone's full data -- standing in for "what we already
know about how LLM verifiers are miscalibrated in general"), then
evaluating each strategy's held-out MAE on the REMAINDER of the first
backbone's data (never touched during fitting).

Strategies compared:
  - none:      no calibration, raw verifier score
  - local:     affine fit on the small local set alone
  - prior:     affine fit on the other backbone's full data, applied as-is
  - shrinkage: local and prior affine coefficients blended, weighted by
               n_local / (n_local + k) toward local as n_local grows
               (larger k = more conservative, trusts the prior longer)

Run:
    python3 compute_hierarchical_calibration.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent
SEED = 42
N_LOCAL_OPTIONS = [10, 20, 30, 50]
SHRINKAGE_K = 20  # at n_local=k, local and prior are weighted equally


def load_verifier_scores(tag: str) -> tuple[np.ndarray, np.ndarray]:
    d = json.loads((BASE / "data" / f"{tag}_pipeline_eval_results.json").read_text())
    human, verified = [], []
    for r in d["results"]:
        s = r.get(f"{tag}_c5_score")
        if s is None:
            continue
        human.append(r["human_score"])
        verified.append(s)
    return np.array(human), np.array(verified)


def fit_affine(y_true: np.ndarray, y_raw: np.ndarray) -> tuple[float, float]:
    """Least-squares y_true ~= a*y_raw + b."""
    A = np.column_stack([y_raw, np.ones_like(y_raw)])
    a, b = np.linalg.lstsq(A, y_true, rcond=None)[0]
    return float(a), float(b)


def apply_affine(y_raw: np.ndarray, coef: tuple[float, float]) -> np.ndarray:
    a, b = coef
    return np.clip(a * y_raw + b, 0.0, 5.0)


def main() -> int:
    human_gpt, verified_gpt = load_verifier_scores("gpt")
    human_ds, verified_ds = load_verifier_scores("deepseek")
    print(f"GPT: n={len(human_gpt)}  DeepSeek: n={len(human_ds)}")

    prior_coef_from_deepseek = fit_affine(human_ds, verified_ds)
    print(f"Prior (fit on all of DeepSeek's data): a={prior_coef_from_deepseek[0]:.4f}, b={prior_coef_from_deepseek[1]:.4f}")

    rng = np.random.default_rng(SEED)
    n_total = len(human_gpt)
    all_results = {}

    for n_local in N_LOCAL_OPTIONS:
        n_reps = 200
        mae_none, mae_local, mae_prior, mae_shrink = [], [], [], []
        for rep in range(n_reps):
            idx = rng.permutation(n_total)
            local_idx = idx[:n_local]
            held_idx = idx[n_local:]

            y_local, r_local = human_gpt[local_idx], verified_gpt[local_idx]
            y_held, r_held = human_gpt[held_idx], verified_gpt[held_idx]

            mae_none.append(float(np.abs(y_held - r_held).mean()))

            local_coef = fit_affine(y_local, r_local)
            mae_local.append(float(np.abs(y_held - apply_affine(r_held, local_coef)).mean()))

            mae_prior.append(float(np.abs(y_held - apply_affine(r_held, prior_coef_from_deepseek)).mean()))

            w = n_local / (n_local + SHRINKAGE_K)
            shrink_coef = (w * local_coef[0] + (1 - w) * prior_coef_from_deepseek[0],
                           w * local_coef[1] + (1 - w) * prior_coef_from_deepseek[1])
            mae_shrink.append(float(np.abs(y_held - apply_affine(r_held, shrink_coef)).mean()))

        row = {
            "n_local": n_local,
            "none": float(np.mean(mae_none)),
            "local_only": float(np.mean(mae_local)),
            "prior_only_crossbackbone": float(np.mean(mae_prior)),
            "shrinkage": float(np.mean(mae_shrink)),
        }
        all_results[n_local] = row
        print(f"\nn_local={n_local} (avg over {n_reps} random splits, held-out n~{n_total-n_local}):")
        print(f"  no calibration:              {row['none']:.4f}")
        print(f"  local-only affine:           {row['local_only']:.4f}")
        print(f"  cross-backbone prior only:   {row['prior_only_crossbackbone']:.4f}")
        print(f"  shrinkage (local+prior):     {row['shrinkage']:.4f}")
        best = min(row, key=lambda k: row[k] if k != "n_local" else float("inf"))
        print(f"  best: {best}")

    out_path = BASE / "data" / "hierarchical_calibration_test.json"
    out_path.write_text(json.dumps({"prior_coef_from_deepseek": prior_coef_from_deepseek,
                                     "shrinkage_k": SHRINKAGE_K, "results": all_results}, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
