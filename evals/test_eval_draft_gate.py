# ABOUTME: CI gate for the draft-safety eval: every planted violation caught, no false positives.
# ABOUTME: The deterministic gate must be perfect on its labeled corpus, with no LLM in the loop.
from __future__ import annotations

from .eval_draft_gate import run


def test_draft_gate_eval_is_perfect() -> None:
    metrics = run()

    # Every planted violation must be caught by its expected check.
    assert metrics.detection_rate == 1.0
    # No clean draft may draw a BLOCK.
    assert metrics.false_positive_count == 0
    assert metrics.misses == ()

    # Corpus shape sanity.
    assert metrics.total == metrics.planted + metrics.clean
    assert metrics.planted > 0
    assert metrics.clean > 0
