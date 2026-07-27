#!/usr/bin/env python3
"""
compute_solo_breakdown.py — Per-SOLO-band MAE reduction across all three
cached datasets. Tests the hypothesis that ConceptGrade's gain is concentrated
in higher-SOLO answers, where KG structure provides the strongest signal.

Outputs both per-band counts and the bottom-line per-band MAE reduction;
results back the per-question SOLO discussion in Paper 1 §5.

Run:
    python compute_solo_breakdown.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent
SOLO_ORDER = ["Prestructural", "Unistructural", "Multistructural",
              "Relational", "Extended Abstract"]


def compute_one(ds: str) -> dict:
    with (BASE / "data" / f"{ds}_eval_results.json").open() as f:
        d = json.load(f)
    results = d["results"]
    by_solo: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in results:
        solo = r.get("solo", "Unknown")
        err_cllm = abs(r["human_score"] - r["cllm_score"])
        err_c5 = abs(r["human_score"] - r["c5_score"])
        by_solo[solo].append((err_cllm, err_c5))

    rows = []
    for solo in SOLO_ORDER + ["Unknown"]:
        if solo not in by_solo:
            continue
        arr = np.array(by_solo[solo])
        n = len(arr)
        m_cllm = float(arr[:, 0].mean())
        m_c5 = float(arr[:, 1].mean())
        delta = m_cllm - m_c5
        red = delta / m_cllm * 100 if m_cllm > 0 else 0.0
        rows.append({
            "solo": solo,
            "n": n,
            "mae_cllm": round(m_cllm, 4),
            "mae_c5": round(m_c5, 4),
            "delta_mae": round(delta, 4),
            "reduction_pct": round(red, 1),
        })
    return {"dataset": ds, "n_total": len(results), "by_solo": rows}


def main() -> int:
    out = {"datasets": []}
    for ds in ["mohler", "digiklausur", "kaggle_asag"]:
        result = compute_one(ds)
        out["datasets"].append(result)
        print(f"\n=== {ds.upper()} (n = {result['n_total']}) ===")
        print(f"  {'SOLO band':<22}{'n':>6}{'MAE_C_LLM':>11}"
              f"{'MAE_C5':>11}{'Δ MAE':>9}{'Reduction':>11}")
        for row in result["by_solo"]:
            sign = "+" if row["delta_mae"] >= 0 else ""
            print(f"  {row['solo']:<22}{row['n']:>6}"
                  f"{row['mae_cllm']:>11.3f}{row['mae_c5']:>11.3f}"
                  f"{sign + format(row['delta_mae'], '.3f'):>9}"
                  f"{row['reduction_pct']:>10.1f}%")

    # Save JSON
    out_path = BASE / "data" / "solo_breakdown.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
