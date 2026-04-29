"""Tool: summarize_pr — summarize a GitHub PR by URL."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from devcontext_mcp.clients import DevDocsClient

_PR_URL_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+/pull/\d+$")


class SummarizePRInput(BaseModel):
    pr_url: str = Field(..., description="https://github.com/<owner>/<repo>/pull/<n>")

    @field_validator("pr_url")
    @classmethod
    def _validate_pr_url(cls, v: str) -> str:
        if not _PR_URL_RE.match(v):
            raise ValueError("pr_url must look like https://github.com/<owner>/<repo>/pull/<n>")
        return v


class SummarizePROutput(BaseModel):
    summary: str
    changed_files: list[str]
    key_changes: list[str]


async def run(payload: SummarizePRInput, client: DevDocsClient) -> SummarizePROutput:
    raw = await client.summarize_pr(payload.pr_url)
    return SummarizePROutput.model_validate(raw)
