# ABOUTME: Unit tests for the cost-engineering layer: disk decision cache and per-run call budget.
# ABOUTME: Proves cache hits skip the inner client, persist across instances, and the budget caps.
from __future__ import annotations

from pathlib import Path

import pytest

from outreach_agent.domain.enums import ModelTier
from outreach_agent.llm.cache import (
    BudgetedLLMClient,
    BudgetExceeded,
    CallBudget,
    DiskCachedLLMClient,
)


class CountingLLM:
    """LLMClient double that counts complete() calls and returns a deterministic string."""

    def __init__(self, text: str = "answer") -> None:
        self._text = text
        self.calls = 0

    def complete(self, *, tier: ModelTier, system: str, user: str, max_tokens: int = 1024) -> str:
        self.calls += 1
        return self._text


def test_repeated_identical_call_hits_cache(tmp_path: Path) -> None:
    inner = CountingLLM()
    cache = DiskCachedLLMClient(inner, tmp_path / "cache.json")

    first = cache.complete(tier=ModelTier.HAIKU, system="s", user="u")
    second = cache.complete(tier=ModelTier.HAIKU, system="s", user="u")

    assert first == second == "answer"
    assert inner.calls == 1
    assert cache.hits == 1
    assert cache.misses == 1


def test_distinct_inputs_are_distinct_keys(tmp_path: Path) -> None:
    inner = CountingLLM()
    cache = DiskCachedLLMClient(inner, tmp_path / "cache.json")

    cache.complete(tier=ModelTier.HAIKU, system="s", user="u")
    cache.complete(tier=ModelTier.SONNET, system="s", user="u")  # different tier
    cache.complete(tier=ModelTier.HAIKU, system="other", user="u")  # different system
    cache.complete(tier=ModelTier.HAIKU, system="s", user="other")  # different user

    assert inner.calls == 4
    assert cache.misses == 4
    assert cache.hits == 0


def test_cache_persists_across_instances(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    inner_a = CountingLLM("persisted")
    DiskCachedLLMClient(inner_a, cache_path).complete(tier=ModelTier.OPUS, system="s", user="u")
    assert inner_a.calls == 1

    inner_b = CountingLLM("fresh")
    cache_b = DiskCachedLLMClient(inner_b, cache_path)
    result = cache_b.complete(tier=ModelTier.OPUS, system="s", user="u")

    assert result == "persisted"
    assert inner_b.calls == 0
    assert cache_b.hits == 1


def test_missing_cache_file_is_tolerated(tmp_path: Path) -> None:
    inner = CountingLLM()
    cache = DiskCachedLLMClient(inner, tmp_path / "does-not-exist.json")
    assert cache.complete(tier=ModelTier.HAIKU, system="s", user="u") == "answer"


def test_corrupt_cache_file_is_treated_as_empty(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{ not json", encoding="utf-8")

    inner = CountingLLM()
    cache = DiskCachedLLMClient(inner, cache_path)  # must not crash on construction

    result = cache.complete(tier=ModelTier.HAIKU, system="s", user="u")
    assert result == "answer"
    assert inner.calls == 1
    assert cache.misses == 1
    assert cache.hits == 0


def test_budget_allows_up_to_max_then_raises() -> None:
    budget = CallBudget(max_calls=2)
    budget.charge()
    budget.charge()
    assert budget.spent == 2
    with pytest.raises(BudgetExceeded):
        budget.charge()
    assert budget.spent == 2


def test_budgeted_client_caps_calls() -> None:
    inner = CountingLLM()
    budget = CallBudget(max_calls=1)
    client = BudgetedLLMClient(inner, budget)

    client.complete(tier=ModelTier.HAIKU, system="s", user="u")
    assert budget.spent == 1
    assert inner.calls == 1

    with pytest.raises(BudgetExceeded):
        client.complete(tier=ModelTier.HAIKU, system="s", user="u2")
    # The breach is raised before the inner client is ever invoked.
    assert inner.calls == 1
    assert budget.spent == 1
