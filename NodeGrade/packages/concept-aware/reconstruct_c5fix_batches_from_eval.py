#!/usr/bin/env python3
"""
Rebuild {dataset}_c5fix_batch_*_response.json from a saved *_eval_results.json.

Use when split batch files were lost but the merged eval JSON still has per-sample c5_score.
"""

from __future__ import annotations

import argparse
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
BACKUP = os.path.join(DATA, "batch_responses")
BATCH_SIZE = 80


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, choices=["kaggle_asag", "digiklausur"])
    args = p.parse_args()
    ds = args.dataset

    eval_path = os.path.join(DATA, f"{ds}_eval_results.json")
    data_path = os.path.join(DATA, f"{ds}_dataset.json")
    with open(eval_path) as f:
        ev = json.load(f)
    with open(data_path) as f:
        records = json.load(f)

    id_to_idx = {r["id"]: i for i, r in enumerate(records)}
    by_batch: dict[int, dict[str, float]] = {}
    for row in ev["results"]:
        sid = row["id"]
        idx = id_to_idx[sid]
        b = idx // BATCH_SIZE + 1
        by_batch.setdefault(b, {})[str(sid)] = float(row["c5_score"])

    os.makedirs(BACKUP, exist_ok=True)
    for b, scores in sorted(by_batch.items()):
        out = {"scores": scores}
        name = f"{ds}_c5fix_batch_{b:02d}_response.json"
        path = os.path.join(BACKUP, name)
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"Wrote {path} ({len(scores)} scores)")
    print("Done. Copy to /tmp/batch_scoring/ if needed for score_batch_results.py.")


if __name__ == "__main__":
    main()
