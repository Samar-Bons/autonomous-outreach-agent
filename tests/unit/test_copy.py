# ABOUTME: Unit tests for the copy stage: rendering, wave mapping, and gate-clean templates.
# ABOUTME: The key test proves every (segment, angle, wave) template passes the safety gate.
from __future__ import annotations

import pytest

from outreach_agent.classify.angles import SEGMENT_ANGLES
from outreach_agent.copy import TemplateCopyGenerator, TemplateStore
from outreach_agent.domain import AngleSelection, Classification, Prospect
from outreach_agent.domain.enums import Archetype, Segment, Wave
from outreach_agent.safety import default_gate


def _prospect(*, email: str | None = "owner@bigrigdiesel.com") -> Prospect:
    return Prospect(
        id="p1",
        name="Big Rig Diesel Service",
        city="Dallas",
        email=email,
    )


def _classification(segment: Segment) -> Classification:
    return Classification(
        prospect_id="p1",
        segment=segment,
        archetype=Archetype.HD_DIESEL,
        confidence=0.9,
    )


def _angle(angle_key: str) -> AngleSelection:
    return AngleSelection(prospect_id="p1", angle_key=angle_key)


def test_placeholders_are_filled() -> None:
    gen = TemplateCopyGenerator(TemplateStore())
    draft = gen.generate(
        _prospect(),
        _classification(Segment.HD_DIESEL),
        _angle("next_day_delivery"),
        wave=1,
    )
    assert "{" not in draft.subject
    assert "{" not in draft.body
    assert "Big Rig Diesel Service" in draft.body
    assert "Dallas" in draft.body


def test_wave_int_maps_to_wave_enum() -> None:
    gen = TemplateCopyGenerator(TemplateStore())
    for wave_int, expected in (
        (1, Wave.INITIAL),
        (2, Wave.BUMP),
        (3, Wave.PIVOT),
        (4, Wave.BREAKUP),
    ):
        draft = gen.generate(
            _prospect(),
            _classification(Segment.HD_DIESEL),
            _angle("bulk_supply"),
            wave=wave_int,
        )
        assert draft.wave is expected


def test_segment_is_carried_through() -> None:
    gen = TemplateCopyGenerator(TemplateStore())
    draft = gen.generate(
        _prospect(),
        _classification(Segment.DEALER_FLEET),
        _angle("volume_pricing"),
        wave=1,
    )
    assert draft.segment is Segment.DEALER_FLEET
    assert draft.angle_key == "volume_pricing"


def test_missing_email_raises_value_error() -> None:
    gen = TemplateCopyGenerator(TemplateStore())
    with pytest.raises(ValueError, match="no email"):
        gen.generate(
            _prospect(email=None),
            _classification(Segment.HD_DIESEL),
            _angle("def_in_stock"),
            wave=1,
        )


def test_unknown_angle_raises_key_error() -> None:
    gen = TemplateCopyGenerator(TemplateStore())
    with pytest.raises(KeyError):
        gen.generate(
            _prospect(),
            _classification(Segment.HD_DIESEL),
            _angle("not_a_real_angle"),
            wave=1,
        )


def test_every_template_passes_the_safety_gate() -> None:
    gen = TemplateCopyGenerator(TemplateStore())
    gate = default_gate()
    checked = 0
    for segment, angle_keys in SEGMENT_ANGLES.items():
        for angle_key in angle_keys:
            for wave_int in (1, 2, 3, 4):
                draft = gen.generate(
                    _prospect(),
                    _classification(segment),
                    _angle(angle_key),
                    wave=wave_int,
                )
                result = gate.validate(draft)
                assert result.passed is True, (
                    f"gate failed for {segment.value}/{angle_key}/wave{wave_int}: "
                    f"{[f.detail for f in result.failures]}"
                )
                checked += 1
    # 6 + 5 + 4 angles across 4 waves each.
    assert checked == (6 + 5 + 4) * 4
