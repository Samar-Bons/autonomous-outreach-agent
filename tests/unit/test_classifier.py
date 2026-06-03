# ABOUTME: Unit tests for LLMClassifier: order, abstention, and batch-halving on failure.
# ABOUTME: Proves the classifier never fabricates a label and isolates failures to NEEDS_RETRY.
from __future__ import annotations

import json
from collections.abc import Callable

from outreach_agent.classify.classifier import LLMClassifier
from outreach_agent.domain import Prospect
from outreach_agent.domain.enums import Archetype, Segment
from outreach_agent.llm import RuleBasedStubLLM
from outreach_agent.protocols import LLMClient
from tests.support import QueueLLM


def _valid_single(segment: str = "hd_diesel", archetype: str = "hd_diesel") -> str:
    return json.dumps(
        [{"idx": 0, "segment": segment, "archetype": archetype, "confidence": 0.9, "reason": "r"}]
    )


def test_stub_classifies_in_scope_and_out_of_scope(
    make_prospect: Callable[..., Prospect],
) -> None:
    prospects = [
        make_prospect("Big Rig Diesel Service", id="a"),
        make_prospect("Sunny Nail Salon", id="b", sic="Personal Care"),
    ]
    results = LLMClassifier(RuleBasedStubLLM()).classify(prospects)
    assert [r.prospect_id for r in results] == ["a", "b"]
    assert results[0].segment is Segment.HD_DIESEL
    assert results[0].is_quarantined is False
    assert results[1].is_quarantined is True


def test_preserves_order_and_count(make_prospect: Callable[..., Prospect]) -> None:
    prospects = [make_prospect(f"Shop {i}", id=str(i)) for i in range(25)]
    results = LLMClassifier(RuleBasedStubLLM(), batch_size=10).classify(prospects)
    assert [r.prospect_id for r in results] == [str(i) for i in range(25)]


def test_single_malformed_response_yields_needs_retry(
    make_prospect: Callable[..., Prospect],
    constant_llm: Callable[[str], LLMClient],
) -> None:
    results = LLMClassifier(constant_llm("garbage")).classify([make_prospect(id="x")])
    assert len(results) == 1
    assert results[0].archetype is Archetype.NEEDS_RETRY
    assert results[0].confidence == 0.0


def test_batch_halving_recovers_after_failure(
    make_prospect: Callable[..., Prospect],
    queue_llm: Callable[[list[str]], QueueLLM],
) -> None:
    # Full batch of 2 fails to parse, then each singleton succeeds.
    llm = queue_llm(["garbage", _valid_single(), _valid_single()])
    prospects = [make_prospect(id="a"), make_prospect(id="b")]
    results = LLMClassifier(llm, batch_size=10).classify(prospects)
    assert llm.calls == 3
    assert all(r.archetype is Archetype.HD_DIESEL for r in results)


def test_empty_input_returns_empty() -> None:
    assert LLMClassifier(RuleBasedStubLLM()).classify([]) == []
