from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import Occurrence
from app.deploy import prepare_database
from app.main import create_app

TOKEN = "test-only-access-code-with-more-than-32-characters"


def test_demo_configuration_fails_closed():
    for options in [
        {"app_env": "demo"},
        {"app_env": "demo", "demo_access_token": TOKEN},
        {"app_env": "production"},
        {"demo_access_token": "weak"},
        {"demo_access_token": " " * 40},
        {"demo_seed": True},
    ]:
        with pytest.raises(ValidationError) as error:
            Settings(_env_file=None, **options)
        assert TOKEN not in str(error.value)


def test_public_demo_serves_persisted_data_without_access_code(clean_database):
    settings = Settings(
        _env_file=None,
        app_env="demo",
        ai_simulation=True,
        demo_seed=True,
        demo_access_token="",
        database_url=clean_database,
    )
    prepare_database(settings)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/access").json() == {"access_required": False}
        listed = client.get("/api/v1/occurrences")
        assert listed.status_code == 200
        assert listed.headers["cache-control"] == "no-store"
        occurrence = listed.json()[0]
        analysis = client.post(f"/api/v1/occurrences/{occurrence['id']}/analyze")
        assert analysis.status_code == 200
        assert analysis.json()["is_simulation"] is True


@pytest.mark.parametrize(
    "path", ["/api/v1/access", "/api/v1/occurrences", "/docs", "/openapi.json"]
)
def test_unauthenticated_requests_do_not_reach_the_database(path):
    app = create_app(
        Settings(_env_file=None, app_env="demo", ai_simulation=True, demo_access_token=TOKEN)
    )
    with TestClient(app) as client:
        for authorization in [None, "Bearer wrong", f"Basic {TOKEN}"]:
            headers = {"Authorization": authorization} if authorization else {}
            response = client.get(path, headers=headers)
            assert response.status_code == 401
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["www-authenticate"] == "Bearer"
            assert TOKEN not in response.text
        assert client.get("/health").status_code == 200
        assert client.get(
            "/api/v1/access", headers={"Authorization": f"Bearer {TOKEN}"}
        ).json() == {"access_required": True}


def test_cors_preflight_and_unauthorized_response_support_access_header():
    app = create_app(
        Settings(_env_file=None, app_env="demo", ai_simulation=True, demo_access_token=TOKEN)
    )
    with TestClient(app) as client:
        origin = {"Origin": "http://localhost:5173"}
        preflight = client.options(
            "/api/v1/occurrences",
            headers={
                **origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert preflight.status_code == 200
        denied = client.get("/api/v1/occurrences", headers=origin)
        assert denied.status_code == 401
        assert denied.headers["access-control-allow-origin"] == origin["Origin"]


def test_demo_bootstrap_is_idempotent_and_serves_protected_persisted_data(clean_database):
    settings = Settings(
        _env_file=None,
        app_env="demo",
        ai_simulation=True,
        demo_seed=True,
        demo_access_token=TOKEN,
        database_url=clean_database,
    )
    prepare_database(settings)
    prepare_database(settings)
    engine = create_engine(clean_database)
    try:
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(Occurrence)) == 1
    finally:
        engine.dispose()
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/ready").status_code == 200
        assert client.get("/api/v1/occurrences").status_code == 401
        client.headers["Authorization"] = f"Bearer {TOKEN}"
        listed = client.get("/api/v1/occurrences")
        assert listed.status_code == 200
        assert listed.headers["cache-control"] == "no-store"
        occurrence = listed.json()[0]
        analysis = client.post(f"/api/v1/occurrences/{occurrence['id']}/analyze")
        assert analysis.status_code == 200
        assert analysis.json()["is_simulation"] is True


def test_database_public_role_cannot_read_or_insert_even_with_table_grants(clean_database):
    engine = create_engine(clean_database)
    try:
        with engine.connect() as connection:
            is_admin = connection.scalar(
                text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
            )
            connection.rollback()
            if not is_admin:
                pytest.skip("A verificação de papel público exige superuser no banco de testes.")
            transaction = connection.begin()
            try:
                role = "smartmall_probe_" + uuid4().hex
                connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
                connection.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
                connection.execute(text(f'GRANT SELECT, INSERT ON users TO "{role}"'))
                connection.execute(
                    text(
                        "INSERT INTO users (id, name, role, is_active) "
                        "VALUES (gen_random_uuid(), 'Fictício protegido', 'technician', true)"
                    )
                )
                assert connection.scalar(text("SELECT count(*) FROM users")) == 1
                connection.execute(text(f'SET LOCAL ROLE "{role}"'))
                assert connection.scalar(text("SELECT count(*) FROM users")) == 0
                with pytest.raises(DBAPIError):
                    connection.execute(
                        text(
                            "INSERT INTO users (id, name, role, is_active) "
                            "VALUES (gen_random_uuid(), 'Inserção bloqueada', 'technician', true)"
                        )
                    )
            finally:
                # Role creation, grants and probe data are all rolled back together.
                transaction.rollback()
    finally:
        engine.dispose()
