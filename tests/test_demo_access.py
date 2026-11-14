import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import Occurrence
from app.deploy import prepare_database
from app.main import create_app

TOKEN = "test-only-access-code-with-more-than-32-characters"


def test_demo_configuration_fails_closed():
    for options in [
        {"app_env": "demo", "ai_simulation": True},
        {"app_env": "demo", "demo_access_token": TOKEN},
        {"app_env": "production"},
        {"demo_access_token": "weak"},
        {"demo_access_token": " " * 40},
        {"demo_seed": True},
    ]:
        with pytest.raises(ValidationError) as error:
            Settings(_env_file=None, **options)
        assert TOKEN not in str(error.value)


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
