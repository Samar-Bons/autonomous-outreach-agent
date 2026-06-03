# ABOUTME: Public surface of the enrichment stage: the synthetic email finder and verifier.
# ABOUTME: Import these from here; resolution internals stay private to the package.
from .finder import SyntheticEmailFinder
from .verifier import SyntheticEmailVerifier

__all__ = [
    "SyntheticEmailFinder",
    "SyntheticEmailVerifier",
]
