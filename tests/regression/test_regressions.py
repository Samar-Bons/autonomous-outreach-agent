# ABOUTME: Regression tests for the five production lessons in LESSONS.md, one test each.
# ABOUTME: These lock in safety guarantees that real incidents proved we cannot lose.
from __future__ import annotations

from datetime import UTC, date, datetime

from outreach_agent.classify.classifier import LLMClassifier
from outreach_agent.domain import Draft, Prospect, Reply
from outreach_agent.domain.enums import Archetype, Segment, Wave
from outreach_agent.safety import RegexOptOutDetector, default_gate
from outreach_agent.schedule import FixedClock, WarmupWavePlanner
from tests.support import ConstantLLM

_MONDAY = date(2026, 4, 20)


# Lesson 1: opt-out detection is deterministic and conservative.
def test_optout_is_deterministic_and_conservative() -> None:
    detector = RegexOptOutDetector()
    assert detector.is_opt_out(_reply("stop")) is True
    assert detector.is_opt_out(_reply("please unsubscribe me")) is True
    # The adversarial case that must never be read as an opt-out.
    assert detector.is_opt_out(_reply("feel free to stop by the shop anytime")) is False


# Lesson 2: the safety gate fails closed on any BLOCK finding.
def test_gate_fails_closed_on_any_block() -> None:
    leaky = Draft(
        prospect_id="p1",
        email="owner@joesauto.com",
        wave=Wave.INITIAL,
        segment=Segment.PASSENGER_LUBE,
        angle_key="next_day_delivery",
        subject="quick question",
        body="Hi {shop_name}, we deliver next day.",  # leaked template variable
    )
    assert default_gate().validate(leaky).passed is False


# Lesson 3: the scheduler never produces a silent zero past the ramp table.
def test_scheduler_has_no_silent_zero_past_the_ramp() -> None:
    clock = FixedClock(_MONDAY, datetime(2026, 4, 20, 9, 0, tzinfo=UTC))
    planner = WarmupWavePlanner(clock, campaign="demo")
    # A breakup wave lands ~10 weekdays out, past the warmup ramp table.
    draft = Draft(
        prospect_id="p1",
        email="a@b.com",
        wave=Wave.BREAKUP,
        segment=Segment.PASSENGER_LUBE,
        angle_key="next_day_delivery",
        subject="last note",
        body="closing the loop",
    )
    scheduled = planner.plan([draft], {})
    assert len(scheduled) == 1  # steady-state cap applies; not silently dropped
    assert scheduled[0].send_at.weekday() < 5


# Lesson 4: a model failure becomes NEEDS_RETRY, never a fabricated label.
def test_model_failure_never_becomes_a_label() -> None:
    results = LLMClassifier(ConstantLLM("garbage not json")).classify([_prospect_like()])
    assert len(results) == 1
    assert results[0].archetype is Archetype.NEEDS_RETRY
    assert results[0].is_quarantined is True


# Lesson 5: idempotency keys are stable across runs.
def test_idempotency_keys_are_stable_across_runs() -> None:
    clock = FixedClock(_MONDAY, datetime(2026, 4, 20, 9, 0, tzinfo=UTC))
    draft = Draft(
        prospect_id="p1",
        email="a@b.com",
        wave=Wave.INITIAL,
        segment=Segment.PASSENGER_LUBE,
        angle_key="next_day_delivery",
        subject="hi",
        body="hello",
    )
    first = WarmupWavePlanner(clock, campaign="demo").plan([draft], {})
    second = WarmupWavePlanner(clock, campaign="demo").plan([draft], {})
    assert first[0].idem_key == second[0].idem_key


def _reply(body: str) -> Reply:
    return Reply(thread_id="t", from_email="x@y.com", subject="re", body=body)


def _prospect_like() -> Prospect:
    return Prospect(id="p1", name="Joe's Auto", city="Dallas", sic="Auto Repair")
