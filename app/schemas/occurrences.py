from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.core.enums import Category, OccurrenceStatus, Priority
from app.schemas.common import APIModel, PatchModel
from app.schemas.operations import Details, Name, TaskRead

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]
Location = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]


class OccurrenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description
    location: Location
    category: Category | None = None
    equipment_id: UUID | None = None


class OccurrenceRead(APIModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    location: str
    category: Category | None
    equipment_id: UUID | None
    status: OccurrenceStatus
    priority: Priority
    created_at: AwareDatetime
    updated_at: AwareDatetime
    ai_analysis: dict[str, Any] | None
    assigned_team: str | None
    recommendation: str | None
    ai_reviewed_at: AwareDatetime | None


class OccurrenceDetail(OccurrenceRead):
    tasks: list[TaskRead] = Field(default_factory=list)


class OccurrencePatch(PatchModel):
    nullable_fields = {"category", "equipment_id", "assigned_team", "recommendation"}

    title: Title | None = None
    description: Description | None = None
    location: Location | None = None
    category: Category | None = None
    equipment_id: UUID | None = None
    status: OccurrenceStatus | None = None
    priority: Priority | None = None
    assigned_team: Name | None = None
    recommendation: Details | None = None
    confirm_ai_review: bool | None = None
