from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.utils import get_demo_user_header, http_error, sanitize_user_id
from src.api.models import User
from src.api.schemas import DemoLoginRequest, DemoLoginResponse, UserProfile
from src.api.routers.deps import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/demo-login",
    summary="Demo login / create user",
    description="Creates (or updates) a demo user profile. No real auth; clients should store and send X-Demo-User.",
    response_model=DemoLoginResponse,
    operation_id="demo_login",
)
async def demo_login(payload: DemoLoginRequest, session: AsyncSession = Depends(get_db)) -> DemoLoginResponse:
    """Demo login: upsert a user profile and return it."""
    user_id = sanitize_user_id(payload.user_id)
    if not user_id:
        http_error("invalid_user_id", "user_id is required")

    existing = await session.get(User, user_id)
    if existing is None:
        user = User(id=user_id, display_name=payload.display_name or "Demo Chef")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return DemoLoginResponse(user=UserProfile.model_validate(user.__dict__))
    else:
        if payload.display_name:
            existing.display_name = payload.display_name
            await session.commit()
            await session.refresh(existing)
        return DemoLoginResponse(user=UserProfile.model_validate(existing.__dict__))


@router.get(
    "/me",
    summary="Get current demo user profile",
    description="Returns the profile for X-Demo-User. If not found, returns 404.",
    response_model=UserProfile,
    operation_id="get_me",
)
async def get_me(
    demo_user: str | None = Depends(get_demo_user_header),
    session: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Return the current demo user's profile."""
    if demo_user is None:
        http_error("missing_demo_user", "Send X-Demo-User header for this endpoint", http_status=400)

    user = await session.get(User, demo_user)
    if user is None:
        http_error("user_not_found", "Demo user not found. Call /auth/demo-login first.", http_status=404)

    return UserProfile.model_validate(user.__dict__)
