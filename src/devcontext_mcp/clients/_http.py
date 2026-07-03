"""Shared HTTP plumbing for the Phase 2 backend clients.

Small, dependency-free layer over ``httpx.AsyncClient``:

- bounded retry with exponential backoff on connection errors, timeouts
  and retryable 5xx responses;
- a minimal SSE consumer for devdocs-rag's ``/query/stream`` endpoint
  (we only ever need the first event of a given name).

Terminal upstream failures surface as ``RuntimeError`` per the project
error conventions; 4xx semantics are owned by the callers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({500, 502, 503, 504})


class HttpBackend:
    """httpx wrapper with retry/backoff shared by both backend clients."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_s: float = 30.0,
        retry_attempts: int = 3,
        retry_backoff_s: float = 0.2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_s, transport=transport)
        self._attempts = max(1, retry_attempts)
        self._backoff_s = retry_backoff_s

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _sleep_before_retry(self, attempt: int) -> None:
        await asyncio.sleep(self._backoff_s * (2**attempt))

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a request, retrying transient failures.

        Returns the final response for any non-retryable status (including
        4xx — the caller owns those semantics). Raises ``RuntimeError`` once
        retries are exhausted.
        """
        last_error: str = ""
        for attempt in range(self._attempts):
            try:
                response = await self._client.request(
                    method, path, json=json_body, params=params, headers=headers
                )
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("request %s %s failed (%s), attempt %d", method, path, exc, attempt)
            else:
                if response.status_code not in RETRYABLE_STATUS:
                    return response
                last_error = f"HTTP {response.status_code}"
                logger.warning(
                    "request %s %s got %d, attempt %d", method, path, response.status_code, attempt
                )
            if attempt + 1 < self._attempts:
                await self._sleep_before_retry(attempt)
        raise RuntimeError(f"upstream request {method} {path} failed after retries ({last_error})")

    async def sse_first(
        self, path: str, json_body: dict[str, Any], *, event_name: str
    ) -> str | None:
        """POST to an SSE endpoint and return the data of the first
        ``event_name`` event (``None`` if the stream ends without one).

        Retries transient failures encountered while *opening* the stream;
        once events are flowing a failure is terminal.
        """
        last_error: str = ""
        for attempt in range(self._attempts):
            try:
                async with self._client.stream("POST", path, json=json_body) as response:
                    if response.status_code in RETRYABLE_STATUS:
                        last_error = f"HTTP {response.status_code}"
                    elif response.status_code != 200:
                        raise RuntimeError(
                            f"upstream SSE request {path} failed: HTTP {response.status_code}"
                        )
                    else:
                        return await _read_first_event(response, event_name)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("SSE %s failed (%s), attempt %d", path, exc, attempt)
            if attempt + 1 < self._attempts:
                await self._sleep_before_retry(attempt)
        raise RuntimeError(f"upstream SSE request {path} failed after retries ({last_error})")


async def _read_first_event(response: httpx.Response, event_name: str) -> str | None:
    """Minimal SSE parse: return the joined data of the first matching event."""
    current_event = "message"
    data_lines: list[str] = []
    async for line in response.aiter_lines():
        if line == "":
            if current_event == event_name:
                return "\n".join(data_lines)
            current_event = "message"
            data_lines = []
        elif line.startswith("event:"):
            current_event = line[len("event:") :].removeprefix(" ").strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].removeprefix(" "))
    return None
