# ABOUTME: Unit tests for the inbound knowledge base: search and the name-drop allowlist.
# ABOUTME: Pure and SDK-free, so these run in CI with no API key.
from __future__ import annotations

from outreach_agent.inbound import DEFAULT_KNOWLEDGE_PATH, KnowledgeBase


def _kb() -> KnowledgeBase:
    return KnowledgeBase(DEFAULT_KNOWLEDGE_PATH)


def test_search_finds_relevant_paragraph() -> None:
    hits = _kb().search("pricing quote")
    assert hits
    assert any("quote" in hit.lower() for hit in hits)


def test_search_empty_query_returns_nothing() -> None:
    assert _kb().search("") == []


def test_reference_customers_all_and_by_city() -> None:
    kb = _kb()
    everyone = kb.reference_customers()
    assert len(everyone) == 5
    plano = kb.reference_customers("Plano")
    assert plano == ["Maple Ridge Auto (Plano)"]


def test_customer_names_is_the_allowlist() -> None:
    names = _kb().customer_names()
    assert "Maple Ridge Auto" in names
    assert "Some Made Up Shop" not in names
