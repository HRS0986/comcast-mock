import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from comcast_mock.database import Base

# JSONB on PostgreSQL (per schema), JSON on SQLite (local dev fallback).
JsonBinary = JSON().with_variant(JSONB(), "postgresql")


def _gen_id() -> str:
    return str(uuid.uuid4())


class TicketStatus(enum.StrEnum):
    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class SubCategory(Base):
    __tablename__ = "sub_categories"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("categories.id"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)

    category: Mapped["Category"] = relationship()


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(Text)
    account_number: Mapped[str | None] = mapped_column(Text, unique=True, index=True)
    country: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("categories.id")
    )
    sub_category_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("sub_categories.id")
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=TicketStatus.NEW.value
    )

    category: Mapped[Optional["Category"]] = relationship()
    sub_category: Mapped[Optional["SubCategory"]] = relationship()


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mcp_tools: Mapped[list] = mapped_column(JsonBinary, nullable=False, default=list)
    inputs: Mapped[list] = mapped_column(JsonBinary, nullable=False, default=list)


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JsonBinary, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)

