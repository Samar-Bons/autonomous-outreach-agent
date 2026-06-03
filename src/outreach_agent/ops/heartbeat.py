# ABOUTME: A dead-man's-switch that tells whether the agent is alive, stalled, or never started.
# ABOUTME: Distinguishes "never ran" from "stopped running" so an on-call operator knows which.
from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ..protocols import Clock


class HeartbeatState(StrEnum):
    """The three states a heartbeat can report.

    ``NEVER_RAN`` (the agent has no recorded run) is deliberately distinct from
    ``STALE`` (it ran once but has gone quiet): the first means "it never
    started", the second means "it stopped", and an operator responds to each
    differently.
    """

    NEVER_RAN = "never_ran"
    STALE = "stale"
    OK = "ok"


class HeartbeatStatus(BaseModel):
    """The frozen verdict of one heartbeat check."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: HeartbeatState
    last_run_at: datetime | None
    silence_minutes: float | None
    message: str

    @property
    def healthy(self) -> bool:
        """True only when the agent ran recently enough."""
        return self.state is HeartbeatState.OK


class HeartbeatMonitor:
    """A dead-man's-switch over the agent's last successful run timestamp.

    ``check`` compares the elapsed silence against ``max_silence_minutes`` using
    the injected clock, so the verdict is deterministic under a ``FixedClock``.
    """

    def __init__(self, clock: Clock, *, max_silence_minutes: int) -> None:
        if max_silence_minutes <= 0:
            raise ValueError("max_silence_minutes must be positive")
        self._clock = clock
        self._max_silence_minutes = max_silence_minutes

    def check(self, last_run_at: datetime | None) -> HeartbeatStatus:
        """Classify the agent's liveness from its last recorded run."""
        if last_run_at is None:
            return HeartbeatStatus(
                state=HeartbeatState.NEVER_RAN,
                last_run_at=None,
                silence_minutes=None,
                message="No run on record: the agent has never started.",
            )

        silence = self._clock.now() - last_run_at
        silence_minutes = silence.total_seconds() / 60.0
        budget = timedelta(minutes=self._max_silence_minutes)

        if silence > budget:
            return HeartbeatStatus(
                state=HeartbeatState.STALE,
                last_run_at=last_run_at,
                silence_minutes=silence_minutes,
                message=(
                    f"Stale: last run {silence_minutes:.1f} min ago "
                    f"exceeds the {self._max_silence_minutes} min budget."
                ),
            )

        return HeartbeatStatus(
            state=HeartbeatState.OK,
            last_run_at=last_run_at,
            silence_minutes=silence_minutes,
            message=(
                f"OK: last run {silence_minutes:.1f} min ago, "
                f"within the {self._max_silence_minutes} min budget."
            ),
        )
