from __future__ import annotations

from app.models.run import RunStatus
from tests.helpers import approve_registered_user_in_test_app, create_project_with_test, create_run


#Tut obrabatyvayu test_run_insights_classify_logs_and_recommendations, vse po delu i bez lishnego.
def test_run_insights_classify_logs_and_recommendations(client, session_factory):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "observer@example.com",
            "username": "observer",
            "password": "RunSecret123!",
        },
    )
    user_id = register_response.json()["user"]["id"]
    approve_registered_user_in_test_app(user_id)
    login_response = client.post(
        "/auth/login",
        json={"email": "observer@example.com", "password": "RunSecret123!"},
    )
    assert login_response.status_code == 200
    _project_id, test_id = create_project_with_test(
        session_factory,
        owner_id=user_id,
        project_name="Wallet",
        test_name="Wallet signing",
    )
    run_id = create_run(
        session_factory,
        test_id=test_id,
        status=RunStatus.failed,
        created_days_ago=0,
        duration_seconds=14,
        queue_delay_seconds=12,
        exit_code=1,
        result_summary="Test execution failed",
        log_messages=[
            "Preparing isolated Docker test environment",
            "[stdout] starting signature flow",
            "[stderr] Traceback: ModuleNotFoundError: No module named 'eth_keys'",
        ],
    )

    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    run_response = client.get(f"/runs/{run_id}", headers=headers)
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["duration_seconds"] == 14.0
    assert run_payload["queue_time_seconds"] == 12.0

    logs_response = client.get(f"/runs/{run_id}/logs", headers=headers)
    assert logs_response.status_code == 200
    logs_payload = logs_response.json()
    assert logs_payload[0]["source"] == "system"
    assert logs_payload[2]["source"] == "stderr"
    assert logs_payload[2]["severity"] == "error"

    insights_response = client.get(f"/runs/{run_id}/insights", headers=headers)
    assert insights_response.status_code == 200
    payload = insights_response.json()

    assert payload["failure_category"] == "dependency"
    assert payload["metrics"]["stderr_lines"] == 1
    assert payload["metrics"]["error_count"] == 1
    assert any("зависимость" in signal["title"].lower() for signal in payload["signals"])
    assert any("docker-образ" in recommendation.lower() for recommendation in payload["recommendations"])
    assert payload["latest_error"] == "Traceback: ModuleNotFoundError: No module named 'eth_keys'"
