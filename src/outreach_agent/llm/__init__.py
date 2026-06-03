# ABOUTME: Public surface of the LLM layer: the real client, the stub, and text extraction.
# ABOUTME: Both clients satisfy the LLMClient Protocol and are swapped by dependency injection.
from .anthropic_client import AnthropicClient, extract_text
from .stub import ANGLE_MARKER, CLASSIFY_MARKER, RuleBasedStubLLM

__all__ = [
    "ANGLE_MARKER",
    "CLASSIFY_MARKER",
    "AnthropicClient",
    "RuleBasedStubLLM",
    "extract_text",
]
