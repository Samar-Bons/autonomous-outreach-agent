# ABOUTME: Closed vocabularies for the pipeline: segments, archetypes, waves, routes, statuses.
# ABOUTME: These enums are the shared contract between the LLM stages and the deterministic code.
from __future__ import annotations

from enum import IntEnum, StrEnum


class Segment(StrEnum):
    """Top-level product taxonomy a prospect is routed into."""

    PASSENGER_LUBE = "passenger_lube"
    HD_DIESEL = "hd_diesel"
    DEALER_FLEET = "dealer_fleet"
    OUT_OF_SCOPE = "out_of_scope"


class Archetype(StrEnum):
    """Finer classification used only to select a pitch angle.

    The four members in ``QUARANTINE_ARCHETYPES`` never receive an email.
    ``NEEDS_RETRY`` is distinct from ``UNCLEAR``: it marks a model *failure*
    (timeout, malformed output) to retry, not a model *decision* that the shop
    is ambiguous. Collapsing those two is how pipelines silently drop leads.
    """

    EURO_SPECIALIST = "euro_specialist"
    HYBRID_SPECIALIST = "hybrid_specialist"
    LUBE_CHAIN = "lube_chain"
    TRANSMISSION_SPECIALIST = "transmission_specialist"
    BODY_SHOP = "body_shop"
    HD_DIESEL = "hd_diesel"
    INDEPENDENT_GENERAL = "independent_general"
    MOBILE_MECHANIC = "mobile_mechanic"
    OUT_OF_SCOPE = "out_of_scope"
    UNCLEAR = "unclear"
    NEEDS_RETRY = "needs_retry"


# Archetypes that are never pitched. "Quarantine over guess": when the system
# is not confident a shop is a real, in-scope buyer, it abstains rather than
# sending the wrong email to a stranger.
QUARANTINE_ARCHETYPES: frozenset[Archetype] = frozenset(
    {
        Archetype.MOBILE_MECHANIC,
        Archetype.OUT_OF_SCOPE,
        Archetype.UNCLEAR,
        Archetype.NEEDS_RETRY,
    }
)


class Wave(IntEnum):
    """Multi-touch sequence position. Offsets (in days) are defined in scheduling."""

    INITIAL = 1
    BUMP = 2
    PIVOT = 3
    BREAKUP = 4


class ReplyClassification(StrEnum):
    """How an inbound reply is triaged."""

    OPT_OUT = "opt_out"
    BOUNCE = "bounce"
    PROSPECT_REPLY = "prospect_reply"
    NOISE = "noise"
    URGENT = "urgent"


class SuppressionReason(StrEnum):
    """Why an address is on the do-not-send list."""

    OPT_OUT = "opt_out"
    BOUNCE = "bounce"
    REPLIED = "replied"
    MANUAL = "manual"


class SendStatus(StrEnum):
    """Lifecycle of a scheduled send. Cancellations are marked, never deleted."""

    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CheckSeverity(StrEnum):
    """Severity of a safety-gate finding. Any BLOCK finding quarantines a draft."""

    BLOCK = "block"
    WARN = "warn"


class ModelTier(StrEnum):
    """Model selection by task criticality, not by raw size.

    Cheap, high-volume reasoning runs on HAIKU; the most expensive model guards
    the last gate before a send goes out.
    """

    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"
