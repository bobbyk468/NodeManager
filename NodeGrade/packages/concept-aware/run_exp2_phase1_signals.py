#!/usr/bin/env python3
"""
run_exp2_phase1_signals.py — Phase 1 of Experiment #2 (question-held-out CV
with in-fold retuning, independent review round 4, decisive experiment #1
of the "not fixed" list).

Purpose
-------
Populate raw, UNFILTERED per-response signals (concept graph with every
extracted concept's confidence score, Bloom's/SOLO, misconceptions,
holistic score) for all 120 Mohler samples, using the exact same pipeline
configuration as the evaluated headline run (self-consistency extraction,
confidence-weighted comparator, frozen v1.0-expert KG -- data/ds_knowledge_graph.json,
NOT the current live builder which is v1.1/187-relationship and would
silently evaluate against the wrong KG), EXCEPT with
extraction_confidence_threshold=0.0 so concepts below the paper's default
tau=0.70 are NOT dropped before caching.

Why this matters: the production pipeline (conceptgrade/pipeline.py) filters
low-confidence concepts BEFORE writing to its LLM-response cache, so the
existing ~/.conceptgrade_cache.json only ever stores the tau=0.70-filtered
view and cannot support testing tau values below 0.70. Running once with
tau=0.0 preserves every concept's raw confidence, from which any candidate
tau (above OR below 0.70) can be reconstructed purely offline in Phase 2 --
no LLM re-extraction needed for the grid search itself.

This also means holistic_score, blooms, solo, and misconceptions -- which
do not depend on the confidence threshold -- only need to be computed once
here and are reused unchanged for every (fold, tau) combination in Phase 2.
Only the concept graph / KG-comparison signals vary with tau.

Output: data/exp2_raw_signals.json -- one entry per Mohler sample:
    {loader_idx, qid, human_score, question, reference_answer, student_answer,
     concept_graph (unfiltered, all concepts + confidences),
     blooms, solo, misconceptions, holistic_score}

Run:
    python3 run_exp2_phase1_signals.py            # populate (resumable)
    python3 run_exp2_phase1_signals.py --status    # show progress only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"
OUT_PATH = DATA / "exp2_raw_signals.json"
SIGNAL_CACHE_PATH = DATA / "exp2_signal_cache.json"  # dedicated cache, does NOT touch ~/.conceptgrade_cache.json


def _load_gemini_key() -> str:
    env_path = BASE.parent / "backend" / ".env"
    with env_path.open() as f:
        for line in f:
            m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
            if m:
                return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def _build_pipeline():
    from conceptgrade.pipeline import ConceptGradePipeline
    from conceptgrade.cache import ResponseCache
    from knowledge_graph.domain_graph import DomainKnowledgeGraph

    with (DATA / "ds_knowledge_graph.json").open() as f:
        kg_data = json.load(f)
    frozen_v1_kg = DomainKnowledgeGraph.from_dict(kg_data)
    assert frozen_v1_kg.num_relationships == 138, (
        f"Expected the frozen v1.0-expert KG (138 relationships), got "
        f"{frozen_v1_kg.num_relationships}. Refusing to run Phase 1 against "
        f"the wrong KG version -- check data/ds_knowledge_graph.json."
    )

    key = _load_gemini_key()
    pipeline = ConceptGradePipeline(
        api_key=key,
        domain_graph=frozen_v1_kg,
        model="gemini-2.5-flash",
        use_self_consistency=True,
        use_confidence_weighting=True,
        use_llm_verifier=False,       # Phase 2 handles verification, batched
        extraction_confidence_threshold=0.0,  # keep ALL concepts + confidences
        sc_inter_run_delay=1.0,
    )
    # Dedicated cache file: never touches ~/.conceptgrade_cache.json (which
    # holds tau=0.70-filtered entries from unrelated prior runs) and is
    # itself repo-tracked/resumable across sessions.
    pipeline.cache = ResponseCache(cache_file=str(SIGNAL_CACHE_PATH))
    return pipeline


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true", help="Show progress only, no new calls")
    args = ap.parse_args()

    from datasets.mohler_loader import load_mohler_sample
    dataset = load_mohler_sample()

    existing: dict = {}
    if OUT_PATH.exists():
        existing = {str(r["loader_idx"]): r for r in json.loads(OUT_PATH.read_text())}

    if args.status:
        print(f"Signals populated: {len(existing)}/{len(dataset.samples)}")
        return 0

    pipeline = _build_pipeline()

    out_rows = list(existing.values())
    done_idx = set(existing.keys())

    for i, s in enumerate(dataset.samples):
        if str(i) in done_idx:
            continue
        print(f"[{i+1}/{len(dataset.samples)}] qid={s.question_id} ...", flush=True)
        assessment = pipeline.assess_student(
            student_id=f"loader{i}",
            question=s.question,
            answer=s.student_answer,
            reference_answer=s.reference_answer,
        )
        row = {
            "loader_idx": i,
            "qid": s.question_id,
            "human_score": s.score_avg,
            "question": s.question,
            "reference_answer": s.reference_answer,
            "student_answer": s.student_answer,
            "concept_graph": assessment.concept_graph,
            "blooms": assessment.blooms,
            "solo": assessment.solo,
            "misconceptions": assessment.misconceptions,
            "holistic_score": pipeline.cache.get(
                pipeline.cache.key(f"llm_sc{int(pipeline.use_self_consistency)}",
                                    pipeline.model, s.question, s.student_answer)
            ).get("holistic_score"),
        }
        out_rows.append(row)
        OUT_PATH.write_text(json.dumps(out_rows, indent=2))
        n_concepts = len(row["concept_graph"].get("concepts", []))
        print(f"    -> {n_concepts} raw concepts, holistic={row['holistic_score']}")

    print(f"\nDone: {len(out_rows)}/{len(dataset.samples)} signals in {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
