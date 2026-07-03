"""Live integration tests against real backends (opt-in).

Skipped unless ``RUN_LIVE=1``. Requires:

- auto-sentinel API on ``AUTO_SENTINEL_URL`` (default http://localhost:8001),
  started with ``AUTOSENTINEL_MULTI_AGENT=1`` + real ARK/GLM keys + Langfuse
  env for tracing (see auto-sentinel README);
- devdocs-rag API on ``DEVDOCS_RAG_URL`` (default http://localhost:8002),
  started with ``USE_MOCK_EMBEDDINGS=false`` and a populated Qdrant.

The analyze test drives the full sentinel pipeline: ~45s and real CNY spend
per run.
"""

from __future__ import annotations

import os

import pytest

from devcontext_mcp.clients import AutoSentinelClient, DevDocsClient
from devcontext_mcp.config import get_settings
from devcontext_mcp.tools import analyze_error, propose_fix, search_codebase

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE") != "1", reason="live backends required (RUN_LIVE=1)"
)

ERROR_LOG = """KeyError: 'user_id'
Traceback (most recent call last):
  File "app/payment/service.py", line 58, in process_payment
    uid = payload["user_id"]
KeyError: 'user_id'
"""


@pytest.fixture
def sentinel() -> AutoSentinelClient:
    return AutoSentinelClient(get_settings().auto_sentinel_url, mock=False)


@pytest.fixture
def devdocs() -> DevDocsClient:
    return DevDocsClient(get_settings().devdocs_rag_url, mock=False)


async def test_analyze_then_propose_fix_end_to_end(sentinel: AutoSentinelClient) -> None:
    diag = await analyze_error.run(analyze_error.AnalyzeErrorInput(log=ERROR_LOG), sentinel)
    assert diag.status == "completed"
    assert len(diag.incident_id) == 32
    assert diag.category in {"runtime", "build", "infra", "config", "unknown"}

    fix = await propose_fix.run(propose_fix.ProposeFixInput(error_id=diag.incident_id), sentinel)
    assert fix.fix_plan
    assert fix.risk_level in {"low", "medium", "high"}


async def test_search_codebase_real_retrieval(devdocs: DevDocsClient) -> None:
    out = await search_codebase.run(
        search_codebase.SearchCodebaseInput(
            query="reciprocal rank fusion", repo="meizhuixu/devdocs-rag"
        ),
        devdocs,
    )
    assert out.results
    assert any("hybrid" in hit.file for hit in out.results)
    for hit in out.results:
        assert 0.0 <= hit.score <= 1.0
        assert hit.line >= 1
