from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.utils import http_error, parse_pagination
from src.api.models import Favorite, Recipe
from src.api.routers.deps import get_db, get_or_create_demo_user
from src.api.schemas import FavoriteToggleResponse, FavoritesResponse, RecipeOut

router = APIRouter(prefix="/favorites", tags=["Favorites"])


def _to_recipe_out(r: Recipe) -> RecipeOut:
    return RecipeOut(
        id=r.id,
        title=r.title,
        description=r.description,
        cuisine=r.cuisine,
        diet_tags=r.diet_tags or [],
        allergen_tags=r.allergen_tags or [],
        total_time_minutes=r.total_time_minutes,
        servings=r.servings,
        ingredients=r.ingredients or [],
        steps=r.steps or [],
        created_at=r.created_at,
    )


@router.get(
    "",
    summary="List favorite recipes",
    description="Returns the current user's favorite recipes.",
    response_model=FavoritesResponse,
    operation_id="list_favorites",
)
async def list_favorites(
    limit: int | None = Query(default=None, ge=1),
    offset: int | None = Query(default=None, ge=0),
    session: AsyncSession = Depends(get_db),
    user=Depends(get_or_create_demo_user),
) -> FavoritesResponse:
    """List favorites with pagination."""
    page = parse_pagination(limit, offset)

    stmt = (
        select(Recipe)
        .join(Favorite, Favorite.recipe_id == Recipe.id)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.id.desc())
    )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    rows = await session.execute(stmt.limit(page.limit).offset(page.offset))
    recipes = rows.scalars().all()
    return FavoritesResponse(meta={"limit": page.limit, "offset": page.offset, "total": int(total)}, items=[_to_recipe_out(r) for r in recipes])


@router.post(
    "/{recipe_id}/toggle",
    summary="Toggle favorite for a recipe",
    description="Adds recipe to favorites if not present; otherwise removes it.",
    response_model=FavoriteToggleResponse,
    operation_id="toggle_favorite",
)
async def toggle_favorite(
    recipe_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(get_or_create_demo_user),
) -> FavoriteToggleResponse:
    """Toggle favorite status."""
    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        http_error("recipe_not_found", "Recipe not found", http_status=404)

    existing = await session.execute(select(Favorite).where(Favorite.user_id == user.id, Favorite.recipe_id == recipe_id))
    fav = existing.scalar_one_or_none()
    if fav is None:
        session.add(Favorite(user_id=user.id, recipe_id=recipe_id))
        await session.commit()
        return FavoriteToggleResponse(recipe_id=recipe_id, is_favorite=True)

    await session.delete(fav)
    await session.commit()
    return FavoriteToggleResponse(recipe_id=recipe_id, is_favorite=False)
