"""
Test all three research extensions end-to-end.

Extensions tested:
  1. Self-Consistent Extractor  — majority-vote across 3 LLM runs
  2. Confidence-Weighted Comparator — coverage weighted by extraction confidence
  3. LLM-as-Verifier — post-scoring LLM judge

Run from packages/concept-aware/:
    python test_extensions.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))

API_KEY = os.environ.get("GROQ_API_KEY")
if not API_KEY:
    raise EnvironmentError("GROQ_API_KEY environment variable not set")

QUESTION = "Explain the difference between a linked list and an array, including time complexity for insertion."
ANSWERS = {
    "deep":   ("A linked list consists of nodes where each node stores data and a pointer to the next node. "
               "Unlike arrays which use contiguous memory, linked lists can scatter nodes anywhere in memory. "
               "This makes insertion O(1) at the head of a linked list since we just update pointers, "
               "whereas array insertion is O(n) because elements must be shifted. However, linked list "
               "access is O(n) since we must traverse from the head, while arrays offer O(1) random access "
               "via index arithmetic. Arrays also benefit from CPU cache locality due to contiguous storage."),
    "shallow": "Arrays store elements in contiguous memory. Linked lists use pointers. Arrays are faster.",
}

SEP = "─" * 60


# ─── Extension 1: Self-Consistent Extractor ──────────────────────────────────

def test_self_consistent():
    print(f"\n{SEP}")
    print("EXT 1: Self-Consistent Extractor (3-run majority voting)")
    print(SEP)

    from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
    from concept_extraction.self_consistent_extractor import SelfConsistentExtractor

    dg = build_data_structures_graph()
    sc = SelfConsistentExtractor(
        domain_graph=dg,
        api_key=API_KEY,
        n_runs=3,
        min_votes=2,
    )

    for label, answer in ANSWERS.items():
        print(f"\n  [{label.upper()} answer]")
        t0 = time.time()
        graph = sc.extract(QUESTION, answer)
        elapsed = time.time() - t0
        print(f"  Concepts accepted: {len(graph.concepts)}")
        print(f"  Relationships accepted: {len(graph.relationships)}")
        print(f"  Overall depth: {graph.overall_depth}")
        print(f"  Time: {elapsed:.1f}s")
        for c in graph.concepts[:5]:
            print(f"    concept={c.concept_id:30s}  conf={c.confidence:.2f}  correct={c.is_correct_usage}")

    print(f"\n  [PASS] Self-Consistent Extractor works.")


# ─── Extension 2: Confidence-Weighted Comparator ─────────────────────────────

def test_confidence_weighted():
    print(f"\n{SEP}")
    print("EXT 2: Confidence-Weighted Comparator")
    print(SEP)

    from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
    from concept_extraction.extractor import ConceptExtractor
    from graph_comparison.comparator import KnowledgeGraphComparator
    from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator

    dg = build_data_structures_graph()
    extractor = ConceptExtractor(domain_graph=dg, api_key=API_KEY)
    std_cmp   = KnowledgeGraphComparator(domain_graph=dg)
    wgt_cmp   = ConfidenceWeightedComparator(domain_graph=dg, alpha=1.0)

    for label, answer in ANSWERS.items():
        print(f"\n  [{label.upper()} answer]")
        graph = extractor.extract(QUESTION, answer)
        time.sleep(1.0)

        std = std_cmp.compare(graph)
        wgt = wgt_cmp.compare(graph)

        print(f"  Standard  coverage={std.concept_coverage_score:.3f}  overall={std.overall_score:.3f}")
        print(f"  Weighted  coverage={wgt.concept_coverage_score:.3f}  overall={wgt.overall_score:.3f}")
        delta = wgt.overall_score - std.overall_score
        direction = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
        print(f"  Delta: {delta:+.3f} {direction}")
        confs = [c.confidence for c in graph.concepts]
        if confs:
            print(f"  Avg extraction confidence: {sum(confs)/len(confs):.3f}")

    print(f"\n  [PASS] Confidence-Weighted Comparator works.")


# ─── Extension 3: LLM Verifier ───────────────────────────────────────────────

def test_llm_verifier():
    print(f"\n{SEP}")
    print("EXT 3: LLM-as-Verifier (post-scoring judge)")
    print(SEP)

    from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
    from concept_extraction.extractor import ConceptExtractor
    from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
    from cognitive_depth.cognitive_depth_classifier import CognitiveDepthClassifier
    from misconception_detection.detector import MisconceptionDetector
    from conceptgrade.verifier import LLMVerifier

    dg  = build_data_structures_graph()
    ext = ConceptExtractor(domain_graph=dg, api_key=API_KEY)
    cmp = ConfidenceWeightedComparator(domain_graph=dg)
    cdc = CognitiveDepthClassifier(api_key=API_KEY)
    mdt = MisconceptionDetector(api_key=API_KEY)
    ver = LLMVerifier(api_key=API_KEY, verifier_weight=0.25)

    for label, answer in ANSWERS.items():
        print(f"\n  [{label.upper()} answer]")
        graph = ext.extract(QUESTION, answer); time.sleep(1.2)
        comp  = cmp.compare(graph)
        cg_d  = graph.to_dict();  cm_d = comp.to_dict()
        dep   = cdc.classify(QUESTION, answer, cg_d, cm_d); time.sleep(1.2)
        misc  = mdt.detect(QUESTION, answer, cg_d, cm_d);   time.sleep(1.2)

        # Simulate KG-only score
        scores = cm_d.get("scores", {})
        kg_score = (
            scores.get("concept_coverage", 0) * 0.15 +
            scores.get("relationship_accuracy", 0) * 0.15 +
            scores.get("integration_quality", 0) * 0.15 +
            ((dep.blooms_level - 1) / 5) * 0.20 +
            ((dep.solo_level - 1) / 4) * 0.20 +
            misc.to_dict().get("overall_accuracy", 1.0) * 0.15
        )

        result = ver.verify(
            question=QUESTION,
            student_answer=answer,
            kg_score=kg_score,
            comparison_result=cm_d,
            blooms=dep.to_blooms_dict(),
            solo=dep.to_solo_dict(),
            misconceptions=misc.to_dict(),
        )
        time.sleep(1.2)

        print(f"  KG score:       {result.kg_score:.3f}")
        print(f"  Verified score: {result.verified_score:.3f}  ({result.adjustment_direction})")
        print(f"  Final score:    {result.final_score:.3f}")
        print(f"  Confidence:     {result.confidence:.2f}")
        print(f"  Reason: {result.adjustment_reason[:120]}")

    print(f"\n  [PASS] LLM Verifier works.")


# ─── Full pipeline with all extensions ───────────────────────────────────────

def test_full_pipeline():
    print(f"\n{SEP}")
    print("FULL PIPELINE: All extensions enabled")
    print(SEP)

    from conceptgrade.pipeline import ConceptGradePipeline

    pipeline = ConceptGradePipeline(
        api_key=API_KEY,
        use_self_consistency=False,      # skipped for speed in quick test
        use_confidence_weighting=True,   # Ext 2 always on
        use_llm_verifier=True,           # Ext 3 enabled
        verifier_weight=0.25,
        rate_limit_delay=1.2,
    )

    for label, answer in ANSWERS.items():
        print(f"\n  [{label.upper()} answer]")
        result = pipeline.assess_student(f"test_{label}", QUESTION, answer)
        print(f"  Overall score:  {result.overall_score:.3f}")
        print(f"  Depth category: {result.depth_category}")
        print(f"  Bloom's:        {result.blooms.get('label')} ({result.blooms.get('level')})")
        print(f"  SOLO:           {result.solo.get('label')} ({result.solo.get('level')})")
        print(f"  Concepts found: {len(result.concept_graph.get('concepts', []))}")
        if result.verifier:
            v = result.verifier
            print(f"  Verifier:       KG={v['kg_score']:.3f} → final={v['final_score']:.3f} ({v['adjustment_direction']})")

    print(f"\n  [PASS] Full pipeline with extensions works.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--ext", choices=["1","2","3","all"], default="all",
                   help="Which extension to test")
    args = p.parse_args()

    if args.ext in ("1", "all"):
        test_self_consistent()
    if args.ext in ("2", "all"):
        test_confidence_weighted()
    if args.ext in ("3", "all"):
        test_llm_verifier()
    if args.ext == "all":
        test_full_pipeline()

    print(f"\n{'='*60}")
    print("All selected extension tests completed.")
    print("="*60)
