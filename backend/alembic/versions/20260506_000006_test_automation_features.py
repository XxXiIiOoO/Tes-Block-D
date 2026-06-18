"""Add test automation and quality gate fields

Revision ID: 20260506_000006
Revises: 20260506_000005
Create Date: 2026-05-06 00:00:06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260506_000006"
down_revision = "20260506_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tests",
        sa.Column("baseline_run_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tests",
        sa.Column(
            "gate_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "tests",
        sa.Column("gate_max_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "tests",
        sa.Column("gate_max_error_logs", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tests",
        sa.Column(
            "schedule_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "tests",
        sa.Column("schedule_interval_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tests",
        sa.Column("schedule_next_run_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tests",
        sa.Column(
            "webhook_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "tests",
        sa.Column("webhook_token_hash", sa.String(length=128), nullable=True),
    )

    op.create_foreign_key(
        "fk_tests_baseline_run_id_runs",
        "tests",
        "runs",
        ["baseline_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_tests_baseline_run_id"), "tests", ["baseline_run_id"], unique=False)

    op.alter_column("tests", "gate_enabled", server_default=None)
    op.alter_column("tests", "schedule_enabled", server_default=None)
    op.alter_column("tests", "webhook_enabled", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_tests_baseline_run_id"), table_name="tests")
    op.drop_constraint("fk_tests_baseline_run_id_runs", "tests", type_="foreignkey")

    op.drop_column("tests", "webhook_token_hash")
    op.drop_column("tests", "webhook_enabled")
    op.drop_column("tests", "schedule_next_run_at")
    op.drop_column("tests", "schedule_interval_minutes")
    op.drop_column("tests", "schedule_enabled")
    op.drop_column("tests", "gate_max_error_logs")
    op.drop_column("tests", "gate_max_duration_seconds")
    op.drop_column("tests", "gate_enabled")
    op.drop_column("tests", "baseline_run_id")
