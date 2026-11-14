import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import ROOT, Settings
from app.main import create_app


class DatabaseURL(str):
    def __repr__(self) -> str:
        return "'<isolated PostgreSQL database>'"


def migration_config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture(scope="session")
def database_url():
    """Migrate a disposable database; never truncate the configured source database."""
    load_dotenv(ROOT / ".env", override=False)
    source = os.getenv("TEST_DATABASE_URL")
    if not source:
        pytest.fail("Defina TEST_DATABASE_URL em .env ou no ambiente para executar a integração.")
    source_url = make_url(source).set(drivername="postgresql+psycopg")
    name = "smartmall_test_" + uuid4().hex
    admin = create_engine(
        source_url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5}
    )
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    isolated = DatabaseURL(source_url.set(database=name).render_as_string(hide_password=False))
    try:
        command.upgrade(migration_config(isolated), "head")
        yield isolated
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def clean_database(database_url):
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE occurrences, equipment, users CASCADE"))
    engine.dispose()
    return database_url


@pytest.fixture
def client(clean_database):
    app = create_app(
        Settings(
            _env_file=None, database_url=clean_database, openai_api_key=None, ai_simulation=False
        )
    )
    with TestClient(app) as client:
        yield client
