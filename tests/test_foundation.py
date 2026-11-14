from unittest.mock import patch

import pytest
from alembic import command
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.main import create_app
from tests.conftest import migration_config


def test_health_and_database_readiness(client):
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_database_failure_is_controlled_without_exposing_connection():
    settings = Settings(_env_file=None, database_url="postgresql://user:private@localhost/test")
    app = create_app(settings)
    with TestClient(app) as client:
        with patch.object(
            app.state.engine,
            "connect",
            side_effect=OperationalError("SELECT 1", {}, Exception("private connection detail")),
        ):
            assert client.get("/health").status_code == 200
            response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Banco de dados indisponível."}
    assert "private" not in response.text


def test_cors_allows_configured_frontend_and_rejects_other_origins(client):
    headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"}
    allowed = client.options("/health", headers=headers)
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    headers["Origin"] = "https://unconfigured.example"
    denied = client.options("/health", headers=headers)
    assert "access-control-allow-origin" not in denied.headers


def test_environment_parses_multiple_origins_and_psycopg_url():
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:password@localhost/test",
        cors_origins="http://localhost:5173/, http://127.0.0.1:5173",
    )
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="sqlite:///test.db")


def test_migration_can_rollback_reapply_and_matches_models(database_url):
    config = migration_config(database_url)
    command.downgrade(config, "base")
    engine = create_engine(database_url)
    try:
        assert inspect(engine).get_table_names() == ["alembic_version"]
    finally:
        engine.dispose()
    command.upgrade(config, "head")
    command.check(config)
