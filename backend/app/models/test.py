from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base
from app.models.mixins import TimestampMixin, utcnow

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.run import Run
    from app.models.test_chat_message import TestChatMessage


class Test(TimestampMixin, Base):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenario: Mapped[str] = mapped_column(Text, nullable=False)
    docker_image: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=settings.default_docker_image,
    )
    command: Mapped[str | None] = mapped_column(Text, nullable=True)
    script: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    repository_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repository_subdir: Mapped[str | None] = mapped_column(String(500), nullable=True)
    setup_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    rpc_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    chain_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baseline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_tests_baseline_run_id_runs",
        ),
        nullable=True,
        index=True,
    )
    gate_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gate_max_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    gate_max_error_logs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    schedule_interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    project: Mapped["Project"] = relationship(back_populates="tests")
    runs: Mapped[list["Run"]] = relationship(
        back_populates="test",
        foreign_keys="Run.test_id",
        cascade="all, delete-orphan",
    )
    chat_messages: Mapped[list["TestChatMessage"]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="TestChatMessage.created_at",
    )
