# ABOUTME: Shared pytest fixtures: a prospect factory and programmable LLM test doubles.
# ABOUTME: The doubles satisfy the LLMClient Protocol so they drop into any stage under test.
from __future__ import annotations

from collections.abc import Callable

import pytest

from outreach_agent.domain import Prospect
from outreach_agent.protocols import LLMClient

from .support import ConstantLLM, QueueLLM


@pytest.fixture
def make_prospect() -> Callable[..., Prospect]:
    def _make(
        name: str = "Generic Auto Repair",
        *,
        id: str = "p1",
        city: str = "Dallas",
        sic: str | None = "Auto Repair",
        employees: int | None = 5,
        website: str | None = None,
    ) -> Prospect:
        return Prospect(id=id, name=name, city=city, sic=sic, employees=employees, website=website)

    return _make


@pytest.fixture
def constant_llm() -> Callable[[str], LLMClient]:
    return lambda text: ConstantLLM(text)


@pytest.fixture
def queue_llm() -> Callable[[list[str]], QueueLLM]:
    return lambda responses: QueueLLM(responses)
