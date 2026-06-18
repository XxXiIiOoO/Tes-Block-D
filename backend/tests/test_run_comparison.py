from __future__ import annotations

from app.models.run import RunStatus
from tests.helpers import create_project_with_test, create_run, register_and_verify_user


def test_run_comparison_returns_metric_and_log_delta(client, session_factory):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="compare-owner@example.com",
        username="compare_owner",
        password="StrongPass123!",
    )
    user_id = verify_response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    _project_id, test_id = create_project_with_test(
        session_factory,
        owner_id=user_id,
        project_name="Comparison Project",
        test_name="Comparable Test",
    )
    baseline_run_id = create_run(
        session_factory,
        test_id=test_id,
        status=RunStatus.finished,
        created_days_ago=1,
        duration_seconds=10,
        queue_delay_seconds=1,
        log_messages=["shared line", "old line"],
    )
    current_run_id = create_run(
        session_factory,
        test_id=test_id,
        status=RunStatus.failed,
        created_days_ago=0,
        duration_seconds=15,
        queue_delay_seconds=3,
        exit_code=1,
        log_messages=["shared line", "new line"],
    )

    response = client.get(
        f"/runs/{current_run_id}/compare",
        headers=headers,
        params={"baseline_run_id": baseline_run_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["baseline_run"]["id"] == baseline_run_id
    assert payload["current_run"]["id"] == current_run_id
    assert payload["status_changed"] is True
    duration_metric = next(metric for metric in payload["metrics"] if metric["key"] == "duration_seconds")
    assert duration_metric["baseline"] == 10.0
    assert duration_metric["current"] == 15.0
    assert duration_metric["delta"] == 5.0
    assert payload["log_diff"]["added"] == ["new line"]
    assert payload["log_diff"]["removed"] == ["old line"]


def test_run_comparison_uses_previous_run_by_default(client, session_factory):
    _register_response, verify_response = register_and_verify_user(
        client,
        email="compare-default@example.com",
        username="compare_default",
        password="StrongPass123!",
    )
    user_id = verify_response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {verify_response.json()['access_token']}"}
    _project_id, test_id = create_project_with_test(
        session_factory,
        owner_id=user_id,
        project_name="Default Comparison Project",
        test_name="Default Comparable Test",
    )
    previous_run_id = create_run(
        session_factory,
        test_id=test_id,
        status=RunStatus.finished,
        created_days_ago=2,
        duration_seconds=4,
    )
    current_run_id = create_run(
        session_factory,
        test_id=test_id,
        status=RunStatus.finished,
        created_days_ago=0,
        duration_seconds=5,
    )

    response = client.get(f"/runs/{current_run_id}/compare", headers=headers)

    assert response.status_code == 200
    assert response.json()["baseline_run"]["id"] == previous_run_id
