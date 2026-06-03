# ABOUTME: Public surface of the safety layer: the draft gate, opt-out detection, suppression.
# ABOUTME: These deterministic guardrails are the guarantees that never depend on the model.
from .checks import (
    AiSlopCheck,
    ForbiddenBrandCheck,
    GenericAddressCheck,
    MergeFieldLeakCheck,
    SpamMarkerCheck,
)
from .gate import DefaultSafetyGate, default_checks, default_gate
from .optout import RegexOptOutDetector
from .suppression import InMemorySuppressionStore, SqliteSuppressionStore

__all__ = [
    "AiSlopCheck",
    "DefaultSafetyGate",
    "ForbiddenBrandCheck",
    "GenericAddressCheck",
    "InMemorySuppressionStore",
    "MergeFieldLeakCheck",
    "RegexOptOutDetector",
    "SpamMarkerCheck",
    "SqliteSuppressionStore",
    "default_checks",
    "default_gate",
]
