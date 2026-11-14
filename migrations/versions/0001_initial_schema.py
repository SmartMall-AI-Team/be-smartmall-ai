"""Create occurrences and the equipment reference table.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("type", sa.String(120), nullable=False),
        sa.Column("location", sa.String(240), nullable=False),
        sa.Column(
            "operational_status",
            sa.Enum(
                "operational",
                "maintenance",
                "out_of_service",
                name="equipment_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="operational",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_equipment"),
    )
    op.create_table(
        "occurrences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(240), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "hvac",
                "electrical",
                "plumbing",
                "cleaning",
                "other",
                name="category",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("equipment_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "in_progress",
                "resolved",
                name="occurrence_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="open",
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "untriaged",
                "low",
                "medium",
                "high",
                "critical",
                name="priority",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="untriaged",
            nullable=False,
        ),
        sa.Column("ai_analysis", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], name="fk_occurrences_equipment_id_equipment"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_occurrences"),
    )
    op.create_index("ix_occurrences_status", "occurrences", ["status"])
    op.create_index("ix_occurrences_priority", "occurrences", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_occurrences_priority", table_name="occurrences")
    op.drop_index("ix_occurrences_status", table_name="occurrences")
    op.drop_table("occurrences")
    op.drop_table("equipment")
