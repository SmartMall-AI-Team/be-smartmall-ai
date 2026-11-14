from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import EquipmentStatus, OccurrenceStatus, Priority, TaskStatus, UserRole
from app.database.models import Equipment, Occurrence, Task, User, utc_now
from app.schemas.operations import (
    EquipmentCreate,
    EquipmentPatch,
    TaskCreate,
    TaskPatch,
    UserCreate,
)
from app.services.history import record_event
from app.services.occurrences import get_occurrence


def save(session: Session, model):
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def get_equipment(session: Session, equipment_id: UUID) -> Equipment:
    equipment = session.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado.")
    return equipment


def create_equipment(session: Session, data: EquipmentCreate) -> Equipment:
    return save(session, Equipment(**data.model_dump()))


def update_equipment(session: Session, equipment_id: UUID, data: EquipmentPatch) -> Equipment:
    equipment = get_equipment(session, equipment_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(equipment, key, value)
    return save(session, equipment)


def create_user(session: Session, data: UserCreate) -> User:
    return save(session, User(**data.model_dump()))


def list_users(session: Session, role: UserRole | None = None) -> list[User]:
    query = select(User).where(User.is_active.is_(True)).order_by(User.name, User.id)
    if role is not None:
        query = query.where(User.role == role)
    return list(session.scalars(query))


def validate_assignee(session: Session, assigned_to: UUID) -> None:
    user = session.get(User, assigned_to)
    if user is None:
        raise HTTPException(status_code=404, detail="Responsável não encontrado.")
    if not user.is_active:
        raise HTTPException(status_code=409, detail="Responsável inativo.")


def create_task(session: Session, data: TaskCreate) -> Task:
    occurrence = get_occurrence(session, data.occurrence_id, lock=True)
    if occurrence.status == OccurrenceStatus.RESOLVED:
        raise HTTPException(
            status_code=409, detail="Reabra a ocorrência antes de criar uma tarefa."
        )
    validate_assignee(session, data.assigned_to)
    task = Task(**data.model_dump())
    session.add(task)
    session.flush()
    record_event(session, occurrence.id, "task_created", task_id=task.id, new_status="pending")
    return save(session, task)


def get_task(session: Session, task_id: UUID) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return task


def update_task(session: Session, task_id: UUID, data: TaskPatch) -> Task:
    task = get_task(session, task_id)
    occurrence = get_occurrence(session, task.occurrence_id, lock=True)
    task = session.scalar(
        select(Task)
        .where(Task.id == task_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    changes = data.model_dump(exclude_unset=True)
    if "assigned_to" in changes:
        validate_assignee(session, changes["assigned_to"])
    previous = task.status
    following = changes.get("status", previous)
    transitions = {
        TaskStatus.PENDING: {TaskStatus.IN_PROGRESS},
        TaskStatus.IN_PROGRESS: {TaskStatus.PENDING, TaskStatus.COMPLETED},
        TaskStatus.COMPLETED: {TaskStatus.IN_PROGRESS},
    }
    if following != previous and following not in transitions[previous]:
        raise HTTPException(status_code=409, detail="Transição de tarefa inválida.")
    if following != TaskStatus.COMPLETED and occurrence.status == OccurrenceStatus.RESOLVED:
        raise HTTPException(
            status_code=409, detail="Reabra a ocorrência antes de reativar uma tarefa."
        )
    changed = {key: value for key, value in changes.items() if getattr(task, key) != value}
    if not changed:
        return task
    for key, value in changed.items():
        setattr(task, key, value)
    if previous != following:
        task.completed_at = utc_now() if following == TaskStatus.COMPLETED else None
        record_event(
            session,
            occurrence.id,
            "task_status_changed",
            task_id=task.id,
            previous_status=previous,
            new_status=following,
        )
    else:
        record_event(
            session,
            occurrence.id,
            "task_updated",
            task_id=task.id,
            details={"fields": sorted(changed)},
        )
    if following == TaskStatus.IN_PROGRESS and occurrence.status == OccurrenceStatus.OPEN:
        record_event(
            session,
            occurrence.id,
            "occurrence_status_changed",
            task_id=task.id,
            previous_status=occurrence.status,
            new_status="in_progress",
        )
        occurrence.status = OccurrenceStatus.IN_PROGRESS
    return save(session, task)


def dashboard_summary(session: Session) -> dict:
    session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    statuses = {status.value: 0 for status in OccurrenceStatus}
    priorities = {priority.value: 0 for priority in Priority}
    equipment = {status.value: 0 for status in EquipmentStatus}
    for status, count in session.execute(
        select(Occurrence.status, func.count()).group_by(Occurrence.status)
    ):
        statuses[status.value] = count
    for priority, count in session.execute(
        select(Occurrence.priority, func.count()).group_by(Occurrence.priority)
    ):
        priorities[priority.value] = count
    for status, count in session.execute(
        select(Equipment.operational_status, func.count()).group_by(Equipment.operational_status)
    ):
        equipment[status.value] = count
    pending = session.scalar(
        select(func.count()).select_from(Task).where(Task.status != TaskStatus.COMPLETED)
    )
    return {
        "occurrences_total": sum(statuses.values()),
        "occurrences_by_status": statuses,
        "occurrences_by_priority": priorities,
        "tasks_pending": pending,
        "equipment_by_status": equipment,
    }
