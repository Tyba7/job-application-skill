"""Compatibility shim: exposes hermes-agent web tools as hermes_tools.

The pipeline expects `from hermes_tools import web_search, web_extract`.
The actual functions in hermes-agent are `web_search_tool` and `web_extract_tool`
and return JSON strings. This shim wraps them to return parsed dicts.
"""
import json
import asyncio
import sys
import os

# Add hermes-agent to path
HERMES_AGENT = "/Users/tayyabarizwan/.hermes/hermes-agent"
if HERMES_AGENT not in sys.path:
    sys.path.insert(0, HERMES_AGENT)

from tools.web_tools import web_search_tool, web_extract_tool


def web_search(query: str, limit: int = 5) -> dict:
    """Search the web. Returns parsed dict with data.web list."""
    result = web_search_tool(query, limit=limit)
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return {"success": False, "error": f"Could not parse: {result[:200]}"}


async def _web_extract_async(urls: list, char_limit: int = None) -> dict:
    """Async wrapper for web_extract_tool."""
    result = await web_extract_tool(urls=urls, char_limit=char_limit)
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return {"results": []}


def web_extract(urls: list, char_limit: int = None) -> dict:
    """Extract content from URLs. Returns parsed dict with results list."""
    return asyncio.run(_web_extract_async(urls, char_limit))


__all__ = ["web_search", "web_extract"]