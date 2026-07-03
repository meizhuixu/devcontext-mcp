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
    incident_id: str = Field(
        description="Backend incident/trace id (32-char lowercase hex); pass to propose_fix."
    )
    status: Literal["completed", "processing"] = Field(
        description="'processing' when the pipeline exceeded the wait budget; retry later."
    )
    category: Category | None
    severity: Severity | None
    summary: str


async def run(payload: AnalyzeErrorInput, client: AutoSentinelClient) -> AnalyzeErrorOutput:
    raw = await client.diagnose(payload.log)
    return AnalyzeErrorOutput.model_validate(raw)
