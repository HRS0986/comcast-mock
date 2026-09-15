from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from comcast_mock.database import get_session
from comcast_mock.models import Investigation, Ticket
from comcast_mock.schemas import AnalyticsSummaryOut

router = APIRouter()


@router.get("/analytics/summary")
async def analytics_summary(
    session: AsyncSession = Depends(get_session),
) -> AnalyticsSummaryOut:
    total = (await session.execute(select(func.count()).select_from(Ticket))).scalar() or 0

    by_category: dict[str, int] = {}
    for cid, cnt in await session.execute(
        select(Ticket.category_id, func.count())
        .where(Ticket.category_id.is_not(None))
        .group_by(Ticket.category_id)
    ):
        by_category[cid] = cnt

    by_sub_category: dict[str, int] = {}
    for sid, cnt in await session.execute(
        select(Ticket.sub_category_id, func.count())
        .where(Ticket.sub_category_id.is_not(None))
        .group_by(Ticket.sub_category_id)
    ):
        by_sub_category[sid] = cnt

    by_status: dict[str, int] = {}
    for stat, cnt in await session.execute(
        select(Ticket.status, func.count()).group_by(Ticket.status)
    ):
        by_status[stat] = cnt

    total_investigations = (
        await session.execute(select(func.count()).select_from(Investigation))
    ).scalar() or 0

    return AnalyticsSummaryOut(
        total_tickets=total,
        by_category=by_category,
        by_sub_category=by_sub_category,
        by_status=by_status,
        total_investigations=total_investigations,
    )
