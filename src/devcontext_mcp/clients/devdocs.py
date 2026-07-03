"""DevDocs RAG backend client.

Phase 2: ``mock=False`` drives the real devdocs-rag HTTP API. The only
query surface is ``POST /query/stream`` (SSE); with the m4-mcp-enabler
additions we send ``retrieval_only=true`` (skip LLM generation — we only
need the ``retrieved`` event) and receive ``start_line``/``end_line``/
``chunk_type`` per chunk.

``summarize_pr`` has no backend endpoint (descoped in M4, see DEBT.md):
http mode returns the canned payload with an explicit ``[mock ...]`` label
so downstream agents cannot mistake it for real data.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from devcontext_mcp.clients._http import HttpBackend

_SEARCH_TOP_K = 10
_MAX_EXAMPLES = 5


def _namespace_for(repo: str) -> str:
    """Map an ``owner/name`` repo filter to a devdocs-rag namespace.

    devdocs-rag namespaces follow ``repo_<name_with_underscores>``
    (e.g. ``meizhuixu/auto-sentinel`` -> ``repo_auto_sentinel``).
    """
    name = repo.rsplit("/", 1)[-1].replace("-", "_")
    return name if name.startswith("repo_") else f"repo_{name}"


class DevDocsClient:
    """Async client for the DevDocs RAG service."""

    def __init__(
        self,
        base_url: str,
        *,
        mock: bool = True,
        timeout_s: float = 30.0,
        retry_attempts: int = 3,
        retry_backoff_s: float = 0.2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._mock = mock
        self._http: HttpBackend | None = None
        if not mock:
            self._http = HttpBackend(
                base_url,
                timeout_s=timeout_s,
                retry_attempts=retry_attempts,
                retry_backoff_s=retry_backoff_s,
                transport=transport,
            )

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    async def _retrieve(self, question: str, namespaces: list[str]) -> list[dict[str, Any]]:
        assert self._http is not None
        data = await self._http.sse_first(
            "/query/stream",
            {
                "question": question,
                "namespaces": namespaces,
                "top_k": _SEARCH_TOP_K,
                "retrieval_only": True,
            },
            event_name="retrieved",
        )
        if data is None:
            return []
        chunks: list[dict[str, Any]] = json.loads(data).get("chunks", [])
        return chunks

    # -- search_codebase ------------------------------------------------------

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
        namespaces = [_namespace_for(repo)] if repo else []
        chunks = await self._retrieve(query, namespaces)
        return [
            {
                "file": chunk["file_path"],
                "line": int(chunk["start_line"]) if chunk.get("start_line") else 1,
                "snippet": chunk["snippet"],
                # Cross-encoder rerank scores are unbounded; the tool contract
                # promises [0, 1].
                "score": max(0.0, min(1.0, float(chunk["score"]))),
            }
            for chunk in chunks
        ]

    # -- find_examples ---------------------------------------------------------

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
        chunks = await self._retrieve(api_name, [])
        code_chunks = [c for c in chunks if c.get("chunk_type") == "code"]
        return [
            {
                "repo": chunk["namespace"],
                "file": chunk["file_path"],
                "code": chunk["snippet"],
            }
            for chunk in code_chunks[:_MAX_EXAMPLES]
        ]

    # -- summarize_pr ------------------------------------------------------------

    async def summarize_pr(self, pr_url: str) -> dict[str, Any]:
        canned = {
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
        if self._mock:
            return canned
        # No backend endpoint exists yet — never hit the network, and label
        # the payload so it cannot be mistaken for real analysis.
        canned["summary"] = f"[mock — no real backend yet] {canned['summary']}"
        return canned
