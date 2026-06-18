from __future__ import annotations

import logging
import re
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_token,
    token_expiration,
    verify_password,
)
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    GenericMessageResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TwoFactorChallengeResponse,
    VerifyEmailRequest,
    VerifyTwoFactorRequest,
)
from app.schemas.user import UserProfileUpdate, UserRead
from app.services.audit import record_audit_event
from app.services.email_verification import (
    generate_verification_token,
    hash_verification_token,
)
from app.services.email import EmailDeliveryError, send_email
from app.services.rate_limit import (
    RateLimitExceeded,
    check_rate_limit,
    fallback_rate_limit_store,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Simple in-memory rate limiter for auth endpoints
# ---------------------------------------------------------------------------
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 10  # per window per IP
TWO_FACTOR_CODE_DIGITS = 6

_rate_limit_store = fallback_rate_limit_store


def _check_rate_limit(request: Request, action: str = "auth") -> None:
    """Raise 429 if too many requests from same IP."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"{action}:{client_ip}"
    try:
        check_rate_limit(
            key,
            max_requests=RATE_LIMIT_MAX_REQUESTS,
            window_seconds=RATE_LIMIT_WINDOW,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов. Попробуйте позже.",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_auth_response(db: Session, user: User) -> AuthResponse:
    subject = str(user.id)
    refresh_token = create_refresh_token(subject)
    refresh_payload = decode_token(refresh_token, expected_type="refresh")
    jti = refresh_payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Некорректные данные refresh-токена",
        )

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            jti=jti,
            expires_at=token_expiration(refresh_payload),
        )
    )
    db.commit()

    return AuthResponse(
        access_token=create_access_token(subject),
        refresh_token=refresh_token,
        user=UserRead.model_validate(user),
    )


def revoke_refresh_token(db: Session, token: str) -> RefreshToken | None:
    token_hash = hash_token(token)
    refresh_token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if refresh_token is None:
        return None
    if refresh_token.revoked_at is None:
        refresh_token.revoked_at = datetime.now(timezone.utc)
        db.add(refresh_token)
    return refresh_token


def revoke_user_refresh_tokens(db: Session, user_id: int) -> None:
    active_tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    ).all()
    now = datetime.now(timezone.utc)
    for refresh_token in active_tokens:
        refresh_token.revoked_at = now
        db.add(refresh_token)


def get_active_refresh_token(db: Session, token: str) -> RefreshToken:
    token_hash = hash_token(token)
    refresh_token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    now = datetime.now(timezone.utc)
    if refresh_token is None or refresh_token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные",
        )

    expires_at = refresh_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        refresh_token.revoked_at = now
        db.add(refresh_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия токена истёк",
        )

    return refresh_token


def _hash_two_factor_code(email: str, code: str) -> str:
    normalized_email = email.strip().lower()
    payload = f"{settings.jwt_secret_key}:{normalized_email}:{code}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _generate_two_factor_code() -> str:
    return f"{secrets.randbelow(10**TWO_FACTOR_CODE_DIGITS):0{TWO_FACTOR_CODE_DIGITS}d}"


def set_two_factor_code(user: User) -> str:
    code = _generate_two_factor_code()
    user.two_factor_code_hash = _hash_two_factor_code(user.email, code)
    user.two_factor_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.email_2fa_code_expire_minutes
    )
    return code


def clear_two_factor_code(user: User) -> None:
    user.two_factor_code_hash = None
    user.two_factor_expires_at = None


def send_two_factor_email(email: str, code: str) -> None:
    try:
        send_email(
            to_email=email,
            subject="BlockTest: код входа",
            body=(
                "Ваш одноразовый код входа в BlockTest:\n\n"
                f"{code}\n\n"
                f"Код действует {settings.email_2fa_code_expire_minutes} минут. "
                "Если вы не выполняли вход, проигнорируйте это уведомление."
            ),
        )
    except EmailDeliveryError as exc:
        logger.exception("Не удалось отправить 2FA-код для %s", email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось отправить код подтверждения входа",
        ) from exc


def _build_password_reset_link(token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={token}"


def _build_admin_users_link() -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/admin"


def notify_admins_about_registration_request(db: Session, user: User) -> None:
    admins = db.scalars(
        select(User).where(
            User.is_admin.is_(True),
            User.email_verified.is_(True),
        )
    ).all()
    if not admins:
        logger.warning("No verified admins found for registration request %s", user.email)
        return

    admin_link = _build_admin_users_link()
    body = (
        "Новая заявка на создание аккаунта BlockTest.\n\n"
        f"Email: {user.email}\n"
        f"Логин: {user.username}\n"
        f"ID: {user.id}\n\n"
        "Откройте админ-раздел, чтобы подтвердить пользователя и назначить доступ к проекту:\n"
        f"{admin_link}"
    )
    for admin in admins:
        try:
            send_email(
                to_email=admin.email,
                subject="BlockTest: новая заявка на аккаунт",
                body=body,
            )
        except EmailDeliveryError:
            logger.exception(
                "Failed to notify admin %s about registration request %s",
                admin.email,
                user.email,
            )


def _sanitize_text(value: str, max_length: int = 500) -> str:
    """Strip dangerous HTML/script content and enforce length."""
    clean = value.strip()[:max_length]
    # Remove any HTML tags
    clean = re.sub(r"<[^>]*>", "", clean)
    return clean


def _validate_url(value: str | None) -> str | None:
    """Only allow http/https URLs for avatar."""
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if not trimmed.startswith(("http://", "https://")):
        return None
    if len(trimmed) > 500:
        return None
    return trimmed


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    _check_rate_limit(request, "register")

    existing = db.scalar(
        select(User).where(or_(User.email == payload.email, User.username == payload.username))
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email или логином уже существует",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        role=UserRole.worker.value,
        is_admin=False,
        email_verified=False,
        email_verification_token_hash=None,
        email_verification_expires_at=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    notify_admins_about_registration_request(db, user)
    record_audit_event(
        db,
        action="auth.registration_requested",
        user=user,
        entity_type="user",
        entity_id=user.id,
        details=f"email={user.email}; status=pending_admin_approval",
        commit=True,
    )

    return RegisterResponse(
        message="Заявка на создание аккаунта отправлена. Попросите администратора предоставить доступ к проекту.",
        verification_token=None,
        user=UserRead.model_validate(user),
    )

@router.post("/verify-email", response_model=AuthResponse)
def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse:
    _check_rate_limit(request, "verify-email")

    token_hash = hash_verification_token(payload.token)
    user = db.scalar(
        select(User).where(User.email_verification_token_hash == token_hash)
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification token was not found",
        )

    expires_at = user.email_verification_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at < datetime.now(timezone.utc):
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None
        db.add(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired",
        )

    user.email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.add(user)
    db.commit()

    record_audit_event(
        db,
        action="auth.email_verified",
        user=user,
        entity_type="user",
        entity_id=user.id,
        details="email verified",
        commit=True,
    )
    return build_auth_response(db, user)


@router.post("/login", response_model=AuthResponse | TwoFactorChallengeResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse | TwoFactorChallengeResponse:
    _check_rate_limit(request, "login")

    login_identifier = payload.email.strip()
    normalized_identifier = login_identifier.lower()
    user = db.scalar(
        select(User).where(
            or_(
                User.email == normalized_identifier,
                User.username == login_identifier,
                User.username == normalized_identifier,
            )
        )
    )

    # Account lockout check
    if user is not None and user.locked_until is not None:
        locked = user.locked_until
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        if locked > datetime.now(timezone.utc):
            remaining = int((locked - datetime.now(timezone.utc)).total_seconds() // 60) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Аккаунт заблокирован. Попробуйте через {remaining} мин.",
            )
        else:
            # Lockout expired, reset
            user.locked_until = None
            user.failed_login_attempts = 0

    if user is None or not verify_password(payload.password, user.password_hash):
        # Increment failed attempts
        if user is not None:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_login_attempts = 0
                db.add(user)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Слишком много неудачных попыток. Аккаунт заблокирован на {LOCKOUT_MINUTES} мин.",
                )
            db.add(user)
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт ожидает подтверждения администратора",
        )

    # Reset failed attempts on successful login
    if user.failed_login_attempts and user.failed_login_attempts > 0:
        user.failed_login_attempts = 0
        user.locked_until = None

    if settings.email_2fa_enabled:
        code = set_two_factor_code(user)
        db.add(user)
        send_two_factor_email(user.email, code)
        db.commit()
        record_audit_event(
            db,
            action="auth.login_2fa.sent",
            user=user,
            entity_type="user",
            entity_id=user.id,
            details="email code sent",
            commit=True,
        )
        return TwoFactorChallengeResponse(
            message="Введите код подтверждения.",
            email=user.email,
        )

    record_audit_event(
        db,
        action="auth.login",
        user=user,
        entity_type="user",
        entity_id=user.id,
        details="login success",
        commit=True,
    )

    return build_auth_response(db, user)


@router.post("/verify-2fa", response_model=AuthResponse)
def verify_two_factor(
    payload: VerifyTwoFactorRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse:
    _check_rate_limit(request, "2fa")

    user = db.scalar(select(User).where(User.email == payload.email))
    expected_hash = _hash_two_factor_code(payload.email, payload.code)
    if user is None or user.two_factor_code_hash != expected_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный код подтверждения входа",
        )

    expires_at = user.two_factor_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at < datetime.now(timezone.utc):
        clear_two_factor_code(user)
        db.add(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Срок действия кода подтверждения входа истёк",
        )

    clear_two_factor_code(user)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    db.commit()
    db.refresh(user)

    record_audit_event(
        db,
        action="auth.login_2fa.verified",
        user=user,
        entity_type="user",
        entity_id=user.id,
        details="email code verified",
        commit=True,
    )

    return build_auth_response(db, user)


@router.post("/refresh", response_model=AuthResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> AuthResponse:
    token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    user_id = token_payload.get("sub")
    jti = token_payload.get("jti")
    if user_id is None or not isinstance(jti, str) or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректные данные токена",
        )

    stored_refresh_token = get_active_refresh_token(db, payload.refresh_token)
    try:
        subject_user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректные данные токена",
        ) from exc

    if stored_refresh_token.jti != jti or stored_refresh_token.user_id != subject_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные",
        )

    user = db.scalar(select(User).where(User.id == subject_user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    stored_refresh_token.revoked_at = datetime.now(timezone.utc)
    db.add(stored_refresh_token)
    return build_auth_response(db, user)


@router.post("/logout", response_model=GenericMessageResponse)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> GenericMessageResponse:
    revoke_refresh_token(db, payload.refresh_token)
    db.commit()
    return GenericMessageResponse(message="Сессия завершена.")


# ---------------------------------------------------------------------------
# Password recovery
# ---------------------------------------------------------------------------

@router.post("/forgot-password", response_model=GenericMessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GenericMessageResponse:
    _check_rate_limit(request, "forgot")

    user = db.scalar(select(User).where(User.email == payload.email))

    # Always return same message to not reveal user existence
    response_message = "Если аккаунт с таким email существует, запрос на сброс пароля обработан."

    if user is None or not user.email_verified:
        return GenericMessageResponse(message=response_message)

    token = generate_verification_token()
    user.password_reset_token_hash = hash_verification_token(token)
    user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.password_reset_token_expire_minutes
    )
    db.add(user)
    db.commit()

    reset_link = _build_password_reset_link(token)
    if (
        settings.email_delivery_mode.lower() != "smtp"
        and settings.expose_verification_token_in_response
    ):
        response_message = f"{response_message}\n\nDemo reset link: {reset_link}"

    try:
        send_email(
            to_email=user.email,
            subject="BlockTest: сброс пароля",
            body=(
                "Для сброса пароля BlockTest откройте ссылку:\n"
                f"{reset_link}\n\n"
                "Если вы не запрашивали сброс пароля, проигнорируйте это уведомление."
            ),
        )
    except EmailDeliveryError as exc:
        logger.exception("Не удалось обработать уведомление сброса пароля для %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось обработать запрос сброса пароля",
        ) from exc

    record_audit_event(
        db,
        action="auth.forgot_password",
        user=user,
        entity_type="user",
        entity_id=user.id,
        details="reset token generated",
        commit=True,
    )

    return GenericMessageResponse(message=response_message)


@router.post("/reset-password", response_model=GenericMessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GenericMessageResponse:
    _check_rate_limit(request, "reset")

    token_hash = hash_verification_token(payload.token)
    user = db.scalar(select(User).where(User.password_reset_token_hash == token_hash))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или просроченный токен сброса пароля",
        )

    expires_at = user.password_reset_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at < datetime.now(timezone.utc):
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None
        db.add(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Срок действия токена сброса истёк. Запросите новую ссылку.",
        )

    user.password_hash = get_password_hash(payload.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.failed_login_attempts = 0
    user.locked_until = None
    revoke_user_refresh_tokens(db, user.id)
    db.add(user)
    db.commit()

    record_audit_event(
        db,
        action="auth.password_reset",
        user=user,
        entity_type="user",
        entity_id=user.id,
        details="password changed via reset token",
        commit=True,
    )

    return GenericMessageResponse(message="Пароль успешно изменён. Теперь вы можете войти с новым паролем.")


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        if isinstance(value, str):
            if field == "avatar_url":
                value = _validate_url(value)
            elif field == "bio":
                value = _sanitize_text(value, max_length=2000) or None
            else:
                value = _sanitize_text(value, max_length=120) or None
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    changed_fields = ", ".join(sorted(updates.keys())) if updates else "no fields"
    record_audit_event(
        db,
        action="auth.profile.updated",
        user=current_user,
        entity_type="user",
        entity_id=current_user.id,
        details=changed_fields,
        commit=True,
    )
    return UserRead.model_validate(current_user)
