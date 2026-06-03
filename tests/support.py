# ABOUTME: Importable test doubles for the LLMClient seam, shared across test modules.
# ABOUTME: Both satisfy the LLMClient Protocol so they drop into any stage under test.
from __future__ import annotations

from outreach_agent.domain.enums import ModelTier


class ConstantLLM:
    """Returns the same text for every call. For testing parse/retry behavior."""

    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, *, tier: ModelTier, system: str, user: str, max_tokens: int = 1024) -> str:
        return self._text


class QueueLLM:
    """Returns queued responses in order, raising when exhausted. Counts calls."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def complete(self, *, tier: ModelTier, system: str, user: str, max_tokens: int = 1024) -> str:
        self.calls += 1
        if not self._responses:
            raise AssertionError("QueueLLM exhausted")
        return self._responses.pop(0)
