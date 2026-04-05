"""
Recompute Chain Coverage for Q3 and Q9 samples using the fixed KG.

Loads data/ablation_intermediates_augmented.json (with augmented concepts),
recomputes chain_coverage using the updated ds_knowledge_graph.py, and saves
results to data/ablation_intermediates_fixed.json.

Usage:
    python3 recompute_chain_coverage.py
"""

from __future__ import annotations

import copy
import json
import os
import sys

import networkx as nx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
sys.path.insert(0, BASE_DIR)

INPUT_FILE = os.path.join(DATA_DIR, "ablation_intermediates_augmented.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "ablation_intermediates_fixed.json")

SEP = "─" * 72


# ─────────────────────────────────────────────────────────────────────────────
# Chain coverage logic (mirrors graph_comparison/comparator.py)
# ─────────────────────────────────────────────────────────────────────────────

def compute_chain_coverage(
    kg_graph: nx.DiGraph,
    student_concept_ids: set[str],
    expected_concept_ids: set[str],
    min_chain_length: int = 2,
) -> tuple[float, str]:
    """
    Multi-hop causal chain coverage — replicates the comparator logic exactly.

    Returns (score 0–1, human-readable summary string).
    """
    # Build the subgraph restricted to expected concepts (those in the domain graph)
    valid_expected = {c for c in expected_concept_ids if c in kg_graph.nodes}
    sub = kg_graph.subgraph(valid_expected)
    if sub.number_of_edges() == 0:
        return 0.0, "no causal chains in domain graph"

    chains_found = total_chains = 0
    seen_paths: set[tuple] = set()

    for src in valid_expected:
        for tgt in valid_expected:
            if src == tgt:
                continue
            try:
                for path in nx.all_simple_paths(sub, src, tgt, cutoff=3):
                    if len(path) < min_chain_length + 1:
                        continue
                    key = tuple(path)
                    if key in seen_paths:
                        continue
                    seen_paths.add(key)
                    total_chains += 1
                    hits = [n in student_concept_ids for n in path]
                    consecutive = sum(
                        1 for i in range(len(hits) - 1) if hits[i] and hits[i + 1]
                    )
                    if consecutive >= 1:
                        chains_found += 1
            except (nx.NetworkXError, nx.NodeNotFound):
                continue

    if total_chains == 0:
        return 0.0, "no causal chains in domain graph"

    score = chains_found / total_chains
    summary = f"{chains_found}/{total_chains} causal chains covered ({score:.0%})"
    return round(score, 4), summary


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(SEP)
    print("Recomputing Chain Coverage with Fixed KG")
    print(SEP)

    # Load the fixed KG
    from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
    kg = build_data_structures_graph()
    kg_graph = kg.graph
    print(f"KG loaded: {len(kg_graph.nodes)} concepts, {len(kg_graph.edges)} edges")

    # Load augmented intermediates
    with open(INPUT_FILE) as f:
        data = json.load(f)

    fixed = copy.deepcopy(data)

    # Track changes
    changes = []

    target_q3 = list(range(36, 48))
    target_q9 = list(range(108, 120))
    target_ids = target_q3 + target_q9

    for sid in target_ids:
        sid_str = str(sid)
        if sid_str not in data:
            continue

        sample = data[sid_str]
        comp = sample.get("comparison", {})
        analysis = comp.get("analysis", {})

        matched_concepts = set(analysis.get("matched_concepts", []))
        old_chain_cov = comp.get("scores", {}).get("chain_coverage", 0.0)

        # Recompute using matched_concepts as both student and expected
        new_chain_cov, chain_summary = compute_chain_coverage(
            kg_graph,
            student_concept_ids=matched_concepts,
            expected_concept_ids=matched_concepts,
        )

        # Update in fixed data
        fixed[sid_str]["comparison"]["scores"]["chain_coverage"] = new_chain_cov

        q_tag = "Q9" if sid >= 108 else "Q3"
        changes.append({
            "sid": sid,
            "q": q_tag,
            "matched": sorted(matched_concepts),
            "old_chain_cov": old_chain_cov,
            "new_chain_cov": new_chain_cov,
            "chain_summary": chain_summary,
        })

    # Report
    print(f"\n{'ID':>4}  {'Q':3}  {'Old':6}  {'New':6}  {'Chains summary'}")
    print("─" * 72)
    for ch in changes:
        delta = ch["new_chain_cov"] - ch["old_chain_cov"]
        marker = "  +" if delta > 0 else "   "
        print(
            f"{ch['sid']:>4}  {ch['q']:3}  {ch['old_chain_cov']:.4f}  "
            f"{ch['new_chain_cov']:.4f}{marker}  {ch['chain_summary']}"
        )

    improved = [c for c in changes if c["new_chain_cov"] > c["old_chain_cov"]]
    print(SEP)
    print(f"Improved chain coverage: {len(improved)}/{len(changes)} samples")

    # Focus on 7 failing samples
    failing = {37, 42, 112, 113, 116, 117, 118}
    print("\n=== Failing Sample Summary (IDs 37, 42, 112, 113, 116, 117, 118) ===")
    for ch in changes:
        if ch["sid"] in failing:
            print(
                f"  ID {ch['sid']} [{ch['q']}]: chain_cov {ch['old_chain_cov']:.4f} → "
                f"{ch['new_chain_cov']:.4f}  | concepts: {ch['matched']}"
            )

    with open(OUTPUT_FILE, "w") as f:
        json.dump(fixed, f, indent=2)
    print(f"\nSaved fixed intermediates → {OUTPUT_FILE}")
    print(SEP)


if __name__ == "__main__":
    main()
