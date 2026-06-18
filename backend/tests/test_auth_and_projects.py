from __future__ import annotations

from tests.helpers import register_and_verify_user


#Tut ya vynes test_register_login_refresh_and_me, chtoby ne razduvat ostalnoy kod.
def test_register_login_refresh_and_me(client):
    register_response, verify_response = register_and_verify_user(
        client,
        email="student@example.com",
        username="student",
        password="secret123",
    )
    register_data = register_response.json()
    verify_data = verify_response.json()
    assert register_data["user"]["email"] == "student@example.com"
    assert register_data["user"]["is_admin"] is False

    access_token = verify_data["access_token"]
    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "student"

    login_response = client.post(
        "/auth/login",
        json={"email": "student@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": login_response.json()["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["user"]["email"] == "student@example.com"


#Zdes sobrana logika test_user_can_create_project_and_test, tak ee proshche podderzhivat.
def test_user_can_create_project_and_test(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="owner@example.com",
        username="owner",
        password="secret123",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}

    project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Wallet App", "description": "Wallet regression suite"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Transfer smoke",
            "description": "Checks transfer command",
            "scenario": "Run a smoke transfer check in an isolated container",
            "docker_image": "python:3.12-slim",
            "command": "python -c \"print('Blockchain test passed')\"",
        },
    )
    assert test_response.status_code == 201
    test_id = test_response.json()["id"]

    get_test_response = client.get(f"/tests/{test_id}", headers=headers)
    assert get_test_response.status_code == 200
    assert get_test_response.json()["name"] == "Transfer smoke"


def test_user_can_create_github_project(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="github-project-owner@example.com",
        username="github-project-owner",
        password="secret123",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}

    project_response = client.post(
        "/projects",
        headers=headers,
        json={
            "name": "Wallet dApp",
            "description": "Project imported from GitHub",
            "repository_url": "https://github.com/example/wallet-dapp",
            "repository_branch": "develop",
            "repository_subdir": "packages/contracts",
        },
    )

    assert project_response.status_code == 201
    payload = project_response.json()
    assert payload["repository_url"] == "https://github.com/example/wallet-dapp"
    assert payload["repository_branch"] == "develop"
    assert payload["repository_subdir"] == "packages/contracts"


def test_github_project_rejects_non_github_source(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="bad-project-source@example.com",
        username="bad-project-source",
        password="secret123",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}

    project_response = client.post(
        "/projects",
        headers=headers,
        json={
            "name": "Bad Git Source",
            "repository_url": "https://example.com/org/repo",
        },
    )

    assert project_response.status_code == 422


def test_user_can_create_github_dapp_test(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="dapp-owner@example.com",
        username="dapp-owner",
        password="secret123",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}

    project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "GitHub dApp", "description": "Repository-backed tests"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Hardhat repository test",
            "description": "Imports a dApp from GitHub",
            "scenario": "Clone dApp sources and execute its test suite",
            "docker_image": "node:20-bookworm-slim",
            "repository_url": "https://github.com/example/wallet-dapp",
            "repository_branch": "main",
            "repository_subdir": "contracts",
            "setup_command": "npm ci",
            "command": "npm test",
            "rpc_url": "http://hardhat:8545",
            "chain_id": 31337,
        },
    )

    assert test_response.status_code == 201
    payload = test_response.json()
    assert payload["repository_url"] == "https://github.com/example/wallet-dapp"
    assert payload["repository_branch"] == "main"
    assert payload["repository_subdir"] == "contracts"
    assert payload["setup_command"] == "npm ci"
    assert payload["rpc_url"] == "http://hardhat:8545"
    assert payload["chain_id"] == 31337


def test_github_dapp_test_rejects_non_github_source(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="bad-source@example.com",
        username="bad-source",
        password="secret123",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Bad Source", "description": None},
    )
    project_id = project_response.json()["id"]

    test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Unsafe import",
            "scenario": "Reject non-GitHub imports",
            "docker_image": "node:20-bookworm-slim",
            "repository_url": "https://example.com/org/repo",
            "command": "npm test",
        },
    )

    assert test_response.status_code == 422
