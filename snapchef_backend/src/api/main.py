from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from src.api.core.config import get_settings
from src.api.core.db import get_engine
from src.api.models import Base
from src.api.routers import (
    analytics_router,
    auth_router,
    favorites_router,
    ingredients_router,
    mealplan_router,
    recipes_router,
    shopping_router,
)
from src.api.services.seed import ensure_seed_data


openapi_tags = [
    {"name": "Health", "description": "Health checks and operational endpoints."},
    {"name": "Auth", "description": "Demo auth and user profile handling (no real authentication yet)."},
    {"name": "Ingredients", "description": "Ingredient recognition (stub) and normalization utilities."},
    {"name": "Recipes", "description": "Recipe browsing, search, and suggestions."},
    {"name": "Favorites", "description": "Saved recipes for a user."},
    {"name": "Shopping List", "description": "Shopping list management."},
    {"name": "Meal Planning", "description": "Meal plan entries per day and slot."},
    {"name": "Analytics", "description": "Event tracking and basic summaries (demo)."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database schema and seed demo data on startup.

    Note: this uses SQLAlchemy metadata create_all for simplicity. In production,
    use Alembic migrations.
    """
    engine: AsyncEngine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed recipes if empty
    from src.api.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        await ensure_seed_data(session)

    yield


app = FastAPI(
    title="SnapChef Backend API",
    description=(
        "SnapChef backend for ingredient recognition (stubbed), recipe search/suggestions, "
        "favorites, shopping lists, meal planning, and analytics. "
        "Demo mode: send X-Demo-User header for user-scoped endpoints."
    ),
    version="0.3.0",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description="Simple health check endpoint.",
    operation_id="health_check",
)
def health_check():
    """Return a simple health response."""
    return {"message": "Healthy"}


@app.get(
    "/docs/demo-auth",
    tags=["Auth"],
    summary="How demo auth works",
    description="Usage notes for demo auth with X-Demo-User.",
    operation_id="demo_auth_docs",
)
def demo_auth_docs():
    """Explain how demo auth is expected to be used by clients."""
    return JSONResponse(
        {
            "demo_auth": {
                "header": "X-Demo-User",
                "description": "User-scoped endpoints require (or use) this header. No real auth yet.",
                "flow": [
                    "POST /auth/demo-login with user_id (and optional display_name)",
                    "Store returned user.id",
                    "Send X-Demo-User: <user.id> on favorites/shopping/meal-plan endpoints",
                ],
            }
        }
    )


# Routers
app.include_router(auth_router)
app.include_router(ingredients_router)
app.include_router(recipes_router)
app.include_router(favorites_router)
app.include_router(shopping_router)
app.include_router(mealplan_router)
app.include_router(analytics_router)
