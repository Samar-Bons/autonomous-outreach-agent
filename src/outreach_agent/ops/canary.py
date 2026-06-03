# ABOUTME: A bounce-rate tripwire that halts a campaign before a bad list torches sender reputation.
# ABOUTME: Trips only above both an absolute floor and a rate threshold, then names sends to cancel.
from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

from pydantic import BaseModel, ConfigDict

from ..domain import ScheduledSend
from ..domain.enums import SendStatus
from ..protocols import Clock


class CanaryVerdict(BaseModel):
    """The frozen verdict of one bounce-rate evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tripped: bool
    bounce_rate: float
    reason: str


class BounceCanary:
    """A two-condition tripwire on observed bounces.

    The canary trips only when both gates are crossed: ``bounced`` reaches an
    ``absolute_floor`` (so a single bounce on a tiny day cannot trip it) and the
    bounce rate exceeds ``rate_threshold`` (so a high count on huge volume is
    judged proportionally). When tripped, the caller emergency-cancels the
    near-term queue via ``sends_to_cancel``.
    """

    def __init__(self, *, absolute_floor: int, rate_threshold: float) -> None:
        if absolute_floor < 0:
            raise ValueError("absolute_floor must be non-negative")
        if not 0.0 <= rate_threshold <= 1.0:
            raise ValueError("rate_threshold must be between 0.0 and 1.0")
        self._absolute_floor = absolute_floor
        self._rate_threshold = rate_threshold

    def evaluate(self, sent: int, bounced: int) -> CanaryVerdict:
        """Judge a sent/bounced tally against the floor and the rate threshold."""
        if sent < 0 or bounced < 0:
            raise ValueError("sent and bounced must be non-negative")
        if bounced > sent:
            raise ValueError("bounced cannot exceed sent")

        bounce_rate = bounced / sent if sent else 0.0

        if bounced < self._absolute_floor:
            return CanaryVerdict(
                tripped=False,
                bounce_rate=bounce_rate,
                reason=(
                    f"Below floor: {bounced} bounce(s) < absolute floor of {self._absolute_floor}."
                ),
            )

        if bounce_rate <= self._rate_threshold:
            return CanaryVerdict(
                tripped=False,
                bounce_rate=bounce_rate,
                reason=(
                    f"Within tolerance: rate {bounce_rate:.2%} "
                    f"<= threshold {self._rate_threshold:.2%}."
                ),
            )

        return CanaryVerdict(
            tripped=True,
            bounce_rate=bounce_rate,
            reason=(
                f"Tripped: {bounced} bounce(s) at rate {bounce_rate:.2%} "
                f"exceeds threshold {self._rate_threshold:.2%} (floor "
                f"{self._absolute_floor} met)."
            ),
        )

    def sends_to_cancel(
        self,
        scheduled: Sequence[ScheduledSend],
        window_hours: int,
        clock: Clock,
    ) -> list[ScheduledSend]:
        """The still-SCHEDULED sends due within the next ``window_hours``.

        These are the sends an operator would emergency-cancel once the canary
        trips. Past sends and already-sent/cancelled/failed entries are left
        alone; only the future queue inside the window is returned, in order.
        """
        if window_hours <= 0:
            raise ValueError("window_hours must be positive")
        now = clock.now()
        horizon = now + timedelta(hours=window_hours)
        return [
            s for s in scheduled if s.status is SendStatus.SCHEDULED and now <= s.send_at <= horizon
        ]
