#!/usr/bin/env python3
"""
analyze_study_results.py — Post-study analysis for ConceptGrade IEEE VIS 2027

Runs ALL pre-registered statistical tests against real or synthetic data.

Usage:
  # Real data (after study is complete):
  python analyze_study_results.py

  # Synthetic dry-run (before any participants):
  python analyze_study_results.py --synthetic

  # Specify a custom log directory:
  python analyze_study_results.py --log-dir path/to/study_logs

Pre-registered hypotheses:
  H1  (Causal Attribution)   Condition B > A on CA think-aloud codes (Poisson GLM)
  H2  (Semantic Alignment)   Condition B > A on SA rubric edits (Mann-Whitney U)
  H3  (Trust Calibration)    Condition B > A on TC ordinal scores (Mann-Whitney U)
  H-DT1  dwell_time_ms ↑ when chain_pct ↓  (Spearman ρ, Condition B only)
  H-DT2  dwell_time_ms ↑ correlates with CA code frequency (Spearman ρ)
  H-DT3  dwell gap B−A largest for SOLO 3–4 answers (Mann-Whitney U per SOLO band)
  SUS    Condition B SUS score > Condition A (independent-samples t-test, Cohen's d)
  Task   Condition B task accuracy > A (Poisson or GEE logistic — simplified here)

Output:
  data/study_analysis_results.json   — machine-readable results
  (stdout)                           — human-readable report
"""

import argparse
import json
import os
import random
import math
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

# ── Paths ──────────────────────────────────────────────────────────────────────

BASE_DIR     = Path(__file__).parent
LOGS_DIR     = BASE_DIR / "data" / "study_logs"
TRM_CACHE    = BASE_DIR / "data" / "digiklausur_trm_cache.json"
OUTPUT_FILE  = BASE_DIR / "data" / "study_analysis_results.json"

# ── Synthetic data generator ───────────────────────────────────────────────────

