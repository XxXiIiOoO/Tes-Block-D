import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


RESERVED_SECRET_NAMES = {
    "HOME",
    "PATH",
    "PWD",
    "PYTHONPATH",
    "PYTHONUNBUFFERED",
    "PYTHONDONTWRITEBYTECODE",
}


class ProjectSecretBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip().upper()
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", name):
            raise ValueError("Secret name must be a valid environment variable name")
        if name.startswith("BLOCKTEST_") or name in RESERVED_SECRET_NAMES:
            raise ValueError("Secret name is reserved")
        return name


class ProjectSecretCreate(ProjectSecretBase):
    value: str = Field(min_length=1, max_length=4000)


class ProjectSecretUpdate(BaseModel):
    value: str = Field(min_length=1, max_length=4000)


class ProjectSecretRead(ProjectSecretBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    value_mask: str = "****"
    created_at: datetime
    updated_at: datetime
