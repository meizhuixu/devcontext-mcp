"""Contract tests for the Phase 2 HTTP clients.

These tests pin the wire contract between devcontext-mcp and the two
backends (auto-sentinel, devdocs-rag) using ``httpx.MockTransport`` — no
real network. The backend contracts they encode:

auto-sentinel (m4-mcp-enabler):
  POST /api/v1/alerts            (+ optional X-Trace-Id: ^[0-9a-f]{32}$)
  GET  /api/v1/alerts/{job_id}   -> status processing|completed|failed
  GET  /api/v1/incidents?q=&limit=

devdocs-rag (m4-mcp-enabler):
  POST /query/stream  (SSE; retrieval_only=true skips LLM generation;
                       chunks carry start_line/end_line/chunk_type)
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import pytest

from devcontext_mcp.clients import AutoSentinelClient, DevDocsClient

TRACE_ID_RE = re.compile(r"^[0-9a-f]{32}$")

COMPLETED_ALERT = {
    "job_id": "PLACEHOLDER",
    "trace_id": "PLACEHOLDER",
    "status": "completed",
    "diagnosis": {
        "category": "runtime",
        "severity": "high",
        "summary": "KeyError raised in payment-service dict lookup.",
    },
    "fix": {
        "fix_plan": "Use .get() with a default and add a regression test.",
        "risk_level": "low",
        "code_diff": "--- a/x.py\n+++ b/x.py\n@@\n-v = d['k']\n+v = d.get('k')\n",
    },
    "report_path": "output/x-report.md",
}


def _sentinel(handler: httpx.MockTransport, **kw: Any) -> AutoSentinelClient:
    kw.setdefault("poll_interval_s", 0.0)
    kw.setdefault("retry_backoff_s", 0.0)
    return AutoSentinelClient("http://sentinel", mock=False, transport=handler, **kw)


def _devdocs(handler: httpx.MockTransport, **kw: Any) -> DevDocsClient:
    kw.setdefault("retry_backoff_s", 0.0)
    return DevDocsClient("http://devdocs", mock=False, transport=handler, **kw)


# --------------------------------------------------------------------------
# AutoSentinelClient.diagnose
# --------------------------------------------------------------------------


async def test_diagnose_posts_alert_with_trace_header_and_polls() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/v1/alerts":
            trace_id = request.headers["X-Trace-Id"]
            assert TRACE_ID_RE.match(trace_id)
            payload = json.loads(request.content)
            # AlertPayload required fields
            assert payload["message"]
            assert payload["service_name"]
            assert payload["error_type"]
            assert payload["timestamp"]
            assert "KeyError" in payload["stack_trace"]
            seen["trace_id"] = trace_id
            return httpx.Response(
                202,
                json={
                    "job_id": trace_id,
                    "status": "accepted",
                    "message": "queued",
                    "trace_id": trace_id,
                },
            )
        if request.method == "GET" and request.url.path == f"/api/v1/alerts/{seen['trace_id']}":
            body = dict(COMPLETED_ALERT)
            body["job_id"] = body["trace_id"] = seen["trace_id"]
            return httpx.Response(200, json=body)
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    client = _sentinel(httpx.MockTransport(handler))
    out = await client.diagnose("KeyError: 'user_id'\n  File 'x.py', line 3")

    assert out["status"] == "completed"
    assert out["incident_id"] == seen["trace_id"]
    assert out["category"] == "runtime"
    assert out["severity"] == "high"
    assert "KeyError" in out["summary"]


async def test_diagnose_waits_through_processing() -> None:
    calls = {"gets": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                202,
                json={"job_id": "a" * 32, "status": "accepted", "message": "q", "trace_id": "a" * 32},
            )
        calls["gets"] += 1
        if calls["gets"] < 3:
            return httpx.Response(
                200,
                json={
                    "job_id": "a" * 32,
                    "trace_id": "a" * 32,
                    "status": "processing",
                    "diagnosis": None,
                    "fix": None,
                    "report_path": None,
                },
            )
        body = dict(COMPLETED_ALERT)
        body["job_id"] = body["trace_id"] = "a" * 32
        return httpx.Response(200, json=body)

    client = _sentinel(httpx.MockTransport(handler))
    out = await client.diagnose("boom")
    assert out["status"] == "completed"
    assert calls["gets"] == 3


async def test_diagnose_returns_processing_on_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                202,
                json={"job_id": "b" * 32, "status": "accepted", "message": "q", "trace_id": "b" * 32},
            )
        return httpx.Response(
            200,
            json={
                "job_id": "b" * 32,
                "trace_id": "b" * 32,
                "status": "processing",
                "diagnosis": None,
                "fix": None,
                "report_path": None,
            },
        )

    client = _sentinel(httpx.MockTransport(handler), analyze_timeout_s=0.05)
    out = await client.diagnose("boom")
    assert out["status"] == "processing"
    assert out["incident_id"] == "b" * 32
    assert out["category"] is None
    assert out["severity"] is None
    assert "processing" in out["summary"]


async def test_diagnose_failed_run_raises_runtime_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                202,
                json={"job_id": "c" * 32, "status": "accepted", "message": "q", "trace_id": "c" * 32},
            )
        return httpx.Response(
            200,
            json={
                "job_id": "c" * 32,
                "trace_id": "c" * 32,
                "status": "failed",
                "diagnosis": None,
                "fix": None,
                "report_path": None,
            },
        )

    client = _sentinel(httpx.MockTransport(handler))
    with pytest.raises(RuntimeError):
        await client.diagnose("boom")


# --------------------------------------------------------------------------
# AutoSentinelClient.search_incidents / propose_fix
# --------------------------------------------------------------------------


async def test_search_incidents_maps_query_params() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/incidents"
        assert request.url.params["q"] == "key error"
        assert request.url.params["limit"] == "3"
        return httpx.Response(
            200,
            json={
                "incidents": [
                    {"id": "d" * 32, "title": "KeyError in payment-service", "resolution": "Use .get()"},
                ]
            },
        )

    client = _sentinel(httpx.MockTransport(handler))
    out = await client.search_incidents("key error", limit=3)
    assert out == [
        {"id": "d" * 32, "title": "KeyError in payment-service", "resolution": "Use .get()"}
    ]


async def test_propose_fix_returns_fix_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/alerts/{'e' * 32}"
        body = dict(COMPLETED_ALERT)
        body["job_id"] = body["trace_id"] = "e" * 32
        return httpx.Response(200, json=body)

    client = _sentinel(httpx.MockTransport(handler))
    out = await client.propose_fix("e" * 32)
    assert out["risk_level"] == "low"
    assert out["fix_plan"]
    assert out["code_diff"].startswith("---")


async def test_propose_fix_unknown_id_raises_value_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    client = _sentinel(httpx.MockTransport(handler))
    with pytest.raises(ValueError):
        await client.propose_fix("f" * 32)


async def test_propose_fix_still_processing_raises_runtime_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "job_id": "a" * 32,
                "trace_id": "a" * 32,
                "status": "processing",
                "diagnosis": None,
                "fix": None,
                "report_path": None,
            },
        )

    client = _sentinel(httpx.MockTransport(handler))
    with pytest.raises(RuntimeError):
        await client.propose_fix("a" * 32)


# --------------------------------------------------------------------------
# Retry / upstream failure behaviour (shared HTTP layer)
# --------------------------------------------------------------------------


async def test_retries_on_5xx_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, text="unavailable")
        return httpx.Response(200, json={"incidents": []})

    client = _sentinel(httpx.MockTransport(handler))
    out = await client.search_incidents("q", limit=5)
    assert out == []
    assert calls["n"] == 2


async def test_exhausted_retries_raise_runtime_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _sentinel(httpx.MockTransport(handler), retry_attempts=2)
    with pytest.raises(RuntimeError):
        await client.search_incidents("q", limit=5)


# --------------------------------------------------------------------------
# DevDocsClient (SSE over /query/stream)
# --------------------------------------------------------------------------

RETRIEVED_CHUNKS = {
    "chunks": [
        {
            "namespace": "repo_auto_sentinel",
            "file_path": "autosentinel/api/main.py",
            "symbol": "ingest_alert",
            "heading_path": "",
            "score": 0.91,
            "snippet": "async def ingest_alert(...): ...",
            "start_line": 38,
            "end_line": 90,
            "chunk_type": "code",
        },
        {
            "namespace": "repo_auto_sentinel",
            "file_path": "README.md",
            "symbol": "",
            "heading_path": "Quickstart",
            "score": 1.7,  # reranker scores are not bounded to [0,1]
            "snippet": "## Quickstart ...",
            "start_line": None,
            "end_line": None,
            "chunk_type": "doc",
        },
    ]
}


def _sse_response(request: httpx.Request, payload: dict[str, Any]) -> httpx.Response:
    body = (
        "event: retrieved\n"
        f"data: {json.dumps(payload)}\n"
        "\n"
        "event: done\n"
        "data: \n"
        "\n"
    )
    return httpx.Response(
        200, content=body.encode(), headers={"content-type": "text/event-stream"}
    )


async def test_search_codebase_consumes_retrieved_event() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/query/stream"
        payload = json.loads(request.content)
        assert payload["question"] == "alert ingestion"
        assert payload["retrieval_only"] is True
        assert payload["namespaces"] == ["repo_auto_sentinel"]
        return _sse_response(request, RETRIEVED_CHUNKS)

    client = _devdocs(httpx.MockTransport(handler))
    hits = await client.search_codebase("alert ingestion", repo="meizhuixu/auto-sentinel")

    assert hits[0] == {
        "file": "autosentinel/api/main.py",
        "line": 38,
        "snippet": "async def ingest_alert(...): ...",
        "score": 0.91,
    }
    # doc chunk: no line info -> line 1; score clamped into [0, 1]
    assert hits[1]["line"] == 1
    assert hits[1]["score"] == 1.0


async def test_search_codebase_without_repo_uses_default_namespaces() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["namespaces"] == []
        return _sse_response(request, {"chunks": []})

    client = _devdocs(httpx.MockTransport(handler))
    assert await client.search_codebase("anything", repo=None) == []


async def test_find_examples_keeps_only_code_chunks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["question"] == "ingest_alert"
        assert payload["retrieval_only"] is True
        return _sse_response(request, RETRIEVED_CHUNKS)

    client = _devdocs(httpx.MockTransport(handler))
    examples = await client.find_examples("ingest_alert")

    assert examples == [
        {
            "repo": "repo_auto_sentinel",
            "file": "autosentinel/api/main.py",
            "code": "async def ingest_alert(...): ...",
        }
    ]


async def test_devdocs_stream_error_raises_runtime_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _devdocs(httpx.MockTransport(handler), retry_attempts=1)
    with pytest.raises(RuntimeError):
        await client.search_codebase("q", repo=None)


async def test_summarize_pr_http_mode_is_labelled_mock() -> None:
    # No backend endpoint exists (descoped in M4, see DEBT.md): http mode
    # must not silently pretend the data is real.
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("summarize_pr must not hit the network")

    client = _devdocs(httpx.MockTransport(handler))
    out = await client.summarize_pr("https://github.com/meizhuixu/devcontext-mcp/pull/1")
    assert out["summary"].startswith("[mock")
