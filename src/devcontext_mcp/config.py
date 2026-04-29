"""Runtime configuration loaded from environment / .env."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BackendMode = Literal["mock", "http"]


class Settings(BaseSettings):
    """Process-wide settings.

    Phase 1: backend_mode defaults to ``mock`` so the server has no external
    dependencies.  Phase 2 will flip to ``http`` and the URLs become required.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",
    )

    auto_sentinel_url: str = Field(default="http://localhost:8001")
    devdocs_rag_url: str = Field(default="http://localhost:8002")
    backend_mode: BackendMode = Field(default="mock", alias="DEVCONTEXT_BACKEND_MODE")


def get_settings() -> Settings:
    """Build a fresh ``Settings`` instance.

    Kept as a function (not a module-level singleton) so tests can override
    env vars without import-time caching getting in the way.
    """
    return Settings()
