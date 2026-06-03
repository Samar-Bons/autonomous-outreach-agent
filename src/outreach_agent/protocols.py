# ABOUTME: The frozen interface layer. Every stage depends on these Protocols, not concretions.
# ABOUTME: Real and stub implementations are interchangeable, which keeps the system testable.
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from .domain import (
    AngleSelection,
    Classification,
    Draft,
    Prospect,
    Reply,
    ScheduledSend,
    SuppressionEntry,
    ValidationResult,
)
from .domain.enums import ModelTier


@runtime_checkable
class DataSource(Protocol):
    """Yields raw prospects into the pipeline. The synthetic CSV source is one impl."""

    def load(self) -> Sequence[Prospect]: ...


@runtime_checkable
class LLMClient(Protocol):
    """The single seam through which all model reasoning flows.

    A real Anthropic-backed client and a deterministic stub satisfy this same
    interface, so the entire pipeline runs in tests with zero tokens spent.
    """

    def complete(
        self,
        *,
        tier: ModelTier,
        system: str,
        user: str,
        max_tokens: int = 1024,
    ) -> str: ...


@runtime_checkable
class Classifier(Protocol):
    """Assigns segment + archetype. Must abstain (NEEDS_RETRY) rather than guess."""

    def classify(self, prospects: Sequence[Prospect]) -> list[Classification]: ...


@runtime_checkable
class AnglePicker(Protocol):
    """Picks the pitch angle for an in-scope prospect, or None to drop it."""

    def pick(self, prospect: Prospect, classification: Classification) -> AngleSelection | None: ...


@runtime_checkable
class EmailFinder(Protocol):
    """Resolves a contact email for a prospect, or None if none can be found."""

    def find(self, prospect: Prospect) -> str | None: ...


@runtime_checkable
class EmailVerifier(Protocol):
    """Verifies deliverability. Returns True to keep, False to drop the address."""

    def verify(self, email: str) -> bool: ...


@runtime_checkable
class CopyGenerator(Protocol):
    """Renders a draft for a prospect, classification, angle, and wave."""

    def generate(
        self,
        prospect: Prospect,
        classification: Classification,
        angle: AngleSelection,
        wave: int,
    ) -> Draft: ...


@runtime_checkable
class DraftCheck(Protocol):
    """One deterministic safety check. The gate runs a chain of these."""

    @property
    def name(self) -> str: ...

    def check(self, draft: Draft) -> ValidationResult: ...


@runtime_checkable
class SafetyGate(Protocol):
    """Runs the full check chain and returns the aggregate verdict for a draft."""

    def validate(self, draft: Draft) -> ValidationResult: ...


@runtime_checkable
class SuppressionStore(Protocol):
    """The append-only do-not-send list. Owned entirely by the system."""

    def is_suppressed(self, email: str) -> bool: ...

    def add(self, entry: SuppressionEntry) -> None: ...

    def all(self) -> Sequence[SuppressionEntry]: ...


@runtime_checkable
class OptOutDetector(Protocol):
    """Deterministic opt-out detection. Runs ahead of any model triage."""

    def is_opt_out(self, reply: Reply) -> bool: ...


@runtime_checkable
class Clock(Protocol):
    """Injectable time source so scheduling is deterministic in tests."""

    def today(self) -> date: ...

    def now(self) -> datetime: ...


@runtime_checkable
class WavePlanner(Protocol):
    """Places sends on the calendar under warmup caps and wave offsets."""

    def plan(
        self,
        drafts: Sequence[Draft],
        existing_counts: dict[date, int],
    ) -> list[ScheduledSend]: ...


@runtime_checkable
class EmailSender(Protocol):
    """Delivers a scheduled send. The default impl is a dry-run (no network)."""

    def send(self, scheduled: ScheduledSend, draft: Draft) -> bool: ...
