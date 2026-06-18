from app.models.project_member import ProjectMember
from tests.helpers import create_project_with_test, create_user


def add_project_member(session_factory, *, project_id: int, user_id: int, role: str) -> None:
    db = session_factory()
    try:
        db.add(ProjectMember(project_id=project_id, user_id=user_id, role=role))
        db.commit()
    finally:
        db.close()


def login(client, *, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_project_developer_can_manage_only_assigned_project(client, session_factory):
    owner_id = create_user(
        session_factory,
        email="owner.member@test.local",
        username="owner_member",
        password="OwnerPass123!",
        email_verified=True,
    )
    developer_id = create_user(
        session_factory,
        email="developer.member@test.local",
        username="developer_member",
        password="DeveloperPass123!",
        email_verified=True,
    )
    project_id, test_id = create_project_with_test(
        session_factory,
        owner_id=owner_id,
        project_name="Assigned project",
        test_name="Assigned smoke",
    )
    other_project_id, other_test_id = create_project_with_test(
        session_factory,
        owner_id=owner_id,
        project_name="Private project",
        test_name="Private smoke",
    )
    add_project_member(session_factory, project_id=project_id, user_id=developer_id, role="developer")
    headers = login(client, email="developer.member@test.local", password="DeveloperPass123!")

    projects_response = client.get("/projects", headers=headers)
    assert projects_response.status_code == 200
    project_ids = {item["id"] for item in projects_response.json()}
    assert project_id in project_ids
    assert other_project_id not in project_ids

    create_test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Developer test",
            "scenario": "Developer can create tests only here",
            "docker_image": "python:3.12-slim",
            "command": "python -c \"print('developer')\"",
        },
    )
    assert create_test_response.status_code == 201

    update_project_response = client.put(
        f"/projects/{project_id}",
        headers=headers,
        json={"description": "Updated by developer"},
    )
    assert update_project_response.status_code == 200

    assigned_test_response = client.get(f"/tests/{test_id}", headers=headers)
    assert assigned_test_response.status_code == 200
    assert assigned_test_response.json()["command"] is not None

    other_test_response = client.get(f"/tests/{other_test_id}", headers=headers)
    assert other_test_response.status_code == 404


def test_project_viewer_has_read_only_sanitized_access(client, session_factory):
    owner_id = create_user(
        session_factory,
        email="viewer-owner@test.local",
        username="viewer_owner",
        password="OwnerPass123!",
        email_verified=True,
    )
    viewer_id = create_user(
        session_factory,
        email="project.viewer@test.local",
        username="project_viewer",
        password="ViewerPass123!",
        email_verified=True,
    )
    project_id, test_id = create_project_with_test(
        session_factory,
        owner_id=owner_id,
        project_name="Observed project",
        test_name="Observed smoke",
    )
    add_project_member(session_factory, project_id=project_id, user_id=viewer_id, role="viewer")
    headers = login(client, email="project.viewer@test.local", password="ViewerPass123!")

    project_response = client.get(f"/projects/{project_id}", headers=headers)
    assert project_response.status_code == 200
    assert project_response.json()["access_role"] == "viewer"

    tests_response = client.get(f"/projects/{project_id}/tests", headers=headers)
    assert tests_response.status_code == 200
    assert tests_response.json()[0]["command"] is None
    assert tests_response.json()[0]["script"] is None
    assert tests_response.json()[0]["setup_command"] is None
    assert tests_response.json()[0]["rpc_url"] is None

    create_test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Forbidden test",
            "scenario": "Viewer cannot create",
            "docker_image": "python:3.12-slim",
            "command": "python -c \"print('no')\"",
        },
    )
    assert create_test_response.status_code == 403

    update_test_response = client.put(
        f"/tests/{test_id}",
        headers=headers,
        json={"name": "Viewer edit"},
    )
    assert update_test_response.status_code == 403

    secrets_response = client.get(f"/projects/{project_id}/secrets", headers=headers)
    assert secrets_response.status_code == 403
