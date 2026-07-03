"""One happy-path test per tool. Phase 1 hits the in-memory mock clients."""

from __future__ import annotations

import pytest

from devcontext_mcp.clients import AutoSentinelClient, DevDocsClient
from devcontext_mcp.tools import (
    analyze_error,
    find_examples,
    get_session_context,
    propose_fix,
    search_codebase,
    search_incidents,
    summarize_pr,
)


@pytest.fixture
def sentinel() -> AutoSentinelClient:
    return AutoSentinelClient("http://unused", mock=True)


@pytest.fixture
def devdocs() -> DevDocsClient:
    return DevDocsClient("http://unused", mock=True)


@pytest.mark.asyncio
async def test_analyze_error_log(sentinel: AutoSentinelClient) -> None:
    out = await analyze_error.run(
        analyze_error.AnalyzeErrorInput(log="NullPointerException at line 42"),
        sentinel,
    )
    assert out.category in {"runtime", "build", "infra", "config", "unknown"}
    assert out.severity in {"low", "medium", "high", "critical"}
    assert out.summary
    # Phase 2 contract: expose the backend incident id so propose_fix can
    # chain off it, plus a completion status for slow pipeline runs.
    assert out.status == "completed"
    assert len(out.incident_id) == 32


@pytest.mark.asyncio
async def test_search_past_incidents(sentinel: AutoSentinelClient) -> None:
    out = await search_incidents.run(
        search_incidents.SearchIncidentsInput(query="auth header", limit=5),
        sentinel,
    )
    assert len(out.incidents) >= 1
    assert all(i.id and i.title and i.resolution for i in out.incidents)


@pytest.mark.asyncio
async def test_propose_fix(sentinel: AutoSentinelClient) -> None:
    out = await propose_fix.run(propose_fix.ProposeFixInput(error_id="INC-1042"), sentinel)
    assert out.risk_level in {"low", "medium", "high"}
    assert out.fix_plan
    assert "---" in out.code_diff or out.code_diff == ""


@pytest.mark.asyncio
async def test_search_codebase(devdocs: DevDocsClient) -> None:
    out = await search_codebase.run(
        search_codebase.SearchCodebaseInput(query="authenticate"), devdocs
    )
    assert len(out.results) >= 1
    for hit in out.results:
        assert 0.0 <= hit.score <= 1.0


@pytest.mark.asyncio
async def test_find_examples(devdocs: DevDocsClient) -> None:
    out = await find_examples.run(
        find_examples.FindExamplesInput(api_name="httpx.AsyncClient.post"), devdocs
    )
    assert len(out.examples) >= 1
    assert all(ex.repo and ex.file and ex.code for ex in out.examples)


@pytest.mark.asyncio
async def test_summarize_pr_validates_url(devdocs: DevDocsClient) -> None:
    with pytest.raises(ValueError):
        summarize_pr.SummarizePRInput(pr_url="not-a-url")

    out = await summarize_pr.run(
        summarize_pr.SummarizePRInput(pr_url="https://github.com/meizhuixu/devcontext-mcp/pull/1"),
        devdocs,
    )
    assert out.summary
    assert out.changed_files
    assert out.key_changes


@pytest.mark.asyncio
async def test_get_session_context() -> None:
    ctx = await get_session_context.run()
    assert isinstance(ctx.recent_queries, list)
    assert ctx.user_preferences
