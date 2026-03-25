"""
API Key Rotator.

Rotates across multiple API keys on rate-limit errors (429).
Each key has its own rate budget, so rotation effectively
multiplies available throughput across independent accounts.

Usage
-----
    from conceptgrade.key_rotator import KeyRotator, API_KEYS
    rotator = KeyRotator(API_KEYS)
    response = rotator.call(client_fn, *args, **kwargs)

Environment variables (any provider)
--------------------------------------
    ANTHROPIC_API_KEY        — single Anthropic key
    ANTHROPIC_API_KEY_1, _2  — multiple Anthropic keys for rotation
    GEMINI_API_KEY           — single Google Gemini key
    GEMINI_API_KEY_1, _2     — multiple Gemini keys for rotation
    GOOGLE_API_KEY           — alias for GEMINI_API_KEY
    OPENAI_API_KEY           — single OpenAI key
    OPENAI_API_KEY_1, _2     — multiple OpenAI keys for rotation
"""

from __future__ import annotations

import os
import time
import threading


def _load_indexed_keys(prefix: str) -> list[str]:
    """Load PREFIX_1, PREFIX_2, ... until gap, then try PREFIX."""
    keys = []
    i = 1
    while True:
        key = os.environ.get(f"{prefix}_{i}")
        if not key:
            break
        keys.append(key)
        i += 1
    if not keys:
        single = os.environ.get(prefix)
        if single:
            keys.append(single)
    return keys


def _load_keys_from_env() -> list[str]:
    """Load API keys for whichever provider(s) are configured in env."""
    keys = []
    # Anthropic
    keys.extend(_load_indexed_keys("ANTHROPIC_API_KEY"))
    # Google Gemini (GEMINI_API_KEY or GOOGLE_API_KEY)
    keys.extend(_load_indexed_keys("GEMINI_API_KEY"))
    if not keys:
        keys.extend(_load_indexed_keys("GOOGLE_API_KEY"))
    # OpenAI
    keys.extend(_load_indexed_keys("OPENAI_API_KEY"))
    return keys


def get_api_key_for_provider(provider: str) -> str | None:
    """
    Return the first available key for a specific provider.

    provider: 'anthropic', 'google', or 'openai'
    """
    if provider == "anthropic":
        keys = _load_indexed_keys("ANTHROPIC_API_KEY")
    elif provider == "google":
        keys = _load_indexed_keys("GEMINI_API_KEY") or _load_indexed_keys("GOOGLE_API_KEY")
    elif provider == "openai":
        keys = _load_indexed_keys("OPENAI_API_KEY")
    else:
        keys = []
    return keys[0] if keys else None


API_KEYS: list[str] = _load_keys_from_env()

# Backwards-compatible alias
GROQ_API_KEYS = API_KEYS


class KeyRotator:
    """
    Thread-safe API key rotator with automatic failover on 429 errors.

    On a rate-limit error, advances to the next key and retries.
    If all keys are exhausted, waits `wait_seconds` and starts over.
    """

    def __init__(
        self,
        keys: list[str] = None,
        wait_seconds: float = 10.0,
    ):
        self._keys = keys or API_KEYS
        if not self._keys:
            raise EnvironmentError(
                "No API keys found. Set ANTHROPIC_API_KEY or "
                "ANTHROPIC_API_KEY_1, ANTHROPIC_API_KEY_2, ..."
            )
        self._idx  = 0
        self._lock = threading.Lock()
        self._wait = wait_seconds
        self._exhausted_at: dict[int, float] = {}

    @property
    def current_key(self) -> str:
        return self._keys[self._idx]

    def next_key(self) -> str:
        """Advance to next key (thread-safe)."""
        with self._lock:
            self._exhausted_at[self._idx] = time.time()
            self._idx = (self._idx + 1) % len(self._keys)
        return self._keys[self._idx]

    def call_with_retry(self, fn, *args, max_retries: int = None, **kwargs):
        """
        Call fn(*args, **kwargs) with automatic key rotation on 429.

        fn should be a callable that accepts `api_key` as its first arg,
        or the key should already be baked into a closure.
        """
        if max_retries is None:
            max_retries = len(self._keys) + 1

        last_error = None
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit" in err_str.lower():
                    old = self._idx
                    self.next_key()
                    print(f"    [KeyRotator] 429 on key {old+1} → switching to key {self._idx+1}")
                    last_error = e
                    time.sleep(1.0)
                else:
                    raise
        raise last_error or RuntimeError("All keys exhausted")


# Global singleton for shared use across pipeline components
_rotator: KeyRotator | None = None


def get_rotator() -> KeyRotator:
    global _rotator
    if _rotator is None:
        _rotator = KeyRotator()
    return _rotator


def current_api_key() -> str:
    """Get the current best API key from the global rotator."""
    return get_rotator().current_key
