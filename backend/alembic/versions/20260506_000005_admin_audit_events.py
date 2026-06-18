"""Add admin audit events table

Revision ID: 20260506_000005
Revises: 20260505_000004
Create Date: 2026-05-06 00:00:05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260506_000005"
down_revision = "20260505_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False)
    op.create_index(op.f("ix_audit_events_entity_id"), "audit_events", ["entity_id"], unique=False)
    op.create_index(
        op.f("ix_audit_events_entity_type"),
        "audit_events",
        ["entity_type"],
        unique=False,
    )
    op.create_index(op.f("ix_audit_events_id"), "audit_events", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_events_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_entity_type"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_entity_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_action"), table_name="audit_events")
    op.drop_table("audit_events")
