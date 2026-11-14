"""Dados fictícios idempotentes para uma demonstração local, sem chamadas de IA."""

from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import Category, TaskStatus, UserRole
from app.database.models import Equipment, Occurrence, Task, User, utc_now
from app.database.session import create_database_engine
from app.schemas.operations import TaskPatch
from app.services.history import record_event
from app.services.operations import update_task


def demo_id(name: str):
    return uuid5(NAMESPACE_URL, "https://smartmall.invalid/demo/" + name)


def seed(session: Session) -> None:
    user_id, equipment_id = demo_id("technician"), demo_id("equipment")
    if session.get(User, user_id) is None:
        session.add(User(id=user_id, name="Técnica fictícia — Ana", role=UserRole.TECHNICIAN))
    if session.get(Equipment, equipment_id) is None:
        session.add(
            Equipment(
                id=equipment_id,
                name="AC fictício 01",
                type="Climatização",
                location="Praça fictícia",
            )
        )
    session.flush()
    occurrence_id = demo_id("occurrence")
    if session.get(Occurrence, occurrence_id) is None:
        session.add(
            Occurrence(
                id=occurrence_id,
                title="Exemplo fictício: ambiente sem refrigeração",
                description="Cenário de demonstração: equipamento ligado sem resfriar o ambiente.",
                location="Praça fictícia",
                category=Category.HVAC,
                equipment_id=equipment_id,
            )
        )
        session.flush()
        record_event(session, occurrence_id, "occurrence_created", new_status="open")
    task_id = demo_id("task")
    if session.get(Task, task_id) is None:
        occurrence = session.get(Occurrence, occurrence_id)
        if occurrence.status == "resolved":
            # Re-running the seed never reopens an operator's resolved occurrence.
            session.commit()
            return
        session.add(
            Task(
                id=task_id,
                occurrence_id=occurrence_id,
                title="Inspeção fictícia pela equipe técnica",
                assigned_to=user_id,
                due_at=utc_now() + timedelta(days=1),
            )
        )
        session.flush()
        record_event(session, occurrence_id, "task_created", task_id=task_id, new_status="pending")
        session.commit()
        update_task(session, task_id, TaskPatch(status=TaskStatus.IN_PROGRESS))
    else:
        session.commit()


def main() -> None:
    settings = Settings()
    if settings.app_env not in {"development", "demo"}:
        raise SystemExit("O seed só é permitido com APP_ENV=development ou demo.")
    engine = create_database_engine(settings.database_url)
    try:
        with Session(engine) as session:
            seed(session)
        print("Dados fictícios disponíveis; reexecução preserva os registros existentes.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
