from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from sqlalchemy import select

import app.api.routes.runs as runs_module
from app.models.run import Run, RunStatus
from tests.helpers import register_and_login_user


#Tut proveryayu, chto zapusk testa stavitsya v ochered i sohranyaetsya kak queued.
def test_run_endpoint_enqueues_job(client, monkeypatch):
    _register_response, login_response = register_and_login_user(
        client,
        email="queue-test@example.com",
        username="queue_test_user",
        password="StrongPass123!",
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Queue Project", "description": "Проверка постановки в очередь"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Queue Smoke Test",
            "description": "Проверка enqueue",
            "scenario": "Создать запуск и проверить постановку в очередь",
            "docker_image": "python:3.12-slim",
            "command": "python -c \"print('ok')\"",
        },
    )
    assert test_response.status_code == 201
    test_id = test_response.json()["id"]

    fake_kiq = AsyncMock()
    monkeypatch.setattr(runs_module.run_test_job, "kiq", fake_kiq)

    run_response = client.post(f"/tests/{test_id}/run", headers=headers)
    assert run_response.status_code == 201
    run_payload = run_response.json()
    assert run_payload["status"] == "queued"

    run_id = run_payload["id"]
    fake_kiq.assert_called_once_with(run_id)


#Tut proveryayu, chto pri padenii ocheredi endpoint vozvrashaet 503 i run stanovitsya failed.
def test_run_endpoint_handles_queue_failure(client, monkeypatch, session_factory):
    _register_response, login_response = register_and_login_user(
        client,
        email="queue-concurrency@example.com",
        username="queue_concurrency",
        password="StrongPass123!",
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Queue Failure Project", "description": "Проверка ошибки очереди"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Queue Failure Test",
            "description": "Проверка 503 от очереди",
            "scenario": "Искусственно уронить enqueue",
            "docker_image": "python:3.12-slim",
            "command": "python -c \"print('ok')\"",
        },
    )
    assert test_response.status_code == 201
    test_id = test_response.json()["id"]

    async def broken_kiq(*args, **kwargs):
        raise ConnectionError("queue unavailable")

    monkeypatch.setattr(runs_module.run_test_job, "kiq", broken_kiq)

    run_response = client.post(f"/tests/{test_id}/run", headers=headers)
    assert run_response.status_code == 503

    db = session_factory()
    try:
        run = db.scalar(select(Run).order_by(Run.id.desc()))
        assert run is not None
        assert run.status == RunStatus.failed
        assert run.result_summary is not None
    finally:
        db.close()
