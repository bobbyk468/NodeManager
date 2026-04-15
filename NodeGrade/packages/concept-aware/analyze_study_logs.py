"""
Study Log Analyzer — IEEE VIS 2027 user study results.

Reads per-session JSONL files from data/study_logs/ and computes:
  - Time-on-task per condition (A = summary-only, B = full dashboard)
  - SUS score per participant and per condition
  - Chart interaction counts per condition (breadth of exploration)
  - Task answer submission rate per condition
  - Rubric edit causal attribution (multi-window: 15 s / 30 s / 60 s, pre-registered)
  - Concept alignment rate — exact ID match + semantic fuzzy match
  - Hypergeometric p-value for semantic alignment (null = chance alignment)
  - Panel focus ordering (panel opened before vs after first trace interaction)

Usage
-----
  python analyze_study_logs.py                    # reads data/study_logs/*.jsonl
  python analyze_study_logs.py --logs-dir PATH    # custom directory
  python analyze_study_logs.py --csv              # also write results/study_results.csv

Output
------
  Console: formatted summary table per condition
  Optional CSV: results/study_analysis.csv (one row per session)

Expected event schema (from studyLogger.ts)
-------------------------------------------
{
  "session_id": "...",
  "condition": "A" | "B",
  "dataset": "mohler" | "digiklausur" | ...,
  "event_type": "page_view" | "tab_change" | "task_start" | "task_submit" | "chart_hover"
              | "trace_interact" | "rubric_edit",
  "timestamp_ms": 1713000000000,
  "elapsed_ms": 123456,
  "payload": {
    // rubric_edit: edit_type, concept_id, concept_label,
    //   within_15s, within_30s, within_60s,
    //   time_since_last_contradicts_ms, source_contradicts_nodes_60s,
    //   concept_in_contradicts_exact, concept_in_contradicts_semantic,
    //   semantic_match_score, semantic_match_node, session_contradicts_nodes,
    //   panel_focus_ms, panel_focus_before_trace, interaction_source,
    //   trace_gap_count (v7+: # structural leaps in most recent LRM trace)
    // task_submit (main_task):  answer, confidence, time_to_answer_ms, event_subtype
    // task_submit (sus):        sus_responses, sus_score, sus_instrument, event_subtype
    // chart_hover:              viz_id
  }
}
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional

DATA_DIR    = Path(__file__).parent / 'data'
LOGS_DIR    = DATA_DIR / 'study_logs'
RESULTS_DIR = Path(__file__).parent / 'results'


# ── Hypergeometric p-value ─────────────────────────────────────────────────────

def _hypergeometric_p(k: int, N: int, K: int, n: int) -> Optional[float]:
    """
    One-tailed hypergeometric p-value: P(X >= k) under the null that educators
    edit concepts uniformly at random from a rubric of size N, where K concepts
    were flagged by the LRM as CONTRADICTS.

    Parameters
    ----------
    k : observed number of edits that matched a CONTRADICTS concept
    N : rubric size (total number of concepts available to edit)
    K : number of CONTRADICTS-flagged concepts in the rubric
    n : total number of rubric edits made

    This is the null model used in the paper for H2 (semantic alignment).
    """
    try:
        from scipy.stats import hypergeom
        K = min(K, N)
        n = min(n, N)
        # P(X >= k) = 1 - CDF(k-1)
        p = float(1 - hypergeom.cdf(k - 1, N, K, n))
        return round(p, 4)
    except Exception:
        return None


# ── Load events from JSONL files ───────────────────────────────────────────────

def load_all_sessions(logs_dir: Path) -> dict[str, list[dict]]:
    """
    Returns {session_id: [events sorted by timestamp_ms]}.
    One file per session; each line is a JSON event object.
    """
    sessions: dict[str, list[dict]] = defaultdict(list)

    if not logs_dir.exists():
        return {}

    for filepath in sorted(logs_dir.glob('*.jsonl')):
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    sid = event.get('session_id', filepath.stem)
                    sessions[sid].append(event)
                except json.JSONDecodeError:
                    continue

    # Sort each session by timestamp
    for sid in sessions:
        sessions[sid].sort(key=lambda e: e.get('timestamp_ms', 0))

    return dict(sessions)


# ── Per-session metrics ────────────────────────────────────────────────────────

def analyse_session(events: list[dict]) -> dict:
    """Compute scalar metrics for a single participant session."""
    if not events:
        return {}

    condition  = events[0].get('condition', '?')
    session_id = events[0].get('session_id', '?')

    # Timestamps
    first_ts = events[0].get('timestamp_ms', 0)
    last_ts  = events[-1].get('timestamp_ms', first_ts)
    total_session_ms = last_ts - first_ts

    # Time-on-task: page_view → task_submit (first main task)
    page_view_ts: Optional[int] = None
    task_start_ts: Optional[int] = None
    task_submit_ts: Optional[int] = None
    sus_score: Optional[int] = None
    confidence: Optional[int] = None
    answer_length: int = 0
    chart_hovers: list[str] = []
    unique_viz_ids: set[str] = set()
    tab_changes: int = 0
    datasets_visited: set[str] = set()

    # Rubric edit tracking (Condition B only)
    rubric_edits: list[dict] = []
    trace_interactions: list[dict] = []

    for ev in events:
        etype   = ev.get('event_type', '')
        payload = ev.get('payload', {}) or {}
        ts      = ev.get('timestamp_ms', 0)
        ds      = ev.get('dataset', '')

        if etype == 'page_view':
            page_view_ts = ts

        elif etype == 'task_start':
            if task_start_ts is None:
                task_start_ts = ts

        elif etype == 'task_submit':
            sub = payload.get('event_subtype', '')
            if sub == 'main_task' and task_submit_ts is None:
                task_submit_ts  = ts
                confidence       = payload.get('confidence')
                ans              = payload.get('answer', '')
                answer_length    = len(str(ans).split()) if ans else 0
            elif sub == 'sus_questionnaire':
                sus_score = payload.get('sus_score')

        elif etype == 'chart_hover':
            viz_id = payload.get('viz_id', '')
            chart_hovers.append(viz_id)
            if viz_id:
                unique_viz_ids.add(viz_id)

        elif etype == 'tab_change':
            tab_changes += 1
            if ds:
                datasets_visited.add(ds)

        elif etype == 'trace_interact':
            trace_interactions.append({
                'ts':             ts,
                'classification': payload.get('classification', ''),
                'node_id':        payload.get('node_id', ''),
                'step_id':        payload.get('step_id'),
            })

        elif etype == 'rubric_edit':
            rubric_edits.append({
                'ts':                              ts,
                'edit_type':                       payload.get('edit_type', ''),
                'concept_id':                      payload.get('concept_id', ''),
                # Multi-window fields (v3 schema)
                'within_15s':                      payload.get('within_15s', False),
                'within_30s':                      payload.get('within_30s', False),
                'within_60s':                      payload.get('within_60s', False),
                'time_since_last_contradicts_ms':  payload.get('time_since_last_contradicts_ms'),
                'source_contradicts_nodes_60s':    payload.get('source_contradicts_nodes_60s', []),
                # Concept alignment fields
                'concept_in_contradicts_exact':    payload.get('concept_in_contradicts_exact',
                                                               payload.get('concept_in_contradicts', False)),
                'concept_in_contradicts_semantic': payload.get('concept_in_contradicts_semantic', False),
                'semantic_match_score':            payload.get('semantic_match_score'),
                'semantic_match_node':             payload.get('semantic_match_node'),
                'session_contradicts_nodes':       payload.get('session_contradicts_nodes', []),
                # Panel timing
                'panel_focus_before_trace':        payload.get('panel_focus_before_trace', False),
                # Interaction source
                'interaction_source':              payload.get('interaction_source', 'manual'),
                # Topological gap & grounding density (v10 schema — defaults for older logs)
                'trace_gap_count':                 payload.get('trace_gap_count', 0),
                'grounding_density':               payload.get('grounding_density', 0.0),
            })

    # Time-to-answer: from task_start (or page_view) to task_submit
    t0 = task_start_ts or page_view_ts or first_ts
    time_to_answer_s = (task_submit_ts - t0) / 1000 if task_submit_ts else None

    # ── Rubric edit analysis ───────────────────────────────────────────────────
    n_edits = len(rubric_edits)

    # Multi-window causal attribution (pre-registered; primary window is 30 s)
    n_within_15s = sum(1 for e in rubric_edits if e['within_15s'])
    n_within_30s = sum(1 for e in rubric_edits if e['within_30s'])
    n_within_60s = sum(1 for e in rubric_edits if e['within_60s'])

    # Concept alignment — exact and semantic (Gemini code review v1: split by source)
    # Gemini Q3 decision: include click_to_add in analysis but report separately.
    # H2 PRIMARY metric = semantic_alignment_rate_manual (unprompted, no UI assist).
    # semantic_alignment_rate_click_to_add is reported as a separate UI-assisted rate.
    n_exact_aligned    = sum(1 for e in rubric_edits if e['concept_in_contradicts_exact'])
    n_semantic_aligned = sum(1 for e in rubric_edits if e['concept_in_contradicts_semantic'])
    n_manual_edits     = sum(1 for e in rubric_edits if e['interaction_source'] == 'manual')
    n_semantic_aligned_manual = sum(
        1 for e in rubric_edits
        if e['concept_in_contradicts_semantic'] and e['interaction_source'] == 'manual'
    )
    n_semantic_aligned_cta = sum(
        1 for e in rubric_edits
        if e['concept_in_contradicts_semantic'] and e['interaction_source'] == 'click_to_add'
    )

    # Click-to-Add interactions (zero lexical ambiguity)
    n_click_to_add = sum(1 for e in rubric_edits if e['interaction_source'] == 'click_to_add')

    # Panel focus ordering
    n_panel_before_trace = sum(1 for e in rubric_edits if e['panel_focus_before_trace'])

    # Topological gap count — moderator variable for H1.
    # Mean trace_gap_count across all rubric edits: do gappier traces produce
    # more causal attribution? (potential moderator; analysed in paper Discussion).
    gap_counts_at_edit = [e['trace_gap_count'] for e in rubric_edits if e.get('trace_gap_count') is not None]
    mean_trace_gap_count = round(sum(gap_counts_at_edit) / len(gap_counts_at_edit), 2) \
        if gap_counts_at_edit else None

    density_at_edit = [e['grounding_density'] for e in rubric_edits if e.get('grounding_density') is not None]
    mean_grounding_density = round(sum(density_at_edit) / len(density_at_edit), 3) \
        if density_at_edit else None

    # Hypergeometric p-value for semantic alignment rate (see docstring for null model)
    # Session-level: k edits, n rubric concepts, m CONTRADICTS concepts
    # Uses the last rubric_edit's session_contradicts_nodes for m and n
    hyper_p: Optional[float] = None
    if n_edits > 0 and rubric_edits:
        session_c = rubric_edits[-1]['session_contradicts_nodes']
        n_rubric  = len({e['concept_id'] for e in rubric_edits})  # distinct edited concepts as proxy
        m_flagged = len(session_c)
        if m_flagged > 0 and n_rubric > 0:
            hyper_p = _hypergeometric_p(
                k=n_semantic_aligned,
                N=max(n_rubric, m_flagged, 20),   # rubric size (estimate 20 if unknown)
                K=m_flagged,
                n=n_edits,
            )

    # Edit type breakdown
    edit_type_counts = defaultdict(int)
    for e in rubric_edits:
        edit_type_counts[e['edit_type']] += 1

    return {
        'session_id':                    session_id,
        'condition':                     condition,
        'sus_score':                     sus_score,
        'confidence':                    confidence,
        'time_to_answer_s':              round(time_to_answer_s, 1) if time_to_answer_s else None,
        'total_session_s':               round(total_session_ms / 1000, 1),
        'answer_words':                  answer_length,
        'chart_hovers':                  len(chart_hovers),
        'unique_charts':                 len(unique_viz_ids),
        'tab_changes':                   tab_changes,
        'datasets_visited':              len(datasets_visited),
        'task_completed':                task_submit_ts is not None,
        'sus_completed':                 sus_score is not None,
        # Rubric edit metrics (both conditions; Condition A expected non-zero for comparison)
        'rubric_edits':                  n_edits,
        'rubric_edits_within_15s':       n_within_15s,
        'rubric_edits_within_30s':       n_within_30s,
        'rubric_edits_within_60s':       n_within_60s,
        'rubric_edits_exact_aligned':         n_exact_aligned,
        'rubric_edits_semantic_aligned':      n_semantic_aligned,
        # H2 PRIMARY: unprompted manual edits only (Gemini code review Q3)
        'rubric_manual_edits':                n_manual_edits,
        'rubric_edits_semantic_aligned_manual': n_semantic_aligned_manual,
        'rubric_edits_semantic_aligned_cta':  n_semantic_aligned_cta,
        'rubric_edits_click_to_add':          n_click_to_add,
        'rubric_panel_before_trace':     n_panel_before_trace,
        'concept_alignment_hyper_p':     hyper_p,
        'rubric_edit_add':               edit_type_counts['add'],
        'rubric_edit_remove':            edit_type_counts['remove'],
        'rubric_edit_increase_weight':   edit_type_counts['increase_weight'],
        'rubric_edit_decrease_weight':   edit_type_counts['decrease_weight'],
        'trace_interactions':            len(trace_interactions),
        'contradicts_interactions':      sum(1 for t in trace_interactions if t['classification'] == 'CONTRADICTS'),
        # Moderators — mean values of the currently visible trace properties at edit time.
        'mean_trace_gap_count':    mean_trace_gap_count,
        'mean_grounding_density':  mean_grounding_density,
    }


# ── Condition-level aggregation ────────────────────────────────────────────────

def aggregate_by_condition(session_metrics: list[dict]) -> dict[str, dict]:
    """
    Groups sessions by condition and computes means ± std.
    Returns {'A': {...}, 'B': {...}}.
    """
    import statistics

    groups: dict[str, list[dict]] = defaultdict(list)
    for m in session_metrics:
        groups[m['condition']].append(m)

    result = {}
    for cond, rows in sorted(groups.items()):
        n = len(rows)

        def mean_of(key: str) -> Optional[float]:
            vals = [r[key] for r in rows if r.get(key) is not None]
            return round(statistics.mean(vals), 2) if vals else None

        def std_of(key: str) -> Optional[float]:
            vals = [r[key] for r in rows if r.get(key) is not None]
            return round(statistics.stdev(vals), 2) if len(vals) >= 2 else None

        total_edits = max(sum(r['rubric_edits'] for r in rows), 1)

        result[cond] = {
            'n':                       n,
            'sus_mean':                mean_of('sus_score'),
            'sus_sd':                  std_of('sus_score'),
            'time_to_answer_mean_s':   mean_of('time_to_answer_s'),
            'time_to_answer_sd_s':     std_of('time_to_answer_s'),
            'chart_hovers_mean':       mean_of('chart_hovers'),
            'unique_charts_mean':      mean_of('unique_charts'),
            'confidence_mean':         mean_of('confidence'),
            'answer_words_mean':       mean_of('answer_words'),
            'task_completion_rate':    round(sum(r['task_completed'] for r in rows) / n, 3),
            'sus_completion_rate':     round(sum(r['sus_completed'] for r in rows) / n, 3),
            # ── Rubric edit — raw means ──────────────────────────────────────
            'rubric_edits_mean':              mean_of('rubric_edits'),
            'contradicts_interactions_mean':  mean_of('contradicts_interactions'),
            'rubric_click_to_add_mean':       mean_of('rubric_edits_click_to_add'),
            # ── Multi-window causal attribution rates (pre-registered) ───────
            # Primary hypothesis window = 30 s (H1_temporal).
            # 15 s and 60 s are sensitivity checks — reported but not the primary claim.
            'causal_attribution_rate_15s': round(
                sum(r['rubric_edits_within_15s'] for r in rows) / total_edits, 3),
            'causal_attribution_rate_30s': round(
                sum(r['rubric_edits_within_30s'] for r in rows) / total_edits, 3),
            'causal_attribution_rate_60s': round(
                sum(r['rubric_edits_within_60s'] for r in rows) / total_edits, 3),
            # ── Concept alignment rates (H2_semantic) ────────────────────────
            # Gemini code review Q3: report manual vs click_to_add separately.
            # H2 PRIMARY = semantic_alignment_rate_manual (unprompted; no UI assist).
            # semantic_alignment_rate_cta is reported separately as UI-assisted rate.
            # semantic_alignment_rate (combined) kept for reference / robustness check.
            'total_manual_edits': sum(r['rubric_manual_edits'] for r in rows),
            'exact_alignment_rate': round(
                sum(r['rubric_edits_exact_aligned'] for r in rows) / total_edits, 3),
            'semantic_alignment_rate': round(
                sum(r['rubric_edits_semantic_aligned'] for r in rows) / total_edits, 3),
            'semantic_alignment_rate_manual': round(
                sum(r['rubric_edits_semantic_aligned_manual'] for r in rows)
                / max(sum(r['rubric_manual_edits'] for r in rows), 1), 3),
            'semantic_alignment_rate_cta': round(
                sum(r['rubric_edits_semantic_aligned_cta'] for r in rows)
                / max(sum(r['rubric_edits_click_to_add'] for r in rows), 1), 3),
            # ── Panel focus ordering ─────────────────────────────────────────
            # What fraction of edits came from educators who opened the rubric
            # BEFORE viewing any trace? (rubric-first vs trace-first strategy)
            'panel_before_trace_rate': round(
                sum(r['rubric_panel_before_trace'] for r in rows) / total_edits, 3),
            # ── Topological gap & grounding density moderators ───────────────
            # Mean structural leaps and grounding density at the time of rubric edits.
            # Used in Stability Analysis (Section 5a) and as moderators for H1.
            'mean_trace_gap_count_mean':   mean_of('mean_trace_gap_count'),
            'mean_grounding_density_mean': mean_of('mean_grounding_density'),
        }
    return result


# ── Statistical tests ──────────────────────────────────────────────────────────

def mann_whitney_u(a_vals: list[float], b_vals: list[float]) -> Optional[float]:
    """Mann-Whitney U test p-value (two-sided). Returns None if insufficient data."""
    try:
        from scipy.stats import mannwhitneyu
        if len(a_vals) < 2 or len(b_vals) < 2:
            return None
        _, p = mannwhitneyu(a_vals, b_vals, alternative='two-sided')
        return round(float(p), 4)
    except Exception:
        return None


def run_gap_moderation_analysis(session_metrics: list[dict]) -> Optional[dict]:
    """
    Pre-registered exploratory moderation analysis (Gemini v8 recommendation).

    Tests whether trace_gap_count moderates the effect of viewing the LRM trace
    on within_30s causal attribution (H1 temporal).

    Model: Generalized Estimating Equations (GEE) with Binomial family + Logit link
      - GEE handles clustered non-independent observations (multiple edits per
        participant) without requiring a fully specified random-effects distribution.
      - Exchangeable correlation structure: edits within the same session share a
        common correlation ρ (estimated from data).
      - Logit link (Gemini v8 correction): correct for binary outcome within_30s.
        `mixedlm` (linear link) was incorrect — it can predict probabilities outside
        [0,1] and inflates Type I error for rare binary outcomes.

    Outcome:  within_30s (binary, per rubric_edit)
    Fixed:    condition (A=0, B=1), trace_gap_count, condition × trace_gap_count
    Clustered by: session_id (participant)

    Requires statsmodels >= 0.14. Silently returns None if unavailable
    or if there are <10 edit records (insufficient for GEE).

    Returns a dict with: coef, p_value, OR (odds ratio), note
    """
    try:
        import numpy as np
        import pandas as pd
        from statsmodels.genmod.generalized_estimating_equations import GEE
        from statsmodels.genmod.families import Binomial
        from statsmodels.genmod.cov_struct import Exchangeable
    except ImportError:
        return {'error': 'statsmodels/pandas not installed — pip install statsmodels pandas'}

    # Build an edit-level dataframe from session-level summary metrics.
    # NOTE: This is a session-level approximation. For the full study, re-derive
    # from raw JSONL event logs (one row per rubric_edit event) for exact GEE.
    rows = []
    for m in session_metrics:
        n_edits = m.get('rubric_edits', 0)
        if n_edits == 0:
            continue
        gap  = float(m.get('mean_trace_gap_count') or 0)
        cond = 1 if m.get('condition') == 'B' else 0
        n_within_30 = m.get('rubric_edits_within_30s', 0)
        sid  = m.get('session_id', '?')
        # Expand to one row per edit, distributing within_30s attributions
        # proportionally (first n_within_30 edits flagged as attributed).
        for i in range(n_edits):
            rows.append({
                'session_id':     sid,
                'condition':      cond,
                'trace_gap_count': gap,
                'within_30s':     1 if i < n_within_30 else 0,
            })

    if len(rows) < 10:
        return {'error': f'Insufficient data: {len(rows)} edit records (need ≥10)'}

    df = pd.DataFrame(rows)
    if df['within_30s'].nunique() < 2:
        return {'error': 'Outcome has no variance — all edits in one class'}

    try:
        # GEE with Binomial family (logit link) and Exchangeable working correlation.
        # Groups = session_id ensures observations within a participant are clustered.
        model = GEE.from_formula(
            'within_30s ~ condition * trace_gap_count',
            groups='session_id',
            data=df,
            family=Binomial(),
            cov_struct=Exchangeable(),
        ).fit()

        params  = model.params
        pvalues = model.pvalues

        gap_coef   = params.get('trace_gap_count', float('nan'))
        gap_p      = pvalues.get('trace_gap_count', float('nan'))
        inter_coef = params.get('condition:trace_gap_count', float('nan'))
        inter_p    = pvalues.get('condition:trace_gap_count', float('nan'))

        # Odds ratios = exp(coef) for logit-link GEE
        gap_or   = round(float(np.exp(gap_coef)),  4) if not np.isnan(gap_coef)  else None
        inter_or = round(float(np.exp(inter_coef)), 4) if not np.isnan(inter_coef) else None

        # Working correlation ρ (exchangeable): justifies why GEE is needed.
        # High |ρ| → edits within a participant are correlated → GEE is essential.
        # Report ρ in the paper Methods section alongside the GEE model specification.
        rho = float(model.cov_struct.dep_params)

        return {
            'model':                  'GEE Binomial/Logit + Exchangeable corr (Gemini v8)',
            'n_edits':                len(df),
            'n_sessions':             int(df['session_id'].nunique()),
            'working_correlation_rho': round(rho, 4),
            'gap_count_coef':         round(float(gap_coef),  4),
            'gap_count_OR':           gap_or,
            'gap_count_p':            round(float(gap_p),     4),
            'interaction_coef':       round(float(inter_coef), 4),
            'interaction_OR':         inter_or,
            'interaction_p':          round(float(inter_p),   4),
            'note': (
                'Pre-registered exploratory (Gemini v8). '
                'p < 0.10 → report as directional trend in Discussion. '
                'Session-level approximation — re-derive from raw events for full study. '
                f'Working correlation ρ={rho:.3f} — report in paper Methods (justifies GEE over GLM).'
            ),
        }
    except Exception as exc:
        return {'error': f'GEE model failed: {exc}'}


# ── Print report ───────────────────────────────────────────────────────────────

def print_report(agg: dict[str, dict], session_metrics: list[dict]) -> None:
    LINE = '─' * 64

    print(f'\n{"="*64}')
    print(f'  ConceptGrade User Study — Results Summary')
    print(f'  Conditions: A = Summary only  |  B = Full VA dashboard')
    print(f'{"="*64}')

    if not agg:
        print('  No session data found. Run a participant study first.')
        print(f'{"="*64}\n')
        return

    cond_a = agg.get('A', {})
    cond_b = agg.get('B', {})
    na, nb = cond_a.get('n', 0), cond_b.get('n', 0)

    print(f'\n  N: Condition A = {na}   Condition B = {nb}\n')
    print(f'  {LINE}')
    print(f'  {"Metric":<30} {"Cond A":>10} {"Cond B":>10} {"p-value":>10}')
    print(f'  {LINE}')

    def row(label: str, key: str, fmt: str = '.2f'):
        a_vals = [m[key] for m in session_metrics if m['condition'] == 'A' and m.get(key) is not None]
        b_vals = [m[key] for m in session_metrics if m['condition'] == 'B' and m.get(key) is not None]
        a_str  = f'{cond_a.get(key.replace("_s","_mean_s").replace("_score","_mean").replace("_words","_words_mean").replace("_hovers","_hovers_mean").replace("_charts","_charts_mean"), "—"):{fmt}}' if cond_a.get(key.replace("_s","_mean_s").replace("_score","_mean").replace("_words","_words_mean").replace("_hovers","_hovers_mean").replace("_charts","_charts_mean")) is not None else '—'
        b_str  = '—'
        p_str  = '—'
        # Simplest approach: use raw key as agg key
        a_mean = cond_a.get(key) if key in cond_a else None
        b_mean = cond_b.get(key) if key in cond_b else None
        a_str  = f'{a_mean:{fmt}}' if a_mean is not None else '—'
        b_str  = f'{b_mean:{fmt}}' if b_mean is not None else '—'
        p      = mann_whitney_u(a_vals, b_vals)
        p_str  = f'{p:.4f}' if p is not None else '—'
        sig    = ' *' if (p is not None and p < 0.05) else ('**' if (p is not None and p < 0.01) else '')
        print(f'  {label:<30} {a_str:>10} {b_str:>10} {p_str:>10}{sig}')

    row('SUS score (mean)',        'sus_mean',              '.1f')
    row('SUS SD',                  'sus_sd',                '.1f')
    row('Time to answer (s, mean)','time_to_answer_mean_s', '.1f')
    row('Time to answer (s, SD)',  'time_to_answer_sd_s',   '.1f')
    row('Chart hovers (mean)',     'chart_hovers_mean',     '.1f')
    row('Unique charts (mean)',    'unique_charts_mean',    '.1f')
    row('Confidence (mean, 1–5)',  'confidence_mean',       '.2f')
    row('Answer words (mean)',     'answer_words_mean',     '.1f')
    row('Task completion rate',    'task_completion_rate',  '.3f')

    # Rubric edit section — now shown for both conditions
    print(f'\n  {"Rubric Edit Metrics":<38} {"Cond A":>8} {"Cond B":>8}')
    print(f'  {LINE}')
    for label, key, fmt in [
        ('Rubric edits (mean)',               'rubric_edits_mean',              '.1f'),
        ('Click-to-Add edits (mean)',          'rubric_click_to_add_mean',       '.1f'),
        ('CONTRADICTS interactions (mean)',    'contradicts_interactions_mean',  '.1f'),
        ('Trace gap count at edits [moderator]', 'mean_trace_gap_count_mean',    '.2f'),
        ('Grounding density at edits [moderator]','mean_grounding_density_mean', '.3f'),
    ]:
        a_val = cond_a.get(key)
        b_val = cond_b.get(key)
        a_str = f'{a_val:{fmt}}' if a_val is not None else '—'
        b_str = f'{b_val:{fmt}}' if b_val is not None else '—'
        print(f'  {label:<38} {a_str:>8} {b_str:>8}')

    print(f'\n  {"Causal Attribution (multi-window)":<38} {"Cond A":>8} {"Cond B":>8}')
    print(f'  {"  Primary claim = 30 s window":<46}')
    print(f'  {LINE}')
    for label, key in [
        ('Attribution rate @ 15 s (sensitivity)', 'causal_attribution_rate_15s'),
        ('Attribution rate @ 30 s (primary H1)', 'causal_attribution_rate_30s'),
        ('Attribution rate @ 60 s (sensitivity)', 'causal_attribution_rate_60s'),
    ]:
        a_val = cond_a.get(key)
        b_val = cond_b.get(key)
        a_str = f'{a_val:.3f}' if a_val is not None else '—'
        b_str = f'{b_val:.3f}' if b_val is not None else '—'
        print(f'  {label:<38} {a_str:>8} {b_str:>8}')

    print(f'\n  {"Concept Alignment (H2_semantic)":<38} {"Cond A":>8} {"Cond B":>8}')
    print(f'  {"  H2 PRIMARY = manual only; CTA reported separately":<46}')
    print(f'  {LINE}')
    for label, key in [
        ('Exact alignment rate   [baseline]', 'exact_alignment_rate'),
        ('Semantic rate — manual [H2 PRIMARY]', 'semantic_alignment_rate_manual'),
        ('Semantic rate — click_to_add [UI-assist]', 'semantic_alignment_rate_cta'),
        ('Semantic rate — combined  [reference]', 'semantic_alignment_rate'),
        ('Panel-before-trace rate',           'panel_before_trace_rate'),
    ]:
        a_val = cond_a.get(key)
        b_val = cond_b.get(key)
        a_str = f'{a_val:.3f}' if a_val is not None else '—'
        b_str = f'{b_val:.3f}' if b_val is not None else '—'
        print(f'  {label:<38} {a_str:>8} {b_str:>8}')

    # Per-session hypergeometric p-values (concept alignment under null)
    b_hyper = [m['concept_alignment_hyper_p'] for m in session_metrics
               if m['condition'] == 'B' and m.get('concept_alignment_hyper_p') is not None]
    if b_hyper:
        import statistics as _st
        print(f'\n  Condition B hypergeometric p (concept alignment null, per session):')
        print(f'    median={_st.median(b_hyper):.4f}  min={min(b_hyper):.4f}  max={max(b_hyper):.4f}')

    print(f'  {LINE}')
    print(f'  * p < 0.05   ** p < 0.01  (Mann-Whitney U, two-sided)')

    # Topological gap moderation analysis (exploratory, pre-registered at v8)
    # GEE Binomial/Logit: within_30s ~ condition * trace_gap_count | session_id
    gap_result = run_gap_moderation_analysis(session_metrics)
    if gap_result:
        print(f'\n  {"Topological Gap Moderation — GEE Binomial/Logit (exploratory)":<46}')
        print(f'  {LINE}')
        if 'error' in gap_result:
            print(f'  Skipped: {gap_result["error"]}')
        else:
            rho      = gap_result.get('working_correlation_rho', float('nan'))
            or_gap   = gap_result.get('gap_count_OR')
            or_inter = gap_result.get('interaction_OR')
            print(f'  N edits: {gap_result["n_edits"]}  N sessions: {gap_result["n_sessions"]}  ρ={rho:.3f}')
            print(f'  trace_gap_count main effect:  coef={gap_result["gap_count_coef"]:+.4f}  OR={or_gap:.3f}  p={gap_result["gap_count_p"]:.4f}')
            print(f'  condition × gap_count:        coef={gap_result["interaction_coef"]:+.4f}  OR={or_inter:.3f}  p={gap_result["interaction_p"]:.4f}')
            sig = '→ DIRECTIONAL TREND' if gap_result['interaction_p'] < 0.10 else '→ n.s.'
            print(f'  {sig}  (ρ justifies GEE over GLM — report in Methods)')

    # SUS interpretation
    for cond_label, data in [('A', cond_a), ('B', cond_b)]:
        s = data.get('sus_mean')
        if s is not None:
            grade = 'A+/Best' if s >= 90 else 'A/Excellent' if s >= 80 else 'B/Good' if s >= 70 else 'C/OK' if s >= 60 else 'D/Poor' if s >= 50 else 'F/Unacceptable'
            print(f'\n  Condition {cond_label} SUS = {s:.1f} → {grade}')

    print(f'\n{"="*64}\n')


# ── CSV export ─────────────────────────────────────────────────────────────────

def write_csv(session_metrics: list[dict], out_path: Path) -> None:
    import csv
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not session_metrics:
        return
    fieldnames = list(session_metrics[0].keys())
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(session_metrics)
    print(f'  CSV saved: {out_path}  ({len(session_metrics)} rows)')


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description='ConceptGrade user study log analyzer')
    parser.add_argument('--logs-dir', default=str(LOGS_DIR),
                        help=f'Path to JSONL session logs (default: {LOGS_DIR})')
    parser.add_argument('--csv', action='store_true',
                        help='Write per-session metrics to results/study_analysis.csv')
    args = parser.parse_args()

    logs_dir = Path(args.logs_dir)
    sessions  = load_all_sessions(logs_dir)

    if not sessions:
        print(f'\n[analyze_study_logs] No session files found in {logs_dir}')
        print('  Run the user study, then re-run this script.')
        return

    print(f'\n[analyze_study_logs] Loaded {len(sessions)} sessions from {logs_dir}')

    session_metrics = [analyse_session(events) for events in sessions.values() if events]
    session_metrics = [m for m in session_metrics if m]  # drop empty

    agg = aggregate_by_condition(session_metrics)
    print_report(agg, session_metrics)

    if args.csv:
        write_csv(session_metrics, RESULTS_DIR / 'study_analysis.csv')


if __name__ == '__main__':
    main()
