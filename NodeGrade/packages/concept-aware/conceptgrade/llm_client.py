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
import re
import os

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


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
    """Return 'anthropic', 'google', or 'openai' based on model name prefix."""
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith("gemini") or m.startswith("models/gemini"):
        return "google"
    if m.startswith("gpt") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4"):
        return "openai"
    # Fallback: check API key prefix to guess provider
    return "anthropic"


# ── Anthropic backend ──────────────────────────────────────────────────────────

class _AnthropicCompletions:
    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

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
        return _Response(response.content[0].text)


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


# ── OpenAI backend ─────────────────────────────────────────────────────────────

class _OpenAICompletions:
    def __init__(self, api_key: str):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)

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
        return _Response(response.choices[0].message.content)


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
            else:
                raise ValueError(f"Unknown provider: {provider!r}")
        return self._backends[provider]


class _DeferredCompletionsAPI:
    """Completions dispatcher — routes each call to the right backend."""

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
        return backend.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


class _DeferredChatAPI:
    def __init__(self, client: LLMClient):
        self.completions = _DeferredCompletionsAPI(client)
