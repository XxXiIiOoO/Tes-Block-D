from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.security import get_password_hash
from app.api.deps import get_db
from app.main import app
from app.models.project import Project
from app.models.run import Run, RunLog, RunStatus
from app.models.test import Test
from app.models.user import User


#Tut ya vynes create_user, chtoby ne razduvat ostalnoy kod.
def create_user(
    session_factory,
    *,
    email: str,
    username: str,
    password: str,
    is_admin: bool = False,
    role: str | None = None,
    email_verified: bool = True,
):
    db = session_factory()
    try:
        resolved_role = role or ("admin" if is_admin else "worker")
        user = User(
            email=email,
            username=username,
            password_hash=get_password_hash(password),
            is_admin=is_admin,
            role=resolved_role,
            email_verified=email_verified,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    finally:
        db.close()


#Funkciya promote_user_to_admin zakryvaet konkretnuyu zadachu v etom meste.
def promote_user_to_admin(session_factory, *, user_id: int):
    db = session_factory()
    try:
        user = db.get(User, user_id)
        if user is not None:
            user.is_admin = True
            user.role = "admin"
            user.email_verified = True
            db.add(user)
            db.commit()
    finally:
        db.close()


def approve_registered_user_in_test_app(user_id: int) -> None:
    override_get_db = app.dependency_overrides[get_db]
    db_generator = override_get_db()
    db = next(db_generator)
    try:
        user = db.get(User, user_id)
        if user is not None:
            user.email_verified = True
            user.email_verification_token_hash = None
            user.email_verification_expires_at = None
            db.add(user)
            db.commit()
    finally:
        db_generator.close()


#Funkciya register_and_login_user zakryvaet konkretnuyu zadachu v etom meste.
def register_and_login_user(client, *, email: str, username: str, password: str):
    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    approve_registered_user_in_test_app(register_response.json()["user"]["id"])

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return register_response, login_response


def register_and_verify_user(client, *, email: str, username: str, password: str):
    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    approve_registered_user_in_test_app(register_response.json()["user"]["id"])
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return register_response, login_response


#Funkciya create_project_with_test zakryvaet konkretnuyu zadachu v etom meste.
def create_project_with_test(
    session_factory,
    *,
    owner_id: int,
    project_name: str,
    test_name: str,
):
    db = session_factory()
    try:
        project = Project(
            owner_id=owner_id,
            name=project_name,
            description=f"{project_name} description",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        test = Test(
            project_id=project.id,
            name=test_name,
            description=f"{test_name} description",
            scenario="Smoke-test blockchain transfer flow",
            docker_image="python:3.12-slim",
            command="python -c \"print('ok')\"",
        )
        db.add(test)
        db.commit()
        db.refresh(test)
        return project.id, test.id
    finally:
        db.close()


#Funkciya create_run zakryvaet konkretnuyu zadachu v etom meste.
def create_run(
    session_factory,
    *,
    test_id: int,
    status: RunStatus,
    created_days_ago: int,
    duration_seconds: int | None = None,
    queue_delay_seconds: int = 0,
    result_summary: str | None = None,
    exit_code: int | None = None,
    log_messages: list[str] | None = None,
):
    db = session_factory()
    try:
        created_at = datetime.now(timezone.utc) - timedelta(days=created_days_ago)
        started_at = created_at + timedelta(seconds=queue_delay_seconds)
        finished_at = None
        if duration_seconds is not None:
            finished_at = started_at + timedelta(seconds=duration_seconds)

        run = Run(
            test_id=test_id,
            status=status,
            created_at=created_at,
            started_at=started_at if status != RunStatus.queued else None,
            finished_at=finished_at,
            exit_code=(
                exit_code
                if exit_code is not None
                else (0 if status == RunStatus.finished else (1 if status == RunStatus.failed else None))
            ),
            result_summary=result_summary or f"{status.value} result",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        if log_messages:
            for index, message in enumerate(log_messages):
                db.add(
                    RunLog(
                        run_id=run.id,
                        message=message,
                        created_at=created_at + timedelta(seconds=index),
                    )
                )
            db.commit()
        return run.id
    finally:
        db.close()
