# ABOUTME: Cost-engineering decorators around the LLMClient seam: a disk-backed decision
# ABOUTME: cache and a hard per-run call budget, making LLM-in-the-loop affordable at scale.
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from ..domain.enums import ModelTier
from ..protocols import LLMClient


def _key(tier: ModelTier, system: str, user: str) -> str:
    """Stable content-addressed key for a decision: identical inputs collapse to one entry."""
    digest = hashlib.sha256(f"{tier.value}|{system}|{user}".encode())
    return digest.hexdigest()


class DiskCachedLLMClient:
    """LLMClient wrapper that memoizes decisions to a JSON file on disk.

    WHY: outreach re-runs over a slowly-changing population. Once a prospect's
    decision is cached, re-running the pipeline is near-free — only genuinely
    fresh inputs ever reach the inner client and spend tokens. The cache is
    content-addressed (sha256 of tier|system|user) so any change to the prompt
    or model tier is correctly treated as a new decision.
    """

    def __init__(self, inner: LLMClient, cache_path: Path) -> None:
        self._inner = inner
        self._cache_path = cache_path
        self._cache = self._load(cache_path)
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _load(cache_path: Path) -> dict[str, str]:
        """Read the cache file once at construction; a missing file is an empty cache."""
        try:
            raw = cache_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        return json.loads(raw)

    def _persist(self) -> None:
        """Write the whole cache atomically: temp file then os.replace, so no half-written JSON."""
        tmp_path = self._cache_path.with_suffix(self._cache_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(self._cache), encoding="utf-8")
        os.replace(tmp_path, self._cache_path)

    def complete(
        self,
        *,
        tier: ModelTier,
        system: str,
        user: str,
        max_tokens: int = 1024,
    ) -> str:
        key = _key(tier, system, user)
        cached = self._cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        result = self._inner.complete(tier=tier, system=system, user=user, max_tokens=max_tokens)
        self._cache[key] = result
        self._persist()
        return result


class BudgetExceeded(RuntimeError):
    """Raised when a run tries to make more model calls than its budget allows."""


class CallBudget:
    """A hard ceiling on model calls for a single run.

    WHY: a cache makes the common case cheap, but a buggy retry loop can still
    spin forever on cache misses. The budget is the circuit breaker that caps
    total spend per run regardless of caching.
    """

    def __init__(self, max_calls: int) -> None:
        self._max_calls = max_calls
        self._spent = 0

    @property
    def spent(self) -> int:
        return self._spent

    def charge(self) -> None:
        """Account for one call, raising BudgetExceeded if it would breach the ceiling."""
        if self._spent + 1 > self._max_calls:
            raise BudgetExceeded(f"call budget of {self._max_calls} exceeded")
        self._spent += 1


class BudgetedLLMClient:
    """LLMClient wrapper that charges a CallBudget before every delegated call.

    WHY: this is the hard ceiling that stops a runaway loop from spending
    unboundedly — the budget is charged first, so a breach raises before the
    inner client is ever invoked.
    """

    def __init__(self, inner: LLMClient, budget: CallBudget) -> None:
        self._inner = inner
        self._budget = budget

    def complete(
        self,
        *,
        tier: ModelTier,
        system: str,
        user: str,
        max_tokens: int = 1024,
    ) -> str:
        self._budget.charge()
        return self._inner.complete(tier=tier, system=system, user=user, max_tokens=max_tokens)
