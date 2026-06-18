from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.routes.projects import get_project_access_role, project_access_filter
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMemberRole
from app.models.run import Run
from app.models.test import Test
from app.models.user import User, UserRole
from app.schemas.automation import (
    AutomationRunTriggerResponse,
    ScheduleTickResponse,
    TestAutomationRead,
    TestAutomationUpdate,
    WebhookTokenRotateResponse,
)
from app.services.audit import record_audit_event
from app.services.scheduler import (
    compute_next_schedule_time,
    process_due_schedules,
    queue_run_for_test,
)


router = APIRouter(tags=["automation"])


#Tut ya vynes _hash_webhook_token, chtoby ne razduvat ostalnoy kod.
def _hash_webhook_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


#Eto otdelnyy shag _serialize_automation_config, chtoby ne kopipastit odno i to zhe.
def _serialize_automation_config(test: Test) -> TestAutomationRead:
    return TestAutomationRead(
        test_id=test.id,
        baseline_run_id=test.baseline_run_id,
        gate_enabled=test.gate_enabled,
        gate_max_duration_seconds=test.gate_max_duration_seconds,
        gate_max_error_logs=test.gate_max_error_logs,
        schedule_enabled=test.schedule_enabled,
        schedule_interval_minutes=test.schedule_interval_minutes,
        schedule_next_run_at=test.schedule_next_run_at,
        webhook_enabled=test.webhook_enabled,
        webhook_token_configured=bool(test.webhook_token_hash),
    )


#Tut obrabatyvayu _get_accessible_test, vse po delu i bez lishnego.
def _get_accessible_test(db: Session, current_user: User, test_id: int) -> Test:
    query = select(Test).join(Project, Test.project_id == Project.id).where(Test.id == test_id)
    if not current_user.is_admin:
        query = query.where(project_access_filter(current_user))

    test = db.scalar(query)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден")
    return test


def _require_test_write_access(db: Session, current_user: User, test_id: int) -> Test:
    if current_user.role == UserRole.viewer.value and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль наблюдателя имеет только доступ на чтение",
        )
    test = _get_accessible_test(db, current_user, test_id)
    project = db.get(Project, test.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден")
    role = get_project_access_role(db, current_user, project)
    if role not in {"admin", "owner", ProjectMemberRole.developer.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления автоматизацией",
        )
    return test


#Tut ya vynes get_test_automation_config, chtoby ne razduvat ostalnoy kod.
@router.get("/tests/{test_id}/automation", response_model=TestAutomationRead)
def get_test_automation_config(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestAutomationRead:
    test = _require_test_write_access(db, current_user, test_id)
    return _serialize_automation_config(test)


#Zdes sobrana logika update_test_automation_config, tak ee proshche podderzhivat.
@router.patch("/tests/{test_id}/automation", response_model=TestAutomationRead)
def update_test_automation_config(
    test_id: int,
    payload: TestAutomationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestAutomationRead:
    test = _require_test_write_access(db, current_user, test_id)
    updates = payload.model_dump(exclude_unset=True)

    if "baseline_run_id" in updates:
        baseline_run_id = updates["baseline_run_id"]
        if baseline_run_id is not None:
            baseline_run = db.scalar(select(Run).where(Run.id == baseline_run_id))
            if baseline_run is None or baseline_run.test_id != test.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Базовый запуск не найден или относится к другому тесту",
                )
        test.baseline_run_id = baseline_run_id

    for field in (
        "gate_enabled",
        "gate_max_duration_seconds",
        "gate_max_error_logs",
        "schedule_enabled",
        "schedule_interval_minutes",
        "webhook_enabled",
    ):
        if field in updates:
            setattr(test, field, updates[field])

    if test.schedule_enabled:
        if not test.schedule_interval_minutes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для расписания укажите интервал в минутах",
            )
        from datetime import datetime, timezone

        now_utc = datetime.now(timezone.utc)
        test.schedule_next_run_at = compute_next_schedule_time(
            now_utc=now_utc,
            previous_next_run_at=test.schedule_next_run_at,
            interval_minutes=test.schedule_interval_minutes,
        )
    else:
        test.schedule_next_run_at = None

    if test.webhook_enabled and not test.webhook_token_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала сгенерируйте токен вебхука",
        )

    db.add(test)
    db.commit()
    db.refresh(test)
    changed_fields = ", ".join(sorted(updates.keys())) if updates else "no fields"
    record_audit_event(
        db,
        action="automation.updated",
        user=current_user,
        entity_type="test",
        entity_id=test.id,
        details=changed_fields,
        commit=True,
    )
    return _serialize_automation_config(test)


#Funkciya rotate_webhook_token zakryvaet konkretnuyu zadachu v etom meste.
@router.post(
    "/tests/{test_id}/automation/webhook-token",
    response_model=WebhookTokenRotateResponse,
)
def rotate_webhook_token(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WebhookTokenRotateResponse:
    test = _require_test_write_access(db, current_user, test_id)
    token = secrets.token_urlsafe(32)
    test.webhook_token_hash = _hash_webhook_token(token)
    test.webhook_enabled = True
    db.add(test)
    db.commit()
    record_audit_event(
        db,
        action="automation.webhook.token_rotated",
        user=current_user,
        entity_type="test",
        entity_id=test.id,
        details="token regenerated",
        commit=True,
    )
    return WebhookTokenRotateResponse(token=token)


#Tut ya vynes trigger_test_webhook, chtoby ne razduvat ostalnoy kod.
@router.post(
    "/automation/webhook/{test_id}",
    response_model=AutomationRunTriggerResponse,
)
async def trigger_test_webhook(
    test_id: int,
    token: str = Query(min_length=10),
    db: Session = Depends(get_db),
) -> AutomationRunTriggerResponse:
    test = db.scalar(select(Test).where(Test.id == test_id))
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден")
    if not test.webhook_enabled or not test.webhook_token_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вебхук для теста выключен",
        )

    if test.webhook_token_hash != _hash_webhook_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен вебхука",
        )

    run = await queue_run_for_test(db, test)
    record_audit_event(
        db,
        action="automation.webhook.triggered",
        user=None,
        entity_type="test",
        entity_id=test.id,
        details=f"run_id={run.id}",
        commit=True,
    )
    return AutomationRunTriggerResponse(
        run_id=run.id,
        status=run.status,
        created_at=run.created_at,
    )


#Tut obrabatyvayu run_schedule_tick, vse po delu i bez lishnego.
@router.post("/automation/schedule/tick", response_model=ScheduleTickResponse)
async def run_schedule_tick(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> ScheduleTickResponse:
    result = await process_due_schedules(db, actor=current_admin)

    return ScheduleTickResponse(
        processed_tests=result.processed_tests,
        enqueued_runs=result.enqueued_runs,
        failed_to_enqueue=result.failed_to_enqueue,
        skipped_tests=result.skipped_tests,
        enqueued_run_ids=result.enqueued_run_ids,
    )
