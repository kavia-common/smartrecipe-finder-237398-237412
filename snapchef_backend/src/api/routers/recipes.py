from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.utils import http_error, parse_pagination
from src.api.models import Recipe
from src.api.routers.deps import get_db
from src.api.schemas import RecipeOut, RecipeSearchResponse, RecipeSuggestionRequest, RecipeSuggestionResponse
from src.api.services.recipes import build_recipe_search_stmt, rank_recipes_for_ingredients

router = APIRouter(prefix="/recipes", tags=["Recipes"])


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
    summary="Browse/search recipes",
    description="Browse recipes with optional query and filters.",
    response_model=RecipeSearchResponse,
    operation_id="list_recipes",
)
async def list_recipes(
    q: str | None = Query(default=None, description="Search query against recipe title."),
    cuisine: str | None = Query(default=None, description="Cuisine filter (e.g. italian, asian)."),
    diet: list[str] = Query(default_factory=list, description="Diet tag filters (e.g. vegetarian)."),
    allergens_exclude: list[str] = Query(default_factory=list, description="Exclude recipes with these allergens."),
    max_time_minutes: int | None = Query(default=None, ge=1, description="Max total time in minutes."),
    limit: int | None = Query(default=None, ge=1, description="Page size."),
    offset: int | None = Query(default=None, ge=0, description="Page offset."),
    session: AsyncSession = Depends(get_db),
) -> RecipeSearchResponse:
    """List recipes with pagination and filters."""
    page = parse_pagination(limit, offset)

    stmt = build_recipe_search_stmt(q=q, cuisine=cuisine, diet=diet, allergens_exclude=allergens_exclude, max_time_minutes=max_time_minutes)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    rows = await session.execute(stmt.limit(page.limit).offset(page.offset))
    recipes = rows.scalars().all()

    return RecipeSearchResponse(meta={"limit": page.limit, "offset": page.offset, "total": int(total)}, items=[_to_recipe_out(r) for r in recipes])


@router.get(
    "/{recipe_id}",
    summary="Get recipe by id",
    description="Returns the recipe detail.",
    response_model=RecipeOut,
    operation_id="get_recipe",
)
async def get_recipe(recipe_id: int, session: AsyncSession = Depends(get_db)) -> RecipeOut:
    """Get a recipe by id."""
    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        http_error("recipe_not_found", "Recipe not found", http_status=404)
    return _to_recipe_out(recipe)


@router.post(
    "/suggestions",
    summary="Get recipe suggestions for a set of ingredients",
    description="Returns suggested recipes ranked by overlap with provided ingredients (simple heuristic).",
    response_model=RecipeSuggestionResponse,
    operation_id="suggest_recipes",
)
async def suggest_recipes(payload: RecipeSuggestionRequest, session: AsyncSession = Depends(get_db)) -> RecipeSuggestionResponse:
    """Suggest recipes based on recognized/confirmed ingredients."""
    # Load a wider set, then rank in Python. For production we'd rank in SQL.
    stmt = build_recipe_search_stmt(
        q=None,
        cuisine=payload.cuisine,
        diet=payload.diet,
        allergens_exclude=payload.allergens_exclude,
        max_time_minutes=payload.max_time_minutes,
    )
    rows = await session.execute(stmt.limit(200))
    recipes = rows.scalars().all()
    ranked = rank_recipes_for_ingredients(list(recipes), payload.ingredients)

    # Default to first 20
    limit = 20
    return RecipeSuggestionResponse(
        meta={"limit": limit, "offset": 0, "total": len(ranked)},
        items=[_to_recipe_out(r) for r in ranked[:limit]],
    )