def generate_synthetic_sessions(n_per_condition: int = 15, seed: int = 42) -> list[dict]:
    """
    Generate N synthetic participant sessions (15 per condition) that approximate
    the expected effect sizes based on the literature and pilot estimates.

    Expected effects (from analysis plan):
      CA codes: Condition B IRR ≈ 3.8× over A
      SA codes: Condition B ~3×  over A
      TC score: Condition B Mdn≈3, A Mdn≈2
      SUS:      Condition B M≈72.5, A M≈58.2
      dwell:    Spearman ρ ≈ −0.35 (low chain_pct → longer dwell in B)
    """
    rng = random.Random(seed)
    np.random.seed(seed)

    sessions = []
    conditions = ['A'] * n_per_condition + ['B'] * n_per_condition

    # Representative concept/answer pairs from DigiKlausur (synthetic IDs)
    CONCEPTS   = ['backpropagation', 'gradient_descent', 'loss_landscape', 'optimisation', 'regularisation']
    SEVERITIES = ['critical', 'moderate', 'minor', 'matched']
    SOLOS      = ['1', '2', '3', '4']

    for pid, cond in enumerate(conditions):
        is_B = cond == 'B'
        session_id = f"synthetic_{cond}_{pid:02d}"

        # ── Think-aloud qualitative codes ─────────────────────────────────────
        # CA: ~Poisson(λ=1.2) for A, Poisson(λ=4.5) for B (IRR ≈ 3.8×)
        ca_count = np.random.poisson(4.5 if is_B else 1.2)
        # SA: ~Poisson(λ=0.8) for A, Poisson(λ=2.4) for B
        sa_count = np.random.poisson(2.4 if is_B else 0.8)
        # TC: ordinal 0–4, ~Normal(μ=3,σ=0.8) for B, (μ=2,σ=0.9) for A → clamp
        tc_score = int(np.clip(round(np.random.normal(3.0 if is_B else 2.0, 0.8)), 0, 4))

        # ── SUS score ─────────────────────────────────────────────────────────
        sus = float(np.clip(np.random.normal(72.5 if is_B else 58.2,
                                              15.0 if is_B else 19.0), 0, 100))

        # ── Task accuracy (binary: did they identify the top-misconception concept?) ──
        task_correct = rng.random() < (0.73 if is_B else 0.47)

        # ── Dwell-time events (Condition B: ~8–12 answers viewed; A: ~3–5) ───
        n_answers = rng.randint(8, 13) if is_B else rng.randint(3, 6)
        dwell_events = []

        # Strategic benchmark seeds (mirrors benchmark_seeds.json).
        # In synthetic mode, inject 1–2 seeded answers per participant to
        # exercise the benchmark trap analysis without needing real JSONL logs.
        BENCHMARK_SEEDS = {
            '0': 'fluent_hallucination',  '9': 'fluent_hallucination',
            '276': 'unorthodox_genius',   '269': 'unorthodox_genius',
            '484': 'lexical_bluffer',     '505': 'lexical_bluffer',
            '32': 'partial_credit_needle','558': 'partial_credit_needle',
        }
        # Each participant naturally encounters 1–2 seeded answers (probability ~25%)
        seeded_candidate_ids = rng.sample(list(BENCHMARK_SEEDS.keys()), k=min(2, len(BENCHMARK_SEEDS)))

        for i in range(n_answers):
            concept   = rng.choice(CONCEPTS)
            severity  = rng.choice(SEVERITIES)
            solo      = rng.choice(SOLOS)
            # chain_pct: continuous 0–100 (string "45%" format from frontend)
            chain_pct_val = rng.uniform(5, 95)
            chain_pct_str = f"{chain_pct_val:.0f}%"

            # Inject seeded answer for the first 1–2 slots (if this participant encounters them)
            if i < len(seeded_candidate_ids) and rng.random() < 0.25:
                ans_id = seeded_candidate_ids[i]
                benchmark_case = BENCHMARK_SEEDS[ans_id]
            else:
                ans_id = str(rng.randint(1, 300))
                benchmark_case = None

            # H-DT1: dwell time negatively correlated with chain_pct in B
            # Additional effect: Condition B dwells longer on seeded trap answers
            if is_B:
                # low chain_pct → long dwell (ρ ≈ −0.35)
                base_dwell = 60000 - 400 * chain_pct_val + np.random.normal(0, 8000)
                if benchmark_case is not None:
                    # Trap cases elicit ~40% longer dwell in Condition B (trace inspection)
                    base_dwell *= 1.4
            else:
                base_dwell = np.random.normal(20000, 6000)  # A: quick glance

            dwell_ms = max(2500, int(base_dwell))  # enforce >2s bounce filter

            dwell_events.append({
                "student_answer_id": ans_id,
                "concept_id": concept,
                "severity": severity,
                "chain_pct": chain_pct_str,
                "solo_level": solo,
                "bloom_level": rng.choice(["remember", "understand", "apply", "analyse"]),
                "dwell_time_ms": dwell_ms,
                "capture_method": "beacon",
                "trace_panel_open": rng.random() < (0.3 if is_B else 0.0),
                "kg_panel_open": rng.random() < (0.4 if is_B else 0.0),
                # benchmark_case: None for ordinary answers; trap type for the 8 seeds.
                # Mirroring the frontend getBenchmarkCase() injection in StudentAnswerPanel.
                "benchmark_case": benchmark_case,
            })

        sessions.append({
            "session_id":   session_id,
            "condition":    cond,
            "dataset":      "digiklausur",
            # Qualitative codes (would come from transcript coding in real study)
            "ca_count":     int(ca_count),
            "sa_count":     int(sa_count),
            "tc_score":     tc_score,
            # Usability
            "sus_score":    round(sus, 1),
            # Task
            "task_correct": task_correct,
            # Per-answer dwell events
            "dwell_events": dwell_events,
        })

    return sessions


