"""
Stage 3a — LRM-as-Verifier.

Uses the DeepSeek API (api.deepseek.com) to run DeepSeek-R1 as a reasoning
verifier. The API exposes reasoning_content (the chain-of-thought trace)
directly in the response — no Ollama, no local GPU, no <think> tag parsing.

Model priority
--------------
  Primary:  deepseek-reasoner  (DeepSeek-R1, best quality, ~$0.55/M tokens)
  Fallback: gemini-2.5-flash   (no trace exposed — used if no DeepSeek key)

Integration path
----------------
  Stage 2  Confidence-Weighted Matching  →  matched_concepts, confidence weights
  Stage 3a LRM-as-Verifier               →  LRMVerifierResult
               ├── raw_think_trace  (str)         — reasoning_content from DeepSeek API
               ├── valid            (bool)         — domain-logical validity verdict
               ├── reasoning        (str)          — one-sentence summary
               └── parsed_steps     (list[dict])   — Stage 3b TraceParser output
  Stage 4  Chain Coverage Scoring        →  coverage %

Format safeguards
-----------------
DeepSeek-R1 returns the final answer in `message.content` (separate from the
reasoning trace in `reasoning_content`), so JSON parsing is much cleaner than
Ollama. Three layers of protection remain:
  1. Prompt instructs strict JSON in the content field.
  2. _regex_extract_json() handles any remaining formatting noise.
  3. Safe default {"valid": true, "reasoning": "parse_error"} prevents crashes.

Latency
-------
DeepSeek API: ~5–15 seconds per answer (vs. 15–40s for local Ollama 70B).
Use averify() for async batch processing — concurrency cap in the runner.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from conceptgrade.trace_parser import parse_trace, summarise_trace


# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert educational assessment verifier with deep domain knowledge.

Your task: Verify whether a student's concept chain is domain-logically valid given a
Knowledge Graph (KG) of expected concepts and relationships.

Think through the problem step by step. Then output ONLY a valid JSON object with
exactly these two fields — no markdown, no code fences, no extra text:
{
  "valid": <boolean>,
  "reasoning": "<one sentence summary>"
}"""

_USER_PROMPT = """DOMAIN: {domain}

QUESTION:
{question}

STUDENT ANSWER:
{student_answer}

MATCHED CONCEPTS (from KG matching stage):
{matched_concepts}

EXPECTED KG RELATIONSHIPS:
{kg_edges}

MISSING CONCEPTS:
{missing_concepts}

CHAIN COVERAGE: {chain_coverage_pct:.0f}%

Verify: Is the student's concept chain domain-logically valid?
Consider whether implied relationships are correct even if not explicitly stated.
Flag any concept that is factually wrong (not just missing)."""


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class LRMVerifierResult:
    """Full output from Stage 3a + 3b."""

    # Stage 3a
    valid: bool
    reasoning: str
    raw_think_trace: str
    latency_ms: int
    model_used: str

    # Stage 3b (populated by TraceParser)
    parsed_steps: list[dict] = field(default_factory=list)
    trace_summary: dict = field(default_factory=dict)
    net_confidence_delta: float = 0.0

    def to_dict(self) -> dict:
        return {
            "valid":                self.valid,
            "reasoning":            self.reasoning,
            "raw_think_trace":      self.raw_think_trace,
            "latency_ms":           self.latency_ms,
            "model_used":           self.model_used,
            "parsed_steps":         self.parsed_steps,
            "trace_summary":        self.trace_summary,
            "net_confidence_delta": round(self.net_confidence_delta, 3),
        }


# ── JSON extraction helpers ───────────────────────────────────────────────────

_JSON_RE = re.compile(r'\{[^{}]*"valid"\s*:\s*(true|false)[^{}]*\}', re.DOTALL | re.IGNORECASE)


