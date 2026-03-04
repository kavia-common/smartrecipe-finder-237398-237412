from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.config import get_settings
from src.api.core.db import db_session
from src.api.core.utils import get_demo_user_header, http_error, sanitize_user_id
from src.api.models import User


# PUBLIC_INTERFACE
async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an AsyncSession."""
    async with db_session() as session:
        yield session


# PUBLIC_INTERFACE
async def require_demo_user_id(demo_user: str | None = Depends(get_demo_user_header)) -> str:
    """Require demo user header to be present."""
    if demo_user is None or demo_user.strip() == "":
        http_error("missing_demo_user", "Send X-Demo-User header for this endpoint", http_status=400)
    return sanitize_user_id(demo_user)


# PUBLIC_INTERFACE
async def get_or_create_demo_user(
    user_id: str = Depends(require_demo_user_id),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Return the demo user (create if allowed by DEMO_AUTO_CREATE_USER)."""
    user = await session.get(User, user_id)
    if user is not None:
        return user

    settings = get_settings()
    if not settings.demo_auto_create_user:
        http_error("user_not_found", "Demo user not found. Call /auth/demo-login first.", http_status=404)

    user = User(id=user_id, display_name="Demo Chef")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
