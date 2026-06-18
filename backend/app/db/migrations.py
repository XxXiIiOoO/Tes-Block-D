from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.db.base import Base


MANAGED_TABLES = {
    "users",
    "projects",
    "project_members",
    "project_secrets",
    "tests",
    "runs",
    "run_logs",
    "test_chat_messages",
    "audit_events",
    "refresh_tokens",
}


#Tut ya vynes get_alembic_config, chtoby ne razduvat ostalnoy kod.
def get_alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


#Eto otdelnyy shag bootstrap_legacy_schema, chtoby ne kopipastit odno i to zhe.
def bootstrap_legacy_schema(engine: Engine) -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("ALTER TYPE run_status ADD VALUE IF NOT EXISTS 'cancelled'"))
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'worker'
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS email_verification_token_hash VARCHAR(128)
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS email_verification_expires_at TIMESTAMP WITH TIME ZONE
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE users
                SET role = CASE WHEN is_admin THEN 'admin' ELSE 'worker' END
                WHERE role IS NULL OR role = ''
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS full_name VARCHAR(120)
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS position VARCHAR(120)
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS bio TEXT
                """
            )
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS script TEXT")
        )
        connection.execute(
            text("ALTER TABLE tests ALTER COLUMN command DROP NOT NULL")
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS baseline_run_id INTEGER")
        )
        connection.execute(
            text(
                """
                ALTER TABLE tests
                ADD COLUMN IF NOT EXISTS gate_enabled BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS gate_max_duration_seconds DOUBLE PRECISION")
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS gate_max_error_logs INTEGER")
        )
        connection.execute(
            text(
                """
                ALTER TABLE tests
                ADD COLUMN IF NOT EXISTS schedule_enabled BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS schedule_interval_minutes INTEGER")
        )
        connection.execute(
            text(
                """
                ALTER TABLE tests
                ADD COLUMN IF NOT EXISTS schedule_next_run_at TIMESTAMP WITH TIME ZONE
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE tests
                ADD COLUMN IF NOT EXISTS webhook_enabled BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS webhook_token_hash VARCHAR(128)")
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS repository_url VARCHAR(1000)")
        )
        connection.execute(
            text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS repository_url VARCHAR(1000)")
        )
        connection.execute(
            text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS repository_branch VARCHAR(255)")
        )
        connection.execute(
            text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS repository_subdir VARCHAR(500)")
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS repository_branch VARCHAR(255)")
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS repository_subdir VARCHAR(500)")
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS setup_command TEXT")
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS rpc_url VARCHAR(1000)")
        )
        connection.execute(
            text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS chain_id INTEGER")
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token_hash VARCHAR(128)")
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS password_reset_expires_at TIMESTAMP WITH TIME ZONE
                """
            )
        )
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_code_hash VARCHAR(128)")
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS two_factor_expires_at TIMESTAMP WITH TIME ZONE
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITH TIME ZONE
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS project_secrets (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    encrypted_value TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    CONSTRAINT uq_project_secrets_project_id_name UNIQUE (project_id, name)
                )
                """
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_project_secrets_id ON project_secrets (id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_project_secrets_project_id ON project_secrets (project_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_project_secrets_name ON project_secrets (name)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS project_members (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    CONSTRAINT uq_project_members_project_user UNIQUE (project_id, user_id)
                )
                """
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_project_members_id ON project_members (id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_project_members_project_id ON project_members (project_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_project_members_user_id ON project_members (user_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_project_members_role ON project_members (role)")
        )


#Funkciya run_migrations zakryvaet konkretnuyu zadachu v etom meste.
def run_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    config = get_alembic_config()

    if "alembic_version" not in existing_tables and existing_tables & MANAGED_TABLES:
        # Existing databases created before Alembic are normalized to the current
        # ORM schema and then stamped so future revisions can be applied cleanly.
        bootstrap_legacy_schema(engine)
        command.stamp(config, "head")
        return

    command.upgrade(config, "head")