# ── Event log loader ───────────────────────────────────────────────────────────

def load_real_sessions(logs_dir: Path) -> list[dict]:
    """
    Aggregate real JSONL event logs into the same format as synthetic sessions.
    Requires:
      - JSONL files with session_id, condition, event_type, payload
      - A separate qualitative_codes.json with {session_id: {ca_count, sa_count, tc_score}}
        (populated after transcript coding with inter-rater reliability κ ≥ 0.70)

    If qualitative_codes.json is missing, qualitative analyses are skipped.
    """
    sessions_raw: dict[str, dict] = {}

    for jsonl_path in logs_dir.glob("*.jsonl"):
        if jsonl_path.name.startswith("test_"):
            continue  # skip dry-run files
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                sid = event.get("session_id", "unknown")
                if sid not in sessions_raw:
                    sessions_raw[sid] = {
                        "session_id": sid,
                        "condition": event.get("condition", "?"),
                        "dataset":   event.get("dataset", "?"),
                        "dwell_events": [],
                        "sus_score": None,
                        "task_correct": None,
                        "ca_count": None,
                        "sa_count": None,
                        "tc_score": None,
                    }

                etype   = event.get("event_type")
                payload = event.get("payload", {})

                if etype == "answer_view_end":
                    sessions_raw[sid]["dwell_events"].append(payload)

                if etype == "task_submit":
                    # task_correct needs to be scored post-hoc by researcher
                    # placeholder: store the raw answer for later
                    sessions_raw[sid]["task_answer"] = payload.get("answer", "")

    # Merge qualitative codes if available
    codes_path = logs_dir / "qualitative_codes.json"
    if codes_path.exists():
        with open(codes_path) as f:
            codes = json.load(f)
        for sid, s in sessions_raw.items():
            if sid in codes:
                s.update(codes[sid])

    # Merge SUS scores if available
    sus_path = logs_dir / "sus_scores.json"
    if sus_path.exists():
        with open(sus_path) as f:
            sus_data = json.load(f)
        for sid, s in sessions_raw.items():
            if sid in sus_data:
                s["sus_score"] = sus_data[sid]

    return list(sessions_raw.values())


# ── Analysis helpers ───────────────────────────────────────────────────────────

def cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d for two independent groups."""
    n_a, n_b = len(a), len(b)
    pooled_std = math.sqrt(((n_a - 1) * a.std(ddof=1)**2 + (n_b - 1) * b.std(ddof=1)**2)
                           / (n_a + n_b - 2))
    return float((b.mean() - a.mean()) / pooled_std) if pooled_std > 0 else 0.0


def chain_pct_numeric(s: str) -> float:
    """Convert '45%' → 45.0; handle raw float strings too."""
    try:
        return float(str(s).replace('%', '').strip())
    except (ValueError, AttributeError):
        return float('nan')


def summarise(arr: np.ndarray, label: str) -> dict:
    return {
        "label": label, "n": int(len(arr)),
        "mean": round(float(arr.mean()), 3),
        "sd":   round(float(arr.std(ddof=1)), 3),
        "median": round(float(np.median(arr)), 3),
        "min":  round(float(arr.min()), 3),
        "max":  round(float(arr.max()), 3),
    }


# ── Main analysis ──────────────────────────────────────────────────────────────

def run_analysis(sessions: list[dict]) -> dict:
    results = {"timestamp": datetime.now().isoformat(), "tests": {}}

    df = pd.DataFrame(sessions)
    cond_A = df[df.condition == 'A']
    cond_B = df[df.condition == 'B']
    n_A, n_B = len(cond_A), len(cond_B)

    print(f"\n{'='*60}")
    print(f"  ConceptGrade VIS 2027 — Study Analysis Report")
    print(f"  Generated: {results['timestamp']}")
    print(f"  N = {len(df)} ({n_A} Condition A, {n_B} Condition B)")
    print(f"{'='*60}")

    # ── H1: Causal Attribution (CA) — Poisson GLM (simplified as Mann-Whitney) ──
    if df.ca_count.notna().any():
        ca_A = cond_A.ca_count.dropna().values.astype(float)
        ca_B = cond_B.ca_count.dropna().values.astype(float)
        stat, p = stats.mannwhitneyu(ca_B, ca_A, alternative='greater')
        irr = ca_B.mean() / ca_A.mean() if ca_A.mean() > 0 else float('nan')
        results["tests"]["H1_causal_attribution"] = {
            "test": "Mann-Whitney U (one-sided B > A)",
            "statistic": round(float(stat), 3), "p_value": round(float(p), 4),
            "significant": bool(p < 0.05),
            "IRR_estimate": round(irr, 2),
            "condition_A": summarise(ca_A, "Condition A"),
            "condition_B": summarise(ca_B, "Condition B"),
        }
        sig = "✅ SIGNIFICANT" if p < 0.05 else "❌ not significant"
        print(f"\n[H1] Causal Attribution (CA codes)")
        print(f"     A: M={ca_A.mean():.2f}  B: M={ca_B.mean():.2f}  IRR={irr:.2f}×")
        print(f"     Mann-Whitney U={stat:.1f}, p={p:.4f}  {sig}")

    # ── H2: Semantic Alignment (SA) — Mann-Whitney U ──────────────────────────
    if df.sa_count.notna().any():
        sa_A = cond_A.sa_count.dropna().values.astype(float)
        sa_B = cond_B.sa_count.dropna().values.astype(float)
        stat, p = stats.mannwhitneyu(sa_B, sa_A, alternative='greater')
        results["tests"]["H2_semantic_alignment"] = {
            "test": "Mann-Whitney U (one-sided B > A)",
            "statistic": round(float(stat), 3), "p_value": round(float(p), 4),
            "significant": bool(p < 0.05),
            "condition_A": summarise(sa_A, "Condition A"),
            "condition_B": summarise(sa_B, "Condition B"),
        }
        sig = "✅ SIGNIFICANT" if p < 0.05 else "❌ not significant"
        print(f"\n[H2] Semantic Alignment (SA rubric edits)")
        print(f"     A: M={sa_A.mean():.2f}  B: M={sa_B.mean():.2f}")
        print(f"     Mann-Whitney U={stat:.1f}, p={p:.4f}  {sig}")

    # ── H3: Trust Calibration (TC) — Mann-Whitney U (ordinal) ─────────────────
    if df.tc_score.notna().any():
        tc_A = cond_A.tc_score.dropna().values.astype(float)
        tc_B = cond_B.tc_score.dropna().values.astype(float)
        stat, p = stats.mannwhitneyu(tc_B, tc_A, alternative='greater')
        results["tests"]["H3_trust_calibration"] = {
            "test": "Mann-Whitney U (one-sided B > A)",
            "statistic": round(float(stat), 3), "p_value": round(float(p), 4),
            "significant": bool(p < 0.05),
            "condition_A": summarise(tc_A, "Condition A"),
            "condition_B": summarise(tc_B, "Condition B"),
        }
        sig = "✅ SIGNIFICANT" if p < 0.05 else "❌ not significant"
        print(f"\n[H3] Trust Calibration (TC ordinal 0–4)")
        print(f"     A: Mdn={np.median(tc_A):.1f}  B: Mdn={np.median(tc_B):.1f}")
        print(f"     Mann-Whitney U={stat:.1f}, p={p:.4f}  {sig}")

    # ── SUS: Usability — independent t-test + Cohen's d ───────────────────────
    if df.sus_score.notna().any():
        sus_A = cond_A.sus_score.dropna().values.astype(float)
        sus_B = cond_B.sus_score.dropna().values.astype(float)
        t_stat, p = stats.ttest_ind(sus_B, sus_A, alternative='greater')
        d = cohen_d(sus_A, sus_B)
        results["tests"]["SUS_usability"] = {
            "test": "Independent t-test (one-sided B > A)",
            "t_statistic": round(float(t_stat), 3), "p_value": round(float(p), 4),
            "cohen_d": round(d, 3), "significant": bool(p < 0.05),
            "condition_A": summarise(sus_A, "Condition A"),
            "condition_B": summarise(sus_B, "Condition B"),
        }
        sig = "✅ SIGNIFICANT" if p < 0.05 else "❌ not significant"
        print(f"\n[SUS] System Usability Scale")
        print(f"      A: M={sus_A.mean():.1f} (SD={sus_A.std(ddof=1):.1f})  B: M={sus_B.mean():.1f} (SD={sus_B.std(ddof=1):.1f})")
        print(f"      t={t_stat:.3f}, p={p:.4f}, Cohen's d={d:.3f}  {sig}")

    # ── Task accuracy — chi-square (or Fisher's exact for small N) ─────────────
    if df.task_correct.notna().any():
        a_correct = int(cond_A.task_correct.dropna().sum())
        b_correct = int(cond_B.task_correct.dropna().sum())
        a_total   = int(cond_A.task_correct.dropna().count())
        b_total   = int(cond_B.task_correct.dropna().count())
        table = [[b_correct, b_total - b_correct], [a_correct, a_total - a_correct]]
        _, p, _, _ = stats.chi2_contingency(table, correction=True)
        results["tests"]["task_accuracy"] = {
            "test": "Chi-square with Yates correction",
            "p_value": round(float(p), 4), "significant": bool(p < 0.05),
            "condition_A": {"correct": a_correct, "total": a_total, "pct": round(100*a_correct/a_total, 1)},
            "condition_B": {"correct": b_correct, "total": b_total, "pct": round(100*b_correct/b_total, 1)},
        }
        sig = "✅ SIGNIFICANT" if p < 0.05 else "❌ not significant"
        print(f"\n[Task] Task accuracy (correct concept identification)")
        print(f"       A: {a_correct}/{a_total} ({100*a_correct/a_total:.1f}%)  B: {b_correct}/{b_total} ({100*b_correct/b_total:.1f}%)")
        print(f"       χ²(Yates), p={p:.4f}  {sig}")

    # ── H-DT1: Dwell time vs chain_pct — Spearman ρ (Condition B only) ────────
    print(f"\n{'─'*60}")
    print(f"  Dwell Time Analyses (pre-registered H-DT1 / H-DT2 / H-DT3)")
    print(f"{'─'*60}")

    # Flatten dwell events from Condition B
    dwell_rows = []
    for _, row in df.iterrows():
        for ev in (row.dwell_events or []):
            cp_num = chain_pct_numeric(ev.get("chain_pct", "nan"))
            dwell_ms = ev.get("dwell_time_ms")
            if dwell_ms is None or dwell_ms < 2000:
                continue   # bounce filter
            dwell_rows.append({
                "session_id": row.session_id,
                "condition":  row.condition,
                "student_answer_id": ev.get("student_answer_id"),
                "concept_id": ev.get("concept_id"),
                "chain_pct":  cp_num,
                "solo_level": ev.get("solo_level"),
                "dwell_ms":   int(dwell_ms),
                "trace_open": bool(ev.get("trace_panel_open", False)),
                "kg_open":    bool(ev.get("kg_panel_open", False)),
                # Strategic seeding field — present only for the 8 benchmark trap cases.
                # undefined/absent for all other answers; analyst filters on non-null.
                "benchmark_case": ev.get("benchmark_case"),   # str | None
            })

    DWELL_COLS = ["session_id", "condition", "student_answer_id", "concept_id",
                  "chain_pct", "solo_level", "dwell_ms", "trace_open", "kg_open",
                  "benchmark_case"]
    dwell_df = pd.DataFrame(dwell_rows, columns=DWELL_COLS) if dwell_rows else pd.DataFrame(columns=DWELL_COLS)
    n_A_dwell = int((dwell_df.condition == 'A').sum())
    n_B_dwell = int((dwell_df.condition == 'B').sum())
    results["tests"]["dwell_summary"] = {
        "total_events": len(dwell_df),
        "condition_A_events": n_A_dwell,
        "condition_B_events": n_B_dwell,
        "bounce_filtered": "< 2000ms excluded",
    }
    print(f"\n  Dwell events: {len(dwell_df)} total (A={n_A_dwell}, B={n_B_dwell})")

    if len(dwell_df) >= 10:
        # H-DT1: low chain_pct → longer dwell in Condition B
        dwell_B = dwell_df[dwell_df.condition == 'B']
        if len(dwell_B) >= 5:
            rho, p = stats.spearmanr(dwell_B.chain_pct, dwell_B.dwell_ms)
            results["tests"]["H_DT1_dwell_vs_chain_pct"] = {
                "test": "Spearman ρ (Condition B only)",
                "rho": round(float(rho), 3), "p_value": round(float(p), 4),
                "significant": bool(p < 0.05), "n": len(dwell_B),
                "direction": "negative (expected: low coverage → longer dwell)",
            }
            sig = "✅ SIGNIFICANT" if p < 0.05 else "❌ not significant"
            dirn = "↓ as expected" if rho < 0 else "↑ unexpected"
            print(f"\n[H-DT1] Dwell time vs KG chain coverage (Cond B, n={len(dwell_B)})")
            print(f"        Spearman ρ={rho:.3f} ({dirn}), p={p:.4f}  {sig}")

        # H-DT2: dwell_ms correlated with CA code count across all participants
        # Aggregate: per-participant mean dwell vs CA count
        if df.ca_count.notna().any():
            dwell_per_p = dwell_df.groupby("session_id")["dwell_ms"].mean().reset_index()
            dwell_per_p.columns = ["session_id", "mean_dwell"]
            merged = df[["session_id", "ca_count"]].merge(dwell_per_p, on="session_id")
            merged = merged.dropna()
            if len(merged) >= 5:
                rho2, p2 = stats.spearmanr(merged.mean_dwell, merged.ca_count)
                results["tests"]["H_DT2_dwell_vs_ca"] = {
                    "test": "Spearman ρ (mean dwell per participant vs CA count)",
                    "rho": round(float(rho2), 3), "p_value": round(float(p2), 4),
                    "significant": bool(p2 < 0.05), "n": len(merged),
                }
                sig = "✅ SIGNIFICANT" if p2 < 0.05 else "❌ not significant"
                print(f"\n[H-DT2] Mean dwell vs CA code count (all conditions, n={len(merged)})")
                print(f"        Spearman ρ={rho2:.3f}, p={p2:.4f}  {sig}")

        # H-DT3: dwell gap B−A largest for SOLO 3–4 (partial credit zone)
        dwell_solo = dwell_df.groupby(["condition", "solo_level"])["dwell_ms"].median().unstack(level=0)
        dwell_solo.columns.name = None
        if "A" in dwell_solo.columns and "B" in dwell_solo.columns:
            dwell_solo["B_minus_A"] = dwell_solo["B"] - dwell_solo["A"]
            solo_results = {}
            for solo in sorted(dwell_solo.index):
                gap = dwell_solo.loc[solo, "B_minus_A"] if solo in dwell_solo.index else float('nan')
                # Mann-Whitney U per SOLO band
                band_A = dwell_df[(dwell_df.condition == 'A') & (dwell_df.solo_level == str(solo))].dwell_ms.values
                band_B = dwell_df[(dwell_df.condition == 'B') & (dwell_df.solo_level == str(solo))].dwell_ms.values
                if len(band_A) >= 3 and len(band_B) >= 3:
                    u_stat, p_u = stats.mannwhitneyu(band_B, band_A, alternative='greater')
                    solo_results[str(solo)] = {
                        "median_A": round(float(np.median(band_A)), 0),
                        "median_B": round(float(np.median(band_B)), 0),
                        "gap_B_minus_A": round(float(gap), 0) if not math.isnan(gap) else None,
                        "mann_whitney_p": round(float(p_u), 4), "n_A": len(band_A), "n_B": len(band_B),
                    }
            results["tests"]["H_DT3_dwell_by_solo"] = {
                "test": "Median dwell gap (B−A) by SOLO level; Mann-Whitney U per band",
                "solo_bands": solo_results,
            }
            print(f"\n[H-DT3] Dwell gap (B−A) by SOLO level:")
            for solo, r in solo_results.items():
                sig = "*" if r["mann_whitney_p"] < 0.05 else " "
                print(f"        SOLO {solo}: A={r['median_A']:.0f}ms  B={r['median_B']:.0f}ms  "
                      f"Δ={r['gap_B_minus_A']:.0f}ms  p={r['mann_whitney_p']:.4f}{sig}")

    # ── Benchmark trap-type analysis ──────────────────────────────────────────
    #
    # For each of the 4 pedagogical trap types, compare dwell time (B vs A) on
    # seeded answers.  "Catching" the trap = dwelling on it longer than the median
    # of non-seeded answers in the same condition.
    #
    # Seeded IDs (benchmark_seeds.json):
    #   fluent_hallucination:    0, 9
    #   unorthodox_genius:       276, 269
    #   lexical_bluffer:         484, 505
    #   partial_credit_needle:   32, 558
    #
    # Primary metrics per trap type (per AGENT_EVALUATION_GUIDE §3.2):
    #   fluent_hallucination  — mean dwell B > A (did B inspect the trace leap?)
    #   unorthodox_genius     — proportion who dwelling > 2× median (automation bias)
    #   lexical_bluffer       — mean dwell B > A (did B spot CONTRADICTS chips?)
    #   partial_credit_needle — mean dwell B > A (time-to-insight via KG subgraph)
    print(f"\n{'─'*60}")
    print(f"  Benchmark Trap-Type Analysis (pre-registered, n=8 seeded answers)")
    print(f"{'─'*60}")

    TRAP_TYPES = [
        "fluent_hallucination",
        "unorthodox_genius",
        "lexical_bluffer",
        "partial_credit_needle",
    ]
    benchmark_results: dict[str, dict] = {}

    seeded_dwell = dwell_df[dwell_df["benchmark_case"].notna()] if len(dwell_df) > 0 else dwell_df
    non_seeded_dwell = dwell_df[dwell_df["benchmark_case"].isna()] if len(dwell_df) > 0 else dwell_df

    for trap in TRAP_TYPES:
        trap_df = seeded_dwell[seeded_dwell["benchmark_case"] == trap] if len(seeded_dwell) > 0 else seeded_dwell
        trap_A = trap_df[trap_df["condition"] == "A"]["dwell_ms"].values
        trap_B = trap_df[trap_df["condition"] == "B"]["dwell_ms"].values

        entry: dict = {
            "trap_type": trap,
            "n_events_A": int(len(trap_A)),
            "n_events_B": int(len(trap_B)),
        }

        if len(trap_A) >= 2 and len(trap_B) >= 2:
            u_stat, p_u = stats.mannwhitneyu(trap_B, trap_A, alternative="greater")
            entry.update({
                "test": "Mann-Whitney U (one-sided B > A)",
                "mean_dwell_A_ms": round(float(np.mean(trap_A)), 0),
                "mean_dwell_B_ms": round(float(np.mean(trap_B)), 0),
                "gap_B_minus_A_ms": round(float(np.mean(trap_B) - np.mean(trap_A)), 0),
                "statistic": round(float(u_stat), 3),
                "p_value": round(float(p_u), 4),
                "significant": bool(p_u < 0.05),
            })
            sig = "✅" if p_u < 0.05 else "❌"
            print(f"\n  [{trap}]  n_A={len(trap_A)} n_B={len(trap_B)}")
            print(f"    Mean dwell  A={np.mean(trap_A):.0f}ms  B={np.mean(trap_B):.0f}ms  "
                  f"Δ={np.mean(trap_B)-np.mean(trap_A):.0f}ms  "
                  f"p={p_u:.4f}  {sig}")
        else:
            entry["note"] = "insufficient events for Mann-Whitney U (< 2 per condition)"
            print(f"\n  [{trap}]  insufficient data (A={len(trap_A)}, B={len(trap_B)})")

        benchmark_results[trap] = entry

    # Overall seeded vs non-seeded dwell comparison (does Condition B slow down for traps?)
    if len(seeded_dwell) >= 4 and len(non_seeded_dwell) >= 4:
        seed_B   = seeded_dwell[seeded_dwell["condition"] == "B"]["dwell_ms"].values
        unseed_B = non_seeded_dwell[non_seeded_dwell["condition"] == "B"]["dwell_ms"].values
        if len(seed_B) >= 2 and len(unseed_B) >= 2:
            u2, p2 = stats.mannwhitneyu(seed_B, unseed_B, alternative="greater")
            benchmark_results["seeded_vs_nonseeded_B"] = {
                "test": "Mann-Whitney U (seeded > non-seeded, Condition B only)",
                "mean_seeded_ms": round(float(np.mean(seed_B)), 0),
                "mean_nonseeded_ms": round(float(np.mean(unseed_B)), 0),
                "statistic": round(float(u2), 3),
                "p_value": round(float(p2), 4),
                "significant": bool(p2 < 0.05),
            }
            sig = "✅" if p2 < 0.05 else "❌"
            print(f"\n  [Seeded vs non-seeded, Cond B]  "
                  f"seeded={np.mean(seed_B):.0f}ms  non={np.mean(unseed_B):.0f}ms  p={p2:.4f}  {sig}")

    results["tests"]["benchmark_trap_analysis"] = benchmark_results

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    sig_tests = [(k, v) for k, v in results["tests"].items() if isinstance(v, dict) and "significant" in v]
    for key, test in sig_tests:
        symbol = "✅" if test["significant"] else "❌"
        p_str  = f"p={test.get('p_value', '?'):.4f}" if isinstance(test.get('p_value'), float) else ""
        print(f"  {symbol} {key:40s} {p_str}")

    return results


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ConceptGrade VIS 2027 study analysis")
    parser.add_argument("--synthetic", action="store_true",
                        help="Use synthetic data (dry-run; does not read JSONL files)")
    parser.add_argument("--log-dir", type=Path, default=LOGS_DIR,
                        help="Directory containing per-session JSONL files")
    parser.add_argument("--n-per-condition", type=int, default=15,
                        help="N per condition for synthetic data (default: 15)")
    args = parser.parse_args()

    if args.synthetic:
        print("⚠  SYNTHETIC DRY-RUN — using generated data, not real participant logs")
        sessions = generate_synthetic_sessions(n_per_condition=args.n_per_condition)
    else:
        print(f"Loading real sessions from: {args.log_dir}")
        sessions = load_real_sessions(args.log_dir)
        if not sessions:
            print("No real sessions found. Run with --synthetic for a dry-run.")
            return
        has_codes = any(s.get("ca_count") is not None for s in sessions)
        if not has_codes:
            print("⚠  qualitative_codes.json not found — H1/H2/H3 analyses will be skipped.")
            print("   After transcript coding, create:")
            print("   data/study_logs/qualitative_codes.json: {session_id: {ca_count, sa_count, tc_score}}")

    results = run_analysis(sessions)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅  Results saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
