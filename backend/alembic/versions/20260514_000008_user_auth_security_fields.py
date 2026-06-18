"""Add user auth security fields

Revision ID: 20260514_000008
Revises: 20260514_000007
Create Date: 2026-05-14 00:00:08
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260514_000008"
down_revision = "20260514_000007"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("users", "password_reset_token_hash"):
        op.add_column(
            "users",
            sa.Column("password_reset_token_hash", sa.String(length=128), nullable=True),
        )

    if not _has_column("users", "password_reset_expires_at"):
        op.add_column(
            "users",
            sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_column("users", "failed_login_attempts"):
        op.add_column(
            "users",
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    if not _has_column("users", "locked_until"):
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if _has_column("users", "locked_until"):
        op.drop_column("users", "locked_until")
    if _has_column("users", "failed_login_attempts"):
        op.drop_column("users", "failed_login_attempts")
    if _has_column("users", "password_reset_expires_at"):
        op.drop_column("users", "password_reset_expires_at")
    if _has_column("users", "password_reset_token_hash"):
        op.drop_column("users", "password_reset_token_hash")
