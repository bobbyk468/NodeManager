"""
Evaluation Metrics Module for ConceptGrade.

Implements all standard ASAG evaluation metrics used in the literature:
  - Pearson correlation coefficient (r)
  - Quadratic Weighted Kappa (QWK) — primary ASAG metric
  - Cohen's Kappa (κ) — inter-rater reliability
  - RMSE / MAE — continuous error metrics
  - F1, Precision, Recall — for classification tasks (Bloom's, SOLO)
  - Concept Extraction F1 — concept-level evaluation

References:
  - Mohler & Mihalcea (2009): Pearson r for ASAG
  - Emirtekin & Ozarslan (2025): QWK for Bloom's (baseline: 0.585–0.640)
  - SemEval 2013 Task 7: 5-way classification accuracy
"""

import json
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.stats import pearsonr, spearmanr, wilcoxon, norm
from sklearn.metrics import (
    cohen_kappa_score,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
    mean_squared_error,
    mean_absolute_error,
    confusion_matrix,
    classification_report,
)


@dataclass
class EvaluationResult:
    """Complete evaluation result."""
    task_name: str = ""
    num_samples: int = 0

    # Correlation metrics (for continuous grading)
    pearson_r: float = 0.0
    pearson_p: float = 1.0
    spearman_rho: float = 0.0
    rmse: float = 0.0
    mae: float = 0.0

    # Agreement metrics (for ordinal classification)
    qwk: float = 0.0  # Quadratic Weighted Kappa
    cohens_kappa: float = 0.0
    accuracy: float = 0.0

    # Classification metrics (for Bloom's/SOLO)
    f1_macro: float = 0.0
    f1_weighted: float = 0.0
    precision_macro: float = 0.0
    recall_macro: float = 0.0
    confusion: list = field(default_factory=list)
    class_report: str = ""

    # Concept-level metrics
    concept_f1: float = 0.0
    concept_precision: float = 0.0
    concept_recall: float = 0.0

    # Bootstrap confidence intervals (95%) for primary metrics
    pearson_r_ci: tuple = field(default_factory=lambda: (0.0, 0.0))
    qwk_ci: tuple = field(default_factory=lambda: (0.0, 0.0))
    rmse_ci: tuple = field(default_factory=lambda: (0.0, 0.0))

    def to_dict(self) -> dict:
        return {
            "task_name": self.task_name,
            "num_samples": self.num_samples,
            "correlation": {
                "pearson_r": round(self.pearson_r, 4),
                "pearson_p": round(self.pearson_p, 6),
                "spearman_rho": round(self.spearman_rho, 4),
                "rmse": round(self.rmse, 4),
                "mae": round(self.mae, 4),
            },
            "agreement": {
                "qwk": round(self.qwk, 4),
                "cohens_kappa": round(self.cohens_kappa, 4),
                "accuracy": round(self.accuracy, 4),
            },
            "classification": {
                "f1_macro": round(self.f1_macro, 4),
                "f1_weighted": round(self.f1_weighted, 4),
                "precision_macro": round(self.precision_macro, 4),
                "recall_macro": round(self.recall_macro, 4),
            },
            "concept_level": {
                "f1": round(self.concept_f1, 4),
                "precision": round(self.concept_precision, 4),
                "recall": round(self.concept_recall, 4),
            },
            "confidence_intervals_95": {
                "pearson_r": [round(self.pearson_r_ci[0], 4), round(self.pearson_r_ci[1], 4)],
                "qwk": [round(self.qwk_ci[0], 4), round(self.qwk_ci[1], 4)],
                "rmse": [round(self.rmse_ci[0], 4), round(self.rmse_ci[1], 4)],
            },
        }

    def summary(self) -> str:
        ci_r = self.pearson_r_ci
        ci_q = self.qwk_ci
        lines = [
            f"=== {self.task_name} (n={self.num_samples}) ===",
            f"  Pearson r: {self.pearson_r:.4f} (p={self.pearson_p:.4e})"
            + (f"  95% CI [{ci_r[0]:.4f}, {ci_r[1]:.4f}]" if ci_r != (0.0, 0.0) else ""),
            f"  QWK: {self.qwk:.4f}"
            + (f"  95% CI [{ci_q[0]:.4f}, {ci_q[1]:.4f}]" if ci_q != (0.0, 0.0) else ""),
            f"  RMSE: {self.rmse:.4f}  MAE: {self.mae:.4f}",
            f"  F1 (macro): {self.f1_macro:.4f}  Accuracy: {self.accuracy:.4f}",
        ]
        if self.concept_f1 > 0:
            lines.append(f"  Concept F1: {self.concept_f1:.4f}")
        return "\n".join(lines)


