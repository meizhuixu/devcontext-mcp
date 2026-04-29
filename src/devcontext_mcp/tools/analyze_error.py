"""Tool: analyze_error_log — diagnose a stack trace / log block."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from devcontext_mcp.clients import AutoSentinelClient

Category = Literal["runtime", "build", "infra", "config", "unknown"]
Severity = Literal["low", "medium", "high", "critical"]


class AnalyzeErrorInput(BaseModel):
    log: str = Field(..., min_length=1, description="Raw error log or stack trace.")


class AnalyzeErrorOutput(BaseModel):
    category: Category
    severity: Severity
    summary: str


async def run(payload: AnalyzeErrorInput, client: AutoSentinelClient) -> AnalyzeErrorOutput:
    raw = await client.diagnose(payload.log)
    return AnalyzeErrorOutput.model_validate(raw)
