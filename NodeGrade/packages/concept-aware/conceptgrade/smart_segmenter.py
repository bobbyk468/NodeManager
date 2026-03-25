"""
SmartSegmenter — AI-driven semantic segmentation for long-form answers.

Problem with fixed-size chunking
---------------------------------
Splitting at every 500 words risks cutting in the middle of an argument,
separating a claim from its evidence, or splitting an anaphoric reference
from the term it refers to.  This makes individual chunks look "incomplete"
to downstream graders.

Solution: LLM-driven boundary detection
-----------------------------------------
A fast, cheap model (Gemini Flash-Lite or Claude Haiku) scans the full text
once and identifies where the topic *genuinely shifts*.  The result is a set
of variable-length segments aligned to natural argument structure:

    Intro          → 280 words
    Manual Alloc   → 720 words
    Reference Cnt  → 510 words
    Tracing GC     → 680 words
    Conclusion     → 240 words

Any segment that still exceeds MAX_WORDS is recursively split using the
same LLM approach (not dumb word-counting), ensuring the constraint is met
without introducing artificial breaks.

Output
------
List of Segment objects, each carrying:
    - index        : 1-based position
    - label        : Human-readable section title (from LLM)
    - text         : Raw segment text
    - word_count   : Number of words
    - start_word   : Starting word offset in the original document
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from conceptgrade.llm_client import LLMClient, parse_llm_json


# ── Prompts ─────────────────────────────────────────────────────────────────

_BOUNDARY_SYSTEM = """You are a document structure analyst.
Your task: identify where the topic genuinely shifts in the given text.
A topic shift occurs when the student transitions to a new main concept,
argument, or section — NOT just a new paragraph.

Rules:
- Ignore minor paragraph breaks within the same topic.
- Identify only MAJOR transitions (typically 3–8 segments for a 5,000-word essay).
- Each segment should be a coherent, self-contained argument unit.
- Return ONLY valid JSON."""

_BOUNDARY_USER = """Identify the topic-shift boundaries in the following essay text.

TEXT:
{text}

Return a JSON array where each element describes one segment:
{{
  "segments": [
    {{
      "label": "Short title for this section (5 words max)",
      "start_phrase": "First 8–10 words of this segment, verbatim",
      "end_phrase":   "Last 8–10 words of this segment, verbatim"
    }},
    ...
  ]
}}

IMPORTANT: start_phrase and end_phrase must be exact substrings of the text."""

_RECURSIVE_SYSTEM = """You are a document structure analyst splitting one section of a
larger essay.  This section is too long and must be divided into 2–3 sub-sections
at a natural topic boundary within it.  Return ONLY valid JSON."""

_RECURSIVE_USER = """Divide the following text into 2–3 sub-sections at natural topic shifts.

TEXT:
{text}

Return:
{{
  "segments": [
    {{
      "label": "Sub-section title",
      "start_phrase": "First 8–10 words verbatim",
      "end_phrase":   "Last 8–10 words verbatim"
    }}
  ]
}}"""

_SUMMARY_SYSTEM = """You are a technical writing analyst.
Extract a concise Executive Summary and Structural Outline from the following essay.
Focus exclusively on technical claims — ignore prose and filler.
Return ONLY valid JSON."""

_SUMMARY_USER = """Essay text (may be truncated to first 2,000 words for efficiency):
{text}

