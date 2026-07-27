"""Regression tests for the OUT_OF_KG_DOMAIN signal chain.

This module covers every node in the chain established by Framework Fixes
#2b → #2c → #8 → #9 → #10 → #11 → #12 → #13 (2026-06-15 session). Before
those fixes a Kaggle-style out-of-domain answer flowed through the system
producing vacuous-positive scores (overall ≈ 0.70, Bloom's=1, "no
misconceptions detected"); after them every downstream consumer correctly
distinguishes "out of KG coverage" from "in-domain but low quality".

Also covers Fix #15 — lower-level vacuous-1.0 returns that previously
inflated scores for shallow in-domain answers.

The existing 38-test suite covered happy paths only and missed all 22
fixes. This file is the safety net so future refactors can't silently
re-introduce the same defect class.
"""

from __future__ import annotations

import os
import sys

# Same import-prep pattern the other test modules use
os.environ.setdefault("CONCEPTGRADE_SEMANTIC", "0")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Note: pre-Fix-#29 a workaround was needed here (preload
# conceptgrade.pipeline to break the cycle). Fix #29 lazified the
# concept_extraction imports inside pipeline.py so this file can now
# import normally — keep this comment as a marker that the original
# defect class is closed.

from concept_extraction.extractor import (  # noqa: E402
    ExtractedConcept,
    ExtractedRelationship,
    StudentConceptGraph,
)
from graph_comparison.comparator import KnowledgeGraphComparator  # noqa: E402
from graph_comparison.confidence_weighted_comparator import (  # noqa: E402
    ConfidenceWeightedComparator,
)
from knowledge_graph.ds_knowledge_graph import build_data_structures_graph  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — build minimal StudentConceptGraph fixtures the comparators accept
# ---------------------------------------------------------------------------


def _out_of_kg_graph() -> StudentConceptGraph:
    """A Kaggle-style answer: extractor signaled OUT_OF_KG_DOMAIN."""
    return StudentConceptGraph(
        question="What is respiration in plants?",
        student_answer="Plants release oxygen during photosynthesis.",
        concepts=[],
        relationships=[],
        domain_match_score=0.0,
    )


def _in_domain_with_content() -> StudentConceptGraph:
    """Standard in-domain answer with concepts and one relationship."""
    return StudentConceptGraph(
        question="Define a linked list.",
        student_answer="A linked list is nodes connected by pointers.",
        concepts=[
            ExtractedConcept("linked_list", 0.9, "nodes connected"),
            ExtractedConcept("node", 0.9, "nodes"),
            ExtractedConcept("pointer", 0.9, "pointers"),
        ],
        relationships=[
            ExtractedRelationship("linked_list", "node", "contains", 0.9, "", True),
        ],
        domain_match_score=0.55,
    )


def _in_domain_empty() -> StudentConceptGraph:
    """Legacy back-compat case: in-domain question, student gave empty answer."""
    return StudentConceptGraph(
        question="Define a linked list.",
        student_answer="I don't know.",
        concepts=[],
        relationships=[],
        domain_match_score=1.0,  # in-domain (extractor flagged the question)
    )


# ---------------------------------------------------------------------------
# Fix #2b — StudentConceptGraph carries the OUT_OF_KG signal
# ---------------------------------------------------------------------------


def test_2b_student_concept_graph_exposes_out_of_kg_property():
    """domain_match_score < 0.05 ⇒ out_of_kg_domain is True."""
    sg = _out_of_kg_graph()
    assert sg.domain_match_score == 0.0
    assert sg.out_of_kg_domain is True


def test_2b_in_domain_graph_is_not_out_of_kg():
    sg = _in_domain_with_content()
    assert sg.out_of_kg_domain is False


def test_2b_round_trip_through_dict_preserves_signal():
    """to_dict / from_dict must preserve domain_match_score, otherwise
    every downstream consumer that reads from the cached dict (cognitive
    depth, misconception detector, comparator) silently loses the flag."""
    sg = _out_of_kg_graph()
    revived = StudentConceptGraph.from_dict(sg.to_dict())
    assert revived.domain_match_score == 0.0
    assert revived.out_of_kg_domain is True

    sg2 = _in_domain_with_content()
    revived2 = StudentConceptGraph.from_dict(sg2.to_dict())
    assert revived2.domain_match_score == 0.55
    assert revived2.out_of_kg_domain is False


