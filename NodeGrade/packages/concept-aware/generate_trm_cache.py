"""
generate_trm_cache.py — Pre-compute TRM metrics for all DigiKlausur answers.

Produces data/digiklausur_trm_cache.json, a static lookup table that maps
student_answer_id → TRM metrics. Study session logs use this file for
post-hoc analysis: Spearman ρ(leap_count, dwell_time_ms).

TRM Metric Definitions (must mirror VerifierReasoningPanel.tsx exactly):

  topological_gap_count:
    Count of consecutive parsed_step pairs (i, i+1) where:
      • Both steps have ≥1 kg_node, AND
      • The sets of kg_nodes share no common element.
    If either step has no kg_nodes, the pair is NOT counted as a gap
    (a step without KG grounding cannot anchor a topological comparison).

  grounding_density:
    Fraction of parsed_steps where len(kg_nodes) > 0.
    Range [0, 1]. 0 = zero-grounding degenerate case (all steps unanchored).

  verification_status:
    'green'  — grounding_density >= 0.50 and topological_gap_count == 0
    'yellow' — grounding_density >= 0.25 or topological_gap_count <= 2
    'red'    — grounding_density < 0.25 or topological_gap_count > 2

Usage:
    cd packages/concept-aware
    python generate_trm_cache.py

Output:
    data/digiklausur_trm_cache.json
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
TRACES_FILE = DATA_DIR / "digiklausur_lrm_traces.json"
CACHE_FILE  = DATA_DIR / "digiklausur_trm_cache.json"


# ── TRM metric helpers (identical logic to VerifierReasoningPanel.tsx) ─────────

def has_topological_gap(step_a: dict, step_b: dict) -> bool:
    """
    Returns True if steps a and b both have KG nodes but share none —
    meaning the reasoning jumped to a disconnected region of the KG.

    Mirrors hasTopologicalGap() in VerifierReasoningPanel.tsx:
      if (stepA.kg_nodes.length === 0 || stepB.kg_nodes.length === 0) return false;
      const nodesA = new Set(stepA.kg_nodes);
      return !stepB.kg_nodes.some(n => nodesA.has(n));
    """
    nodes_a = set(step_a.get("kg_nodes", []))
    nodes_b = set(step_b.get("kg_nodes", []))
    if not nodes_a or not nodes_b:
        return False
    return nodes_a.isdisjoint(nodes_b)


def compute_trm_metrics(parsed_steps: list[dict]) -> dict:
    """
    Compute topological_gap_count, grounding_density, and verification_status
    from a list of parsed reasoning steps.
    """
    if not parsed_steps:
        # Zero-grounding degenerate case: no steps → can't evaluate TRM
        return {
            "topological_gap_count": 0,
            "grounding_density": 0.0,
            "verification_status": "red",
            "reasoning_step_count": 0,
            "grounded_step_count": 0,
            "zero_grounding_degenerate": True,
        }

    # Gap count: walk consecutive pairs
    gap_count = 0
    for i in range(1, len(parsed_steps)):
        if has_topological_gap(parsed_steps[i - 1], parsed_steps[i]):
            gap_count += 1

    # Grounding density: fraction of steps with ≥1 kg_node
    grounded = sum(1 for s in parsed_steps if len(s.get("kg_nodes", [])) > 0)
    density = grounded / len(parsed_steps)

    # Zero-grounding degenerate case: every step is unanchored (density == 0)
    # These answers are false negatives — gap_count = 0 masks hallucinations.
    zero_grounding_degenerate = density == 0.0

    # Verification status (traffic-light encoding)
    if density >= 0.50 and gap_count == 0:
        status = "green"
    elif density >= 0.25 or gap_count <= 2:
        status = "yellow"
    else:
        status = "red"

    return {
        "topological_gap_count": gap_count,
        "grounding_density": round(density, 4),
        "verification_status": status,
        "reasoning_step_count": len(parsed_steps),
        "grounded_step_count": grounded,
        "zero_grounding_degenerate": zero_grounding_degenerate,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TRACES_FILE.exists():
        print(f"ERROR: Traces file not found: {TRACES_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(TRACES_FILE) as f:
        traces = json.load(f)

    cache: dict[str, dict] = {}
    degenerate_count = 0
    gap_distribution: dict[int, int] = {}

    for answer_id, trace in traces.items():
        parsed_steps = trace.get("parsed_steps", [])
        metrics = compute_trm_metrics(parsed_steps)

        # Build cache entry
        cache[str(answer_id)] = {
            "student_answer_id": answer_id,
            "dataset": "digiklausur",
            **metrics,
            # Supporting metadata for analysis scripts
            "lrm_valid": trace.get("lrm_valid"),
            "lrm_model": trace.get("lrm_model"),
            "human_score": trace.get("human_score"),
            "c5_score": trace.get("c5_score"),
            "net_delta": trace.get("net_delta"),
        }

        if metrics["zero_grounding_degenerate"]:
            degenerate_count += 1

        g = metrics["topological_gap_count"]
        gap_distribution[g] = gap_distribution.get(g, 0) + 1

    # Write output
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

    # Summary report
    print(f"✅ TRM cache written → {CACHE_FILE}")
    print(f"   Total answers:            {len(cache)}")
    print(f"   Zero-grounding degenerate: {degenerate_count} "
          f"({100 * degenerate_count / len(cache):.1f}%)")
    print(f"\n   Gap count distribution:")
    for g in sorted(gap_distribution):
        bar = "█" * gap_distribution[g]
        print(f"     {g:2d} leaps: {gap_distribution[g]:4d}  {bar[:50]}")

    # Spot-check: show a high-gap example
    high_gap = max(cache.values(), key=lambda e: e["topological_gap_count"])
    print(f"\n   Highest gap count: answer {high_gap['student_answer_id']} "
          f"({high_gap['topological_gap_count']} leaps, "
          f"{high_gap['grounding_density']*100:.0f}% grounded)")


if __name__ == "__main__":
    main()
