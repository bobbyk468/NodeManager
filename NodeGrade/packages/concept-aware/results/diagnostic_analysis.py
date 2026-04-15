"""
Diagnostic Analysis — responding to Gemini's review questions Q1 and Q2.

Q1: CONTRADICTS frequency by KG node
   → Are the LRM's contradictions targeting rubric-aligned nodes (over-penalisation)
     or hallucinated out-of-scope concepts (domain boundary mismatch)?

Q2: Chain Coverage distribution for Mohler
   → Is the distribution bimodal (0% or 100%)? That would confirm the KG edges are
     too rigid to capture natural student phrasing, explaining why C5 = C_LLM.

Also prints: Mohler score distribution to expose the MAE=2.25 anomaly.

Usage: python results/diagnostic_analysis.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR    = Path(__file__).parent.parent / 'data'
RESULTS_DIR = Path(__file__).parent


def load_traces(dataset: str) -> list[dict]:
    path = DATA_DIR / f'{dataset}_lrm_traces.json'
    with open(path) as f:
        d = json.load(f)
    return [v for v in d.values() if v.get('lrm_model') not in ('error', None)]


def section(title: str) -> None:
    print(f'\n{"="*64}')
    print(f'  {title}')
    print(f'{"="*64}')


# ── Q1: CONTRADICTS frequency by KG node ──────────────────────────────────────

def contradicts_by_node(traces: list[dict], label: str, top_n: int = 20) -> dict:
    """
    For every CONTRADICTS step, collect the KG nodes it references.
    Returns {node_id: count} sorted descending.
    """
    node_counter: Counter = Counter()
    total_contradicts = 0

    for t in traces:
        for step in t.get('parsed_steps', []):
            if step.get('classification') == 'CONTRADICTS':
                total_contradicts += 1
                for node in step.get('kg_nodes', []):
                    node_counter[node.strip()] += 1

    section(f'Q1 — CONTRADICTS by KG node  [{label}]  (total={total_contradicts})')
    print(f'  {"KG Node":<40} {"Count":>6}  {"% of CONTRADICTS":>16}')
    print(f'  {"-"*64}')
    top = node_counter.most_common(top_n)
    for node, cnt in top:
        pct = cnt / total_contradicts * 100 if total_contradicts else 0
        print(f'  {node:<40} {cnt:>6}  {pct:>15.1f}%')

    if not top:
        print('  (no CONTRADICTS steps found)')

    # Also report: how many CONTRADICTS steps reference NO KG nodes at all
    # (those are likely hallucinated concepts outside the rubric)
    no_node_steps = sum(
        1 for t in traces
        for step in t.get('parsed_steps', [])
        if step.get('classification') == 'CONTRADICTS' and not step.get('kg_nodes')
    )
    if total_contradicts:
        print(f'\n  Steps with NO KG node reference (potential hallucination):')
        print(f'  {no_node_steps}/{total_contradicts} = {no_node_steps/total_contradicts*100:.1f}%')
        print('  (High % → domain boundary mismatch; Low % → over-penalisation of rubric nodes)')

    return dict(node_counter)


# ── Q2: Chain Coverage distribution ───────────────────────────────────────────

def chain_coverage_distribution(traces: list[dict], label: str) -> None:
    """
    Print a histogram of chain_coverage_pct for a dataset's traces.
    Bimodal distribution (spike at 0% AND 100%) would confirm KG rigidity.

    For Mohler: falls back to ablation_intermediates_fixed.json which stores
    comparison.scores.chain_coverage (0–1 scale) with actual pipeline output.
    """
    # Try to get chain_pct from trace entries first
    coverages = []
    for t in traces:
        cp = t.get('chain_pct') or t.get('chain_coverage_pct')
        if cp is not None:
            try:
                coverages.append(float(str(cp).replace('%', '')))
            except ValueError:
                pass

    section(f'Q2 — Chain Coverage Distribution  [{label}]  (n will be updated)')

    if not coverages:
        # Mohler fallback: ablation_intermediates_fixed.json has comparison.scores.chain_coverage
        intermediates_path = DATA_DIR / 'ablation_intermediates_fixed.json'
        if intermediates_path.exists():
            with open(intermediates_path) as f:
                im = json.load(f)
            for entry in im.values():
                cov = entry.get('comparison', {}).get('scores', {}).get('chain_coverage')
                if cov is not None:
                    coverages.append(float(cov) * 100)  # 0–1 → 0–100
            if coverages:
                print(f'  (source: ablation_intermediates_fixed.json, n={len(coverages)})')
        if not coverages:
            print(f'  No chain_pct data found — skipping.')
            return

    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    counts = [0] * (len(bins) - 1)
    for v in coverages:
        for i in range(len(bins) - 1):
            if bins[i] <= v <= bins[i + 1]:
                counts[i] += 1
                break

    total = len(coverages)
    print(f'  {"Range":<12} {"Count":>6}  Bar')
    print(f'  {"-"*50}')
    for i, cnt in enumerate(counts):
        bar = '█' * int(cnt / total * 40)
        label_str = f'{bins[i]}–{bins[i+1]}%'
        print(f'  {label_str:<12} {cnt:>6}  {bar}  ({cnt/total*100:.1f}%)')

    zero_pct  = sum(1 for v in coverages if v == 0.0)
    full_pct  = sum(1 for v in coverages if v == 100.0)
    mean_cov  = sum(coverages) / len(coverages)
    print(f'\n  Mean coverage: {mean_cov:.1f}%')
    print(f'  Exactly 0%: {zero_pct}/{total} ({zero_pct/total*100:.1f}%)')
    print(f'  Exactly 100%: {full_pct}/{total} ({full_pct/total*100:.1f}%)')
    bimodal_pct = (zero_pct + full_pct) / total * 100
    print(f'  Bimodal (0% or 100%): {zero_pct+full_pct}/{total} ({bimodal_pct:.1f}%)')
    if bimodal_pct > 50:
        print('  ⚠  CONFIRMED: Majority of answers score at extremes → KG edges too rigid')
    else:
        print('  OK: Coverage is distributed across the range')


# ── Mohler score distribution ─────────────────────────────────────────────────

def score_distribution(traces: list[dict], label: str) -> None:
    """Print human vs C5 vs C_LLM score distributions to expose MAE=2.25 anomaly."""
    section(f'Score Distribution  [{label}]')

    human_scores = [v['human_score'] for v in traces if v.get('human_score') is not None]
    c5_scores    = [v['c5_score']    for v in traces if v.get('c5_score')    is not None]
    cllm_scores  = [v['cllm_score']  for v in traces if v.get('cllm_score')  is not None]

    def hist(scores: list, name: str) -> None:
        if not scores:
            return
        n = len(scores)
        mean = sum(scores) / n
        buckets: dict[int, int] = defaultdict(int)
        for s in scores:
            buckets[round(s)] += 1
        print(f'  {name} (mean={mean:.2f}):')
        for score in sorted(buckets):
            bar = '█' * int(buckets[score] / n * 30)
            print(f'    {score}: {bar} {buckets[score]}')

    hist(human_scores, 'Human')
    hist(c5_scores,    'C5   ')
    hist(cllm_scores,  'C_LLM')

    # How many C5 scores == 0 (complete KG miss)?
    zero_c5 = sum(1 for s in c5_scores if s == 0.0)
    n = len(c5_scores)
    print(f'\n  C5=0 (complete KG miss): {zero_c5}/{n} ({zero_c5/n*100:.1f}%)')


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # Mohler
    mohler = load_traces('mohler')
    contradicts_by_node(mohler, 'Mohler')
    chain_coverage_distribution(mohler, 'mohler')
    score_distribution(mohler, 'Mohler')

    # DigiKlausur
    digi = load_traces('digiklausur')
    contradicts_by_node(digi, 'DigiKlausur')

    # Cross-dataset CONTRADICTS comparison
    section('Q1 Summary — CONTRADICTS step composition comparison')
    for label, traces in [('Mohler', mohler), ('DigiKlausur', digi)]:
        total = sum(len(t.get('parsed_steps', [])) for t in traces)
        supp  = sum(1 for t in traces for s in t.get('parsed_steps', [])
                    if s.get('classification') == 'SUPPORTS')
        cont  = sum(1 for t in traces for s in t.get('parsed_steps', [])
                    if s.get('classification') == 'CONTRADICTS')
        unc   = sum(1 for t in traces for s in t.get('parsed_steps', [])
                    if s.get('classification') == 'UNCERTAIN')
        no_node_cont = sum(1 for t in traces for s in t.get('parsed_steps', [])
                           if s.get('classification') == 'CONTRADICTS'
                           and not s.get('kg_nodes'))
        print(f'\n  {label}:')
        print(f'    SUPPORTS {supp/total*100:.0f}%  CONTRADICTS {cont/total*100:.0f}%  UNCERTAIN {unc/total*100:.0f}%')
        if cont:
            print(f'    CONTRADICTS with no KG node: {no_node_cont}/{cont} = {no_node_cont/cont*100:.1f}%  '
                  f'(hallucination rate)')

    print()


if __name__ == '__main__':
    main()