# ---------------------------------------------------------------------------
# Fix #10 — KnowledgeGraphComparator OUT_OF_KG short-circuit
# ---------------------------------------------------------------------------


def test_10_comparator_zeroes_out_of_kg_scores():
    """Pre-Fix-#10 returned overall=0.70 for empty student + empty expected.
    Post-fix: all-zero scores + explicit not_assessed marker."""
    kg = build_data_structures_graph()
    cmp = KnowledgeGraphComparator(domain_graph=kg)
    result = cmp.compare(_out_of_kg_graph())
    assert result.concept_coverage_score == 0.0
    assert result.relationship_accuracy_score == 0.0
    assert result.overall_score == 0.0
    assert result.out_of_kg_domain is True
    assert result.depth_assessment == "not_assessed"
    # to_dict must surface the flag for downstream consumers (verifier #13)
    assert result.to_dict()["scores"]["out_of_kg_domain"] is True


def test_10_in_domain_path_unaffected():
    kg = build_data_structures_graph()
    cmp = KnowledgeGraphComparator(domain_graph=kg)
    result = cmp.compare(_in_domain_with_content())
    assert result.out_of_kg_domain is False
    # Coverage should be positive when student matched expected concepts
    assert result.concept_coverage_score > 0.0


# ---------------------------------------------------------------------------
# Fix #12 — ConfidenceWeightedComparator OUT_OF_KG short-circuit
# ---------------------------------------------------------------------------


def test_12_confidence_weighted_comparator_zeroes_out_of_kg():
    kg = build_data_structures_graph()
    cmp = ConfidenceWeightedComparator(domain_graph=kg)
    result = cmp.compare(_out_of_kg_graph())
    assert result.overall_score == 0.0
    assert result.out_of_kg_domain is True


# ---------------------------------------------------------------------------
# Fix #15 — lower-level vacuous-1.0 returns no longer inflate shallow answers
# ---------------------------------------------------------------------------


def test_15_legacy_in_domain_empty_no_longer_inflated():
    """Pre-Fix-#15: in-domain empty answer scored overall=0.70 (vacuous
    1.0 coverage of empty expected set × 0.4 weight + vacuous 1.0 accuracy
    × 0.3 weight). Post-fix: 0.0 across the board."""
    kg = build_data_structures_graph()
    cmp = KnowledgeGraphComparator(domain_graph=kg)
    result = cmp.compare(_in_domain_empty())
    assert result.concept_coverage_score == 0.0
    assert result.relationship_accuracy_score == 0.0
    assert result.overall_score == 0.0
    # but the OUT_OF_KG flag is FALSE — this is a back-compat legacy
    # in-domain answer, not an out-of-scope question
    assert result.out_of_kg_domain is False


def test_15_in_domain_shallow_keyword_dump_penalized():
    """Student lists 3 concepts but extracts zero relationships —
    pre-Fix-#15 got a free 30% accuracy boost (1.0 × accuracy_weight)."""
    sg = StudentConceptGraph(
        question="Define a linked list.",
        student_answer="linked list. node. pointer.",
        concepts=[
            ExtractedConcept("linked_list", 0.9, "ev"),
            ExtractedConcept("node", 0.9, "ev"),
            ExtractedConcept("pointer", 0.9, "ev"),
        ],
        relationships=[],
        domain_match_score=0.55,
    )
    kg = build_data_structures_graph()
    result = KnowledgeGraphComparator(domain_graph=kg).compare(sg)
    assert result.relationship_accuracy_score == 0.0  # was 1.0 pre-fix


# ---------------------------------------------------------------------------
# Fix #8 — CognitiveDepthClassifier evidence builder respects OUT_OF_KG
# ---------------------------------------------------------------------------


def test_8_cognitive_depth_evidence_marks_out_of_kg():
    """The evidence dict fed to the LLM must surface 'OUT OF KG COVERAGE'
    instead of 'Concepts found: 0' which primed the model toward level 1."""
    from cognitive_depth.cognitive_depth_classifier import CognitiveDepthClassifier
    clf = CognitiveDepthClassifier(api_key="placeholder", model="any")

    ev_oot = clf._build_evidence(
        {"concepts": [], "relationships": [], "out_of_kg_domain": True},
        None,
    )
    assert ev_oot["num_concepts"] == "OUT OF KG COVERAGE"
    assert ev_oot["concept_list"].startswith("OUT OF KG COVERAGE")
    assert ev_oot["_out_of_kg"] is True


