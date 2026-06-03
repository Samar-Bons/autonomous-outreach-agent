# ABOUTME: Prompt builders and strict response parsers for the classification stages.
# ABOUTME: Parsers reject malformed or off-list output (returning None) so the caller can abstain.
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import cast

from ..domain import Classification, Prospect
from ..domain.enums import Archetype, Segment
from ..llm import strip_code_fences
from ..llm.stub import ANGLE_MARKER, CLASSIFY_MARKER

_VALID_SEGMENTS = {s.value for s in Segment}
_VALID_ARCHETYPES = {a.value for a in Archetype}

# Production prompt text is proprietary and omitted from this public reference
# build. The minimal stub below preserves the input/output contract; the strict
# parsing and the quarantine-over-guess logic are the engineering on show.
_CLASSIFY_SYSTEM = (
    "Classify each business into one segment and one archetype, or abstain. "
    "Production prompt text is omitted from this reference build."
)


def format_prospect_line(idx: int, prospect: Prospect) -> str:
    """One machine- and model-readable line describing a prospect."""
    return (
        f"idx={idx}; name={prospect.name}; sic={prospect.sic or ''}; "
        f"city={prospect.city}; employees={prospect.employees or ''}; "
        f"website={prospect.website or ''}"
    )


def build_classification_prompt(prospects: Sequence[Prospect]) -> tuple[str, str]:
    """Build (system, user) for a batch classification call."""
    lines = "\n".join(format_prospect_line(i, p) for i, p in enumerate(prospects))
    user = (
        f"{CLASSIFY_MARKER}\n"
        f"Segments: {', '.join(sorted(_VALID_SEGMENTS))}\n"
        f"Archetypes: {', '.join(sorted(_VALID_ARCHETYPES))}\n\n"
        "For each prospect below, return a JSON array of objects with keys "
        "idx, segment, archetype, confidence (0-1), reason. Return one object "
        "per prospect, no prose.\n\n"
        f"{lines}"
    )
    return _CLASSIFY_SYSTEM, user


def parse_classification_response(
    text: str, expected_idxs: Sequence[int]
) -> dict[int, tuple[Segment, Archetype, float, str]] | None:
    """Parse a batch response, or return None if it is malformed or off-list.

    Returns None (so the caller marks the whole batch needs-retry) when the JSON
    is invalid, the count does not match, an idx is unexpected, or a label is not
    on the allowed list. An off-list answer is treated as the model being wrong,
    not coerced into a default.
    """
    try:
        parsed = json.loads(strip_code_fences(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    raw = cast("list[object]", parsed)
    if len(raw) != len(expected_idxs):
        return None

    expected = set(expected_idxs)
    out: dict[int, tuple[Segment, Archetype, float, str]] = {}
    for item in raw:
        if not isinstance(item, dict):
            return None
        row = cast("dict[str, object]", item)
        idx = row.get("idx")
        seg_val = row.get("segment")
        arch_val = row.get("archetype")
        confidence = row.get("confidence")
        if not isinstance(idx, int) or idx not in expected or idx in out:
            return None
        if seg_val not in _VALID_SEGMENTS or arch_val not in _VALID_ARCHETYPES:
            return None
        if not isinstance(confidence, int | float) or not 0.0 <= float(confidence) <= 1.0:
            return None
        reason = row.get("reason")
        # Membership in the str-only valid sets guarantees these are strings.
        out[idx] = (
            Segment(cast("str", seg_val)),
            Archetype(cast("str", arch_val)),
            float(confidence),
            reason if isinstance(reason, str) else "",
        )
    if set(out) != expected:
        return None
    return out


def build_angle_prompt(
    prospect: Prospect, classification: Classification, candidates: Sequence[str]
) -> tuple[str, str]:
    """Build (system, user) to pick one angle from a constrained candidate list."""
    # Production prompt text is proprietary and omitted; the constrained-candidate
    # contract and the strict parsing are what this reference build demonstrates.
    system = "Pick one angle from the candidate list. Production prompt text omitted."
    candidate_block = "\n".join(f"- {c}" for c in candidates)
    user = (
        f"{ANGLE_MARKER}\n"
        f"Business: {prospect.name} ({prospect.city}); "
        f"segment={classification.segment.value}; archetype={classification.archetype.value}\n\n"
        f"Candidates:\n{candidate_block}\n\n"
        'Return JSON {"angle_key": "<one candidate>", "reason": "<short>"}.'
    )
    return system, user


def parse_angle_response(text: str, candidates: Sequence[str]) -> str | None:
    """Return the chosen angle if it is one of the candidates, else None."""
    try:
        raw = json.loads(strip_code_fences(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    angle = cast("dict[str, object]", raw).get("angle_key")
    if isinstance(angle, str) and angle in set(candidates):
        return angle
    return None
