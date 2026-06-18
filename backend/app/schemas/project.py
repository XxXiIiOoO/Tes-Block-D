from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.github_sources import GitHubSourceError, parse_github_repository_url


class ProjectBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    repository_url: str | None = Field(default=None, max_length=1000)
    repository_branch: str | None = Field(default=None, max_length=255)
    repository_subdir: str | None = Field(default=None, max_length=500)

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        repository_url = value.strip()
        if not repository_url:
            return None
        try:
            parse_github_repository_url(repository_url)
        except GitHubSourceError as exc:
            raise ValueError(str(exc)) from exc
        return repository_url


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    repository_url: str | None = Field(default=None, max_length=1000)
    repository_branch: str | None = Field(default=None, max_length=255)
    repository_subdir: str | None = Field(default=None, max_length=500)

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        repository_url = value.strip()
        if not repository_url:
            return None
        try:
            parse_github_repository_url(repository_url)
        except GitHubSourceError as exc:
            raise ValueError(str(exc)) from exc
        return repository_url


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    owner_username: str | None = None
    access_role: Literal["admin", "owner", "developer", "viewer"] | None = None
    repository_url: str | None = None
    repository_branch: str | None = None
    repository_subdir: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectMemberCreate(BaseModel):
    user_id: int
    role: Literal["developer", "viewer"]


class ProjectMemberUpdate(BaseModel):
    role: Literal["developer", "viewer"]


class ProjectMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    username: str
    email: str
    full_name: str | None = None
    role: Literal["developer", "viewer"]
    created_at: datetime
    updated_at: datetime
