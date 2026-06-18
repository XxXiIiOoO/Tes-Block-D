"""Add user profile fields and test chat

Revision ID: 20260505_000003
Revises: 20260505_000002
Create Date: 2026-05-05 00:00:03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260505_000003"
down_revision = "20260505_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("position", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))

    op.create_table(
        "test_chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_test_chat_messages_id"), "test_chat_messages", ["id"], unique=False)
    op.create_index(op.f("ix_test_chat_messages_test_id"), "test_chat_messages", ["test_id"], unique=False)
    op.create_index(op.f("ix_test_chat_messages_user_id"), "test_chat_messages", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_test_chat_messages_user_id"), table_name="test_chat_messages")
    op.drop_index(op.f("ix_test_chat_messages_test_id"), table_name="test_chat_messages")
    op.drop_index(op.f("ix_test_chat_messages_id"), table_name="test_chat_messages")
    op.drop_table("test_chat_messages")

    op.drop_column("users", "bio")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "position")
    op.drop_column("users", "full_name")
