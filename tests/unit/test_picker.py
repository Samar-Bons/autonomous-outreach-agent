# ABOUTME: Unit tests for ConstrainedAnglePicker: quarantine, deterministic single, model multi.
# ABOUTME: Proves a single-candidate pick makes no model call and failures fall back safely.
from __future__ import annotations

from collections.abc import Callable

from outreach_agent.classify.picker import ConstrainedAnglePicker
from outreach_agent.domain import Classification, Prospect
from outreach_agent.domain.enums import Archetype, Segment
from outreach_agent.llm import RuleBasedStubLLM
from outreach_agent.protocols import LLMClient
from tests.support import QueueLLM


def _cls(segment: Segment, archetype: Archetype) -> Classification:
    return Classification(prospect_id="p1", segment=segment, archetype=archetype, confidence=0.9)


def test_quarantined_prospect_gets_no_angle(make_prospect: Callable[..., Prospect]) -> None:
    picker = ConstrainedAnglePicker(QueueLLM([]))  # would raise if called
    result = picker.pick(make_prospect(), _cls(Segment.PASSENGER_LUBE, Archetype.MOBILE_MECHANIC))
    assert result is None


def test_single_candidate_is_deterministic_no_model_call(
    make_prospect: Callable[..., Prospect],
) -> None:
    # EURO_SPECIALIST in DEALER_FLEET intersects to exactly one angle.
    picker = ConstrainedAnglePicker(QueueLLM([]))  # raises if the model is called
    result = picker.pick(make_prospect(), _cls(Segment.DEALER_FLEET, Archetype.EURO_SPECIALIST))
    assert result is not None
    assert result.angle_key == "oem_spec_match"
    assert result.reason == "single candidate"


def test_multi_candidate_uses_model(make_prospect: Callable[..., Prospect]) -> None:
    picker = ConstrainedAnglePicker(RuleBasedStubLLM())
    result = picker.pick(make_prospect(), _cls(Segment.HD_DIESEL, Archetype.HD_DIESEL))
    assert result is not None
    assert result.angle_key in result.candidates
    assert result.reason == "model pick"
    assert len(result.candidates) > 1


def test_multi_candidate_falls_back_on_failure(
    make_prospect: Callable[..., Prospect],
    constant_llm: Callable[[str], LLMClient],
) -> None:
    picker = ConstrainedAnglePicker(constant_llm("garbage"))
    result = picker.pick(make_prospect(), _cls(Segment.HD_DIESEL, Archetype.HD_DIESEL))
    assert result is not None
    assert result.angle_key == result.candidates[0]
    assert result.reason.startswith("fallback")
