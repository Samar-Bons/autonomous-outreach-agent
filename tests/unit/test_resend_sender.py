# ABOUTME: Unit tests for ResendSender: status-to-bool, payload shape, and compliance headers.
# ABOUTME: Uses a fake HttpPoster that records the request, so nothing touches the network.
from __future__ import annotations

from datetime import datetime
from typing import Any

from outreach_agent.delivery.resend_sender import ResendSender
from outreach_agent.domain import Draft, ScheduledSend
from outreach_agent.domain.enums import Segment, Wave


class FakePoster:
    """Records the last request and returns a configurable (status, body)."""

    def __init__(self, status: int = 200, body: dict[str, Any] | None = None) -> None:
        self.status = status
        self.body: dict[str, Any] = body if body is not None else {"id": "msg_1"}
        self.url: str | None = None
        self.headers: dict[str, str] = {}
        self.payload: dict[str, Any] = {}

    def post(
        self, url: str, *, headers: dict[str, str], payload: dict[str, Any]
    ) -> tuple[int, dict[str, Any]]:
        self.url = url
        self.headers = headers
        self.payload = payload
        return self.status, self.body


def _scheduled() -> ScheduledSend:
    return ScheduledSend(
        prospect_id="p1",
        email="shop@example.com",
        wave=Wave.INITIAL,
        send_at=datetime(2026, 6, 2, 9, 0, 0),
        idem_key="camp/shop@example.com-w1",
    )


def _draft() -> Draft:
    return Draft(
        prospect_id="p1",
        email="shop@example.com",
        wave=Wave.INITIAL,
        segment=Segment.HD_DIESEL,
        angle_key="uptime",
        subject="Cut your fleet downtime",
        body="Hello there.",
    )


def test_send_returns_true_on_2xx() -> None:
    poster = FakePoster(status=200)
    sender = ResendSender(api_key="re_test", from_address="hi@northwind.com", transport=poster)
    assert sender.send(_scheduled(), _draft()) is True


def test_send_returns_false_on_4xx() -> None:
    poster = FakePoster(status=422, body={"error": "invalid"})
    sender = ResendSender(api_key="re_test", from_address="hi@northwind.com", transport=poster)
    assert sender.send(_scheduled(), _draft()) is False


def test_send_returns_false_on_5xx() -> None:
    poster = FakePoster(status=500, body={"error": "boom"})
    sender = ResendSender(api_key="re_test", from_address="hi@northwind.com", transport=poster)
    assert sender.send(_scheduled(), _draft()) is False


def test_posts_to_resend_emails_endpoint() -> None:
    poster = FakePoster()
    sender = ResendSender(api_key="re_test", from_address="hi@northwind.com", transport=poster)
    sender.send(_scheduled(), _draft())
    assert poster.url == "https://api.resend.com/emails"


def test_payload_contains_core_fields() -> None:
    poster = FakePoster()
    sender = ResendSender(api_key="re_test", from_address="hi@northwind.com", transport=poster)
    sender.send(_scheduled(), _draft())

    assert poster.payload["from"] == "hi@northwind.com"
    assert poster.payload["to"] == ["shop@example.com"]
    assert poster.payload["subject"] == "Cut your fleet downtime"
    assert poster.payload["text"] == "Hello there."
    assert poster.payload["scheduled_at"] == "2026-06-02T09:00:00"


def test_headers_contain_auth_and_idempotency_key() -> None:
    poster = FakePoster()
    sender = ResendSender(api_key="re_test", from_address="hi@northwind.com", transport=poster)
    scheduled = _scheduled()
    sender.send(scheduled, _draft())

    assert poster.headers["Authorization"] == "Bearer re_test"
    assert poster.headers["Content-Type"] == "application/json"
    assert poster.headers["Idempotency-Key"] == scheduled.idem_key


def test_payload_carries_one_click_unsubscribe_headers() -> None:
    poster = FakePoster()
    sender = ResendSender(api_key="re_test", from_address="hi@northwind.com", transport=poster)
    sender.send(_scheduled(), _draft())

    headers = poster.payload["headers"]
    assert headers["List-Unsubscribe"] == "<mailto:unsubscribe@northwind.com?subject=unsubscribe>"
    assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


def test_reply_to_included_only_when_set() -> None:
    poster = FakePoster()
    without = ResendSender(api_key="re_test", from_address="hi@northwind.com", transport=poster)
    without.send(_scheduled(), _draft())
    assert "reply_to" not in poster.payload

    with_reply = ResendSender(
        api_key="re_test",
        from_address="hi@northwind.com",
        transport=poster,
        reply_to="sales@northwind.com",
    )
    with_reply.send(_scheduled(), _draft())
    assert poster.payload["reply_to"] == "sales@northwind.com"
