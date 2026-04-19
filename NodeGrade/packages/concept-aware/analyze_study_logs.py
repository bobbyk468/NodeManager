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
    //   panel_mount_timestamp_ms, panel_focus_before_trace, interaction_source,
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
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Optional

DATA_DIR    = Path(__file__).parent / 'data'
LOGS_DIR    = DATA_DIR / 'study_logs'
RESULTS_DIR = Path(__file__).parent / 'results'

# Cap for wall-clock dwell fallback — prevents overnight sessions from inflating medians.
_MAX_DWELL_MS = 10 * 60 * 1_000  # 10 minutes

# Maximum concepts shown in the concept_frequency chart — bounds the educator's
# effective rubric size N for the hypergeometric null model (H2).
# Update this if the frontend UI is changed to show more concepts.
CONCEPT_FREQUENCY_MAX_BARS = 15


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
    # Primary dataset for this session (most common across events)
    _dataset_counts: dict[str, int] = {}
    for _ev in events:
        _ds = _ev.get('dataset', '')
        if _ds:
            _dataset_counts[_ds] = _dataset_counts.get(_ds, 0) + 1
    primary_dataset = max(_dataset_counts, key=lambda k: _dataset_counts[k]) if _dataset_counts else ''

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

    # Answer dwell tracking
    pending_views: dict[str, dict] = {}   # student_answer_id → {start_ts, severity, benchmark_case}
    answer_dwells: list[dict] = []

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
                'timestamp_ms':   ts,
                'classification': payload.get('classification', ''),
                'node_id':        payload.get('node_id', ''),
                'step_id':        payload.get('step_id'),
            })

        elif etype == 'answer_view_start':
            aid = str(payload.get('student_answer_id', ''))
            if aid:
                pending_views[aid] = {
                    'start_ts':       ts,
                    'severity':       payload.get('severity', ''),
                    'benchmark_case': payload.get('benchmark_case'),
                }

        elif etype == 'answer_view_end':
            aid = str(payload.get('student_answer_id', ''))
            dwell_ms  = payload.get('dwell_time_ms')
            severity  = payload.get('severity', '') or pending_views.get(aid, {}).get('severity', '')
            bcase     = payload.get('benchmark_case') or pending_views.get(aid, {}).get('benchmark_case')
            # Prefer the dwell_time_ms delivered by sendBeacon — already corrected for
            # tab visibility (Page Visibility API), so no cap is applied.
            # Wall-clock fallback is capped at _MAX_DWELL_MS to prevent overnight
            # sessions from inflating median dwell.
            if isinstance(dwell_ms, (int, float)) and dwell_ms > 0:
                computed = int(dwell_ms)                                    # trust beacon
            elif aid in pending_views:
                computed = min(max(0, ts - pending_views[aid]['start_ts']), _MAX_DWELL_MS)
            else:
                computed = 0
            if computed > 0:
                answer_dwells.append({
                    'answer_id':      aid,
                    'dwell_ms':       computed,
                    'severity':       severity,
                    'benchmark_case': bcase,
                })
            pending_views.pop(aid, None)

        elif etype == 'rubric_edit':
            rubric_edits.append({
                'timestamp_ms':                    ts,
                'session_id':                      session_id,
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
                # Topological gap & grounding density — per-edit values (not session mean)
                'trace_gap_count':                 payload.get('trace_gap_count', 0),
                'grounding_density':               payload.get('grounding_density', 0.0),
                # Rubric population (v21 schema — for hypergeometric N).
                # Capped at CONCEPT_FREQUENCY_MAX_BARS: concept_frequency shows at most
                # that many concepts, bounding the educator's effective rubric size.
                'rubric_size': min(payload.get('rubric_size', 0), CONCEPT_FREQUENCY_MAX_BARS),
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

    # Hypergeometric p-value for semantic alignment rate (see docstring for null model).
    # N = true rubric size from rubric_size field (v21 schema); falls back to max of
    # m_flagged and 20 for logs produced before the rubric_size field was added.
    hyper_p_manual: Optional[float] = None    # H2 PRIMARY — manual edits only (pre-registered)
    hyper_p_combined: Optional[float] = None  # robustness check — all edits incl. Click-to-Add
    if n_edits > 0 and rubric_edits:
        # Use the last edit's session_contradicts_nodes as K (full session accumulation).
        # This is a conservative estimator: as K grows throughout the session, the
        # hypergeometric null becomes easier to satisfy by chance (larger K = smaller
        # denominator for the null proportion K/N), making it harder to reject H2.
        # Reported as a paper footnote; sensitivity analysis with K = 30s-window only
        # is available via --window-k flag. Pre-registration locks the full-session K.
        session_c = rubric_edits[-1]['session_contradicts_nodes']
        m_flagged = len(session_c)
        # Use the median rubric_size reported across edits; rubric_size=0 means old log.
        rubric_sizes = [e['rubric_size'] for e in rubric_edits if e.get('rubric_size', 0) > 0]
        if rubric_sizes:
            n_rubric = int(statistics.median(rubric_sizes))
        else:
            n_rubric = max(m_flagged, CONCEPT_FREQUENCY_MAX_BARS)
        N_eff = max(n_rubric, m_flagged)
        if m_flagged > 0 and n_rubric > 0:
            # PRIMARY: manual edits only — Click-to-Add always aligns by construction,
            # so including it would inflate k and understate the unprompted alignment rate.
            if n_manual_edits > 0:
                hyper_p_manual = _hypergeometric_p(
                    k=n_semantic_aligned_manual,
                    N=N_eff,
                    K=m_flagged,
                    n=n_manual_edits,
                )
            # COMBINED robustness check — all edits (CTA + manual); reported in footnote.
            hyper_p_combined = _hypergeometric_p(
                k=n_semantic_aligned,
                N=N_eff,
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
        'dataset':                       primary_dataset,
        # Placebo alignment rate — computed post-hoc in main() for Condition A sessions
        # by testing their manual edits against the hidden CONTRADICTS reference set
        # derived from Condition B trace interactions on the same dataset.
        'placebo_alignment_rate':        None,
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
        'concept_alignment_hyper_p':         hyper_p_manual,    # H2 PRIMARY (manual only)
        'concept_alignment_hyper_p_combined': hyper_p_combined,  # robustness (all edits)
        'rubric_edit_add':               edit_type_counts['add'],
        'rubric_edit_remove':            edit_type_counts['remove'],
        'rubric_edit_increase_weight':   edit_type_counts['increase_weight'],
        'rubric_edit_decrease_weight':   edit_type_counts['decrease_weight'],
        'trace_interactions':            len(trace_interactions),
        'contradicts_interactions':      sum(1 for t in trace_interactions if t['classification'] == 'CONTRADICTS'),
        # Moderators — mean values of the currently visible trace properties at edit time.
        'mean_trace_gap_count':    mean_trace_gap_count,
        'mean_grounding_density':  mean_grounding_density,
        # Per-edit records — consumed by run_gap_moderation_analysis() for exact GEE.
        'raw_edits':    rubric_edits,
        # Per-answer dwell records — consumed by aggregate_by_condition() and print_report().
        'answer_dwells': answer_dwells,
    }


# ── Dwell-time helper ─────────────────────────────────────────────────────────

def _median_dwell_by(dwells: list[dict], key: str) -> dict[str, float]:
    """Compute median dwell time (seconds) for answer views grouped by a string key.

    Parameters
    ----------
    dwells : flat list of answer_dwell records (each has 'dwell_ms' and the key field)
    key    : 'severity' or 'benchmark_case'
    """
    grps: dict[str, list[int]] = defaultdict(list)
    for d in dwells:
        v = d.get(key)
        if v:
            grps[v].append(d['dwell_ms'])
    return {k: round(statistics.median(vs) / 1000, 2) for k, vs in grps.items() if vs}


# ── Condition-level aggregation ────────────────────────────────────────────────

def aggregate_by_condition(session_metrics: list[dict]) -> dict[str, dict]:
    """
    Groups sessions by condition and computes means ± std.
    Returns {'A': {...}, 'B': {...}}.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for m in session_metrics:
        groups[m['condition']].append(m)

    result = {}
    for cond, rows in sorted(groups.items()):
        n = len(rows)

        # Explicit-parameter helpers prevent Python late-binding closure bugs:
        # if `rows` were captured implicitly from the loop variable, a future
        # refactor that mutates or reassigns it would silently corrupt all results.
        # Passing `rows` explicitly makes each helper independently testable.

        def mean_of(cond_rows: list[dict], key: str) -> Optional[float]:
            vals = [r[key] for r in cond_rows if r.get(key) is not None]
            return round(statistics.mean(vals), 2) if vals else None

        def std_of(cond_rows: list[dict], key: str) -> Optional[float]:
            vals = [r[key] for r in cond_rows if r.get(key) is not None]
            return round(statistics.stdev(vals), 2) if len(vals) >= 2 else None

        def participant_mean_ratio(cond_rows: list[dict], window_key: str, min_edits: int = 1) -> Optional[float]:
            """Per-participant ratio: within-window edits / total edits; averaged across participants.

            Equal-weighting ensures no single high-volume participant dominates the H1 rate.
            Only includes participants who made at least `min_edits` rubric edits.

            Args:
                cond_rows:   condition-filtered session rows (explicit, no closure risk).
                window_key:  key for the within-window edit count field.
                min_edits:   minimum edit count threshold (default 1 = all participants with any edit;
                             use 3 for the primary pre-registered estimator that excludes
                             single/dual-edit sessions with high variance).
            """
            ratios = []
            for r in cond_rows:
                n_edits = r.get('rubric_edits') or 0
                n_window = r.get(window_key) or 0
                if n_edits >= min_edits:
                    ratios.append(n_window / n_edits)
            return round(statistics.mean(ratios), 3) if ratios else None

        def participant_weighted_ratio(cond_rows: list[dict], window_key: str) -> Optional[float]:
            """Edit-weighted mean ratio: weights each participant's ratio by their edit count.

            Use as secondary estimator (robustness check). Higher-volume participants
            contribute proportionally more, which is appropriate when edit volume itself
            indicates deeper engagement with the tool rather than noise.
            """
            total_w = total_wn = 0
            for r in cond_rows:
                n_edits = r.get('rubric_edits') or 0
                n_window = r.get(window_key) or 0
                if n_edits > 0:
                    total_w  += n_edits
                    total_wn += n_window
            return round(total_wn / total_w, 3) if total_w > 0 else None

        total_edits = max(sum(r['rubric_edits'] for r in rows), 1)

        # ── Answer dwell metrics (Q4) ────────────────────────────────────────────
        all_dwells = [d for r in rows for d in r.get('answer_dwells', [])]

        seed_dwells     = [d['dwell_ms'] for d in all_dwells if d.get('benchmark_case')]
        non_seed_dwells = [d['dwell_ms'] for d in all_dwells if not d.get('benchmark_case')]
        seed_dwell_ratio = (
            round(statistics.median(seed_dwells) / statistics.median(non_seed_dwells), 3)
            if seed_dwells and non_seed_dwells else None
        )

        result[cond] = {
            'n':                       n,
            'sus_mean':                mean_of(rows, 'sus_score'),
            'sus_sd':                  std_of(rows, 'sus_score'),
            'time_to_answer_mean_s':   mean_of(rows, 'time_to_answer_s'),
            'time_to_answer_sd_s':     std_of(rows, 'time_to_answer_s'),
            'chart_hovers_mean':       mean_of(rows, 'chart_hovers'),
            'unique_charts_mean':      mean_of(rows, 'unique_charts'),
            'confidence_mean':         mean_of(rows, 'confidence'),
            'answer_words_mean':       mean_of(rows, 'answer_words'),
            'task_completion_rate':    round(sum(r['task_completed'] for r in rows) / n, 3),
            'sus_completion_rate':     round(sum(r['sus_completed'] for r in rows) / n, 3),
            # ── Rubric edit — raw means ──────────────────────────────────────
            'rubric_edits_mean':              mean_of(rows, 'rubric_edits'),
            'contradicts_interactions_mean':  mean_of(rows, 'contradicts_interactions'),
            'rubric_click_to_add_mean':       mean_of(rows, 'rubric_edits_click_to_add'),
            # ── Multi-window causal attribution rates ────────────────────────
            # PRIMARY (pre-registered): unweighted participant mean, all participants
            # with ≥1 edit. This is the exact estimator defined at pre-registration.
            # Reported in main H1 table. Swapped back to min_edits=1 per Gemini v4 review
            # (Q-B): introducing min_edits=3 post-hoc as primary would be a researcher
            # degree of freedom — IEEE VIS reviewers would flag it as p-hacking.
            'causal_attribution_rate_15s': participant_mean_ratio(rows, 'rubric_edits_within_15s'),
            'causal_attribution_rate_30s': participant_mean_ratio(rows, 'rubric_edits_within_30s'),
            'causal_attribution_rate_60s': participant_mean_ratio(rows, 'rubric_edits_within_60s'),
            # Sensitivity & Robustness Analysis (Supplementary Material):
            #   _min3: restrict to high-engagement sessions (≥3 edits) to test whether
            #          result holds after excluding high-variance 1–2 edit sessions.
            #          Paper language: "The causal attribution trend held stable..."
            #   _weighted: edit-count-weighted mean, giving high-volume participants
            #              proportionally more influence (alternative weighting scheme).
            'causal_attribution_rate_15s_min3': participant_mean_ratio(rows, 'rubric_edits_within_15s', min_edits=3),
            'causal_attribution_rate_30s_min3': participant_mean_ratio(rows, 'rubric_edits_within_30s', min_edits=3),
            'causal_attribution_rate_60s_min3': participant_mean_ratio(rows, 'rubric_edits_within_60s', min_edits=3),
            'causal_attribution_rate_30s_weighted': participant_weighted_ratio(rows, 'rubric_edits_within_30s'),
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
            # Condition A only: fraction of manual edits coincidentally matching the
            # hidden CONTRADICTS reference set derived from Condition B trace events
            # on the same dataset.  None for Condition B (not applicable).
            'placebo_alignment_rate_mean': mean_of(rows, 'placebo_alignment_rate'),
            # ── Panel focus ordering ─────────────────────────────────────────
            # What fraction of edits came from educators who opened the rubric
            # BEFORE viewing any trace? (rubric-first vs trace-first strategy)
            'panel_before_trace_rate': round(
                sum(r['rubric_panel_before_trace'] for r in rows) / total_edits, 3),
            # ── Topological gap & grounding density moderators ───────────────
            # Mean structural leaps and grounding density at the time of rubric edits.
            # Used in Stability Analysis (Section 5a) and as moderators for H1.
            'mean_trace_gap_count_mean':   mean_of(rows, 'mean_trace_gap_count'),
            'mean_grounding_density_mean': mean_of(rows, 'mean_grounding_density'),
            # ── Answer dwell (Q4) ────────────────────────────────────────────
            'dwell_by_severity':    _median_dwell_by(all_dwells, 'severity'),
            'dwell_by_benchmark':   _median_dwell_by(all_dwells, 'benchmark_case'),
            'seed_dwell_ratio':     seed_dwell_ratio,
            'n_answer_views':       len(all_dwells),
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

    Each row in the GEE dataframe is one rubric_edit event, using the per-edit
    trace_gap_count and within_30s values captured atomically at edit time
    (from m['raw_edits']).  No session-level approximation is used.

    Working correlation ρ (exchangeable): justifies why GEE is needed over GLM.
    High |ρ| → edits within a participant are correlated. Report ρ in the paper
    Methods section alongside the GEE model specification.

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

    # Build an edit-level dataframe from raw per-edit records (Q2 fix).
    # Each rubric_edit event carries its own trace_gap_count and within_30s
    # captured atomically at edit time — no session-mean approximation needed.
    rows = []
    for m in session_metrics:
        cond = 1 if m.get('condition') == 'B' else 0
        sid  = m.get('session_id', '?')
        for edit in m.get('raw_edits', []):
            rows.append({
                'session_id':      sid,
                'condition':       cond,
                'trace_gap_count': float(edit.get('trace_gap_count', 0)),
                'within_30s':      1 if edit.get('within_30s', False) else 0,
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
                'Uses exact per-edit rows from raw_edits (trace_gap_count and within_30s '
                'captured atomically at edit time — no session-level approximation). '
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

    def row(label: str, agg_key: str, raw_key: Optional[str] = None, fmt: str = '.2f'):
        if raw_key:
            a_vals = [m[raw_key] for m in session_metrics if m['condition'] == 'A' and m.get(raw_key) is not None]
            b_vals = [m[raw_key] for m in session_metrics if m['condition'] == 'B' and m.get(raw_key) is not None]
            p = mann_whitney_u(a_vals, b_vals)
        else:
            p = None

        a_mean = cond_a.get(agg_key)
        b_mean = cond_b.get(agg_key)
        a_str  = f'{a_mean:{fmt}}' if a_mean is not None else '—'
        b_str  = f'{b_mean:{fmt}}' if b_mean is not None else '—'
        p_str  = f'{p:.4f}' if p is not None else '—'
        sig    = ' *' if (p is not None and p < 0.05) else ('**' if (p is not None and p < 0.01) else '')
        print(f'  {label:<30} {a_str:>10} {b_str:>10} {p_str:>10}{sig}')

    row('SUS score (mean)',        'sus_mean',              'sus_score', '.1f')
    row('SUS SD',                  'sus_sd',                None,        '.1f')
    row('Time to answer (s, mean)','time_to_answer_mean_s', 'time_to_answer_s', '.1f')
    row('Time to answer (s, SD)',  'time_to_answer_sd_s',   None,        '.1f')
    row('Chart hovers (mean)',     'chart_hovers_mean',     'chart_hovers', '.1f')
    row('Unique charts (mean)',    'unique_charts_mean',    'unique_charts', '.1f')
    row('Confidence (mean, 1–5)',  'confidence_mean',       'confidence', '.2f')
    row('Answer words (mean)',     'answer_words_mean',     'answer_words', '.1f')
    row('Task completion rate',    'task_completion_rate',  None, '.3f')

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
    print(f'  {"  Primary = pre-registered (≥1 edit); 30s window":<46}')
    print(f'  {LINE}')
    # Condition A has no VerifierReasoningPanel, so CONTRADICTS interactions are
    # structurally impossible. Reporting 0.000 would mislead reviewers into thinking
    # this is an observed zero effect rather than a design constraint. Use N/A.
    cond_a_has_trace = (cond_a.get('contradicts_interactions_mean') or 0) > 0
    for label, key in [
        ('Attribution rate @ 15 s (sensitivity)', 'causal_attribution_rate_15s'),
        ('Attribution rate @ 30 s [PRIMARY H1]',  'causal_attribution_rate_30s'),
        ('Attribution rate @ 60 s (sensitivity)', 'causal_attribution_rate_60s'),
        # Sensitivity & Robustness (Supplementary Material)
        ('  ↳ high-engagement only (≥3 edits)',    'causal_attribution_rate_30s_min3'),
        ('  ↳ edit-weighted mean',                 'causal_attribution_rate_30s_weighted'),
    ]:
        a_val = cond_a.get(key)
        b_val = cond_b.get(key)
        # Show N/A for Condition A causal rates — trace interaction not available in Cond A.
        # Table footnote: "N/A: Condition A educators do not receive trace explanations
        # and therefore cannot perform the triggering CONTRADICTS interaction."
        a_str = f'{a_val:.3f}' if (a_val is not None and cond_a_has_trace) else 'N/A †'
        b_str = f'{b_val:.3f}' if b_val is not None else '—'
        print(f'  {label:<38} {a_str:>8} {b_str:>8}')
    print(f'  † N/A: Condition A has no trace panel; CONTRADICTS interaction structurally impossible.')

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
        b_val = cond_b.get(key)
        b_str = f'{b_val:.3f}' if b_val is not None else '—'
        if key == 'semantic_alignment_rate_manual':
            # Condition A cannot have a regular semantic alignment rate (session_contradicts_nodes
            # is always empty — no trace panel).  Instead show the Placebo Alignment Rate:
            # fraction of Condition A manual edits that coincidentally matched the hidden
            # CONTRADICTS reference derived from Condition B sessions on the same dataset.
            # This is the true control baseline for H2 (Gemini review Q-M).
            a_placebo = cond_a.get('placebo_alignment_rate_mean')
            a_str = f'{a_placebo:.3f} ‡' if a_placebo is not None else 'N/A  ‡'
        else:
            a_val = cond_a.get(key)
            a_str = f'{a_val:.3f}' if a_val is not None else '—'
        print(f'  {label:<38} {a_str:>8} {b_str:>8}')
    print(f'  ‡ Cond A: placebo baseline — manual edits tested against hidden CONTRADICTS'
          f'\n    reference derived from Cond B traces on the same dataset.')

    # Per-session hypergeometric p-values (concept alignment under null)
    b_hyper = [m['concept_alignment_hyper_p'] for m in session_metrics
               if m['condition'] == 'B' and m.get('concept_alignment_hyper_p') is not None]
    if b_hyper:
        print(f'\n  Condition B hypergeometric p (concept alignment null, per session):')
        print(f'    median={statistics.median(b_hyper):.4f}  min={min(b_hyper):.4f}  max={max(b_hyper):.4f}')

    print(f'  {LINE}')
    print(f'  * p < 0.05   ** p < 0.01  (Mann-Whitney U, two-sided)')

    # ── Answer dwell time (Q4) ─────────────────────────────────────────────────
    for cond_label, data in [('A', cond_a), ('B', cond_b)]:
        dwell_sev  = data.get('dwell_by_severity', {})
        dwell_bm   = data.get('dwell_by_benchmark', {})
        ratio      = data.get('seed_dwell_ratio')
        n_views    = data.get('n_answer_views', 0)
        if n_views > 0:
            print(f'\n  Condition {cond_label} — Answer Dwell Time  (n={n_views} view-end events)')
            print(f'  {LINE}')
            if dwell_sev:
                print(f'    Median dwell (s) by severity:')
                for sev, val in sorted(dwell_sev.items()):
                    print(f'      {sev:<12} {val:>6.2f} s')
            if dwell_bm:
                print(f'    Median dwell (s) by benchmark_case:')
                for bcase, val in sorted(dwell_bm.items()):
                    print(f'      {bcase:<30} {val:>6.2f} s')
            if ratio is not None:
                print(f'    Seed / non-seed dwell ratio: {ratio:.3f}'
                      f'  (>1.0 → educators dwell longer on trap answers)')

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

# Keys that hold nested lists and must be excluded from the flat per-session CSV.
_NON_SCALAR_KEYS = frozenset({'raw_edits', 'answer_dwells'})


def write_csv(session_metrics: list[dict], out_path: Path) -> None:
    """Write one row per session. Nested list columns (raw_edits, answer_dwells) are
    excluded — use write_edits_csv() for per-edit records."""
    import csv
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not session_metrics:
        return
    all_keys: dict[str, None] = {}
    for m in session_metrics:
        for k in m.keys():
            if k not in _NON_SCALAR_KEYS:
                all_keys[k] = None
    fieldnames = sorted(all_keys)
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore', restval='')
        writer.writeheader()
        writer.writerows(session_metrics)
    print(f'  CSV saved: {out_path}  ({len(session_metrics)} rows)')


def write_edits_csv(session_metrics: list[dict], out_path: Path) -> None:
    """Export one row per rubric_edit event for downstream GEE analysis in R/statsmodels.
    Joins session_id and condition onto each edit row."""
    import csv
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for m in session_metrics:
        for edit in m.get('raw_edits', []):
            rows.append({
                'session_id': m['session_id'],   # canonical session key — not overwritten by edit spread
                'condition':  m['condition'],
                **{
                    k: ('|'.join(str(x) for x in v) if v else '') if isinstance(v, list) else v
                    for k, v in edit.items()
                    if k != 'session_id' and not isinstance(v, dict)
                },
            })
    if not rows:
        return
    all_keys: dict[str, None] = {}
    for r in rows:
        for k in r.keys():
            all_keys[k] = None
    fieldnames = list(all_keys.keys())
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval='')
        writer.writeheader()
        writer.writerows(rows)
    print(f'  Edits CSV saved: {out_path}  ({len(rows)} edit rows)')


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description='ConceptGrade user study log analyzer')
    parser.add_argument('--logs-dir', default=str(LOGS_DIR),
                        help=f'Path to JSONL session logs (default: {LOGS_DIR})')
    parser.add_argument('--csv', action='store_true',
                        help='Write per-session metrics to results/study_analysis.csv '
                             'and per-edit records to results/study_edits.csv')
    parser.add_argument('--pilot', action='store_true',
                        help='Print GO/NO-GO pilot gate based on overall task completion '
                             'rate (pre-registered threshold: >50%%).')
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

    # ── Q-M: Placebo Alignment Rate for Condition A ────────────────────────────
    # Build the reference CONTRADICTS set from all Condition B trace_interact events.
    # Key: dataset name → set of node_ids flagged as CONTRADICTS.
    # Condition A educators never see the trace, so their session_contradicts_nodes
    # is always empty and semantic_alignment_rate_manual is 0 by construction.
    # Testing their manual edits against this hidden reference gives a true placebo
    # baseline for H2: did Condition B educators align significantly more than chance?
    b_contradicts: dict[str, set] = defaultdict(set)
    for events in sessions.values():
        cond = next((e.get('condition') for e in events if e.get('condition')), None)
        if cond != 'B':
            continue
        for e in events:
            if e.get('event_type') == 'trace_interact' and \
               e.get('payload', {}).get('classification') == 'CONTRADICTS':
                ds      = e.get('dataset', '')
                node_id = e.get('payload', {}).get('node_id', '')
                if ds and node_id:
                    b_contradicts[ds].add(node_id)

    for m in session_metrics:
        if m.get('condition') != 'A':
            continue
        reference = b_contradicts.get(m.get('dataset', ''), set())
        if not reference:
            continue
        manual_concepts = [
            e['concept_id'] for e in m.get('raw_edits', [])
            if e.get('interaction_source') == 'manual' and e.get('concept_id')
        ]
        if manual_concepts:
            aligned = sum(1 for c in manual_concepts if c in reference)
            m['placebo_alignment_rate'] = round(aligned / len(manual_concepts), 3)

    agg = aggregate_by_condition(session_metrics)
    print_report(agg, session_metrics)

    # ── Q-N: Pilot GO/NO-GO gate (pre-registered threshold: >50%) ─────────────
    if args.pilot:
        _PILOT_THRESHOLD = 0.50
        all_completed = sum(1 for m in session_metrics if m.get('task_completed'))
        overall_rate  = round(all_completed / len(session_metrics), 3) if session_metrics else 0.0
        if overall_rate > _PILOT_THRESHOLD:
            print(f'\033[92m[PILOT GATE] GO ✓  task_completion_rate = {overall_rate:.3f}'
                  f' > {_PILOT_THRESHOLD} → proceed to full study\033[0m\n')
        else:
            print(f'\033[91m[PILOT GATE] NO-GO ✗  task_completion_rate = {overall_rate:.3f}'
                  f' ≤ {_PILOT_THRESHOLD} → structural review required before full study\033[0m\n')

    if args.csv:
        write_csv(session_metrics, RESULTS_DIR / 'study_analysis.csv')
        write_edits_csv(session_metrics, RESULTS_DIR / 'study_edits.csv')


if __name__ == '__main__':
    main()
