"""Use English names for built-in preset tests

Revision ID: 20260521_000015
Revises: 20260521_000014
Create Date: 2026-05-21 00:00:15
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text


revision = "20260521_000015"
down_revision = "20260521_000014"
branch_labels = None
depends_on = None


RENAMES = {
    "python /opt/blocktest-presets/run_preset.py node_health": "Live: Hardhat node health",
    "python /opt/blocktest-presets/run_preset.py balance_check": "Live: Hardhat account balance",
    "python /opt/blocktest-presets/run_preset.py eth_transfer": "Live: Hardhat ETH transfer",
    "python /opt/blocktest-presets/run_preset.py deploy_counter": "Live: Counter contract compile and deploy",
}


def upgrade() -> None:
    connection = op.get_bind()
    for command, name in RENAMES.items():
        connection.execute(
            text("UPDATE tests SET name = :name WHERE command = :command"),
            {"name": name, "command": command},
        )


def downgrade() -> None:
    pass
