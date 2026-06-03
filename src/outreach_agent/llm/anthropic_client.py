# ABOUTME: The real LLMClient: a thin adapter over the Anthropic SDK, selected by tier.
# ABOUTME: Text extraction is a pure function so the adapter is unit-tested without a network.
from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from anthropic import Anthropic
from anthropic.types import TextBlock

from ..config import Config
from ..domain.enums import ModelTier

if TYPE_CHECKING:
    from anthropic.types import ContentBlock


def extract_text(blocks: Iterable[ContentBlock]) -> str:
    """Concatenate the text blocks of a model response, ignoring non-text blocks."""
    return "".join(block.text for block in blocks if isinstance(block, TextBlock))


class AnthropicClient:
    """LLMClient backed by the Anthropic API. Model id is chosen per tier."""

    def __init__(self, config: Config, *, client: Anthropic | None = None) -> None:
        self._config = config
        self._client = client or Anthropic()

    def complete(
        self,
        *,
        tier: ModelTier,
        system: str,
        user: str,
        max_tokens: int = 1024,
    ) -> str:
        message = self._client.messages.create(
            model=self._config.model_id(tier),
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return extract_text(message.content)
