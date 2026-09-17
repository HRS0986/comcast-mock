import hashlib
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter()

DomesticMethod = Literal["original_payment_method", "bank_transfer", "statement_credit"]
InternationalMethod = Literal["international_bank_transfer", "original_payment_method"]
AccountSegment = Literal["individual", "business"]


class DomesticRefundRequest(BaseModel):
    account_number: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    currency: Literal["USD"]
    method: DomesticMethod
    account_segment: AccountSegment = "individual"

    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("account_number must be a non-empty string")
        return value


class InternationalRefundRequest(BaseModel):
    account_number: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=1)
    destination_country: str = Field(..., min_length=1)
    method: InternationalMethod
    account_segment: AccountSegment = "individual"

    @field_validator("account_number", "currency", "destination_country")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must be a non-empty string")
        return value


class RefundStatusRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1)

    @field_validator("transaction_id")
    @classmethod
    def validate_transaction_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("transaction_id must be a non-empty string")
        return value


class DomesticRefundResponse(BaseModel):
    transaction_id: str
    requires_approval: bool
    estimated_days: str
    approval_note: str | None = None


class InternationalRefundResponse(BaseModel):
    transaction_id: str
    requires_approval: bool
    estimated_days: str
    possible_fees: bool
    fee_note: str
    approval_note: str | None = None


class RefundStatusResponse(BaseModel):
    found: bool
    status: str | None = None
    last_updated: datetime | None = None


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12].upper()


def _approval_note(account_segment: AccountSegment, amount: float) -> str | None:
    if account_segment == "business" and amount > 500:
        return "Business refunds above $500 require manager approval."
    return None


@router.post(
    "/tools/initiate-domestic-refund",
    response_model=DomesticRefundResponse,
    status_code=status.HTTP_200_OK,
)
async def initiate_domestic_refund(payload: DomesticRefundRequest) -> DomesticRefundResponse:
    transaction_id = f"RFD-DOM-{_short_hash(f'{payload.account_number}|{payload.amount:.2f}') }"
    return DomesticRefundResponse(
        transaction_id=transaction_id,
        requires_approval=True,
        estimated_days="3-5 business days",
        approval_note=_approval_note(payload.account_segment, payload.amount),
    )


@router.post(
    "/tools/initiate-international-refund",
    response_model=InternationalRefundResponse,
    status_code=status.HTTP_200_OK,
)
async def initiate_international_refund(
    payload: InternationalRefundRequest,
) -> InternationalRefundResponse:
    hash_input = f"{payload.account_number}|{payload.amount:.2f}|{payload.destination_country}"
    transaction_id = f"RFD-INTL-{_short_hash(hash_input)}"
    return InternationalRefundResponse(
        transaction_id=transaction_id,
        requires_approval=True,
        estimated_days="7-12 business days",
        possible_fees=True,
        fee_note="International refunds may incur exchange-rate or bank processing fees.",
        approval_note=_approval_note(payload.account_segment, payload.amount),
    )


@router.post(
    "/tools/check-refund-status",
    response_model=RefundStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def check_refund_status(payload: RefundStatusRequest) -> RefundStatusResponse:
    if not (
        payload.transaction_id.startswith("RFD-DOM-")
        or payload.transaction_id.startswith("RFD-INTL-")
    ):
        return RefundStatusResponse(found=False)

    status_by_bucket = ["initiated", "in_review", "in_transit", "completed"]
    digest = hashlib.sha256(payload.transaction_id.encode("utf-8")).hexdigest()
    refund_status = status_by_bucket[int(digest, 16) % len(status_by_bucket)]
    return RefundStatusResponse(
        found=True,
        status=refund_status,
        last_updated=datetime.now(UTC),
    )