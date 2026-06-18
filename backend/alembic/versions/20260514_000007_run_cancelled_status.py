"""Add cancelled run status

Revision ID: 20260514_000007
Revises: 20260506_000006
Create Date: 2026-05-14 00:00:07
"""
from __future__ import annotations

from alembic import op


revision = "20260514_000007"
down_revision = "20260506_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE run_status ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the
    # type and rewriting dependent columns, so downgrade is intentionally empty.
    pass
