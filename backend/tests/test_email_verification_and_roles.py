from __future__ import annotations

import re

from tests.helpers import approve_registered_user_in_test_app, create_user


#Tut ya vynes test_login_requires_email_verification, chtoby ne razduvat ostalnoy kod.
def test_login_requires_email_verification(client):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "new-user@example.com",
            "username": "new-user",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["verification_required"] is True
    assert register_payload["verification_token"] is None

    login_before_verification = client.post(
        "/auth/login",
        json={"email": "new-user@example.com", "password": "secret123"},
    )
    assert login_before_verification.status_code == 403

    approve_registered_user_in_test_app(register_payload["user"]["id"])

    login_after_verification = client.post(
        "/auth/login",
        json={"email": "new-user@example.com", "password": "secret123"},
    )
    assert login_after_verification.status_code == 200


def test_register_notifies_admins_for_approval(client, session_factory, monkeypatch):
    import app.api.routes.auth as auth_module

    sent_messages: list[dict[str, str]] = []

    def fake_send_email(*, to_email: str, subject: str, body: str) -> None:
        sent_messages.append({"to_email": to_email, "subject": subject, "body": body})

    create_user(
        session_factory,
        email="admin-approver@example.com",
        username="admin-approver",
        password="admin-secret",
        is_admin=True,
        role="admin",
        email_verified=True,
    )
    monkeypatch.setattr(auth_module.settings, "frontend_base_url", "http://45.90.34.89")
    monkeypatch.setattr(auth_module, "send_email", fake_send_email)

    register_response = client.post(
        "/auth/register",
        json={
            "email": "pending-user@example.com",
            "username": "pending-user",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["verification_token"] is None
    assert sent_messages
    assert sent_messages[0]["to_email"] == "admin-approver@example.com"
    assert "http://45.90.34.89/admin" in sent_messages[0]["body"]


#Zdes sobrana logika test_viewer_role_has_read_only_access, tak ee proshche podderzhivat.
def test_viewer_role_has_read_only_access(client, session_factory):
    create_user(
        session_factory,
        email="viewer@example.com",
        username="viewer",
        password="viewer-secret",
        role="viewer",
        email_verified=True,
    )

    login_response = client.post(
        "/auth/login",
        json={"email": "viewer@example.com", "password": "viewer-secret"},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    create_project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Should fail", "description": "viewer cannot create"},
    )
    assert create_project_response.status_code == 403

    run_test_response = client.post("/tests/1/run", headers=headers)
    assert run_test_response.status_code == 403


def test_email_two_factor_login_requires_code(client, monkeypatch):
    import app.api.routes.auth as auth_module

    sent_messages: list[dict[str, str]] = []

    def fake_send_email(*, to_email: str, subject: str, body: str) -> None:
        sent_messages.append({"to_email": to_email, "subject": subject, "body": body})

    monkeypatch.setattr(auth_module.settings, "email_2fa_enabled", True)
    monkeypatch.setattr(auth_module, "send_email", fake_send_email)

    register_response = client.post(
        "/auth/register",
        json={
            "email": "two-factor@example.com",
            "username": "two-factor",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201

    approve_registered_user_in_test_app(register_response.json()["user"]["id"])

    login_response = client.post(
        "/auth/login",
        json={"email": "two-factor@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["two_factor_required"] is True
    assert "access_token" not in login_payload

    code_match = re.search(r"\b\d{6}\b", sent_messages[-1]["body"])
    assert code_match is not None

    two_factor_response = client.post(
        "/auth/verify-2fa",
        json={
            "email": "two-factor@example.com",
            "code": code_match.group(0),
        },
    )
    assert two_factor_response.status_code == 200
    assert two_factor_response.json()["access_token"]
