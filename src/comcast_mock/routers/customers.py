from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from comcast_mock.database import get_session
from comcast_mock.exceptions import not_found
from comcast_mock.models import Customer
from comcast_mock.routers import pagination
from comcast_mock.schemas import CustomerCreate, CustomerOut, PaginatedResponse

router = APIRouter()


@router.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    session: AsyncSession = Depends(get_session),
) -> CustomerOut:
    customer = Customer(**payload.model_dump())
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer


@router.get("/customers", response_model=PaginatedResponse)
async def list_customers(
    pagination_values: tuple[int, int] = Depends(pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    limit, offset = pagination_values
    stmt = select(Customer)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    result = await session.execute(
        stmt.order_by(Customer.created_at, Customer.id).limit(limit).offset(offset)
    )
    items = [CustomerOut.model_validate(customer) for customer in result.scalars().all()]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/customers/{customer_id}", response_model=CustomerOut)
async def get_customer_by_id(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
) -> CustomerOut:
    customer = (
        (await session.execute(select(Customer).where(Customer.account_number == customer_id)))
        .scalars()
        .one_or_none()
    )
    if customer is None:
        raise not_found(f"Customer {customer_id} not found")
    return customer


@router.get("/customers/{customer_email}", response_model=CustomerOut)
async def get_customer_by_email(
    customer_email: str,
    session: AsyncSession = Depends(get_session),
) -> CustomerOut:
    customer = (
        (await session.execute(select(Customer).where(Customer.email == customer_email)))
        .scalars()
        .one_or_none()
    )
    if customer is None:
        raise not_found(f"Customer {customer_email} not found")
    return customer
