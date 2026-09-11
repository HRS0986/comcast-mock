from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from comcast_mock.database import get_session
from comcast_mock.exceptions import not_found
from comcast_mock.models import Category, SubCategory, Ticket, TicketStatus
from comcast_mock.routers import pagination
from comcast_mock.schemas import (
    PaginatedResponse,
    TicketDetailOut,
    TicketIngestRequest,
    TicketOut,
    TicketUpdate,
)

router = APIRouter()


@router.post("/tickets/ingest", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def ingest_ticket(
    payload: TicketIngestRequest,
    session: AsyncSession = Depends(get_session),
) -> TicketOut:
    if payload.category_id is not None:
        category = (
            (await session.execute(select(Category).where(Category.id == payload.category_id)))
            .scalars()
            .one_or_none()
        )
        if category is None:
            raise not_found(f"Category {payload.category_id} not found")

    if payload.sub_category_id is not None:
        sub_category = (
            (
                await session.execute(
                    select(SubCategory).where(SubCategory.id == payload.sub_category_id)
                )
            )
            .scalars()
            .one_or_none()
        )
        if sub_category is None:
            raise not_found(f"Sub-category {payload.sub_category_id} not found")

        if payload.category_id is not None and sub_category.category_id != payload.category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Sub-category {payload.sub_category_id} does not belong to "
                    f"category {payload.category_id}"
                ),
            )

    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        category_id=payload.category_id,
        sub_category_id=payload.sub_category_id,
        status=TicketStatus.NEW.value,
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


@router.get("/tickets", response_model=PaginatedResponse)
async def list_tickets(
    status: str | None = Query(default=None, description="Filter by ticket status."),
    category_id: str | None = Query(default=None, description="Filter by category id."),
    sub_category_id: str | None = Query(default=None, description="Filter by sub-category id."),
    pagination: tuple[int, int] = Depends(pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    limit, offset = pagination
    stmt = select(Ticket)
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    if category_id is not None:
        stmt = stmt.where(Ticket.category_id == category_id)
    if sub_category_id is not None:
        stmt = stmt.where(Ticket.sub_category_id == sub_category_id)

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar() or 0
    result = await session.execute(stmt.order_by(Ticket.id).limit(limit).offset(offset))
    items = [TicketOut.model_validate(t) for t in result.scalars().all()]
    return PaginatedResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def get_ticket(
    ticket_id: str,
    session: AsyncSession = Depends(get_session),
) -> TicketDetailOut:
    ticket = (
        (
            await session.execute(
                select(Ticket)
                .options(selectinload(Ticket.category), selectinload(Ticket.sub_category))
                .where(Ticket.id == ticket_id)
            )
        )
        .scalars()
        .one_or_none()
    )
    if ticket is None:
        raise not_found(f"Ticket {ticket_id} not found")
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    session: AsyncSession = Depends(get_session),
) -> TicketOut:
    ticket = (
        (await session.execute(select(Ticket).where(Ticket.id == ticket_id)))
        .scalars()
        .one_or_none()
    )
    if ticket is None:
        raise not_found(f"Ticket {ticket_id} not found")

    update_data = payload.model_dump(exclude_unset=True)
    if update_data.get("status") is not None:
        try:
            TicketStatus(update_data["status"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status value: {update_data['status']}",
            ) from None

    for field, value in update_data.items():
        setattr(ticket, field, value)

    await session.commit()
    await session.refresh(ticket)
    return ticket
