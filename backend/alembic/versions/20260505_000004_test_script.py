"""Add script column and make command nullable

Revision ID: 20260505_000004
Revises: 20260505_000003
Create Date: 2026-05-05 00:00:04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260505_000004"
down_revision = "20260505_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tests", sa.Column("script", sa.Text(), nullable=True))
    op.alter_column("tests", "command", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.alter_column("tests", "command", existing_type=sa.Text(), nullable=False)
    op.drop_column("tests", "script")
