"""Resource: get_session_context — current-session metadata."""

from __future__ import annotations

from pydantic import BaseModel


class SessionContext(BaseModel):
    recent_queries: list[str]
    active_repo: str | None
    user_preferences: dict[str, str]


async def run() -> SessionContext:
    return SessionContext(
        recent_queries=[
            "How does the auth middleware reject missing headers?",
            "Find examples of httpx.AsyncClient.post",
        ],
        active_repo="meizhuixu/devcontext-mcp",
        user_preferences={"language": "python", "verbosity": "concise"},
    )
