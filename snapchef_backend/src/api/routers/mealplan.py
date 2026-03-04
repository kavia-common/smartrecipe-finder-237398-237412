from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.utils import http_error, parse_pagination
from src.api.models import MealPlanEntry, Recipe
from src.api.routers.deps import get_db, get_or_create_demo_user
from src.api.schemas import MealPlanCreate, MealPlanOut, MealPlanResponse

router = APIRouter(prefix="/meal-plan", tags=["Meal Planning"])


def _to_out(entry: MealPlanEntry) -> MealPlanOut:
    return MealPlanOut(
        id=entry.id,
        day=entry.day,
        slot=entry.slot,  # type: ignore[arg-type]
        recipe_id=entry.recipe_id,
        note=entry.note,
        created_at=entry.created_at,
    )


@router.get(
    "",
    summary="List meal plan entries",
    description="List meal plan entries for the user. Defaults to the next 7 days window.",
    response_model=MealPlanResponse,
    operation_id="list_meal_plan",
)
async def list_meal_plan(
    start_day: date | None = Query(default=None, description="Start day (inclusive)."),
    end_day: date | None = Query(default=None, description="End day (inclusive)."),
    limit: int | None = Query(default=None, ge=1),
    offset: int | None = Query(default=None, ge=0),
    session: AsyncSession = Depends(get_db),
    user=Depends(get_or_create_demo_user),
) -> MealPlanResponse:
    """List meal plan entries."""
    page = parse_pagination(limit, offset)
    today = date.today()
    start = start_day or today
    end = end_day or (today + timedelta(days=7))

    stmt = (
        select(MealPlanEntry)
        .where(MealPlanEntry.user_id == user.id, MealPlanEntry.day >= start, MealPlanEntry.day <= end)
        .order_by(MealPlanEntry.day.asc(), MealPlanEntry.slot.asc())
    )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    rows = await session.execute(stmt.limit(page.limit).offset(page.offset))
    entries = rows.scalars().all()
    return MealPlanResponse(meta={"limit": page.limit, "offset": page.offset, "total": int(total)}, items=[_to_out(e) for e in entries])


@router.post(
    "",
    summary="Create or replace a meal plan entry",
    description="Upserts an entry for (day, slot).",
    response_model=MealPlanOut,
    operation_id="upsert_meal_plan",
)
async def upsert_meal_plan(
    payload: MealPlanCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(get_or_create_demo_user),
) -> MealPlanOut:
    """Upsert meal plan entry."""
    if payload.recipe_id is not None:
        recipe = await session.get(Recipe, payload.recipe_id)
        if recipe is None:
            http_error("recipe_not_found", "Recipe not found", http_status=404)

    existing = await session.execute(
        select(MealPlanEntry).where(MealPlanEntry.user_id == user.id, MealPlanEntry.day == payload.day, MealPlanEntry.slot == payload.slot)
    )
    entry = existing.scalar_one_or_none()
    if entry is None:
        entry = MealPlanEntry(user_id=user.id, day=payload.day, slot=payload.slot, recipe_id=payload.recipe_id, note=payload.note)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return _to_out(entry)

    entry.recipe_id = payload.recipe_id
    entry.note = payload.note
    await session.commit()
    await session.refresh(entry)
    return _to_out(entry)


@router.delete(
    "/{entry_id}",
    summary="Delete a meal plan entry",
    description="Deletes a meal plan entry by id.",
    operation_id="delete_meal_plan_entry",
)
async def delete_meal_plan_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(get_or_create_demo_user),
) -> dict:
    """Delete an entry."""
    entry = await session.get(MealPlanEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        http_error("meal_plan_not_found", "Meal plan entry not found", http_status=404)
    await session.delete(entry)
    await session.commit()
    return {"status": "ok"}
