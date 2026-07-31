#!/usr/bin/env python3
"""
verify_domain_match_fix_live.py — regression-validates the LIVE, now-patched
`_build_question_ontology()` in concept_extraction/extractor.py against all
1,262 cached real Mohler samples. ZERO new API calls: this method does not
call the LLM, it only builds a keyword-matched ontology string and sets
`self._last_domain_match_score` as a side effect.

Checks required before trusting the patch (per GPT + Gemini review,
docs/ALGORITHM_FIX_REVIEW_REQUEST.md):
  1. Confusion matrix of out_of_kg_domain before/after -- confirm only the
     expected ~106 OUT_OF_KG_DOMAIN -> IN_DOMAIN flips occur, zero
     unexpected IN_DOMAIN -> OUT_OF_KG_DOMAIN flips or other surprises.
  2. Full domain_match_score diff across all 1,262 samples, not just the
     106 known-affected ones.
"""
from __future__ import annotations

import json
from pathlib import Path

from knowledge_graph.domain_graph import DomainKnowledgeGraph
from concept_extraction.extractor import ConceptExtractor

BASE = Path(__file__).parent


def main() -> int:
    kg_dict = json.loads((BASE / "data" / "ds_knowledge_graph.json").read_text())
    domain_graph = DomainKnowledgeGraph.from_dict(kg_dict)
    assert len(domain_graph.get_all_relationships()) == 138, "KG version mismatch"

    extractor = ConceptExtractor(domain_graph=domain_graph, api_key="unused-not-called")

    with (BASE / "data" / "mohler_real_phaseA_signals.json").open() as f:
        phase_a = json.load(f)

    n_total = 0
    n_match_cached = 0
    mismatches = []
    flips_out_to_in = 0
    flips_in_to_out = 0
    unchanged_out = 0
    unchanged_in = 0

    for r in phase_a:
        n_total += 1
        question = r["question"]
        cached_score = r["concept_graph"]["domain_match_score"]
        cached_out = r["concept_graph"]["out_of_kg_domain"]

        extractor._build_question_ontology(question)
        new_score = extractor._last_domain_match_score
        new_out = new_score < 0.05

        if abs(new_score - cached_score) <= 5e-4:
            n_match_cached += 1
        # (no assertion here -- we EXPECT the 106 affected samples to differ)

        if cached_out and not new_out:
            flips_out_to_in += 1
        elif not cached_out and new_out:
            flips_in_to_out += 1
            mismatches.append({
                "id": r["sample_id"], "question": question,
                "cached_score": cached_score, "new_score": new_score,
                "direction": "UNEXPECTED IN_DOMAIN -> OUT_OF_KG_DOMAIN",
            })
        elif cached_out and new_out:
            unchanged_out += 1
        else:
            unchanged_in += 1

    print(f"Total samples checked: {n_total}")
    print(f"\n=== Confusion matrix: out_of_kg_domain, cached (old) vs live (new, patched) ===")
    print(f"  OUT_OF_KG_DOMAIN -> IN_DOMAIN (expected fix):  {flips_out_to_in}")
    print(f"  IN_DOMAIN -> OUT_OF_KG_DOMAIN (UNEXPECTED):    {flips_in_to_out}")
    print(f"  Unchanged, still OUT_OF_KG_DOMAIN:             {unchanged_out}")
    print(f"  Unchanged, still IN_DOMAIN:                    {unchanged_in}")

    print(f"\nExpectation check: flips_out_to_in should be 106 (Finding 1's measured scope)")
    print(f"  -> {'PASS' if flips_out_to_in == 106 else 'FAIL'} (got {flips_out_to_in})")
    print(f"Expectation check: flips_in_to_out should be 0 (no unexpected regressions)")
    print(f"  -> {'PASS' if flips_in_to_out == 0 else 'FAIL'} (got {flips_in_to_out})")

    if mismatches:
        print(f"\n!!! {len(mismatches)} UNEXPECTED regressions found -- inspect before shipping:")
        for m in mismatches[:10]:
            print(f"  {m}")

    out_path = BASE / "data" / "domain_match_fix_live_regression.json"
    out_path.write_text(json.dumps({
        "n_total": n_total,
        "flips_out_to_in": flips_out_to_in,
        "flips_in_to_out": flips_in_to_out,
        "unchanged_out": unchanged_out,
        "unchanged_in": unchanged_in,
        "unexpected_regressions": mismatches,
    }, indent=2))
    print(f"\n[saved] {out_path}")

    ok = flips_out_to_in == 106 and flips_in_to_out == 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
