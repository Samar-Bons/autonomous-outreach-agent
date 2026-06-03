# ABOUTME: Deterministic, no-network email finder that resolves a contact address for a prospect.
# ABOUTME: Stands in for a real email-discovery step in the reference build.
from __future__ import annotations

from ..domain import Prospect, normalize_email


def _registrable_domain(website: str) -> str | None:
    """Strip scheme, path, and a leading ``www.`` to a bare, lowercased host."""
    host = website.strip().lower()
    host = host.split("://", 1)[-1]
    host = host.split("/", 1)[0]
    host = host.removeprefix("www.")
    if "." not in host:
        return None
    return host


class SyntheticEmailFinder:
    """Resolves a contact email without any network access.

    This is a deterministic placeholder for the reference build's real finder,
    which would use a real email-discovery service to find a deliverable address.
    Here the resolution is purely a function of the prospect record: a present
    email is canonicalized, otherwise an ``owner@<domain>`` address is derived
    from the website, otherwise nothing is found.
    """

    def find(self, prospect: Prospect) -> str | None:
        if prospect.email:
            return normalize_email(prospect.email)
        if prospect.website:
            domain = _registrable_domain(prospect.website)
            if domain is not None:
                return f"owner@{domain}"
        return None
