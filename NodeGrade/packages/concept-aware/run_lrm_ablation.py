"""
LRM Ablation Runner — Stage 3a/3b batch evaluation.

Compares two Stage 3 verifier backends on the same answer pool:
  Condition A: Gemini 2.5 Flash      (current production verifier — no trace)
  Condition B: DeepSeek-R1 via API   (LRM — exposes reasoning_content trace)

Datasets evaluated:
  mohler       — all 120 answers (from offline_eval_results.json)
  digiklausur  — random 300-answer sample (from digiklausur_eval_results.json)

Outputs
-------
  data/mohler_lrm_traces.json       — SampleTraceResponse per answer (Condition B)
  data/digiklausur_lrm_traces.json  — same format for sampled DigiKlausur answers
  data/lrm_ablation_summary.json    — MAE comparison: Flash vs R1-Distill per dataset

Usage
-----
  # Set your DeepSeek API key (get one at https://platform.deepseek.com)
  export DEEPSEEK_API_KEY=sk-...

  # Run (async batch, all answers in parallel with concurrency cap)
  python run_lrm_ablation.py --datasets mohler digiklausur --sample-n 300

  # Use a specific DeepSeek model (default: deepseek-reasoner = DeepSeek-R1)
  python run_lrm_ablation.py --datasets mohler --deepseek-model deepseek-reasoner

  # Dry run with Gemini fallback (no trace produced, for testing pipeline):
  python run_lrm_ablation.py --datasets mohler --gemini-key YOUR_KEY --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import time
from pathlib import Path
from typing import Optional

from conceptgrade.lrm_verifier import LRMVerifier, LRMVerifierResult
from conceptgrade.trace_parser  import parse_trace, summarise_trace

DATA_DIR = Path(__file__).parent / 'data'


# ── Load dataset helpers ──────────────────────────────────────────────────────

def load_mohler_samples() -> list[dict]:
    """
    Load Mohler answers.

    Priority:
      1. data/mohler_eval_results.json   — has pre-computed concept scores (preferred)
      2. MohlerDataset embedded loader   — fallback, provides raw Q/A + human scores
         (matched_concepts / c5_score will be empty / 0 in this case)

    KG enrichment (either path):
      data/mohler_auto_kg.json — if present, adds kg_nodes/kg_edges/kg_edges_text
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    # Path 1: pre-computed eval results with concept data
    eval_path = DATA_DIR / 'mohler_eval_results.json'
    if eval_path.exists():
        with open(eval_path) as f:
            raw = json.load(f)
        results = raw.get('results', [])
        if results:
            return _enrich_with_kg(results, 'mohler')

    # Path 2: embedded MohlerDataset (always available)
    from datasets.mohler_loader import load_mohler_sample
    dataset = load_mohler_sample()
    samples = []
    for i, s in enumerate(dataset.samples):
        samples.append({
            'id':              i,
            'question':        s.question,
            'student_answer':  s.student_answer,
            'reference_answer': s.reference_answer,
            'human_score':     s.score_avg,
            'cllm_score':      0.0,   # not pre-computed — MAE vs CLLM will be 0
            'c5_score':        0.0,   # not pre-computed — ablation MAE placeholder
            'matched_concepts': [],
            'missing_concepts': [],
            'chain_pct':       0,
        })
    return _enrich_with_kg(samples, 'mohler')


def _enrich_with_kg(samples: list[dict], dataset: str) -> list[dict]:
    """Add kg_nodes / kg_edges / kg_edges_text from {dataset}_auto_kg.json if present."""
    kg_nodes_by_q: dict[str, list[str]] = {}
    kg_edges_by_q: dict[str, list[str]] = {}
    kg_text_by_q:  dict[str, str]       = {}

    kg_path = DATA_DIR / f'{dataset}_auto_kg.json'
    if kg_path.exists():
        with open(kg_path) as f:
            kg_raw = json.load(f)
        for qid, qdata in (kg_raw.get('question_kgs') or {}).items():
            nodes = qdata.get('expected_concepts', [])
            edges = list({e.get('type', '') for e in qdata.get('relationships', [])})
            text  = '; '.join(
                f"{e.get('source','')} {e.get('type','')} {e.get('target','')}"
                for e in qdata.get('relationships', [])[:10]
            )
            kg_nodes_by_q[qid] = nodes
            kg_edges_by_q[qid] = edges
            kg_text_by_q[qid]  = text

    for s in samples:
        qid = str(s.get('question_id', s.get('id', '')))
        s.setdefault('kg_nodes',     kg_nodes_by_q.get(qid, []))
        s.setdefault('kg_edges',     kg_edges_by_q.get(qid, []))
        s.setdefault('kg_edges_text', kg_text_by_q.get(qid, ''))
        s.setdefault('matched_concepts', [])
        s.setdefault('missing_concepts', [])
        s.setdefault('chain_pct', 0)

    return samples


