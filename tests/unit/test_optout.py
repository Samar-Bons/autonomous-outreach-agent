# ABOUTME: Unit tests for RegexOptOutDetector: true opt-outs caught, adversarial near-misses spared.
# ABOUTME: The "stop by anytime" cases prove a bare "stop" in prose never triggers an opt-out.
from __future__ import annotations

import pytest

from outreach_agent.domain import Reply
from outreach_agent.safety.optout import RegexOptOutDetector


def _reply(body: str) -> Reply:
    return Reply(thread_id="t1", from_email="owner@shop.com", subject="Re: oil", body=body)


@pytest.mark.parametrize(
    "body",
    [
        "stop",
        "Stop please",
        "unsubscribe",
        "please remove me",
        "take me off your list",
        "stop emailing me",
        "opt me out",
        "do not contact me again",
    ],
)
def test_true_opt_outs(body: str) -> None:
    assert RegexOptOutDetector().is_opt_out(_reply(body)) is True


@pytest.mark.parametrize(
    "body",
    [
        "stop by anytime!",
        "feel free to stop by the shop",
        "we offer non-stop service",
        "what's your pricing on bulk oil?",
        "can you send a quote for 50 gallons?",
        "thanks, talk soon",
    ],
)
def test_non_opt_outs(body: str) -> None:
    assert RegexOptOutDetector().is_opt_out(_reply(body)) is False
