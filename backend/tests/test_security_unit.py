import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

from app.core.security import (
    get_password_hash,
    verify_password,
    hash_token,
    encrypt_secret_value,
    decrypt_secret_value,
    create_access_token,
    create_refresh_token,
    decode_token,
    token_expiration
)

def test_password_hashing():
    """Test that passwords are hashed correctly and can be verified."""
    password = "supersecretpassword123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_token_hashing():
    """Test that generic tokens (like refresh tokens) are hashed securely."""
    token = "some-random-token-string"
    hashed = hash_token(token)
    assert hashed != token
    assert hash_token(token) == hashed  # Deterministic

def test_secret_encryption_decryption():
    """Test symmetric encryption and decryption for project secrets."""
    secret_value = "my_api_key_12345_!@#$"
    encrypted = encrypt_secret_value(secret_value)
    assert encrypted != secret_value
    
    decrypted = decrypt_secret_value(encrypted)
    assert decrypted == secret_value

def test_secret_decryption_invalid_payload():
    """Test that invalid encrypted payloads raise a ValueError."""
    with pytest.raises(ValueError, match="Invalid secret payload"):
        decrypt_secret_value("invalid_base64_string")
        
    with pytest.raises(ValueError, match="Invalid secret payload"):
        decrypt_secret_value("short_string")

def test_access_token_creation_and_decoding():
    """Test JWT access token creation and decoding."""
    subject = "user123"
    token = create_access_token(subject)
    
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == subject
    assert payload["type"] == "access"

def test_refresh_token_creation_and_decoding():
    """Test JWT refresh token creation and decoding."""
    subject = "user123"
    token = create_refresh_token(subject)
    
    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == subject
    assert payload["type"] == "refresh"

def test_decode_token_wrong_type():
    """Test that providing the wrong expected token type raises 401."""
    token = create_access_token("user123")
    with pytest.raises(HTTPException) as exc_info:
        # Expecting refresh, but provided access token
        decode_token(token, expected_type="refresh")
    assert exc_info.value.status_code == 401
    assert "Не удалось проверить учетные данные" in exc_info.value.detail

def test_token_expiration_parsing():
    """Test the token expiration parsing function from numeric timestamps."""
    now = datetime.now(timezone.utc)
    payload = {"exp": now.timestamp()}
    exp_time = token_expiration(payload)
    
    # Allow precision difference of max 1 second
    assert abs((exp_time - now).total_seconds()) < 1.0
