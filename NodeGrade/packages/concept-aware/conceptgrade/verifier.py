"""
LLM-as-Verifier Layer.

Research Extension 3 — ConceptGrade Enhancement.

Motivation
----------
Knowledge-graph scoring is objective but blind to nuance:
  - A student may express a correct concept in non-standard vocabulary,
    getting penalised by the KG matcher even though they understand it.
  - A student may game keyword matching without genuine understanding.

The Verifier addresses this by running an LLM "judge" after the KG scoring
phase. The LLM receives the raw student answer AND the KG-computed evidence
and must output a verified score with an explicit chain-of-thought that
either confirms or overrides the KG score.

Algorithm
---------
1. Collect KG scores (coverage, accuracy, integration), Bloom's level,
   SOLO level, and misconception count from the preceding pipeline layers.
2. Feed them alongside the raw Q&A to an LLM verifier prompt.
3. LLM outputs:
   - verified_score (0-1): Its own holistic estimate of correctness
   - adjustment_reason: Why it agrees/disagrees with KG
   - confidence: How confident it is in the adjustment
4. Final score = weighted blend of KG score and verified score:
     final = (1 - verifier_weight) × kg_score + verifier_weight × verified_score
   Default verifier_weight = 0.25 (KG score dominates; LLM provides soft correction)

Effect on downstream evaluation
---------------------------------
On the Mohler benchmark, this correction layer is expected to improve:
  - Pearson r  by 0.01–0.03 (handles vocabulary mismatch cases)
  - RMSE       by 0.05–0.10 (reduces large outlier errors)
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, field
from typing import List
from conceptgrade.llm_client import LLMClient as Groq


VERIFIER_SYSTEM_LAG = """You are an expert Computer Science educator grading a student's long-form essay answer.

IMPORTANT CALIBRATION — essays are typically over-graded. Apply these anchors strictly:
- 5.0: Exceptional — covers ALL key concepts with accurate mechanisms and clear explanations
- 4.0: Good — covers most concepts accurately, only minor gaps
- 3.0: Moderate — covers main ideas but missing important details or depth
- 2.0: Basic — some correct points but significant gaps or shallow explanations
- 1.0: Minimal — vaguely related, mostly off-target or very incomplete
- 0.5: Trace — one correct idea buried in incorrect or irrelevant content

DEPTH RULE: An essay that lists concept names without explaining HOW or WHY they work
scores NO HIGHER than 3.0. Reserve 4.0+ for answers with mechanistic explanations.

Your task:
1. Read the question, reference answer, and student essay carefully.
2. Use the concept evidence (covered/missing concepts) to identify specific gaps.
3. Assign a score from 0.0 to 5.0 using one decimal place.

Return ONLY valid JSON."""

VERIFIER_SYSTEM = """You are an expert Computer Science educator grading a student's short answer.

Your task:
1. Read the question, reference answer, and student answer carefully.
2. Use the concept evidence (covered/missing concepts from the knowledge graph) to ground your assessment.
3. Assign a score from 0.0 to 5.0 using one decimal place (e.g. 1.5, 2.5, 3.5).

HOW TO SCORE:
- Compare the student answer directly to the reference answer.
- The reference answer defines what 5.0 looks like.
- Missing critical concepts lower the score; misconceptions lower it further.
- Causal chain coverage tells you if the student understands concept relationships, not just isolated facts.
- Partially correct or vague explanations merit partial credit (e.g. 1.5 not 1 or 2).
- Be precise: use the full range 0.0–5.0 with one decimal place.

Return ONLY valid JSON."""

VERIFIER_USER = """QUESTION: {question}

REFERENCE ANSWER (expert answer — defines 5.0):
{reference_answer}

STUDENT ANSWER:
{student_answer}

