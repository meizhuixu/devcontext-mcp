"""Tool: search_codebase — semantic search over indexed repos."""

from __future__ import annotations

from pydantic import BaseModel, Field

from devcontext_mcp.clients import DevDocsClient


class CodeHit(BaseModel):
    file: str
    line: int = Field(..., ge=0)
    snippet: str
    score: float = Field(..., ge=0.0, le=1.0)


class SearchCodebaseInput(BaseModel):
    query: str = Field(..., min_length=1)
    repo: str | None = Field(default=None, description="Optional 'owner/name' filter.")


class SearchCodebaseOutput(BaseModel):
    results: list[CodeHit]


async def run(payload: SearchCodebaseInput, client: DevDocsClient) -> SearchCodebaseOutput:
    rows = await client.search_codebase(payload.query, payload.repo)
    return SearchCodebaseOutput(results=[CodeHit.model_validate(r) for r in rows])