def compute_qwk(y_true: list, y_pred: list, num_classes: int = 0) -> float:
    """
    Compute Quadratic Weighted Kappa (QWK).
    
    QWK is the standard metric for ASAG systems, measuring
    agreement between human and system scores while accounting
    for chance agreement and penalizing larger disagreements more.
    """
    return cohen_kappa_score(y_true, y_pred, weights="quadratic")


def evaluate_grading(
    y_true: list[float],
    y_pred: list[float],
    task_name: str = "Grading Evaluation",
    num_classes: int = 6,
    scale_max: float = 5.0,
) -> EvaluationResult:
    """
    Evaluate continuous grading scores (e.g., Mohler 0-5 scale).
    
    Args:
        y_true: Human expert scores
        y_pred: System-predicted scores
        task_name: Name for this evaluation
        num_classes: Number of score levels for QWK
        scale_max: Maximum score value
    """
    result = EvaluationResult(task_name=task_name, num_samples=len(y_true))

    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)

    # Correlation
    if len(y_true) >= 3:
        r, p = pearsonr(y_true_arr, y_pred_arr)
        result.pearson_r = float(r)
        result.pearson_p = float(p)
        rho, _ = spearmanr(y_true_arr, y_pred_arr)
        result.spearman_rho = float(rho)

    # Error metrics
    result.rmse = float(np.sqrt(mean_squared_error(y_true_arr, y_pred_arr)))
    result.mae = float(mean_absolute_error(y_true_arr, y_pred_arr))

    # QWK (discretize to integer levels)
    y_true_int = np.clip(np.round(y_true_arr).astype(int), 0, num_classes - 1)
    y_pred_int = np.clip(np.round(y_pred_arr).astype(int), 0, num_classes - 1)
    result.qwk = float(compute_qwk(y_true_int, y_pred_int))
    result.cohens_kappa = float(cohen_kappa_score(y_true_int, y_pred_int))
    result.accuracy = float(accuracy_score(y_true_int, y_pred_int))

    return result


def evaluate_classification(
    y_true: list[int],
    y_pred: list[int],
    task_name: str = "Classification Evaluation",
    labels: Optional[list[str]] = None,
) -> EvaluationResult:
    """
    Evaluate ordinal classification (Bloom's 1-6, SOLO 1-5).
    
    Args:
        y_true: True class labels
        y_pred: Predicted class labels
        task_name: Name for this evaluation
        labels: Human-readable label names
    """
    result = EvaluationResult(task_name=task_name, num_samples=len(y_true))

    # QWK (ordinal)
    result.qwk = float(compute_qwk(y_true, y_pred))
    result.cohens_kappa = float(cohen_kappa_score(y_true, y_pred))
    result.accuracy = float(accuracy_score(y_true, y_pred))

    # Classification metrics
    result.f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    result.f1_weighted = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
    result.precision_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    result.recall_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    result.confusion = cm.tolist()

    # Classification report
    if labels:
        result.class_report = classification_report(
            y_true, y_pred, target_names=labels, zero_division=0
        )
    else:
        result.class_report = classification_report(y_true, y_pred, zero_division=0)

    # Correlation (treat as ordinal values)
    if len(y_true) >= 3:
        r, p = pearsonr(y_true, y_pred)
        result.pearson_r = float(r)
        result.pearson_p = float(p)
        rho, _ = spearmanr(y_true, y_pred)
        result.spearman_rho = float(rho)

    return result


def evaluate_concept_extraction(
    true_concepts: list[set[str]],
    pred_concepts: list[set[str]],
) -> tuple[float, float, float]:
    """
    Evaluate concept extraction at the set level.
    
    Args:
        true_concepts: List of expert-annotated concept sets per response
        pred_concepts: List of system-extracted concept sets per response
    
    Returns:
        (precision, recall, f1) averaged across all responses
    """
    precisions, recalls, f1s = [], [], []

    for true_set, pred_set in zip(true_concepts, pred_concepts):
        if not pred_set:
            precisions.append(0.0)
            recalls.append(0.0 if true_set else 1.0)
            f1s.append(0.0 if true_set else 1.0)
            continue

        tp = len(true_set & pred_set)
        p = tp / len(pred_set) if pred_set else 0
        r = tp / len(true_set) if true_set else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

        precisions.append(p)
        recalls.append(r)
        f1s.append(f1)

    return (
        float(np.mean(precisions)),
        float(np.mean(recalls)),
        float(np.mean(f1s)),
    )


def format_comparison_table(results: list[EvaluationResult]) -> str:
    """Format a comparison table of multiple evaluation results."""
    header = f"{'System':<30} {'Pearson r':<12} {'QWK':<10} {'RMSE':<10} {'F1 (m)':<10} {'Acc':<10}"
    lines = [header, "─" * 82]
    for r in results:
        lines.append(
            f"{r.task_name:<30} {r.pearson_r:<12.4f} {r.qwk:<10.4f} "
            f"{r.rmse:<10.4f} {r.f1_macro:<10.4f} {r.accuracy:<10.4f}"
        )
    return "\n".join(lines)


