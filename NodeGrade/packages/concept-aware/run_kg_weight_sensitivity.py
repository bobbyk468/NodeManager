#!/usr/bin/env python3
"""
Sensitivity Analysis: Test kg_weight parameter across different values.

This script tests the robustness of ConceptGrade by varying the kg_weight
hyperparameter (which governs the influence of knowledge graph matching in
the final score blend) and computing MAE improvement for each weight.

Claimed values in Paper 1 (lines 612-617):
  - kg_weight=0.01: 29.8% improvement
  - kg_weight=0.05: 32.4% improvement (default)
  - kg_weight=0.10: 31.2% improvement
  - kg_weight=0.50: 28.1% improvement

This script verifies these claims using cached batch responses.
"""

import json
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Dict, List, Tuple

# Add parent to path
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

from conceptgrade.pipeline import ConceptGradePipeline
from knowledge_graph.domain_graph import DomainKnowledgeGraph

def load_batch_responses(dataset: str) -> List[Dict]:
    """Load cached batch responses from data/batch_responses/"""
    batch_dir = BASE_DIR / "data" / "batch_responses"
    pattern = f"{dataset}_c5fix_batch_*_response.json"

    responses = []
    for batch_file in sorted(batch_dir.glob(pattern)):
        with open(batch_file) as f:
            batch_data = json.load(f)
            if isinstance(batch_data, list):
                responses.extend(batch_data)
            else:
                responses.append(batch_data)

    return responses

def load_dataset(dataset: str) -> Tuple[List[Dict], str]:
    """Load evaluation dataset"""
    data_dir = BASE_DIR / "data"

    if dataset == "mohler":
        with open(data_dir / "Mohler_dataset_gpt4o_responses.json") as f:
            data = json.load(f)
            return data, "Mohler (CS Data Structures)"
    elif dataset == "digiklausur":
        with open(data_dir / "DigiKlausur_dataset_gpt4o_responses.json") as f:
            data = json.load(f)
            return data, "DigiKlausur (Neural Networks)"
    elif dataset == "kaggle_asag":
        with open(data_dir / "Kaggle_ASAG_dataset_gpt4o_responses.json") as f:
            data = json.load(f)
            return data, "Kaggle ASAG (Elementary Science)"
    else:
        raise ValueError(f"Unknown dataset: {dataset}")

def compute_mae(predictions: List[float], targets: List[float]) -> float:
    """Compute Mean Absolute Error"""
    if len(predictions) != len(targets):
        raise ValueError("Predictions and targets must have same length")
    errors = [abs(p - t) for p, t in zip(predictions, targets)]
    return mean(errors) if errors else 0.0

def compute_improvement(baseline_mae: float, system_mae: float) -> float:
    """Compute improvement percentage (lower MAE is better)"""
    if baseline_mae == 0:
        return 0.0
    return ((baseline_mae - system_mae) / baseline_mae) * 100.0

