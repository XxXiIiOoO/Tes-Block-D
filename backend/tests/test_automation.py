from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from sqlalchemy import select

import app.services.scheduler as scheduler_module
from app.models.run import Run
from app.models.test import Test
from tests.helpers import promote_user_to_admin, register_and_verify_user


#Funkciya _create_test_for_user zakryvaet konkretnuyu zadachu v etom meste.
def _create_test_for_user(client, headers: dict[str, str]) -> int:
    project_response = client.post(
        "/projects",
        headers=headers,
        json={"name": "Automation Project", "description": "Automation coverage"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    test_response = client.post(
        f"/projects/{project_id}/tests",
        headers=headers,
        json={
            "name": "Automation Scenario",
            "description": "Проверка автоматизационных возможностей",
            "scenario": "Запуск через webhook, расписание и quality-gates",
            "docker_image": "python:3.12-slim",
            "command": "python -c \"print('ok')\"",
        },
    )
    assert test_response.status_code == 201
    return test_response.json()["id"]


#Tut obrabatyvayu test_automation_config_and_webhook_token, vse po delu i bez lishnego.
def test_automation_config_and_webhook_token(client):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="automation-owner@example.com",
        username="automation_owner",
        password="StrongPass123!",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    test_id = _create_test_for_user(client, headers)

    update_response = client.patch(
        f"/tests/{test_id}/automation",
        headers=headers,
        json={
            "gate_enabled": True,
            "gate_max_duration_seconds": 12,
            "gate_max_error_logs": 0,
            "schedule_enabled": True,
            "schedule_interval_minutes": 30,
        },
    )
    assert update_response.status_code == 200
    update_payload = update_response.json()
    assert update_payload["gate_enabled"] is True
    assert update_payload["schedule_enabled"] is True
    assert update_payload["schedule_interval_minutes"] == 30
    assert update_payload["schedule_next_run_at"] is not None

    token_response = client.post(
        f"/tests/{test_id}/automation/webhook-token",
        headers=headers,
    )
    assert token_response.status_code == 200
    token = token_response.json()["token"]
    assert token

    get_response = client.get(f"/tests/{test_id}/automation", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["webhook_token_configured"] is True
    assert get_response.json()["webhook_enabled"] is True


#Tut ya vynes test_webhook_trigger_queues_run, chtoby ne razduvat ostalnoy kod.
def test_webhook_trigger_queues_run(client, monkeypatch):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="automation-webhook@example.com",
        username="automation_webhook_user",
        password="StrongPass123!",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    test_id = _create_test_for_user(client, headers)

    token_response = client.post(
        f"/tests/{test_id}/automation/webhook-token",
        headers=headers,
    )
    token = token_response.json()["token"]

    fake_kiq = AsyncMock()
    monkeypatch.setattr(scheduler_module.run_test_job, "kiq", fake_kiq)

    webhook_response = client.post(
        f"/automation/webhook/{test_id}",
        params={"token": token},
    )
    assert webhook_response.status_code == 200
    payload = webhook_response.json()
    assert payload["status"] == "queued"
    fake_kiq.assert_called_once_with(payload["run_id"])


#Zdes sobrana logika test_schedule_tick_enqueues_due_tests_for_admin, tak ee proshche podderzhivat.
def test_schedule_tick_enqueues_due_tests_for_admin(client, monkeypatch, session_factory):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="automation-admin@example.com",
        username="automation_admin_user",
        password="StrongPass123!",
    )
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    user_id = verify_response.json()["user"]["id"]
    promote_user_to_admin(session_factory, user_id=user_id)

    test_id = _create_test_for_user(client, headers)
    update_response = client.patch(
        f"/tests/{test_id}/automation",
        headers=headers,
        json={"schedule_enabled": True, "schedule_interval_minutes": 5},
    )
    assert update_response.status_code == 200

    db = session_factory()
    try:
        test = db.scalar(select(Test).where(Test.id == test_id))
        assert test is not None
        test.schedule_next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.add(test)
        db.commit()
    finally:
        db.close()

    fake_kiq = AsyncMock()
    monkeypatch.setattr(scheduler_module.run_test_job, "kiq", fake_kiq)

    tick_response = client.post("/automation/schedule/tick", headers=headers)
    assert tick_response.status_code == 200
    payload = tick_response.json()
    assert payload["enqueued_runs"] == 1
    assert payload["failed_to_enqueue"] == 0

    db = session_factory()
    try:
        run = db.scalar(select(Run).order_by(Run.id.desc()))
        assert run is not None
        assert run.test_id == test_id
        assert run.status.value == "queued"
    finally:
        db.close()
