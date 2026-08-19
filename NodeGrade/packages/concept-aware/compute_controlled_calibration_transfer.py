#!/usr/bin/env python3
"""
compute_controlled_calibration_transfer.py -- properly controlled re-test
of compute_hierarchical_calibration.py, per the external GPT design
review's exact specification: matched calibration-set sizes across all
methods, both transfer directions (GPT->DeepSeek and DeepSeek->GPT), a
shrinkage-strength sweep instead of one hard-coded tau, and confidence
intervals rather than just mean MAE.

The original test gave the "prior" an unfair sample-size advantage (fit
on all 298 DeepSeek samples vs. a 10-50-sample local GPT fit), so its
"prior beats shrinkage" conclusion was confounded with "more data beats
less data," not isolating cross-backbone transferability. This script
fixes that: every method gets exactly n calibration examples.

Zero new API calls -- reuses cached verifier scores.

Run:
    python3 compute_controlled_calibration_transfer.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent
SEED = 42
N_OPTIONS = [10, 20, 30, 50]
TAU_GRID = [5, 10, 20, 50, 100]
N_REPS = 200


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
    A = np.column_stack([y_raw, np.ones_like(y_raw)])
    a, b = np.linalg.lstsq(A, y_true, rcond=None)[0]
    return float(a), float(b)


def apply_affine(y_raw: np.ndarray, coef: tuple[float, float]) -> np.ndarray:
    a, b = coef
    return np.clip(a * y_raw + b, 0.0, 5.0)


def mean_ci(values: list[float]) -> tuple[float, float, float]:
    arr = np.array(values)
    mean = arr.mean()
    se = arr.std(ddof=1) / np.sqrt(len(arr))
    return float(mean), float(mean - 1.96 * se), float(mean + 1.96 * se)


def run_direction(src_name: str, y_src_full: np.ndarray, r_src_full: np.ndarray,
                   tgt_name: str, y_tgt_full: np.ndarray, r_tgt_full: np.ndarray,
                   n: int, rng: np.random.Generator) -> dict:
    """Fit source calibration on exactly n source examples; fit target
    local calibration on exactly n (different, held-out-from-eval) target
    examples; evaluate everything on the REMAINING target examples."""
    results = {"none": [], "local": [], "prior": []}
    for tau in TAU_GRID:
        results[f"shrink_tau{tau}"] = []

    n_tgt_total = len(y_tgt_full)
    n_src_total = len(y_src_full)

    for rep in range(N_REPS):
        src_idx = rng.choice(n_src_total, size=n, replace=False)
        y_src, r_src = y_src_full[src_idx], r_src_full[src_idx]
        src_coef = fit_affine(y_src, r_src)

        tgt_perm = rng.permutation(n_tgt_total)
        local_idx = tgt_perm[:n]
        held_idx = tgt_perm[n:]
        y_local, r_local = y_tgt_full[local_idx], r_tgt_full[local_idx]
        y_held, r_held = y_tgt_full[held_idx], r_tgt_full[held_idx]

        results["none"].append(float(np.abs(y_held - r_held).mean()))

        local_coef = fit_affine(y_local, r_local)
        results["local"].append(float(np.abs(y_held - apply_affine(r_held, local_coef)).mean()))

        results["prior"].append(float(np.abs(y_held - apply_affine(r_held, src_coef)).mean()))

        for tau in TAU_GRID:
            w = n / (n + tau)
            shrink_coef = (w * local_coef[0] + (1 - w) * src_coef[0],
                           w * local_coef[1] + (1 - w) * src_coef[1])
            results[f"shrink_tau{tau}"].append(
                float(np.abs(y_held - apply_affine(r_held, shrink_coef)).mean()))

    return {"n": n, "direction": f"{src_name}->{tgt_name}", "n_reps": N_REPS,
            "metrics": {k: dict(zip(["mean", "ci_lo", "ci_hi"], mean_ci(v))) for k, v in results.items()}}


def main() -> int:
    human_gpt, verified_gpt = load_verifier_scores("gpt")
    human_ds, verified_ds = load_verifier_scores("deepseek")
    print(f"GPT: n={len(human_gpt)}  DeepSeek: n={len(human_ds)}")

    rng = np.random.default_rng(SEED)
    all_results = []
    for n in N_OPTIONS:
        for direction, (src, tgt) in [
            ("deepseek->gpt", (("deepseek", human_ds, verified_ds), ("gpt", human_gpt, verified_gpt))),
            ("gpt->deepseek", (("gpt", human_gpt, verified_gpt), ("deepseek", human_ds, verified_ds))),
        ]:
            src_name, y_src, r_src = src
            tgt_name, y_tgt, r_tgt = tgt
            row = run_direction(src_name, y_src, r_src, tgt_name, y_tgt, r_tgt, n, rng)
            all_results.append(row)

            print(f"\n{direction}  n={n}  ({N_REPS} reps)")
            m = row["metrics"]
            print(f"  no calibration:       {m['none']['mean']:.4f}  [{m['none']['ci_lo']:.4f}, {m['none']['ci_hi']:.4f}]")
            print(f"  local-only:           {m['local']['mean']:.4f}  [{m['local']['ci_lo']:.4f}, {m['local']['ci_hi']:.4f}]")
            print(f"  prior-only (transfer):{m['prior']['mean']:.4f}  [{m['prior']['ci_lo']:.4f}, {m['prior']['ci_hi']:.4f}]")
            best_tau, best_val = None, float("inf")
            for tau in TAU_GRID:
                v = m[f"shrink_tau{tau}"]["mean"]
                print(f"  shrinkage tau={tau:<4d}:      {v:.4f}  [{m[f'shrink_tau{tau}']['ci_lo']:.4f}, {m[f'shrink_tau{tau}']['ci_hi']:.4f}]")
                if v < best_val:
                    best_val, best_tau = v, tau
            print(f"  best shrinkage tau={best_tau} ({best_val:.4f})")
            overall_best = min(["none", "local", "prior"] + [f"shrink_tau{t}" for t in TAU_GRID],
                                key=lambda k: m[k]["mean"])
            print(f"  OVERALL BEST: {overall_best}")

    out_path = BASE / "data" / "controlled_calibration_transfer.json"
    out_path.write_text(json.dumps(all_results, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
