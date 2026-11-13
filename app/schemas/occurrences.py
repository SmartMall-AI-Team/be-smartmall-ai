from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
)

from app.core.enums import Category, OccurrenceStatus, Priority

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


class OccurrenceRead(BaseModel):
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

    @field_serializer("created_at", "updated_at")
    def serialize_utc(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat()


class OccurrenceDetail(OccurrenceRead):
    # Tasks will have their own schema when the task endpoints are implemented.
    tasks: list[dict[str, Any]] = Field(default_factory=list)
