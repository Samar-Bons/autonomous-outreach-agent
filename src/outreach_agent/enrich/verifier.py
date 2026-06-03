# ABOUTME: Deterministic, no-network email verifier that rejects malformed addresses.
# ABOUTME: A stand-in for a real deliverability-verification API in the reference build.
from __future__ import annotations


class SyntheticEmailVerifier:
    """Verifies an address by shape alone, with no network access.

    This is a deterministic placeholder for the reference build's real verifier,
    which would call a real deliverability-verification API to catch invalid,
    catch-all, and disposable addresses. Here verification is a pure syntactic
    check: an address is rejected when it is obviously malformed and otherwise
    accepted.
    """

    def verify(self, email: str) -> bool:
        if any(c.isspace() for c in email):
            return False
        if email.count("@") != 1:
            return False
        local, domain = email.split("@", 1)
        if not local or not domain:
            return False
        if not local[0].isalnum():
            return False
        return "." in domain
