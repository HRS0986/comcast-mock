import enum
from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from comcast_mock.database import Base

# JSONB on PostgreSQL (per schema), JSON on SQLite (local dev fallback).
JsonBinary = JSON().with_variant(JSONB(), "postgresql")


class TicketStatus(enum.StrEnum):
    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class SubCategory(Base):
    __tablename__ = "sub_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    category: Mapped["Category"] = relationship()


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"))
    sub_category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sub_categories.id"))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=TicketStatus.NEW.value)

    category: Mapped[Optional["Category"]] = relationship()
    sub_category: Mapped[Optional["SubCategory"]] = relationship()


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sub_category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sub_categories.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JsonBinary, nullable=True)
    metadata_value: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JsonBinary, nullable=True
    )
