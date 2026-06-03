# ABOUTME: Public surface of the domain layer: enums, models, and the quarantine set.
# ABOUTME: Import domain types from here so call sites do not reach into submodules.
from .enums import (
    QUARANTINE_ARCHETYPES,
    Archetype,
    CheckSeverity,
    ModelTier,
    ReplyClassification,
    Segment,
    SendStatus,
    SuppressionReason,
    Wave,
)
from .models import (
    AngleSelection,
    CheckFailure,
    Classification,
    Draft,
    Prospect,
    Reply,
    ScheduledSend,
    SuppressionEntry,
    ValidationResult,
    normalize_email,
)

__all__ = [
    "QUARANTINE_ARCHETYPES",
    "AngleSelection",
    "Archetype",
    "CheckFailure",
    "CheckSeverity",
    "Classification",
    "Draft",
    "ModelTier",
    "Prospect",
    "Reply",
    "ReplyClassification",
    "ScheduledSend",
    "Segment",
    "SendStatus",
    "SuppressionEntry",
    "SuppressionReason",
    "ValidationResult",
    "Wave",
    "normalize_email",
]
