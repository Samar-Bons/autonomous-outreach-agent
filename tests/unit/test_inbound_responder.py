# ABOUTME: Unit tests for the responder's deterministic guards, with a faked agent runner.
# ABOUTME: Covers opt-out short-circuit, price guard, name-drop allowlist, and parsing.
from __future__ import annotations

import json
from datetime import UTC, date, datetime

import pytest

from outreach_agent.domain import Reply
from outreach_agent.inbound import (
    DEFAULT_KNOWLEDGE_PATH,
    InboundResponder,
    InboundRoute,
    KnowledgeBase,
    mentions_price,
    parse_responder_json,
)
from outreach_agent.safety import InMemorySuppressionStore, RegexOptOutDetector
from outreach_agent.schedule import FixedClock


class _CannedRunner:
    def __init__(self, text: str) -> None:
        self._text = text

    async def run(self, reply: Reply) -> str:
        return self._text


class _RaisingRunner:
    async def run(self, reply: Reply) -> str:
        raise AssertionError("the agent must not be called on an opt-out")


def _clock() -> FixedClock:
    return FixedClock(date(2026, 4, 20), datetime(2026, 4, 20, 9, 0, tzinfo=UTC))


def _responder(runner: object, suppression: InMemorySuppressionStore) -> InboundResponder:
    return InboundResponder(
        opt_out_detector=RegexOptOutDetector(),
        suppression=suppression,
        knowledge=KnowledgeBase(DEFAULT_KNOWLEDGE_PATH),
        runner=runner,  # type: ignore[arg-type]
        clock=_clock(),
    )


def _reply(body: str, *, subject: str = "re: oil", email: str = "shop@acme.com") -> Reply:
    return Reply(thread_id="t1", from_email=email, subject=subject, body=body)


def _draft_json(**overrides: object) -> str:
    payload: dict[str, object] = {
        "route": "auto_draft",
        "category": "pricing",
        "draft_subject": "thanks for reaching out",
        "draft_body": "Happy to help. We will send a written quote within a business day.",
        "name_drops_used": [],
        "reason": "grounded answer",
    }
    payload.update(overrides)
    return json.dumps(payload)


async def test_opt_out_short_circuits_before_the_agent() -> None:
    suppression = InMemorySuppressionStore()
    responder = _responder(_RaisingRunner(), suppression)
    result = await responder.respond(_reply("please unsubscribe me"))
    assert result.route is InboundRoute.OPT_OUT
    assert suppression.is_suppressed("shop@acme.com")


async def test_clean_auto_draft_passes() -> None:
    responder = _responder(_CannedRunner(_draft_json()), InMemorySuppressionStore())
    result = await responder.respond(_reply("what oils do you carry?"))
    assert result.route is InboundRoute.AUTO_DRAFT
    assert "quote" in result.draft_body.lower()


async def test_price_in_draft_is_escalated() -> None:
    runner = _CannedRunner(_draft_json(draft_body="Sure, it is $5 per gallon delivered."))
    responder = _responder(runner, InMemorySuppressionStore())
    result = await responder.respond(_reply("how much is bulk oil?"))
    assert result.route is InboundRoute.ESCALATE
    assert "price" in result.reason.lower()


async def test_invented_name_drop_is_escalated() -> None:
    runner = _CannedRunner(_draft_json(name_drops_used=["Totally Fake Shop"]))
    responder = _responder(runner, InMemorySuppressionStore())
    result = await responder.respond(_reply("who else do you supply?"))
    assert result.route is InboundRoute.ESCALATE


async def test_allowlisted_name_drop_passes() -> None:
    runner = _CannedRunner(_draft_json(name_drops_used=["Maple Ridge Auto"]))
    responder = _responder(runner, InMemorySuppressionStore())
    result = await responder.respond(_reply("any references near Plano?"))
    assert result.route is InboundRoute.AUTO_DRAFT


async def test_malformed_agent_output_is_escalated() -> None:
    responder = _responder(_CannedRunner("not json at all"), InMemorySuppressionStore())
    result = await responder.respond(_reply("hello"))
    assert result.route is InboundRoute.ESCALATE


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("it is $5 a gallon", True),
        ("about 12 dollars", True),
        ("roughly 4.50 per gallon", True),
        ("we will send a written quote", False),
        ("next-day delivery across the metro", False),
    ],
)
def test_mentions_price(text: str, expected: bool) -> None:
    assert mentions_price(text) is expected


def test_parse_rejects_bad_route() -> None:
    assert parse_responder_json(json.dumps({"route": "send_it"})) is None


def test_parse_accepts_fenced_json() -> None:
    fenced = "```json\n" + _draft_json() + "\n```"
    result = parse_responder_json(fenced)
    assert result is not None
    assert result.route is InboundRoute.AUTO_DRAFT
