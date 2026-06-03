# ABOUTME: Unit tests for the ops layer: heartbeat states, bounce canary, and the daily report.
# ABOUTME: Time is frozen via FixedClock so every boundary and window decision is exact.
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from outreach_agent.domain import ScheduledSend
from outreach_agent.domain.enums import SendStatus, Wave
from outreach_agent.ops import (
    BounceCanary,
    DailyReport,
    HeartbeatMonitor,
    HeartbeatState,
    StatusTier,
    tier_for_bounce_rate,
)
from outreach_agent.schedule import FixedClock

# A fixed instant for all clock-dependent assertions.
_NOW = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
_TODAY = date(2026, 4, 20)


def _clock(now: datetime = _NOW) -> FixedClock:
    return FixedClock(today_value=now.date(), now_value=now)


# --- Heartbeat -------------------------------------------------------------


def test_heartbeat_never_ran_when_no_timestamp() -> None:
    monitor = HeartbeatMonitor(_clock(), max_silence_minutes=30)
    status = monitor.check(None)
    assert status.state is HeartbeatState.NEVER_RAN
    assert status.last_run_at is None
    assert status.silence_minutes is None
    assert not status.healthy
    assert "never started" in status.message


def test_heartbeat_ok_when_recent() -> None:
    monitor = HeartbeatMonitor(_clock(), max_silence_minutes=30)
    last_run = _NOW - timedelta(minutes=10)
    status = monitor.check(last_run)
    assert status.state is HeartbeatState.OK
    assert status.healthy
    assert status.silence_minutes == 10.0


def test_heartbeat_ok_exactly_at_boundary() -> None:
    # Silence equal to the budget is still OK; only strictly-greater is stale.
    monitor = HeartbeatMonitor(_clock(), max_silence_minutes=30)
    status = monitor.check(_NOW - timedelta(minutes=30))
    assert status.state is HeartbeatState.OK
    assert status.silence_minutes == 30.0


def test_heartbeat_stale_just_past_boundary() -> None:
    monitor = HeartbeatMonitor(_clock(), max_silence_minutes=30)
    status = monitor.check(_NOW - timedelta(minutes=30, seconds=1))
    assert status.state is HeartbeatState.STALE
    assert not status.healthy
    assert "Stale" in status.message


def test_heartbeat_rejects_nonpositive_budget() -> None:
    import pytest

    with pytest.raises(ValueError, match="must be positive"):
        HeartbeatMonitor(_clock(), max_silence_minutes=0)


# --- Bounce canary ---------------------------------------------------------


def test_canary_does_not_trip_below_absolute_floor() -> None:
    # 1 bounce out of 2 sends is a 50% rate, but below the floor of 3.
    canary = BounceCanary(absolute_floor=3, rate_threshold=0.05)
    verdict = canary.evaluate(sent=2, bounced=1)
    assert not verdict.tripped
    assert verdict.bounce_rate == 0.5
    assert "Below floor" in verdict.reason


def test_canary_does_not_trip_above_floor_but_within_rate() -> None:
    # 5 bounces clears the floor, but 5/500 = 1% is under the 5% threshold.
    canary = BounceCanary(absolute_floor=3, rate_threshold=0.05)
    verdict = canary.evaluate(sent=500, bounced=5)
    assert not verdict.tripped
    assert verdict.bounce_rate == 0.01
    assert "Within tolerance" in verdict.reason


def test_canary_trips_above_floor_and_rate() -> None:
    # 10 bounces clears the floor of 3, and 10/100 = 10% exceeds 5%.
    canary = BounceCanary(absolute_floor=3, rate_threshold=0.05)
    verdict = canary.evaluate(sent=100, bounced=10)
    assert verdict.tripped
    assert verdict.bounce_rate == 0.1
    assert "Tripped" in verdict.reason


def test_canary_does_not_trip_when_rate_equals_threshold() -> None:
    # Exactly at the threshold is tolerated; only strictly-greater trips.
    canary = BounceCanary(absolute_floor=3, rate_threshold=0.05)
    verdict = canary.evaluate(sent=100, bounced=5)
    assert not verdict.tripped
    assert verdict.bounce_rate == 0.05


