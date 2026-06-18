from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import settings
from app.services.github_sources import GitHubSourceError, parse_github_repository_url


class TestBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    scenario: str = Field(min_length=3, max_length=4000)
    docker_image: str = Field(default=settings.default_docker_image, min_length=3)
    command: str | None = Field(default=None, max_length=4000)
    script: str | None = Field(default=None, max_length=20000)
    repository_url: str | None = Field(default=None, max_length=1000)
    repository_branch: str | None = Field(default=None, max_length=255)
    repository_subdir: str | None = Field(default=None, max_length=500)
    setup_command: str | None = Field(default=None, max_length=4000)
    rpc_url: str | None = Field(default=None, max_length=1000)
    chain_id: int | None = Field(default=None, ge=1)

    @field_validator("docker_image")
    @classmethod
    def validate_docker_image(cls, value: str) -> str:
        image = value.strip()
        if not settings.is_docker_image_allowed(image):
            raise ValueError("Docker image is not allowed")
        return image

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

    @field_validator("rpc_url")
    @classmethod
    def validate_rpc_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        rpc_url = value.strip()
        if not rpc_url:
            return None
        if not rpc_url.startswith(("http://", "https://", "ws://", "wss://")):
            raise ValueError("RPC URL must start with http://, https://, ws://, or wss://")
        return rpc_url


class TestCreate(TestBase):
    #Funkciya require_command_or_script zakryvaet konkretnuyu zadachu v etom meste.
    @model_validator(mode="after")
    def require_command_or_script(self) -> "TestCreate":
        if self.repository_url and not self.command:
            raise ValueError("GitHub dApp tests must provide a test command")
        if self.repository_url and self.script:
            raise ValueError("GitHub dApp tests cannot use inline Python scripts")
        if not self.command and not self.script:
            raise ValueError("Either command or script must be provided")
        return self


class TestUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    scenario: str | None = Field(default=None, min_length=3, max_length=4000)
    docker_image: str | None = Field(default=None, min_length=3)
    command: str | None = Field(default=None, max_length=4000)
    script: str | None = Field(default=None, max_length=20000)
    repository_url: str | None = Field(default=None, max_length=1000)
    repository_branch: str | None = Field(default=None, max_length=255)
    repository_subdir: str | None = Field(default=None, max_length=500)
    setup_command: str | None = Field(default=None, max_length=4000)
    rpc_url: str | None = Field(default=None, max_length=1000)
    chain_id: int | None = Field(default=None, ge=1)

    @field_validator("docker_image")
    @classmethod
    def validate_docker_image(cls, value: str | None) -> str | None:
        if value is None:
            return None
        image = value.strip()
        if not settings.is_docker_image_allowed(image):
            raise ValueError("Docker image is not allowed")
        return image

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

    @field_validator("rpc_url")
    @classmethod
    def validate_rpc_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        rpc_url = value.strip()
        if not rpc_url:
            return None
        if not rpc_url.startswith(("http://", "https://", "ws://", "wss://")):
            raise ValueError("RPC URL must start with http://, https://, ws://, or wss://")
        return rpc_url


class TestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    description: str | None
    scenario: str
    docker_image: str
    command: str | None
    script: str | None
    repository_url: str | None
    repository_branch: str | None
    repository_subdir: str | None
    setup_command: str | None
    rpc_url: str | None
    chain_id: int | None
    created_at: datetime
    updated_at: datetime


class TestChatMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class TestChatMessageRead(BaseModel):
    id: int
    test_id: int
    user_id: int
    username: str
    role: str
    message: str
    created_at: datetime
