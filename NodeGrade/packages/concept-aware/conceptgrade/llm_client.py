"""
LLM Client — multi-provider, provider-agnostic wrapper.

Supports Anthropic (Claude), Google (Gemini), and OpenAI (GPT/o-series).
Provider is auto-detected from the model name — no call-site changes needed.

Model name → Provider mapping
------------------------------
  claude-*         → Anthropic  (claude-haiku-4-5-20251001, claude-sonnet-4-6, …)
  gemini-*         → Google     (gemini-2.0-flash, gemini-flash-latest, …)
  gpt-* / o1 / o3 → OpenAI     (gpt-4o, o3-mini, …)

Interface (unchanged from original):
    client = LLMClient(api_key=api_key)
    response = client.chat.completions.create(
        model=model, messages=[...], temperature=0.1, max_tokens=512
    )
    text = response.choices[0].message.content

Swap provider simply by passing a different model name to create().
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


# ============================================================================
# Framework Fix #22 (2026-06-15): request-level logging.
#
# Every LLM call routed through LLMClient is logged via a thread-safe JSONL
# writer when the CONCEPTGRADE_LLM_LOG env var is set. This survives the
# downstream `except Exception` catches in the verifier and cognitive depth
# classifier, so a silently-degraded score still has a trail in the log.
#
# Activate by setting CONCEPTGRADE_LLM_LOG to a file path. Set to "stderr"
# to log to standard error (useful for ad-hoc debugging). Default OFF so
# batch runs don't accidentally write multi-GB logs.
#
# Log line format (one JSON object per line):
#   { "ts": <epoch>, "provider": "anthropic|google|openai|deepseek",
#     "model": "...", "prompt_chars": N, "latency_ms": M,
#     "outcome": "success" | "error",
#     "error_type": "ValueError" (only when outcome=error),
#     "error_message": "..." (only when outcome=error),
#     "response_chars": N (only when outcome=success) }
# ============================================================================


class _LLMLogger:
    """Thread-safe JSONL appender. Owns its own write lock."""

    def __init__(self, target: str | None):
        self._target = target  # None | "stderr" | filesystem path
        self._lock = threading.Lock()
        self._handle = None
        if target and target != "stderr":
            p = Path(target)
            p.parent.mkdir(parents=True, exist_ok=True)
            self._handle = p.open("a", buffering=1)

    @property
    def enabled(self) -> bool:
        return self._target is not None

    def write(self, record: dict) -> None:
        if not self.enabled:
            return
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            if self._target == "stderr":
                import sys as _sys
                print(line, file=_sys.stderr, flush=True)
            else:
                self._handle.write(line + "\n")


_LLM_LOG = _LLMLogger(os.environ.get("CONCEPTGRADE_LLM_LOG") or None)


def _prompt_chars(messages: list[dict]) -> int:
    """Sum of message-content character lengths — coarse prompt-size proxy."""
    return sum(len(str(m.get("content", ""))) for m in messages)


def parse_llm_json(text: str) -> dict:
    """
    Robustly parse JSON from an LLM response.

    Handles:
      - Markdown code fences: ```json ... ```
      - Missing commas between properties (Gemini quirk)
      - Trailing commas in arrays/objects
      - Python-style True/False/None
      - Truncated responses (best-effort via json-repair)
    """
    if text is None:
        raise ValueError("LLM returned None (empty or blocked response)")

    # 1. Strip markdown code fences
    md = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if md:
        text = md.group(1).strip()

    # 2. Try strict parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Quick fixes for common Gemini issues
    fixed = text
    fixed = re.sub(r',\s*([}\]])', r'\1', fixed)          # trailing commas
    fixed = re.sub(r'([}\]"\d])\s*\n(\s*["{])', r'\1,\n\2', fixed)  # missing commas
    fixed = fixed.replace('True', 'true').replace('False', 'false').replace('None', 'null')
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 4. Find outermost { } and try again
    start, end = fixed.find('{'), fixed.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(fixed[start:end + 1])
        except json.JSONDecodeError:
            pass

    # 5. Use json-repair as last resort
    try:
        from json_repair import repair_json
        repaired = repair_json(text)
        return json.loads(repaired)
    except Exception:
        pass

    raise ValueError(f"Could not parse JSON: {text[:300]}")


# ── Shared response types (OpenAI-compatible shape) ────────────────────────────

class _Message:
    def __init__(self, content: str):
        self.content = content


class _Choice:
    def __init__(self, content: str):
        self.message = _Message(content)


class _Response:
    def __init__(self, content: str):
        self.choices = [_Choice(content)]


# ── Provider detection ─────────────────────────────────────────────────────────

def detect_provider(model: str) -> str:
    """Return 'anthropic', 'google', 'openai', or 'deepseek' based on model name prefix."""
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith("gemini") or m.startswith("models/gemini"):
        return "google"
    if m.startswith("gpt") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4"):
        return "openai"
    if m.startswith("deepseek"):
        return "deepseek"
    # Fallback
    return "anthropic"


# ── Anthropic backend ──────────────────────────────────────────────────────────

class _AnthropicCompletions:
    # Framework Fix #21 (2026-06-15): 60s default timeout matching Gemini.
    # Without this we relied on the anthropic SDK's default (10 minutes
    # historically), which could hang a batch run on a stuck connection.
    DEFAULT_TIMEOUT_S = 60.0

    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(
            api_key=api_key,
            timeout=self.DEFAULT_TIMEOUT_S,
        )

    def create(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 1024,
        **kwargs,
    ) -> _Response:
        system = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})

        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=user_messages,
            temperature=temperature,
        )
        # Same null/empty-content protection as Gemini/DeepSeek/OpenAI (Fix #20/#21).
        # response.content may be an empty list when stop_reason == "max_tokens"
        # with no assistant text emitted, or contain only non-text blocks.
        if not response.content:
            raise ValueError(
                f"Anthropic returned empty content list "
                f"(model={model}, stop_reason={getattr(response, 'stop_reason', 'unknown')}). "
                f"Possible causes: max_tokens hit before text emission, "
                f"tool-use-only response, or upstream API error."
            )
        first = response.content[0]
        text = getattr(first, "text", None)
        if not text:
            raise ValueError(
                f"Anthropic first content block has no text "
                f"(model={model}, block_type={getattr(first, 'type', 'unknown')}, "
                f"stop_reason={getattr(response, 'stop_reason', 'unknown')})."
            )
        return _Response(text)


# ── Google Gemini backend ──────────────────────────────────────────────────────

class _GoogleCompletions:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def create(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 1024,
        **kwargs,
    ) -> _Response:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)

        # Extract system instruction and user turns
        system_instruction = None
        user_parts = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                user_parts.append(msg["content"])

        user_content = "\n\n".join(user_parts) if user_parts else ""

        json_mode = kwargs.get("json_mode", True)  # default True: all pipeline calls expect JSON
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction or None,
            response_mime_type="application/json" if json_mode else None,
            thinking_config=types.ThinkingConfig(thinking_budget=0),  # disable thinking tokens (matches TS pipeline)
        )

        import concurrent.futures as _cf
        def _call():
            return client.models.generate_content(
                model=model,
                contents=user_content,
                config=config,
            )
        with _cf.ThreadPoolExecutor(max_workers=1) as _pool:
            _fut = _pool.submit(_call)
            try:
                response = _fut.result(timeout=60)  # 60-second hard timeout per call
            except _cf.TimeoutError:
                raise TimeoutError(f"Gemini API timed out after 60s (model={model})")
        text = response.text
        if text is None:
            raise ValueError(
                f"Gemini returned None text — possible safety block or empty response "
                f"(model={model}, finish_reason={getattr(response, 'prompt_feedback', 'unknown')})"
            )
        return _Response(text)

    async def async_create(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 1024,
        **kwargs,
    ) -> _Response:
        """Async version using generate_content_async — enables asyncio.gather parallelism."""
        import asyncio
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)

        system_instruction = None
        user_parts = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                user_parts.append(msg["content"])
        user_content = "\n\n".join(user_parts) if user_parts else ""

        json_mode = kwargs.get("json_mode", True)
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction or None,
            response_mime_type="application/json" if json_mode else None,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model, contents=user_content, config=config
                ),
                timeout=60,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Gemini async timed out after 60s (model={model})")

        text = response.text
        if text is None:
            raise ValueError(f"Gemini returned None (model={model})")
        return _Response(text)


# ── DeepSeek backend ───────────────────────────────────────────────────────────
#
# Uses the DeepSeek API (api.deepseek.com) which is OpenAI-compatible.
# Key difference: the response message has a `reasoning_content` attribute
# containing the full chain-of-thought trace when using deepseek-reasoner.
#
# Supported models:
#   deepseek-reasoner          — DeepSeek-R1 (full, best quality)
#   deepseek-chat              — DeepSeek-V3 (fast, no trace)

class _DeepSeekMessage:
    """Extends _Message with an optional reasoning_content field."""
    def __init__(self, content: str, reasoning_content: str = ""):
        self.content = content
        self.reasoning_content = reasoning_content  # <think> trace

class _DeepSeekChoice:
    def __init__(self, content: str, reasoning_content: str = ""):
        self.message = _DeepSeekMessage(content, reasoning_content)

class _DeepSeekResponse:
    def __init__(self, content: str, reasoning_content: str = ""):
        self.choices = [_DeepSeekChoice(content, reasoning_content)]

class _DeepSeekCompletions:
    BASE_URL = "https://api.deepseek.com"

    def __init__(self, api_key: str):
        self._api_key = api_key

    def create(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 8192,
        **kwargs,
    ) -> _DeepSeekResponse:
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key, base_url=self.BASE_URL)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Framework Fix #20 (2026-06-15): explicit-raise on null content,
        # matching the Gemini backend's pattern. The old `or ""` silently
        # produced an empty response which downstream parse_llm_json then
        # raised on, losing the actual cause (rate limit, safety block,
        # max_tokens hit). Now the caller sees a clear ValueError with
        # diagnostic context so the pipeline-level error handler can
        # decide between retry, key-rotation, and heuristic fallback.
        msg = resp.choices[0].message
        content = msg.content
        if content is None or content == "":
            finish = getattr(resp.choices[0], "finish_reason", "unknown")
            raise ValueError(
                f"DeepSeek returned empty content "
                f"(model={model}, finish_reason={finish}). "
                f"Possible causes: rate limit, max_tokens hit, "
                f"safety block, or upstream API error."
            )
        reasoning_content = getattr(msg, "reasoning_content", "") or ""
        return _DeepSeekResponse(content, reasoning_content)

    async def async_create(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 8192,
        **kwargs,
    ) -> _DeepSeekResponse:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.create(model, messages, temperature, max_tokens, **kwargs),
        )


# ── OpenAI backend ─────────────────────────────────────────────────────────────

class _OpenAICompletions:
    # Framework Fix #21 (2026-06-15): 60s default timeout matching Gemini
    # and Anthropic. Without this we relied on the openai SDK's default
    # (10 minutes), which could hang a batch run on a stuck connection.
    DEFAULT_TIMEOUT_S = 60.0

    def __init__(self, api_key: str):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, timeout=self.DEFAULT_TIMEOUT_S)

    def create(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 1024,
        **kwargs,
    ) -> _Response:
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Same null-content protection as DeepSeek (Fix #20).
        content = response.choices[0].message.content
        if content is None or content == "":
            finish = getattr(response.choices[0], "finish_reason", "unknown")
            raise ValueError(
                f"OpenAI returned empty content "
                f"(model={model}, finish_reason={finish}). "
                f"Possible causes: rate limit, max_tokens hit, "
                f"content filter, or upstream API error."
            )
        return _Response(content)


# ── Unified Chat wrapper ───────────────────────────────────────────────────────

class _ChatAPI:
    def __init__(self, completions):
        self.completions = completions


# ── Public LLMClient ──────────────────────────────────────────────────────────

class LLMClient:
    """
    Multi-provider LLM client with OpenAI-compatible interface.

    Provider is selected automatically from the model name passed to
    `chat.completions.create()`. The api_key must match the provider
    of the model being called.

    Usage:
        client = LLMClient(api_key=anthropic_key)
        resp = client.chat.completions.create(
            model="claude-haiku-4-5-20251001", messages=[...])

        client = LLMClient(api_key=gemini_key)
        resp = client.chat.completions.create(
            model="gemini-2.0-flash", messages=[...])

        client = LLMClient(api_key=openai_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini", messages=[...])

        text = resp.choices[0].message.content  # same for all providers
    """

    def __init__(self, api_key: str, provider: str | None = None):
        self._api_key = api_key
        self._provider = provider  # None = auto-detect per call
        # Lazy-initialise per-provider completions backends
        self._backends: dict[str, object] = {}
        # Expose a default chat API (provider resolved at call time)
        self.chat = _DeferredChatAPI(self)

    def _get_completions(self, provider: str):
        if provider not in self._backends:
            if provider == "anthropic":
                self._backends[provider] = _AnthropicCompletions(self._api_key)
            elif provider == "google":
                self._backends[provider] = _GoogleCompletions(self._api_key)
            elif provider == "openai":
                self._backends[provider] = _OpenAICompletions(self._api_key)
            elif provider == "deepseek":
                self._backends[provider] = _DeepSeekCompletions(self._api_key)
            else:
                raise ValueError(f"Unknown provider: {provider!r}")
        return self._backends[provider]


class _DeferredCompletionsAPI:
    """Completions dispatcher — routes each call to the right backend.

    Framework Fix #22 (2026-06-15): the create() method is the single
    point all LLM calls flow through, so we instrument it here once instead
    of per-backend. Every call writes a structured log line when
    CONCEPTGRADE_LLM_LOG is set, with outcome + latency + error details
    preserved across any downstream try/except masking.
    """

    def __init__(self, client: LLMClient):
        self._client = client

    def create(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 1024,
        **kwargs,
    ) -> _Response:
        provider = self._client._provider or detect_provider(model)
        backend = self._client._get_completions(provider)
        log_enabled = _LLM_LOG.enabled
        t0 = time.time() if log_enabled else 0.0
        try:
            resp = backend.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except Exception as e:
            if log_enabled:
                _LLM_LOG.write({
                    "ts": time.time(),
                    "provider": provider,
                    "model": model,
                    "prompt_chars": _prompt_chars(messages),
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                    "outcome": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:500],
                })
            raise
        if log_enabled:
            try:
                resp_chars = len(resp.choices[0].message.content or "")
            except Exception:
                resp_chars = -1
            _LLM_LOG.write({
                "ts": time.time(),
                "provider": provider,
                "model": model,
                "prompt_chars": _prompt_chars(messages),
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "outcome": "success",
                "response_chars": resp_chars,
            })
        return resp


class _DeferredChatAPI:
    def __init__(self, client: LLMClient):
        self.completions = _DeferredCompletionsAPI(client)
