#!/usr/bin/env python3
"""
Validate stored *eval_results.json files.

- Recomputes MAE, RMSE, r, rho, QWK, bias, P@0.5 from results[] and compares to metrics.
- Recomputes Wilcoxon p (paired |C5−human| vs |C_LLM−human|).
- Recomputes MAE reduction %.
- Optionally checks human_score and ids against *_dataset.json.
- Optionally checks split batch_responses JSONs cover the same IDs as results[].

Usage:
  python3 validate_stored_eval.py
  python3 validate_stored_eval.py --dataset kaggle_asag
  python3 validate_stored_eval.py --check-batches
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from scipy.stats import wilcoxon

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUP_DIR = os.path.join(DATA_DIR, "batch_responses")

sys.path.insert(0, BASE_DIR)
from score_batch_results import compute_metrics  # noqa: E402


def _close(a: float, b: float, rtol: float = 1e-5, atol: float = 1e-5) -> bool:
    return bool(np.isclose(a, b, rtol=rtol, atol=atol))


def _p_close(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) < 1e-5 or _close(a, b, rtol=1e-3, atol=1e-6)


def validate_eval_json(path: str, dataset_key: str) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    with open(path) as f:
        d = json.load(f)

    results = d.get("results")
    if not results:
        return ([f"{path}: missing or empty results[]"], [])

    n_stored = d.get("n", len(results))
    n_miss = d.get("n_missing", 0)
    if n_stored != len(results):
        errors.append(
            f"{dataset_key}: top-level n={n_stored} but len(results)={len(results)}"
        )

    h = np.array([float(r["human_score"]) for r in results])
    cllm = np.array([float(r["cllm_score"]) for r in results])
    c5 = np.array([float(r["c5_score"]) for r in results])

    m_cllm = compute_metrics(h, cllm)
    m_c5 = compute_metrics(h, c5)

    for label, stored, comp in (
        ("C_LLM", d["metrics"]["C_LLM"], m_cllm),
        ("C5_fix", d["metrics"]["C5_fix"], m_c5),
    ):
        for k in ("mae", "rmse", "r", "rho", "qwk", "bias", "prec"):
            sv, cv = float(stored[k]), float(comp[k])
            if not _close(sv, cv):
                errors.append(
                    f"{dataset_key} {label}.{k}: stored={sv:.10g} recomputed={cv:.10g}"
                )

    try:
        _, p_rec = wilcoxon(np.abs(c5 - h), np.abs(cllm - h))
        p_rec = float(p_rec)
    except Exception as e:
        warnings.append(f"{dataset_key}: Wilcoxon recompute skipped ({e})")
        p_rec = None

    if p_rec is not None:
        p_stored = float(d.get("wilcoxon_p", 0.0))
        if not _p_close(p_stored, p_rec):
            errors.append(
                f"{dataset_key} wilcoxon_p: stored={p_stored:.10g} recomputed={p_rec:.10g}"
            )

    mae_red_stored = float(d.get("mae_reduction_pct", 0.0))
    mae_red = (m_cllm["mae"] - m_c5["mae"]) / m_cllm["mae"] * 100.0
    if not _close(mae_red_stored, mae_red, rtol=1e-4, atol=1e-4):
        errors.append(
            f"{dataset_key} mae_reduction_pct: stored={mae_red_stored:.6g} "
            f"recomputed={mae_red:.6g}"
        )

    # IDs monotonic / unique
    ids = [r["id"] for r in results]
    if len(ids) != len(set(ids)):
        errors.append(f"{dataset_key}: duplicate sample ids in results[]")

    ds_path = os.path.join(DATA_DIR, f"{dataset_key}_dataset.json")
    if os.path.isfile(ds_path):
        with open(ds_path) as f:
            records = json.load(f)
        by_id = {int(r["id"]): r for r in records}
        for row in results:
            sid = int(row["id"])
            if sid not in by_id:
                errors.append(f"{dataset_key}: result id={sid} not in dataset")
                continue
            hg = float(by_id[sid]["human_score"])
            hr = float(row["human_score"])
            if not _close(hg, hr):
                errors.append(
                    f"{dataset_key}: id={sid} human_score dataset={hg} eval={hr}"
                )
        if n_miss == 0 and len(results) != len(records):
            warnings.append(
                f"{dataset_key}: n_missing=0 but len(results)={len(results)} "
                f"!= len(dataset)={len(records)}"
            )

    return errors, warnings


def validate_batch_responses(dataset_key: str, result_ids: set[int]) -> list[str]:
    errors: list[str] = []
    import glob

    cllm = sorted(glob.glob(os.path.join(BACKUP_DIR, f"{dataset_key}_cllm_batch_*_response.json")))
    c5 = sorted(glob.glob(os.path.join(BACKUP_DIR, f"{dataset_key}_c5fix_batch_*_response.json")))
    if not cllm or not c5:
        return [
            f"{dataset_key}: missing split batch files under data/batch_responses/ "
            f"(cllm={len(cllm)} c5fix={len(c5)})"
        ]

    def load_ids(paths: list[str]) -> set[int]:
        out: set[int] = set()
        for p in paths:
            with open(p) as f:
                raw = json.load(f)
            for k in raw.get("scores", {}):
                out.add(int(k))
        return out

    cllm_ids = load_ids(cllm)
    c5_ids = load_ids(c5)
    if cllm_ids != c5_ids:
        only_l = cllm_ids - c5_ids
        only_5 = c5_ids - cllm_ids
        errors.append(
            f"{dataset_key}: C_LLM vs C5_fix batch ID mismatch "
            f"(only cllm={len(only_l)} only c5={len(only_5)})"
        )
    if cllm_ids != result_ids:
        missing = result_ids - cllm_ids
        extra = cllm_ids - result_ids
        if missing or extra:
            errors.append(
                f"{dataset_key}: batch IDs vs eval results: "
                f"missing_in_batches={len(missing)} extra_in_batches={len(extra)}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate stored eval_results JSON")
    parser.add_argument(
        "--dataset",
        choices=["kaggle_asag", "digiklausur", "all"],
        default="all",
    )
    parser.add_argument(
        "--check-batches",
        action="store_true",
        help="Also verify data/batch_responses split files align with eval results",
    )
    args = parser.parse_args()

    datasets = (
        ["kaggle_asag", "digiklausur"]
        if args.dataset == "all"
        else [args.dataset]
    )

    all_errors: list[str] = []
    all_warnings: list[str] = []

    for key in datasets:
        path = os.path.join(DATA_DIR, f"{key}_eval_results.json")
        if not os.path.isfile(path):
            all_warnings.append(f"Skip {key}: no file {path}")
            continue
        err, warn = validate_eval_json(path, key)
        all_errors.extend(err)
        all_warnings.extend(warn)

        if args.check_batches:
            with open(path) as f:
                d = json.load(f)
            ids = {int(r["id"]) for r in d.get("results", [])}
            all_errors.extend(validate_batch_responses(key, ids))

    for w in all_warnings:
        print(f"WARNING: {w}")
    if all_errors:
        print("VALIDATION FAILED")
        for e in all_errors:
            print(f"  {e}")
        return 1

    print("VALIDATION OK — stored metrics match recomputation from results[]")
    for key in datasets:
        p = os.path.join(DATA_DIR, f"{key}_eval_results.json")
        if os.path.isfile(p):
            print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
