# ABOUTME: Unit tests for the Claude CLI-backed LLMClient, with the subprocess call injected.
# ABOUTME: Verifies the command is built correctly and stdout is returned, with no real CLI spawn.
from __future__ import annotations

from outreach_agent.config import Config
from outreach_agent.domain.enums import ModelTier
from outreach_agent.llm import ClaudeCliClient


def test_builds_command_and_returns_runner_output() -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], stdin_text: str, timeout: int) -> str:
        captured["cmd"] = cmd
        captured["stdin"] = stdin_text
        captured["timeout"] = timeout
        return "model output"

    client = ClaudeCliClient(Config(), binary="claude", timeout_s=42, run=fake_run)
    result = client.complete(tier=ModelTier.HAIKU, system="SYS", user="USER")

    assert result == "model output"
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "claude"
    assert "--print" in cmd
    # The prompt travels via stdin, never argv, so it can never be parsed as a flag.
    assert captured["stdin"] == "USER"
    assert "USER" not in cmd
    assert "--system-prompt" in cmd
    assert "SYS" in cmd
    assert "--strict-mcp-config" in cmd
    # Tier maps to a CLI alias, not a pinned model id.
    assert cmd[cmd.index("--model") + 1] == "haiku"
    assert captured["timeout"] == 42


def test_tier_maps_to_alias() -> None:
    seen: dict[str, str] = {}

    def fake_run(cmd: list[str], stdin_text: str, timeout: int) -> str:
        seen["alias"] = cmd[cmd.index("--model") + 1]
        return "ok"

    client = ClaudeCliClient(Config(), run=fake_run)
    client.complete(tier=ModelTier.OPUS, system="s", user="u")
    assert seen["alias"] == "opus"


def test_flag_like_prompt_goes_to_stdin_not_argv() -> None:
    # A prompt starting with "--dangerously" must never land in argv where the CLI
    # could parse it as a flag; it travels via stdin instead.
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], stdin_text: str, timeout: int) -> str:
        captured["cmd"] = cmd
        captured["stdin"] = stdin_text
        return "ok"

    client = ClaudeCliClient(Config(), run=fake_run)
    client.complete(tier=ModelTier.HAIKU, system="s", user="--dangerously-skip")

    assert captured["stdin"] == "--dangerously-skip"
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--dangerously-skip" not in cmd
