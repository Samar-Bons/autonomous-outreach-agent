# ABOUTME: Runtime configuration: model IDs per tier, campaign name, paths, warmup caps.
# ABOUTME: Values come from the environment with sane defaults; nothing secret lives here.
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .domain.enums import ModelTier

_DEFAULT_MODELS: dict[ModelTier, str] = {
    ModelTier.OPUS: "claude-opus-4-7",
    ModelTier.SONNET: "claude-sonnet-4-6",
    ModelTier.HAIKU: "claude-haiku-4-5",
}

# Per-UTC-date send ceilings. The campaign ramps volume to protect domain
# reputation, then holds steady. Weekends are intentionally zero.
DEFAULT_WARMUP_CAPS: tuple[int, ...] = (50, 100, 200, 400, 500)
STEADY_STATE_CAP: int = 500

# Days after the initial send that each follow-up wave goes out.
WAVE_OFFSET_DAYS: dict[int, int] = {1: 0, 2: 3, 3: 7, 4: 14}


@dataclass(frozen=True)
class Config:
    """Resolved configuration for a pipeline run."""

    campaign: str = "northwind-outbound-2026"
    db_path: str = "outreach.db"
    models: dict[ModelTier, str] = field(default_factory=lambda: dict(_DEFAULT_MODELS))
    daily_cap: int = STEADY_STATE_CAP

    def model_id(self, tier: ModelTier) -> str:
        """The concrete model string to send to the API for a given tier."""
        return self.models[tier]


def load_config() -> Config:
    """Build a Config from environment variables, falling back to defaults."""
    models = dict(_DEFAULT_MODELS)
    for tier, env_key in (
        (ModelTier.OPUS, "OUTREACH_MODEL_OPUS"),
        (ModelTier.SONNET, "OUTREACH_MODEL_SONNET"),
        (ModelTier.HAIKU, "OUTREACH_MODEL_HAIKU"),
    ):
        override = os.environ.get(env_key)
        if override:
            models[tier] = override
    return Config(
        db_path=os.environ.get("OUTREACH_DB_PATH", "outreach.db"),
        models=models,
    )
