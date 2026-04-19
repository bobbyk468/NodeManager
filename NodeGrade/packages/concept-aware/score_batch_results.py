"""
Score batch results for new datasets (DigiKlausur, Kaggle ASAG).

Reads all /tmp/batch_scoring/{dataset}_batch_XX_response.json files,
merges them, and computes full metrics comparing C_LLM vs C5_fix.

Usage:
    python3 score_batch_results.py --dataset digiklausur
    python3 score_batch_results.py --dataset kaggle_asag
    python3 score_batch_results.py --dataset all

Expects response files:
    /tmp/batch_scoring/{dataset}_batch_01_response.json
    /tmp/batch_scoring/{dataset}_batch_02_response.json
    ...

Response format (Gemini output):
    {"scores": {"<id>": {"cllm_score": X.X, "c5fix_score": X.X}, ...}}

Outputs:
    data/{dataset}_eval_results.json   — full results
    data/{dataset}_metrics_summary.txt — human-readable metrics
"""

from __future__ import annotations

import argparse
import json
import os
import glob

import numpy as np
from scipy.stats import pearsonr, spearmanr, wilcoxon
from sklearn.metrics import cohen_kappa_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BATCH_DIR = os.environ.get('CONCEPTGRADE_BATCH_DIR', os.path.join(BASE_DIR, 'data', 'tmp'))
BACKUP_DIR = os.path.join(DATA_DIR, "batch_responses")  # persistent fallback
SEP = "=" * 70


def _find_responses(pattern: str) -> list[str]:
    """Find response files in BATCH_DIR, falling back to BACKUP_DIR."""
    files = sorted(glob.glob(pattern))
    if not files:
        # Try persistent backup dir
        backup_pattern = pattern.replace(BATCH_DIR, BACKUP_DIR)
        files = sorted(glob.glob(backup_pattern))
    return files


def load_responses(dataset: str) -> dict[int, dict]:
    """Merge all batch response files into a single dict keyed by sample ID.

    Supports two modes:
    - Split mode: separate *_cllm_batch_*_response.json and *_c5fix_batch_*_response.json
    - Dual mode (legacy): combined *_batch_*_response.json with {cllm_score, c5fix_score}
    """
    # Try split mode first (separate cllm and c5fix responses)
    cllm_pattern = os.path.join(BATCH_DIR, f"{dataset}_cllm_batch_*_response.json")
    c5fix_pattern = os.path.join(BATCH_DIR, f"{dataset}_c5fix_batch_*_response.json")
    cllm_files = _find_responses(cllm_pattern)
    c5fix_files = _find_responses(c5fix_pattern)

    if cllm_files and c5fix_files:
        # Split mode: load each system's scores separately
        cllm_scores: dict[int, float] = {}
        for f_path in cllm_files:
            with open(f_path) as f:
                raw = json.load(f)
            for k, v in raw.get("scores", {}).items():
                sid = int(k)
                cllm_scores[sid] = float(v) if not isinstance(v, dict) else float(v.get("score", 0.0))

        c5fix_scores: dict[int, float] = {}
        for f_path in c5fix_files:
            with open(f_path) as f:
                raw = json.load(f)
            for k, v in raw.get("scores", {}).items():
                sid = int(k)
                c5fix_scores[sid] = float(v) if not isinstance(v, dict) else float(v.get("score", 0.0))

        if set(c5fix_scores) != set(cllm_scores):
            raise ValueError(
                "Incomplete split-mode merge: C_LLM and C5_fix must cover the same sample IDs. "
                f"Got {len(cllm_scores)} C_LLM vs {len(c5fix_scores)} C5_fix scores. "
                "Restore batch JSONs from data/batch_responses/ or re-run scoring with a valid API key."
            )

        merged = {}
        for sid in cllm_scores:
            merged[sid] = {
                "cllm": cllm_scores[sid],
                "c5fix": c5fix_scores[sid],
            }

        print(f"Split mode: {len(cllm_scores)} C_LLM + {len(c5fix_scores)} C5_fix scores "
              f"from {len(cllm_files)+len(c5fix_files)} files")
        return merged

    # Fall back to dual mode (legacy)
    pattern = os.path.join(BATCH_DIR, f"{dataset}_batch_*_response.json")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"No response files found. Run:\n"
            f"  python3 run_full_pipeline.py --dataset {dataset}"
        )

    merged = {}
    for f_path in files:
        with open(f_path) as f:
            raw = json.load(f)
        scores = raw.get("scores", raw)
        for k, v in scores.items():
            sid = int(k)
            if isinstance(v, dict):
                merged[sid] = {
                    "cllm": float(v.get("cllm_score", v.get("cllm", 0.0))),
                    "c5fix": float(v.get("c5fix_score", v.get("c5fix", 0.0))),
                }
            else:
                merged[sid] = {"cllm": float(v), "c5fix": float(v)}

    print(f"Dual mode: loaded {len(merged)} scores from {len(files)} files")
    return merged


DIGIKLAUSUR_SCORE_LEVELS = np.array([0.0, 2.5, 5.0], dtype=np.float64)


