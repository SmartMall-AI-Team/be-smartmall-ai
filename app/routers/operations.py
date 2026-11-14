from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.enums import EquipmentStatus, TaskStatus, UserRole
from app.database.models import Equipment, Task
from app.database.session import DatabaseSession
from app.schemas.occurrences import OccurrenceRead
from app.schemas.operations import (
    DashboardSummary,
    EquipmentCreate,
    EquipmentPatch,
    EquipmentRead,
    TaskCreate,
    TaskPatch,
    TaskRead,
    UserCreate,
    UserRead,
)
from app.services import occurrences
from app.services import operations as service

router = APIRouter(prefix="/api/v1")


@router.get("/users", response_model=list[UserRead], tags=["Responsáveis"])
def list_users(session: DatabaseSession, role: UserRole | None = None):
    return service.list_users(session, role)


@router.post("/users", response_model=UserRead, status_code=201, tags=["Responsáveis"])
def create_user(data: UserCreate, session: DatabaseSession):
    return service.create_user(session, data)


@router.get("/equipment", response_model=list[EquipmentRead], tags=["Equipamentos"])
def list_equipment(
    session: DatabaseSession,
    operational_status: EquipmentStatus | None = None,
    location: Annotated[str | None, Query(min_length=1, max_length=240)] = None,
):
    query = select(Equipment).order_by(Equipment.name, Equipment.id)
    if operational_status is not None:
        query = query.where(Equipment.operational_status == operational_status)
    if location is not None:
        query = query.where(Equipment.location.icontains(location, autoescape=True))
    return list(session.scalars(query))


@router.post("/equipment", response_model=EquipmentRead, status_code=201, tags=["Equipamentos"])
def create_equipment(data: EquipmentCreate, session: DatabaseSession):
    return service.create_equipment(session, data)


@router.get("/equipment/{equipment_id}", response_model=EquipmentRead, tags=["Equipamentos"])
def get_equipment(equipment_id: UUID, session: DatabaseSession):
    return service.get_equipment(session, equipment_id)


@router.patch("/equipment/{equipment_id}", response_model=EquipmentRead, tags=["Equipamentos"])
def update_equipment(equipment_id: UUID, data: EquipmentPatch, session: DatabaseSession):
    return service.update_equipment(session, equipment_id, data)


@router.get(
    "/equipment/{equipment_id}/occurrences",
    response_model=list[OccurrenceRead],
    tags=["Equipamentos"],
)
def equipment_occurrences(equipment_id: UUID, session: DatabaseSession):
    service.get_equipment(session, equipment_id)
    return occurrences.list_occurrences(session, equipment_id=equipment_id)


@router.get("/tasks", response_model=list[TaskRead], tags=["Tarefas"])
def list_tasks(
    session: DatabaseSession,
    status: TaskStatus | None = None,
    assigned_to: UUID | None = None,
    occurrence_id: UUID | None = None,
):
    query = select(Task).order_by(Task.due_at, Task.id)
    for field, value in (
        (Task.status, status),
        (Task.assigned_to, assigned_to),
        (Task.occurrence_id, occurrence_id),
    ):
        if value is not None:
            query = query.where(field == value)
    return list(session.scalars(query))


@router.post("/tasks", response_model=TaskRead, status_code=201, tags=["Tarefas"])
def create_task(data: TaskCreate, session: DatabaseSession):
    return service.create_task(session, data)


@router.get("/tasks/{task_id}", response_model=TaskRead, tags=["Tarefas"])
def get_task(task_id: UUID, session: DatabaseSession):
    return service.get_task(session, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskRead, tags=["Tarefas"])
def update_task(task_id: UUID, data: TaskPatch, session: DatabaseSession):
    return service.update_task(session, task_id, data)


@router.get("/dashboard/summary", response_model=DashboardSummary, tags=["Dashboard"])
def dashboard(session: DatabaseSession):
    return service.dashboard_summary(session)
