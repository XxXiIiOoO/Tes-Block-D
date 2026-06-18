import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import LocalEmailModel
from app.schemas.user import UserRead


class RegisterRequest(LocalEmailModel):
    email: str
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Пароль должен содержать хотя бы одну букву")
        if not re.search(r"[0-9]", value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        clean = value.strip()
        if not re.match(r"^[a-zA-Z0-9_\-]+$", clean):
            raise ValueError("Имя пользователя может содержать только буквы, цифры, _ и -")
        return clean


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class VerifyTwoFactorRequest(LocalEmailModel):
    email: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=24, max_length=256)


class ResendVerificationRequest(LocalEmailModel):
    email: str


class ForgotPasswordRequest(LocalEmailModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=24, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Пароль должен содержать хотя бы одну букву")
        if not re.search(r"[0-9]", value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return value


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class TwoFactorChallengeResponse(BaseModel):
    two_factor_required: Literal[True] = True
    message: str
    email: str


class RegisterResponse(BaseModel):
    message: str
    verification_required: bool = True
    verification_token: str | None = None
    user: UserRead


class GenericMessageResponse(BaseModel):
    message: str
