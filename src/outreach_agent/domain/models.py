# ABOUTME: Core domain models passed between pipeline stages, validated with Pydantic.
# ABOUTME: These types are the frozen contract; stages depend on them, not on each other.
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    QUARANTINE_ARCHETYPES,
    Archetype,
    CheckSeverity,
    ReplyClassification,
    Segment,
    SendStatus,
    SuppressionReason,
    Wave,
)


class _Frozen(BaseModel):
    """Immutable base. Stage outputs are values, not mutable buffers."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Prospect(_Frozen):
    """A business sourced into the pipeline, before any model touches it."""

    id: str
    name: str
    city: str
    state: str = "TX"
    sic: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    employees: int | None = None
    rating: float | None = None
    review_count: int | None = None
    source: str = "synthetic"


class Classification(_Frozen):
    """The segment + archetype verdict for one prospect."""

    prospect_id: str
    segment: Segment
    archetype: Archetype
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""

    @property
    def is_quarantined(self) -> bool:
        """True when this prospect must never be pitched."""
        return self.archetype in QUARANTINE_ARCHETYPES


class AngleSelection(_Frozen):
    """The chosen pitch angle for one prospect, plus the candidates considered."""

    prospect_id: str
    angle_key: str
    candidates: tuple[str, ...] = ()
    reason: str = ""


class Draft(_Frozen):
    """A rendered email for one prospect and wave, before safety validation."""

    prospect_id: str
    email: str
    wave: Wave
    segment: Segment
    angle_key: str
    subject: str
    body: str


class CheckFailure(_Frozen):
    """A single finding from one safety check."""

    check_name: str
    severity: CheckSeverity
    detail: str


class ValidationResult(_Frozen):
    """The aggregate verdict of the safety gate for one draft."""

    prospect_id: str
    wave: Wave
    failures: tuple[CheckFailure, ...] = ()

    @property
    def passed(self) -> bool:
        """A draft passes only if no BLOCK-severity check fired."""
        return not any(f.severity is CheckSeverity.BLOCK for f in self.failures)


class ScheduledSend(_Frozen):
    """A send placed on the calendar. ``idem_key`` makes re-runs safe."""

    prospect_id: str
    email: str
    wave: Wave
    send_at: datetime
    idem_key: str
    status: SendStatus = SendStatus.SCHEDULED
    cancel_reason: str | None = None

    @staticmethod
    def make_idem_key(campaign: str, email: str, wave: Wave) -> str:
        """Deterministic key so the same prospect+wave is never scheduled twice."""
        return f"{campaign}/{email.strip().lower()}-w{wave.value}"


class Reply(_Frozen):
    """An inbound reply to be triaged."""

    thread_id: str
    from_email: str
    subject: str
    body: str
    classification: ReplyClassification | None = None


class SuppressionEntry(_Frozen):
    """A do-not-send record. The suppression list is append-only."""

    email: str
    reason: SuppressionReason
    source: str
    added_at: datetime


# A display-name form like ``Joe <joe@x.com>``; the real address is in the brackets.
_ANGLE_ADDR_RE = re.compile(r"<([^<>]+)>")


def normalize_email(email: str) -> str:
    """Canonical form used everywhere a suppression decision is made.

    A display-name form like ``Joe <joe@x.com>`` is reduced to the inner address
    first, so it cannot bypass suppression. Bare addresses are left as-is.
    """
    match = _ANGLE_ADDR_RE.search(email)
    if match is not None:
        email = match.group(1)
    return email.strip().lower().strip("<>\"' ")