def test_8_cognitive_depth_evidence_legacy_path_preserved():
    """In-domain or unflagged empty must keep the old 0/none format."""
    from cognitive_depth.cognitive_depth_classifier import CognitiveDepthClassifier
    clf = CognitiveDepthClassifier(api_key="placeholder", model="any")

    ev_legacy = clf._build_evidence(
        {"concepts": [], "relationships": []},  # no out_of_kg flag
        None,
    )
    assert ev_legacy["num_concepts"] == 0
    assert ev_legacy["_out_of_kg"] is False


def test_8_cognitive_depth_fallback_no_longer_floors_out_of_kg():
    """Pre-Fix-#8: out_of_kg + LLM parse fail → Bloom's=1, SOLO=1.
    Post-fix: returns neutral Bloom's=2 / SOLO=2 with low confidence."""
    from cognitive_depth.cognitive_depth_classifier import CognitiveDepthClassifier
    clf = CognitiveDepthClassifier(api_key="placeholder", model="any")
    fb = clf._fallback(num_concepts=0, num_rels=0, out_of_kg=True)
    assert fb.blooms_level == 2
    assert fb.solo_level == 2
    assert fb.blooms_confidence < 0.5
    # Legacy back-compat: empty without out_of_kg keeps the 1/1 floor
    fb_legacy = clf._fallback(num_concepts=0, num_rels=0, out_of_kg=False)
    assert fb_legacy.blooms_level == 1
    assert fb_legacy.solo_level == 1


# ---------------------------------------------------------------------------
# Fix #9 — MisconceptionDetector explicit "not assessed" on OUT_OF_KG
# ---------------------------------------------------------------------------


def test_9_misconception_detector_explicit_not_assessed_on_out_of_kg():
    from misconception_detection.detector import MisconceptionDetector
    det = MisconceptionDetector(api_key="placeholder", model="any")
    report = det.detect(
        question="What is respiration?",
        student_answer="Plants release oxygen.",
        concept_graph={"concepts": [], "relationships": [], "out_of_kg_domain": True},
        comparison_result=None,
    )
    assert report.total_misconceptions == 0
    assert "outside the knowledge graph" in report.summary.lower()
    # The misleading legacy phrasing must NOT appear for out_of_kg
    assert "appear correct" not in report.summary


def test_9_misconception_detector_legacy_empty_keeps_old_message():
    """Back-compat: in-domain empty (no out_of_kg flag) keeps old wording."""
    from misconception_detection.detector import MisconceptionDetector
    det = MisconceptionDetector(api_key="placeholder", model="any")
    report = det.detect(
        question="Q?", student_answer="A.",
        concept_graph={"concepts": [], "relationships": []},
        comparison_result=None,
    )
    assert "appear correct" in report.summary


# ---------------------------------------------------------------------------
# Fix #18 — taxonomy ↔ KG cross-references + drift detection
# ---------------------------------------------------------------------------


def test_18_taxonomy_for_concept_returns_attachments():
    from misconception_detection.detector import taxonomy_for_concept
    # linked_list is referenced by multiple taxonomy entries
    attachments = taxonomy_for_concept("linked_list")
    assert len(attachments) >= 1
    # trie was added in Fix #16 but no taxonomy entry references it
    assert taxonomy_for_concept("trie") == []
    # bogus concept_id returns empty list, not error
    assert taxonomy_for_concept("not_a_real_concept_id") == []


def test_18_validate_taxonomy_clean_against_real_kg():
    from misconception_detection.detector import validate_taxonomy_against_kg
    kg = build_data_structures_graph()
    kg_ids = {c.id for c in kg.get_all_concepts()}
    audit = validate_taxonomy_against_kg(kg_ids)
    assert audit["missing_refs"] == []  # current KG has zero broken refs
    assert audit["referenced_count"] > 0


