# ABOUTME: Public surface of the delivery stage: the dry-run email sender.
# ABOUTME: Import the sender from here; a real provider adapter implements the same Protocol.
from .sender import DryRunSender

__all__ = [
    "DryRunSender",
]