def bootstrap_ci(
    y_true: list[float],
    y_pred: list[float],
    metric_fn,
    n_bootstrap: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """
    Compute bootstrap confidence interval for a metric function.

    Args:
        y_true: Ground-truth values
        y_pred: Predicted values
        metric_fn: callable(y_true_sample, y_pred_sample) → float
        n_bootstrap: Number of bootstrap resamples
        ci: Confidence level (default 0.95 = 95% CI)
        seed: Random seed for reproducibility

    Returns:
        (lower, upper) confidence interval bounds
    """
    rng = np.random.RandomState(seed)
    n = len(y_true)
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)
    scores = []
    for _ in range(n_bootstrap):
        idx = rng.randint(0, n, size=n)
        try:
            s = metric_fn(y_true_arr[idx], y_pred_arr[idx])
            if not math.isnan(s):
                scores.append(s)
        except Exception:
            pass
    if not scores:
        return (0.0, 0.0)
    alpha = 1.0 - ci
    lower = float(np.percentile(scores, alpha / 2 * 100))
    upper = float(np.percentile(scores, (1 - alpha / 2) * 100))
    return (lower, upper)


def add_bootstrap_cis(
    result: EvaluationResult,
    y_true: list[float],
    y_pred: list[float],
    n_bootstrap: int = 1000,
) -> EvaluationResult:
    """
    Add 95% bootstrap confidence intervals to an EvaluationResult in-place.

    Computes CIs for Pearson r, QWK, and RMSE. Call this after
    evaluate_grading() when you want published-quality uncertainty estimates.
    """
    from scipy.stats import pearsonr as _pearsonr
    from sklearn.metrics import cohen_kappa_score as _kappa

    def _r(yt, yp):
        r, _ = _pearsonr(yt, yp)
        return float(r)

    def _qwk(yt, yp):
        yt_i = np.clip(np.round(yt).astype(int), 0, 5)
        yp_i = np.clip(np.round(yp).astype(int), 0, 5)
        return float(_kappa(yt_i, yp_i, weights="quadratic"))

    def _rmse(yt, yp):
        return float(np.sqrt(np.mean((yt - yp) ** 2)))

    result.pearson_r_ci = bootstrap_ci(y_true, y_pred, _r, n_bootstrap)
    result.qwk_ci = bootstrap_ci(y_true, y_pred, _qwk, n_bootstrap)
    result.rmse_ci = bootstrap_ci(y_true, y_pred, _rmse, n_bootstrap)
    return result


def wilcoxon_significance(
    y_true: list[float],
    scores_a: list[float],
    scores_b: list[float],
    system_a: str = "A",
    system_b: str = "B",
) -> dict:
    """
    Wilcoxon signed-rank test to determine if system A outperforms system B
    significantly on absolute error vs. human scores.

    Uses |error_B| - |error_A| as the paired differences — positive values
    indicate A is better (lower error).

    Args:
        y_true: Human expert scores
        scores_a: System A predictions
        scores_b: System B predictions
        system_a, system_b: Names for the report

    Returns:
        dict with statistic, p_value, significant (p < 0.05), direction
    """
    err_a = np.abs(np.array(y_true) - np.array(scores_a))
    err_b = np.abs(np.array(y_true) - np.array(scores_b))
    diffs = err_b - err_a  # positive = A is better (smaller error)

    try:
        stat, p = wilcoxon(diffs, alternative="greater")
    except ValueError:
        # All differences zero — no signal
        return {
            "statistic": 0.0, "p_value": 1.0,
            "significant": False, "direction": "no_difference",
            "system_a": system_a, "system_b": system_b,
        }

    significant = bool(p < 0.05)
    return {
        "statistic": float(stat),
        "p_value": float(p),
        "significant": significant,
        "direction": f"{system_a} > {system_b}" if significant else "no_significant_difference",
        "system_a": system_a,
        "system_b": system_b,
        "mean_error_a": float(np.mean(err_a)),
        "mean_error_b": float(np.mean(err_b)),
    }


def format_significance_table(tests: list[dict]) -> str:
    """Format Wilcoxon significance test results as a table."""
    lines = [
        f"{'Comparison':<40} {'W-stat':<10} {'p-value':<12} {'Sig?':<8} {'Direction'}",
        "─" * 90,
    ]
    for t in tests:
        comparison = f"{t['system_a']} vs {t['system_b']}"
        sig = "✓ p<0.05" if t["significant"] else "✗ n.s."
        lines.append(
            f"{comparison:<40} {t['statistic']:<10.2f} {t['p_value']:<12.4f} "
            f"{sig:<8} {t['direction']}"
        )
    return "\n".join(lines)