def run_sensitivity_analysis(dataset: str = "mohler"):
    """Run kg_weight sensitivity analysis"""
    print("=" * 80)
    print("KG_WEIGHT SENSITIVITY ANALYSIS")
    print("=" * 80)

    # Load dataset and responses
    data, dataset_name = load_dataset(dataset)
    print(f"\n[1/3] Loading {dataset_name}...")
    print(f"      Loaded {len(data)} student answers")

    # Load KG from cache
    print(f"\n[2/3] Loading cached KG...")
    kg_cache_file = BASE_DIR / "data" / f"{dataset}_kg.json"
    if kg_cache_file.exists():
        with open(kg_cache_file) as f:
            kg_data = json.load(f)
        kg = KnowledgeGraphBuilder.from_dict(kg_data)
        print(f"      Loaded KG with {len(kg.nodes)} nodes")
    else:
        print(f"      ERROR: KG cache not found at {kg_cache_file}")
        return

    # Get baseline (LLM-only, no KG)
    print(f"\n[3/3] Computing scores with different kg_weight values...")
    baseline_predictions = []
    for item in data:
        student_answer = item.get("answer", "")
        ground_truth_score = float(item.get("score", 0.0))

        # Create pipeline with kg_weight=0 (baseline: LLM only)
        pipeline = ConceptGradePipeline(
            kg=kg,
            kg_weight=0.0,  # LLM only
            holistic_weight=1.0
        )

        result = pipeline.assess_student(
            student_answer=student_answer,
            reference_answer=item.get("reference_answer", ""),
            rubric=item.get("rubric", "")
        )
        baseline_predictions.append(result.overall_score)

    baseline_mae = compute_mae(baseline_predictions, [item["score"] for item in data])
    print(f"\n  Baseline (LLM only, kg_weight=0.0): MAE={baseline_mae:.4f}")

    # Test different kg_weight values
    kg_weights = [0.01, 0.05, 0.10, 0.50]
    results = []

    for kg_weight in kg_weights:
        holistic_weight = 1.0 - kg_weight
        predictions = []

        for item in data:
            student_answer = item.get("answer", "")
            ground_truth_score = float(item.get("score", 0.0))

            pipeline = ConceptGradePipeline(
                kg=kg,
                kg_weight=kg_weight,
                holistic_weight=holistic_weight
            )

            result = pipeline.assess_student(
                student_answer=student_answer,
                reference_answer=item.get("reference_answer", ""),
                rubric=item.get("rubric", "")
            )
            predictions.append(result.overall_score)

        mae = compute_mae(predictions, [item["score"] for item in data])
        improvement = compute_improvement(baseline_mae, mae)

        results.append({
            "kg_weight": kg_weight,
            "holistic_weight": holistic_weight,
            "mae": mae,
            "improvement_pct": improvement
        })

        print(f"  kg_weight={kg_weight:.2f}: MAE={mae:.4f}, improvement={improvement:.1f}%")

    # Print summary
    print("\n" + "=" * 80)
    print("SENSITIVITY ANALYSIS RESULTS")
    print("=" * 80)
    print(f"\nDataset: {dataset_name}")
    print(f"Baseline (LLM only): MAE={baseline_mae:.4f}")
    print(f"\nResults:")
    print(f"{'kg_weight':<12} {'holistic_weight':<18} {'MAE':<10} {'Improvement':<15}")
    print("-" * 55)
    for r in results:
        print(f"{r['kg_weight']:<12.2f} {r['holistic_weight']:<18.2f} {r['mae']:<10.4f} {r['improvement_pct']:<14.1f}%")

    # Verify against claimed values
    print("\n" + "=" * 80)
    print("VERIFICATION AGAINST PAPER 1 CLAIMS")
    print("=" * 80)
    print("\nClaimed values (paper_phase1_ieee.tex lines 612-617):")
    print("  - kg_weight=0.01: 29.8% improvement")
    print("  - kg_weight=0.05: 32.4% improvement (default)")
    print("  - kg_weight=0.10: 31.2% improvement")
    print("  - kg_weight=0.50: 28.1% improvement")

    print("\nActual values (this run):")
    for r in results:
        claimed = {
            0.01: 29.8,
            0.05: 32.4,
            0.10: 31.2,
            0.50: 28.1
        }.get(r["kg_weight"])

        actual = r["improvement_pct"]
        if claimed:
            diff = abs(actual - claimed)
            status = "✓" if diff < 2.0 else "✗"
            print(f"  {status} kg_weight={r['kg_weight']:.2f}: claimed={claimed:.1f}%, actual={actual:.1f}%, diff={diff:.1f}%")

    print("\n✓ Sensitivity analysis complete.")
    print("  Save this output for Paper 1 verification report.")

if __name__ == "__main__":
    dataset = sys.argv[1] if len(sys.argv) > 1 else "mohler"
    try:
        run_sensitivity_analysis(dataset)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
