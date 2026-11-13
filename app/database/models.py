from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import Category, EquipmentStatus, OccurrenceStatus, Priority
from app.database.base import Base


def enum_column(enum: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda values: [value.value for value in values],
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


class Equipment(Base):
    """Base para validar vínculos; o módulo de cadastro será entregue depois."""

    __tablename__ = "equipment"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(240))
    type: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(240))
    operational_status: Mapped[EquipmentStatus] = mapped_column(
        enum_column(EquipmentStatus, "equipment_status"),
        default=EquipmentStatus.OPERATIONAL,
        server_default="operational",
    )


class Occurrence(Base):
    __tablename__ = "occurrences"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(240))
    category: Mapped[Category | None] = mapped_column(enum_column(Category, "category"))
    equipment_id: Mapped[UUID | None] = mapped_column(ForeignKey("equipment.id"))
    status: Mapped[OccurrenceStatus] = mapped_column(
        enum_column(OccurrenceStatus, "occurrence_status"),
        default=OccurrenceStatus.OPEN,
        server_default="open",
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        enum_column(Priority, "priority"),
        default=Priority.UNTRIAGED,
        server_default="untriaged",
        index=True,
    )
    ai_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), onupdate=utc_now
    )
