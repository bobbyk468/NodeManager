"""
CrossParaIntegrator — Detects cross-paragraph concept integration in multi-segment essays.

Two-tier detection:
  1. Lexical tier  (free, no LLM): detect transitional phrases
  2. Semantic tier (1 LLM call):   detect implicit concept bridges via concept lists
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from conceptgrade.llm_client import LLMClient, parse_llm_json


# ── Transitional phrase registry ──────────────────────────────────────────────

_FORWARD_REFS = [
    "as we will see", "this leads to", "building on this", "furthermore",
    "as we shall see", "we will explore", "this will be", "next we",
]

_BACKWARD_REFS = [
    "as mentioned", "as shown above", "recall that", "this is why",
    "therefore", "thus", "consequently", "as discussed", "as noted",
    "as established", "as we saw", "as described", "as stated",
    "from the above", "given the above", "in light of this",
]

_CONTRAST_BRIDGES = [
    "however", "on the other hand", "in contrast", "unlike", "whereas",
    "despite this", "nevertheless", "nonetheless", "yet", "but",
    "conversely", "although", "even though",
]

_EXTENSION_BRIDGES = [
    "additionally", "moreover", "similarly", "this also explains",
    "in addition", "likewise", "by extension",
    "this further", "building upon", "this reinforces",
]

_BRIDGE_TYPES: list[tuple[str, list[str]]] = [
    ("forward",   _FORWARD_REFS),
    ("backward",  _BACKWARD_REFS),
    ("contrast",  _CONTRAST_BRIDGES),
    ("extension", _EXTENSION_BRIDGES),
]


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class IntegrationResult:
    lexical_bridges: list[dict]       = field(default_factory=list)
    semantic_bridges: list[dict]      = field(default_factory=list)
    integration_score: float          = 0.0   # 0–1
    integration_level: str            = "none" # none/weak/moderate/strong/n/a
    lexical_bridge_count: int         = 0
    semantic_bridge_count: int        = 0
    reasoning: str                    = ""
    # Contradiction detection fields
    contradictions: list[dict]        = field(default_factory=list)
    coherence_penalty: float          = 1.0   # multiplicative penalty 0–1 (1 = no penalty)
    coherence_report: str             = ""    # human-readable summary for verifier prompt

    def to_dict(self) -> dict:
        d = {
            "integration_score":     round(self.integration_score, 3),
            "integration_level":     self.integration_level,
            "lexical_bridge_count":  self.lexical_bridge_count,
            "semantic_bridge_count": self.semantic_bridge_count,
            "lexical_bridges":       self.lexical_bridges,
            "semantic_bridges":      self.semantic_bridges,
            "reasoning":             self.reasoning,
        }
        if self.contradictions:
            d["contradictions"]    = self.contradictions
            d["coherence_penalty"] = round(self.coherence_penalty, 3)
            d["coherence_report"]  = self.coherence_report
        return d


# ── Main class ─────────────────────────────────────────────────────────────────

class CrossParaIntegrator:
    """
    Detects cross-paragraph concept integration in multi-segment essays.

    Two-tier detection:
    1. Lexical tier (free, no LLM): detect transitional phrases
    2. Semantic tier (1 LLM call): detect implicit concept bridges
    """

    _SYSTEM_PROMPT = (
        "You are evaluating cross-paragraph concept integration in a student essay. "
        "Given concept lists per segment, identify explicit concept bridges — where a concept "
        "introduced in one paragraph is directly referenced, extended, or applied in a later paragraph. "
        "Return ONLY valid JSON."
    )

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model   = model
        self._client = LLMClient(api_key=api_key)

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, question: str, segment_scores: list) -> IntegrationResult:
        """
        Detect cross-paragraph integration.

        Parameters
        ----------
        question       : The assessment question text
        segment_scores : list[SegmentScore] from the LAG pipeline

        Returns
        -------
        IntegrationResult
        """
        n = len(segment_scores)

        # Single-segment: no cross-paragraph integration possible
        if n < 2:
            return IntegrationResult(
                lexical_bridges=[],
                semantic_bridges=[],
                integration_score=1.0,
                integration_level="n/a",
                lexical_bridge_count=0,
                semantic_bridge_count=0,
                reasoning="Single-segment answer — cross-paragraph integration is not applicable.",
            )

        # Tier 1: lexical detection (no LLM)
        lexical_bridges = self._detect_lexical(segment_scores)

        # Tier 2: semantic detection (1 LLM call)
        semantic_result = self._detect_semantic(question, segment_scores)

        semantic_bridges   = semantic_result.get("bridges", [])
        integration_score  = float(semantic_result.get("integration_score", 0.0))
        integration_level  = semantic_result.get("integration_level", "none")
        reasoning          = semantic_result.get("reasoning", "")

        # Blend lexical signal into the final score (lexical adds up to +0.15 bonus)
        lexical_bonus = min(0.15, len(lexical_bridges) * 0.02)
        blended_score = min(1.0, integration_score + lexical_bonus)

        # Re-evaluate level after blending
        final_level = self._score_to_level(blended_score) if integration_level != "n/a" else integration_level

        # Tier 3: contradiction detection (1 LLM call)
        contradiction_result = self._detect_contradictions(segment_scores)
        contradictions    = contradiction_result.get("contradictions", [])
        coherence_penalty = contradiction_result.get("coherence_penalty", 1.0)
        coherence_report  = contradiction_result.get("coherence_report", "")

        return IntegrationResult(
            lexical_bridges=lexical_bridges,
            semantic_bridges=semantic_bridges,
            integration_score=round(blended_score, 3),
            integration_level=final_level,
            lexical_bridge_count=len(lexical_bridges),
            semantic_bridge_count=len(semantic_bridges),
            reasoning=reasoning,
            contradictions=contradictions,
            coherence_penalty=coherence_penalty,
            coherence_report=coherence_report,
        )

    # ── Tier 1 — Lexical detection ────────────────────────────────────────────

    def _detect_lexical(self, segment_scores: list) -> list[dict]:
        """
        Scan each segment for transitional phrases and return bridge records.

        Each bridge record:
          {segment_from, segment_to, phrase, bridge_type}

        segment_from is the inferred source (previous segment index, 1-based).
        segment_to   is the current segment index (1-based).
        """
        bridges: list[dict] = []

        for ss in segment_scores:
            seg_index = ss.segment.index   # 1-based
            text      = ss.segment.text.lower()

            for bridge_type, phrases in _BRIDGE_TYPES:
                for phrase in phrases:
                    if re.search(r'\b' + re.escape(phrase) + r'\b', text):
                        # Backward/contrast/extension references imply a link from the prior segment
                        seg_from = max(1, seg_index - 1)
                        bridges.append({
                            "segment_from": seg_from,
                            "segment_to":   seg_index,
                            "phrase":       phrase,
                            "bridge_type":  bridge_type,
                        })
                        break  # Only record the first match per bridge_type per segment

        return bridges

    # ── Tier 2 — Semantic detection ───────────────────────────────────────────

    def _detect_semantic(self, question: str, segment_scores: list) -> dict:
        """
        Ask the LLM to identify concept bridges across segments.
        Returns the parsed JSON dict from the LLM.
        """
        # Build compact concept-list per segment (IDs only)
        seg_descriptions: list[str] = []
        for ss in segment_scores:
            concept_ids = [
                c.get("concept_id", c.get("id", ""))
                for c in ss.concepts
                if c.get("concept_id", c.get("id", ""))
            ]
            label = ss.segment.label
            seg_descriptions.append(
                f"Segment {ss.segment.index} ({label}): {concept_ids or ['(no concepts extracted)']}"
            )

        user_prompt = (
            f"QUESTION: {question}\n\n"
            f"SEGMENT CONCEPT LISTS:\n" +
            "\n".join(seg_descriptions) +
            "\n\n"
            "For each pair of consecutive segments, identify which concepts from the earlier "
            "segment are explicitly referenced, extended, or applied in the later segment.\n\n"
            "Return JSON with this exact structure:\n"
            "{\n"
            '  "bridges": [\n'
            '    {"from_segment": 1, "to_segment": 2, "concept": "<concept_id>", "bridge_type": "extension|reference|application|contrast"}\n'
            "  ],\n"
            '  "integration_score": 0.0,\n'
            '  "integration_level": "none|weak|moderate|strong",\n'
            '  "reasoning": "brief explanation"\n'
            "}"
        )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=400,
            )
            raw = response.choices[0].message.content
            return parse_llm_json(raw)
        except Exception as e:
            # Graceful fallback — return a zero-integration result
            return {
                "bridges": [],
                "integration_score": 0.0,
                "integration_level": "none",
                "reasoning": f"LLM call failed: {e}",
            }

    # ── Tier 3 — Contradiction detection ──────────────────────────────────────

    _CONTRADICTION_SYSTEM = (
        "You are a grading assistant checking whether a student's multi-paragraph essay "
        "contains factual contradictions — places where one paragraph makes a claim that "
        "directly conflicts with a claim in another paragraph. "
        "Focus only on contradictions about the same concept or mechanism. "
        "Ignore stylistic variation and mere differences in emphasis. "
        "Return ONLY valid JSON."
    )

    def _detect_contradictions(self, segment_scores: list) -> dict:
        """
        Detect factual contradictions across essay segments via a single LLM call.

        Returns a dict with:
          contradictions   : list of {seg_a, seg_b, claim_a, claim_b, severity}
          coherence_penalty: float  (1.0 = no penalty, 0.85 = minor, 0.6 = critical)
          coherence_report : str    (human-readable summary for verifier prompt)
        """
        # Build segment summaries — use full text for accurate contradiction detection
        seg_summaries: list[str] = []
        for ss in segment_scores:
            # Truncate only if very long (>600 chars) to fit model context while preserving key claims
            text_snippet = ss.segment.text[:600].replace("\n", " ").strip()
            seg_summaries.append(
                f"Segment {ss.segment.index} ({ss.segment.label}): \"{text_snippet}\""
            )

        user_prompt = (
            "ESSAY SEGMENTS:\n" +
            "\n".join(seg_summaries) +
            "\n\n"
            "Identify any pairs of segments that make directly contradictory factual claims "
            "about the same concept or mechanism.\n\n"
            "Return JSON:\n"
            "{\n"
            '  "contradictions": [\n'
            '    {"seg_a": 1, "seg_b": 2, "claim_a": "...", "claim_b": "...", '
            '"severity": "critical|minor"}\n'
            "  ],\n"
            '  "overall_coherence": "coherent|minor_issues|critical_issues"\n'
            "}"
        )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._CONTRADICTION_SYSTEM},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=1200,
            )
            raw = response.choices[0].message.content
            parsed = parse_llm_json(raw)
        except Exception as e:
            return {
                "contradictions": [],
                "coherence_penalty": 1.0,
                "coherence_report": f"Contradiction detection failed: {e}",
            }

        contradictions = parsed.get("contradictions", [])
        overall = parsed.get("overall_coherence", "coherent")

        # Compute penalty
        has_critical = any(c.get("severity") == "critical" for c in contradictions)
        has_minor    = any(c.get("severity") == "minor"    for c in contradictions)

        if has_critical:
            coherence_penalty = 0.60
        elif has_minor:
            coherence_penalty = 0.85
        else:
            coherence_penalty = 1.0

        # Build human-readable report for the verifier prompt
        if not contradictions:
            coherence_report = "No factual contradictions detected across paragraphs."
        else:
            lines = ["COHERENCE ISSUES DETECTED:"]
            for c in contradictions:
                sev = c.get("severity", "minor").upper()
                lines.append(
                    f"  [{sev}] Seg {c.get('seg_a')} vs Seg {c.get('seg_b')}: "
                    f"\"{c.get('claim_a')}\" contradicts \"{c.get('claim_b')}\""
                )
            lines.append(
                f"Coherence penalty applied: {coherence_penalty:.0%} of verifier score."
            )
            coherence_report = "\n".join(lines)

        return {
            "contradictions":    contradictions,
            "coherence_penalty": coherence_penalty,
            "coherence_report":  coherence_report,
        }

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _score_to_level(score: float) -> str:
        if score < 0.15:
            return "none"
        if score < 0.40:
            return "weak"
        if score < 0.70:
            return "moderate"
        return "strong"
