from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.utils import http_error, parse_pagination
from src.api.models import ShoppingItem
from src.api.routers.deps import get_db, get_or_create_demo_user
from src.api.schemas import ShoppingItemCreate, ShoppingItemOut, ShoppingItemUpdate, ShoppingListResponse

router = APIRouter(prefix="/shopping-list", tags=["Shopping List"])


def _to_out(item: ShoppingItem) -> ShoppingItemOut:
    return ShoppingItemOut(
        id=item.id,
        name=item.name,
        quantity=item.quantity,
        unit=item.unit,
        checked=item.checked,
        created_at=item.created_at,
    )


@router.get(
    "",
    summary="Get shopping list",
    description="List shopping items for the current demo user.",
    response_model=ShoppingListResponse,
    operation_id="list_shopping_items",
)
async def list_items(
    limit: int | None = Query(default=None, ge=1),
    offset: int | None = Query(default=None, ge=0),
    session: AsyncSession = Depends(get_db),
    user=Depends(get_or_create_demo_user),
) -> ShoppingListResponse:
    """List shopping items."""
    page = parse_pagination(limit, offset)

    stmt = select(ShoppingItem).where(ShoppingItem.user_id == user.id).order_by(ShoppingItem.id.desc())
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    rows = await session.execute(stmt.limit(page.limit).offset(page.offset))
    items = rows.scalars().all()
    return ShoppingListResponse(meta={"limit": page.limit, "offset": page.offset, "total": int(total)}, items=[_to_out(i) for i in items])


@router.post(
    "",
    summary="Add item to shopping list",
    description="Adds an item (upserts by name per-user).",
    response_model=ShoppingItemOut,
    operation_id="add_shopping_item",
)
async def add_item(
    payload: ShoppingItemCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(get_or_create_demo_user),
) -> ShoppingItemOut:
    """Add item (upsert by name)."""
    existing = await session.execute(
        select(ShoppingItem).where(ShoppingItem.user_id == user.id, func.lower(ShoppingItem.name) == payload.name.strip().lower())
    )
    item = existing.scalar_one_or_none()
    if item is None:
        item = ShoppingItem(user_id=user.id, name=payload.name.strip(), quantity=payload.quantity, unit=payload.unit, checked=False)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return _to_out(item)

    item.quantity = payload.quantity
    item.unit = payload.unit
    await session.commit()
    await session.refresh(item)
    return _to_out(item)


@router.patch(
    "/{item_id}",
    summary="Update shopping item",
    description="Update quantity/unit/checked state.",
    response_model=ShoppingItemOut,
    operation_id="update_shopping_item",
)
async def update_item(
    item_id: int,
    payload: ShoppingItemUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(get_or_create_demo_user),
) -> ShoppingItemOut:
    """Update an item."""
    item = await session.get(ShoppingItem, item_id)
    if item is None or item.user_id != user.id:
        http_error("shopping_item_not_found", "Shopping item not found", http_status=404)

    if payload.quantity is not None:
        item.quantity = payload.quantity
    if payload.unit is not None:
        item.unit = payload.unit
    if payload.checked is not None:
        item.checked = payload.checked

    await session.commit()
    await session.refresh(item)
    return _to_out(item)


@router.delete(
    "/{item_id}",
    summary="Delete shopping item",
    description="Removes an item from the shopping list.",
    operation_id="delete_shopping_item",
)
async def delete_item(
    item_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(get_or_create_demo_user),
) -> dict:
    """Delete shopping item."""
    item = await session.get(ShoppingItem, item_id)
    if item is None or item.user_id != user.id:
        http_error("shopping_item_not_found", "Shopping item not found", http_status=404)

    await session.delete(item)
    await session.commit()
    return {"status": "ok"}