Return:
{{
  "executive_summary": "2–3 sentences capturing the main thesis and key arguments",
  "structural_outline": [
    {{"label": "section name", "main_concepts": ["concept1", "concept2"]}}
  ]
}}"""


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class Segment:
    """One semantically coherent chunk of a longer answer."""
    index: int
    label: str
    text: str
    word_count: int
    start_word: int          # word offset in the original document
    subsegment_of: Optional[int] = None   # parent index if recursively split


@dataclass
class SegmentationResult:
    """Full output of SmartSegmenter.segment()."""
    segments: list[Segment]
    executive_summary: str
    structural_outline: list[dict]
    total_words: int
    strategy: str            # "passthrough" | "sliding_window" | "smart_ai"

    def context_prefix(self) -> str:
        """Short prefix to prepend to every segment prompt (Global Context Injector)."""
        outline_str = "; ".join(
            f"{s['label']}: {', '.join(s.get('main_concepts', []))}"
            for s in self.structural_outline
        )
        return (
            f"GLOBAL CONTEXT: {self.executive_summary}\n"
            f"STRUCTURAL OUTLINE: {outline_str}\n"
        )


# ── Main class ────────────────────────────────────────────────────────────────

class SmartSegmenter:
    """
    AI-driven semantic segmenter for long-form student answers.

    Segmentation strategy is chosen automatically based on answer length:

    ┌────────────────┬──────────────────────────────────────────────────────┐
    │ Word count     │ Strategy                                             │
    ├────────────────┼──────────────────────────────────────────────────────┤
    │ ≤ PASSTHROUGH  │ Return whole text as one segment (no LLM call)       │
    │ ≤ WINDOW_MAX   │ Sliding-window (150w window, 50w overlap, no LLM)    │
    │ > WINDOW_MAX   │ AI boundary detection + recursive split if needed    │
    └────────────────┴──────────────────────────────────────────────────────┘

    Parameters
    ----------
    api_key   : API key for the segmentation model
    model     : LLM to use for boundary detection (default: Gemini Flash-Lite)
    max_words : Hard limit per segment; segments above this are recursively split
    passthrough_threshold : Below this word count → single segment, no splitting
    window_threshold      : Below this → sliding window; above → AI segmentation
    """

    PASSTHROUGH_THRESHOLD = 300    # words — use as-is
    WINDOW_THRESHOLD      = 800    # words — sliding window vs. AI
    DEFAULT_MAX_WORDS     = 600    # hard cap per segment

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        max_words: int = DEFAULT_MAX_WORDS,
    ):
        self.client = LLMClient(api_key=api_key)
        self.model  = model
        self.max_words = max_words

    # ── Public API ────────────────────────────────────────────────────────

    def segment(self, text: str) -> SegmentationResult:
        """
        Segment the answer and generate its Global Context (Executive Summary).

        Returns a SegmentationResult with segments + context_prefix().
        """
        words = text.split()
        total = len(words)

        # --- Strategy 1: passthrough (short answer) ----------------------
        if total <= self.PASSTHROUGH_THRESHOLD:
            segs = [Segment(index=1, label="Full Answer", text=text,
                            word_count=total, start_word=0)]
            return SegmentationResult(
                segments=segs,
                executive_summary="",
                structural_outline=[],
                total_words=total,
                strategy="passthrough",
            )

        # --- Strategy 2: sliding window (medium answer) ------------------
        if total <= self.WINDOW_THRESHOLD:
            segs = self._sliding_window(words)
            return SegmentationResult(
                segments=segs,
                executive_summary="",
                structural_outline=[],
                total_words=total,
                strategy="sliding_window",
            )

        # --- Strategy 3: AI semantic segmentation (long essay) -----------
        summary_data = self._generate_summary(text[:8000])   # first ~2k words
        raw_segs     = self._detect_boundaries(text)
        segments     = self._resolve_boundaries(text, raw_segs)
        segments     = self._enforce_max_words(text, segments)

        return SegmentationResult(
            segments=segments,
            executive_summary=summary_data.get("executive_summary", ""),
            structural_outline=summary_data.get("structural_outline", []),
            total_words=total,
            strategy="smart_ai",
        )

    # ── Private helpers ────────────────────────────────────────────────────

    def _sliding_window(self, words: list[str],
                         window: int = 150, stride: int = 100) -> list[Segment]:
        """Fixed sliding-window fallback for medium-length answers."""
        segments = []
        i = 0
        idx = 1
        while i < len(words):
            chunk_words = words[i: i + window]
            segments.append(Segment(
                index=idx,
                label=f"Segment {idx}",
                text=" ".join(chunk_words),
                word_count=len(chunk_words),
                start_word=i,
            ))
            i += stride
            idx += 1
        return segments

    def _generate_summary(self, text_excerpt: str) -> dict:
        """Generate Executive Summary + Structural Outline via LLM."""
        try:
            raw = self._call_llm(_SUMMARY_SYSTEM, _SUMMARY_USER.format(text=text_excerpt))
            return parse_llm_json(raw)
        except Exception:
            return {"executive_summary": "", "structural_outline": []}

    def _detect_boundaries(self, text: str) -> list[dict]:
        """Ask the LLM where topic shifts occur. Returns raw segment descriptors."""
        # Feed up to ~6,000 words to keep prompt manageable
        excerpt = " ".join(text.split()[:6000])
        try:
            raw = self._call_llm(_BOUNDARY_SYSTEM, _BOUNDARY_USER.format(text=excerpt),
                                 max_tokens=1024)
            parsed = parse_llm_json(raw)
            return parsed.get("segments", [])
        except Exception:
            return []

    def _resolve_boundaries(self, text: str, raw_segs: list[dict]) -> list[Segment]:
        """
        Convert start_phrase / end_phrase markers into actual text slices.

        Falls back to equal-thirds splitting if phrases can't be located.
        """
        if not raw_segs:
            return self._equal_split(text)

        # Build a list of (start_char_idx, end_char_idx, label) tuples
        boundaries = []
        cursor = 0
        for seg in raw_segs:
            start_p = seg.get("start_phrase", "").strip()
            end_p   = seg.get("end_phrase", "").strip()

            # Find start phrase from current cursor onward
            s_idx = text.find(start_p, cursor) if start_p else cursor
            if s_idx == -1:
                s_idx = cursor   # phrase not found, continue from cursor

            # Find end phrase from s_idx onward
            e_raw = text.find(end_p, s_idx) if end_p else -1
            if e_raw != -1:
                e_idx = e_raw + len(end_p)
            else:
                e_idx = -1       # will be resolved in next iteration

            boundaries.append((s_idx, e_idx, seg.get("label", f"Segment {len(boundaries)+1}")))
            cursor = s_idx + 1

        # Fill in any -1 end indices by using next segment's start
        segments: list[Segment] = []
        for i, (s_idx, e_idx, label) in enumerate(boundaries):
            if e_idx == -1:
                # Use start of next boundary, or end of text
                next_start = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
                e_idx = next_start
            chunk = text[s_idx:e_idx].strip()
            wc    = len(chunk.split())
            # Compute start word offset
            start_word = len(text[:s_idx].split())
            segments.append(Segment(
                index=i + 1,
                label=label,
                text=chunk,
                word_count=wc,
                start_word=start_word,
            ))

        return [s for s in segments if s.word_count > 20]   # drop near-empty fragments

    def _enforce_max_words(self, text: str, segments: list[Segment]) -> list[Segment]:
        """
        Recursively split any segment that exceeds max_words using the LLM.
        If the LLM fails, fall back to equal halving.
        """
        result: list[Segment] = []
        for seg in segments:
            if seg.word_count <= self.max_words:
                result.append(seg)
                continue

            # Try LLM recursive split
            sub_segs = self._recursive_split(seg)
            for j, sub in enumerate(sub_segs):
                sub.index = len(result) + 1
                sub.subsegment_of = seg.index
                result.append(sub)

        # Re-index sequentially
        for k, s in enumerate(result):
            s.index = k + 1
        return result

    def _recursive_split(self, seg: Segment) -> list[Segment]:
        """Split an oversized segment into 2–3 parts using the LLM."""
        try:
            raw     = self._call_llm(_RECURSIVE_SYSTEM,
                                     _RECURSIVE_USER.format(text=seg.text),
                                     max_tokens=512)
            parsed  = parse_llm_json(raw)
            sub_raw = parsed.get("segments", [])
            if len(sub_raw) >= 2:
                return self._resolve_boundaries(seg.text, sub_raw)
        except Exception:
            pass
        # Fallback: equal halving
        return self._equal_split(seg.text)

    def _equal_split(self, text: str, n: int = 2) -> list[Segment]:
        """Split text into n equal parts by word count (last-resort fallback)."""
        words = text.split()
        size  = max(1, len(words) // n)
        segs  = []
        for i in range(n):
            chunk = words[i * size: (i + 1) * size]
            segs.append(Segment(
                index=i + 1,
                label=f"Part {i + 1}",
                text=" ".join(chunk),
                word_count=len(chunk),
                start_word=i * size,
            ))
        return [s for s in segs if s.word_count > 0]

    def _call_llm(self, system: str, user: str, max_tokens: int = 800) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
