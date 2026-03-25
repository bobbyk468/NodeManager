"""
FeedbackSynthesizer — Professor-quality feedback generator.

The goal
---------
ConceptGrade's pipeline produces accurate *scores* but clinical output:
  "Score: 3.7/5. Missing: memory_compaction. Misconception in Segment 9."

The FeedbackSynthesizer converts raw pipeline evidence into feedback that
reads like a senior professor wrote it — specific, encouraging where warranted,
rigorous where not, and always pointing to *exactly* where the evidence was found.

Design principle: Better than raw AI
--------------------------------------
A direct "grade this essay" LLM prompt produces generic feedback.
FeedbackSynthesizer is better because it operates on *structured evidence*
from the ConceptGrade pipeline:

  - Exact concept coverage gaps (Knowledge Gaps vs. Accuracy Gaps)
  - Per-segment Bloom's level (so feedback is localised: "In Segment 3...")
  - Misconception severity (persistent vs. isolated)
  - Consistency Index (disciplined writer vs. flash-of-brilliance pattern)
  - Secondary KG hits (curriculum breadth visible to the grader)

This structured evidence is what prevents the feedback from being vague.
The LLM's role here is *prose generation*, not *judgement* — the judgement
has already been made by the KG pipeline.

Tone adaptation
----------------
Tone is automatically adjusted to the student's performance level:

  Score ≤ 2.0: Supportive — emphasise what they did correctly first
  Score 2.1–3.5: Constructive — balance positives and gaps equally
  Score 3.6–4.4: Rigorous — high standards, specific targets for improvement
  Score 4.5–5.0: Peer-level — acknowledge mastery, suggest frontier extensions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from conceptgrade.llm_client import LLMClient, parse_llm_json


# ── Prompts ──────────────────────────────────────────────────────────────────

_SYNTH_SYSTEM = """You are a senior Computer Science professor writing feedback on a
student's answer. Your feedback must:

1. Sound like it was written by a human expert, not a machine.
2. Be specific — reference exact concepts, segments, and examples the student used.
3. Distinguish between:
   - Knowledge Gaps: correct topics the student simply didn't cover
   - Accuracy Gaps: things the student stated incorrectly (misconceptions)
4. Open with what the student did well before addressing gaps.
5. Close with exactly what the student should do to reach the next grade level.
6. Match the tone to the student's score level (instructions below).
7. Write in second person ("your analysis", "you correctly identified").
8. Do NOT mention "ConceptGrade", "KG score", "Segment numbers", or any internal
   system terminology — speak as a professor, not a grader.

Return ONLY valid JSON."""

_SYNTH_USER = """STUDENT PERFORMANCE DATA:

Question: {question}
Final Score: {score:.1f} / 5.0
Tone Level: {tone_level}  ({tone_desc})

WHAT THE STUDENT DID WELL (Knowledge Graph evidence):
{strengths}

KNOWLEDGE GAPS (correct concepts not covered):
{knowledge_gaps}

ACCURACY GAPS (misconceptions detected):
{accuracy_gaps}

