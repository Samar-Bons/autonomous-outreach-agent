# ABOUTME: Unit tests for the domain contracts: the behaviors stages rely on.
# ABOUTME: Covers quarantine derivation, gate verdicts, idempotency keys, and normalization.
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from outreach_agent.domain import (
    Archetype,
    CheckFailure,
    CheckSeverity,
    Classification,
    Prospect,
    ScheduledSend,
    Segment,
    ValidationResult,
    Wave,
    normalize_email,
)
from outreach_agent.domain.enums import QUARANTINE_ARCHETYPES


def _classification(archetype: Archetype) -> Classification:
    return Classification(
        prospect_id="p1",
        segment=Segment.PASSENGER_LUBE,
        archetype=archetype,
        confidence=0.9,
    )


@pytest.mark.parametrize("archetype", sorted(QUARANTINE_ARCHETYPES))
def test_quarantine_archetypes_are_quarantined(archetype: Archetype) -> None:
    assert _classification(archetype).is_quarantined is True


@pytest.mark.parametrize(
    "archetype",
    [a for a in Archetype if a not in QUARANTINE_ARCHETYPES],
)
def test_in_scope_archetypes_are_not_quarantined(archetype: Archetype) -> None:
    assert _classification(archetype).is_quarantined is False


def test_needs_retry_is_distinct_from_unclear() -> None:
    # Both quarantine, but they mean different things and must stay separate.
    assert Archetype.NEEDS_RETRY is not Archetype.UNCLEAR
    assert Archetype.NEEDS_RETRY in QUARANTINE_ARCHETYPES
    assert Archetype.UNCLEAR in QUARANTINE_ARCHETYPES


def test_validation_passes_with_no_failures() -> None:
    result = ValidationResult(prospect_id="p1", wave=Wave.INITIAL)
    assert result.passed is True


def test_validation_passes_with_only_warnings() -> None:
    result = ValidationResult(
        prospect_id="p1",
        wave=Wave.INITIAL,
        failures=(CheckFailure(check_name="x", severity=CheckSeverity.WARN, detail="d"),),
    )
    assert result.passed is True


def test_validation_fails_on_any_block() -> None:
    result = ValidationResult(
        prospect_id="p1",
        wave=Wave.INITIAL,
        failures=(
            CheckFailure(check_name="a", severity=CheckSeverity.WARN, detail="d"),
            CheckFailure(check_name="b", severity=CheckSeverity.BLOCK, detail="d"),
        ),
    )
    assert result.passed is False


def test_idem_key_is_deterministic_and_normalized() -> None:
    a = ScheduledSend.make_idem_key("camp", "  Owner@Shop.COM ", Wave.BUMP)
    b = ScheduledSend.make_idem_key("camp", "owner@shop.com", Wave.BUMP)
    assert a == b == "camp/owner@shop.com-w2"


def test_idem_key_differs_per_wave() -> None:
    w1 = ScheduledSend.make_idem_key("camp", "a@b.com", Wave.INITIAL)
    w4 = ScheduledSend.make_idem_key("camp", "a@b.com", Wave.BREAKUP)
    assert w1 != w4


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Foo@Bar.com  ", "foo@bar.com"),
        ("<foo@bar.com>", "foo@bar.com"),
        ('"foo@bar.com"', "foo@bar.com"),
        ("FOO@BAR.COM", "foo@bar.com"),
    ],
)
def test_normalize_email(raw: str, expected: str) -> None:
    assert normalize_email(raw) == expected


def test_models_are_immutable() -> None:
    p = Prospect(id="p1", name="Shop", city="Dallas")
    with pytest.raises(ValidationError):
        p.name = "Other"  # type: ignore[misc]


def test_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Prospect(id="p1", name="Shop", city="Dallas", bogus="x")  # type: ignore[call-arg]


def test_scheduled_send_defaults_to_scheduled_status() -> None:
    s = ScheduledSend(
        prospect_id="p1",
        email="a@b.com",
        wave=Wave.INITIAL,
        send_at=datetime(2026, 4, 22, 11, 0, 0),
        idem_key="camp/a@b.com-w1",
    )
    assert s.status.value == "scheduled"
    assert s.cancel_reason is None
