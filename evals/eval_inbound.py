# ABOUTME: Eval #5: the responder's deterministic guarantees (opt-out routing + output guards).
# ABOUTME: Runs in CI with a faked agent runner; --live drives the real Agent SDK responder.
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from outreach_agent.domain import Reply
from outreach_agent.inbound import (
    DEFAULT_KNOWLEDGE_PATH,
    InboundResponder,
    InboundRoute,
    KnowledgeBase,
)
from outreach_agent.safety import InMemorySuppressionStore, RegexOptOutDetector
from outreach_agent.schedule import FixedClock

GOLDEN_PATH = Path(__file__).parent / "golden" / "inbound.jsonl"

_CLEAN_DRAFT = json.dumps(
    {
        "route": "auto_draft",
        "category": "question",
        "draft_subject": "thanks for reaching out",
        "draft_body": "Happy to help. We will send a written quote within a business day.",
        "name_drops_used": [],
        "reason": "grounded answer",
    }
)
_PRICE_DRAFT = json.dumps(
    {
        "route": "auto_draft",
        "draft_subject": "quote",
        "draft_body": "Bulk diesel oil is $4.50 per gallon delivered.",
        "name_drops_used": [],
        "reason": "answered pricing",
    }
)
_FAKE_NAME_DRAFT = json.dumps(
    {
        "route": "auto_draft",
        "draft_subject": "references",
        "draft_body": "We supply lots of shops in your area.",
        "name_drops_used": ["Totally Fake Shop"],
        "reason": "social proof",
    }
)


class _CannedRunner:
    def __init__(self, text: str) -> None:
        self._text = text

    async def run(self, reply: Reply) -> str:
        return self._text


@dataclass(frozen=True)
class InboundEvalMetrics:
    """Deterministic-guarantee scores for the inbound responder."""

    total: int
    optout_recall: float
    optout_false_positives: int
    guards_passed: int
    guards_total: int


def _clock() -> FixedClock:
    return FixedClock(date(2026, 4, 20), datetime(2026, 4, 20, 9, 0, tzinfo=UTC))


def _responder(runner: _CannedRunner, suppression: InMemorySuppressionStore) -> InboundResponder:
    return InboundResponder(
        opt_out_detector=RegexOptOutDetector(),
        suppression=suppression,
        knowledge=KnowledgeBase(DEFAULT_KNOWLEDGE_PATH),
        runner=runner,
        clock=_clock(),
    )


async def _route(runner: _CannedRunner, reply: Reply) -> InboundRoute:
    result = await _responder(runner, InMemorySuppressionStore()).respond(reply)
    return result.route


async def run() -> InboundEvalMetrics:
    """Score opt-out routing and the output guards with a faked agent runner."""
    rows = [json.loads(line) for line in GOLDEN_PATH.read_text().splitlines() if line.strip()]
    clean = _CannedRunner(_CLEAN_DRAFT)

    true_opt = caught = false_pos = 0
    for row in rows:
        reply = Reply(
            thread_id=str(row["thread_id"]),
            from_email=str(row["from_email"]),
            subject=str(row["subject"]),
            body=str(row["body"]),
        )
        route = await _route(clean, reply)
        if row["is_opt_out"]:
            true_opt += 1
            if route is InboundRoute.OPT_OUT:
                caught += 1
        elif route is InboundRoute.OPT_OUT:
            false_pos += 1

    # Output guards: a priced draft and an invented name-drop must both escalate.
    guard_reply = Reply(thread_id="g", from_email="g@x.com", subject="q", body="how much?")
    guards = [
        await _route(_CannedRunner(_PRICE_DRAFT), guard_reply) is InboundRoute.ESCALATE,
        await _route(_CannedRunner(_FAKE_NAME_DRAFT), guard_reply) is InboundRoute.ESCALATE,
    ]

    return InboundEvalMetrics(
        total=len(rows),
        optout_recall=caught / true_opt if true_opt else 1.0,
        optout_false_positives=false_pos,
        guards_passed=sum(guards),
        guards_total=len(guards),
    )


def to_markdown(metrics: InboundEvalMetrics) -> str:
    """Render inbound-responder guarantee metrics as Markdown."""
    return (
        "# Inbound responder eval (deterministic guarantees)\n\n"
        f"- replies: {metrics.total}\n"
        f"- opt-out recall (safety): {metrics.optout_recall:.3f}\n"
        f"- opt-out false positives: {metrics.optout_false_positives}\n"
        f"- output guards passed: {metrics.guards_passed}/{metrics.guards_total}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the inbound responder eval.")
    parser.parse_args()
    print(to_markdown(asyncio.run(run())))


if __name__ == "__main__":
    main()
