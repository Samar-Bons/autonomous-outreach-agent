# ABOUTME: Public surface of the LLM layer: real client, stub, caching, budget, text extraction.
# ABOUTME: All clients satisfy the LLMClient Protocol and are composed by dependency injection.
from .anthropic_client import AnthropicClient, extract_text
from .cache import BudgetedLLMClient, BudgetExceeded, CallBudget, DiskCachedLLMClient
from .cli_client import ClaudeCliClient
from .stub import ANGLE_MARKER, CLASSIFY_MARKER, RuleBasedStubLLM

__all__ = [
    "ANGLE_MARKER",
    "CLASSIFY_MARKER",
    "AnthropicClient",
    "BudgetExceeded",
    "BudgetedLLMClient",
    "CallBudget",
    "ClaudeCliClient",
    "DiskCachedLLMClient",
    "RuleBasedStubLLM",
    "extract_text",
]
