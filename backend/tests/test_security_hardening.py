from __future__ import annotations

import pytest

from app.core.config import Settings
from tests.helpers import create_user, register_and_verify_user


def test_refresh_token_rotates_and_old_token_is_rejected(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="rotate@example.com",
        username="rotate",
        password="secret123",
    )
    old_refresh_token = verify_response.json()["refresh_token"]

    first_refresh = client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert first_refresh.status_code == 200
    new_refresh_token = first_refresh.json()["refresh_token"]
    assert new_refresh_token != old_refresh_token

    replay_response = client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert replay_response.status_code == 401

    second_refresh = client.post("/auth/refresh", json={"refresh_token": new_refresh_token})
    assert second_refresh.status_code == 200


def test_logout_revokes_refresh_token(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="logout@example.com",
        username="logout",
        password="secret123",
    )
    refresh_token = verify_response.json()["refresh_token"]

    logout_response = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 200

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401


def test_bruteforce_lockout_after_repeated_failures(client, session_factory):
    create_user(
        session_factory,
        email="locked@example.com",
        username="locked",
        password="secret123",
    )

    for _ in range(4):
        response = client.post(
            "/auth/login",
            json={"email": "locked@example.com", "password": "wrong123"},
        )
        assert response.status_code == 401

    lock_response = client.post(
        "/auth/login",
        json={"email": "locked@example.com", "password": "wrong123"},
    )
    assert lock_response.status_code == 429

    correct_password_response = client.post(
        "/auth/login",
        json={"email": "locked@example.com", "password": "secret123"},
    )
    assert correct_password_response.status_code == 429


def test_project_search_does_not_expand_with_sql_injection_payload(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="search@example.com",
        username="search",
        password="secret123",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}

    create_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Wallet App", "description": "Wallet regression suite"},
    )
    assert create_response.status_code == 201

    search_response = client.get(
        "/projects",
        headers=headers,
        params={"search": "' OR 1=1 --"},
    )
    assert search_response.status_code == 200
    assert search_response.json() == []


def test_disallowed_docker_image_is_rejected(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="image@example.com",
        username="image",
        password="secret123",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Image policy", "description": "checks image allowlist"},
    )
    assert project_response.status_code == 201

    test_response = client.post(
        f"/projects/{project_response.json()['id']}/tests",
        headers=headers,
        json={
            "name": "Disallowed image",
            "scenario": "Try to use an image outside the allowlist",
            "docker_image": "alpine:latest",
            "command": "echo unsafe",
        },
    )
    assert test_response.status_code == 422


def test_production_config_rejects_unsafe_defaults():
    config = Settings(
        BLOCKTEST_ENV="production",
        JWT_SECRET_KEY="change-me",
        BACKEND_CORS_ORIGINS="*",
        EMAIL_DELIVERY_MODE="demo",
        EXPOSE_VERIFICATION_TOKEN_IN_RESPONSE=True,
        DOCKER_ALLOWED_IMAGES="",
    )

    with pytest.raises(RuntimeError):
        config.validate_security_settings()