def _regex_extract_json(text: str) -> Optional[dict]:
    """Extract the first JSON object containing "valid" from text."""
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    match = _JSON_RE.search(text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    brace = re.search(r'\{.*?\}', text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group())
        except json.JSONDecodeError:
            pass

    return None


# ── DeepSeek client ───────────────────────────────────────────────────────────

class _DeepSeekClient:
    """
    Thin wrapper around the DeepSeek API using the openai SDK.
    api.deepseek.com is OpenAI-compatible; reasoning_content is exposed
    directly on the response message object.
    """

    def __init__(self, api_key: str, model: str = "deepseek-reasoner"):
        self.api_key = api_key
        self.model   = model

    def chat(self, system: str, user: str) -> tuple[str, str]:
        """
        Returns (content, reasoning_content).
        content           — the final JSON verdict
        reasoning_content — the full chain-of-thought trace
        """
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.0,
            max_tokens=8192,
        )
        msg = resp.choices[0].message
        content           = msg.content or ""
        reasoning_content = getattr(msg, "reasoning_content", "") or ""
        return content, reasoning_content

    async def achat(self, system: str, user: str) -> tuple[str, str]:
        """Async wrapper — runs the blocking call in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.chat, system, user)


# ── Gemini client (thinking-enabled) ─────────────────────────────────────────

class _GeminiClient:
    """
    Gemini 2.5 Flash with thinking enabled.

    When thinking_budget > 0 (default 8192), the model exposes its full
    chain-of-thought via response parts with part.thought == True — equivalent
    to DeepSeek's reasoning_content field. Typical latency: 5–15 s/sample
    (vs. ~58 s for DeepSeek-R1).

    Set thinking_budget=0 to disable thinking (fast but no trace produced).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        thinking_budget: int = 8192,
    ):
        self._api_key        = api_key
        self._model          = model
        self._thinking_budget = thinking_budget

    def chat(self, system: str, user: str) -> tuple[str, str]:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self._api_key)

            include = self._thinking_budget > 0
            thinking_cfg = types.ThinkingConfig(
                thinking_budget=self._thinking_budget,
                include_thoughts=include,   # expose thought parts in response
            )
            # temperature must be 1.0 when thinking is enabled (API requirement)
            temp = 1.0 if include else 0.0

            config = types.GenerateContentConfig(
                temperature=temp,
                system_instruction=system,
                thinking_config=thinking_cfg,
            )
            resp = client.models.generate_content(
                model=self._model,
                contents=user,
                config=config,
            )

            answer_text  = ""
            thinking_text = ""
            try:
                for part in resp.candidates[0].content.parts:
                    if getattr(part, "thought", False):
                        thinking_text += part.text or ""
                    else:
                        answer_text += part.text or ""
            except (IndexError, AttributeError):
                answer_text = resp.text or ""

            return answer_text, thinking_text

        except Exception as e:
            return f'{{"valid": true, "reasoning": "gemini error: {e}"}}', ""

    async def achat(self, system: str, user: str) -> tuple[str, str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.chat, system, user)


# ── Main LRMVerifier ──────────────────────────────────────────────────────────

