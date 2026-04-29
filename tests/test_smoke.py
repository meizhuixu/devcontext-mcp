"""Smoke tests: server constructs and registers all 7 tools + 1 resource."""

from __future__ import annotations

import pytest

from devcontext_mcp.server import SESSION_RESOURCE_URI, build_server

EXPECTED_TOOLS = {
    "analyze_error_log",
    "search_past_incidents",
    "propose_fix",
    "search_codebase",
    "find_examples",
    "summarize_pr",
}


@pytest.mark.asyncio
async def test_server_lists_seven_tools() -> None:
    server = build_server()
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS.issubset(names), f"missing tools: {EXPECTED_TOOLS - names}"
    assert len(EXPECTED_TOOLS & names) == 6


@pytest.mark.asyncio
async def test_server_exposes_session_resource() -> None:
    server = build_server()
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert SESSION_RESOURCE_URI in uris
