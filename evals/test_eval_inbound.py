# ABOUTME: CI gate for eval #5: the responder's deterministic guarantees with a faked runner.
# ABOUTME: Opt-out recall must be perfect and both output guards must trip.
from __future__ import annotations

from .eval_inbound import run


async def test_inbound_guarantees() -> None:
    metrics = await run()

    # Safety-critical: every opt-out is routed to suppression, none missed.
    assert metrics.optout_recall == 1.0
    assert metrics.optout_false_positives == 0
    # The price guard and the name-drop allowlist guard both trip.
    assert metrics.guards_passed == metrics.guards_total == 2
