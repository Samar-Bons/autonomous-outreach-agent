# ABOUTME: A deterministic, rule-based LLMClient stub so the pipeline runs with zero tokens.
# ABOUTME: It reads the same prompt a real model would and returns structured JSON by keyword rules.
from __future__ import annotations

import json
import re

from ..domain.enums import ModelTier

# Markers the prompt builders embed so the stub can tell tasks apart. A real
# model ignores them; the stub branches on them.
CLASSIFY_MARKER = "TASK=classify_prospects"
ANGLE_MARKER = "TASK=pick_angle"

_IDX_LINE = re.compile(r"^\s*idx=(\d+);")
_CANDIDATE_LINE = re.compile(r"^\s*-\s*(\S+)")


def _rules(text: str) -> tuple[str, str, float]:
    """Map a prospect's text to (segment, archetype, confidence) by keyword rules.

    This is intentionally simple. It approximates what a real classifier decides
    and is good enough to drive the pipeline deterministically in tests.
    """
    t = text.lower()
    if any(k in t for k in ("nail", "salon", "bakery", "restaurant", "florist", "law office")):
        return ("out_of_scope", "out_of_scope", 0.95)
    if "mobile" in t:
        return ("passenger_lube", "mobile_mechanic", 0.9)
    if "unknown" in t or "name=;" in t:
        return ("out_of_scope", "unclear", 0.4)
    if any(k in t for k in ("euro", "bmw", "mercedes", "audi", "volkswagen", "porsche")):
        return ("passenger_lube", "euro_specialist", 0.9)
    if "hybrid" in t:
        return ("passenger_lube", "hybrid_specialist", 0.85)
    if "transmission" in t:
        return ("passenger_lube", "transmission_specialist", 0.85)
    if any(k in t for k in ("body", "collision", "paint")):
        return ("passenger_lube", "body_shop", 0.8)
    if "dealer" in t:
        return ("dealer_fleet", "independent_general", 0.85)
    if any(k in t for k in ("diesel", "truck", "fleet")):
        return ("hd_diesel", "hd_diesel", 0.9)
    if any(k in t for k in ("lube", "oil change", "quick", "express")):
        return ("passenger_lube", "lube_chain", 0.85)
    if any(k in t for k in ("auto", "automotive", "repair", "tire", "service center")):
        return ("passenger_lube", "independent_general", 0.7)
    return ("out_of_scope", "unclear", 0.4)


def _classify_response(user: str) -> str:
    results: list[dict[str, object]] = []
    for line in user.splitlines():
        m = _IDX_LINE.match(line)
        if not m:
            continue
        segment, archetype, confidence = _rules(line)
        results.append(
            {
                "idx": int(m.group(1)),
                "segment": segment,
                "archetype": archetype,
                "confidence": confidence,
                "reason": "stub rule match",
            }
        )
    return json.dumps(results)


def _angle_response(user: str) -> str:
    for line in user.splitlines():
        m = _CANDIDATE_LINE.match(line)
        if m:
            return json.dumps({"angle_key": m.group(1), "reason": "stub picked first candidate"})
    return json.dumps({"angle_key": "", "reason": "no candidates"})


class RuleBasedStubLLM:
    """LLMClient that returns deterministic JSON for known prompt tasks."""

    def complete(
        self,
        *,
        tier: ModelTier,
        system: str,
        user: str,
        max_tokens: int = 1024,
    ) -> str:
        if CLASSIFY_MARKER in user or CLASSIFY_MARKER in system:
            return _classify_response(user)
        if ANGLE_MARKER in user or ANGLE_MARKER in system:
            return _angle_response(user)
        return "{}"
