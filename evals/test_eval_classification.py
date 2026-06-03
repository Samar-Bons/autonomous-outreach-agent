# ABOUTME: CI gate for the classification eval: runs the stub and asserts the safety thresholds.
# ABOUTME: Pitch precision and quarantine recall must be perfect; archetype accuracy above a floor.
from __future__ import annotations

from .eval_classification import run


def test_classification_eval_meets_safety_thresholds() -> None:
    metrics = run()  # stub LLM, deterministic

    # Safety-critical: never pitch a truly out-of-scope shop, never miss a
    # truly-quarantine shop.
    assert metrics.pitch_precision == 1.0
    assert metrics.quarantine_recall == 1.0

    # Quality floor on exact archetype match.
    assert metrics.archetype_accuracy >= 0.85
    assert metrics.total == 16
    assert metrics.needs_retry == 0
