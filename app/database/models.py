from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    Category,
    EquipmentStatus,
    OccurrenceStatus,
    Priority,
    TaskStatus,
    UserRole,
)
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
    assigned_team: Mapped[str | None] = mapped_column(String(240))
    recommendation: Mapped[str | None] = mapped_column(Text)
    ai_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tasks: Mapped[list["Task"]] = relationship(back_populates="occurrence", lazy="selectin")


class User(Base):
    """Cadastro de responsáveis; não representa uma sessão autenticada."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(240))
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole, "user_role"))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    occurrence_id: Mapped[UUID] = mapped_column(ForeignKey("occurrences.id"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    details: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[TaskStatus] = mapped_column(
        enum_column(TaskStatus, "task_status"),
        default=TaskStatus.PENDING,
        server_default="pending",
        index=True,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), onupdate=utc_now
    )
    occurrence: Mapped[Occurrence] = relationship(back_populates="tasks")


class OccurrenceEvent(Base):
    __tablename__ = "occurrence_history"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    occurrence_id: Mapped[UUID] = mapped_column(ForeignKey("occurrences.id"), index=True)
    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("tasks.id"))
    event_type: Mapped[str] = mapped_column(String(80))
    previous_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str | None] = mapped_column(String(40))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
