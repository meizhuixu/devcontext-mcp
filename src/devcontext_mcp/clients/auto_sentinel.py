"""Auto Sentinel backend client.

Phase 1 returns canned data. The interface is fixed so that Phase 2 can swap
the body of each method to ``httpx.AsyncClient`` calls without touching the
tool layer.
"""

from __future__ import annotations

from typing import Any


class AutoSentinelClient:
    """Async client for the Auto Sentinel service."""

    def __init__(self, base_url: str, *, mock: bool = True) -> None:
        self._base_url = base_url
        self._mock = mock

    async def diagnose(self, log: str) -> dict[str, Any]:
        if self._mock:
            return {
                "category": "runtime",
                "severity": "medium",
                "summary": (
                    "Mock diagnosis: NullPointerException raised in user-service "
                    "when handling a request with a missing `Authorization` header."
                ),
            }
        raise NotImplementedError("HTTP backend wired in Phase 2")

    async def search_incidents(self, query: str, limit: int) -> list[dict[str, str]]:
        if self._mock:
            sample = [
                {
                    "id": "INC-1042",
                    "title": "Auth header missing in user-service",
                    "resolution": "Added defensive parsing + 401 fallback in middleware.",
                },
                {
                    "id": "INC-0987",
                    "title": "DB pool exhaustion on bursty traffic",
                    "resolution": "Raised pool size to 50 and added pgbouncer.",
                },
            ]
            return sample[:limit]
        raise NotImplementedError("HTTP backend wired in Phase 2")

    async def propose_fix(self, error_id: str) -> dict[str, str]:
        if self._mock:
            return {
                "fix_plan": (
                    f"For {error_id}: validate `Authorization` header presence in "
                    "auth middleware and return 401 with a structured error body."
                ),
                "risk_level": "low",
                "code_diff": (
                    "--- a/services/user/auth.py\n"
                    "+++ b/services/user/auth.py\n"
                    "@@\n"
                    "-    token = request.headers['Authorization']\n"
                    "+    token = request.headers.get('Authorization')\n"
                    "+    if token is None:\n"
                    "+        raise Unauthorized('missing Authorization header')\n"
                ),
            }
        raise NotImplementedError("HTTP backend wired in Phase 2")
