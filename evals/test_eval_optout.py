# ABOUTME: CI gate for the opt-out eval: recall must be perfect, precision high, near-misses spared.
# ABOUTME: Missing a true opt-out is a CAN-SPAM violation, so the recall assertion is mandatory.
from __future__ import annotations

from outreach_agent.domain import Reply
from outreach_agent.safety.optout import RegexOptOutDetector

from .eval_optout import run


def test_optout_eval_meets_safety_thresholds() -> None:
    metrics = run()

    # Safety-critical: NEVER miss a true opt-out. A single false negative is a
    # CAN-SPAM violation, so recall must be exactly perfect.
    assert metrics.recall == 1.0

    # Quality floor: do not over-suppress real prospects.
    assert metrics.precision >= 0.9


def test_stop_by_anytime_is_not_opt_out() -> None:
    reply = Reply(
        thread_id="t1", from_email="owner@shop.com", subject="Re: oil", body="stop by anytime"
    )
    assert RegexOptOutDetector().is_opt_out(reply) is False
