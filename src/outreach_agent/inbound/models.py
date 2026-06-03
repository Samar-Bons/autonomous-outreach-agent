# ABOUTME: Domain types for the inbound responder: the route taxonomy and the result shape.
# ABOUTME: A ResponderResult is always a DRAFT; nothing here ever sends an email.
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class InboundRoute(StrEnum):
    """What the responder decided to do with an inbound reply."""

    AUTO_DRAFT = "auto_draft"  # a grounded draft, pending human approval
    ESCALATE = "escalate"  # hand to a human (uncertain, or a guard tripped)
    OPT_OUT = "opt_out"  # suppress; never contact again
    BOUNCE = "bounce"  # delivery failure
    NOISE = "noise"  # auto-reply / not a real reply


class ResponderResult(BaseModel):
    """The responder's decision for one reply. Always a draft, never a send."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    route: InboundRoute
    category: str = ""
    draft_subject: str = ""
    draft_body: str = ""
    name_drops_used: tuple[str, ...] = ()
    reason: str = ""
