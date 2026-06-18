"""Add GitHub dApp test source fields

Revision ID: 20260516_000010
Revises: 20260514_000009
Create Date: 2026-05-16 00:00:10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260516_000010"
down_revision = "20260514_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tests", sa.Column("repository_url", sa.String(length=1000), nullable=True))
    op.add_column("tests", sa.Column("repository_branch", sa.String(length=255), nullable=True))
    op.add_column("tests", sa.Column("repository_subdir", sa.String(length=500), nullable=True))
    op.add_column("tests", sa.Column("setup_command", sa.Text(), nullable=True))
    op.add_column("tests", sa.Column("rpc_url", sa.String(length=1000), nullable=True))
    op.add_column("tests", sa.Column("chain_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("tests", "chain_id")
    op.drop_column("tests", "rpc_url")
    op.drop_column("tests", "setup_command")
    op.drop_column("tests", "repository_subdir")
    op.drop_column("tests", "repository_branch")
    op.drop_column("tests", "repository_url")
