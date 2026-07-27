"""Unit tests for explicit false-belief detection behavior."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from misconception_detection.detector import (  # noqa: E402
    FalseBeliefDetector,
    Severity,
)


def test_false_belief_detector_parses_valid_json(monkeypatch):
    detector = FalseBeliefDetector(api_key="test", model="test-model")

    def fake_call(_system: str, _user: str, max_tokens: int = 600):  # noqa: ARG001
        return """{
          "false_beliefs": [
            {
              "false_belief_id": "FB-1",
              "severity": "critical",
              "student_claim": "A stack is FIFO",
              "correct_understanding": "A stack is LIFO",
              "explanation": "FIFO describes queues, not stacks",
              "confidence": 0.95
            }
          ],
          "summary": "One explicit false claim found."
        }"""

    monkeypatch.setattr(detector, "_call_llm", fake_call)
    out = detector.detect("What is a stack?", "A stack is FIFO.")

    assert len(out) == 1
    assert out[0].false_belief_id == "FB-1"
    assert out[0].severity == Severity.CRITICAL
    assert out[0].student_claim == "A stack is FIFO"


def test_false_belief_detector_returns_empty_on_non_rate_errors(monkeypatch):
    detector = FalseBeliefDetector(api_key="test", model="test-model")

    def fake_call(_system: str, _user: str, max_tokens: int = 600):  # noqa: ARG001
        raise RuntimeError("500 backend failed")

    monkeypatch.setattr(detector, "_call_llm", fake_call)
    out = detector.detect("Q", "A")
    assert out == []


def test_false_belief_detector_raises_on_rate_limit(monkeypatch):
    detector = FalseBeliefDetector(api_key="test", model="test-model")

    def fake_call(_system: str, _user: str, max_tokens: int = 600):  # noqa: ARG001
        raise RuntimeError("429 rate_limit exceeded")

    monkeypatch.setattr(detector, "_call_llm", fake_call)
    try:
        detector.detect("Q", "A")
        assert False, "Expected rate-limit errors to propagate"
    except RuntimeError as exc:
        assert "rate_limit" in str(exc).lower() or "429" in str(exc)
