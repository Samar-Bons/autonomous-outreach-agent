# ABOUTME: CI gate for eval #4: the LLM-as-judge angle-quality harness with a stub judge.
# ABOUTME: Confirms the harness runs end to end and the mean judged score clears the bar.
from __future__ import annotations

from .eval_angle_quality import run


def test_angle_quality_meets_threshold() -> None:
    metrics = run()  # all stub: deterministic

    assert metrics.count > 0
    assert metrics.mean_score >= 0.8
    assert metrics.min_score >= 0.0
    assert metrics.below_threshold == []
