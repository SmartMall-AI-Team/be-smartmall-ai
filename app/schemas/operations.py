from typing import Annotated, Any
from uuid import UUID

from pydantic import AwareDatetime, StringConstraints

from app.core.enums import EquipmentStatus, TaskStatus, UserRole
from app.schemas.common import APIModel, PatchModel

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Details = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class UserCreate(APIModel):
    name: Name
    role: UserRole = UserRole.TECHNICIAN


class UserRead(UserCreate):
    id: UUID
    is_active: bool


class EquipmentCreate(APIModel):
    name: Name
    type: ShortText
    location: Name
    operational_status: EquipmentStatus = EquipmentStatus.OPERATIONAL


class EquipmentPatch(PatchModel):
    name: Name | None = None
    type: ShortText | None = None
    location: Name | None = None
    operational_status: EquipmentStatus | None = None


class EquipmentRead(EquipmentCreate):
    id: UUID


class TaskCreate(APIModel):
    occurrence_id: UUID
    title: Name
    details: Details | None = None
    assigned_to: UUID
    due_at: AwareDatetime


class TaskPatch(PatchModel):
    nullable_fields = {"details"}

    title: Name | None = None
    details: Details | None = None
    assigned_to: UUID | None = None
    due_at: AwareDatetime | None = None
    status: TaskStatus | None = None


class TaskRead(TaskCreate):
    id: UUID
    status: TaskStatus
    completed_at: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class OccurrenceEventRead(APIModel):
    id: UUID
    occurrence_id: UUID
    task_id: UUID | None
    event_type: str
    previous_status: str | None
    new_status: str | None
    details: dict[str, Any]
    created_at: AwareDatetime


class DashboardSummary(APIModel):
    occurrences_total: int
    occurrences_by_status: dict[str, int]
    occurrences_by_priority: dict[str, int]
    tasks_pending: int
    equipment_by_status: dict[str, int]
