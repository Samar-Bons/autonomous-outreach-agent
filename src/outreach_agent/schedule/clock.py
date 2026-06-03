# ABOUTME: Clock implementations: a real wall-clock and a frozen clock for deterministic tests.
# ABOUTME: Scheduling depends on the Clock Protocol, so time never leaks into the planning logic.
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime


class SystemClock:
    """The real time source, used in production runs."""

    def today(self) -> date:
        """Today's UTC date."""
        return datetime.now(UTC).date()

    def now(self) -> datetime:
        """The current UTC instant."""
        return datetime.now(UTC)


@dataclass(frozen=True)
class FixedClock:
    """A clock pinned to known values so schedules are reproducible in tests."""

    today_value: date
    now_value: datetime

    def today(self) -> date:
        """The pinned campaign-relative date."""
        return self.today_value

    def now(self) -> datetime:
        """The pinned instant."""
        return self.now_value
