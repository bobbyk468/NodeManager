"""
ConceptGrade Evaluation Package.

Provides metrics, baselines, and evaluation utilities for benchmarking
the ConceptGrade framework against standard ASAG systems.
"""

from .metrics import (
    EvaluationResult,
    compute_qwk,
    evaluate_grading,
    evaluate_classification,
    evaluate_concept_extraction,
    format_comparison_table,
)

from .baselines import (
    BaselineScore,
    CosineSimilarityBaseline,
    LLMZeroShotBaseline,
)

__all__ = [
    "EvaluationResult",
    "compute_qwk",
    "evaluate_grading",
    "evaluate_classification",
    "evaluate_concept_extraction",
    "format_comparison_table",
    "BaselineScore",
    "CosineSimilarityBaseline",
    "LLMZeroShotBaseline",
]
