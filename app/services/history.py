from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import OccurrenceEvent


def record_event(
    session: Session,
    occurrence_id: UUID,
    event_type: str,
    *,
    task_id: UUID | None = None,
    previous_status: str | None = None,
    new_status: str | None = None,
    details: dict | None = None,
) -> None:
    session.add(
        OccurrenceEvent(
            occurrence_id=occurrence_id,
            event_type=event_type,
            task_id=task_id,
            previous_status=previous_status,
            new_status=new_status,
            details=details or {},
        )
    )


def list_history(session: Session, occurrence_id: UUID) -> list[OccurrenceEvent]:
    return list(
        session.scalars(
            select(OccurrenceEvent)
            .where(OccurrenceEvent.occurrence_id == occurrence_id)
            .order_by(OccurrenceEvent.created_at, OccurrenceEvent.id)
        )
    )
