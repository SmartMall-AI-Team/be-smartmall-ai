"""Block non-owner database access until explicit policies are designed.

Revision ID: 3c4e52d8a901
Revises: 144cf912a4c9
"""

from alembic import op

revision = "3c4e52d8a901"
down_revision = "144cf912a4c9"
branch_labels = None
depends_on = None

TABLES = ("equipment", "occurrences", "users", "tasks", "occurrence_history")


def upgrade() -> None:
    # No public policies: anon/authenticated roles must not bypass the FastAPI access gate.
    # The backend's private table-owner connection keeps the existing application behavior.
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
