# ABOUTME: Public surface of the inbound responder: the CI-safe, SDK-free core.
# ABOUTME: The Agent SDK runner lives in .agent and is imported explicitly where needed.
from pathlib import Path

from .knowledge import KnowledgeBase
from .models import InboundRoute, ResponderResult
from .responder import (
    AgentRunner,
    InboundResponder,
    mentions_price,
    parse_responder_json,
)

DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parents[3] / "data" / "seed" / "knowledge"

__all__ = [
    "DEFAULT_KNOWLEDGE_PATH",
    "AgentRunner",
    "InboundResponder",
    "InboundRoute",
    "KnowledgeBase",
    "ResponderResult",
    "mentions_price",
    "parse_responder_json",
]
