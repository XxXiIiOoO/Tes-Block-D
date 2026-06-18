"""Add GitHub source fields to projects

Revision ID: 20260521_000014
Revises: 20260518_000013
Create Date: 2026-05-21 00:00:14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_000014"
down_revision = "20260518_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("repository_url", sa.String(length=1000), nullable=True))
    op.add_column("projects", sa.Column("repository_branch", sa.String(length=255), nullable=True))
    op.add_column("projects", sa.Column("repository_subdir", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "repository_subdir")
    op.drop_column("projects", "repository_branch")
    op.drop_column("projects", "repository_url")
