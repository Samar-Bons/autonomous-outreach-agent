# ABOUTME: Unit tests for the strict classification/angle parsers.
# ABOUTME: The parsers must reject malformed or off-list output so the caller can abstain.
from __future__ import annotations

import json

from outreach_agent.classify.prompts import (
    parse_angle_response,
    parse_classification_response,
)
from outreach_agent.domain.enums import Archetype, Segment


def _row(idx: int, segment: str, archetype: str, confidence: float = 0.9) -> dict[str, object]:
    return {
        "idx": idx,
        "segment": segment,
        "archetype": archetype,
        "confidence": confidence,
        "reason": "r",
    }


def test_parses_valid_batch() -> None:
    text = json.dumps(
        [_row(0, "hd_diesel", "hd_diesel"), _row(1, "passenger_lube", "euro_specialist")]
    )
    parsed = parse_classification_response(text, [0, 1])
    assert parsed is not None
    assert parsed[0][0] is Segment.HD_DIESEL
    assert parsed[1][1] is Archetype.EURO_SPECIALIST


def test_parses_fenced_json() -> None:
    text = "```json\n" + json.dumps([_row(0, "hd_diesel", "hd_diesel")]) + "\n```"
    assert parse_classification_response(text, [0]) is not None


def test_rejects_invalid_json() -> None:
    assert parse_classification_response("not json", [0]) is None


def test_rejects_length_mismatch() -> None:
    text = json.dumps([_row(0, "hd_diesel", "hd_diesel")])
    assert parse_classification_response(text, [0, 1]) is None


def test_rejects_off_list_archetype() -> None:
    text = json.dumps([_row(0, "hd_diesel", "spaceship_mechanic")])
    assert parse_classification_response(text, [0]) is None


def test_rejects_off_list_segment() -> None:
    text = json.dumps([_row(0, "aerospace", "hd_diesel")])
    assert parse_classification_response(text, [0]) is None


def test_rejects_unexpected_idx() -> None:
    text = json.dumps([_row(5, "hd_diesel", "hd_diesel")])
    assert parse_classification_response(text, [0]) is None


def test_rejects_duplicate_idx() -> None:
    text = json.dumps([_row(0, "hd_diesel", "hd_diesel"), _row(0, "hd_diesel", "hd_diesel")])
    assert parse_classification_response(text, [0, 1]) is None


def test_rejects_confidence_out_of_range() -> None:
    text = json.dumps([_row(0, "hd_diesel", "hd_diesel", confidence=1.5)])
    assert parse_classification_response(text, [0]) is None


def test_angle_parse_accepts_candidate() -> None:
    text = json.dumps({"angle_key": "bulk_supply", "reason": "r"})
    assert parse_angle_response(text, ["bulk_supply", "next_day_delivery"]) == "bulk_supply"


def test_angle_parse_rejects_non_candidate() -> None:
    text = json.dumps({"angle_key": "made_up_angle", "reason": "r"})
    assert parse_angle_response(text, ["bulk_supply"]) is None


def test_angle_parse_rejects_invalid_json() -> None:
    assert parse_angle_response("{bad", ["bulk_supply"]) is None
