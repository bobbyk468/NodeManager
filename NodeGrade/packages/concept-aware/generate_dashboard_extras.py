"""
generate_dashboard_extras.py — Populate student_radar and misconception_heatmap
from existing cached evaluation results. No API calls required.

Reads:
  data/{dataset}_eval_results.json       — per-sample scores + matched concepts
  data/{dataset}_auto_kg.json            — expected concepts per question
  data/{dataset}_dataset.json            — question text → match to KG index

Writes:
  data/{dataset}_dashboard_extras.json   — radar + heatmap data for the NestJS API

Usage:
    python3 generate_dashboard_extras.py --dataset digiklausur
    python3 generate_dashboard_extras.py --dataset kaggle_asag
    python3 generate_dashboard_extras.py --dataset all
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

SOLO_LEVEL_MAP = {
    "Prestructural": 1, "Unistructural": 2, "Multistructural": 3,
    "Relational": 4, "Extended Abstract": 5,
}
BLOOM_LEVEL_MAP = {
    "Remember": 1, "Understand": 2, "Apply": 3,
    "Analyze": 4, "Evaluate": 5, "Create": 6,
}


# ── Radar: group samples by score quartile and compute 5-dimension profiles ──

def build_student_radar(results: list[dict]) -> dict:
    """
    Group all samples into 4 score quartiles and compute a 5-dimension
    cognitive profile per group. These serve as representative "student types"
    in the radar chart.

    Dimensions:
      1. Concept Coverage  — chain_pct as fraction [0-1]
      2. SOLO Level        — numeric 1-5, normalised to [0-1]
      3. Bloom Level       — numeric 1-6, normalised to [0-1]
      4. Grading Accuracy  — 1 - |c5_score - human_score| / max_scale
      5. Score             — c5_score normalised to [0-1]
    """
    if not results:
        return {"dimensions": [], "students": []}

    max_score = max((r["human_score"] for r in results), default=5.0)
    max_score = max(max_score, 1.0)

    def chain_to_float(pct: str) -> float:
        try:
            return float(pct.rstrip("%")) / 100
        except Exception:
            return 0.0

    DIMS = ["Concept Coverage", "SOLO Level", "Bloom Level", "Grading Accuracy", "Score"]

    # Sort by human_score then split into quartiles
    sorted_r = sorted(results, key=lambda r: r["human_score"])
    n = len(sorted_r)
    quartile_labels = ["Low Scorers (Q1)", "Mid-Low (Q2)", "Mid-High (Q3)", "High Scorers (Q4)"]
    quartile_colors = ["#ef4444", "#f97316", "#22c55e", "#3b82f6"]

    students = []
    for qi in range(4):
        lo = qi * n // 4
        hi = (qi + 1) * n // 4 if qi < 3 else n
        group = sorted_r[lo:hi]
        if not group:
            continue

        cov   = float(np.mean([chain_to_float(r.get("chain_pct", "0%")) for r in group]))
        solo  = float(np.mean([SOLO_LEVEL_MAP.get(r.get("solo", ""), 0) for r in group])) / 5
        bloom = float(np.mean([BLOOM_LEVEL_MAP.get(r.get("bloom", ""), 0) for r in group])) / 6
        acc   = float(np.mean([
            1.0 - abs(r["c5_score"] - r["human_score"]) / max_score for r in group
        ]))
        score = float(np.mean([r["c5_score"] for r in group])) / max_score

        students.append({
            "student_id": quartile_labels[qi],
            "color": quartile_colors[qi],
            "n": len(group),
            "avg_human_score": float(np.mean([r["human_score"] for r in group])),
            "values": [
                round(cov, 3),
                round(solo, 3),
                round(bloom, 3),
                round(acc, 3),
                round(score, 3),
            ],
        })

    return {"dimensions": DIMS, "students": students}


# ── Heatmap: concepts missed × severity level ────────────────────────────────

def build_question_to_expected(kg_path: str, dataset_path: str) -> dict[int, list[str]]:
    """Return mapping: sample_id → expected_concept_ids from the KG."""
    if not os.path.exists(kg_path) or not os.path.exists(dataset_path):
        return {}

    with open(kg_path) as f:
        kg_raw = json.load(f)
    q_to_kg = kg_raw.get("question_kgs", kg_raw)

    with open(dataset_path) as f:
        dataset = json.load(f)

    # Build question-text → KG index map
    q_text_to_idx: dict[str, str] = {}
    for idx, qdata in q_to_kg.items():
        q_text_to_idx[qdata.get("question", "").strip().lower()] = idx

    # Map each sample's question text → expected concepts
    sample_to_expected: dict[int, list[str]] = {}
    for row in dataset:
        sid = int(row["id"])
        q_text = row.get("question", "").strip().lower()
        idx = q_text_to_idx.get(q_text)
        if idx is not None:
            sample_to_expected[sid] = q_to_kg[idx].get("expected_concepts", [])
        else:
            sample_to_expected[sid] = []
    return sample_to_expected


def build_misconception_heatmap(
    results: list[dict],
    sample_to_expected: dict[int, list[str]],
    top_k: int = 20,
) -> dict:
    """
    Compute a concept × severity heatmap.

    Severity buckets (by human_score):
      critical: human_score >= 3.5   (good students who still missed the concept)
      moderate: human_score 2.0–3.5
      minor:    human_score < 2.0    (low-scoring students where misses are expected)

    A concept appears in a cell when it is in expected_concepts but NOT in matched_concepts.
    """
    SEVERITY = [
        ("critical", lambda h: h >= 3.5),
        ("moderate", lambda h: 2.0 <= h < 3.5),
        ("minor",    lambda h: h < 2.0),
    ]

    # concept_id → {"critical": count, "moderate": count, "minor": count}
    missed_counts: dict[str, dict[str, int]] = {}

    for r in results:
        sid = int(r["id"])
        human = r["human_score"]
        matched = set(r.get("matched_concepts") or [])
        expected = sample_to_expected.get(sid, [])
        missed = [c for c in expected if c not in matched]

        for concept in missed:
            if concept not in missed_counts:
                missed_counts[concept] = {"critical": 0, "moderate": 0, "minor": 0}
            for sev_name, sev_fn in SEVERITY:
                if sev_fn(human):
                    missed_counts[concept][sev_name] += 1
                    break  # only one bucket per sample

    if not missed_counts:
        return {
            "cells": [],
            "x_labels": ["critical", "moderate", "minor"],
            "y_labels": [],
        }

    # Sort concepts by total miss count descending, take top K
    sorted_concepts = sorted(
        missed_counts.keys(),
        key=lambda c: sum(missed_counts[c].values()),
        reverse=True,
    )[:top_k]

    x_labels = ["critical", "moderate", "minor"]
    y_labels = sorted_concepts

    # Build cells list: each cell = {x, y, value}
    max_val = max(
        max(missed_counts[c][sev] for sev in x_labels)
        for c in sorted_concepts
    ) if sorted_concepts else 1

    cells = []
    for c in sorted_concepts:
        for sev in x_labels:
            cnt = missed_counts[c][sev]
            cells.append({
                "x": sev,
                "y": c,
                "value": cnt,
                "intensity": round(cnt / max(max_val, 1), 3),
            })

    # Top-3 insights
    total_by_concept = {c: sum(missed_counts[c].values()) for c in sorted_concepts}
    top3 = sorted(sorted_concepts, key=lambda c: total_by_concept[c], reverse=True)[:3]
    insights = [
        f"Most missed concept: '{top3[0]}' ({total_by_concept[top3[0]]} misses total)."
        if top3 else "No concept miss data.",
    ]
    critical_hot = sorted(
        sorted_concepts,
        key=lambda c: missed_counts[c]["critical"],
        reverse=True,
    )
    if critical_hot and missed_counts[critical_hot[0]]["critical"] > 0:
        c = critical_hot[0]
        insights.append(
            f"'{c}' most frequently missed by high-scoring students "
            f"({missed_counts[c]['critical']} critical misses)."
        )

    return {
        "cells": cells,
        "x_labels": x_labels,
        "y_labels": y_labels,
        "max_value": max_val,
        "insights": insights,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def process(dataset: str) -> None:
    eval_path    = os.path.join(DATA_DIR, f"{dataset}_eval_results.json")
    kg_path      = os.path.join(DATA_DIR, f"{dataset}_auto_kg.json")
    dataset_path = os.path.join(DATA_DIR, f"{dataset}_dataset.json")
    out_path     = os.path.join(DATA_DIR, f"{dataset}_dashboard_extras.json")

    if not os.path.exists(eval_path):
        print(f"  [{dataset}] SKIP — {eval_path} not found")
        return

    with open(eval_path) as f:
        ev = json.load(f)
    results = ev.get("results", [])
    print(f"  [{dataset}] {len(results)} samples loaded")

    # Student radar
    radar_data = build_student_radar(results)
    print(f"    radar: {len(radar_data['students'])} quartile groups")

    # Misconception heatmap
    sample_to_expected = build_question_to_expected(kg_path, dataset_path)
    heatmap_data = build_misconception_heatmap(results, sample_to_expected, top_k=20)
    print(f"    heatmap: {len(heatmap_data['y_labels'])} concepts × "
          f"{len(heatmap_data['x_labels'])} severity levels, "
          f"{len(heatmap_data['cells'])} cells")

    extras = {
        "dataset": dataset,
        "student_radar": radar_data,
        "misconception_heatmap": heatmap_data,
    }
    with open(out_path, "w") as f:
        json.dump(extras, f, indent=2)
    print(f"    → {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        choices=["digiklausur", "kaggle_asag", "all"],
        default="all",
    )
    args = parser.parse_args()

    datasets = ["digiklausur", "kaggle_asag"] if args.dataset == "all" else [args.dataset]
    print(f"Generating dashboard extras for: {datasets}")
    for ds in datasets:
        process(ds)
    print("Done.")


if __name__ == "__main__":
    main()
