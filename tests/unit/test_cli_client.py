# ABOUTME: Unit tests for the Claude CLI-backed LLMClient, with the subprocess call injected.
# ABOUTME: Verifies the command is built correctly and stdout is returned, with no real CLI spawn.
from __future__ import annotations

from outreach_agent.config import Config
from outreach_agent.domain.enums import ModelTier
from outreach_agent.llm import ClaudeCliClient


def test_builds_command_and_returns_runner_output() -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], timeout: int) -> str:
        captured["cmd"] = cmd
        captured["timeout"] = timeout
        return "model output"

    client = ClaudeCliClient(Config(), binary="claude", timeout_s=42, run=fake_run)
    result = client.complete(tier=ModelTier.HAIKU, system="SYS", user="USER")

    assert result == "model output"
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "claude"
    assert "--print" in cmd
    assert "USER" in cmd
    assert "--system-prompt" in cmd
    assert "SYS" in cmd
    assert "--strict-mcp-config" in cmd
    # Tier maps to a CLI alias, not a pinned model id.
    assert cmd[cmd.index("--model") + 1] == "haiku"
    assert captured["timeout"] == 42


def test_tier_maps_to_alias() -> None:
    seen: dict[str, str] = {}

    def fake_run(cmd: list[str], timeout: int) -> str:
        seen["alias"] = cmd[cmd.index("--model") + 1]
        return "ok"

    client = ClaudeCliClient(Config(), run=fake_run)
    client.complete(tier=ModelTier.OPUS, system="s", user="u")
    assert seen["alias"] == "opus"
