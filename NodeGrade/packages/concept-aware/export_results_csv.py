"""
export_results_csv.py — Export all evaluation results and batch API responses to CSV.

Produces:
  data/csv/{dataset}_per_sample.csv   — one row per answer with all scores + features
  data/csv/{dataset}_metrics.csv      — one row per dataset with aggregate metrics
  data/csv/all_datasets_metrics.csv   — combined metrics across all datasets
  data/csv/batch_responses/{dataset}_{system}_batch_NN.csv  — raw API response per batch

Usage:
    python3 export_results_csv.py                   # export all datasets
    python3 export_results_csv.py --dataset digiklausur
    python3 export_results_csv.py --no-batches       # skip raw batch response CSVs
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data")
CSV_DIR   = os.path.join(DATA_DIR, "csv")
BATCH_DIR = os.path.join(DATA_DIR, "batch_responses")


def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


# ── Per-sample CSV ────────────────────────────────────────────────────────────

def export_per_sample(dataset: str) -> str:
    eval_path = os.path.join(DATA_DIR, f"{dataset}_eval_results.json")
    if not os.path.exists(eval_path):
        return ""
    with open(eval_path) as f:
        ev = json.load(f)
    results = ev.get("results", [])
    if not results:
        return ""

    out_path = os.path.join(CSV_DIR, f"{dataset}_per_sample.csv")
    fieldnames = [
        "id", "human_score", "cllm_score", "c5_score",
        "cllm_abs_error", "c5_abs_error", "c5_wins",
        "matched_concepts", "n_matched_concepts", "chain_pct", "solo", "bloom",
    ]

    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            cllm_err = abs(r["cllm_score"] - r["human_score"])
            c5_err   = abs(r["c5_score"]   - r["human_score"])
            matched  = r.get("matched_concepts") or []
            w.writerow({
                "id":               r["id"],
                "human_score":      r["human_score"],
                "cllm_score":       r["cllm_score"],
                "c5_score":         r["c5_score"],
                "cllm_abs_error":   round(cllm_err, 4),
                "c5_abs_error":     round(c5_err, 4),
                "c5_wins":          1 if c5_err < cllm_err else (0 if c5_err > cllm_err else "tie"),
                "matched_concepts": "|".join(matched),
                "n_matched_concepts": len(matched),
                "chain_pct":        r.get("chain_pct", ""),
                "solo":             r.get("solo", ""),
                "bloom":            r.get("bloom", ""),
            })
    return out_path


# ── Aggregate metrics CSV ─────────────────────────────────────────────────────

METRIC_FIELDS = ["mae", "rmse", "r", "rho", "qwk", "bias"]

def export_metrics(datasets: list[str]) -> str:
    rows: list[dict] = []
    for dataset in datasets:
        eval_path = os.path.join(DATA_DIR, f"{dataset}_eval_results.json")
        if not os.path.exists(eval_path):
            continue
        with open(eval_path) as f:
            ev = json.load(f)
        mc  = ev.get("metrics", {}).get("C_LLM", {})
        m5  = ev.get("metrics", {}).get("C5_fix", {})
        row: dict = {
            "dataset":          dataset,
            "n":                ev.get("n", 0),
            "wilcoxon_p":       round(ev.get("wilcoxon_p", 1.0), 6),
            "mae_reduction_pct": round(ev.get("mae_reduction_pct", 0.0), 4),
        }
        for mf in METRIC_FIELDS:
            row[f"cllm_{mf}"] = round(mc.get(mf, 0.0), 6)
            row[f"c5fix_{mf}"] = round(m5.get(mf, 0.0), 6)
        # Snapped metrics if available
        ms = ev.get("metrics_snapped")
        if ms:
            mcs = ms.get("C_LLM", {})
            m5s = ms.get("C5_fix", {})
            row["snap_cllm_mae"]  = round(mcs.get("mae", 0.0), 6)
            row["snap_c5fix_mae"] = round(m5s.get("mae", 0.0), 6)
            row["snap_wilcoxon_p"] = round(ms.get("wilcoxon_p", 1.0), 6)
            row["snap_mae_reduction_pct"] = round(ms.get("mae_reduction_pct", 0.0), 4)
        rows.append(row)

    # Add Mohler from offline eval results
    mohler_path = os.path.join(DATA_DIR, "evaluation_results.json")
    if os.path.exists(mohler_path):
        with open(mohler_path) as f:
            moh = json.load(f)
        results_dict = moh.get("results", {})
        cg  = results_dict.get("conceptgrade", {})
        llm = results_dict.get("llm_zero_shot", {})
        rows.insert(0, {
            "dataset": "mohler_2011",
            "n": 120,
            "wilcoxon_p": 0.0026,
            "mae_reduction_pct": round((llm.get("mae", 0) - cg.get("mae", 0)) / max(llm.get("mae", 1), 1e-9) * 100, 4),
            "cllm_mae": round(llm.get("mae", 0), 6),
            "c5fix_mae": round(cg.get("mae", 0), 6),
            "cllm_r": round(llm.get("pearson_r", 0), 6),
            "c5fix_r": round(cg.get("pearson_r", 0), 6),
            "cllm_qwk": round(llm.get("qwk", 0), 6),
            "c5fix_qwk": round(cg.get("qwk", 0), 6),
        })

    if not rows:
        return ""

    all_fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in all_fields:
                all_fields.append(k)

    out_path = os.path.join(CSV_DIR, "all_datasets_metrics.csv")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in all_fields})

    return out_path


# ── Raw batch response CSVs ───────────────────────────────────────────────────

def export_batch_responses(dataset: str) -> list[str]:
    """Convert every batch_responses/{dataset}_*_batch_NN_response.json to CSV."""
    batch_csv_dir = os.path.join(CSV_DIR, "batch_responses")
    ensure_dir(batch_csv_dir)

    pattern = os.path.join(BATCH_DIR, f"{dataset}_*_batch_*.json")
    files = sorted(glob.glob(pattern))
    written: list[str] = []

    for fpath in files:
        with open(fpath) as f:
            raw = json.load(f)
        scores = raw.get("scores", raw)
        if not isinstance(scores, dict):
            continue

        stem = os.path.splitext(os.path.basename(fpath))[0]  # e.g. digiklausur_cllm_batch_01_response
        out_path = os.path.join(batch_csv_dir, f"{stem}.csv")
        with open(out_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["sample_id", "score"])
            for sid, val in sorted(scores.items(), key=lambda x: int(x[0])):
                if isinstance(val, dict):
                    score = val.get("score", val.get("cllm_score", val.get("c5fix_score", "")))
                else:
                    score = val
                w.writerow([sid, score])
        written.append(out_path)

    return written


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        choices=["digiklausur", "kaggle_asag", "all"],
        default="all",
    )
    parser.add_argument(
        "--no-batches",
        action="store_true",
        help="Skip exporting individual batch response CSVs",
    )
    args = parser.parse_args()
    ensure_dir(CSV_DIR)

    datasets = ["digiklausur", "kaggle_asag"] if args.dataset == "all" else [args.dataset]

    print(f"Exporting CSVs → {CSV_DIR}/")
    print()

    # Per-sample CSVs
    for ds in datasets:
        p = export_per_sample(ds)
        if p:
            n = sum(1 for _ in open(p)) - 1  # subtract header
            print(f"  {os.path.relpath(p, BASE_DIR)}  ({n} rows)")

    # Aggregate metrics
    p = export_metrics(datasets)
    if p:
        print(f"  {os.path.relpath(p, BASE_DIR)}")

    # Raw batch response CSVs
    if not args.no_batches:
        print()
        print("  Batch response CSVs:")
        for ds in datasets:
            written = export_batch_responses(ds)
            for p in written:
                print(f"    {os.path.relpath(p, BASE_DIR)}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
