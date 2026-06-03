# ABOUTME: The warmup wave planner: ramps daily volume, skips weekends, and offsets follow-ups.
# ABOUTME: Pure and deterministic given an injected Clock; placing a send never touches the network.
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from ..config import DEFAULT_WARMUP_CAPS, STEADY_STATE_CAP, WAVE_OFFSET_DAYS
from ..domain import Draft, ScheduledSend
from ..protocols import Clock

# How far forward to probe for an open slot before giving up. A campaign that
# cannot place a send within this horizon is misconfigured, not merely full.
_SEARCH_HORIZON_DAYS = 120

# All sends for a given date land inside this UTC window, spaced apart so the
# burst looks organic rather than a single machine-gun blast.
_SEND_HOUR_UTC = 11
_SLOT_SPACING_SECONDS = 30


class WarmupWavePlanner:
    """Places drafts on the calendar under warmup caps and per-wave offsets.

    The campaign starts on ``clock.today()``. Daily ceilings ramp by weekday
    index since start (weekends are zero), then hold at the steady-state cap.
    Each draft is placed on the earliest weekday at or after its wave offset
    that still has capacity, preserving input order in the returned list.
    """

    def __init__(self, clock: Clock, *, campaign: str) -> None:
        self._clock = clock
        self._campaign = campaign

    def cap_for(self, target: date) -> int:
        """The send ceiling for ``target``: zero on weekends, else the ramped cap."""
        if target.weekday() >= 5:
            return 0
        start = self._clock.today()
        index = 0
        cursor = start
        while cursor < target:
            cursor += timedelta(days=1)
            if cursor.weekday() < 5:
                index += 1
        if index < len(DEFAULT_WARMUP_CAPS):
            return DEFAULT_WARMUP_CAPS[index]
        return STEADY_STATE_CAP

    def plan(
        self,
        drafts: Sequence[Draft],
        existing_counts: dict[date, int],
    ) -> list[ScheduledSend]:
        """Schedule every draft, returning the placements in input order."""
        used: dict[date, int] = dict(existing_counts)
        scheduled: list[ScheduledSend] = []
        for draft in drafts:
            base = self._clock.today() + timedelta(days=WAVE_OFFSET_DAYS[draft.wave.value])
            target = self._earliest_open_day(base, used)
            slot = used.get(target, 0)
            used[target] = slot + 1
            send_at = datetime(
                target.year, target.month, target.day, _SEND_HOUR_UTC, 0, tzinfo=UTC
            ) + timedelta(seconds=slot * _SLOT_SPACING_SECONDS)
            scheduled.append(
                ScheduledSend(
                    prospect_id=draft.prospect_id,
                    email=draft.email,
                    wave=draft.wave,
                    send_at=send_at,
                    idem_key=ScheduledSend.make_idem_key(self._campaign, draft.email, draft.wave),
                )
            )
        return scheduled

    def _earliest_open_day(self, base: date, used: dict[date, int]) -> date:
        """Walk forward from ``base`` to the first weekday with spare capacity."""
        for offset in range(_SEARCH_HORIZON_DAYS):
            target = base + timedelta(days=offset)
            if used.get(target, 0) < self.cap_for(target):
                return target
        raise RuntimeError(
            f"no open send slot within {_SEARCH_HORIZON_DAYS} days of {base.isoformat()}"
        )
