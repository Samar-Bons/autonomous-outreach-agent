# ABOUTME: The angle picker: constrains the choice to the archetype's vetted shortlist.
# ABOUTME: One candidate is chosen with no model call; several go to the model with a safe fallback.
from __future__ import annotations

from ..domain import AngleSelection, Classification, Prospect
from ..domain.enums import ModelTier
from ..protocols import LLMClient
from .angles import candidate_angles
from .prompts import build_angle_prompt, parse_angle_response


class ConstrainedAnglePicker:
    """Picks one angle from the candidate set, or None to drop the prospect.

    Quarantined prospects and prospects with no candidate angle return None. A
    single candidate is chosen deterministically with no model call. With several
    candidates the model chooses; if it fails, the first candidate is used. That
    fallback is safe because every candidate is pre-vetted for the archetype, so
    unlike classification there is no wrong answer to guess.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def pick(self, prospect: Prospect, classification: Classification) -> AngleSelection | None:
        if classification.is_quarantined:
            return None
        candidates = candidate_angles(classification.segment, classification.archetype)
        if not candidates:
            return None
        if len(candidates) == 1:
            return AngleSelection(
                prospect_id=prospect.id,
                angle_key=candidates[0],
                candidates=candidates,
                reason="single candidate",
            )

        system, user = build_angle_prompt(prospect, classification, candidates)
        text = self._llm.complete(tier=ModelTier.HAIKU, system=system, user=user)
        chosen = parse_angle_response(text, candidates)
        if chosen is None:
            return AngleSelection(
                prospect_id=prospect.id,
                angle_key=candidates[0],
                candidates=candidates,
                reason="fallback: first candidate after pick failure",
            )
        return AngleSelection(
            prospect_id=prospect.id,
            angle_key=chosen,
            candidates=candidates,
            reason="model pick",
        )
