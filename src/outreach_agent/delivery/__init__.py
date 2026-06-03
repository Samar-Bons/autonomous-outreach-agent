# ABOUTME: Public surface of the delivery stage: the dry-run sender and the Resend adapter.
# ABOUTME: Both implement the EmailSender Protocol; swap by dependency injection.
from .resend_sender import HttpPoster, ResendSender, UrllibPoster
from .sender import DryRunSender

__all__ = [
    "DryRunSender",
    "HttpPoster",
    "ResendSender",
    "UrllibPoster",
]
