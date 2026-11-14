from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Category, OccurrenceStatus, Priority, TaskStatus
from app.database.models import Equipment, Occurrence, Task, utc_now
from app.schemas.occurrences import OccurrenceCreate, OccurrencePatch
from app.services.history import record_event


def create_occurrence(session: Session, data: OccurrenceCreate) -> Occurrence:
    if data.equipment_id is not None and session.get(Equipment, data.equipment_id) is None:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado.")
    occurrence = Occurrence(**data.model_dump())
    session.add(occurrence)
    session.flush()
    record_event(session, occurrence.id, "occurrence_created", new_status="open")
    session.commit()
    session.refresh(occurrence)
    return occurrence


def list_occurrences(
    session: Session,
    status_filter: OccurrenceStatus | None = None,
    priority: Priority | None = None,
    category: Category | None = None,
    equipment_id: UUID | None = None,
    location: str | None = None,
) -> list[Occurrence]:
    query = select(Occurrence).order_by(Occurrence.created_at.desc(), Occurrence.id.desc())
    if status_filter is not None:
        query = query.where(Occurrence.status == status_filter)
    if priority is not None:
        query = query.where(Occurrence.priority == priority)
    if category is not None:
        query = query.where(Occurrence.category == category)
    if equipment_id is not None:
        query = query.where(Occurrence.equipment_id == equipment_id)
    if location is not None:
        query = query.where(Occurrence.location.icontains(location, autoescape=True))
    return list(session.scalars(query))


def get_occurrence(session: Session, occurrence_id: UUID, *, lock: bool = False) -> Occurrence:
    query = select(Occurrence).where(Occurrence.id == occurrence_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    occurrence = session.scalar(query)
    if occurrence is None:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada.")
    return occurrence


def update_occurrence(session: Session, occurrence_id: UUID, data: OccurrencePatch) -> Occurrence:
    occurrence = get_occurrence(session, occurrence_id, lock=True)
    changes = data.model_dump(exclude_unset=True)
    confirm_review = changes.pop("confirm_ai_review", False)
    if changes.get("equipment_id") is not None:
        if session.get(Equipment, changes["equipment_id"]) is None:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado.")
    if changes.get("status") == OccurrenceStatus.RESOLVED:
        pending = session.scalar(
            select(Task.id)
            .where(Task.occurrence_id == occurrence_id, Task.status != TaskStatus.COMPLETED)
            .limit(1)
        )
        if pending is not None:
            raise HTTPException(
                status_code=409, detail="Conclua as tarefas antes de resolver a ocorrência."
            )
    changed = {key: value for key, value in changes.items() if getattr(occurrence, key) != value}
    source_changed = bool(set(changed) & {"title", "description", "location", "equipment_id"})
    if confirm_review and (occurrence.ai_analysis is None or source_changed):
        raise HTTPException(
            status_code=409, detail="Analise a ocorrência atual antes de confirmar a revisão."
        )
    old_status = occurrence.status
    for key, value in changed.items():
        setattr(occurrence, key, value)
    if source_changed:
        occurrence.ai_analysis = None
        occurrence.ai_reviewed_at = None
    if changed:
        record_event(
            session, occurrence_id, "occurrence_updated", details={"fields": sorted(changed)}
        )
    if old_status != occurrence.status:
        record_event(
            session,
            occurrence_id,
            "occurrence_status_changed",
            previous_status=old_status,
            new_status=occurrence.status,
        )
    if confirm_review:
        occurrence.ai_reviewed_at = utc_now()
        record_event(session, occurrence_id, "ai_reviewed")
    if changed or confirm_review:
        occurrence.updated_at = utc_now()
        session.commit()
        session.refresh(occurrence)
    return occurrence
