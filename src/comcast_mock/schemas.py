from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone: str | None = None
    account_number: str | None = None
    country: str | None = None
    status: str
    created_at: datetime


class CustomerCreate(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    account_number: str | None = None
    country: str | None = None
    status: str = "active"


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class SubCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category_id: int
    description: str | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    category_id: int | None = None
    sub_category_id: int | None = None
    status: str


class TicketDetailOut(TicketOut):
    category: CategoryOut | None = None
    sub_category: SubCategoryOut | None = None


class TicketIngestRequest(BaseModel):
    title: str
    description: str | None = None
    category_id: int | None = None
    sub_category_id: int | None = None


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    category_id: int | None = None
    sub_category_id: int | None = None


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class AnalyticsSummaryOut(BaseModel):
    total_tickets: int
    by_category: dict[int, int] = Field(default_factory=dict)
    by_sub_category: dict[int, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)


class KnowledgeBaseCreateRequest(BaseModel):
    sub_category_id: int
    content: str
    metadata: dict[str, Any] | None = None


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sub_category_id: int
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_value")
