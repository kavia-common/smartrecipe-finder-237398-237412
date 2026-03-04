from __future__ import annotations

from typing import Iterable

from sqlalchemy import Select, and_, func, or_, select

from src.api.models import Recipe
from src.api.services.ingredients import expand_synonyms, normalize_ingredient_name


def _apply_filters(
    stmt: Select,
    q: str | None,
    cuisine: str | None,
    diet: list[str] | None,
    allergens_exclude: list[str] | None,
    max_time_minutes: int | None,
) -> Select:
    conditions = []

    if q:
        like = f"%{q.strip().lower()}%"
        conditions.append(func.lower(Recipe.title).like(like))

    if cuisine:
        conditions.append(func.lower(Recipe.cuisine) == cuisine.strip().lower())

    if max_time_minutes is not None:
        conditions.append(Recipe.total_time_minutes.is_not(None))
        conditions.append(Recipe.total_time_minutes <= max_time_minutes)

    if diet:
        # Diet tags are JSON arrays. Simple containment test using LIKE on JSON text for portability.
        # (In production, we'd use JSONB operators.)
        for d in diet:
            d = d.strip().lower()
            if d:
                conditions.append(func.cast(Recipe.diet_tags, str).like(f"%{d}%"))

    if allergens_exclude:
        for a in allergens_exclude:
            a = a.strip().lower()
            if a:
                conditions.append(or_(Recipe.allergen_tags.is_(None), ~func.cast(Recipe.allergen_tags, str).like(f"%{a}%")))

    if conditions:
        stmt = stmt.where(and_(*conditions))
    return stmt


# PUBLIC_INTERFACE
def build_recipe_search_stmt(
    q: str | None,
    cuisine: str | None,
    diet: list[str] | None,
    allergens_exclude: list[str] | None,
    max_time_minutes: int | None,
) -> Select:
    """Build SQLAlchemy Select for recipe search with filters."""
    stmt = select(Recipe).order_by(Recipe.id.desc())
    return _apply_filters(stmt, q=q, cuisine=cuisine, diet=diet, allergens_exclude=allergens_exclude, max_time_minutes=max_time_minutes)


def _ingredient_match_score(recipe: Recipe, normalized_ingredients: Iterable[str]) -> float:
    recipe_ings = recipe.ingredients or []
    recipe_names = [normalize_ingredient_name((x or {}).get("name", "")) for x in recipe_ings]
    recipe_set = set(recipe_names)

    score = 0.0
    for ing in normalized_ingredients:
        for variant in expand_synonyms(ing):
            if variant in recipe_set:
                score += 1.0
                break
    # Normalize by ingredient count to reduce bias toward longer lists.
    denom = max(1, len(set(normalized_ingredients)))
    return score / denom


# PUBLIC_INTERFACE
def rank_recipes_for_ingredients(recipes: list[Recipe], ingredients: list[str]) -> list[Recipe]:
    """Rank recipes by ingredient overlap score (simple heuristic)."""
    normalized = [normalize_ingredient_name(i) for i in ingredients if i and i.strip()]
    scored = [(r, _ingredient_match_score(r, normalized)) for r in recipes]

    # Sort primarily by match score, then prefer known (shorter) times.
    # Key is: (score, has_time, -time) with reverse=True.
    scored.sort(
        key=lambda x: (
            x[1],
            x[0].total_time_minutes is not None,
            -(x[0].total_time_minutes or 10**9),
        ),
        reverse=True,
    )
    return [r for (r, _) in scored]