CONCEPT ANALYSIS (from structured knowledge graph):
- Concepts student COVERED: {covered_concepts}
- Concepts student MISSED: {missing_concepts}
- Causal chain coverage: {chain_coverage}
- Bloom's cognitive level: {blooms_label} (level {blooms_level}/6)
- SOLO level: {solo_label} (level {solo_level}/5)
- Misconceptions detected: {misc_count}{misc_details}
{kg_confidence_note}{topological_note}
Grade the student answer compared to the reference. Use causal chain coverage to assess depth of understanding beyond keyword matching. Critical misconceptions about core mechanisms should significantly lower the score even if other content is correct.

Return ONLY valid JSON:
{{
  "verified_score": <float 0.0–5.0 with one decimal, e.g. 2.5>,
  "adjustment_direction": "confirm|increase|decrease",
  "adjustment_reason": "2-3 sentence explanation comparing student to reference answer",
  "confidence": 0.0-1.0,
  "key_evidence": "Most compelling evidence for your grade"
}}"""

VERIFIER_USER_LAG = """QUESTION: {question}

REFERENCE ANSWER (expert answer — defines 5.0):
{reference_answer}

STUDENT ESSAY:
{student_answer}

CONCEPT ANALYSIS (from structured knowledge graph):
- Concepts student COVERED: {covered_concepts}
- Concepts student MISSED: {missing_concepts}
- Causal chain coverage: {chain_coverage}
- Bloom's cognitive level: {blooms_label} (level {blooms_level}/6)
- SOLO level: {solo_label} (level {solo_level}/5)
{kg_confidence_note}{topological_note}
- Misconceptions detected: {misc_count}{misc_details}

DEPTH EVALUATION CHECKLIST (answer each before scoring):
1. Does the essay explain HOW/WHY concepts work, or just name them? (depth vs. breadth)
2. Are the covered concepts explained accurately with mechanisms, or are they vague?
3. How many of the MISSED concepts are critical to a complete answer?
4. Does the essay demonstrate genuine understanding or surface-level recall?

Grade the student essay compared to the reference. Use the depth checklist and causal chain coverage to assess depth beyond keyword matching.

