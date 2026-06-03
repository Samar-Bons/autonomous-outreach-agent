# ABOUTME: Renders a Markdown operator report with a traffic-light status from the bounce rate.
# ABOUTME: Pure and deterministic: identical counts render identical reports, no clock or network.
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# Bounce-rate band edges. A rate below GREEN_MAX is healthy; below YELLOW_MAX is
# a warning; at or above YELLOW_MAX the campaign is in the red.
_GREEN_MAX = 0.015
_YELLOW_MAX = 0.03


class StatusTier(StrEnum):
    """The operator-facing health tier, surfaced as a traffic-light emoji."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

    @property
    def emoji(self) -> str:
        """The traffic-light glyph for this tier."""
        return {
            StatusTier.GREEN: "\U0001f7e2",
            StatusTier.YELLOW: "\U0001f7e1",
            StatusTier.RED: "\U0001f534",
        }[self]


def tier_for_bounce_rate(bounce_rate: float) -> StatusTier:
    """Map a bounce rate onto a status tier: <1.5% green, <3% yellow, else red."""
    if bounce_rate < _GREEN_MAX:
        return StatusTier.GREEN
    if bounce_rate < _YELLOW_MAX:
        return StatusTier.YELLOW
    return StatusTier.RED


class DailyReport(BaseModel):
    """A frozen snapshot of one day's outreach counts plus its health tier."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sent: int = Field(ge=0)
    bounced: int = Field(ge=0)
    opt_outs: int = Field(ge=0)
    scheduled_ahead: int = Field(ge=0)
    tier: StatusTier

    @property
    def bounce_rate(self) -> float:
        """Bounces as a fraction of sends; zero when nothing was sent."""
        return self.bounced / self.sent if self.sent else 0.0

    @classmethod
    def from_counts(
        cls,
        *,
        sent: int,
        bounced: int,
        opt_outs: int,
        scheduled_ahead: int,
    ) -> DailyReport:
        """Build a report, deriving the status tier from the bounce rate."""
        rate = bounced / sent if sent else 0.0
        return cls(
            sent=sent,
            bounced=bounced,
            opt_outs=opt_outs,
            scheduled_ahead=scheduled_ahead,
            tier=tier_for_bounce_rate(rate),
        )

    def render(self) -> str:
        """Render the report as a short Markdown block for the operator channel."""
        lines = [
            f"## {self.tier.emoji} Outreach daily report",
            "",
            f"- **Status:** {self.tier.value}",
            f"- **Sent:** {self.sent}",
            f"- **Bounced:** {self.bounced} ({self.bounce_rate:.2%})",
            f"- **Opt-outs:** {self.opt_outs}",
            f"- **Scheduled ahead:** {self.scheduled_ahead}",
        ]
        return "\n".join(lines)
