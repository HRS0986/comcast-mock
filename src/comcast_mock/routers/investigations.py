import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from comcast_mock.database import get_session
from comcast_mock.exceptions import not_found
from comcast_mock.models import Investigation, Ticket
from comcast_mock.routers import pagination
from comcast_mock.schemas import InvestigationCreate, InvestigationOut, PaginatedResponse

router = APIRouter()


@router.post("/investigations", response_model=InvestigationOut)
async def create_investigation(
    payload: InvestigationCreate,
    session: AsyncSession = Depends(get_session),
) -> InvestigationOut:
    ticket = (
        (await session.execute(select(Ticket).where(Ticket.id == payload.ticket_id)))
        .scalars()
        .one_or_none()
    )
    if ticket is None:
        raise not_found(f"Ticket {payload.ticket_id} not found")

    if len(payload.mcp_tools) != len(payload.inputs):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mcp_tools and inputs must have the same length and order",
        )

    run_id = payload.run_id or f"run-{uuid.uuid4().hex[:12]}"

    investigation = Investigation(
        ticket_id=payload.ticket_id,
        run_id=run_id,
        mcp_tools=payload.mcp_tools,
        inputs=payload.inputs,
    )
    session.add(investigation)
    await session.commit()
    await session.refresh(investigation)
    return investigation


@router.get("/investigations", response_model=PaginatedResponse)
async def list_investigations(
    ticket_id: str | None = Query(default=None, description="Filter investigations for a ticket."),
    pagination: tuple[int, int] = Depends(pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    limit, offset = pagination
    stmt = select(Investigation)
    if ticket_id is not None:
        stmt = stmt.where(Investigation.ticket_id == ticket_id)

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar() or 0
    result = await session.execute(stmt.order_by(Investigation.id).limit(limit).offset(offset))
    items = [InvestigationOut.model_validate(inv) for inv in result.scalars().all()]
    return PaginatedResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get("/investigations/{investigation_id}", response_model=InvestigationOut)
async def get_investigation(
    investigation_id: str,
    session: AsyncSession = Depends(get_session),
) -> InvestigationOut:
    investigation = (
        (
            await session.execute(
                select(Investigation).where(Investigation.id == investigation_id)
            )
        )
        .scalars()
        .one_or_none()
    )
    if investigation is None:
        raise not_found(f"Investigation {investigation_id} not found")
    return investigation