def snap_to_discrete_levels(pred: np.ndarray, levels: np.ndarray) -> np.ndarray:
    """Snap each prediction to the nearest allowed level (e.g. DigiKlausur rubric)."""
    if levels.size == 0:
        return pred
    idx = np.argmin(np.abs(pred[:, np.newaxis] - levels[np.newaxis, :]), axis=1)
    return levels[idx].astype(np.float64)


def compute_metrics(h: np.ndarray, pred: np.ndarray) -> dict:
    r, _ = pearsonr(h, pred)
    rho, _ = spearmanr(h, pred)
    mae = float(np.mean(np.abs(h - pred)))
    rmse = float(np.sqrt(np.mean((h - pred) ** 2)))
    bias = float(np.mean(pred - h))
    prec = float(np.mean(np.abs(h - pred) <= 0.5))
    hi = np.round(h * 4).astype(int)
    pi = np.round(pred * 4).astype(int)
    qwk = float(cohen_kappa_score(hi, pi, weights="quadratic"))
    return dict(mae=mae, rmse=rmse, r=r, rho=rho, qwk=qwk, bias=bias, prec=prec)


def run(dataset: str, snap_digi: bool | None = None) -> None:
    data_path = os.path.join(DATA_DIR, f"{dataset}_dataset.json")
    feat_path = os.path.join(BATCH_DIR, f"{dataset}_precomputed.json")
    feat_data = os.path.join(DATA_DIR, f"{dataset}_precomputed.json")

    with open(data_path) as f:
        records = json.load(f)

    if os.path.exists(feat_path):
        with open(feat_path) as f:
            features = json.load(f)
    elif os.path.exists(feat_data):
        with open(feat_data) as f:
            features = json.load(f)
    else:
        features = {}

    # Load Gemini responses
    scores = load_responses(dataset)

    # Match records to scores
    results = []
    missing = []
    for r in records:
        sid = r["id"]
        if sid not in scores:
            missing.append(sid)
            continue
        feat = features.get(str(sid), {})
        results.append({
            "id": sid,
            "human_score": r["human_score"],
            "cllm_score": scores[sid]["cllm"],
            "c5_score": scores[sid]["c5fix"],
            "matched_concepts": feat.get("matched_concepts", []),
            "chain_pct": feat.get("chain_pct", "0%"),
            "solo": feat.get("solo", "Prestructural"),
            "bloom": feat.get("bloom", "Remember"),
        })

    if missing:
        print(f"WARNING: {len(missing)} samples missing from responses: {missing[:10]}...")

    print(f"Scoring {len(results)} samples")

    h = np.array([r["human_score"] for r in results])
    cllm = np.array([r["cllm_score"] for r in results])
    c5 = np.array([r["c5_score"] for r in results])

    # Always compute raw (continuous) metrics first
    m_cllm = compute_metrics(h, cllm)
    m_c5 = compute_metrics(h, c5)

    try:
        _, p_wil = wilcoxon(np.abs(c5 - h), np.abs(cllm - h))
    except Exception:
        p_wil = 1.0

    def _print_metrics_block(label: str, mc: dict, m5: dict, p: float) -> None:
        mae_red = (mc['mae'] - m5['mae']) / mc['mae'] * 100
        print(f"\n  {label}")
        print(f"  {'System':40} {'MAE':7} {'r':7} {'rho':7} {'QWK':7} {'Bias':7} {'P@0.5':6}")
        print("  " + "-" * 70)
        print(f"  {'C_LLM (no KG)':40} {mc['mae']:.4f}  {mc['r']:.4f}  {mc['rho']:.4f}  {mc['qwk']:.4f}  {mc['bias']:+.4f}  {mc['prec']:.3f}")
        print(f"  {'C5_fix / ConceptGrade (full KG)':40} {m5['mae']:.4f}  {m5['r']:.4f}  {m5['rho']:.4f}  {m5['qwk']:.4f}  {m5['bias']:+.4f}  {m5['prec']:.3f}")
        print(f"  Wilcoxon p (paired |err|, two-sided): {p:.4f}")
        print(f"  MAE reduction: {mae_red:.1f}%")
        sig = p < 0.05
        if m5['mae'] < mc['mae'] and sig:
            print(f"  ✓ ConceptGrade BEATS C_LLM")
        elif m5['mae'] < mc['mae']:
            print(f"  ▲ Lower MAE for C5_fix; significance borderline")
        else:
            print(f"  ✗ C_LLM better on this dataset")

    print()
    print(SEP)
    print(f"RESULTS — {dataset.upper()} (n={len(results)})")
    print(SEP)
    _print_metrics_block("Continuous scores (primary):", m_cllm, m_c5, p_wil)

    mae_reduction = (m_cllm['mae'] - m_c5['mae']) / m_cllm['mae'] * 100

    # For DigiKlausur: always also report snapped metrics (rubric-aligned comparison)
    m_cllm_snap = m_c5_snap = p_wil_snap = mae_reduction_snap = None
    if dataset == "digiklausur":
        cllm_s = snap_to_discrete_levels(cllm, DIGIKLAUSUR_SCORE_LEVELS)
        c5_s = snap_to_discrete_levels(c5, DIGIKLAUSUR_SCORE_LEVELS)
        m_cllm_snap = compute_metrics(h, cllm_s)
        m_c5_snap = compute_metrics(h, c5_s)
        try:
            _, p_wil_snap = wilcoxon(np.abs(c5_s - h), np.abs(cllm_s - h))
        except Exception:
            p_wil_snap = 1.0
        mae_reduction_snap = (m_cllm_snap['mae'] - m_c5_snap['mae']) / m_cllm_snap['mae'] * 100
        levels_str = [float(v) for v in DIGIKLAUSUR_SCORE_LEVELS]
        _print_metrics_block(
            f"Snapped to rubric levels {levels_str} (sensitivity analysis):",
            m_cllm_snap, m_c5_snap, p_wil_snap,
        )

    # If --snap-digi was passed, also overwrite results rows with snapped values
    do_snap = bool(snap_digi) and dataset == "digiklausur"
    if do_snap:
        cllm_s = snap_to_discrete_levels(cllm, DIGIKLAUSUR_SCORE_LEVELS)
        c5_s = snap_to_discrete_levels(c5, DIGIKLAUSUR_SCORE_LEVELS)
        for i, r in enumerate(results):
            r["cllm_score"] = float(cllm_s[i])
            r["c5_score"] = float(c5_s[i])
        print(f"\n  NOTE: --snap-digi set; saved results rows use snapped scores.")

    # Save
    out = {
        "dataset": dataset,
        "n": len(results),
        "n_missing": len(missing),
        "metrics": {"C_LLM": m_cllm, "C5_fix": m_c5},
        "wilcoxon_p": float(p_wil),
        "mae_reduction_pct": float(mae_reduction),
        "results": results,
        "missing_ids": missing,
        "snap_discrete_levels": list(DIGIKLAUSUR_SCORE_LEVELS) if do_snap else None,
        **({"metrics_snapped": {"C_LLM": m_cllm_snap, "C5_fix": m_c5_snap,
                                "wilcoxon_p": float(p_wil_snap),
                                "mae_reduction_pct": float(mae_reduction_snap)}}
           if m_cllm_snap is not None else {}),
    }
    out_path = os.path.join(DATA_DIR, f"{dataset}_eval_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    # Text summary
    summary = [
        SEP,
        f"ConceptGrade Evaluation — {dataset.upper()}",
        f"n={len(results)} samples",
        SEP,
        "  Continuous scores (primary):",
        f"    C_LLM:   MAE={m_cllm['mae']:.4f}  r={m_cllm['r']:.4f}  QWK={m_cllm['qwk']:.4f}  bias={m_cllm['bias']:+.4f}",
        f"    C5_fix:  MAE={m_c5['mae']:.4f}  r={m_c5['r']:.4f}  QWK={m_c5['qwk']:.4f}  bias={m_c5['bias']:+.4f}",
        f"    MAE reduction: {mae_reduction:.1f}%  Wilcoxon p={p_wil:.4f}",
    ]
    if m_cllm_snap is not None:
        summary += [
            f"  Snapped to {[float(v) for v in DIGIKLAUSUR_SCORE_LEVELS]} (sensitivity):",
            f"    C_LLM:   MAE={m_cllm_snap['mae']:.4f}  r={m_cllm_snap['r']:.4f}  QWK={m_cllm_snap['qwk']:.4f}  bias={m_cllm_snap['bias']:+.4f}",
            f"    C5_fix:  MAE={m_c5_snap['mae']:.4f}  r={m_c5_snap['r']:.4f}  QWK={m_c5_snap['qwk']:.4f}  bias={m_c5_snap['bias']:+.4f}",
            f"    MAE reduction: {mae_reduction_snap:.1f}%  Wilcoxon p={p_wil_snap:.4f}",
        ]
    sum_path = os.path.join(DATA_DIR, f"{dataset}_metrics_summary.txt")
    with open(sum_path, "w") as f:
        f.write("\n".join(summary) + "\n")

    print(f"\nSaved → {out_path}")
    print(f"Summary → {sum_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["digiklausur", "kaggle_asag", "all"], required=True)
    parser.add_argument(
        "--snap-digi",
        dest="snap_digi",
        action="store_true",
        default=False,
        help="Snap predictions to {0, 2.5, 5} for DigiKlausur (sensitivity / rubric-aligned MAE).",
    )
    args = parser.parse_args()

    if args.dataset == "all":
        for ds in ["digiklausur", "kaggle_asag"]:
            print(f"\n{'='*60}")
            print(f"Dataset: {ds}")
            print(f"{'='*60}")
            try:
                run(ds, snap_digi=args.snap_digi)
            except FileNotFoundError as e:
                print(f"SKIP: {e}")
    else:
        run(args.dataset, snap_digi=args.snap_digi)


if __name__ == "__main__":
    main()
