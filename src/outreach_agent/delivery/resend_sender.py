# ABOUTME: The real Resend email-provider adapter, behind the EmailSender Protocol.
# ABOUTME: HTTP transport is injectable; the default uses stdlib urllib, so tests need no network.
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol, cast, runtime_checkable

from ..domain import Draft, ScheduledSend

RESEND_EMAILS_URL = "https://api.resend.com/emails"


@runtime_checkable
class HttpPoster(Protocol):
    """The single HTTP seam for the Resend adapter.

    A real urllib-backed implementation and a test fake satisfy this same
    interface, so :class:`ResendSender` can be exercised with zero network.
    """

    def post(
        self, url: str, *, headers: dict[str, str], payload: dict[str, Any]
    ) -> tuple[int, dict[str, Any]]:
        """POST ``payload`` as JSON to ``url`` and return (status_code, parsed_body)."""
        ...


class UrllibPoster:
    """Default :class:`HttpPoster` built on stdlib ``urllib.request``.

    Carries no external dependency. An ``HTTPError`` (any non-2xx response) is
    caught and reported as its status code plus parsed body, so callers branch
    on the status rather than handling exceptions.
    """

    def post(
        self, url: str, *, headers: dict[str, str], payload: dict[str, Any]
    ) -> tuple[int, dict[str, Any]]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request) as response:
                status = int(response.status)
                body = self._parse(response.read())
                return status, body
        except urllib.error.HTTPError as error:
            body = self._parse(error.read())
            return int(error.code), body

    @staticmethod
    def _parse(raw: bytes) -> dict[str, Any]:
        if not raw:
            return {}
        decoded: Any = json.loads(raw)
        if isinstance(decoded, dict):
            return cast("dict[str, Any]", decoded)
        return {"data": decoded}


class ResendSender:
    """The real provider adapter: delivers a scheduled send through Resend.

    Implements the EmailSender Protocol, so it slots in wherever
    ``DryRunSender`` does. Three details make it production-safe:

    * The ``Idempotency-Key`` header is set to ``ScheduledSend.idem_key`` so a
      retried send (same prospect + wave) is collapsed by Resend and never
      double-delivers.
    * ``scheduled_at`` is passed through so Resend honors the planned send time.
    * ``List-Unsubscribe`` and ``List-Unsubscribe-Post`` headers are always
      attached for CAN-SPAM / RFC 8058 one-click-unsubscribe compliance.
    """

    def __init__(
        self,
        *,
        api_key: str,
        from_address: str,
        transport: HttpPoster | None = None,
        reply_to: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._from_address = from_address
        self._transport: HttpPoster = transport if transport is not None else UrllibPoster()
        self._reply_to = reply_to

    def send(self, scheduled: ScheduledSend, draft: Draft) -> bool:
        """Deliver one send via Resend. Returns True only on a 2xx response."""
        payload = self._build_payload(scheduled, draft)
        headers = self._build_headers(scheduled)
        status, _ = self._transport.post(RESEND_EMAILS_URL, headers=headers, payload=payload)
        return 200 <= status < 300

    def _build_payload(self, scheduled: ScheduledSend, draft: Draft) -> dict[str, Any]:
        domain = self._from_domain()
        payload: dict[str, Any] = {
            "from": self._from_address,
            "to": [scheduled.email],
            "subject": draft.subject,
            "text": draft.body,
            "scheduled_at": scheduled.send_at.isoformat(),
            "headers": {
                "List-Unsubscribe": f"<mailto:unsubscribe@{domain}?subject=unsubscribe>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        }
        if self._reply_to is not None:
            payload["reply_to"] = self._reply_to
        return payload

    def _build_headers(self, scheduled: ScheduledSend) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": scheduled.idem_key,
        }

    def _from_domain(self) -> str:
        """The domain part of ``from_address`` (after the last ``@``)."""
        return self._from_address.rsplit("@", 1)[-1]
