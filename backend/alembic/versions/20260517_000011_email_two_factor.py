"""Add email two-factor login fields

Revision ID: 20260517_000011
Revises: 20260516_000010
Create Date: 2026-05-17 00:00:11
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260517_000011"
down_revision = "20260516_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("two_factor_code_hash", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("two_factor_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "two_factor_expires_at")
    op.drop_column("users", "two_factor_code_hash")
