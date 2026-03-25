"""
LongAnswerPipeline — ConceptGrade for multi-paragraph essays.

Speed design: Wave Parallelism
-------------------------------
Instead of running each segment sequentially through all pipeline layers,
we batch by layer and run ALL segments in parallel per wave:

  Wave 1: Extract concepts from ALL segments simultaneously
  Wave 2: Bloom's/SOLO + Misconception from ALL segments simultaneously
           (both are independent of each other, only need Wave 1 output)
  Wave 3: KG comparison  (pure Python, no LLM, instant)
  Wave 4: ONE verifier on the full answer  (not per-segment)
  Wave 5: ONE feedback synthesis pass

Timing for a 4-segment essay (500 words each, no cache):
  Wave 1: ~4s  (4 parallel extraction calls)
  Wave 2: ~4s  (8 parallel calls: 4 bloom + 4 misconception)
  Wave 3: <0.1s
  Wave 4: ~4s
  Wave 5: ~4s
  Total:  ~16s  (vs ~60–80s naive sequential)

With cache: sub-second for any repeat answer.

Architecture
------------
SAG components are used directly (not through the full pipeline.py) so we
can control parallelism precisely at each wave.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable

from knowledge_graph.domain_graph import DomainKnowledgeGraph
from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
from concept_extraction.extractor import ConceptExtractor, StudentConceptGraph
from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
from cognitive_depth.cognitive_depth_classifier import CognitiveDepthClassifier
from misconception_detection.detector import MisconceptionDetector
from conceptgrade.verifier import LLMVerifier, SureResult
from conceptgrade.cache import ResponseCache
from conceptgrade.smart_segmenter import SmartSegmenter, SegmentationResult, Segment
from conceptgrade.feedback_synthesizer import FeedbackSynthesizer, FeedbackReport
from conceptgrade.cross_para_integrator import CrossParaIntegrator


_BLOOM_LABELS = {
    1: "Remember", 2: "Understand", 3: "Apply",
    4: "Analyze",  5: "Evaluate",  6: "Create",
}


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class SegmentScore:
    """Scores for one segment, produced after Wave 2+3."""
    segment: Segment
    concepts: list[dict]
    concept_graph_dict: dict
    comparison: dict
    blooms: dict
    solo: dict
    misconceptions: dict
    kg_score: float          # 0–1 composite from KG pipeline


@dataclass
class AggregatedResult:
    """Map-Reduce aggregation across all segment scores."""
    covered_concepts: list[str]  = field(default_factory=list)
    missing_concepts: list[str]  = field(default_factory=list)
    bloom_sequence: list[int]    = field(default_factory=list)
    modal_bloom_level: int       = 1
    modal_bloom_label: str       = "Remember"
    ceiling_bloom_level: int     = 1
    ceiling_bloom_label: str     = "Remember"
    consistency_index: float     = 1.0
    depth_trajectory: str        = "plateau"
    misconceptions: list[dict]   = field(default_factory=list)
    segment_scores: list[float]  = field(default_factory=list)   # 0–5 per segment
    mean_score: float            = 0.0
    final_score: float           = 0.0
    inter_chunk_variance: float  = 0.0
    requires_human_review: bool  = False
    sure_scores: list            = field(default_factory=list)
    integration: dict            = field(default_factory=dict)

    def to_dict(self) -> dict:
        traj_desc = {
            "rising":   "Depth builds toward conclusion",
            "falling":  "Strongest content in introduction",
            "plateau":  "Consistent depth throughout",
            "variable": "Depth shifts across sections",
        }
        return {
            "final_score": round(self.final_score, 2),
            "mean_segment_score": round(self.mean_score, 2),
            "segment_scores": [round(s, 2) for s in self.segment_scores],
            "inter_chunk_variance": round(self.inter_chunk_variance, 4),
            "concepts": {
                "covered": self.covered_concepts,
                "missing": self.missing_concepts,
                "count": len(self.covered_concepts),
            },
            "depth": {
                "bloom_sequence": self.bloom_sequence,
                "modal_level": self.modal_bloom_level,
                "modal_label": self.modal_bloom_label,
                "ceiling_level": self.ceiling_bloom_level,
                "ceiling_label": self.ceiling_bloom_label,
                "consistency_index": round(self.consistency_index, 2),
                "trajectory": self.depth_trajectory,
                "trajectory_description": traj_desc.get(self.depth_trajectory, ""),
            },
            "misconceptions": self.misconceptions,
            **({"integration": self.integration} if self.integration else {}),
        }


@dataclass
class LongAnswerResult:
    """Full output of LongAnswerPipeline.assess()."""
    student_id: str
    question: str
    answer: str
    segmentation: SegmentationResult
    segment_scores: list[SegmentScore]
    aggregated: AggregatedResult
    feedback: FeedbackReport
    elapsed_seconds: float
    verifier: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "student_id": self.student_id,
            "question": self.question,
            "segmentation": {
                "strategy": self.segmentation.strategy,
                "n_segments": len(self.segmentation.segments),
                "total_words": self.segmentation.total_words,
                "executive_summary": self.segmentation.executive_summary,
                "segments": [
                    {"index": s.index, "label": s.label, "word_count": s.word_count}
                    for s in self.segmentation.segments
                ],
            },
            "segment_breakdown": [
                {
                    "index": ss.segment.index,
                    "label": ss.segment.label,
                    "word_count": ss.segment.word_count,
                    "score": round(ss.kg_score * 5, 2),
                    "bloom": ss.blooms.get("label", "?"),
                    "solo": ss.solo.get("label", "?"),
                    "misconceptions": ss.misconceptions.get("total_misconceptions", 0),
                }
                for ss in self.segment_scores
            ],
            "aggregated": self.aggregated.to_dict(),
            "feedback": self.feedback.to_dict(),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }
        if self.verifier:
            d["verifier"] = self.verifier
        return d


# ── Main pipeline ─────────────────────────────────────────────────────────────

class LongAnswerPipeline:
    """
    ConceptGrade pipeline for multi-paragraph long-form answers.

    Uses wave parallelism to score all segments simultaneously at each
    pipeline layer, keeping total latency close to a single SAG call.

    Parameters
    ----------
    api_key         : API key (provider auto-detected from model name)
    model           : LLM for scoring components (extraction, depth, misconception)
    domain_graph    : Domain KG (defaults to DS graph)
    segmenter_model : Optional cheaper model just for segmentation
    feedback_model  : Optional stronger model just for feedback prose
    max_workers     : Thread pool size for parallel waves (default 8)
    on_progress     : Callback(stage: str, detail: str) for live output
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        domain_graph: Optional[DomainKnowledgeGraph] = None,
        segmenter_model: Optional[str] = None,
        feedback_model: Optional[str] = None,
        max_workers: int = 8,
        on_progress: Optional[Callable[[str, str], None]] = None,
        use_sure: bool = False,
        use_cross_para: bool = False,
    ):
        self.api_key       = api_key
        self.model         = model
        self.max_workers   = max_workers
        self.on_progress   = on_progress or (lambda stage, detail: None)
        self.use_sure      = use_sure
        self.use_cross_para = use_cross_para

        dg = domain_graph or build_data_structures_graph()

        # Segmentation — fast/cheap model preferred
        self.segmenter = SmartSegmenter(
            api_key=api_key,
            model=segmenter_model or model,
        )

        # Scoring components — instantiated once, shared across all threads
        # (they hold no mutable state between calls)
        self.extractor  = ConceptExtractor(domain_graph=dg, api_key=api_key, model=model)
        self.comparator = ConfidenceWeightedComparator(domain_graph=dg)
        self.depth_clf  = CognitiveDepthClassifier(api_key=api_key, model=model)
        self.misc_det   = MisconceptionDetector(api_key=api_key, model=model)
        self.verifier   = LLMVerifier(api_key=api_key, model=model, verifier_weight=1.0)
        self.synthesizer = FeedbackSynthesizer(
            api_key=api_key,
            model=feedback_model or model,
        )

        # Cross-paragraph integrator — always instantiated, only called when use_cross_para=True
        self.integrator = CrossParaIntegrator(api_key=api_key, model=model)

        # Shared cache — all threads write to the same cache instance
        self.cache = ResponseCache()

    # ── Public API ────────────────────────────────────────────────────────────

    def assess(
        self,
        question: str,
        student_answer: str,
        reference_answer: str = "",
        student_id: str = "student",
    ) -> LongAnswerResult:
        """
        Assess a long-form student answer using wave-parallel processing.

        Progress callbacks fire at each stage so callers can show live output.
        """
        t0 = time.time()

        # Essay-level cache key — if the full answer was already graded, return instantly
        essay_cache_key = self.cache.key("lag_v1", self.model, question, student_answer)
        if essay_cache_key in self.cache:
            cached = self.cache.get(essay_cache_key)
            self.on_progress("cache", "Essay cache hit — returning instantly")
            return self._deserialize_result(cached, student_id, question, student_answer,
                                            time.time() - t0)

        # ── Wave 0: Segment the essay ─────────────────────────────────────
        self.on_progress("segment", "Detecting topic boundaries...")
        seg_result = self.segmenter.segment(student_answer)
        context_pfx = seg_result.context_prefix()
        n = len(seg_result.segments)
        self.on_progress("segment",
            f"  Strategy: {seg_result.strategy} → {n} segment(s), "
            f"{seg_result.total_words} words total")
        for s in seg_result.segments:
            self.on_progress("segment", f"  [{s.index}/{n}] {s.label} ({s.word_count}w)")

        # ── Wave 1: Extract concepts from all segments in parallel ────────
        self.on_progress("wave1", f"Extracting concepts ({n} segments in parallel)...")
        concept_graphs = self._wave_extract(question, seg_result.segments, context_pfx)

        # ── Wave 2a+2b: Bloom's/SOLO + Misconceptions simultaneously ─────
        self.on_progress("wave2", f"Classifying depth + detecting misconceptions ({n*2} calls)...")
        depth_results, misc_results = self._wave_depth_and_misc(
            question, seg_result.segments, concept_graphs, context_pfx
        )

        # ── Wave 3: KG comparison (pure Python, no LLM) ───────────────────
        comparison_results = {}
        for i, seg in enumerate(seg_result.segments):
            cg = concept_graphs.get(i)
            try:
                comp = self.comparator.compare(student_graph=cg).to_dict() if cg else {}
            except Exception:
                comp = {"scores": {}, "analysis": {}}
            comparison_results[i] = comp

        # ── Assemble segment scores ────────────────────────────────────────
        seg_scores: list[SegmentScore] = []
        for i, seg in enumerate(seg_result.segments):
            cg     = concept_graphs.get(i)
            comp   = comparison_results[i]
            bloom  = depth_results.get(i, {}).get("blooms", {})
            solo   = depth_results.get(i, {}).get("solo", {})
            misc   = misc_results.get(i, {})
            kg_sc  = self._compute_kg_score(comp, bloom, solo, misc)
            seg_scores.append(SegmentScore(
                segment=seg,
                concepts=cg.to_dict().get("concepts", []) if cg else [],
                concept_graph_dict=cg.to_dict() if cg else {},
                comparison=comp,
                blooms=bloom,
                solo=solo,
                misconceptions=misc,
                kg_score=kg_sc,
            ))
            score_5 = round(kg_sc * 5, 2)
            self.on_progress("score",
                f"  Segment {i+1}: {seg.label} → {score_5}/5 "
                f"[{bloom.get('label','?')}]")

        # ── Wave 2b: Cross-paragraph integration detection ────────────────
        if self.use_cross_para and len(seg_scores) >= 2:
            self.on_progress("wave2b", "Detecting cross-paragraph integration...")
            try:
                integration = self.integrator.detect(
                    question=question,
                    segment_scores=seg_scores,
                )
                # Will be attached to aggregated result after _aggregate()
                _integration_result = integration
            except Exception as e:
                self.on_progress("wave2b", f"  Integration detection failed: {e}")
                _integration_result = None
        else:
            _integration_result = None

        # ── Wave 4: ONE verifier on the full answer ────────────────────────
        sure_label = "SURE (3-persona)" if self.use_sure else "holistic"
        self.on_progress("verify", f"Running {sure_label} verifier on full answer...")
        agg_pre = self._aggregate(seg_scores)
        if _integration_result is not None:
            agg_pre.integration = _integration_result.to_dict()
        verifier_dict: dict = {}
        try:
            # Build a merged concept graph dict for the verifier
            merged_comp = self._merge_comparison(seg_scores)
            merged_bloom = {"level": agg_pre.modal_bloom_level,
                            "label": agg_pre.modal_bloom_label}
            merged_solo  = {"level": seg_scores[-1].solo.get("level", 1),
                            "label": seg_scores[-1].solo.get("label", "Prestructural")}
            merged_misc  = {"total_misconceptions": len(agg_pre.misconceptions)}

            if self.use_sure:
                sure_result = self.verifier.verify_sure(
                    question=question,
                    student_answer=student_answer,
                    kg_score=agg_pre.final_score / 5.0,
                    comparison_result=merged_comp,
                    blooms=merged_bloom,
                    solo=merged_solo,
                    misconceptions=merged_misc,
                    reference_answer=reference_answer,
                    mode="lag",
                )
                verified_score = round(sure_result.final_score * 5.0, 2)
                verifier_dict = sure_result.to_dict()
                agg_pre.requires_human_review = sure_result.requires_human_review
                agg_pre.sure_scores = sure_result.scores
            else:
                ver = self.verifier.verify(
                    question=question,
                    student_answer=student_answer,
                    kg_score=agg_pre.final_score / 5.0,
                    comparison_result=merged_comp,
                    blooms=merged_bloom,
                    solo=merged_solo,
                    misconceptions=merged_misc,
                    reference_answer=reference_answer,
                    mode="lag",
                )
                verified_score = round(ver.final_score * 5.0, 2)
                verifier_dict = ver.to_dict()
        except Exception as e:
            verified_score = agg_pre.final_score
        agg_pre.final_score = min(5.0, verified_score)
        agg = agg_pre
        self.on_progress("verify", f"  Final score: {agg.final_score}/5")

        # ── Wave 5: Professor feedback ────────────────────────────────────
        self.on_progress("feedback", "Synthesizing feedback...")
        feedback = self.synthesizer.synthesize(
            question=question,
            final_score=agg.final_score,
            covered_concepts=agg.covered_concepts,
            missing_primary_concepts=agg.missing_concepts,
            secondary_concepts_hit=[],
            misconceptions=agg.misconceptions,
            modal_bloom=agg.modal_bloom_label,
            modal_level=agg.modal_bloom_level,
            ceiling_bloom=agg.ceiling_bloom_label,
            ceiling_level=agg.ceiling_bloom_level,
            consistency_index=agg.consistency_index,
            depth_trajectory=agg.depth_trajectory,
            segment_labels=[s.segment.label for s in seg_scores],
        )

        result = LongAnswerResult(
            student_id=student_id,
            question=question,
            answer=student_answer,
            segmentation=seg_result,
            segment_scores=seg_scores,
            aggregated=agg,
            feedback=feedback,
            elapsed_seconds=time.time() - t0,
            verifier=verifier_dict,
        )

        # Cache the full result
        self.cache.set(essay_cache_key, result.to_dict())
        return result

    # ── Wave helpers ──────────────────────────────────────────────────────────

    def _wave_extract(
        self,
        question: str,
        segments: list[Segment],
        context_pfx: str,
    ) -> dict[int, Optional[StudentConceptGraph]]:
        """Run concept extraction on all segments in parallel (Wave 1)."""
        results: dict[int, Optional[StudentConceptGraph]] = {}

        def _extract(i: int, seg: Segment):
            enriched_q = self._enrich_q(question, seg, context_pfx)
            cache_key  = self.cache.key("lag_ext_v1", self.model, enriched_q, seg.text)
            if cache_key in self.cache:
                cached = self.cache.get(cache_key)
                try:
                    from concept_extraction.extractor import StudentConceptGraph
                    return i, StudentConceptGraph.from_dict(cached)
                except Exception:
                    pass
            try:
                cg = self.extractor.extract(question=enriched_q, student_answer=seg.text)
                self.cache.set(cache_key, cg.to_dict())
                return i, cg
            except Exception:
                return i, None

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(_extract, i, seg)
                       for i, seg in enumerate(segments)]
            for f in as_completed(futures):
                i, cg = f.result()
                results[i] = cg
        return results

    def _wave_depth_and_misc(
        self,
        question: str,
        segments: list[Segment],
        concept_graphs: dict[int, Optional[StudentConceptGraph]],
        context_pfx: str,
    ) -> tuple[dict, dict]:
        """Run Bloom's/SOLO and misconception detection simultaneously (Wave 2)."""
        depth_results: dict[int, dict] = {}
        misc_results:  dict[int, dict] = {}

        def _classify_depth(i: int, seg: Segment):
            enriched_q = self._enrich_q(question, seg, context_pfx)
            cg = concept_graphs.get(i)
            cg_dict = cg.to_dict() if cg else {}
            cache_key = self.cache.key("lag_dep_v1", self.model, enriched_q, seg.text)
            if cache_key in self.cache:
                return ("depth", i, self.cache.get(cache_key))
            try:
                dr = self.depth_clf.classify(
                    question=enriched_q, student_answer=seg.text,
                    concept_graph=cg_dict, comparison_result={},
                )
                result = {"blooms": dr.to_blooms_dict(), "solo": dr.to_solo_dict()}
                self.cache.set(cache_key, result)
                return ("depth", i, result)
            except Exception:
                return ("depth", i, {
                    "blooms": {"level": 1, "label": "Remember"},
                    "solo":   {"level": 1, "label": "Prestructural"},
                })

        def _detect_misc(i: int, seg: Segment):
            enriched_q = self._enrich_q(question, seg, context_pfx)
            cg = concept_graphs.get(i)
            cg_dict = cg.to_dict() if cg else {}
            cache_key = self.cache.key("lag_mis_v1", self.model, enriched_q, seg.text)
            if cache_key in self.cache:
                return ("misc", i, self.cache.get(cache_key))
            try:
                mr = self.misc_det.detect(
                    question=enriched_q, student_answer=seg.text,
                    concept_graph=cg_dict, comparison_result={},
                )
                result = mr.to_dict()
                self.cache.set(cache_key, result)
                return ("misc", i, result)
            except Exception:
                return ("misc", i, {"total_misconceptions": 0, "misconceptions": []})

        # Submit ALL depth + ALL misconception calls at the same time
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = (
                [pool.submit(_classify_depth, i, seg) for i, seg in enumerate(segments)] +
                [pool.submit(_detect_misc,    i, seg) for i, seg in enumerate(segments)]
            )
            for f in as_completed(futures):
                kind, i, data = f.result()
                if kind == "depth":
                    depth_results[i] = data
                else:
                    misc_results[i] = data

        return depth_results, misc_results

    # ── Aggregation ───────────────────────────────────────────────────────────

    def _aggregate(self, seg_scores: list[SegmentScore]) -> AggregatedResult:
        agg = AggregatedResult()

        # Concepts: union with max confidence
        all_concepts: dict[str, float] = {}
        seen_missing: set[str] = set()
        missing: list[str] = []
        for ss in seg_scores:
            for c in ss.concepts:
                cid  = c.get("concept_id", c.get("id", ""))
                conf = float(c.get("confidence", 0.5))
                if cid:
                    all_concepts[cid] = max(all_concepts.get(cid, 0.0), conf)
            for mc in ss.comparison.get("analysis", {}).get("missing_concepts", []):
                mid = (mc.get("id", mc) if isinstance(mc, dict) else str(mc)).strip()
                if mid and mid not in all_concepts and mid not in seen_missing:
                    missing.append(mid)
                    seen_missing.add(mid)
        agg.covered_concepts = list(all_concepts.keys())
        agg.missing_concepts = missing[:5]

        # Depth profile
        bloom_seq = [ss.blooms.get("level", 1) for ss in seg_scores]
        agg.bloom_sequence = bloom_seq
        modal = max(set(bloom_seq), key=bloom_seq.count) if bloom_seq else 1
        ceil  = max(bloom_seq) if bloom_seq else 1
        agg.modal_bloom_level   = modal
        agg.modal_bloom_label   = _BLOOM_LABELS.get(modal, "Apply")
        agg.ceiling_bloom_level = ceil
        agg.ceiling_bloom_label = _BLOOM_LABELS.get(ceil, "Apply")
        agg.consistency_index   = round(modal / ceil, 2) if ceil else 1.0

        if   bloom_seq == sorted(bloom_seq):                       agg.depth_trajectory = "rising"
        elif bloom_seq == sorted(bloom_seq, reverse=True):         agg.depth_trajectory = "falling"
        elif len(set(bloom_seq)) == 1:                             agg.depth_trajectory = "plateau"
        else:                                                       agg.depth_trajectory = "variable"

        # Misconceptions: deduplicate by concept pair
        seen_misc: set[str] = set()
        freq: dict[str, int] = {}
        for ss in seg_scores:
            for m in ss.misconceptions.get("misconceptions", []):
                key = m.get("source_concept", "") + "|" + m.get("target_concept", "")
                freq[key] = freq.get(key, 0) + 1
                if key not in seen_misc:
                    seen_misc.add(key)
                    agg.misconceptions.append({
                        "concept":     m.get("source_concept", ""),
                        "description": m.get("student_claim", m.get("explanation", "")),
                        "severity":    "persistent" if freq.get(key, 0) >= 2 else "isolated",
                    })

        # Scoring: 60% mean + 40% ceiling (rewards peak performance)
        scores = [ss.kg_score * 5.0 for ss in seg_scores]
        agg.segment_scores = [round(s, 2) for s in scores]
        mean = sum(scores) / len(scores) if scores else 0.0
        agg.mean_score = round(mean, 2)

        raw = 0.60 * mean + 0.40 * max(scores, default=0.0)
        n_pers = sum(1 for m in agg.misconceptions if m["severity"] == "persistent")
        n_isol = sum(1 for m in agg.misconceptions if m["severity"] == "isolated")
        penalty = min(1.5, n_pers * 0.4 + n_isol * 0.1)
        agg.final_score = round(max(0.0, min(5.0, raw - penalty)), 2)

        if len(scores) > 1:
            agg.inter_chunk_variance = round(
                sum((s - mean) ** 2 for s in scores) / len(scores), 4)

        return agg

    def _merge_comparison(self, seg_scores: list[SegmentScore]) -> dict:
        """Build a single merged comparison dict for the verifier."""
        all_cov   = [ss.comparison.get("scores", {}).get("concept_coverage", 0.0) for ss in seg_scores]
        all_acc   = [ss.comparison.get("scores", {}).get("relationship_accuracy", 0.0) for ss in seg_scores]
        all_integ = [ss.comparison.get("scores", {}).get("integration_quality", 0.0) for ss in seg_scores]
        return {"scores": {
            "concept_coverage":      max(all_cov,   default=0.0),
            "relationship_accuracy": sum(all_acc)   / len(all_acc)   if all_acc   else 0.0,
            "integration_quality":   sum(all_integ) / len(all_integ) if all_integ else 0.0,
        }}

    @staticmethod
    def _compute_kg_score(comp: dict, bloom: dict, solo: dict, misc: dict) -> float:
        """Replicate pipeline.py's _compute_overall_score for one segment."""
        sc = comp.get("scores", {})
        cov  = sc.get("concept_coverage", 0.0)
        acc  = sc.get("relationship_accuracy", 0.0)
        intg = sc.get("integration_quality", 0.0)
        b_n  = (bloom.get("level", 1) - 1) / 5.0
        s_n  = (solo.get("level",  1) - 1) / 4.0
        n_m  = misc.get("total_misconceptions", 0)
        crit = misc.get("by_severity", {}).get("critical", 0)
        pen  = min(0.30, n_m * 0.06 + crit * 0.10)
        know = cov * 0.45 + acc * 0.35 + intg * 0.20
        dep  = b_n * 0.55 + s_n * 0.45
        return min(1.0, max(0.0, (know * 0.60 + dep * 0.40) * (1.0 - pen)))

    @staticmethod
    def _enrich_q(question: str, seg: Segment, ctx: str) -> str:
        if not ctx:
            return question
        return f"{ctx}SECTION: {seg.label}\nQUESTION: {question}"

    @staticmethod
    def _deserialize_result(cached: dict, student_id: str, question: str,
                             answer: str, elapsed: float) -> LongAnswerResult:
        """Reconstruct a minimal LongAnswerResult from a cached dict."""
        from conceptgrade.smart_segmenter import SegmentationResult
        from conceptgrade.feedback_synthesizer import FeedbackReport
        seg_data = cached.get("segmentation", {})
        seg_result = SegmentationResult(
            segments=[], executive_summary=seg_data.get("executive_summary", ""),
            structural_outline=[], total_words=seg_data.get("total_words", 0),
            strategy=seg_data.get("strategy", "cached"),
        )
        fb_data = cached.get("feedback", {})
        struct = fb_data.get("structured", {})
        feedback = FeedbackReport(
            score=cached.get("aggregated", {}).get("final_score", 0.0),
            opening=struct.get("opening", ""),
            knowledge_gap_feedback=struct.get("knowledge_gap_feedback", ""),
            accuracy_gap_feedback=struct.get("accuracy_gap_feedback", ""),
            depth_feedback=struct.get("depth_feedback", ""),
            closing=struct.get("closing", ""),
            one_line_summary=fb_data.get("one_line_summary", ""),
            tone_level=fb_data.get("tone_level", "constructive"),
        )
        agg_data = cached.get("aggregated", {})
        depth_data = agg_data.get("depth", {})
        agg = AggregatedResult(
            covered_concepts=agg_data.get("concepts", {}).get("covered", []),
            missing_concepts=agg_data.get("concepts", {}).get("missing", []),
            bloom_sequence=depth_data.get("bloom_sequence", []),
            modal_bloom_level=depth_data.get("modal_level", 1),
            modal_bloom_label=depth_data.get("modal_label", "Remember"),
            ceiling_bloom_level=depth_data.get("ceiling_level", 1),
            ceiling_bloom_label=depth_data.get("ceiling_label", "Remember"),
            consistency_index=depth_data.get("consistency_index", 1.0),
            depth_trajectory=depth_data.get("trajectory", "plateau"),
            misconceptions=agg_data.get("misconceptions", []),
            segment_scores=agg_data.get("segment_scores", []),
            mean_score=agg_data.get("mean_segment_score", 0.0),
            final_score=agg_data.get("final_score", 0.0),
            inter_chunk_variance=agg_data.get("inter_chunk_variance", 0.0),
        )
        # Reconstruct minimal SegmentScore objects so run_lag.py can display the table
        from conceptgrade.smart_segmenter import Segment
        reconstructed_segs: list[SegmentScore] = []
        for bd in cached.get("segment_breakdown", []):
            seg = Segment(
                index=bd.get("index", 1),
                label=bd.get("label", f"Segment {bd.get('index', 1)}"),
                text="",
                word_count=bd.get("word_count", 0),
                start_word=0,
            )
            bloom_label = bd.get("bloom", "Remember")
            bloom_level = {"Remember": 1, "Understand": 2, "Apply": 3,
                           "Analyze": 4, "Evaluate": 5, "Create": 6}.get(bloom_label, 1)
            reconstructed_segs.append(SegmentScore(
                segment=seg,
                concepts=[],
                concept_graph_dict={},
                comparison={},
                blooms={"label": bloom_label, "level": bloom_level},
                solo={"label": bd.get("solo", "Prestructural"), "level": 1},
                misconceptions={"total_misconceptions": bd.get("misconceptions", 0)},
                kg_score=bd.get("score", 0.0) / 5.0,
            ))

        return LongAnswerResult(
            student_id=student_id, question=question, answer=answer,
            segmentation=seg_result, segment_scores=reconstructed_segs,
            aggregated=agg, feedback=feedback, elapsed_seconds=elapsed,
        )
