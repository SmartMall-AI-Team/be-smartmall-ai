from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.models import User
from tests.test_occurrences import PAYLOAD

BASE = "/api/v1"


def setup_work(client):
    occurrence = client.post(BASE + "/occurrences", json=PAYLOAD).json()
    user = client.post(BASE + "/users", json={"name": "Técnico fictício"}).json()
    task_data = {
        "occurrence_id": occurrence["id"],
        "title": "Inspecionar equipamento",
        "assigned_to": user["id"],
        "due_at": "2026-12-01T12:00:00-03:00",
    }
    return occurrence, user, task_data


def test_task_workflow_history_and_dashboard(client):
    occurrence, user, data = setup_work(client)
    path = BASE + "/occurrences/" + occurrence["id"]
    response = client.post(BASE + "/tasks", json=data)
    assert response.status_code == 201
    task = response.json()
    task_path = BASE + "/tasks/" + task["id"]
    assert task["due_at"] == "2026-12-01T15:00:00Z"
    assert task["completed_at"] is None
    assert client.get(task_path).json() == task
    assert client.get(path).json()["tasks"] == [task]
    assert client.patch(path, json={"status": "resolved"}).status_code == 409
    assert client.patch(task_path, json={"status": "completed"}).status_code == 409
    assert client.patch(task_path, json={"status": "in_progress"}).status_code == 200
    assert client.get(path).json()["status"] == "in_progress"
    summary = client.get(BASE + "/dashboard/summary").json()
    assert summary["occurrences_total"] == 1
    assert summary["occurrences_by_status"] == {"open": 0, "in_progress": 1, "resolved": 0}
    assert summary["tasks_pending"] == 1
    completed = client.patch(task_path, json={"status": "completed"}).json()
    assert completed["completed_at"] is not None
    assert client.get(path).json()["status"] == "in_progress"
    assert client.patch(path, json={"status": "resolved"}).status_code == 200
    assert client.post(BASE + "/tasks", json=data).status_code == 409
    assert client.patch(task_path, json={"status": "in_progress"}).status_code == 409
    assert client.patch(path, json={"status": "open"}).status_code == 200
    reopened = client.patch(task_path, json={"status": "in_progress"}).json()
    assert reopened["completed_at"] is None
    events = client.get(path + "/history").json()
    assert events[0]["event_type"] == "occurrence_created"
    changes = [e for e in events if e["event_type"] == "task_status_changed"]
    assert [e["new_status"] for e in changes] == ["in_progress", "completed", "in_progress"]
    assert all(e["created_at"].endswith("Z") for e in events)
    assert client.get(BASE + f"/tasks?status=in_progress&assigned_to={user['id']}").json() == [
        reopened
    ]
    assert client.get(BASE + "/tasks?status=completed").json() == []


def test_equipment_filters_and_manual_classification(client):
    response = client.post(
        BASE + "/equipment", json={"name": "AC fictício", "type": "HVAC", "location": "Praça 10%"}
    )
    assert response.status_code == 201
    equipment = response.json()
    ep = BASE + "/equipment/" + equipment["id"]
    assert client.get(ep).json() == equipment
    assert client.patch(ep, json={"operational_status": "maintenance"}).status_code == 200
    assert (
        len(client.get(BASE + "/equipment?operational_status=maintenance&location=10%25").json())
        == 1
    )
    assert client.get(BASE + "/equipment?location=10_").json() == []
    occurrence = client.post(
        BASE + "/occurrences", json={**PAYLOAD, "equipment_id": equipment["id"]}
    ).json()
    path = BASE + "/occurrences/" + occurrence["id"]
    updated = client.patch(
        path,
        json={"category": "hvac", "priority": "high", "assigned_team": "Climatização"},
    ).json()
    assert updated["priority"] == "high"
    assert updated["ai_reviewed_at"] is None
    assert client.get(ep + "/occurrences").json()[0]["id"] == occurrence["id"]
    assert len(client.get(BASE + "/occurrences?category=hvac&location=ALIMENTA").json()) == 1
    assert client.get(BASE + f"/occurrences?equipment_id={uuid4()}").json() == []
    assert client.patch(path, json={"equipment_id": None}).json()["equipment_id"] is None
    summary = client.get(BASE + "/dashboard/summary").json()
    assert summary["equipment_by_status"]["maintenance"] == 1
    assert summary["occurrences_by_priority"]["high"] == 1
    assert client.patch(path, json={"confirm_ai_review": True}).status_code == 409


@pytest.mark.parametrize("payload", [{}, {"status": None}, {"title": " "}, {"id": "x"}])
def test_patch_rejects_invalid_fields(client, payload):
    occurrence, _, data = setup_work(client)
    task = client.post(BASE + "/tasks", json=data).json()
    assert client.patch(BASE + "/tasks/" + task["id"], json=payload).status_code == 422
    assert client.patch(BASE + "/occurrences/" + occurrence["id"], json=payload).status_code == 422


def test_task_references_inactive_user_and_timezone(client, clean_database):
    occurrence, user, data = setup_work(client)
    assert (
        client.post(BASE + "/tasks", json={**data, "assigned_to": str(uuid4())}).status_code == 404
    )
    assert (
        client.post(BASE + "/tasks", json={**data, "occurrence_id": str(uuid4())}).status_code
        == 404
    )
    assert (
        client.post(BASE + "/tasks", json={**data, "due_at": "2026-12-01T12:00:00"}).status_code
        == 422
    )
    engine = create_engine(clean_database)
    with Session(engine) as session:
        person = session.get(User, user["id"])
        person.is_active = False
        session.commit()
    engine.dispose()
    assert client.post(BASE + "/tasks", json=data).status_code == 409
    assert client.get(BASE + "/users").json() == []
    assert client.get(BASE + "/tasks").json() == []
    assert len(client.get(BASE + "/occurrences/" + occurrence["id"] + "/history").json()) == 1


@pytest.mark.parametrize("resource", ["tasks", "equipment", "occurrences"])
def test_missing_resources(client, resource):
    assert client.get(BASE + f"/{resource}/{uuid4()}").status_code == 404


def test_empty_dashboard_has_all_enum_keys(client):
    data = client.get(BASE + "/dashboard/summary").json()
    assert data["occurrences_total"] == 0
    assert data["tasks_pending"] == 0
    assert set(data["occurrences_by_priority"]) == {
        "untriaged",
        "low",
        "medium",
        "high",
        "critical",
    }
    assert all(value == 0 for value in data["equipment_by_status"].values())
