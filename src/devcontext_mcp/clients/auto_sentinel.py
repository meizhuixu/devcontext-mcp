"""Auto Sentinel backend client.

Phase 2: ``mock=False`` drives the real auto-sentinel HTTP API
(m4-mcp-enabler surface):

- ``POST /api/v1/alerts`` with an ``X-Trace-Id`` header (32-char lowercase
  hex, generated here). auto-sentinel adopts it as job/trace/incident id
  and opens the parent Langfuse trace itself, so spans nest correctly
  (see llmops-dashboard "Trace Ownership").
- ``GET /api/v1/alerts/{job_id}`` polled until the pipeline completes.
- ``GET /api/v1/incidents?q=&limit=`` keyword search over past incidents.

The pipeline is asynchronous upstream (~45s per real run), so ``diagnose``
polls with a bounded timeout and reports ``status="processing"`` instead of
blocking forever.
"""

from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime
from typing import Any

import httpx

from devcontext_mcp.clients._http import HttpBackend


def _guess_error_type(log: str) -> str:
    """Best-effort exception-name extraction from the first log line."""
    lines = log.strip().splitlines()
    if not lines:
        return "unknown"
    token = lines[0].split(":")[0].strip()
    if token and " " not in token and ("Error" in token or "Exception" in token):
        return token
    return "unknown"


class AutoSentinelClient:
    """Async client for the Auto Sentinel service."""

    def __init__(
        self,
        base_url: str,
        *,
        mock: bool = True,
        timeout_s: float = 30.0,
        analyze_timeout_s: float = 120.0,
        poll_interval_s: float = 2.0,
        retry_attempts: int = 3,
        retry_backoff_s: float = 0.2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._mock = mock
        self._analyze_timeout_s = analyze_timeout_s
        self._poll_interval_s = poll_interval_s
        self._http: HttpBackend | None = None
        if not mock:
            self._http = HttpBackend(
                base_url,
                timeout_s=timeout_s,
                retry_attempts=retry_attempts,
                retry_backoff_s=retry_backoff_s,
                transport=transport,
            )

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    # -- analyze_error_log --------------------------------------------------

    async def diagnose(self, log: str) -> dict[str, Any]:
        if self._mock:
            return {
                "incident_id": "0" * 32,
                "status": "completed",
                "category": "runtime",
                "severity": "medium",
                "summary": (
                    "Mock diagnosis: NullPointerException raised in user-service "
                    "when handling a request with a missing `Authorization` header."
                ),
            }
        assert self._http is not None
        trace_id = secrets.token_hex(16)
        alert = {
            "service_name": "unknown",
            "error_type": _guess_error_type(log),
            "message": log.strip().splitlines()[0][:500],
            "timestamp": datetime.now(UTC).isoformat(),
            "stack_trace": log,
        }
        response = await self._http.request(
            "POST", "/api/v1/alerts", json_body=alert, headers={"X-Trace-Id": trace_id}
        )
        if response.status_code not in (200, 202):
            raise RuntimeError(f"alert ingestion failed: HTTP {response.status_code}")
        # The server echoes the injected X-Trace-Id; trust its answer as the
        # canonical id (covers backends that ignore the header).
        trace_id = response.json().get("trace_id") or trace_id

        deadline = asyncio.get_running_loop().time() + self._analyze_timeout_s
        while True:
            body = await self._get_alert(trace_id)
            status = body.get("status")
            if status == "completed":
                diagnosis = body.get("diagnosis") or {}
                return {
                    "incident_id": trace_id,
                    "status": "completed",
                    "category": diagnosis.get("category", "unknown"),
                    "severity": diagnosis.get("severity", "medium"),
                    "summary": diagnosis.get("summary", ""),
                }
            if status == "failed":
                raise RuntimeError(f"auto-sentinel pipeline failed for incident {trace_id}")
            if asyncio.get_running_loop().time() >= deadline:
                return {
                    "incident_id": trace_id,
                    "status": "processing",
                    "category": None,
                    "severity": None,
                    "summary": (
                        f"Diagnosis for incident {trace_id} is still processing "
                        f"(pipeline runs take ~45s). Retry propose_fix('{trace_id}') "
                        "shortly to fetch the result."
                    ),
                }
            await asyncio.sleep(self._poll_interval_s)

    async def _get_alert(self, incident_id: str) -> dict[str, Any]:
        assert self._http is not None
        response = await self._http.request("GET", f"/api/v1/alerts/{incident_id}")
        if response.status_code == 404:
            raise ValueError(f"unknown incident id: {incident_id}")
        if response.status_code != 200:
            raise RuntimeError(f"alert status fetch failed: HTTP {response.status_code}")
        result: dict[str, Any] = response.json()
        return result

    # -- search_past_incidents ----------------------------------------------

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
        assert self._http is not None
        response = await self._http.request(
            "GET", "/api/v1/incidents", params={"q": query, "limit": str(limit)}
        )
        if response.status_code != 200:
            raise RuntimeError(f"incident search failed: HTTP {response.status_code}")
        incidents: list[dict[str, str]] = response.json()["incidents"]
        return incidents

    # -- propose_fix ---------------------------------------------------------

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
        body = await self._get_alert(error_id)
        status = body.get("status")
        if status == "processing":
            raise RuntimeError(f"incident {error_id} is still processing; retry in a few seconds")
        if status != "completed":
            raise RuntimeError(f"incident {error_id} did not complete (status={status})")
        fix = body.get("fix")
        if not fix:
            raise RuntimeError(f"incident {error_id} completed without a fix artifact")
        return {
            "fix_plan": fix.get("fix_plan", ""),
            "risk_level": fix.get("risk_level", "medium"),
            "code_diff": fix.get("code_diff", ""),
        }
