from __future__ import annotations

from tests.helpers import register_and_login_user


#Tut smoke-test po osnovnomu scenariyu raboty platformy.
def test_project_system_smoke_flow(client):
    _register_response, login_response = register_and_login_user(
        client,
        email="system-smoke@example.com",
        username="system_smoke_user",
        password="StrongPass123!",
    )
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    project_response = client.post(
        "/projects",
        headers=headers,
        json={
            "name": "System Smoke Project",
            "description": "Проверка базового e2e-сценария",
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Smoke Test Scenario",
            "description": "Проверка API и модели тестов",
            "scenario": "Создать тест, получить его, оставить сообщение в чате",
            "docker_image": "python:3.12-slim",
            "command": "python -c \"print('smoke ok')\"",
        },
    )
    assert test_response.status_code == 201
    test_id = test_response.json()["id"]

    get_test_response = client.get(f"/tests/{test_id}", headers=headers)
    assert get_test_response.status_code == 200
    assert get_test_response.json()["name"] == "Smoke Test Scenario"

    chat_post_response = client.post(
        f"/tests/{test_id}/chat",
        headers=headers,
        json={"message": "Проверка рабочего чата в тесте"},
    )
    assert chat_post_response.status_code == 201

    chat_list_response = client.get(f"/tests/{test_id}/chat", headers=headers)
    assert chat_list_response.status_code == 200
    assert len(chat_list_response.json()) == 1

    runs_list_response = client.get("/runs", headers=headers)
    assert runs_list_response.status_code == 200

    stats_response = client.get("/stats/overview", headers=headers)
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["project_count"] >= 1
    assert stats_payload["test_count"] >= 1
