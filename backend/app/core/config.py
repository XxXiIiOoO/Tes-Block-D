from functools import lru_cache
from fnmatch import fnmatchcase
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="BlockTest API", alias="BLOCKTEST_APP_NAME")
    debug: bool = Field(default=False, alias="BLOCKTEST_DEBUG")
    environment: str = Field(default="development", alias="BLOCKTEST_ENV")

    database_url: str = Field(
        default="postgresql+psycopg://app:app@localhost:5432/blocktest",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    bootstrap_admin_email: str | None = Field(default=None, alias="BLOCKTEST_ADMIN_EMAIL")
    bootstrap_admin_username: str | None = Field(
        default=None,
        alias="BLOCKTEST_ADMIN_USERNAME",
    )
    bootstrap_admin_password: str | None = Field(
        default=None,
        alias="BLOCKTEST_ADMIN_PASSWORD",
    )
    bootstrap_worker_email: str | None = Field(default=None, alias="BLOCKTEST_WORKER_EMAIL")
    bootstrap_worker_username: str | None = Field(
        default=None,
        alias="BLOCKTEST_WORKER_USERNAME",
    )
    bootstrap_worker_password: str | None = Field(
        default=None,
        alias="BLOCKTEST_WORKER_PASSWORD",
    )
    bootstrap_viewer_email: str | None = Field(default=None, alias="BLOCKTEST_VIEWER_EMAIL")
    bootstrap_viewer_username: str | None = Field(
        default=None,
        alias="BLOCKTEST_VIEWER_USERNAME",
    )
    bootstrap_viewer_password: str | None = Field(
        default=None,
        alias="BLOCKTEST_VIEWER_PASSWORD",
    )

    password_reset_token_expire_minutes: int = Field(
        default=60,
        alias="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES",
    )

    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        alias="REFRESH_TOKEN_EXPIRE_DAYS",
    )

    backend_cors_origins_raw: str = Field(
        default="http://localhost:5173",
        alias="BACKEND_CORS_ORIGINS",
    )

    default_docker_image: str = Field(
        default="python:3.12-slim",
        alias="DEFAULT_DOCKER_IMAGE",
    )
    docker_run_timeout_seconds: int = Field(
        default=30,
        alias="DOCKER_RUN_TIMEOUT_SECONDS",
    )
    docker_memory_limit: str = Field(default="256m", alias="DOCKER_MEMORY_LIMIT")
    docker_pids_limit: int = Field(default=128, alias="DOCKER_PIDS_LIMIT")
    docker_nano_cpus: int = Field(default=1_000_000_000, alias="DOCKER_NANO_CPUS")
    docker_read_only_rootfs: bool = Field(default=False, alias="DOCKER_READ_ONLY_ROOTFS")
    docker_user: str = Field(default="1000:1000", alias="DOCKER_RUN_USER")
    docker_allowed_images_raw: str = Field(
        default="python:3.12-slim,node:20-bookworm-slim,blocktest-evm-presets:latest",
        alias="DOCKER_ALLOWED_IMAGES",
    )
    docker_network_disabled: bool = Field(
        default=True,
        alias="DOCKER_NETWORK_DISABLED",
    )
    docker_compose_network: str | None = Field(
        default=None,
        alias="DOCKER_COMPOSE_NETWORK",
    )

    taskiq_queue_name: str = Field(default="default", alias="TASKIQ_QUEUE_NAME")
    scheduler_enabled: bool = Field(default=True, alias="BLOCKTEST_SCHEDULER_ENABLED")
    scheduler_tick_seconds: int = Field(
        default=60,
        ge=5,
        alias="BLOCKTEST_SCHEDULER_TICK_SECONDS",
    )

    seed_presets: bool = Field(default=False, alias="BLOCKTEST_SEED_PRESETS")
    frontend_base_url: str = Field(default="http://localhost:5173", alias="FRONTEND_BASE_URL")
    email_verification_token_expire_minutes: int = Field(
        default=60 * 24,
        alias="EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES",
    )
    expose_verification_token_in_response: bool = Field(
        default=True,
        alias="EXPOSE_VERIFICATION_TOKEN_IN_RESPONSE",
    )
    email_delivery_mode: str = Field(default="demo", alias="EMAIL_DELIVERY_MODE")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="noreply@blocktest.local", alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    email_2fa_enabled: bool = Field(default=False, alias="EMAIL_2FA_ENABLED")
    email_2fa_code_expire_minutes: int = Field(default=10, alias="EMAIL_2FA_CODE_EXPIRE_MINUTES")

    #Funkciya backend_cors_origins zakryvaet konkretnuyu zadachu v etom meste.
    @property
    def backend_cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins_raw.split(",")
            if origin.strip()
        ]

    @property
    def docker_allowed_images(self) -> list[str]:
        return [
            image.strip()
            for image in self.docker_allowed_images_raw.split(",")
            if image.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}

    def is_docker_image_allowed(self, image: str) -> bool:
        allowed_images = self.docker_allowed_images
        if not allowed_images:
            return True
        return any(fnmatchcase(image, pattern) for pattern in allowed_images)

    def validate_security_settings(self) -> None:
        if not self.is_production:
            return

        errors: list[str] = []
        if self.jwt_secret_key in {"change-me", "change-this-to-a-long-random-secret"}:
            errors.append("JWT_SECRET_KEY must be changed in production")
        if len(self.jwt_secret_key) < 32:
            errors.append("JWT_SECRET_KEY must be at least 32 characters in production")
        if "*" in self.backend_cors_origins:
            errors.append("BACKEND_CORS_ORIGINS must not contain * in production")
        if self.expose_verification_token_in_response:
            errors.append("EXPOSE_VERIFICATION_TOKEN_IN_RESPONSE must be false in production")
        if self.email_delivery_mode == "demo":
            errors.append("EMAIL_DELIVERY_MODE must not be demo in production")
        if self.email_2fa_enabled and self.email_delivery_mode.lower() != "smtp":
            errors.append("EMAIL_DELIVERY_MODE must be smtp when EMAIL_2FA_ENABLED is true in production")
        if not self.docker_allowed_images:
            errors.append("DOCKER_ALLOWED_IMAGES must not be empty in production")
        if not self.docker_network_disabled and not self.docker_compose_network:
            errors.append("Docker network access must be disabled or pinned to a compose network in production")

        if errors:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))


#Zdes sobrana logika get_settings, tak ee proshche podderzhivat.
@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
