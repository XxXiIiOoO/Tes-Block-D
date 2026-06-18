"""Add project secrets

Revision ID: 20260517_000012
Revises: 20260517_000011
Create Date: 2026-05-17 00:00:12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260517_000012"
down_revision = "20260517_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_secrets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "name", name="uq_project_secrets_project_id_name"),
    )
    op.create_index(op.f("ix_project_secrets_id"), "project_secrets", ["id"], unique=False)
    op.create_index(op.f("ix_project_secrets_project_id"), "project_secrets", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_secrets_name"), "project_secrets", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_secrets_name"), table_name="project_secrets")
    op.drop_index(op.f("ix_project_secrets_project_id"), table_name="project_secrets")
    op.drop_index(op.f("ix_project_secrets_id"), table_name="project_secrets")
    op.drop_table("project_secrets")
