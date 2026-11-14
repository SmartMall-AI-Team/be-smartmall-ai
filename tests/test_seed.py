from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database.models import Occurrence, OccurrenceEvent, Task
from app.seed import demo_id, seed


def test_demo_seed_is_idempotent_and_preserves_operator_edits(clean_database):
    engine = create_engine(clean_database)
    with Session(engine) as session:
        seed(session)
        occurrence = session.get(Occurrence, demo_id("occurrence"))
        occurrence.title = "Título editado pelo operador"
        session.commit()
        before = session.scalar(select(func.count()).select_from(OccurrenceEvent))
        seed(session)
        assert session.scalar(select(func.count()).select_from(Occurrence)) == 1
        assert session.scalar(select(func.count()).select_from(Task)) == 1
        assert session.scalar(select(func.count()).select_from(OccurrenceEvent)) == before
        assert occurrence.title == "Título editado pelo operador"
    engine.dispose()
