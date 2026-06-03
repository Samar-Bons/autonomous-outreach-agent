# ABOUTME: Unit tests for the real LLMClient adapter, with no network calls.
# ABOUTME: Verifies tier->model selection and text extraction from a response.
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from anthropic import Anthropic
from anthropic.types import TextBlock

from outreach_agent.config import Config
from outreach_agent.domain.enums import ModelTier
from outreach_agent.llm.anthropic_client import AnthropicClient, extract_text


def test_extract_text_joins_text_blocks() -> None:
    blocks = [TextBlock(type="text", text="a"), TextBlock(type="text", text="b")]
    assert extract_text(blocks) == "ab"


def test_extract_text_ignores_non_text_blocks() -> None:
    blocks = [TextBlock(type="text", text="a"), SimpleNamespace(type="tool_use")]
    assert extract_text(cast(Any, blocks)) == "a"


def test_extract_text_empty() -> None:
    assert extract_text([]) == ""


class _FakeMessages:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return SimpleNamespace(content=[TextBlock(type="text", text="ok")])


class _FakeAnthropic:
    def __init__(self) -> None:
        self.messages = _FakeMessages()


def test_adapter_selects_model_by_tier_and_returns_text() -> None:
    fake = _FakeAnthropic()
    config = Config()
    client = AnthropicClient(config, client=cast(Anthropic, fake))

    result = client.complete(tier=ModelTier.HAIKU, system="s", user="u", max_tokens=64)

    assert result == "ok"
    assert fake.messages.kwargs["model"] == config.model_id(ModelTier.HAIKU)
    assert fake.messages.kwargs["max_tokens"] == 64
    assert fake.messages.kwargs["system"] == "s"