def test_18_validate_taxonomy_surfaces_drift():
    from misconception_detection.detector import validate_taxonomy_against_kg
    kg = build_data_structures_graph()
    # Remove a concept that we know is taxonomy-referenced
    kg_ids = {c.id for c in kg.get_all_concepts()} - {"linked_list"}
    audit = validate_taxonomy_against_kg(kg_ids)
    assert audit["missing_refs"], "synthetic drift must surface broken refs"
    # Every reported entry must name the missing concept
    for tid, cid in audit["missing_refs"]:
        assert cid == "linked_list"


# ---------------------------------------------------------------------------
# Fix #16 + #17 — KG completeness invariants
# ---------------------------------------------------------------------------


def test_16_no_isolated_concepts_in_kg():
    """Pre-Fix-#16: 15 isolated concepts (degree=0) under-weighted in
    coverage and contributed nothing to chain-coverage."""
    kg = build_data_structures_graph()
    isolated = [c.id for c in kg.get_all_concepts() if kg.graph.degree(c.id) == 0]
    assert isolated == [], f"isolated concepts present: {isolated}"


def test_17_operation_pairs_linked():
    """Pre-Fix-#17: push/pop/peek/enqueue/dequeue/fifo/lifo had no contrast
    edges, blocking the comparator from spotting operation-pair gaps."""
    kg = build_data_structures_graph()
    pairs = [
        ("push", "pop"), ("pop", "peek"), ("enqueue", "dequeue"),
        ("fifo", "lifo"), ("max_heap", "min_heap"),
    ]
    for a, b in pairs:
        assert kg.graph.has_edge(a, b) or kg.graph.has_edge(b, a), \
            f"operation pair {a} ↔ {b} not linked in KG"


# ---------------------------------------------------------------------------
# Fix #19 — dataset deduplication helper
# ---------------------------------------------------------------------------


def test_19_dedupe_records_returns_unique_with_indices():
    from datasets.dataset_dedupe import dedupe_records
    records = [
        {"id": 1, "question": "Q1", "reference_answer": "R1", "student_answer": "A1"},
        {"id": 2, "question": "Q1", "reference_answer": "R1", "student_answer": "A1"},  # dup
        {"id": 3, "question": "Q2", "reference_answer": "R2", "student_answer": "A2"},
        {"id": 4, "question": "Q1", "reference_answer": "R1", "student_answer": "A1"},  # dup of 1
    ]
    unique, indices, dropped = dedupe_records(records)
    assert len(unique) == 2
    assert indices == [0, 2]
    assert dropped == 2


def test_19_dedupe_empty_safe():
    from datasets.dataset_dedupe import dedupe_records
    assert dedupe_records([]) == ([], [], 0)


def test_19_dedupe_whitespace_normalised():
    """Strip-equivalence — Kaggle records with trailing spaces should
    dedupe with their canonical-form siblings."""
    from datasets.dataset_dedupe import dedupe_records
    records = [
        {"question": "What is X?", "reference_answer": "R", "student_answer": "A"},
        {"question": "What is X?", "reference_answer": "R", "student_answer": "A  "},  # extra spaces
    ]
    unique, indices, dropped = dedupe_records(records)
    assert len(unique) == 1
    assert dropped == 1


# ---------------------------------------------------------------------------
# Fix #20 / #21 — LLMClient explicit-raise on empty content
# ---------------------------------------------------------------------------


def test_20_deepseek_raises_on_null_content():
    """The old `or ""` silently emitted empty content; now raises with
    finish_reason context so the caller can decide retry vs fallback."""
    import types as _types
    fake_openai = _types.ModuleType("openai")

    class _Msg:
        def __init__(self, c): self.content = c
    class _Choice:
        def __init__(self, c, fr): self.message = _Msg(c); self.finish_reason = fr
    class _Resp:
        def __init__(self, c, fr): self.choices = [_Choice(c, fr)]
    class _Comp:
        _inj = _Resp("ok", "stop")
        @staticmethod
        def create(**_kw): return _Comp._inj
    class _Chat:
        completions = _Comp()
    class _OAI:
        def __init__(self, **_kw): self.chat = _Chat()
    fake_openai.OpenAI = _OAI
    sys.modules["openai"] = fake_openai

    # Need to reload the module so it picks up the mocked openai
    import importlib
    from conceptgrade import llm_client as L
    importlib.reload(L)

    ds = L._DeepSeekCompletions(api_key="dummy")
    _Comp._inj = _Resp(None, "length")
    import pytest
    with pytest.raises(ValueError, match="DeepSeek returned empty content"):
        ds.create(model="deepseek-chat", messages=[{"role": "user", "content": "x"}])