class LRMVerifier:
    """
    Stage 3a + 3b combined verifier.

    Parameters
    ----------
    deepseek_api_key : str, optional
        DeepSeek API key (platform.deepseek.com). When provided, DeepSeek-R1
        is used as the primary backend (~58 s/sample, richest traces).
    deepseek_model : str
        Default "deepseek-reasoner" (R1). Use "deepseek-chat" for V3 (no trace).
    gemini_api_key : str, optional
        Gemini API key. When provided and deepseek_api_key is absent (or
        use_gemini_primary=True), Gemini 2.5 Flash with thinking is used
        (~5–15 s/sample, full chain-of-thought trace via part.thought).
    gemini_thinking_budget : int
        Token budget for Gemini thinking (default 8192). Set 0 to disable
        thinking — fast but produces no trace.
    use_gemini_primary : bool
        Force Gemini as primary even if deepseek_api_key is present.
        Useful for ablation runs where speed matters more than R1 depth.
    max_trace_steps : int
        Maximum ParsedStep entries returned (default 20).

    Usage (batch / async)
    ---------------------
        # Fast Gemini path (~10 s/sample, full trace):
        verifier = LRMVerifier(gemini_api_key=os.environ["GEMINI_API_KEY"])

        # DeepSeek-R1 path (~58 s/sample, deepest trace):
        verifier = LRMVerifier(deepseek_api_key=os.environ["DEEPSEEK_API_KEY"])

        result = await verifier.averify(
            domain="Neural Networks",
            question="Explain backpropagation.",
            student_answer="...",
            matched_concepts=["Gradient_Descent", "Weight_Update"],
            missing_concepts=["Chain_Rule"],
            kg_nodes=["Backpropagation", "Gradient_Descent", ...],
            kg_edge_types=["PREREQUISITE_FOR", "PRODUCES"],
            kg_edges_text="Gradient_Descent PREREQUISITE_FOR Backpropagation",
            chain_coverage_pct=67.0,
        )
        result.parsed_steps   # → feed to VerifierReasoningPanel
        result.trace_summary  # → feed to ClassSummaryCard
    """

    def __init__(
        self,
        deepseek_api_key:        Optional[str] = None,
        deepseek_model:          str = "deepseek-reasoner",
        gemini_api_key:          Optional[str] = None,
        gemini_thinking_budget:  int = 8192,
        use_gemini_primary:      bool = False,
        max_trace_steps:         int = 20,
    ):
        use_gemini = (gemini_api_key and (use_gemini_primary or not deepseek_api_key))
        use_deepseek = deepseek_api_key and not use_gemini_primary

        if use_deepseek:
            self._client    = _DeepSeekClient(deepseek_api_key, deepseek_model)
            self._client_id = deepseek_model
        elif use_gemini:
            self._client    = _GeminiClient(
                gemini_api_key,
                thinking_budget=gemini_thinking_budget,
            )
            label = "gemini-2.5-flash-thinking" if gemini_thinking_budget > 0 else "gemini-2.5-flash-no-trace"
            self._client_id = label
        else:
            raise ValueError(
                "Provide at least one of: deepseek_api_key or gemini_api_key.\n"
                "Get a DeepSeek key at: https://platform.deepseek.com"
            )
        self._max_steps = max_trace_steps

    async def averify(
        self,
        domain:             str,
        question:           str,
        student_answer:     str,
        matched_concepts:   list[str],
        missing_concepts:   list[str],
        kg_nodes:           list[str],
        kg_edge_types:      list[str],
        kg_edges_text:      str,
        chain_coverage_pct: float,
    ) -> LRMVerifierResult:
        """Async verify — await concurrently in batch pipelines."""

        user_prompt = _USER_PROMPT.format(
            domain             = domain,
            question           = question,
            student_answer     = student_answer,
            matched_concepts   = ", ".join(matched_concepts) or "none",
            kg_edges           = kg_edges_text or "not provided",
            missing_concepts   = ", ".join(missing_concepts) or "none",
            chain_coverage_pct = chain_coverage_pct,
        )

        t0 = time.monotonic()
        content, raw_think = await self._client.achat(_SYSTEM_PROMPT, user_prompt)
        latency_ms = int((time.monotonic() - t0) * 1000)

        # Parse verdict
        parsed_json = _regex_extract_json(content)
        if parsed_json and "valid" in parsed_json:
            valid     = bool(parsed_json["valid"])
            reasoning = str(parsed_json.get("reasoning", ""))
        else:
            print(f"  [LRMVerifier] JSON parse failed — safe default. tail={content[-150:]!r}")
            valid     = True
            reasoning = "parse_error: could not extract verdict"

        # Stage 3b: TraceParser
        parsed_steps: list[dict] = []
        trace_summary: dict      = {}

        if raw_think:
            parsed_steps  = parse_trace(
                raw_lrm_output = raw_think,   # reasoning_content is already stripped of <think> tags
                kg_nodes       = kg_nodes,
                kg_edge_types  = kg_edge_types,
                max_steps      = self._max_steps,
            )
            trace_summary = summarise_trace(parsed_steps)

        net_delta = sum(s["confidence_delta"] for s in parsed_steps)

        print(
            f"  [LRMVerifier] model={self._client_id} valid={valid} "
            f"latency={latency_ms}ms steps={len(parsed_steps)} "
            f"trace_chars={len(raw_think)} net_delta={net_delta:+.2f}"
        )

        return LRMVerifierResult(
            valid                = valid,
            reasoning            = reasoning,
            raw_think_trace      = raw_think,
            latency_ms           = latency_ms,
            model_used           = self._client_id,
            parsed_steps         = parsed_steps,
            trace_summary        = trace_summary,
            net_confidence_delta = round(net_delta, 3),
        )

    def verify(self, **kwargs) -> LRMVerifierResult:
        """Synchronous wrapper — blocks until done. Use averify() in batch."""
        return asyncio.get_event_loop().run_until_complete(self.averify(**kwargs))
