from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from app.core.enums import OccurrenceStatus, Priority
from app.database.session import DatabaseSession
from app.schemas.occurrences import OccurrenceCreate, OccurrenceDetail, OccurrenceRead
from app.services import occurrences as service

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
):
    return service.list_occurrences(session, status_filter=status, priority=priority)


@router.get("/{occurrence_id}", response_model=OccurrenceDetail)
def get_occurrence(occurrence_id: UUID, session: DatabaseSession):
    return service.get_occurrence(session, occurrence_id)
