from alembic import context

from app.core.config import get_settings
from app.database.base import Base
from app.database.models import Equipment, Occurrence  # noqa: F401
from app.database.session import create_database_engine

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    # Tests can supply an isolated database through the Alembic Config object.
    return config.attributes.get("database_url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_database_engine(database_url())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
