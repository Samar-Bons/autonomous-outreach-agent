# ABOUTME: Unit tests for DryRunSender: in-order recording, True return, and optional log callback.
# ABOUTME: Proves the dry-run sender captures every send without touching the network.
from __future__ import annotations

from datetime import datetime

from outreach_agent.delivery import DryRunSender
from outreach_agent.domain import Draft, ScheduledSend
from outreach_agent.domain.enums import Segment, Wave


def _scheduled(email: str, wave: Wave) -> ScheduledSend:
    return ScheduledSend(
        prospect_id="p1",
        email=email,
        wave=wave,
        send_at=datetime(2026, 6, 2, 9, 0, 0),
        idem_key=f"camp/{email}-w{wave.value}",
    )


def _draft(email: str, wave: Wave, subject: str) -> Draft:
    return Draft(
        prospect_id="p1",
        email=email,
        wave=wave,
        segment=Segment.HD_DIESEL,
        angle_key="uptime",
        subject=subject,
        body="hello",
    )


def test_send_records_in_order_and_returns_true() -> None:
    sender = DryRunSender()
    first = (_scheduled("a@x.com", Wave.INITIAL), _draft("a@x.com", Wave.INITIAL, "one"))
    second = (_scheduled("b@y.com", Wave.BUMP), _draft("b@y.com", Wave.BUMP, "two"))

    assert sender.send(*first) is True
    assert sender.send(*second) is True

    assert sender.sent == [first, second]


def test_send_invokes_log_callback_when_provided() -> None:
    lines: list[str] = []
    sender = DryRunSender(log=lines.append)

    sender.send(_scheduled("a@x.com", Wave.INITIAL), _draft("a@x.com", Wave.INITIAL, "one"))

    assert len(lines) == 1
    assert "a@x.com" in lines[0]


def test_send_without_log_callback_does_not_raise() -> None:
    sender = DryRunSender()
    sender.send(_scheduled("a@x.com", Wave.INITIAL), _draft("a@x.com", Wave.INITIAL, "one"))
    assert len(sender.sent) == 1
