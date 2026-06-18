from __future__ import annotations

from tests.helpers import approve_registered_user_in_test_app, create_project_with_test, create_run
from app.models.run import RunStatus


#Zdes sobrana logika test_stats_overview_returns_extended_metrics, tak ee proshche podderzhivat.
def test_stats_overview_returns_extended_metrics(client, session_factory):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "analyst@example.com",
            "username": "analyst",
            "password": "StatsSecret123!",
        },
    )
    user_id = register_response.json()["user"]["id"]
    approve_registered_user_in_test_app(user_id)
    login_response = client.post(
        "/auth/login",
        json={"email": "analyst@example.com", "password": "StatsSecret123!"},
    )
    assert login_response.status_code == 200

    project_id_1, test_id_1 = create_project_with_test(
        session_factory,
        owner_id=user_id,
        project_name="Bridge",
        test_name="Bridge smoke",
    )
    _project_id_2, test_id_2 = create_project_with_test(
        session_factory,
        owner_id=user_id,
        project_name="Dex",
        test_name="Dex smoke",
    )

    create_run(
        session_factory,
        test_id=test_id_1,
        status=RunStatus.finished,
        created_days_ago=0,
        duration_seconds=12,
        queue_delay_seconds=4,
    )
    create_run(
        session_factory,
        test_id=test_id_1,
        status=RunStatus.failed,
        created_days_ago=1,
        duration_seconds=18,
        queue_delay_seconds=8,
        result_summary="Execution timed out",
        exit_code=124,
        log_messages=[
            "Preparing isolated Docker test environment",
            "[stdout] booting",
            "[stderr] Execution timed out",
        ],
    )
    create_run(
        session_factory,
        test_id=test_id_2,
        status=RunStatus.queued,
        created_days_ago=2,
    )
    create_run(
        session_factory,
        test_id=test_id_2,
        status=RunStatus.running,
        created_days_ago=3,
    )

    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    stats_response = client.get("/stats/overview", headers=headers)
    assert stats_response.status_code == 200
    payload = stats_response.json()

    assert payload["project_count"] == 2
    assert payload["test_count"] == 2
    assert payload["run_count"] == 4
    assert payload["successful_run_count"] == 1
    assert payload["failed_run_count"] == 1
    assert payload["queued_run_count"] == 1
    assert payload["running_run_count"] == 1
    assert payload["success_rate"] == 25.0
    assert payload["average_duration_seconds"] == 15.0
    assert payload["average_queue_time_seconds"] == 4.0
    assert payload["active_projects_last_7_days"] == 2
    assert payload["last_run_at"] is not None
    assert len(payload["daily_runs"]) == 7
    assert len(payload["runs_by_status"]) == 5
    assert payload["top_projects"][0]["project_name"] in {"Bridge", "Dex"}
    assert payload["top_projects"][0]["project_id"] in {project_id_1, _project_id_2}
    assert payload["failure_reasons"][0]["category"] == "timeout"
    assert payload["failure_reasons"][0]["count"] == 1
    assert payload["slowest_tests"][0]["test_name"] == "Bridge smoke"
    assert payload["recent_failures"][0]["failure_category"] == "timeout"
    assert payload["alerts"]
