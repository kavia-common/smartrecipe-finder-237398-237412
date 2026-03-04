from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse


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


def _to_asyncpg_sqlalchemy_scheme(url: str) -> str:
    """Convert postgres/postgresql scheme to SQLAlchemy asyncpg scheme."""
    url = url.replace("postgres://", "postgresql://")
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Fallback: if user provided something odd, still try to prepend.
    return f"postgresql+asyncpg://{url}"


# PUBLIC_INTERFACE
def build_postgres_dsn(settings: Settings) -> str:
    """Build a SQLAlchemy async DSN for Postgres.

    Integration note:
        Some environments provide a POSTGRES_URL without credentials (e.g. "postgresql://host:port/db")
        but also provide POSTGRES_USER/POSTGRES_PASSWORD. asyncpg will otherwise fall back to the OS user
        (often "kavia"), causing "role does not exist". This function merges credentials/db/port from the
        individual env vars into POSTGRES_URL when missing.

    Prefers POSTGRES_URL if provided (expected format: postgresql://... or postgres://...).
    Otherwise, builds a DSN from POSTGRES_USER/PASSWORD/DB/PORT.

    Returns:
        str: SQLAlchemy DSN using the asyncpg driver.
    """
    if settings.postgres_url:
        # Normalize scheme first.
        raw = settings.postgres_url.replace("postgres://", "postgresql://")

        # Try to parse and enrich with credentials if missing.
        try:
            parsed = urlparse(raw)
            # Only attempt to enrich standard postgres URLs.
            if parsed.scheme in ("postgresql", "postgresql+asyncpg"):
                username = parsed.username or (settings.postgres_user or None)
                password = parsed.password or (settings.postgres_password or None)

                # If db isn't specified in the URL, use env var (if any).
                db_from_url = (parsed.path or "").lstrip("/") or None
                db = db_from_url or (settings.postgres_db or None)

                # If port isn't specified in the URL, use env var (if any).
                port = parsed.port or (int(settings.postgres_port) if (settings.postgres_port or "").isdigit() else None)

                hostname = parsed.hostname or "localhost"

                netloc = hostname
                if port is not None:
                    netloc = f"{netloc}:{port}"

                if username:
                    userinfo = username
                    if password:
                        userinfo = f"{userinfo}:{password}"
                    netloc = f"{userinfo}@{netloc}"

                path = f"/{db}" if db else (parsed.path or "")

                enriched = urlunparse(
                    (
                        "postgresql",  # use base scheme; we'll convert to +asyncpg below
                        netloc,
                        path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )
                return _to_asyncpg_sqlalchemy_scheme(enriched)
        except Exception:
            # If parsing fails, fall back to simple scheme conversion.
            pass

        return _to_asyncpg_sqlalchemy_scheme(raw)

    user = settings.postgres_user or "postgres"
    password = settings.postgres_password or ""
    db = settings.postgres_db or "postgres"
    port = settings.postgres_port or "5432"

    # Database host is assumed to be reachable via the POSTGRES_URL when deployed.
    # If POSTGRES_URL is not provided, we default to localhost for dev.
    host = "localhost"
    auth = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql+asyncpg://{auth}{host}:{port}/{db}"
