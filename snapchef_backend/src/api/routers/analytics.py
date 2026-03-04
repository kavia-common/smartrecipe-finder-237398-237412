from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models import AnalyticsEvent
from src.api.routers.deps import get_db, get_demo_user_header
from src.api.schemas import AnalyticsSummaryResponse, AnalyticsTrackRequest, AnalyticsTrackResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post(
    "/track",
    summary="Track an analytics event",
    description="Stores an analytics event in Postgres (demo). If X-Demo-User is provided, it is associated.",
    response_model=AnalyticsTrackResponse,
    operation_id="track_event",
)
async def track_event(
    payload: AnalyticsTrackRequest,
    session: AsyncSession = Depends(get_db),
    demo_user: str | None = Depends(get_demo_user_header),
) -> AnalyticsTrackResponse:
    """Track an event."""
    event = AnalyticsEvent(user_id=demo_user, event_name=payload.event_name, payload=payload.payload)
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return AnalyticsTrackResponse(status="ok", event_id=event.id)


@router.get(
    "/summary",
    summary="Get basic analytics summary",
    description="Returns aggregated event counts (overall and last 7 days).",
    response_model=AnalyticsSummaryResponse,
    operation_id="analytics_summary",
)
async def summary(session: AsyncSession = Depends(get_db)) -> AnalyticsSummaryResponse:
    """Aggregate analytics events."""
    total = (await session.execute(select(func.count()).select_from(AnalyticsEvent))).scalar_one()

    rows = await session.execute(select(AnalyticsEvent.event_name, func.count()).group_by(AnalyticsEvent.event_name))
    by_event_name = {name: int(cnt) for (name, cnt) in rows.all()}

    today = date.today()
    start = today - timedelta(days=6)
    day_rows = await session.execute(
        select(func.date(AnalyticsEvent.created_at), func.count())
        .where(func.date(AnalyticsEvent.created_at) >= start)
        .group_by(func.date(AnalyticsEvent.created_at))
    )
    tmp = {str(day): int(cnt) for (day, cnt) in day_rows.all()}

    last_7_days = {}
    for i in range(7):
        d = start + timedelta(days=i)
        last_7_days[str(d)] = int(tmp.get(str(d), 0))

    return AnalyticsSummaryResponse(total_events=int(total), by_event_name=by_event_name, last_7_days=last_7_days)
