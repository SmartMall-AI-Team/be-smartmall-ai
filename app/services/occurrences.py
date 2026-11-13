from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import OccurrenceStatus, Priority
from app.database.models import Equipment, Occurrence
from app.schemas.occurrences import OccurrenceCreate


def create_occurrence(session: Session, data: OccurrenceCreate) -> Occurrence:
    if data.equipment_id is not None and session.get(Equipment, data.equipment_id) is None:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado.")
    occurrence = Occurrence(**data.model_dump())
    session.add(occurrence)
    session.commit()
    session.refresh(occurrence)
    return occurrence


def list_occurrences(
    session: Session,
    status_filter: OccurrenceStatus | None = None,
    priority: Priority | None = None,
) -> list[Occurrence]:
    query = select(Occurrence).order_by(Occurrence.created_at.desc(), Occurrence.id.desc())
    if status_filter is not None:
        query = query.where(Occurrence.status == status_filter)
    if priority is not None:
        query = query.where(Occurrence.priority == priority)
    return list(session.scalars(query))


def get_occurrence(session: Session, occurrence_id: UUID) -> Occurrence:
    occurrence = session.get(Occurrence, occurrence_id)
    if occurrence is None:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada.")
    return occurrence
