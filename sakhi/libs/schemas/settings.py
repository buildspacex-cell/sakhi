"""Application settings management leveraging pydantic v2."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if os.getenv("ENV", "development") in {"development", "dev", "local"}:
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except Exception:
        # Containers should not rely on .env presence; ignore if missing.
        pass


class AppSettings(BaseSettings):
    """Typed configuration sourced from environment variables."""

    app_name: str = Field(
        default="Sakhi",
        validation_alias=AliasChoices("APP_NAME", "SAKHI_APP_NAME"),
    )
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "SAKHI_ENVIRONMENT"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "SAKHI_REDIS_URL"),
    )
    supabase_url: str = Field(
        default="http://localhost:54321",
        validation_alias=AliasChoices("SUPABASE_URL", "SAKHI_SUPABASE_URL"),
    )
    supabase_service_key: str = Field(
        default="changeme",
        validation_alias=AliasChoices(
            "SUPABASE_SERVICE_KEY", "SAKHI_SUPABASE_SERVICE_KEY"
        ),
    )
    postgres_dsn: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/sakhi",
        validation_alias=AliasChoices("DATABASE_URL", "SAKHI_POSTGRES_DSN"),
    )
    openrouter_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "SAKHI_OPENROUTER_API_KEY"),
    )
    llm_router: str = Field(
        default="stub",
        validation_alias=AliasChoices("LLM_ROUTER", "SAKHI_LLM_ROUTER"),
    )
    model_chat: str = Field(
        default="openrouter/chat",
        validation_alias=AliasChoices("MODEL_CHAT", "SAKHI_MODEL_CHAT"),
    )
    model_tool: str = Field(
        default="openrouter/tool",
        validation_alias=AliasChoices("MODEL_TOOL", "SAKHI_MODEL_TOOL"),
    )
    model_reflect: str = Field(
        default="openrouter/reflect",
        validation_alias=AliasChoices("MODEL_REFLECT", "SAKHI_MODEL_REFLECT"),
    )
    model_embed: str = Field(
        default="text-embedding-3-small",
        validation_alias=AliasChoices("MODEL_EMBED", "SAKHI_MODEL_EMBED"),
    )
    event_bridge_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EVENT_BRIDGE_URL", "SAKHI_EVENT_BRIDGE_URL"),
    )
    demo_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEMO_MODE", "SAKHI_DEMO_MODE"),
    )
    demo_user_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DEMO_USER_ID", "SAKHI_DEMO_USER_ID"),
    )
    # Safety gates: when false, identity/reflective writers must no-op.
    # Used to enforce a single learning authority.
    enable_identity_workers: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_IDENTITY_WORKERS", "SAKHI_ENABLE_IDENTITY_WORKERS"
        ),
    )
    enable_reflective_state_writes: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_REFLECTIVE_STATE_WRITES", "SAKHI_ENABLE_REFLECTIVE_STATE_WRITES"
        ),
    )
    enable_rhythm_workers: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_RHYTHM_WORKERS", "SAKHI_ENABLE_RHYTHM_WORKERS"
        ),
    )
    enable_rhythm_forecast_writes: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "ENABLE_RHYTHM_FORECAST_WRITES", "SAKHI_ENABLE_RHYTHM_FORECAST_WRITES"
        ),
    )
    # Weekly synthesis safety gates (disable prose/snippet persistence by default).
    enable_weekly_synthesis_writes: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "ENABLE_WEEKLY_SYNTHESIS_WRITES", "SAKHI_ENABLE_WEEKLY_SYNTHESIS_WRITES"
        ),
    )
    enable_weekly_synthesis_personal_model_writes: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "ENABLE_WEEKLY_SYNTHESIS_PERSONAL_MODEL_WRITES",
            "SAKHI_ENABLE_WEEKLY_SYNTHESIS_PERSONAL_MODEL_WRITES",
        ),
    )
    debug_weekly_pipeline: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "DEBUG_WEEKLY_PIPELINE", "SAKHI_DEBUG_WEEKLY_PIPELINE"
        ),
    )
    enable_weekly_reflection_llm: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_WEEKLY_REFLECTION_LLM", "SAKHI_ENABLE_WEEKLY_REFLECTION_LLM"
        ),
    )
    weekly_reflection_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_MODEL_CHAT", "gpt-4.1-mini"),
        validation_alias=AliasChoices(
            "WEEKLY_REFLECTION_MODEL", "SAKHI_WEEKLY_REFLECTION_MODEL"
        ),
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "sakhi/.env", "sakhi/infra/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Expose the primary database URL."""

        return self.postgres_dsn


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Load environment variables and return a cached settings instance."""

    return AppSettings()


__all__ = ["AppSettings", "get_settings"]
