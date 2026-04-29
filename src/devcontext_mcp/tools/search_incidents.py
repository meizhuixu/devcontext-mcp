"""Tool: search_past_incidents — retrieve historical incidents."""

from __future__ import annotations

from pydantic import BaseModel, Field

from devcontext_mcp.clients import AutoSentinelClient


class Incident(BaseModel):
    id: str
    title: str
    resolution: str


class SearchIncidentsInput(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=50)


class SearchIncidentsOutput(BaseModel):
    incidents: list[Incident]


async def run(payload: SearchIncidentsInput, client: AutoSentinelClient) -> SearchIncidentsOutput:
    rows = await client.search_incidents(payload.query, payload.limit)
    return SearchIncidentsOutput(incidents=[Incident.model_validate(r) for r in rows])
