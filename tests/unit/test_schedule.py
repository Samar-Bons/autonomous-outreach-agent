# ABOUTME: Unit tests for the warmup wave planner: caps, weekend skips, offsets, and spacing.
# ABOUTME: Time is frozen via FixedClock anchored on a known Monday so every placement is exact.
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from outreach_agent.config import DEFAULT_WARMUP_CAPS, WAVE_OFFSET_DAYS
from outreach_agent.domain import Draft, ScheduledSend
from outreach_agent.domain.enums import Segment, Wave
from outreach_agent.schedule import FixedClock, WarmupWavePlanner

# A verified Monday: date(2026, 4, 20).weekday() == 0.
_START = date(2026, 4, 20)
_CAMPAIGN = "test-campaign"


def _clock() -> FixedClock:
    return FixedClock(today_value=_START, now_value=datetime(2026, 4, 20, 9, 0, tzinfo=UTC))


def _planner() -> WarmupWavePlanner:
    return WarmupWavePlanner(_clock(), campaign=_CAMPAIGN)


def _draft(idx: int, wave: Wave = Wave.INITIAL, email: str | None = None) -> Draft:
    return Draft(
        prospect_id=f"p{idx}",
        email=email or f"shop{idx}@example.com",
        wave=wave,
        segment=Segment.HD_DIESEL,
        angle_key="uptime",
        subject="s",
        body="b",
    )


def test_start_date_is_a_monday() -> None:
    assert _START.weekday() == 0


def test_caps_enforced_overflow_rolls_to_next_weekday() -> None:
    day0_cap = DEFAULT_WARMUP_CAPS[0]
    drafts = [_draft(i) for i in range(day0_cap + 5)]
    sends = _planner().plan(drafts, {})

    on_day0 = [s for s in sends if s.send_at.date() == _START]
    assert len(on_day0) == day0_cap

    overflow = [s for s in sends if s.send_at.date() != _START]
    assert len(overflow) == 5
    next_weekday = _START + timedelta(days=1)
    assert all(s.send_at.date() == next_weekday for s in overflow)
    assert next_weekday.weekday() < 5


def test_no_send_lands_on_a_weekend() -> None:
    # Enough volume to overflow several days past the first weekend.
    total = DEFAULT_WARMUP_CAPS[0] + DEFAULT_WARMUP_CAPS[1] + DEFAULT_WARMUP_CAPS[2] + 10
    drafts = [_draft(i) for i in range(total)]
    sends = _planner().plan(drafts, {})
    assert all(s.send_at.weekday() < 5 for s in sends)


def test_wave_offsets_respected() -> None:
    sends = _planner().plan([_draft(0, Wave.INITIAL), _draft(1, Wave.BREAKUP)], {})
    initial, breakup = sends

    assert initial.send_at.date() >= _START + timedelta(days=WAVE_OFFSET_DAYS[Wave.INITIAL.value])
    assert breakup.send_at.date() >= _START + timedelta(days=WAVE_OFFSET_DAYS[Wave.BREAKUP.value])


def test_idem_key_format() -> None:
    email = "owner@shop.com"
    sends = _planner().plan([_draft(0, Wave.PIVOT, email=email)], {})
    assert sends[0].idem_key == f"{_CAMPAIGN}/{email}-w{Wave.PIVOT.value}"
    assert sends[0].idem_key == ScheduledSend.make_idem_key(_CAMPAIGN, email, Wave.PIVOT)


def test_existing_counts_respected() -> None:
    day0_cap = DEFAULT_WARMUP_CAPS[0]
    # Seed day 0 to one slot below its cap: only one new send may land there.
    existing = {_START: day0_cap - 1}
    drafts = [_draft(i) for i in range(3)]
    sends = _planner().plan(drafts, existing)

    on_day0 = [s for s in sends if s.send_at.date() == _START]
    assert len(on_day0) == 1
    assert len([s for s in sends if s.send_at.date() != _START]) == 2


def test_same_day_sends_are_spaced_30s_at_11_utc() -> None:
    sends = _planner().plan([_draft(0), _draft(1)], {})
    first, second = sends

    assert first.send_at == datetime(2026, 4, 20, 11, 0, tzinfo=UTC)
    assert second.send_at == datetime(2026, 4, 20, 11, 0, 30, tzinfo=UTC)
    assert (second.send_at - first.send_at).total_seconds() == 30


def test_existing_counts_input_dict_not_mutated() -> None:
    existing: dict[date, int] = {_START: 1}
    _planner().plan([_draft(0)], existing)
    assert existing == {_START: 1}


def test_returns_results_in_input_order() -> None:
    drafts = [_draft(i) for i in range(5)]
    sends = _planner().plan(drafts, {})
    assert [s.prospect_id for s in sends] == [d.prospect_id for d in drafts]
