"""Initial schema

Revision ID: 20260425_000001
Revises:
Create Date: 2026-04-25 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260425_000001"
down_revision = None
branch_labels = None
depends_on = None


run_status_enum = postgresql.ENUM(
    "queued",
    "running",
    "finished",
    "failed",
    name="run_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    run_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    op.create_index(op.f("ix_projects_name"), "projects", ["name"], unique=False)
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)

    op.create_table(
        "tests",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column("docker_image", sa.String(length=255), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_tests_id"), "tests", ["id"], unique=False)
    op.create_index(op.f("ix_tests_name"), "tests", ["name"], unique=False)
    op.create_index(op.f("ix_tests_project_id"), "tests", ["project_id"], unique=False)

    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("status", run_status_enum, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_runs_id"), "runs", ["id"], unique=False)
    op.create_index(op.f("ix_runs_status"), "runs", ["status"], unique=False)
    op.create_index(op.f("ix_runs_test_id"), "runs", ["test_id"], unique=False)

    op.create_table(
        "run_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_run_logs_id"), "run_logs", ["id"], unique=False)
    op.create_index(op.f("ix_run_logs_run_id"), "run_logs", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_run_logs_run_id"), table_name="run_logs")
    op.drop_index(op.f("ix_run_logs_id"), table_name="run_logs")
    op.drop_table("run_logs")

    op.drop_index(op.f("ix_runs_test_id"), table_name="runs")
    op.drop_index(op.f("ix_runs_status"), table_name="runs")
    op.drop_index(op.f("ix_runs_id"), table_name="runs")
    op.drop_table("runs")

    op.drop_index(op.f("ix_tests_project_id"), table_name="tests")
    op.drop_index(op.f("ix_tests_name"), table_name="tests")
    op.drop_index(op.f("ix_tests_id"), table_name="tests")
    op.drop_table("tests")

    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_name"), table_name="projects")
    op.drop_index(op.f("ix_projects_id"), table_name="projects")
    op.drop_table("projects")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    run_status_enum.drop(bind, checkfirst=True)
