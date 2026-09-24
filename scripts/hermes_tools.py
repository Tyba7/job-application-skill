#!/usr/bin/env python3
"""Compatibility shim: exposes hermes-agent web tools as hermes_tools."""
import json
import asyncio
import os
import sys
from pathlib import Path

HERMES_AGENT = os.environ.get(
    "HERMES_AGENT_PATH",
    str(Path.home() / ".hermes" / "hermes-agent"),
)

def _try_import():
    """Try to import web_search_tool and web_extract_tool from known locations."""
    candidates = [
        "tools.web_tools",
        "hermes_agent.tools.web_tools",
        "hermes_tools.web_tools",
    ]
    for mod_name in candidates:
        try:
            mod = __import__(mod_name, fromlist=["web_search_tool", "web_extract_tool"])
            if hasattr(mod, "web_search_tool") and hasattr(mod, "web_extract_tool"):
                return mod.web_search_tool, mod.web_extract_tool
        except (ImportError, ModuleNotFoundError):
            continue
    agent_tools = Path(HERMES_AGENT) / "tools"
    if agent_tools.exists():
        sys.path.insert(0, str(agent_tools))
        try:
            from web_tools import web_search_tool, web_extract_tool
            return web_search_tool, web_extract_tool
        except ImportError:
            pass
    raise ImportError(
        f"Could not find web_tools in any of: {candidates} or {agent_tools}"
    )

try:
    web_search_tool, web_extract_tool = _try_import()
except ImportError as e:
    def web_search_tool(query, limit=5):
        return json.dumps({"success": False, "error": str(e)})
    def web_extract_tool(urls, char_limit=None):
        return json.dumps({"results": []})

def web_search(query: str, limit: int = 5) -> dict:
    result = web_search_tool(query, limit=limit)
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return {"success": False, "error": str(result)[:200]}

async def _web_extract_async(urls: list, char_limit: int = None) -> dict:
    result = await web_extract_tool(urls=urls, char_limit=char_limit)
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return {"results": []}

def web_extract(urls: list, char_limit: int = None) -> dict:
    return asyncio.run(_web_extract_async(urls, char_limit))

__all__ = ["web_search", "web_extract"]
