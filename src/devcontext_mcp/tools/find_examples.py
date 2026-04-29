"""Tool: find_examples — usage examples of a specific API symbol."""

from __future__ import annotations

from pydantic import BaseModel, Field

from devcontext_mcp.clients import DevDocsClient


class Example(BaseModel):
    repo: str
    file: str
    code: str


class FindExamplesInput(BaseModel):
    api_name: str = Field(..., min_length=1)


class FindExamplesOutput(BaseModel):
    examples: list[Example]


async def run(payload: FindExamplesInput, client: DevDocsClient) -> FindExamplesOutput:
    rows = await client.find_examples(payload.api_name)
    return FindExamplesOutput(examples=[Example.model_validate(r) for r in rows])
