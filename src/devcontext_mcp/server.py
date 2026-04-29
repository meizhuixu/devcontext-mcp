"""FastMCP server entry — wires tools and resources together.

This module is intentionally thin: it constructs the backend clients, then
registers each tool function and the session resource with FastMCP. Business
logic lives in ``tools/`` and ``clients/``.

Run with::

    uv run mcp dev src/devcontext_mcp/server.py
    # or
    uv run devcontext-mcp
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from devcontext_mcp.clients import AutoSentinelClient, DevDocsClient
from devcontext_mcp.config import Settings, get_settings
from devcontext_mcp.tools import (
    analyze_error,
    find_examples,
    get_session_context,
    propose_fix,
    search_codebase,
    search_incidents,
    summarize_pr,
)

logger = logging.getLogger(__name__)

SESSION_RESOURCE_URI = "devcontext://session"


def build_server(settings: Settings | None = None) -> FastMCP:
    """Construct a fully-wired FastMCP server.

    Exposed as a function (rather than a module-level singleton) so tests can
    construct a fresh server per test without hitting import-order issues.
    """
    cfg = settings or get_settings()
    mock = cfg.backend_mode == "mock"

    sentinel = AutoSentinelClient(cfg.auto_sentinel_url, mock=mock)
    devdocs = DevDocsClient(cfg.devdocs_rag_url, mock=mock)

    mcp = FastMCP("devcontext-mcp")

    # --- Auto Sentinel tools ---------------------------------------------

    @mcp.tool(description="Diagnose an error log / stack trace via Auto Sentinel.")
    async def analyze_error_log(log: str) -> dict[str, Any]:
        result = await analyze_error.run(analyze_error.AnalyzeErrorInput(log=log), sentinel)
        return result.model_dump()

    @mcp.tool(description="Search past incidents matching a free-text query.")
    async def search_past_incidents(query: str, limit: int = 5) -> dict[str, Any]:
        result = await search_incidents.run(
            search_incidents.SearchIncidentsInput(query=query, limit=limit), sentinel
        )
        return result.model_dump()

    @mcp.tool(name="propose_fix", description="Propose a fix plan for an incident id.")
    async def propose_fix_tool(error_id: str) -> dict[str, Any]:
        result = await propose_fix.run(propose_fix.ProposeFixInput(error_id=error_id), sentinel)
        return result.model_dump()

    # --- DevDocs RAG tools ----------------------------------------------

    @mcp.tool(
        name="search_codebase",
        description="Semantic search over indexed code repositories.",
    )
    async def search_codebase_tool(query: str, repo: str | None = None) -> dict[str, Any]:
        result = await search_codebase.run(
            search_codebase.SearchCodebaseInput(query=query, repo=repo), devdocs
        )
        return result.model_dump()

    @mcp.tool(
        name="find_examples",
        description="Find concrete usage examples of a specific API symbol.",
    )
    async def find_examples_tool(api_name: str) -> dict[str, Any]:
        result = await find_examples.run(
            find_examples.FindExamplesInput(api_name=api_name), devdocs
        )
        return result.model_dump()

    @mcp.tool(
        name="summarize_pr",
        description="Summarize a GitHub pull request by URL.",
    )
    async def summarize_pr_tool(pr_url: str) -> dict[str, Any]:
        result = await summarize_pr.run(summarize_pr.SummarizePRInput(pr_url=pr_url), devdocs)
        return result.model_dump()

    # --- Session context resource ---------------------------------------

    @mcp.resource(
        SESSION_RESOURCE_URI,
        name="session_context",
        description="Current-session metadata (recent queries, active repo, prefs).",
        mime_type="application/json",
    )
    async def session_context() -> dict[str, Any]:
        ctx = await get_session_context.run()
        return ctx.model_dump()

    return mcp


# Module-level singleton — `mcp dev` imports this attribute by convention.
mcp = build_server()


def main() -> None:
    """Console-script entry point: run over stdio."""
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
