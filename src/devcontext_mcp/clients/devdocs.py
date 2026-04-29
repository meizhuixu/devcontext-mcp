"""DevDocs RAG backend client.

Phase 1 returns canned data. Phase 2 swaps to httpx.
"""

from __future__ import annotations

from typing import Any


class DevDocsClient:
    """Async client for the DevDocs RAG service."""

    def __init__(self, base_url: str, *, mock: bool = True) -> None:
        self._base_url = base_url
        self._mock = mock

    async def search_codebase(self, query: str, repo: str | None) -> list[dict[str, Any]]:
        if self._mock:
            return [
                {
                    "file": "src/auth/middleware.py",
                    "line": 42,
                    "snippet": "def authenticate(request: Request) -> User: ...",
                    "score": 0.91,
                },
                {
                    "file": "src/auth/jwt.py",
                    "line": 17,
                    "snippet": "def decode_token(token: str) -> dict: ...",
                    "score": 0.84,
                },
                {
                    "file": "tests/test_auth.py",
                    "line": 88,
                    "snippet": "def test_missing_header_returns_401(): ...",
                    "score": 0.72,
                },
            ]
        raise NotImplementedError("HTTP backend wired in Phase 2")

    async def find_examples(self, api_name: str) -> list[dict[str, str]]:
        if self._mock:
            return [
                {
                    "repo": "meizhuixu/auto-sentinel",
                    "file": "agents/diagnosis.py",
                    "code": f"# Example use of {api_name}\nresult = {api_name}(payload)",
                },
                {
                    "repo": "meizhuixu/devdocs-rag",
                    "file": "ingest/runner.py",
                    "code": f"async def run():\n    await {api_name}(url)",
                },
            ]
        raise NotImplementedError("HTTP backend wired in Phase 2")

    async def summarize_pr(self, pr_url: str) -> dict[str, Any]:
        if self._mock:
            return {
                "summary": (
                    f"PR {pr_url} introduces defensive header parsing in the user-service "
                    "auth middleware and adds two regression tests."
                ),
                "changed_files": [
                    "services/user/auth.py",
                    "services/user/tests/test_auth.py",
                ],
                "key_changes": [
                    "Replace bracket access on Authorization header with .get()",
                    "Raise Unauthorized when header is missing",
                    "Add regression tests for the missing-header path",
                ],
            }
        raise NotImplementedError("HTTP backend wired in Phase 2")
