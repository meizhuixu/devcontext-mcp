"""Tool: propose_fix — fix plan for a given incident id."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from devcontext_mcp.clients import AutoSentinelClient

RiskLevel = Literal["low", "medium", "high"]


class ProposeFixInput(BaseModel):
    error_id: str = Field(..., min_length=1)


class ProposeFixOutput(BaseModel):
    fix_plan: str
    risk_level: RiskLevel
    code_diff: str


async def run(payload: ProposeFixInput, client: AutoSentinelClient) -> ProposeFixOutput:
    raw = await client.propose_fix(payload.error_id)
    return ProposeFixOutput.model_validate(raw)