def load_eval_samples(dataset: str, sample_n: Optional[int] = None) -> list[dict]:
    """
    Load samples from {dataset}_eval_results.json.

    If eval_results lacks question/student_answer text (stored separately in
    {dataset}_dataset.json), joins on 'id' to recover the raw text.
    """
    path = DATA_DIR / f'{dataset}_eval_results.json'
    with open(path) as f:
        raw = json.load(f)
    results = raw.get('results', [])
    if sample_n and len(results) > sample_n:
        rng = random.Random(42)   # deterministic sample for reproducibility
        results = rng.sample(results, sample_n)

    # Load raw text from {dataset}_dataset.json if eval results lack it
    raw_text_by_id: dict[str, dict] = {}
    dataset_path = DATA_DIR / f'{dataset}_dataset.json'
    if dataset_path.exists():
        with open(dataset_path) as f:
            dataset_rows = json.load(f)
        if isinstance(dataset_rows, list):
            for row in dataset_rows:
                raw_text_by_id[str(row.get('id', ''))] = row

    # KG enrichment
    kg_nodes_by_q: dict[str, list[str]] = {}
    kg_edges_by_q: dict[str, list[str]] = {}
    kg_text_by_q:  dict[str, str]       = {}
    kg_path = DATA_DIR / f'{dataset}_auto_kg.json'
    if kg_path.exists():
        with open(kg_path) as f:
            kg_raw = json.load(f)
        for qid, qdata in (kg_raw.get('question_kgs') or {}).items():
            nodes  = qdata.get('expected_concepts', [])
            edges  = list({e.get('type', '') for e in qdata.get('relationships', [])})
            text   = '; '.join(
                f"{e.get('source','')} {e.get('type','')} {e.get('target','')}"
                for e in qdata.get('relationships', [])[:10]
            )
            kg_nodes_by_q[qid] = nodes
            kg_edges_by_q[qid] = edges
            kg_text_by_q[qid]  = text

    enriched = []
    for r in results:
        sid = str(r.get('id', ''))
        qid = str(r.get('question_id', sid))
        raw_text = raw_text_by_id.get(sid, {})
        enriched.append({
            'id':              r.get('id'),
            'question':        r.get('question') or raw_text.get('question', ''),
            'student_answer':  r.get('student_answer') or raw_text.get('student_answer', ''),
            'reference_answer': r.get('reference_answer') or raw_text.get('reference_answer', ''),
            'human_score':     r.get('human_score', 0),
            'cllm_score':      r.get('cllm_score', 0),
            'c5_score':        r.get('c5_score', 0),
            'matched_concepts': r.get('matched_concepts', []),
            'missing_concepts': r.get('missing_concepts', []),
            'chain_pct':       r.get('chain_pct', 0),
            'kg_nodes':        kg_nodes_by_q.get(qid, []),
            'kg_edges':        kg_edges_by_q.get(qid, []),
            'kg_edges_text':   kg_text_by_q.get(qid, ''),
        })
    return enriched


# ── Cache helpers ─────────────────────────────────────────────────────────────

def load_cache(out_path: Path) -> dict[str, dict]:
    """Load existing trace results from disk (empty dict if file absent)."""
    if out_path.exists():
        try:
            with open(out_path) as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(out_path: Path, results: dict[str, dict]) -> None:
    """Atomically write results dict to disk (temp file + rename)."""
    tmp = out_path.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(results, f, indent=2)
    tmp.replace(out_path)


# ── Batch async runner ────────────────────────────────────────────────────────

