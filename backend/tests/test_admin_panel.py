from app.models.user import User
from tests.helpers import create_user


#Tut ya vynes test_admin_can_manage_users_and_read_audit, chtoby ne razduvat ostalnoy kod.
def test_admin_can_manage_users_and_read_audit(client, session_factory):
    admin_password = "StrongPass123!"
    worker_password = "WorkerPass123!"

    admin_user_id = create_user(
        session_factory,
        email="admin.panel@test.local",
        username="admin_panel",
        password=admin_password,
        is_admin=True,
        role="admin",
        email_verified=True,
    )
    worker_user_id = create_user(
        session_factory,
        email="worker.panel@test.local",
        username="worker_panel",
        password=worker_password,
        is_admin=False,
        role="worker",
        email_verified=True,
    )

    login_response = client.post(
        "/auth/login",
        json={"email": "admin.panel@test.local", "password": admin_password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    users_response = client.get("/admin/users", headers=headers)
    assert users_response.status_code == 200
    users_payload = users_response.json()
    managed_user = next((item for item in users_payload if item["id"] == worker_user_id), None)
    assert managed_user is not None
    assert managed_user["role"] == "worker"

    patch_response = client.patch(
        f"/admin/users/{worker_user_id}",
        headers=headers,
        json={"role": "viewer", "email_verified": False},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["role"] == "viewer"
    assert patch_response.json()["email_verified"] is False

    db = session_factory()
    try:
        worker = db.get(User, worker_user_id)
        assert worker is not None
        assert worker.role == "viewer"
        assert worker.is_admin is False
        assert worker.email_verified is False
        admin_user = db.get(User, admin_user_id)
        assert admin_user is not None
    finally:
        db.close()

    events_response = client.get("/admin/audit-events?limit=50", headers=headers)
    assert events_response.status_code == 200
    actions = [event["action"] for event in events_response.json()]
    assert "admin.user.updated" in actions


def test_admin_user_crud(client, session_factory):
    admin_password = "StrongPass123!"
    create_user(
        session_factory,
        email="crud.admin@test.local",
        username="crud_admin",
        password=admin_password,
        is_admin=True,
        role="admin",
        email_verified=True,
    )

    login_response = client.post(
        "/auth/login",
        json={"email": "crud.admin@test.local", "password": admin_password},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    create_response = client.post(
        "/admin/users",
        headers=headers,
        json={
            "email": "crud.worker@test.local",
            "username": "crud_worker",
            "password": "WorkerPass123!",
            "role": "worker",
            "email_verified": True,
            "full_name": "CRUD Worker",
            "position": "QA",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["email"] == "crud.worker@test.local"
    assert created["role"] == "worker"

    patch_response = client.patch(
        f"/admin/users/{created['id']}",
        headers=headers,
        json={
            "email": "crud.viewer@test.local",
            "username": "crud_viewer",
            "password": "ViewerPass123!",
            "role": "viewer",
            "email_verified": False,
            "full_name": "CRUD Viewer",
            "position": "Observer",
            "bio": "Read only user",
        },
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["email"] == "crud.viewer@test.local"
    assert updated["username"] == "crud_viewer"
    assert updated["role"] == "viewer"
    assert updated["email_verified"] is False

    old_login_response = client.post(
        "/auth/login",
        json={"email": "crud.viewer@test.local", "password": "WorkerPass123!"},
    )
    assert old_login_response.status_code == 401

    verify_response = client.patch(
        f"/admin/users/{created['id']}",
        headers=headers,
        json={"email_verified": True},
    )
    assert verify_response.status_code == 200
    new_login_response = client.post(
        "/auth/login",
        json={"email": "crud.viewer@test.local", "password": "ViewerPass123!"},
    )
    assert new_login_response.status_code == 200

    delete_response = client.delete(f"/admin/users/{created['id']}", headers=headers)
    assert delete_response.status_code == 204
    users_response = client.get("/admin/users", headers=headers)
    assert users_response.status_code == 200
    assert all(item["id"] != created["id"] for item in users_response.json())

    events_response = client.get("/admin/audit-events?limit=50", headers=headers)
    actions = [event["action"] for event in events_response.json()]
    assert "admin.user.created" in actions
    assert "admin.user.updated" in actions
    assert "admin.user.deleted" in actions
