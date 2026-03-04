from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.api.core.config import build_postgres_dsn, get_settings


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


# PUBLIC_INTERFACE
def get_engine() -> AsyncEngine:
    """Get (and lazily create) the global SQLAlchemy async engine."""
    global _engine, _sessionmaker
    if _engine is None:
        settings = get_settings()
        dsn = build_postgres_dsn(settings)
        _engine = create_async_engine(dsn, pool_pre_ping=True, future=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


# PUBLIC_INTERFACE
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Get the global AsyncSession factory."""
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


# PUBLIC_INTERFACE
@asynccontextmanager
async def db_session() -> AsyncIterator[AsyncSession]:
    """Context manager that yields an AsyncSession and ensures cleanup."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        await session.close()