def test_21_explicit_timeouts_on_anthropic_and_openai():
    """Both clients now construct their SDK with timeout=60.0 (was unset)."""
    import types as _types

    # Fake openai
    class _OAIChat: pass
    class _OAI:
        def __init__(self, **kw):
            self.timeout = kw.get("timeout")
            self.chat = _OAIChat()
    fake_openai = _types.ModuleType("openai"); fake_openai.OpenAI = _OAI
    sys.modules["openai"] = fake_openai

    # Fake anthropic
    class _AntMsgs: pass
    class _Ant:
        def __init__(self, **kw):
            self.timeout = kw.get("timeout")
            self.messages = _AntMsgs()
    fake_ant = _types.ModuleType("anthropic"); fake_ant.Anthropic = _Ant
    sys.modules["anthropic"] = fake_ant

    import importlib
    from conceptgrade import llm_client as L
    importlib.reload(L)

    assert L._OpenAICompletions(api_key="k")._client.timeout == 60.0
    assert L._AnthropicCompletions(api_key="k")._client.timeout == 60.0


# ---------------------------------------------------------------------------
# Fix #26 — legacy classifiers respect OUT_OF_KG too
# ---------------------------------------------------------------------------


def test_26_legacy_blooms_classifier_marks_out_of_kg():
    """Building the evidence-extraction block of BloomsClassifier with an
    out_of_kg-flagged concept_graph must surface 'OUT OF KG COVERAGE' in
    the prompt-filling locals (we don't fire the LLM here)."""
    # We can't easily reach into the local variables of classify(), so
    # we exercise the public path with a mocked LLM and inspect the
    # captured prompt. The classifier currently calls _call_llm.
    from cognitive_depth.blooms_classifier import BloomsClassifier
    captured = {}

    class _MockBlooms(BloomsClassifier):
        def __init__(self):
            # bypass parent __init__ (no real LLM client needed)
            self.client = None
            self.model = "mock"

        def _call_llm(self, system, user, max_tokens=512):
            captured["user"] = user
            import json as _j
            return _j.dumps({
                "blooms_level": 2, "blooms_label": "Understand",
                "blooms_confidence": 0.8, "blooms_justification": "...",
                "reasoning_steps": []
            })

    clf = _MockBlooms()
    clf.classify(
        question="What is respiration?",
        student_answer="Plants release oxygen.",
        concept_graph={"concepts": [], "relationships": [], "out_of_kg_domain": True},
        comparison_result=None,
    )
    assert "OUT OF KG COVERAGE" in captured["user"]


def test_26_legacy_solo_classifier_trusts_llm_on_out_of_kg():
    """SOLOClassifier ensemble pre-Fix-#26: rule_level was PRESTRUCTURAL,
    LLM was averaged into it, dragging the result toward 1. Post-fix: the
    out_of_kg path matches the concept_graph-is-None path (trusts LLM)."""
    from cognitive_depth.solo_classifier import SOLOClassifier
    import json as _j

    class _MockSOLO(SOLOClassifier):
        def __init__(self):
            self.client = None; self.model = "mock"

        def _call_llm(self, system, user, max_tokens=512):
            return _j.dumps({
                "solo_level": 4, "solo_label": "Relational",
                "confidence": 0.85, "justification": "...",
                "reasoning_steps": [],
                "capacity": "many", "relating_operation": "relate",
            })

    clf = _MockSOLO()
    result = clf.classify(
        question="What is respiration?",
        student_answer="Plants release oxygen during photosynthesis, "
                       "which connects to cellular respiration in the dark.",
        concept_graph={"concepts": [], "relationships": [], "out_of_kg_domain": True},
        comparison_result=None,
    )
    # LLM said 4; rule-based would have said 1; out_of_kg trusts LLM
    assert result.level.value == 4, \
        f"out_of_kg should pass LLM verdict through; got {result.level.value}"
