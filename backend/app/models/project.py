from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, utcnow

if TYPE_CHECKING:
    from app.models.project_member import ProjectMember
    from app.models.project_secret import ProjectSecret
    from app.models.test import Test
    from app.models.user import User


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    repository_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repository_subdir: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="projects")
    tests: Mapped[list["Test"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    secrets: Mapped[list["ProjectSecret"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )

    #Eto otdelnyy shag owner_username, chtoby ne kopipastit odno i to zhe.
    @property
    def owner_username(self) -> str | None:
        return self.owner.username if self.owner else None
