import hashlib
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comcast_mock.database import get_session
from comcast_mock.models import Customer

router = APIRouter()

AccountSegment = Literal["individual", "business", "enterprise"]


class AccountAccessRequest(BaseModel):
    identifier: str = Field(..., min_length=1)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("identifier must be a non-empty string")
        return value


class UnlockAccountRequest(AccountAccessRequest):
    requested_by: str | None = None

    @field_validator("requested_by")
    @classmethod
    def normalize_requested_by(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class LoginStatusResponse(BaseModel):
    account_found: bool
    locked: bool | None = None
    failed_attempts: int | None = None
    last_attempt: datetime | None = None
    account_segment: AccountSegment | None = None


class UnlockAccountResponse(BaseModel):
    account_found: bool
    requires_approval: bool | None = None
    simulated_result: str | None = None
    requested_by: str | None = None


async def _find_customer(identifier: str, session: AsyncSession) -> Customer | None:
    # Email is checked first so an identifier matching both fields follows the API contract.
    customer = (
        (await session.execute(select(Customer).where(Customer.email == identifier)))
        .scalars()
        .one_or_none()
    )
    if customer is not None:
        return customer

    return (
        (await session.execute(select(Customer).where(Customer.account_number == identifier)))
        .scalars()
        .one_or_none()
    )


def _hash_value(identifier: str) -> int:
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
    return int(digest, 16)


def _account_segment(hash_value: int) -> AccountSegment:
    # Replace this derived value with customers.segment when that column exists.
    return ("individual", "business", "enterprise")[hash_value % 3]


@router.post(
    "/tools/check-login-status",
    response_model=LoginStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def check_login_status(
    payload: AccountAccessRequest,
    session: AsyncSession = Depends(get_session),
) -> LoginStatusResponse:
    customer = await _find_customer(payload.identifier, session)
    if customer is None:
        return LoginStatusResponse(account_found=False)

    hash_value = _hash_value(payload.identifier)
    locked = hash_value % 3 == 0
    if not locked:
        return LoginStatusResponse(
            account_found=True,
            locked=False,
            failed_attempts=0,
            last_attempt=None,
            account_segment=_account_segment(hash_value),
        )

    return LoginStatusResponse(
        account_found=True,
        locked=True,
        failed_attempts=hash_value % 5 + 3,
        last_attempt=datetime.now(UTC) - timedelta(minutes=hash_value % 60 + 5),
        account_segment=_account_segment(hash_value),
    )


@router.post(
    "/tools/unlock-account",
    response_model=UnlockAccountResponse,
    status_code=status.HTTP_200_OK,
)
async def unlock_account(
    payload: UnlockAccountRequest,
    session: AsyncSession = Depends(get_session),
) -> UnlockAccountResponse:
    customer = await _find_customer(payload.identifier, session)
    if customer is None:
        return UnlockAccountResponse(account_found=False)

    return UnlockAccountResponse(
        account_found=True,
        requires_approval=True,
        simulated_result="would_unlock_ok",
        requested_by=payload.requested_by,
    )