async def run_batch(
    samples: list[dict],
    verifier: LRMVerifier,
    domain: str,
    out_path: Path,
    concurrency: int = 4,
    force: bool = False,
) -> dict[str, dict]:
    """
    Run verifier over all samples with a bounded concurrency semaphore.

    Cache behaviour
    ---------------
    Loads existing results from out_path before starting. Any sample whose ID
    already has a non-error entry in the cache is skipped — the API is NOT
    called again. Results are saved to disk after every completed sample so a
    mid-run crash loses at most one in-flight request.

    Pass --force to ignore the cache and re-run everything.

    Returns {str(sample_id): SampleTraceResponse dict} (cache + new results).
    """
    # Seed results dict from cache
    results: dict[str, dict] = {} if force else load_cache(out_path)

    # Filter to samples not yet cached (or errored on a previous run)
    pending = [
        s for s in samples
        if force
        or str(s['id']) not in results
        or results[str(s['id'])].get('lrm_model') == 'error'
    ]

    cached_count = len(samples) - len(pending)
    total        = len(samples)

    if cached_count:
        print(f'  Cache: {cached_count}/{total} already done — skipping API calls for those.')
    if not pending:
        print(f'  All samples cached. Use --force to re-run.')
        return results

    print(f'  Calling API for {len(pending)} remaining sample(s)…')

    semaphore = asyncio.Semaphore(concurrency)
    lock      = asyncio.Lock()   # protects results dict + file write

    async def process(sample: dict, global_idx: int) -> None:
        async with semaphore:
            sid = str(sample['id'])
            try:
                result: LRMVerifierResult = await verifier.averify(
                    domain             = domain,
                    question           = sample['question'],
                    student_answer     = sample['student_answer'],
                    matched_concepts   = sample['matched_concepts'],
                    missing_concepts   = sample['missing_concepts'],
                    kg_nodes           = sample['kg_nodes'],
                    kg_edge_types      = sample['kg_edges'],
                    kg_edges_text      = sample['kg_edges_text'],
                    chain_coverage_pct = float(str(sample.get('chain_pct') or '0').replace('%', '') or 0),
                )
                entry = {
                    'id':              sample['id'],
                    'dataset':         domain,
                    'lrm_valid':       result.valid,
                    'lrm_reasoning':   result.reasoning,
                    'lrm_model':       result.model_used,
                    'lrm_latency_ms':  result.latency_ms,
                    'parsed_steps':    result.parsed_steps,
                    'trace_summary':   result.trace_summary,
                    'human_score':     sample['human_score'],
                    'cllm_score':      sample['cllm_score'],
                    'c5_score':        sample['c5_score'],
                    'net_delta':       result.net_confidence_delta,
                }
                async with lock:
                    results[sid] = entry
                    save_cache(out_path, results)   # incremental write
                print(f'  [{global_idx+1}/{total}] id={sid}  valid={result.valid}'
                      f'  steps={len(result.parsed_steps)}  latency={result.latency_ms}ms  [saved]')
            except Exception as e:
                print(f'  [{global_idx+1}/{total}] id={sid}  ERROR: {e}')
                async with lock:
                    # Store errors too so the cache knows this ID was attempted
                    results[sid] = {
                        'id': sample['id'], 'dataset': domain,
                        'lrm_valid': None, 'lrm_reasoning': f'error: {e}',
                        'lrm_model': 'error', 'lrm_latency_ms': 0,
                        'parsed_steps': [], 'trace_summary': {},
                        'human_score': sample['human_score'],
                        'cllm_score':  sample['cllm_score'],
                        'c5_score':    sample['c5_score'],
                        'net_delta':   0.0,
                    }
                    # Don't persist errors to cache — let them be retried next run

    # Map each pending sample back to its global index (for progress display)
    pending_set = {str(s['id']) for s in pending}
    global_indices = {str(s['id']): i for i, s in enumerate(samples)}

    await asyncio.gather(*[
        process(s, global_indices[str(s['id'])])
        for s in pending
        if str(s['id']) in pending_set
    ])
    return results


