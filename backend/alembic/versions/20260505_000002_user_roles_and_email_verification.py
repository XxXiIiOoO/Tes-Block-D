"""Add user roles and email verification fields

Revision ID: 20260505_000002
Revises: 20260425_000001
Create Date: 2026-05-05 00:00:02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260505_000002"
down_revision = "20260425_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="worker"),
    )
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("email_verification_token_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("email_verification_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE users
        SET role = CASE WHEN is_admin THEN 'admin' ELSE 'worker' END
        """
    )
    op.execute(
        """
        UPDATE users
        SET email_verified = TRUE
        """
    )
    op.alter_column("users", "role", server_default=None)
    op.alter_column("users", "email_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "role")
