"""
Inter-Rater Reliability Module for ConceptGrade.

Computes agreement metrics between ConceptGrade's automated scores and
human expert raters — the gold standard evaluation for any ASAG system.

Metrics implemented
-------------------
1. Cohen's κ (linear weighted)    — pairwise agreement, ordinal penalty
2. Cohen's κ (quadratic weighted) — QWK, standard ASAG metric
3. Krippendorff's α               — multi-rater, handles missing data
4. Intraclass Correlation (ICC)   — continuous agreement (two-way mixed)
5. Pearson r / Spearman ρ         — correlation with human consensus
6. Exact agreement %              — fraction of exact matches
7. Adjacent agreement %           — fraction within ±0.5 of human score
8. Bland-Altman analysis          — mean bias and limits of agreement
9. Per-question reliability       — identifies questions where system struggles

Research context
----------------
Following SemEval 2013 Task 7, ASAG systems are evaluated against
two human raters. The system's κ with each rater should approach
the human-human κ (upper bound). ConceptGrade targets:
  - QWK ≥ 0.70 (strong agreement)
  - Pearson r ≥ 0.90
  - Human-human QWK serves as the theoretical ceiling

Reference
---------
  Landis & Koch (1977): κ interpretation:
    < 0.20 Slight, 0.21-0.40 Fair, 0.41-0.60 Moderate,
    0.61-0.80 Substantial, 0.81-1.00 Almost Perfect
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.stats import pearsonr, spearmanr, norm
from sklearn.metrics import cohen_kappa_score


# ─── Krippendorff's α ────────────────────────────────────────────────────────

def krippendorff_alpha(
    ratings: list[list[Optional[float]]],
    level: str = "ordinal",
    max_val: float = 5.0,
) -> float:
    """
    Compute Krippendorff's α for multiple raters.

    Parameters
    ----------
    ratings : list of rater score lists.
              ratings[i] = list of scores from rater i (None = missing).
    level   : "nominal", "ordinal", "interval", or "ratio"
    max_val : Maximum score value (for ordinal/ratio metrics)

    Returns
    -------
    α ∈ [-1, 1] (1 = perfect agreement, 0 = chance, <0 = worse than chance)
    """
    n_raters = len(ratings)
    n_units  = len(ratings[0])

    # Build coincidence matrix
    # First flatten to (unit, rater) pairs
    values = sorted({v for r in ratings for v in r if v is not None})
    val_to_idx = {v: i for i, v in enumerate(values)}
    n_vals = len(values)

    if n_vals < 2:
        return 1.0  # All raters gave same value

    # Coincidence matrix c[k][l] = number of times value k and l appear
    # in same unit (across rater pairs)
    c = np.zeros((n_vals, n_vals))
    n_pairs_total = 0

    for u in range(n_units):
        unit_vals = [ratings[r][u] for r in range(n_raters) if ratings[r][u] is not None]
        n_u = len(unit_vals)
        if n_u < 2:
            continue
        for i in range(n_u):
            for j in range(n_u):
                if i != j:
                    k = val_to_idx[unit_vals[i]]
                    l = val_to_idx[unit_vals[j]]
                    c[k][l] += 1.0 / (n_u - 1)
        n_pairs_total += n_u * (n_u - 1) / (n_u - 1)

    if n_pairs_total == 0:
        return float("nan")

    n_k = c.sum(axis=1)  # Marginal counts per value

    # Difference function d²(k, l) depends on measurement level
    def d2(k_idx, l_idx):
        if level == "nominal":
            return 0.0 if k_idx == l_idx else 1.0
        elif level == "ordinal":
            # Sum of marginal counts between k and l
            lo, hi = min(k_idx, l_idx), max(k_idx, l_idx)
            return (sum(n_k[lo:hi+1]) - (n_k[lo] + n_k[hi]) / 2.0) ** 2
        elif level == "interval":
            vk = values[k_idx]
            vl = values[l_idx]
            return (vk - vl) ** 2
        else:  # ratio
            vk = values[k_idx]
            vl = values[l_idx]
            return ((vk - vl) / (vk + vl + 1e-9)) ** 2 if (vk + vl) > 0 else 0.0

    # Observed disagreement
    D_o = sum(c[k][l] * d2(k, l) for k in range(n_vals) for l in range(n_vals))
    D_o /= c.sum()

    # Expected disagreement
    n_total = n_k.sum()
    D_e = sum(n_k[k] * n_k[l] * d2(k, l)
              for k in range(n_vals) for l in range(n_vals))
    D_e /= n_total * (n_total - 1) if n_total > 1 else 1.0

    if D_e == 0:
        return 1.0 if D_o == 0 else 0.0

    return float(1.0 - D_o / D_e)


# ─── ICC ─────────────────────────────────────────────────────────────────────

def icc_two_way_mixed(
    rater1: list[float],
    rater2: list[float],
) -> dict[str, float]:
    """
    Two-way mixed-effects ICC (consistency, single measure) — ICC(3,1).

    This is the appropriate ICC model when:
    - Raters are fixed (same raters for all units)
    - Units are random (sampled from a population)
    - We care about consistency, not absolute agreement

    Returns dict with icc, f_stat, p_value, lower_ci, upper_ci (95%).
    """
    y1 = np.array(rater1, dtype=float)
    y2 = np.array(rater2, dtype=float)
    n = len(y1)
    if n < 3:
        return {"icc": float("nan"), "f_stat": float("nan"),
                "p_value": 1.0, "lower_ci": float("nan"), "upper_ci": float("nan")}

    k = 2  # Two raters
    # Grand mean
    grand_mean = (y1.mean() + y2.mean()) / 2.0
    data = np.stack([y1, y2], axis=1)  # (n, k)

    # SS between subjects (rows)
    row_means = data.mean(axis=1)
    SSr = k * np.sum((row_means - grand_mean) ** 2)
    MSr = SSr / (n - 1)

    # SS between raters (columns)
    col_means = data.mean(axis=0)
    SSc = n * np.sum((col_means - grand_mean) ** 2)
    MSc = SSc / (k - 1)

    # SS residual (error)
    SSe = np.sum((data - row_means[:, None] - col_means[None, :] + grand_mean) ** 2)
    MSe = SSe / ((n - 1) * (k - 1))

    # ICC(3,1) — two-way mixed, consistency
    icc_val = (MSr - MSe) / (MSr + (k - 1) * MSe)

    # F-test
    F = MSr / MSe if MSe > 0 else float("inf")
    from scipy.stats import f as f_dist
    df1 = n - 1
    df2 = (n - 1) * (k - 1)
    p = 1.0 - f_dist.cdf(F, df1, df2)

    # 95% CI via Fisher's z-transform approximation
    # (Shrout & Fleiss, 1979)
    FL = (F / f_dist.ppf(0.975, df1, df2) - 1) / (F / f_dist.ppf(0.975, df1, df2) + k - 1)
    FU = (F * f_dist.ppf(0.975, df2, df1) - 1) / (F * f_dist.ppf(0.975, df2, df1) + k - 1)
    FL = max(0.0, FL)
    FU = min(1.0, FU)

    return {
        "icc": round(float(icc_val), 4),
        "f_stat": round(float(F), 3),
        "p_value": round(float(p), 5),
        "lower_ci_95": round(float(FL), 4),
        "upper_ci_95": round(float(FU), 4),
    }


# ─── Bland-Altman ────────────────────────────────────────────────────────────

def bland_altman(
    method1: list[float],
    method2: list[float],
    name1: str = "Rater1",
    name2: str = "System",
) -> dict:
    """
    Bland-Altman analysis of agreement between two measurement methods.

    Computes:
    - Mean difference (bias): positive = method2 scores higher
    - Standard deviation of differences
    - 95% Limits of Agreement (LoA): mean ± 1.96 * SD
    - Percentage within LoA
    """
    a = np.array(method1, dtype=float)
    b = np.array(method2, dtype=float)
    diffs = b - a
    means = (a + b) / 2.0

    bias = float(np.mean(diffs))
    sd   = float(np.std(diffs, ddof=1))
    loa_lo = bias - 1.96 * sd
    loa_hi = bias + 1.96 * sd

    within_loa = float(np.mean((diffs >= loa_lo) & (diffs <= loa_hi)) * 100)

    return {
        "bias": round(bias, 4),
        "sd_diff": round(sd, 4),
        "loa_lower": round(loa_lo, 4),
        "loa_upper": round(loa_hi, 4),
        "within_loa_pct": round(within_loa, 1),
        "name1": name1,
        "name2": name2,
        "n": len(diffs),
    }


# ─── Main reliability result ──────────────────────────────────────────────────

@dataclass
class ReliabilityResult:
    """Complete inter-rater reliability analysis."""
    comparison: str          # e.g. "ConceptGrade vs Rater1"
    n_samples: int = 0

    # Core agreement
    qwk: float = 0.0
    linear_kappa: float = 0.0
    pearson_r: float = 0.0
    pearson_p: float = 1.0
    spearman_rho: float = 0.0

    # ICC
    icc: dict = field(default_factory=dict)

    # Bland-Altman
    bland_altman: dict = field(default_factory=dict)

    # Agreement rates
    exact_agreement_pct: float = 0.0
    adjacent_agreement_pct: float = 0.0  # within ±0.5

    # Krippendorff's α
    krippendorff_alpha: float = 0.0

    # Landis-Koch interpretation
    kappa_interpretation: str = ""

    def to_dict(self) -> dict:
        return {
            "comparison": self.comparison,
            "n_samples": self.n_samples,
            "qwk": round(self.qwk, 4),
            "linear_kappa": round(self.linear_kappa, 4),
            "pearson_r": round(self.pearson_r, 4),
            "pearson_p": round(self.pearson_p, 6),
            "spearman_rho": round(self.spearman_rho, 4),
            "icc": self.icc,
            "bland_altman": self.bland_altman,
            "exact_agreement_pct": round(self.exact_agreement_pct, 1),
            "adjacent_agreement_pct": round(self.adjacent_agreement_pct, 1),
            "krippendorff_alpha": round(self.krippendorff_alpha, 4),
            "kappa_interpretation": self.kappa_interpretation,
        }

    def summary(self) -> str:
        lines = [
            f"=== {self.comparison} (n={self.n_samples}) ===",
            f"  QWK:              {self.qwk:.4f}  [{self._interp(self.qwk)}]",
            f"  Linear κ:         {self.linear_kappa:.4f}",
            f"  Krippendorff α:   {self.krippendorff_alpha:.4f}",
            f"  Pearson r:        {self.pearson_r:.4f}  (p={self.pearson_p:.4e})",
            f"  Spearman ρ:       {self.spearman_rho:.4f}",
            f"  ICC(3,1):         {self.icc.get('icc', 'N/A')}  "
            f"95%CI [{self.icc.get('lower_ci_95','?')}, {self.icc.get('upper_ci_95','?')}]",
            f"  Exact agreement:  {self.exact_agreement_pct:.1f}%",
            f"  Adjacent (±0.5):  {self.adjacent_agreement_pct:.1f}%",
            f"  Bland-Altman bias:{self.bland_altman.get('bias', 'N/A'):.4f}  "
            f"LoA [{self.bland_altman.get('loa_lower','?'):.3f}, "
            f"{self.bland_altman.get('loa_upper','?'):.3f}]",
        ]
        return "\n".join(lines)

    @staticmethod
    def _interp(k: float) -> str:
        if k < 0.20:  return "Slight"
        if k < 0.40:  return "Fair"
        if k < 0.60:  return "Moderate"
        if k < 0.80:  return "Substantial"
        return "Almost Perfect"


def _kappa_interpretation(k: float) -> str:
    if k < 0.20:  return "Slight"
    if k < 0.40:  return "Fair"
    if k < 0.60:  return "Moderate"
    if k < 0.80:  return "Substantial"
    return "Almost Perfect"


# ─── Main function ────────────────────────────────────────────────────────────

def compute_reliability(
    scores_a: list[float],
    scores_b: list[float],
    comparison: str = "A vs B",
    scale_max: float = 5.0,
    n_classes: int = 6,
) -> ReliabilityResult:
    """
    Compute full inter-rater reliability between two sets of scores.

    Parameters
    ----------
    scores_a    : Scores from rater/system A
    scores_b    : Scores from rater/system B
    comparison  : Label for this comparison
    scale_max   : Maximum score (Mohler = 5.0)
    n_classes   : Number of integer classes for κ (6 for 0-5)
    """
    a = np.array(scores_a, dtype=float)
    b = np.array(scores_b, dtype=float)
    n = len(a)

    result = ReliabilityResult(comparison=comparison, n_samples=n)

    # Integer labels for κ
    a_int = np.clip(np.round(a).astype(int), 0, n_classes - 1)
    b_int = np.clip(np.round(b).astype(int), 0, n_classes - 1)

    # Cohen's κ
    result.qwk          = float(cohen_kappa_score(a_int, b_int, weights="quadratic"))
    result.linear_kappa = float(cohen_kappa_score(a_int, b_int, weights="linear"))
    result.kappa_interpretation = _kappa_interpretation(result.qwk)

    # Correlation
    if n >= 3:
        r, p = pearsonr(a, b)
        result.pearson_r = float(r)
        result.pearson_p = float(p)
        rho, _ = spearmanr(a, b)
        result.spearman_rho = float(rho)

    # ICC
    result.icc = icc_two_way_mixed(scores_a, scores_b)

    # Bland-Altman
    label_a, label_b = comparison.split(" vs ") if " vs " in comparison else ("A", "B")
    result.bland_altman = bland_altman(scores_a, scores_b, label_a.strip(), label_b.strip())

    # Agreement rates
    result.exact_agreement_pct = float(np.mean(a == b) * 100)
    result.adjacent_agreement_pct = float(np.mean(np.abs(a - b) <= 0.5) * 100)

    # Krippendorff's α (interval level for continuous scores)
    result.krippendorff_alpha = krippendorff_alpha(
        [scores_a, scores_b], level="interval"
    )

    return result


def full_reliability_study(
    human_r1: list[float],
    human_r2: list[float],
    system: list[float],
    question_ids: Optional[list[str]] = None,
    scale_max: float = 5.0,
) -> dict:
    """
    Complete inter-rater reliability study comparing system vs two human raters.

    Computes three comparisons:
    1. Rater1 vs Rater2  (human-human upper bound)
    2. System vs Rater1
    3. System vs Rater2
    4. System vs Human-Consensus (average of r1, r2)

    Also computes:
    - Three-way Krippendorff α
    - Per-question reliability breakdown

    Parameters
    ----------
    human_r1, human_r2 : Human rater scores (same length)
    system             : ConceptGrade predicted scores
    question_ids       : Per-sample question ID (for per-question breakdown)
    """
    consensus = [(r1 + r2) / 2.0 for r1, r2 in zip(human_r1, human_r2)]

    results = {
        "human_vs_human": compute_reliability(
            human_r1, human_r2, "Rater1 vs Rater2"
        ),
        "system_vs_r1": compute_reliability(
            system, human_r1, "ConceptGrade vs Rater1"
        ),
        "system_vs_r2": compute_reliability(
            system, human_r2, "ConceptGrade vs Rater2"
        ),
        "system_vs_consensus": compute_reliability(
            system, consensus, "ConceptGrade vs Human Consensus"
        ),
    }

    # Three-way Krippendorff α
    results["three_way_alpha"] = krippendorff_alpha(
        [human_r1, human_r2, system], level="interval"
    )

    # Percentage of system's QWK vs human-human QWK (theoretical ceiling)
    hh_qwk = results["human_vs_human"].qwk
    sys_qwk = results["system_vs_consensus"].qwk
    results["qwk_ceiling_pct"] = round(
        (sys_qwk / hh_qwk * 100) if hh_qwk > 0 else 0.0, 1
    )

    # Per-question breakdown
    if question_ids:
        per_q = {}
        unique_qs = sorted(set(question_ids))
        for qid in unique_qs:
            idx = [i for i, q in enumerate(question_ids) if q == qid]
            if len(idx) < 3:
                continue
            q_r1  = [human_r1[i] for i in idx]
            q_r2  = [human_r2[i] for i in idx]
            q_sys = [system[i]   for i in idx]
            q_cons = [(r1+r2)/2 for r1,r2 in zip(q_r1, q_r2)]
            r_hh, _ = pearsonr(q_r1, q_r2)
            r_sys, _ = pearsonr(q_sys, q_cons)
            per_q[qid] = {
                "n": len(idx),
                "human_human_r": round(float(r_hh), 4),
                "system_human_r": round(float(r_sys), 4),
                "delta_r": round(float(r_sys - r_hh), 4),
            }
        results["per_question"] = per_q

    return results


def format_reliability_table(study: dict) -> str:
    """Format the reliability study as a comparison table."""
    comps = ["human_vs_human", "system_vs_r1", "system_vs_r2", "system_vs_consensus"]
    labels = {
        "human_vs_human":       "Rater1 vs Rater2    (upper bound)",
        "system_vs_r1":         "ConceptGrade vs Rater1",
        "system_vs_r2":         "ConceptGrade vs Rater2",
        "system_vs_consensus":  "ConceptGrade vs Consensus",
    }

    header = (f"{'Comparison':<42}  {'QWK':>7}  {'κ(lin)':>7}  "
              f"{'α(Kripp)':>9}  {'ICC':>7}  {'r':>7}  {'Adj%':>6}")
    sep = "─" * 90
    rows = [header, sep]

    for key in comps:
        r = study[key]
        rows.append(
            f"  {labels[key]:<40}  {r.qwk:>7.4f}  {r.linear_kappa:>7.4f}  "
            f"{r.krippendorff_alpha:>9.4f}  {r.icc.get('icc', 0):>7.4f}  "
            f"{r.pearson_r:>7.4f}  {r.adjacent_agreement_pct:>5.1f}%"
        )

    rows.append(sep)
    rows.append(
        f"  Three-way Krippendorff α: {study['three_way_alpha']:.4f}  |  "
        f"System QWK as % of ceiling: {study['qwk_ceiling_pct']:.1f}%"
    )
    return "\n".join(rows)


def generate_reliability_latex(study: dict) -> str:
    """Generate a LaTeX table for the reliability study."""
    lines = [
        "% Inter-Rater Reliability — ConceptGrade vs Human Raters",
        "\\begin{table}[h]",
        "\\centering",
        "\\caption{Inter-rater reliability on the Mohler dataset. "
        "QWK = Quadratic Weighted Kappa; $\\alpha$ = Krippendorff's $\\alpha$; "
        "ICC = Intraclass Correlation Coefficient (two-way mixed); "
        "Adj\\% = percentage of scores within $\\pm0.5$. "
        "Human-Human serves as the theoretical ceiling.}",
        "\\label{tab:reliability}",
        "\\begin{tabular}{@{}lrrrrr@{}}",
        "\\toprule",
        "\\textbf{Comparison} & \\textbf{QWK} & \\textbf{$\\kappa$} & "
        "\\textbf{$\\alpha$} & \\textbf{ICC} & \\textbf{Adj\\%} \\\\",
        "\\midrule",
        "\\textit{Human-Human (ceiling)} & "
        f"{study['human_vs_human'].qwk:.3f} & "
        f"{study['human_vs_human'].linear_kappa:.3f} & "
        f"{study['human_vs_human'].krippendorff_alpha:.3f} & "
        f"{study['human_vs_human'].icc.get('icc',0):.3f} & "
        f"{study['human_vs_human'].adjacent_agreement_pct:.1f}\\% \\\\",
        "\\midrule",
    ]
    for key, label in [
        ("system_vs_r1",        "ConceptGrade vs Rater 1"),
        ("system_vs_r2",        "ConceptGrade vs Rater 2"),
        ("system_vs_consensus", "ConceptGrade vs Consensus"),
    ]:
        r = study[key]
        lines.append(
            f"{label} & {r.qwk:.3f} & {r.linear_kappa:.3f} & "
            f"{r.krippendorff_alpha:.3f} & {r.icc.get('icc',0):.3f} & "
            f"{r.adjacent_agreement_pct:.1f}\\% \\\\"
        )
    lines += [
        "\\bottomrule",
        "\\multicolumn{6}{l}{\\footnotesize Three-way $\\alpha$ = "
        f"{study['three_way_alpha']:.3f}; "
        f"System QWK as \\%% of ceiling = {study['qwk_ceiling_pct']:.1f}\\%}} \\\\",
        "\\end{tabular}",
        "\\end{table}",
    ]
    return "\n".join(lines)
