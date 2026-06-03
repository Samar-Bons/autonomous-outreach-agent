# ABOUTME: The dry-run sender: records every send in memory and never touches the network.
# ABOUTME: Default sender for the reference build; a real provider adapter fits the same Protocol.
from __future__ import annotations

from collections.abc import Callable

from ..domain import Draft, ScheduledSend


class DryRunSender:
    """Records sends in memory instead of delivering them.

    This is the default sender for the reference build: it appends each
    ``(scheduled, draft)`` pair to :attr:`sent` and returns True, with no
    network access. A real provider adapter (e.g. Resend, passing ``scheduled_at``
    and an idempotency key derived from ``ScheduledSend.idem_key``) would
    implement the same EmailSender Protocol and slot in unchanged.
    """

    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self.sent: list[tuple[ScheduledSend, Draft]] = []
        self._log = log

    def send(self, scheduled: ScheduledSend, draft: Draft) -> bool:
        self.sent.append((scheduled, draft))
        if self._log is not None:
            self._log(
                f"[dry-run] would send wave {scheduled.wave.value} to {scheduled.email} "
                f"at {scheduled.send_at.isoformat()}: {draft.subject}"
            )
        return True