COGNITIVE DEPTH:
- Modal level: {modal_bloom} (Bloom's {modal_level}/6)
- Ceiling level: {ceiling_bloom} (Bloom's {ceiling_level}/6)
- Consistency: {consistency_label}  (CI={ci:.2f})
- Depth trajectory: {trajectory}

SECONDARY CURRICULUM COVERAGE:
{secondary_coverage}

TO REACH THE NEXT GRADE (what's needed for {next_score:.1f}/5.0):
{next_steps}

---
Write the professor feedback now. Structure it as:
{{
  "opening":   "1–2 sentences on what the student did well",
  "knowledge_gap_feedback": "1–2 sentences on topics not covered",
  "accuracy_gap_feedback":  "1–2 sentences on corrections needed (empty string if none)",
  "depth_feedback":         "1 sentence on cognitive depth",
  "closing":                "1–2 sentences on exactly how to reach the next grade",
  "one_line_summary":       "One sentence summary suitable for a grade report"
}}"""


# ── Tone configuration ────────────────────────────────────────────────────────

_TONE_CONFIG = {
    "supportive": {
        "range": (0.0, 2.0),
        "desc": "Supportive — open with positives, avoid discouraging language",
    },
    "constructive": {
        "range": (2.1, 3.5),
        "desc": "Constructive — balance positives and areas for improvement equally",
    },
    "rigorous": {
        "range": (3.6, 4.4),
        "desc": "Rigorous — high standards, specific technical targets, minimal praise",
    },
    "peer_level": {
        "range": (4.5, 5.0),
        "desc": "Peer-level — acknowledge mastery, suggest advanced extensions",
    },
}


def _detect_tone(score: float) -> tuple[str, str]:
    for level, cfg in _TONE_CONFIG.items():
        lo, hi = cfg["range"]
        if lo <= score <= hi:
            return level, cfg["desc"]
    return "constructive", _TONE_CONFIG["constructive"]["desc"]


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class FeedbackReport:
    """Structured professor-quality feedback."""
    score: float
    opening: str
    knowledge_gap_feedback: str
    accuracy_gap_feedback: str
    depth_feedback: str
    closing: str
    one_line_summary: str
    tone_level: str

    def full_text(self) -> str:
        """Render as a coherent prose paragraph for the student."""
        parts = [self.opening]
        if self.knowledge_gap_feedback:
            parts.append(self.knowledge_gap_feedback)
        if self.accuracy_gap_feedback:
            parts.append(self.accuracy_gap_feedback)
        if self.depth_feedback:
            parts.append(self.depth_feedback)
        parts.append(self.closing)
        return "  ".join(p.strip() for p in parts if p.strip())

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "one_line_summary": self.one_line_summary,
            "full_feedback": self.full_text(),
            "tone_level": self.tone_level,
            "structured": {
                "opening": self.opening,
                "knowledge_gap_feedback": self.knowledge_gap_feedback,
                "accuracy_gap_feedback": self.accuracy_gap_feedback,
                "depth_feedback": self.depth_feedback,
                "closing": self.closing,
            },
        }


# ── Main class ────────────────────────────────────────────────────────────────

class FeedbackSynthesizer:
    """
    Converts raw ConceptGrade pipeline output into professor-quality feedback.

    Parameters
    ----------
    api_key  : API key for the synthesis model
    model    : LLM for feedback prose generation
               Recommendation: Claude Haiku 4.5 (nuanced prose) or
               Gemini 2.5 Flash (faster, slightly less natural)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
    ):
        self.client = LLMClient(api_key=api_key)
        self.model  = model

    MAX_TOKENS = 1500   # Gemini generates verbose JSON; 800 truncates later fields

    def synthesize(
        self,
        question: str,
        final_score: float,
        # KG evidence
        covered_concepts: list[str],
        missing_primary_concepts: list[str],
        secondary_concepts_hit: list[str],
        # Misconceptions
        misconceptions: list[dict],        # [{"concept": ..., "description": ..., "severity": "persistent"|"isolated"}]
        # Depth profile
        modal_bloom: str,
        modal_level: int,
        ceiling_bloom: str,
        ceiling_level: int,
        consistency_index: float,
        depth_trajectory: str,             # "rising" | "falling" | "plateau" | "variable"
        # Optional context
        segment_labels: Optional[list[str]] = None,
    ) -> FeedbackReport:
        """
        Generate professor-quality feedback from structured pipeline evidence.

        The LLM receives only processed evidence — it never sees the raw student
        text. Its job is prose generation, not judgement.
        """
        tone_level, tone_desc = _detect_tone(final_score)

        strengths     = self._format_strengths(covered_concepts, secondary_concepts_hit, segment_labels)
        knowledge_gaps = self._format_knowledge_gaps(missing_primary_concepts)
        accuracy_gaps  = self._format_accuracy_gaps(misconceptions)
        next_steps    = self._next_steps_for(final_score, missing_primary_concepts,
                                              misconceptions, ceiling_level)
        next_score    = min(5.0, round(final_score + 1.0, 1))
        ci_label      = self._ci_label(consistency_index)

        user_prompt = _SYNTH_USER.format(
            question=question,
            score=final_score,
            tone_level=tone_level,
            tone_desc=tone_desc,
            strengths=strengths,
            knowledge_gaps=knowledge_gaps or "None — all primary concepts covered.",
            accuracy_gaps=accuracy_gaps or "None detected.",
            modal_bloom=modal_bloom,
            modal_level=modal_level,
            ceiling_bloom=ceiling_bloom,
            ceiling_level=ceiling_level,
            consistency_label=ci_label,
            ci=consistency_index,
            trajectory=depth_trajectory,
            secondary_coverage=", ".join(secondary_concepts_hit) if secondary_concepts_hit
                               else "No secondary curriculum concepts identified.",
            next_steps=next_steps,
            next_score=next_score,
        )

        try:
            raw    = self._call_llm(_SYNTH_SYSTEM, user_prompt, max_tokens=self.MAX_TOKENS)
            parsed = parse_llm_json(raw)
            return FeedbackReport(
                score=final_score,
                opening=parsed.get("opening", ""),
                knowledge_gap_feedback=parsed.get("knowledge_gap_feedback", ""),
                accuracy_gap_feedback=parsed.get("accuracy_gap_feedback", ""),
                depth_feedback=parsed.get("depth_feedback", ""),
                closing=parsed.get("closing", ""),
                one_line_summary=parsed.get("one_line_summary", ""),
                tone_level=tone_level,
            )
        except Exception as e:
            # Fallback: assemble plain-text feedback without LLM prose pass
            return self._fallback_report(
                final_score, tone_level,
                missing_primary_concepts, misconceptions, next_steps,
            )

    # ── Formatting helpers ────────────────────────────────────────────────

    def _format_strengths(
        self,
        covered: list[str],
        secondary: list[str],
        seg_labels: Optional[list[str]],
    ) -> str:
        lines = []
        if covered:
            lines.append(f"- Correctly identified concepts: {', '.join(covered[:8])}"
                         + (" (and more)" if len(covered) > 8 else ""))
        if secondary:
            lines.append(f"- Advanced curriculum coverage: {', '.join(secondary)}")
        return "\n".join(lines) if lines else "Basic concept presence confirmed."

    def _format_knowledge_gaps(self, missing: list[str]) -> str:
        if not missing:
            return ""
        return "\n".join(f"- {c}" for c in missing)

    def _format_accuracy_gaps(self, misconceptions: list[dict]) -> str:
        if not misconceptions:
            return ""
        lines = []
        for m in misconceptions:
            sev = m.get("severity", "isolated")
            desc = m.get("description", m.get("concept", ""))
            tag = " [persistent — mentioned multiple times]" if sev == "persistent" else ""
            lines.append(f"- {desc}{tag}")
        return "\n".join(lines)

    def _next_steps_for(
        self,
        score: float,
        missing: list[str],
        misconceptions: list[dict],
        ceiling_level: int,
    ) -> str:
        steps = []
        if misconceptions:
            first_misc = misconceptions[0].get("concept", "the identified misconception")
            steps.append(f"Correct the misconception about {first_misc}")
        if missing:
            top_missing = missing[:3]
            steps.append(f"Cover these missing concepts: {', '.join(top_missing)}")
        if ceiling_level < 4 and score < 4.0:
            steps.append("Attempt analysis-level reasoning — explain *why* relationships exist, not just *what* they are")
        if score >= 4.0 and ceiling_level < 5:
            steps.append("Add an evaluative argument: critique a limitation, compare tradeoffs, or propose an improvement")
        return "\n".join(f"- {s}" for s in steps) if steps else "- Maintain current depth and add secondary curriculum coverage."

    def _ci_label(self, ci: float) -> str:
        if ci >= 0.90:
            return "Highly consistent — disciplined technical writer"
        elif ci >= 0.70:
            return "Moderately consistent — good follow-through with occasional depth spikes"
        elif ci >= 0.50:
            return "Variable — strong sections alongside weaker ones"
        else:
            return "Flash-of-brilliance — isolated peak with mostly surface-level content"

    def _fallback_report(
        self,
        score: float,
        tone: str,
        missing: list[str],
        misconceptions: list[dict],
        next_steps: str,
    ) -> FeedbackReport:
        """Plain-text fallback when the LLM call fails."""
        gap_str  = f"Consider covering: {', '.join(missing[:3])}." if missing else ""
        misc_str = f"One correction needed: {misconceptions[0]['concept']}." \
                   if misconceptions else ""
        return FeedbackReport(
            score=score,
            opening="Your answer demonstrates understanding of the core topic.",
            knowledge_gap_feedback=gap_str,
            accuracy_gap_feedback=misc_str,
            depth_feedback="",
            closing=next_steps.replace("- ", "", 1),
            one_line_summary=f"Score {score:.1f}/5.0 — {gap_str or 'good coverage.'}",
            tone_level=tone,
        )

    def _call_llm(self, system: str, user: str, max_tokens: int = 800) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.3,    # Slight creativity for natural prose
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
