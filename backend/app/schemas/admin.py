from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LocalEmailModel


class AdminUserCreate(LocalEmailModel):
    email: str
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "worker", "viewer"] = "worker"
    email_verified: bool = True
    full_name: str | None = Field(default=None, max_length=120)
    position: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=2000)


class AdminUserUpdate(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, min_length=3, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: Literal["admin", "worker", "viewer"] | None = None
    email_verified: bool | None = None
    full_name: str | None = Field(default=None, max_length=120)
    position: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=2000)


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    username: str | None
    action: str
    entity_type: str | None
    entity_id: int | None
    details: str | None
    created_at: datetime