def _mae_at_scale(human: list, c5: list, deltas: list, scale: float) -> float:
    """MAE when LRM additive delta is multiplied by `scale`."""
    adjusted = [max(0.0, min(5.0, c + scale * d)) for c, d in zip(c5, deltas)]
    return sum(abs(h - a) for h, a in zip(human, adjusted)) / len(human)


def _mae_binary_gate(human: list, c5: list, valids: list, penalty: float = 0.7) -> float:
    """
    MAE under a binary validity gate:
      if valid=True  → keep c5_score unchanged
      if valid=False → c5_score * penalty   (multiplicative, not subtractive)

    A multiplicative penalty punishes high-scoring "concept salads" heavily
    while applying a softer touch to already low-scoring answers.
    """
    adjusted = [c * penalty if not v else c for c, v in zip(c5, valids)]
    adjusted = [max(0.0, min(5.0, a)) for a in adjusted]
    return sum(abs(h - a) for h, a in zip(human, adjusted)) / len(human)


def find_optimal_lrm_scale(
    human: list, c5: list, deltas: list,
    lo: float = 0.0, hi: float = 1.0, steps: int = 200,
) -> tuple[float, float]:
    """Grid search over scale ∈ [lo, hi] to minimise LRM-adjusted MAE."""
    best_scale, best_mae = lo, _mae_at_scale(human, c5, deltas, lo)
    for i in range(1, steps + 1):
        s = lo + (hi - lo) * i / steps
        m = _mae_at_scale(human, c5, deltas, s)
        if m < best_mae:
            best_mae, best_scale = m, s
    return round(best_scale, 4), round(best_mae, 4)


def _wilcoxon_stats(errors_a: list[float], errors_b: list[float]) -> dict:
    """
    Wilcoxon signed-rank test on paired absolute errors, plus rank-biserial r
    and Cohen's d as effect size measures.

    H0: errors_a and errors_b come from the same distribution.
    Alternative: two-sided (we report which condition wins separately).
    """
    try:
        from scipy.stats import wilcoxon as _wilcoxon
        import math

        diffs = [a - b for a, b in zip(errors_a, errors_b)]
        nonzero = [d for d in diffs if d != 0]
        n_nz = len(nonzero)
        if n_nz < 10:
            return {'wilcoxon_p': None, 'rank_biserial_r': None, 'cohens_d': None,
                    'note': f'too few non-zero diffs ({n_nz})'}

        stat, p = _wilcoxon(errors_a, errors_b, alternative='two-sided', zero_method='wilcox')

        # Rank-biserial correlation: r = 1 - 4*T_min / (n*(n+1))
        # where stat = T_min (smaller of T+ and T-)
        rank_biserial = round(1.0 - (4.0 * stat) / (n_nz * (n_nz + 1)), 4)

        # Cohen's d on paired differences
        mean_d = sum(diffs) / len(diffs)
        std_d  = math.sqrt(sum((x - mean_d) ** 2 for x in diffs) / (len(diffs) - 1))
        cohens_d = round(mean_d / std_d, 4) if std_d > 0 else 0.0

        return {
            'wilcoxon_p':        round(float(p), 6),
            'rank_biserial_r':   rank_biserial,
            'cohens_d':          cohens_d,
            'n_nonzero_diffs':   n_nz,
        }
    except Exception as e:
        return {'wilcoxon_p': None, 'rank_biserial_r': None, 'cohens_d': None,
                'note': str(e)}


