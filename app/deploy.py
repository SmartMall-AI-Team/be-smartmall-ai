"""Migrate and optionally seed the demo before accepting HTTP traffic."""

import os

import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import ROOT, Settings
from app.database.session import create_database_engine
from app.seed import seed

MIGRATION_LOCK = 723649201


def prepare_database(settings: Settings) -> None:
    engine = create_database_engine(settings.database_url)
    try:
        # Session-level lock serializes startup migrations/seed across overlapping deploys.
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as lock:
            lock.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK})
            try:
                config = Config(str(ROOT / "alembic.ini"))
                config.attributes["database_url"] = settings.database_url
                command.upgrade(config, "head")
                if settings.demo_seed:
                    with Session(engine) as session:
                        seed(session)
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK})
    finally:
        engine.dispose()


def main() -> None:
    settings = Settings()
    prepare_database(settings)
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
