# ABOUTME: An LLMClient that runs inference through the Claude CLI in print mode.
# ABOUTME: Bills against a Claude subscription instead of a metered API key; no network code here.
from __future__ import annotations

import subprocess
from collections.abc import Callable

from ..config import Config
from ..domain.enums import ModelTier

# The CLI resolves these aliases to the current model in each tier, so the client
# does not pin a model id that can go stale.
_TIER_ALIAS: dict[ModelTier, str] = {
    ModelTier.OPUS: "opus",
    ModelTier.SONNET: "sonnet",
    ModelTier.HAIKU: "haiku",
}

# Returns the process stdout for a command, given stdin text and a timeout. Injected for tests.
RunFn = Callable[[list[str], str, int], str]


def _subprocess_run(cmd: list[str], stdin_text: str, timeout_s: int) -> str:
    # No ANTHROPIC_API_KEY is passed, so the CLI uses the logged-in subscription.
    result = subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return result.stdout.strip()


class ClaudeCliClient:
    """LLMClient backed by `claude --print`. Same seam as the API client.

    Inference runs through the local Claude CLI, which authenticates against a
    logged-in subscription. This mirrors how the original production system did
    inference and lets anyone with a subscription run the live evals without a
    metered API key. The subprocess call is injected so it is unit-testable
    without spawning the CLI.
    """

    def __init__(
        self,
        config: Config,
        *,
        binary: str = "claude",
        timeout_s: int = 120,
        run: RunFn = _subprocess_run,
    ) -> None:
        self._config = config
        self._binary = binary
        self._timeout_s = timeout_s
        self._run = run

    def complete(
        self,
        *,
        tier: ModelTier,
        system: str,
        user: str,
        max_tokens: int = 1024,
    ) -> str:
        cmd = [
            self._binary,
            "--print",
            "--model",
            _TIER_ALIAS[tier],
            "--system-prompt",
            system,
            "--strict-mcp-config",
        ]
        # The prompt travels via stdin, never argv, so untrusted text starting with
        # ``-`` can never be parsed as a flag (argv flag-injection).
        return self._run(cmd, user, self._timeout_s)
