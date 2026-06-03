# ABOUTME: The safety gate: runs the deterministic check chain and aggregates one verdict.
# ABOUTME: A draft ships only if no check returns a BLOCK; warnings are surfaced, not fatal.
from __future__ import annotations

from collections.abc import Sequence

from ..domain import CheckFailure, Draft, ValidationResult
from ..protocols import DraftCheck
from .checks import (
    AiSlopCheck,
    ForbiddenBrandCheck,
    GenericAddressCheck,
    MergeFieldLeakCheck,
    SpamMarkerCheck,
)


class DefaultSafetyGate:
    """Runs every check over a draft and concatenates their findings into one result."""

    def __init__(self, checks: Sequence[DraftCheck]) -> None:
        self._checks = tuple(checks)

    def validate(self, draft: Draft) -> ValidationResult:
        failures: list[CheckFailure] = []
        for check in self._checks:
            failures.extend(check.check(draft).failures)
        return ValidationResult(
            prospect_id=draft.prospect_id,
            wave=draft.wave,
            failures=tuple(failures),
        )


def default_checks() -> list[DraftCheck]:
    """The standard chain, ordered cheapest-signal first."""
    return [
        MergeFieldLeakCheck(),
        SpamMarkerCheck(),
        AiSlopCheck(),
        ForbiddenBrandCheck(),
        GenericAddressCheck(),
    ]


def default_gate() -> DefaultSafetyGate:
    """A gate wired with the standard check chain."""
    return DefaultSafetyGate(default_checks())
