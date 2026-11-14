from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_serializer(
        "created_at",
        "updated_at",
        "due_at",
        "completed_at",
        "ai_reviewed_at",
        check_fields=False,
    )
    def serialize_utc(self, value: datetime | None) -> str | None:
        return (
            value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value is not None else None
        )


class PatchModel(APIModel):
    nullable_fields: ClassVar[set[str]] = set()

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("Informe pelo menos um campo para atualizar.")
        for name in self.model_fields_set:
            if getattr(self, name) is None and name not in self.nullable_fields:
                raise ValueError(f"O campo {name} não aceita null.")
        return self
