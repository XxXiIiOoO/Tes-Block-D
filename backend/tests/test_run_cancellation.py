from __future__ import annotations

from tests.helpers import create_project_with_test, create_run, register_and_verify_user
from app.models.run import RunStatus


def test_user_can_cancel_queued_run(client, session_factory):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="cancel-owner@example.com",
        username="cancel_owner",
        password="StrongPass123!",
    )
    user_id = verify_response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    _project_id, test_id = create_project_with_test(
        session_factory,
        owner_id=user_id,
        project_name="Cancellation Project",
        test_name="Cancelable Test",
    )
    run_id = create_run(
        session_factory,
        test_id=test_id,
        status=RunStatus.queued,
        created_days_ago=0,
    )

    response = client.post(f"/runs/{run_id}/cancel", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["exit_code"] == 130

    logs_response = client.get(f"/runs/{run_id}/logs", headers=headers)
    assert logs_response.status_code == 200
    assert any("отмен" in log["message"].lower() for log in logs_response.json())


def test_cancelled_run_log_stream_returns_final_snapshot(client, session_factory):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="stream-owner@example.com",
        username="stream_owner",
        password="StrongPass123!",
    )
    user_id = verify_response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    _project_id, test_id = create_project_with_test(
        session_factory,
        owner_id=user_id,
        project_name="Stream Project",
        test_name="Streamed Test",
    )
    run_id = create_run(
        session_factory,
        test_id=test_id,
        status=RunStatus.cancelled,
        created_days_ago=0,
        result_summary="Запуск отменён пользователем",
        exit_code=130,
        log_messages=["Запуск отменён пользователем"],
    )

    with client.stream("GET", f"/runs/{run_id}/logs/stream", headers=headers) as response:
        payload = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "event: snapshot" in payload
    assert '"status": "cancelled"' in payload
    assert '"done": true' in payload
