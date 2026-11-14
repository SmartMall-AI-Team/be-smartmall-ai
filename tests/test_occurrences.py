from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import OccurrenceStatus, Priority
from app.database.models import Equipment, Occurrence
from app.main import create_app

PAYLOAD = {
    "title": "Ar-condicionado sem refrigeração",
    "description": "Equipamento ligado, mas sem resfriar a praça de alimentação.",
    "location": "Praça de alimentação",
}


def test_create_list_and_detail_survive_new_application_instance(clean_database):
    settings = Settings(_env_file=None, database_url=clean_database)
    first = create_app(settings)
    with TestClient(first) as client:
        response = client.post("/api/v1/occurrences", json={**PAYLOAD, "category": "hvac"})
        assert response.status_code == 201
        created = response.json()
        UUID(created["id"])
        assert response.headers["location"].endswith("/occurrences/" + created["id"])
        assert created["status"] == "open"
        assert created["priority"] == "untriaged"
        assert created["ai_analysis"] is None
        assert created["equipment_id"] is None
        assert datetime.fromisoformat(created["created_at"]).utcoffset() == timedelta(0)
        assert datetime.fromisoformat(created["updated_at"]).utcoffset() == timedelta(0)

    # New app + new engine + new connection pool, reading the same PostgreSQL database.
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/occurrences").json() == [created]
        detail = client.get("/api/v1/occurrences/" + created["id"])
        assert detail.status_code == 200
        assert detail.json() == {**created, "tasks": []}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "   "),
        ("description", "\n\t"),
        ("location", ""),
        ("title", "a" * 241),
        ("description", "a" * 5001),
        ("location", "a" * 241),
        ("category", "not_a_category"),
        ("equipment_id", "not-a-uuid"),
        ("status", "resolved"),
        ("id", str(uuid4())),
        ("priority", "critical"),
    ],
)
def test_invalid_input_and_server_controlled_fields_are_not_persisted(client, field, value):
    response = client.post("/api/v1/occurrences", json={**PAYLOAD, field: value})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert client.get("/api/v1/occurrences").json() == []


@pytest.mark.parametrize("field", ["title", "description", "location"])
def test_required_field_cannot_be_omitted(client, field):
    payload = {key: value for key, value in PAYLOAD.items() if key != field}
    assert client.post("/api/v1/occurrences", json=payload).status_code == 422


def test_optional_fields_and_trimmed_text(client):
    response = client.post("/api/v1/occurrences", json={**PAYLOAD, "title": "  Lâmpada apagada  "})
    assert response.status_code == 201
    assert response.json()["title"] == "Lâmpada apagada"
    assert response.json()["category"] is None


def test_missing_occurrence_and_invalid_identifier(client):
    response = client.get(f"/api/v1/occurrences/{uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Ocorrência não encontrada."}
    assert client.get("/api/v1/occurrences/not-a-uuid").status_code == 422


def test_equipment_reference_must_exist(client, clean_database):
    response = client.post("/api/v1/occurrences", json={**PAYLOAD, "equipment_id": str(uuid4())})
    assert response.status_code == 404
    assert response.json() == {"detail": "Equipamento não encontrado."}
    assert client.get("/api/v1/occurrences").json() == []

    engine = create_engine(clean_database)
    with Session(engine) as session:
        equipment = Equipment(name="AC fictício 01", type="Ar-condicionado", location="Praça")
        session.add(equipment)
        session.commit()
        equipment_id = str(equipment.id)
    engine.dispose()
    response = client.post("/api/v1/occurrences", json={**PAYLOAD, "equipment_id": equipment_id})
    assert response.status_code == 201
    assert response.json()["equipment_id"] == equipment_id


def test_filters_are_combined_and_order_is_newest_first(client, clean_database):
    engine = create_engine(clean_database)
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add_all(
            [
                Occurrence(
                    **PAYLOAD,
                    status=OccurrenceStatus.OPEN,
                    priority=Priority.HIGH,
                    created_at=now - timedelta(minutes=1),
                ),
                Occurrence(
                    **PAYLOAD,
                    status=OccurrenceStatus.RESOLVED,
                    priority=Priority.HIGH,
                    created_at=now,
                ),
                Occurrence(
                    **PAYLOAD,
                    status=OccurrenceStatus.OPEN,
                    priority=Priority.LOW,
                    created_at=now + timedelta(minutes=1),
                ),
            ]
        )
        session.commit()
    engine.dispose()
    all_items = client.get("/api/v1/occurrences").json()
    assert [item["priority"] for item in all_items] == ["low", "high", "high"]
    filtered = client.get("/api/v1/occurrences?status=open&priority=high").json()
    assert len(filtered) == 1
    assert filtered[0]["id"] == all_items[-1]["id"]
    assert client.get("/api/v1/occurrences?status=in_progress").json() == []
    assert client.get("/api/v1/occurrences?priority=urgent").status_code == 422


def test_sql_like_title_is_saved_as_data(client, clean_database):
    title = "'); DROP TABLE occurrences; --"
    response = client.post("/api/v1/occurrences", json={**PAYLOAD, "title": title})
    assert response.status_code == 201
    assert response.json()["title"] == title
    engine = create_engine(clean_database)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Occurrence)) == 1
    engine.dispose()
