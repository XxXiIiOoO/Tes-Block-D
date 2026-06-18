from __future__ import annotations

from tests.helpers import approve_registered_user_in_test_app, create_project_with_test, promote_user_to_admin


#Tut obrabatyvayu test_admin_can_manage_other_users_tests, vse po delu i bez lishnego.
def test_admin_can_manage_other_users_tests(client, session_factory):
    owner_response = client.post(
        "/auth/register",
        json={"email": "owner@example.com", "username": "owner", "password": "OwnerSecret123!"},
    )
    owner_id = owner_response.json()["user"]["id"]
    approve_registered_user_in_test_app(owner_id)

    admin_response = client.post(
        "/auth/register",
        json={"email": "admin@example.com", "username": "admin", "password": "AdminSecret123!"},
    )
    admin_id = admin_response.json()["user"]["id"]
    approve_registered_user_in_test_app(admin_id)
    promote_user_to_admin(session_factory, user_id=admin_id)

    project_id, test_id = create_project_with_test(
        session_factory,
        owner_id=owner_id,
        project_name="Exchange backend",
        test_name="Liquidity smoke",
    )

    login_response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminSecret123!"},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    projects_response = client.get("/projects", headers=headers)
    assert projects_response.status_code == 200
    assert projects_response.json()[0]["owner_username"] == "owner"

    get_test_response = client.get(f"/tests/{test_id}", headers=headers)
    assert get_test_response.status_code == 200
    assert get_test_response.json()["name"] == "Liquidity smoke"

    update_test_response = client.put(
        f"/tests/{test_id}",
        headers=headers,
        json={"name": "Liquidity smoke admin edit"},
    )
    assert update_test_response.status_code == 200
    assert update_test_response.json()["name"] == "Liquidity smoke admin edit"

    create_test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Admin created test",
            "description": "Created by admin",
            "scenario": "Admin creates tests on any project",
            "docker_image": "python:3.12-slim",
            "command": "python -c \"print('admin')\"",
        },
    )
    assert create_test_response.status_code == 201

    delete_test_response = client.delete(f"/tests/{test_id}", headers=headers)
    assert delete_test_response.status_code == 204
