from __future__ import annotations

"""
Centralized typed configuration for OpenQueue.

Why this exists
---------------
Production-grade services should not spread `os.getenv(...)` calls across the codebase.
This module provides a single, typed source of truth for configuration.

Design goals
------------
- Typed settings with sane defaults for dev
- Explicit required values where appropriate
- Environment-variable driven configuration (12-factor style)
- Compatible with Docker/Kubernetes

How to use
----------
    from .settings import get_settings

    settings = get_settings()
    print(settings.database_url)

Notes
-----
- `pydantic-settings` is not currently pinned in requirements. If you adopt this
  module, add it to `requirements.txt`:
      pydantic-settings>=2.0
"""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvName = Literal["dev", "test", "prod"]


class Settings(BaseSettings):
    """
    OpenQueue settings.

    Values are loaded from:
    - environment variables
    - optionally a `.env` file (local dev)

    Prefixing:
    - We do NOT enforce a prefix to keep compatibility with existing env vars
      (e.g. DATABASE_URL).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------
    # Core environment
    # -------------------------

    env: EnvName = Field(default="dev", alias="OPENQUEUE_ENV")

    # -------------------------
    # Database
    # -------------------------

    database_url: str = Field(
        ...,
        alias="DATABASE_URL",
        description="PostgreSQL connection URL for asyncpg and Alembic.",
    )

    # Pool sizing (used by asyncpg.create_pool when you wire it in)
    db_pool_min_size: int = Field(
        default=1,
        alias="OPENQUEUE_DB_POOL_MIN_SIZE",
        ge=1,
        description="Minimum number of connections in the asyncpg pool.",
    )
    db_pool_max_size: int = Field(
        default=10,
        alias="OPENQUEUE_DB_POOL_MAX_SIZE",
        ge=1,
        description="Maximum number of connections in the asyncpg pool.",
    )

    # Optional statement timeout (ms). You can apply this per connection if desired.
    db_statement_timeout_ms: Optional[int] = Field(
        default=None,
        alias="OPENQUEUE_DB_STATEMENT_TIMEOUT_MS",
        ge=1,
        description="Optional statement timeout in milliseconds (applied per connection).",
    )

    # -------------------------
    # Authentication / tokens
    # -------------------------

    token_hmac_secret: Optional[str] = Field(
        default=None,
        alias="OPENQUEUE_TOKEN_HMAC_SECRET",
        description=(
            "If set, OpenQueue derives token hashes via HMAC-SHA256(secret, token). "
            "If not set, it uses plain SHA-256(token)."
        ),
    )

    # -------------------------
    # Rate limiting (in-memory)
    # -------------------------

    # NOTE: the actual limiter configuration currently lives in app/rate_limit.py.
    # These settings allow you to later wire limits from env without code changes.
    rate_limit_enabled: bool = Field(
        default=True,
        alias="OPENQUEUE_RATE_LIMIT_ENABLED",
        description="Enable/disable in-memory rate limiting.",
    )

    # -------------------------
    # Payload guardrails
    # -------------------------

    max_enqueue_payload_bytes: int = Field(
        default=256 * 1024,
        alias="OPENQUEUE_MAX_ENQUEUE_PAYLOAD_BYTES",
        ge=1,
        description="Maximum request size allowed for enqueue payloads (bytes).",
    )
    max_result_payload_bytes: int = Field(
        default=256 * 1024,
        alias="OPENQUEUE_MAX_RESULT_PAYLOAD_BYTES",
        ge=1,
        description="Maximum request size allowed for ack result payloads (bytes).",
    )
    max_error_text_bytes: int = Field(
        default=8 * 1024,
        alias="OPENQUEUE_MAX_ERROR_TEXT_BYTES",
        ge=1,
        description="Maximum length allowed for nack error text (bytes, best-effort).",
    )

    # -------------------------
    # Observability
    # -------------------------

    log_level: str = Field(
        default="INFO",
        alias="OPENQUEUE_LOG_LEVEL",
        description="Application log level (e.g. DEBUG, INFO, WARNING).",
    )

    # -------------------------
    # Maintenance
    # -------------------------

    maintenance_enabled: bool = Field(
        default=False,
        alias="OPENQUEUE_MAINTENANCE_ENABLED",
        description=(
            "If true, the API process may run maintenance tasks. "
            "Recommended to run maintenance as a separate process/container instead."
        ),
    )
    maintenance_interval_seconds: int = Field(
        default=30,
        alias="OPENQUEUE_MAINTENANCE_INTERVAL_SECONDS",
        ge=1,
        description="Maintenance loop interval (seconds).",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Using an LRU cache avoids re-reading env and re-parsing settings for every import.
    """
    return Settings()
