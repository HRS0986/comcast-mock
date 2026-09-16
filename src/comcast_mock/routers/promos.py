import hashlib
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comcast_mock.database import get_session
from comcast_mock.models import Customer

router = APIRouter()


class PromoApplicationRequest(BaseModel):
    account_number: str = Field(..., min_length=1)


class PromoExpiryRequest(BaseModel):
    account_number: str = Field(..., min_length=1)


class PromoApplicationResponse(BaseModel):
    account_found: bool
    promo_found: bool | None = None
    applied: bool | None = None
    expected_discount_pct: int | None = None
    cross_border_note: str | None = None


class PromoExpiryResponse(BaseModel):
    account_found: bool
    promo_start_date: str | None = None
    promo_end_date: str | None = None
    current_price: float | None = None
    standard_price: float | None = None
    customer_notified: bool | None = None
    cross_border_note: str | None = None


def _hash_bucket(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest, 16) % 3


def _expected_discount(value: str) -> int:
    discounts = [10, 15, 20, 25]
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return discounts[int(digest, 16) % len(discounts)]


def _customer_country_note(country: str | None) -> str | None:
    if country and country != "United States":
        return (
            "This promotion is subject to cross-border pricing and compliance review "
            "for non-US market coverage."
        )
    return None


@router.post(
    "/tools/check-promo-application",
    response_model=PromoApplicationResponse,
    status_code=status.HTTP_200_OK,
)
async def check_promo_application(
    payload: PromoApplicationRequest,
    session: AsyncSession = Depends(get_session),
) -> PromoApplicationResponse:
    account_number = payload.account_number.strip()
    if not account_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="account_number is required and must be a non-empty string",
        )

    customer = (
        (await session.execute(select(Customer).where(Customer.account_number == account_number)))
        .scalars()
        .one_or_none()
    )
    if customer is None:
        return PromoApplicationResponse(account_found=False)

    bucket = _hash_bucket(account_number)
    promo_found: bool
    applied: bool | None = None

    if bucket == 0:
        promo_found = True
        applied = True
    elif bucket == 1:
        promo_found = True
        applied = False
    else:
        promo_found = False

    response = PromoApplicationResponse(
        account_found=True,
        promo_found=promo_found,
        applied=applied,
        expected_discount_pct=_expected_discount(account_number),
    )

    if customer.country is not None and customer.country != "United States":
        response.cross_border_note = _customer_country_note(customer.country)

    return response


@router.post(
    "/tools/check-promo-expiry",
    response_model=PromoExpiryResponse,
    status_code=status.HTTP_200_OK,
)
async def check_promo_expiry(
    payload: PromoExpiryRequest,
    session: AsyncSession = Depends(get_session),
) -> PromoExpiryResponse:
    account_number = payload.account_number.strip()
    if not account_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="account_number is required and must be a non-empty string",
        )

    customer = (
        (await session.execute(select(Customer).where(Customer.account_number == account_number)))
        .scalars()
        .one_or_none()
    )
    if customer is None:
        return PromoExpiryResponse(account_found=False)

    promo_start = customer.created_at.astimezone(timezone.utc) + timedelta(days=7)
    promo_end = promo_start + timedelta(days=365)
    now = datetime.now(timezone.utc)

    expired = promo_end < now
    standard_price = 99.99
    current_price = standard_price if expired else round(standard_price * 0.8, 2)
    customer_notified = _hash_bucket(account_number) % 2 == 0

    return PromoExpiryResponse(
        account_found=True,
        promo_start_date=promo_start.date().isoformat(),
        promo_end_date=promo_end.date().isoformat(),
        current_price=current_price,
        standard_price=standard_price,
        customer_notified=customer_notified,
        cross_border_note=_customer_country_note(customer.country),
    )
