from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LocalEmailModel


class UserRead(LocalEmailModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    is_admin: bool
    role: str
    email_verified: bool
    full_name: str | None
    position: str | None
    avatar_url: str | None
    bio: str | None
    created_at: datetime


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    position: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=2000)
