# ABOUTME: Unit tests for the suppression stores, parametrized over the in-memory and sqlite impls.
# ABOUTME: Proves normalization on add/query, miss behavior, and that all() returns what was added.
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from outreach_agent.domain import ScheduledSend, SuppressionEntry
from outreach_agent.domain.enums import SendStatus, SuppressionReason, Wave
from outreach_agent.protocols import SuppressionStore
from outreach_agent.safety.suppression import (
    InMemorySuppressionStore,
    SqliteSuppressionStore,
    cancel_suppressed_sends,
)

StoreFactory = Callable[[], SuppressionStore]


@pytest.fixture(params=["memory", "sqlite"])
def store(request: pytest.FixtureRequest) -> SuppressionStore:
    if request.param == "memory":
        return InMemorySuppressionStore()
    return SqliteSuppressionStore(":memory:")


def _entry(email: str) -> SuppressionEntry:
    return SuppressionEntry(
        email=email,
        reason=SuppressionReason.OPT_OUT,
        source="test",
        added_at=datetime(2026, 6, 2, 12, 0, 0),
    )


def test_add_then_is_suppressed(store: SuppressionStore) -> None:
    store.add(_entry("owner@shop.com"))
    assert store.is_suppressed("owner@shop.com") is True


def test_is_suppressed_normalizes_case_and_whitespace(store: SuppressionStore) -> None:
    store.add(_entry("Owner@Shop.com"))
    assert store.is_suppressed(" owner@shop.com ") is True


def test_is_suppressed_false_for_unknown(store: SuppressionStore) -> None:
    store.add(_entry("owner@shop.com"))
    assert store.is_suppressed("stranger@elsewhere.com") is False


def test_all_returns_added_entries(store: SuppressionStore) -> None:
    store.add(_entry("a@shop.com"))
    store.add(_entry("b@shop.com"))
    entries = store.all()
    assert len(entries) == 2
    assert {e.email for e in entries} == {"a@shop.com", "b@shop.com"}
    assert all(e.reason is SuppressionReason.OPT_OUT for e in entries)


def test_sqlite_store_persists_across_close_and_reopen(tmp_path: Path) -> None:
    db_path = str(tmp_path / "suppressions.db")
    with SqliteSuppressionStore(db_path) as store:
        store.add(_entry("owner@shop.com"))

    reopened = SqliteSuppressionStore(db_path)
    try:
        assert reopened.is_suppressed("owner@shop.com") is True
    finally:
        reopened.close()


def _scheduled(email: str) -> ScheduledSend:
    return ScheduledSend(
        prospect_id="p",
        email=email,
        wave=Wave.BUMP,
        send_at=datetime(2026, 4, 23, 11, 0, tzinfo=UTC),
        idem_key=f"c/{email}-w2",
    )


def test_cancel_suppressed_sends_cancels_only_suppressed() -> None:
    store = InMemorySuppressionStore()
    store.add(_entry("opted@out.com"))

    swept = cancel_suppressed_sends(
        [_scheduled("opted@out.com"), _scheduled("fine@shop.com")], store
    )
    by_email = {s.email: s for s in swept}

    assert by_email["opted@out.com"].status is SendStatus.CANCELLED
    assert by_email["opted@out.com"].cancel_reason == "suppressed"
    assert by_email["fine@shop.com"].status is SendStatus.SCHEDULED