def compute_ablation_mae(trace_results: dict[str, dict]) -> dict:
    """
    Compute per-condition MAE from stored scores.

    Conditions evaluated:
      C_LLM     — pure LLM baseline
      C5        — 5-stage KG pipeline (no LRM adjustment)
      LRM raw   — C5 ± raw net_delta  (additive, scale=1.0)
      LRM cal   — C5 ± calibrated net_delta  (grid-searched scale)
      LRM gate  — binary validity gate: invalid answers multiplied by 0.7

    Statistical tests (Wilcoxon signed-rank, two-sided):
      C5 vs C_LLM, LRM-gate vs C5
    Effect sizes: rank-biserial correlation, Cohen's d on paired diffs.
    """
    rows   = [v for v in trace_results.values() if v.get('human_score') is not None]
    human  = [v['human_score'] for v in rows]
    cllm   = [v['cllm_score']  for v in rows]
    c5     = [v['c5_score']    for v in rows]
    deltas = [v.get('net_delta', 0.0) for v in rows]
    valids = [bool(v.get('lrm_valid', True)) for v in rows]
    n = len(human)
    if n == 0:
        return {'n': 0}

    # Per-sample absolute errors
    err_cllm = [abs(h - c) for h, c in zip(human, cllm)]
    err_c5   = [abs(h - c) for h, c in zip(human, c5)]

    mae_cllm    = sum(err_cllm) / n
    mae_c5      = sum(err_c5) / n
    mae_lrm_raw = _mae_at_scale(human, c5, deltas, scale=1.0)
    best_scale, mae_lrm_cal = find_optimal_lrm_scale(human, c5, deltas)
    mae_lrm_gate = _mae_binary_gate(human, c5, valids, penalty=0.7)

    # Per-sample errors for gated condition (for Wilcoxon)
    gated = [c * 0.7 if not v else c for c, v in zip(c5, valids)]
    err_gate = [abs(h - a) for h, a in zip(human, gated)]

    def pct(base, new):
        return round((base - new) / base * 100, 2) if base > 0 else 0.0

    return {
        'n':                  n,
        # MAE values
        'mae_cllm':           round(mae_cllm, 4),
        'mae_c5':             round(mae_c5, 4),
        'mae_lrm_raw':        round(mae_lrm_raw, 4),
        'mae_lrm_calibrated': mae_lrm_cal,
        'mae_lrm_gate':       round(mae_lrm_gate, 4),
        'lrm_scale':          best_scale,
        # Relative improvements
        'c5_vs_cllm_pct':     pct(mae_cllm, mae_c5),
        'lrm_raw_vs_c5_pct':  pct(mae_c5, mae_lrm_raw),
        'lrm_cal_vs_c5_pct':  pct(mae_c5, mae_lrm_cal),
        'lrm_gate_vs_c5_pct': pct(mae_c5, mae_lrm_gate),
        # Statistical tests
        'stats_c5_vs_cllm':   _wilcoxon_stats(err_c5, err_cllm),
        'stats_gate_vs_c5':   _wilcoxon_stats(err_gate, err_c5),
        'stats_cal_vs_c5':    _wilcoxon_stats(
            [abs(h - max(0.0, min(5.0, c + best_scale * d)))
             for h, c, d in zip(human, c5, deltas)], err_c5),
        # LRM trace quality
        'valid_rate':         round(sum(valids) / n, 4),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

DOMAIN_MAP = {
    'mohler':      'Computer Science (Data Structures)',
    'digiklausur': 'Neural Networks',
    'kaggle_asag': 'Elementary Science',
}

async def main_async(args: argparse.Namespace) -> None:
    verifier = LRMVerifier(
        deepseek_api_key       = args.deepseek_key,
        deepseek_model         = args.deepseek_model,
        gemini_api_key         = args.gemini_key,
        gemini_thinking_budget = args.gemini_thinking_budget,
        use_gemini_primary     = args.use_gemini,
        max_trace_steps        = 20,
    )

    all_summaries: dict[str, dict] = {}

    for dataset in args.datasets:
        print(f'\n{"="*60}')
        print(f'Dataset: {dataset}')
        print(f'{"="*60}')

        if dataset == 'mohler':
            samples = load_mohler_samples()
        else:
            samples = load_eval_samples(dataset, sample_n=args.sample_n)

        if args.dry_run:
            samples = samples[:3]
            print(f'  [DRY RUN] Using first 3 samples only')

        out_path = DATA_DIR / f'{dataset}_lrm_traces.json'
        cached_before = len(load_cache(out_path)) if not args.force else 0
        print(f'  Loaded {len(samples)} samples  '
              f'(cache: {cached_before} already done) — running LRM verifier ...')
        t0 = time.monotonic()

        trace_results = await run_batch(
            samples     = samples,
            verifier    = verifier,
            domain      = DOMAIN_MAP.get(dataset, dataset),
            out_path    = out_path,
            concurrency = args.concurrency,
            force       = args.force,
        )

        elapsed = time.monotonic() - t0
        new_calls = len(trace_results) - cached_before
        print(f'  Done in {elapsed:.1f}s'
              f'  ({new_calls} new API calls'
              + (f', {elapsed/new_calls:.1f}s/call avg' if new_calls else '')
              + f')  total cached: {len(trace_results)}')
        print(f'  Cache file: {out_path} ({out_path.stat().st_size//1024} KB)')

        # Compute ablation MAE
        summary = compute_ablation_mae(trace_results)
        summary['dataset'] = dataset
        summary['elapsed_s'] = round(elapsed, 1)
        all_summaries[dataset] = summary
        print(f'\n  Ablation MAE summary (n={summary.get("n")}):')
        print(f'    C_LLM baseline:       {summary.get("mae_cllm", "n/a")}')
        print(f'    C5 (5-stage):         {summary.get("mae_c5", "n/a")}  '
              f'({summary.get("c5_vs_cllm_pct", 0):+.1f}% vs C_LLM)')

        s_c5 = summary.get('stats_c5_vs_cllm', {})
        print(f'      Wilcoxon p={s_c5.get("wilcoxon_p", "n/a")}  '
              f'r_rb={s_c5.get("rank_biserial_r", "n/a")}  '
              f'd={s_c5.get("cohens_d", "n/a")}')

        print(f'    LRM raw (scale=1.0):  {summary.get("mae_lrm_raw", "n/a")}  '
              f'({summary.get("lrm_raw_vs_c5_pct", 0):+.1f}% vs C5)')
        print(f'    LRM calibrated:       {summary.get("mae_lrm_calibrated", "n/a")}  '
              f'({summary.get("lrm_cal_vs_c5_pct", 0):+.1f}% vs C5,  '
              f'scale={summary.get("lrm_scale", "n/a")})')
        print(f'    LRM gate (×0.7):      {summary.get("mae_lrm_gate", "n/a")}  '
              f'({summary.get("lrm_gate_vs_c5_pct", 0):+.1f}% vs C5  '
              f'valid_rate={summary.get("valid_rate", "n/a"):.1%})')

        s_gate = summary.get('stats_gate_vs_c5', {})
        print(f'      Wilcoxon p={s_gate.get("wilcoxon_p", "n/a")}  '
              f'r_rb={s_gate.get("rank_biserial_r", "n/a")}  '
              f'd={s_gate.get("cohens_d", "n/a")}')

    # Save overall summary
    summary_path = DATA_DIR / 'lrm_ablation_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(all_summaries, f, indent=2)
    print(f'\nAblation summary saved: {summary_path}')


def main() -> None:
    parser = argparse.ArgumentParser(description='LRM Stage 3 ablation runner')
    parser.add_argument('--datasets',    nargs='+', default=['mohler'],
                        choices=['mohler', 'digiklausur', 'kaggle_asag'],
                        help='Datasets to evaluate (default: mohler)')
    parser.add_argument('--sample-n',       type=int, default=300,
                        help='Max samples to draw from DigiKlausur/Kaggle (default: 300)')
    parser.add_argument('--deepseek-key',   default=os.environ.get('DEEPSEEK_API_KEY', ''),
                        help='DeepSeek API key (or set DEEPSEEK_API_KEY env var)')
    parser.add_argument('--deepseek-model', default='deepseek-reasoner',
                        help='DeepSeek model (default: deepseek-reasoner = R1)')
    parser.add_argument('--gemini-key',     default=os.environ.get('GEMINI_API_KEY', ''),
                        help='Gemini API key (or set GEMINI_API_KEY env var)')
    parser.add_argument('--use-gemini',  action='store_true',
                        help='Use Gemini 2.5 Flash with thinking as primary backend (~10 s/sample '
                             'vs ~58 s for DeepSeek-R1). Produces equivalent reasoning traces.')
    parser.add_argument('--gemini-thinking-budget', type=int, default=8192,
                        help='Gemini thinking token budget (default: 8192). Set 0 to disable thinking.')
    parser.add_argument('--concurrency', type=int, default=4,
                        help='Max concurrent LRM requests (default: 4)')
    parser.add_argument('--dry-run',    action='store_true',
                        help='Run on first 3 samples only (testing)')
    parser.add_argument('--force',      action='store_true',
                        help='Ignore cache and re-run all samples (overwrites existing results)')
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
