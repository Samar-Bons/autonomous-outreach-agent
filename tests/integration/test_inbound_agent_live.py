# ABOUTME: Live integration test for the real Agent SDK responder. Skipped without an API key.
# ABOUTME: Confirms the agent loop runs and the never-quote-a-price guarantee holds end to end.
from __future__ import annotations

import os

import pytest

pytest.importorskip("claude_agent_sdk")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="requires ANTHROPIC_API_KEY"),
]


async def test_live_responder_never_quotes_a_price() -> None:
    from outreach_agent.config import load_config
    from outreach_agent.domain import Reply
    from outreach_agent.inbound import DEFAULT_KNOWLEDGE_PATH, InboundRoute, KnowledgeBase
    from outreach_agent.inbound.agent import build_responder
    from outreach_agent.safety import InMemorySuppressionStore, RegexOptOutDetector
    from outreach_agent.schedule import SystemClock

    responder = build_responder(
        config=load_config(),
        knowledge=KnowledgeBase(DEFAULT_KNOWLEDGE_PATH),
        suppression=InMemorySuppressionStore(),
        opt_out_detector=RegexOptOutDetector(),
        clock=SystemClock(),
    )
    reply = Reply(
        thread_id="t1",
        from_email="prospect@example.com",
        subject="pricing",
        body="What does bulk diesel oil cost per gallon delivered?",
    )
    result = await responder.respond(reply)

    # The agent must never quote a price: it either drafts without one or escalates.
    assert result.route in {InboundRoute.AUTO_DRAFT, InboundRoute.ESCALATE}
    assert "$" not in result.draft_body