def test_canary_zero_sent_is_safe() -> None:
    canary = BounceCanary(absolute_floor=1, rate_threshold=0.05)
    verdict = canary.evaluate(sent=0, bounced=0)
    assert not verdict.tripped
    assert verdict.bounce_rate == 0.0


def _send(
    idx: int,
    *,
    send_at: datetime,
    status: SendStatus = SendStatus.SCHEDULED,
) -> ScheduledSend:
    return ScheduledSend(
        prospect_id=f"p{idx}",
        email=f"shop{idx}@example.com",
        wave=Wave.INITIAL,
        send_at=send_at,
        idem_key=f"c/shop{idx}@example.com-w1",
        status=status,
    )


def test_sends_to_cancel_returns_only_future_in_window_scheduled() -> None:
    clock = _clock()
    in_window = _send(0, send_at=_NOW + timedelta(hours=2))
    at_horizon = _send(1, send_at=_NOW + timedelta(hours=6))
    past = _send(2, send_at=_NOW - timedelta(hours=1))
    beyond = _send(3, send_at=_NOW + timedelta(hours=10))
    already_sent = _send(4, send_at=_NOW + timedelta(hours=1), status=SendStatus.SENT)
    cancelled = _send(5, send_at=_NOW + timedelta(hours=1), status=SendStatus.CANCELLED)

    canary = BounceCanary(absolute_floor=1, rate_threshold=0.01)
    to_cancel = canary.sends_to_cancel(
        [in_window, at_horizon, past, beyond, already_sent, cancelled],
        window_hours=6,
        clock=clock,
    )

    assert [s.prospect_id for s in to_cancel] == ["p0", "p1"]


def test_sends_to_cancel_includes_send_due_now() -> None:
    clock = _clock()
    due_now = _send(0, send_at=_NOW)
    canary = BounceCanary(absolute_floor=1, rate_threshold=0.01)
    to_cancel = canary.sends_to_cancel([due_now], window_hours=6, clock=clock)
    assert [s.prospect_id for s in to_cancel] == ["p0"]


def test_sends_to_cancel_rejects_nonpositive_window() -> None:
    import pytest

    canary = BounceCanary(absolute_floor=1, rate_threshold=0.01)
    with pytest.raises(ValueError, match="must be positive"):
        canary.sends_to_cancel([], window_hours=0, clock=_clock())


# --- Daily report ----------------------------------------------------------


def test_tier_green_below_one_point_five_percent() -> None:
    assert tier_for_bounce_rate(0.0) is StatusTier.GREEN
    assert tier_for_bounce_rate(0.0149) is StatusTier.GREEN


def test_tier_yellow_band() -> None:
    # 1.5% is the green boundary -> yellow; under 3% stays yellow.
    assert tier_for_bounce_rate(0.015) is StatusTier.YELLOW
    assert tier_for_bounce_rate(0.029) is StatusTier.YELLOW


def test_tier_red_at_and_above_three_percent() -> None:
    assert tier_for_bounce_rate(0.03) is StatusTier.RED
    assert tier_for_bounce_rate(0.5) is StatusTier.RED


def test_report_green_emoji_and_content() -> None:
    report = DailyReport.from_counts(sent=1000, bounced=5, opt_outs=2, scheduled_ahead=400)
    assert report.tier is StatusTier.GREEN
    rendered = report.render()
    assert "\U0001f7e2" in rendered
    assert "**Sent:** 1000" in rendered
    assert "**Bounced:** 5 (0.50%)" in rendered
    assert "**Opt-outs:** 2" in rendered
    assert "**Scheduled ahead:** 400" in rendered


def test_report_yellow_emoji() -> None:
    report = DailyReport.from_counts(sent=1000, bounced=20, opt_outs=0, scheduled_ahead=0)
    assert report.tier is StatusTier.YELLOW
    assert "\U0001f7e1" in report.render()


def test_report_red_emoji() -> None:
    report = DailyReport.from_counts(sent=1000, bounced=40, opt_outs=0, scheduled_ahead=0)
    assert report.tier is StatusTier.RED
    assert "\U0001f534" in report.render()


def test_report_bounce_rate_zero_when_nothing_sent() -> None:
    report = DailyReport.from_counts(sent=0, bounced=0, opt_outs=0, scheduled_ahead=10)
    assert report.bounce_rate == 0.0
    assert report.tier is StatusTier.GREEN
