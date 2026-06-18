from __future__ import annotations

from app.models.run import RunStatus
from tests.helpers import create_project_with_test, create_run, register_and_verify_user


def _create_report_run(client, session_factory) -> tuple[int, dict[str, str]]:
    register_response, verify_response = register_and_verify_user(
        client,
        email="reporter@example.com",
        username="reporter",
        password="RunSecret123!",
    )
    user_id = register_response.json()["user"]["id"]
    _project_id, test_id = create_project_with_test(
        session_factory,
        owner_id=user_id,
        project_name="Report Project",
        test_name="Report Smoke",
    )
    run_id = create_run(
        session_factory,
        test_id=test_id,
        status=RunStatus.failed,
        created_days_ago=0,
        duration_seconds=8,
        queue_delay_seconds=2,
        exit_code=1,
        result_summary="Report run failed",
        log_messages=[
            "Preparing report test",
            "[stdout] started",
            "[stderr] AssertionError: expected transfer event",
        ],
    )
    return run_id, {"Authorization": f"Bearer {verify_response.json()['access_token']}"}


def test_run_html_report_download(client, session_factory):
    run_id, headers = _create_report_run(client, session_factory)

    response = client.get(f"/runs/{run_id}/report.html", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["content-disposition"] == f'attachment; filename="run-{run_id}-report.html"'
    assert f"BlockTest Run #{run_id} Report" in response.text
    assert "Report Project" in response.text
    assert "AssertionError" in response.text


def test_run_pdf_report_download(client, session_factory):
    run_id, headers = _create_report_run(client, session_factory)

    response = client.get(f"/runs/{run_id}/report.pdf", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == f'attachment; filename="run-{run_id}-report.pdf"'
    assert response.content.startswith(b"%PDF")