Return ONLY valid JSON:
{{
  "verified_score": <float 0.0–5.0 with one decimal>,
  "adjustment_direction": "confirm|increase|decrease",
  "depth_assessment": "depth (HOW/WHY explained) or breadth (concepts named only)?",
  "adjustment_reason": "2-3 sentence explanation comparing student to reference answer",
  "confidence": 0.0-1.0,
  "key_evidence": "Most compelling evidence for your grade"
}}"""


# ── SURE Framework constants ───────────────────────────────────────────────────

HUMAN_REVIEW_THRESHOLD = 0.10  # 0.5 / 5.0 on the 0-1 scale

_SURE_PERSONAS = [
    (
        "Meticulous",
        "You are a strict academic grader. Penalise vague language, missing mechanisms, "
        "and incomplete explanations. Require precision. An answer missing any critical "
        "concept from the reference scores no higher than 3.5.",
    ),
    (
        "Standard",
        "You are a fair academic grader. Reward correct core ideas, penalise significant "
        "omissions or misconceptions. Use the reference answer as the definitive standard.",
    ),
    (
        "Lenient",
        "You are a supportive academic grader. Reward demonstrated understanding and effort. "
        "Only penalise factually wrong statements.",
    ),
]

# LAG-specific personas: replace Lenient with Analytical to avoid over-rewarding
# essay breadth without depth. Essays naturally mention many concepts superficially —
# the Lenient persona inflates scores by ~0.6 pts on average for long answers.
_SURE_PERSONAS_LAG = [
    (
        "Meticulous",
        "You are a strict academic grader for long-form essays. Penalise shallow coverage, "
        "vague language, and missing mechanisms. A student who lists concepts without "
        "explaining them earns no more than 2.5/5.",
    ),
    (
        "Standard",
        "You are a fair academic grader for essays. Reward correct core ideas with clear "
        "explanations. Penalise significant omissions, misconceptions, and surface-level "
        "answers that lack depth. Breadth alone is not sufficient for a high score.",
    ),
    (
        "Analytical",
        "You are a depth-focused academic grader. Evaluate whether the student demonstrates "
        "genuine understanding of mechanisms and relationships, not just terminology recall. "
        "An essay that names concepts but does not explain how or why they work scores "
        "no higher than 3.0/5. Reserve 4.0+ for answers showing causal understanding.",
    ),
]


@dataclass
class SureResult:
    """Result from the SURE (Self-Uncertainty-Reduction Ensemble) verification."""

    scores: List[float]           # 3 raw verified scores (0-1)
    median_score: float           # median of scores
    spread: float                 # max - min
    requires_human_review: bool   # spread > HUMAN_REVIEW_THRESHOLD
    directions: List[str]         # confirm/increase/decrease per persona
    verifier_weight: float
    kg_score: float
    final_score: float            # blend: (1-w)*kg + w*median

    def to_dict(self) -> dict:
        return {
            "mode": "sure",
            "kg_score": round(self.kg_score, 4),
            "sure_scores": [round(s, 4) for s in self.scores],
            "median_score": round(self.median_score, 4),
            "spread": round(self.spread, 4),
            "requires_human_review": self.requires_human_review,
            "directions": self.directions,
            "verifier_weight": self.verifier_weight,
            "final_score": round(self.final_score, 4),
        }


@dataclass
class VerifierResult:
    """Result from the LLM verifier layer."""
    kg_score: float
    verified_score: float
    final_score: float
    adjustment_direction: str  # "confirm", "increase", "decrease"
    adjustment_reason: str
    confidence: float
    key_evidence: str
    verifier_weight: float

    def to_dict(self) -> dict:
        return {
            "kg_score": round(self.kg_score, 4),
            "verified_score": round(self.verified_score, 4),
            "final_score": round(self.final_score, 4),
            "adjustment_direction": self.adjustment_direction,
            "adjustment_reason": self.adjustment_reason,
            "confidence": round(self.confidence, 3),
            "key_evidence": self.key_evidence,
            "verifier_weight": self.verifier_weight,
        }


class LLMVerifier:
    """
    Post-scoring LLM verifier that validates and optionally adjusts the
    KG-computed composite score.

    Parameters
    ----------
    api_key         : Groq API key
    model           : LLM model name
    verifier_weight : Weight of LLM score in final blend (0 = KG only, 1 = LLM only)
                      Default 0.25 — KG dominates, LLM provides soft correction.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        verifier_weight: float = 0.25,
    ):
        self.client = Groq(api_key=api_key)
        self.model = model
        if not 0.0 <= verifier_weight <= 1.0:
            raise ValueError("verifier_weight must be in [0, 1]")
        self.verifier_weight = verifier_weight

    def verify(
        self,
        question: str,
        student_answer: str,
        kg_score: float,
        comparison_result: dict,
        blooms: dict,
        solo: dict,
        misconceptions: dict,
        reference_answer: str = "",
        mode: str = "sag",
    ) -> VerifierResult:
        """
        Verify and optionally adjust the KG-computed score.

        Parameters
        ----------
        question         : Assessment question
        student_answer   : Student's free-text response
        kg_score         : Overall score from ConceptGradePipeline
        comparison_result: Output of KnowledgeGraphComparator.compare().to_dict()
        blooms           : Bloom's classification dict
        solo             : SOLO classification dict
        mode             : "sag" (default) or "lag" — selects calibrated prompt for essays
        misconceptions   : Misconception detection dict

        Returns
        -------
        VerifierResult with blended final score
        """
        analysis = comparison_result.get("analysis", comparison_result)

        covered_str, critical_str, minor_str = self._extract_concept_strings(analysis)
        missing_str = ", ".join(filter(None, [critical_str.replace("none", ""), minor_str.replace("none", "")])).strip(", ") or "none — full coverage"
        chain_str = comparison_result.get("scores", {}).get("chain_coverage", None)
        chain_coverage_str = (
            f"{chain_str:.0%} of causal concept chains covered" if chain_str is not None
            else analysis.get("chain_coverage_summary", "not computed")
        )

        # Low-KG-confidence note: when concept coverage or KG relevance is low,
        # tell the verifier to rely on holistic assessment rather than KG evidence.
        cov_score = comparison_result.get("scores", {}).get("concept_coverage", 1.0)
        rho = comparison_result.get("scores", {}).get("kg_relevance_score", 1.0)
        if cov_score < 0.30 or rho < 0.25:
            kg_confidence_note = (
                "⚠ KG RELEVANCE LOW (coverage={:.0%}, ρ={:.0%}): The knowledge graph may not fully "
                "represent this topic's domain vocabulary. Rely primarily on your holistic assessment "
                "of the student answer vs. the reference answer rather than the KG concept lists.\n".format(cov_score, rho)
            )
        else:
            kg_confidence_note = ""

        # Topological note: anchor-conductance features for hallucination detection
        topo_summary = comparison_result.get("diagnostic", {}).get("topological_summary", "")
        anchor_ratio = comparison_result.get("scores", {}).get("anchor_ratio", 1.0)
        if topo_summary and anchor_ratio < 0.65:
            topological_note = f"⚙ GRAPH TOPOLOGY: {topo_summary}\n"
        else:
            topological_note = ""

        # Misconception details: surface critical misconceptions to the verifier
        misc_list = misconceptions.get("misconceptions", [])
        if misc_list:
            critical = [m for m in misc_list if m.get("severity", "").lower() in ("critical", "persistent")]
            if critical:
                details = "; ".join(
                    m.get("description", m.get("explanation", m.get("student_claim", "")))[:80]
                    for m in critical[:3]
                )
                misc_details = f" — CRITICAL: {details}"
            else:
                misc_details = ""
        else:
            misc_details = ""

        user_template = VERIFIER_USER_LAG if mode == "lag" else VERIFIER_USER
        fmt_kwargs = dict(
            question=question,
            reference_answer=reference_answer or "(not provided)",
            student_answer=student_answer,
            covered_concepts=covered_str,
            missing_concepts=missing_str,
            chain_coverage=chain_coverage_str,
            blooms_label=blooms.get("label", "Remember"),
            blooms_level=blooms.get("level", 1),
            solo_label=solo.get("label", "Prestructural"),
            solo_level=solo.get("level", 1),
            misc_count=misconceptions.get("total_misconceptions", 0),
            misc_details=misc_details,
            kg_confidence_note=kg_confidence_note,
            topological_note=topological_note,
        )
        user_prompt = user_template.format(**fmt_kwargs)

        try:
            system_prompt = VERIFIER_SYSTEM_LAG if mode == "lag" else VERIFIER_SYSTEM
            raw = self._call_llm(system_prompt, user_prompt)
            parsed = self._parse_json(raw)
            raw_score = float(parsed.get("verified_score", kg_score * 5))
            # Round to nearest 0.5
            verified_fine = round(raw_score * 2) / 2
            verified_fine = max(0.0, min(5.0, verified_fine))
            verified = verified_fine / 5.0   # 0-1 for blend arithmetic
            direction = parsed.get("adjustment_direction", "confirm")
            reason = parsed.get("adjustment_reason", "")
            conf = float(parsed.get("confidence", 0.5))
            evidence = parsed.get("key_evidence", "")
        except Exception as e:
            # Fallback: trust KG score
            import traceback
            print(f"  [Verifier] FALLBACK triggered — {type(e).__name__}: {e}")
            traceback.print_exc()
            verified = kg_score
            direction = "confirm"
            reason = f"LLM verification failed: {e}; using KG score unchanged."
            conf = 0.0
            evidence = ""

        # Blend: at verifier_weight=1.0 the KG analysis informs the prompt
        # but the LLM holistic grade drives the final score.
        final = (1.0 - self.verifier_weight) * kg_score + self.verifier_weight * verified

        print(
            f"  [Verifier] KG={kg_score * 5:.1f}/5 → verified={verified * 5:.1f}/5 "
            f"({direction}) → final={final * 5:.2f}/5"
        )

        return VerifierResult(
            kg_score=kg_score,
            verified_score=verified,
            final_score=round(final, 4),
            adjustment_direction=direction,
            adjustment_reason=reason,
            confidence=conf,
            key_evidence=evidence,
            verifier_weight=self.verifier_weight,
        )

    def verify_sure(
        self,
        question: str,
        student_answer: str,
        kg_score: float,
        comparison_result: dict,
        blooms: dict,
        solo: dict,
        misconceptions: dict,
        reference_answer: str = "",
        mode: str = "sag",
    ) -> "SureResult":
        """
        Run 3-persona SURE (Self-Uncertainty-Reduction Ensemble) verification.

        Parameters
        ----------
        mode : "sag" (default) uses Meticulous/Standard/Lenient personas.
               "lag" uses Meticulous/Standard/Analytical personas — replaces
               the Lenient persona which inflates scores for long essays that
               have breadth without depth.

        Each of the three personas grades the
        student answer independently. The final score is the median. A large
        spread across personas flags the answer for human review.

        Parameters
        ----------
        question         : Assessment question
        student_answer   : Student's free-text response
        kg_score         : Overall score from ConceptGradePipeline (0-1)
        comparison_result: Output of KnowledgeGraphComparator.compare().to_dict()
        blooms           : Bloom's classification dict
        solo             : SOLO classification dict
        misconceptions   : Misconception detection dict
        reference_answer : Expert/model reference answer (optional)

        Returns
        -------
        SureResult with median blended final score and human-review flag
        """
        scores_01: List[float] = []
        directions: List[str] = []

        # Build the shared user prompt (identical across all personas)
        analysis = comparison_result.get("analysis", comparison_result)
        covered_str, critical_str, minor_str = self._extract_concept_strings(analysis)
        missing_str = ", ".join(filter(None, [critical_str.replace("none", ""), minor_str.replace("none", "")])).strip(", ") or "none — full coverage"
        chain_str = comparison_result.get("scores", {}).get("chain_coverage", None)
        chain_coverage_str = (
            f"{chain_str:.0%} of causal concept chains covered" if chain_str is not None
            else comparison_result.get("analysis", {}).get("chain_coverage_summary", "not computed")
        )

        cov_score = comparison_result.get("scores", {}).get("concept_coverage", 1.0)
        rho = comparison_result.get("scores", {}).get("kg_relevance_score", 1.0)
        if cov_score < 0.30 or rho < 0.25:
            kg_confidence_note = (
                "⚠ KG RELEVANCE LOW (coverage={:.0%}, ρ={:.0%}): The knowledge graph may not fully "
                "represent this topic's domain vocabulary. Rely primarily on your holistic assessment "
                "of the student answer vs. the reference answer rather than the KG concept lists.\n".format(cov_score, rho)
            )
        else:
            kg_confidence_note = ""

        topo_summary = comparison_result.get("diagnostic", {}).get("topological_summary", "")
        anchor_ratio = comparison_result.get("scores", {}).get("anchor_ratio", 1.0)
        if topo_summary and anchor_ratio < 0.65:
            topological_note = f"⚙ GRAPH TOPOLOGY: {topo_summary}\n"
        else:
            topological_note = ""

        misc_list = misconceptions.get("misconceptions", [])
        if misc_list:
            critical = [m for m in misc_list if m.get("severity", "").lower() in ("critical", "persistent")]
            if critical:
                details = "; ".join(
                    m.get("description", m.get("explanation", m.get("student_claim", "")))[:80]
                    for m in critical[:3]
                )
                misc_details = f" — CRITICAL: {details}"
            else:
                misc_details = ""
        else:
            misc_details = ""

        user_template = VERIFIER_USER_LAG if mode == "lag" else VERIFIER_USER
        fmt_kwargs = dict(
            question=question,
            reference_answer=reference_answer or "(not provided)",
            student_answer=student_answer,
            covered_concepts=covered_str,
            missing_concepts=missing_str,
            chain_coverage=chain_coverage_str,
            blooms_label=blooms.get("label", "Remember"),
            blooms_level=blooms.get("level", 1),
            solo_label=solo.get("label", "Prestructural"),
            solo_level=solo.get("level", 1),
            misc_count=misconceptions.get("total_misconceptions", 0),
            misc_details=misc_details,
            kg_confidence_note=kg_confidence_note,
            topological_note=topological_note,
        )
        user_prompt = user_template.format(**fmt_kwargs)

        personas = _SURE_PERSONAS_LAG if mode == "lag" else _SURE_PERSONAS
        base_system = VERIFIER_SYSTEM_LAG if mode == "lag" else VERIFIER_SYSTEM

        def _grade_persona(args):
            persona_name, persona_prefix = args
            persona_system = f"{persona_prefix}\n\n{base_system}"
            try:
                raw = self._call_llm(persona_system, user_prompt)
                parsed = self._parse_json(raw)
                raw_score = float(parsed.get("verified_score", kg_score * 5))
                verified_fine = round(raw_score * 2) / 2
                verified_fine = max(0.0, min(5.0, verified_fine))
                return verified_fine / 5.0, parsed.get("adjustment_direction", "confirm"), persona_name
            except Exception as e:
                print(f"  [SURE/{persona_name}] FALLBACK — {type(e).__name__}: {e}; using kg_score")
                return kg_score, "confirm", persona_name

        from concurrent.futures import ThreadPoolExecutor, as_completed
        results_map = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(_grade_persona, p): p[0] for p in personas}
            for future in as_completed(futures):
                verified, direction, persona_name = future.result()
                results_map[persona_name] = (verified, direction)

        # Preserve original persona order for reproducibility
        for persona_name, _ in personas:
            verified, direction = results_map[persona_name]
            scores_01.append(verified)
            directions.append(direction)
            print(f"  [SURE/{persona_name}] score={verified * 5:.1f}/5 ({direction})")

        spread = max(scores_01) - min(scores_01)
        median_01 = statistics.median(scores_01)
        requires_review = spread > HUMAN_REVIEW_THRESHOLD

        final = (1.0 - self.verifier_weight) * kg_score + self.verifier_weight * median_01
        final = round(final, 4)

        print(
            f"  [SURE] KG={kg_score * 5:.1f}/5 → median={median_01 * 5:.1f}/5 "
            f"spread={spread * 5:.2f}/5 "
            f"{'⚠ REVIEW' if requires_review else 'OK'} → final={final * 5:.2f}/5"
        )

        return SureResult(
            scores=scores_01,
            median_score=round(median_01, 4),
            spread=round(spread, 4),
            requires_human_review=requires_review,
            directions=directions,
            verifier_weight=self.verifier_weight,
            kg_score=kg_score,
            final_score=final,
        )

    def _extract_concept_strings(self, analysis: dict) -> tuple[str, str, str]:
        """
        Return (covered_str, critical_missing_str, minor_missing_str).

        Missing concepts are split by importance:
          critical  : importance >= 0.6  (high-weight, core concepts)
          minor     : importance <  0.6  (supporting details)
        """
        matched = analysis.get("matched_concepts", [])
        missing_raw = analysis.get("missing_concepts", [])

        covered_str = ", ".join(matched[:12]) if matched else "none identified"

        critical, minor = [], []
        for g in missing_raw:
            if isinstance(g, dict):
                cid = g.get("concept_id", g.get("id", "?"))
                imp = float(g.get("importance", 0.5))
            else:
                cid, imp = str(g), 0.5
            if imp >= 0.6:
                critical.append(cid)
            else:
                minor.append(cid)

        critical_str = ", ".join(critical[:6]) if critical else "none"
        minor_str    = ", ".join(minor[:6])    if minor    else "none"
        return covered_str, critical_str, minor_str

    def _call_llm(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.0,   # Deterministic — verifier should be consistent
            max_tokens=1200,
        )
        return response.choices[0].message.content

    def _parse_json(self, text: str) -> dict:
        from conceptgrade.llm_client import parse_llm_json
        return parse_llm_json(text)
