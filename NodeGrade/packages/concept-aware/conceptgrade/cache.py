"""
Simple file-based response cache for the ConceptGrade pipeline.

Purpose (research): Avoid re-running identical LLM calls when the same
question/answer pair appears more than once (e.g. repeated experiments,
re-runs after a crash, batch evaluation with duplicate answers).

Cache key: SHA-256 of "question|||answer|||layer_tag"
Storage:   Single JSON file — human-readable, easy to inspect / delete.
"""

import hashlib
import json
import os


class ResponseCache:
    """
    Lightweight persistent cache backed by a single JSON file.

    Usage::
        cache = ResponseCache()          # defaults to ~/.conceptgrade_cache.json
        key = cache.key("extract", question, answer)
        if key in cache:
            return cache.get(key)
        result = expensive_llm_call(...)
        cache.set(key, result)
    """

    def __init__(self, cache_file: str = "~/.conceptgrade_cache.json"):
        self.cache_file = os.path.expanduser(cache_file)
        self._data: dict = self._load()

    # ── persistence ────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError as e:
            print(f"[Cache] Warning: could not write cache file: {e}")

    # ── public API ──────────────────────────────────────────────────────────

    def key(self, layer: str, *parts: str) -> str:
        """Build a stable cache key from layer name + arbitrary string parts."""
        combined = f"{layer}|||" + "|||".join(parts)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self._save()

    def clear(self) -> None:
        """Remove all cached entries (useful between experiments)."""
        self._data = {}
        self._save()

    @property
    def size(self) -> int:
        return len(self._data)

    def stats(self) -> dict:
        return {
            "entries": self.size,
            "file": self.cache_file,
            "exists": os.path.exists(self.cache_file),
        }
