import hashlib
import hmac
import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


#Zdes sobrana logika get_password_hash, tak ee proshche podderzhivat.
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


#Eto otdelnyy shag verify_password, chtoby ne kopipastit odno i to zhe.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


#Zdes sobrana logika _create_token, tak ee proshche podderzhivat.
def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": secrets.token_urlsafe(32),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


#Eto otdelnyy shag create_access_token, chtoby ne kopipastit odno i to zhe.
def create_access_token(subject: str) -> str:
    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


#Eto otdelnyy shag create_refresh_token, chtoby ne kopipastit odno i to zhe.
def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _secret_encryption_key() -> bytes:
    return hashlib.sha256(settings.jwt_secret_key.encode("utf-8")).digest()


def _secret_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < length:
        block = hmac.new(
            key,
            nonce + counter.to_bytes(4, "big"),
            hashlib.sha256,
        ).digest()
        output.extend(block)
        counter += 1
    return bytes(output[:length])


def encrypt_secret_value(value: str) -> str:
    key = _secret_encryption_key()
    nonce = secrets.token_bytes(16)
    plaintext = value.encode("utf-8")
    stream = _secret_keystream(key, nonce, len(plaintext))
    ciphertext = bytes(left ^ right for left, right in zip(plaintext, stream))
    signature = hmac.new(key, b"project-secret" + nonce + ciphertext, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + signature + ciphertext).decode("ascii")


def decrypt_secret_value(payload: str) -> str:
    try:
        raw = base64.urlsafe_b64decode(payload.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Invalid secret payload") from exc

    if len(raw) < 48:
        raise ValueError("Invalid secret payload")

    nonce = raw[:16]
    signature = raw[16:48]
    ciphertext = raw[48:]
    key = _secret_encryption_key()
    expected_signature = hmac.new(
        key,
        b"project-secret" + nonce + ciphertext,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid secret signature")

    stream = _secret_keystream(key, nonce, len(ciphertext))
    plaintext = bytes(left ^ right for left, right in zip(ciphertext, stream))
    return plaintext.decode("utf-8")


def token_expiration(payload: dict[str, Any]) -> datetime:
    exp = payload.get("exp")
    if isinstance(exp, datetime):
        return exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Некорректные данные токена",
    )


#Tut ya vynes decode_token, chtoby ne razduvat ostalnoy kod.
def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия токена истёк",
        ) from exc
    except InvalidTokenError as exc:
        raise credentials_exception from exc

    if payload.get("type") != expected_type:
        raise credentials_exception

    return payload
