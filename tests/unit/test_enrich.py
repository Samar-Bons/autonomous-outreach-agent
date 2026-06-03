# ABOUTME: Unit tests for SyntheticEmailFinder and SyntheticEmailVerifier.
# ABOUTME: Proves deterministic email resolution and the syntactic acceptance/rejection rules.
from __future__ import annotations

from collections.abc import Callable

from outreach_agent.domain import Prospect
from outreach_agent.enrich import SyntheticEmailFinder, SyntheticEmailVerifier


def test_finder_returns_existing_email_normalized(
    make_prospect: Callable[..., Prospect],
) -> None:
    prospect = make_prospect().model_copy(update={"email": "  Joe@JoesAuto.com "})
    assert SyntheticEmailFinder().find(prospect) == "joe@joesauto.com"


def test_finder_derives_owner_address_from_website(
    make_prospect: Callable[..., Prospect],
) -> None:
    prospect = make_prospect(website="https://www.joesauto.com/contact")
    assert SyntheticEmailFinder().find(prospect) == "owner@joesauto.com"


def test_finder_returns_none_without_email_or_website(
    make_prospect: Callable[..., Prospect],
) -> None:
    assert SyntheticEmailFinder().find(make_prospect()) is None


def test_finder_prefers_email_over_website(
    make_prospect: Callable[..., Prospect],
) -> None:
    prospect = make_prospect(website="https://joesauto.com").model_copy(
        update={"email": "hi@example.org"}
    )
    assert SyntheticEmailFinder().find(prospect) == "hi@example.org"


def test_verifier_accepts_normal_address() -> None:
    assert SyntheticEmailVerifier().verify("owner@joesauto.com") is True


def test_verifier_rejects_missing_at() -> None:
    assert SyntheticEmailVerifier().verify("ownerjoesauto.com") is False


def test_verifier_rejects_double_at() -> None:
    assert SyntheticEmailVerifier().verify("owner@@joesauto.com") is False


def test_verifier_rejects_empty_local() -> None:
    assert SyntheticEmailVerifier().verify("@joesauto.com") is False


def test_verifier_rejects_empty_domain() -> None:
    assert SyntheticEmailVerifier().verify("owner@") is False


def test_verifier_rejects_whitespace() -> None:
    assert SyntheticEmailVerifier().verify("owner @joesauto.com") is False


def test_verifier_rejects_leading_punctuation_local() -> None:
    assert SyntheticEmailVerifier().verify(".owner@joesauto.com") is False


def test_verifier_rejects_dotless_domain() -> None:
    assert SyntheticEmailVerifier().verify("owner@localhost") is False
