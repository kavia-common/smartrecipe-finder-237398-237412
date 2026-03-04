from __future__ import annotations

import os
from dataclasses import dataclass


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    postgres_url: str | None
    postgres_user: str | None
    postgres_password: str | None
    postgres_db: str | None
    postgres_port: str | None

    cors_allow_origins: list[str]
    default_page_size: int
    max_page_size: int
    demo_auto_create_user: bool


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load SnapChef settings from environment variables.

    Returns:
        Settings: Loaded settings object.
    """
    # For CORS, allow '*' or a comma-separated list of origins.
    cors_raw = _get_env("CORS_ALLOW_ORIGINS", "*") or "*"
    cors_allow_origins = ["*"] if cors_raw.strip() == "*" else [o.strip() for o in cors_raw.split(",") if o.strip()]

    def _to_int(name: str, default: int) -> int:
        raw = _get_env(name, str(default))
        try:
            return int(raw) if raw is not None else default
        except ValueError:
            return default

    demo_auto_create_user = (_get_env("DEMO_AUTO_CREATE_USER", "true") or "true").lower() in ("1", "true", "yes", "y")

    return Settings(
        postgres_url=_get_env("POSTGRES_URL"),
        postgres_user=_get_env("POSTGRES_USER"),
        postgres_password=_get_env("POSTGRES_PASSWORD"),
        postgres_db=_get_env("POSTGRES_DB"),
        postgres_port=_get_env("POSTGRES_PORT"),
        cors_allow_origins=cors_allow_origins,
        default_page_size=_to_int("DEFAULT_PAGE_SIZE", 20),
        max_page_size=_to_int("MAX_PAGE_SIZE", 100),
        demo_auto_create_user=demo_auto_create_user,
    )


# PUBLIC_INTERFACE
def build_postgres_dsn(settings: Settings) -> str:
    """Build a SQLAlchemy async DSN for Postgres.

    Prefers POSTGRES_URL if provided (expected format: postgresql://... or postgres://...).
    Otherwise, builds a DSN from POSTGRES_USER/PASSWORD/DB/PORT.

    Returns:
        str: SQLAlchemy DSN using the asyncpg driver.
    """
    if settings.postgres_url:
        # Normalize scheme and force asyncpg driver for SQLAlchemy.
        url = settings.postgres_url.replace("postgres://", "postgresql://")
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Fallback: if user provided something odd, still try to prepend.
        return f"postgresql+asyncpg://{url}"

    user = settings.postgres_user or "postgres"
    password = settings.postgres_password or ""
    db = settings.postgres_db or "postgres"
    port = settings.postgres_port or "5432"

    # Database host is assumed to be reachable via the POSTGRES_URL when deployed.
    # If POSTGRES_URL is not provided, we default to localhost for dev.
    host = "localhost"
    auth = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql+asyncpg://{auth}{host}:{port}/{db}"
