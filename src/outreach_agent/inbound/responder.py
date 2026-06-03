# ABOUTME: The inbound responder: deterministic guards around an agent that drafts replies.
# ABOUTME: Opt-outs short-circuit before the model; price and name-drop guards police its output.
from __future__ import annotations

import json
import re
from typing import Protocol, cast

from ..domain import Reply, SuppressionEntry
from ..domain.enums import SuppressionReason
from ..llm import strip_code_fences
from ..protocols import Clock, OptOutDetector, SuppressionStore
from .knowledge import KnowledgeBase
from .models import InboundRoute, ResponderResult

_PRICE = re.compile(
    r"\$\s?\d|\b\d+(?:\.\d+)?\s*(?:dollars|per gallon|/gal|a gallon)\b", re.IGNORECASE
)


class AgentRunner(Protocol):
    """Runs the grounded drafting agent for one reply and returns its raw JSON."""

    async def run(self, reply: Reply) -> str: ...


def mentions_price(text: str) -> bool:
    """True if the text appears to quote a price. The responder never may."""
    return bool(_PRICE.search(text))


def parse_responder_json(text: str) -> ResponderResult | None:
    """Parse the agent's JSON into a ResponderResult, or None if malformed."""
    body = strip_code_fences(text)
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    obj = cast("dict[str, object]", parsed)
    route_value = obj.get("route")
    if not isinstance(route_value, str) or route_value not in {r.value for r in InboundRoute}:
        return None
    name_drops_raw = obj.get("name_drops_used", [])
    name_drops: tuple[str, ...] = ()
    if isinstance(name_drops_raw, list):
        name_drops = tuple(str(n) for n in cast("list[object]", name_drops_raw))

    def _str(key: str) -> str:
        value = obj.get(key)
        return value if isinstance(value, str) else ""

    return ResponderResult(
        route=InboundRoute(route_value),
        category=_str("category"),
        draft_subject=_str("draft_subject"),
        draft_body=_str("draft_body"),
        name_drops_used=name_drops,
        reason=_str("reason"),
    )


def _escalate(reason: str) -> ResponderResult:
    return ResponderResult(route=InboundRoute.ESCALATE, reason=reason)


class InboundResponder:
    """Drafts grounded replies, with deterministic guards the model cannot override.

    The flow: a deterministic opt-out check runs first and short-circuits before
    any model call. Otherwise the agent drafts a reply, and two guards police the
    output: a draft that quotes a price or names a customer not on the allowlist
    is downgraded to ESCALATE rather than trusted. Every result is a draft; this
    class never sends.
    """

    def __init__(
        self,
        *,
        opt_out_detector: OptOutDetector,
        suppression: SuppressionStore,
        knowledge: KnowledgeBase,
        runner: AgentRunner,
        clock: Clock,
        source: str = "inbound",
    ) -> None:
        self._detector = opt_out_detector
        self._suppression = suppression
        self._knowledge = knowledge
        self._runner = runner
        self._clock = clock
        self._source = source

    async def respond(self, reply: Reply) -> ResponderResult:
        # Deterministic guarantee: opt-outs never reach the model.
        if self._detector.is_opt_out(reply):
            self._suppression.add(
                SuppressionEntry(
                    email=reply.from_email,
                    reason=SuppressionReason.OPT_OUT,
                    source=self._source,
                    added_at=self._clock.now(),
                )
            )
            return ResponderResult(
                route=InboundRoute.OPT_OUT,
                category="opt_out",
                reason="deterministic opt-out match",
            )

        result = parse_responder_json(await self._runner.run(reply))
        if result is None:
            return _escalate("agent output was not valid JSON")

        if result.route is InboundRoute.AUTO_DRAFT:
            if mentions_price(result.draft_body) or mentions_price(result.draft_subject):
                return _escalate("draft quoted a price")
            # Trust the draft text, not the model's self-report. Escalate on any
            # declared reference outside the allowlist, and on any allowlisted
            # customer that appears in the draft without being declared (an
            # evasive under-report). A wholly fabricated name in free prose is
            # caught at human approval, not by this guard.
            allowed = self._knowledge.customer_names()
            declared = set(result.name_drops_used)
            text = f"{result.draft_subject}\n{result.draft_body}".lower()
            off_list = sorted(declared - allowed)
            if off_list:
                return _escalate(f"draft declared non-allowlisted customers: {off_list}")
            undeclared = sorted(n for n in allowed if n.lower() in text and n not in declared)
            if undeclared:
                return _escalate(f"draft references undeclared customers: {undeclared}")
        return result
