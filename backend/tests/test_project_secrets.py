from __future__ import annotations

from sqlalchemy import select

from app.core.security import decrypt_secret_value
from app.models.project_secret import ProjectSecret
from tests.helpers import register_and_verify_user


def test_project_secret_crud_stores_encrypted_value(client, session_factory):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="secrets-owner@example.com",
        username="secrets_owner",
        password="StrongPass123!",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}

    project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Secrets Project", "description": "stores env secrets"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    create_response = client.post(
        f"/projects/{project_id}/secrets",
        headers=headers,
        json={"name": "rpc_token", "value": "super-secret-token"},
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["name"] == "RPC_TOKEN"
    assert payload["value_mask"] == "****"
    assert "super-secret-token" not in str(payload)

    db = session_factory()
    try:
        secret = db.scalar(select(ProjectSecret).where(ProjectSecret.id == payload["id"]))
        assert secret is not None
        assert secret.encrypted_value != "super-secret-token"
        assert decrypt_secret_value(secret.encrypted_value) == "super-secret-token"
    finally:
        db.close()

    update_response = client.put(
        f"/projects/{project_id}/secrets/{payload['id']}",
        headers=headers,
        json={"value": "rotated-secret"},
    )
    assert update_response.status_code == 200

    list_response = client.get(f"/projects/{project_id}/secrets", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "RPC_TOKEN"

    delete_response = client.delete(
        f"/projects/{project_id}/secrets/{payload['id']}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    list_after_delete = client.get(f"/projects/{project_id}/secrets", headers=headers)
    assert list_after_delete.status_code == 200
    assert list_after_delete.json() == []


def test_project_secret_rejects_reserved_names(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="reserved-secret@example.com",
        username="reserved_secret",
        password="StrongPass123!",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Reserved Secret Project", "description": None},
    )
    project_id = project_response.json()["id"]

    response = client.post(
        f"/projects/{project_id}/secrets",
        headers=headers,
        json={"name": "BLOCKTEST_RPC_URL", "value": "unsafe"},
    )
    assert response.status_code == 422
