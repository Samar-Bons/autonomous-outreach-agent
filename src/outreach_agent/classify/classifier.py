# ABOUTME: The LLM classifier: batched, order-preserving, and biased toward abstaining.
# ABOUTME: Parse failures split the batch and ultimately yield NEEDS_RETRY, never a guessed label.
from __future__ import annotations

from collections.abc import Sequence

from ..domain import Classification, Prospect
from ..domain.enums import Archetype, ModelTier, Segment
from ..protocols import LLMClient
from .prompts import build_classification_prompt, parse_classification_response


def _needs_retry(prospect: Prospect) -> Classification:
    """Result for a prospect the model failed to classify (not a decision)."""
    return Classification(
        prospect_id=prospect.id,
        segment=Segment.OUT_OF_SCOPE,
        archetype=Archetype.NEEDS_RETRY,
        confidence=0.0,
        reason="classification failed; queued for retry",
    )


class LLMClassifier:
    """Assigns segment + archetype in batches, abstaining on failure.

    On a malformed or off-list batch response the batch is split in half and each
    half retried. A single prospect that still fails becomes NEEDS_RETRY. No
    prospect is ever assigned a fabricated label.
    """

    def __init__(self, llm: LLMClient, *, batch_size: int = 10) -> None:
        self._llm = llm
        self._batch_size = max(1, batch_size)

    def classify(self, prospects: Sequence[Prospect]) -> list[Classification]:
        results: list[Classification] = []
        for start in range(0, len(prospects), self._batch_size):
            chunk = prospects[start : start + self._batch_size]
            results.extend(self._classify_chunk(chunk))
        return results

    def _classify_chunk(self, chunk: Sequence[Prospect]) -> list[Classification]:
        if not chunk:
            return []
        system, user = build_classification_prompt(chunk)
        text = self._llm.complete(tier=ModelTier.HAIKU, system=system, user=user)
        parsed = parse_classification_response(text, range(len(chunk)))

        if parsed is None:
            if len(chunk) == 1:
                return [_needs_retry(chunk[0])]
            mid = len(chunk) // 2
            return self._classify_chunk(chunk[:mid]) + self._classify_chunk(chunk[mid:])

        out: list[Classification] = []
        for i, prospect in enumerate(chunk):
            segment, archetype, confidence, reason = parsed[i]
            out.append(
                Classification(
                    prospect_id=prospect.id,
                    segment=segment,
                    archetype=archetype,
                    confidence=confidence,
                    reason=reason,
                )
            )
        return out
