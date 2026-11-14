from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

from app.core.enums import Category, OccurrenceStatus, Priority
from app.database.session import DatabaseSession
from app.schemas.analysis import AIAnalysis
from app.schemas.occurrences import (
    OccurrenceCreate,
    OccurrenceDetail,
    OccurrencePatch,
    OccurrenceRead,
)
from app.schemas.operations import OccurrenceEventRead
from app.services import occurrences as service
from app.services.analysis import analyze_occurrence
from app.services.history import list_history

router = APIRouter(prefix="/api/v1/occurrences", tags=["Ocorrências"])


@router.post("", response_model=OccurrenceRead, status_code=status.HTTP_201_CREATED)
def create_occurrence(
    data: OccurrenceCreate, request: Request, response: Response, session: DatabaseSession
):
    occurrence = service.create_occurrence(session, data)
    response.headers["Location"] = str(
        request.url_for("get_occurrence", occurrence_id=str(occurrence.id))
    )
    return occurrence


@router.get("", response_model=list[OccurrenceRead])
def list_occurrences(
    session: DatabaseSession,
    status: OccurrenceStatus | None = None,
    priority: Priority | None = None,
    category: Category | None = None,
    equipment_id: UUID | None = None,
    location: Annotated[str | None, Query(min_length=1, max_length=240)] = None,
):
    return service.list_occurrences(
        session,
        status_filter=status,
        priority=priority,
        category=category,
        equipment_id=equipment_id,
        location=location,
    )


@router.get("/{occurrence_id}", response_model=OccurrenceDetail)
def get_occurrence(occurrence_id: UUID, session: DatabaseSession):
    return service.get_occurrence(session, occurrence_id)


@router.patch("/{occurrence_id}", response_model=OccurrenceDetail)
def update_occurrence(occurrence_id: UUID, data: OccurrencePatch, session: DatabaseSession):
    return service.update_occurrence(session, occurrence_id, data)


@router.get("/{occurrence_id}/history", response_model=list[OccurrenceEventRead])
def occurrence_history(occurrence_id: UUID, session: DatabaseSession):
    service.get_occurrence(session, occurrence_id)
    return list_history(session, occurrence_id)


@router.post("/{occurrence_id}/analyze", response_model=AIAnalysis)
def analyze(occurrence_id: UUID, request: Request, session: DatabaseSession):
    return analyze_occurrence(session, occurrence_id, request.app.state.settings)
