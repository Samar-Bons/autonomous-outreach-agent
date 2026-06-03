# ABOUTME: The in-process Agent SDK tools the responder exposes: grounded KB lookups.
# ABOUTME: Importing this module requires the optional claude-agent-sdk dependency.
from __future__ import annotations

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool
from claude_agent_sdk.types import McpSdkServerConfig

from .knowledge import KnowledgeBase


def build_kb_server(kb: KnowledgeBase) -> McpSdkServerConfig:
    """Build an in-process MCP server exposing the knowledge base as two tools."""

    @tool(
        "search_knowledge",
        "Search the company knowledge base for facts about products, delivery, and terms.",
        {"query": str},
    )
    async def search_knowledge(args: dict[str, Any]) -> dict[str, Any]:
        hits = kb.search(str(args.get("query", "")))
        text = "\n\n".join(hits) if hits else "No matching knowledge."
        return {"content": [{"type": "text", "text": text}]}

    @tool(
        "list_reference_customers",
        "List approved reference customers for social proof, optionally filtered by city.",
        {"city": str},
    )
    async def list_reference_customers(args: dict[str, Any]) -> dict[str, Any]:
        city = args.get("city")
        names = kb.reference_customers(str(city) if city else None)
        text = "\n".join(names) if names else "No approved reference customers for that city."
        return {"content": [{"type": "text", "text": text}]}

    return create_sdk_mcp_server(
        name="kb",
        version="1.0.0",
        tools=[search_knowledge, list_reference_customers],
    )
