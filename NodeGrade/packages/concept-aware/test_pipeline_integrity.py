"""
test_pipeline_integrity.py -- regression tests for the Phase 0 integrity
fixes from the 2026-08-19 external review (REPRODUCIBILITY.md Finding 6):

  1. assess_class() must propagate reference_answer to every
     assess_student() call, instead of silently dropping it.
  2. Cache keys must change when reference_answer, the extraction
     confidence threshold, the KG (domain, version), or the verifier
     prompt version change -- otherwise a stale cached result can be
     served after any of these change, exactly the failure mode that
     let the Finding-5 prompt change go undetected by caching.

No real API key or network access required -- both properties are
testable by inspecting call arguments / cache keys directly, without
executing an actual LLM call.

Run from packages/concept-aware/:
    python3 test_pipeline_integrity.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def test_assess_class_propagates_reference_answer():
    print("\n=== assess_class() reference_answer propagation ===")
    from conceptgrade.pipeline import ConceptGradePipeline

    pipeline = ConceptGradePipeline(api_key="dummy-not-used")
    calls = []

    def fake_assess_student(sid, question, answer, reference_answer=""):
        calls.append({"sid": sid, "question": question, "answer": answer,
                       "reference_answer": reference_answer})
        from conceptgrade.pipeline import StudentAssessment
        return StudentAssessment(student_id=sid, question=question, answer=answer)

    with patch.object(pipeline, "assess_student", side_effect=fake_assess_student):
        pipeline.assess_class(
            question="What is a stack?",
            student_answers={"s1": "A LIFO structure.", "s2": "A FIFO structure."},
            reference_answer="A stack is a LIFO (last-in-first-out) data structure.",
        )

    check("both students were assessed", len(calls) == 2, f"got {len(calls)} calls")
    check(
        "reference_answer reached every call",
        all(c["reference_answer"] == "A stack is a LIFO (last-in-first-out) data structure." for c in calls),
        f"reference_answers seen: {[c['reference_answer'] for c in calls]}",
    )

    # Default (omitted) reference_answer should still propagate as "" explicitly,
    # not silently vanish in a way that's indistinguishable from a bug.
    calls.clear()
    with patch.object(pipeline, "assess_student", side_effect=fake_assess_student):
        pipeline.assess_class(question="What is a stack?", student_answers={"s1": "..."})
    check(
        "omitted reference_answer defaults to empty string, not lost silently",
        calls[0]["reference_answer"] == "",
    )


def test_cache_key_sensitivity():
    print("\n=== Cache key sensitivity to semantic inputs ===")
    from conceptgrade.pipeline import ConceptGradePipeline

    from conceptgrade.cache import CACHE_SCHEMA_VERSION as _CSV, canonical_hash as _ch
    p1 = ConceptGradePipeline(api_key="dummy-not-used")

    question, answer = "What is a stack?", "A LIFO structure."

    def _llm_key(ect=None, kg_version=None, sc_n_runs=None, sc_min_votes=None,
                 prompt_hash=None, config_fingerprint=None, reference="Reference A"):
        ect = p1.extraction_confidence_threshold if ect is None else ect
        kg_version = p1.domain_graph.version if kg_version is None else kg_version
        sc_n_runs = p1.sc_n_runs if sc_n_runs is None else sc_n_runs
        sc_min_votes = p1.sc_min_votes if sc_min_votes is None else sc_min_votes
        prompt_hash = "base" if prompt_hash is None else prompt_hash
        cfg = config_fingerprint or "none"
        return p1.cache.key(
            f"llm_{_CSV}"
            f"_sc{int(p1.use_self_consistency)}"
            f"_screns{sc_n_runs}_scmv{sc_min_votes}"
            f"_ect{ect}"
            f"_kg{p1.domain_graph.domain}v{kg_version}"
            f"_prompts{prompt_hash}"
            f"_cfg{cfg}",
            p1.model, question, answer, reference,
        )

    llm_key_base = _llm_key()
    check(
        "llm_key changes when reference_answer changes",
        llm_key_base != _llm_key(reference="Reference B"),
    )
    check(
        "llm_key changes when extraction_confidence_threshold changes",
        llm_key_base != _llm_key(ect=0.99),
    )
    check(
        "llm_key changes when KG version changes",
        llm_key_base != _llm_key(kg_version="9.9-different"),
    )
    check(
        "llm_key changes when sc_n_runs changes",
        llm_key_base != _llm_key(sc_n_runs=(p1.sc_n_runs or 0) + 1),
    )
    check(
        "llm_key changes when sc_min_votes changes",
        llm_key_base != _llm_key(sc_min_votes=(p1.sc_min_votes or 0) + 1),
    )
    check(
        "llm_key changes when the extraction/depth/misconception prompt "
        "hash changes (simulates an edit to any of extractor.py, "
        "cognitive_depth_classifier.py, or misconception_detection/detector.py "
        "-- 2026-08-19, third review round: llm_key previously had no way "
        "to detect a prompt-text edit at all)",
        llm_key_base != _llm_key(prompt_hash=_ch({"extraction_system": "a different prompt"})),
    )
    check(
        "llm_key changes when config_fingerprint changes (simulates the "
        "pipeline being built from a different named PipelineConfig via "
        "conceptgrade.configs.build_pipeline)",
        llm_key_base != _llm_key(config_fingerprint="some-config-hash-abc123"),
    )

    from conceptgrade.verifier import VERIFIER_PROMPT_VERSION_SAG
    from conceptgrade.cache import CACHE_SCHEMA_VERSION, canonical_hash
    p2 = ConceptGradePipeline(api_key="dummy-not-used")  # verifier_weight=1.0 default

    def _ver_key(prompt_version, comparison, blooms, solo, misconceptions):
        config_fingerprint = (
            f"verifier_{CACHE_SCHEMA_VERSION}"
            f"_sc{int(p2.use_self_consistency)}"
            f"_cw{int(p2.use_confidence_weighting)}"
            f"_sure{int(p2.use_sure_verifier)}"
            f"_vw{p2.verifier.verifier_weight}"
            f"_promptver{prompt_version}"
            f"_kg{p2.domain_graph.domain}v{p2.domain_graph.version}"
            f"_comparator{type(p2.comparator).__name__}"
        )
        evidence_hash = canonical_hash({
            "comparison": comparison, "blooms": blooms, "solo": solo, "misconceptions": misconceptions,
        })
        return p2.cache.key(config_fingerprint, p2.model, question, answer, "Reference A", evidence_hash)

    base_comparison = {"scores": {"concept_coverage": 0.8, "relationship_accuracy": 0.5}}
    base_blooms = {"level": 2, "label": "Understand"}
    base_solo = {"level": 2, "label": "Unistructural"}
    base_misc = {"total_misconceptions": 0, "misconceptions": []}

    key_base = _ver_key(VERIFIER_PROMPT_VERSION_SAG, base_comparison, base_blooms, base_solo, base_misc)
    key_prompt_changed = _ver_key(VERIFIER_PROMPT_VERSION_SAG + "_different", base_comparison, base_blooms, base_solo, base_misc)
    check(
        "verifier cache key changes when VERIFIER_PROMPT_VERSION_SAG changes "
        "(this is the exact check that should catch a future repeat of the "
        "Finding-5 staleness incident)",
        key_base != key_prompt_changed,
    )

    # The critical new check (2026-08-19): a comparator VALUE change with NO
    # flag change -- exactly what the relationship-direction fix produces
    # (same class, same config, different scores) -- must still invalidate
    # the cache. This is what the old enumerate-every-flag scheme could
    # never catch by construction.
    changed_comparison = {"scores": {"concept_coverage": 0.8, "relationship_accuracy": 0.0}}  # e.g. post-fix
    key_evidence_changed = _ver_key(VERIFIER_PROMPT_VERSION_SAG, changed_comparison, base_blooms, base_solo, base_misc)
    check(
        "verifier cache key changes when comparison_result VALUES change with "
        "no config flag changing (the relationship-direction-fix scenario)",
        key_base != key_evidence_changed,
    )

    changed_misc = {"total_misconceptions": 1, "misconceptions": [{"severity": "critical"}]}
    key_misc_changed = _ver_key(VERIFIER_PROMPT_VERSION_SAG, base_comparison, base_blooms, base_solo, changed_misc)
    check(
        "verifier cache key changes when misconceptions content changes",
        key_base != key_misc_changed,
    )

    changed_blooms = {"level": 4, "label": "Analyze"}
    key_blooms_changed = _ver_key(VERIFIER_PROMPT_VERSION_SAG, base_comparison, changed_blooms, base_solo, base_misc)
    check(
        "verifier cache key changes when Bloom's level changes",
        key_base != key_blooms_changed,
    )

    # A pipeline built directly (not via configs.py) must have a defined,
    # falsy config_fingerprint -- confirms the cache-key components above
    # don't silently break for the common non-named-config case.
    check(
        "a directly-constructed pipeline has config_fingerprint=None (not "
        "an AttributeError -- llm_key/ver_key construction depends on this "
        "attribute always existing)",
        p1.config_fingerprint is None and p1.config_name is None,
    )

    # A pipeline built FROM a named config gets a real, non-None fingerprint,
    # and two different named configs get two different fingerprints.
    from conceptgrade.configs import REGISTRY, build_pipeline
    built = {name: build_pipeline(cfg, api_key="dummy-not-used") for name, cfg in REGISTRY.items()}
    for name, p in built.items():
        check(
            f"pipeline built from named config {name!r} has a non-None config_fingerprint",
            p.config_fingerprint is not None and p.config_name == name,
        )
    fingerprints = {name: p.config_fingerprint for name, p in built.items()}
    if len(fingerprints) >= 2:
        vals = list(fingerprints.values())
        check(
            "different named configs produce different config_fingerprints",
            len(set(vals)) == len(vals),
            f"fingerprints={fingerprints}",
        )

    # 2026-08-19, fourth review round: config_fingerprint() must NOT change
    # when only pinned_commit/name/description change -- those are
    # provenance/identity metadata, not semantic configuration. The prior
    # version hashed pinned_commit too, so commit 7dc6085 (which only
    # re-pinned two configs) silently changed every cache key built from
    # them, contradicting its own commit message's "only metadata, no
    # pipeline behavior" claim. This is the regression test for that bug.
    from dataclasses import replace
    from conceptgrade.configs import DEPLOYED_SAG_GEMINI, config_fingerprint
    base_fp = config_fingerprint(DEPLOYED_SAG_GEMINI)
    repinned_fp = config_fingerprint(replace(DEPLOYED_SAG_GEMINI, pinned_commit="deadbeef"))
    check(
        "config_fingerprint is UNCHANGED when only pinned_commit changes "
        "(re-pinning a config to a new commit must not invalidate caches "
        "built under it -- pinned_commit is provenance, not semantics)",
        base_fp == repinned_fp,
    )
    renamed_fp = config_fingerprint(replace(DEPLOYED_SAG_GEMINI, name="x", description="y"))
    check(
        "config_fingerprint is UNCHANGED when only name/description change",
        base_fp == renamed_fp,
    )
    sc_changed_fp = config_fingerprint(replace(DEPLOYED_SAG_GEMINI, sc_n_runs=99))
    check(
        "config_fingerprint DOES change when a semantic field (sc_n_runs) changes",
        base_fp != sc_changed_fp,
    )


def test_named_config_enforcement():
    print("\n=== conceptgrade/configs.py: declared fields are enforced, not decorative ===")
    from conceptgrade.configs import PipelineConfig, build_pipeline, ConfigProvenanceError, REGISTRY

    for name, config in REGISTRY.items():
        try:
            p = build_pipeline(config, api_key="dummy-not-used")
            check(
                f"config {name!r} builds and the loaded KG version matches what it declares",
                p.domain_graph.version == config.kg_version,
                f"declared={config.kg_version!r} actual={p.domain_graph.version!r}",
            )
        except ConfigProvenanceError as e:
            check(f"config {name!r} builds without raising", False, str(e))

    bad_kg = PipelineConfig(
        name="_test_bad_kg", description="test", model="gemini-2.5-flash", provider="google",
        verifier_prompt_version_sag="sag_v2_skepticism_2026-08-18",
        use_self_consistency=False, use_confidence_weighting=True, use_llm_verifier=True, verifier_weight=1.0,
        kg_version="9.9-nonexistent", kg_snapshot_path="data/ds_knowledge_graph.json",
    )
    try:
        build_pipeline(bad_kg, api_key="dummy-not-used")
        check("KG version mismatch is rejected, not silently built", False)
    except ConfigProvenanceError:
        check("KG version mismatch is rejected, not silently built", True)

    no_snapshot = PipelineConfig(
        name="_test_no_snapshot", description="test", model="gemini-2.5-flash", provider="google",
        verifier_prompt_version_sag="sag_v2_skepticism_2026-08-18",
        use_self_consistency=False, use_confidence_weighting=True, use_llm_verifier=True, verifier_weight=1.0,
        kg_snapshot_path=None,
    )
    try:
        build_pipeline(no_snapshot, api_key="dummy-not-used")
        check("missing kg_snapshot_path is rejected, not silently falling back to the live v1.1 builder", False)
    except ConfigProvenanceError:
        check("missing kg_snapshot_path is rejected, not silently falling back to the live v1.1 builder", True)

    bad_provider = PipelineConfig(
        name="_test_bad_provider", description="test", model="gemini-2.5-flash", provider="openrouter",
        verifier_prompt_version_sag="sag_v2_skepticism_2026-08-18",
        use_self_consistency=False, use_confidence_weighting=True, use_llm_verifier=True, verifier_weight=1.0,
    )
    try:
        build_pipeline(bad_provider, api_key="dummy-not-used")
        check("provider/model mismatch is rejected, not silently accepted", False)
    except ConfigProvenanceError:
        check("provider/model mismatch is rejected, not silently accepted", True)


def main() -> int:
    test_assess_class_propagates_reference_answer()
    test_cache_key_sensitivity()
    test_named_config_enforcement()

    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed: {FAILURES}")
        return 1
    print("PASS: all integrity regression checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
