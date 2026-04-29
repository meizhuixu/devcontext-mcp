"""Backend HTTP clients. Phase 1 returns mock data."""

from devcontext_mcp.clients.auto_sentinel import AutoSentinelClient
from devcontext_mcp.clients.devdocs import DevDocsClient

__all__ = ["AutoSentinelClient", "DevDocsClient"]
