from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.run import Run, RunStatus
from app.models.test import Test
from app.models.user import User
from app.services.audit import record_audit_event
from app.workers.jobs import run_test_job


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduleProcessResult:
    processed_tests: int
    enqueued_runs: int
    failed_to_enqueue: int
    skipped_tests: int
    enqueued_run_ids: list[int]


def ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def compute_next_schedule_time(
    *,
    now_utc: datetime,
    previous_next_run_at: datetime | None,
    interval_minutes: int,
) -> datetime:
    if previous_next_run_at is None:
        return now_utc + timedelta(minutes=interval_minutes)

    next_run_at = ensure_utc_datetime(previous_next_run_at)
    while next_run_at <= now_utc:
        next_run_at += timedelta(minutes=interval_minutes)
    return next_run_at


async def queue_run_for_test(db: Session, test: Test) -> Run:
    run = Run(test_id=test.id, status=RunStatus.queued)
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        await run_test_job.kiq(run.id)
    except Exception as exc:
        run.status = RunStatus.failed
        run.finished_at = datetime.now(timezone.utc)
        run.result_summary = "Не удалось поставить запуск в очередь Redis"
        db.add(run)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось поставить запуск в очередь",
        ) from exc
    return run


async def process_due_schedules(
    db: Session,
    *,
    actor: User | None = None,
    now_utc: datetime | None = None,
) -> ScheduleProcessResult:
    now_utc = now_utc or datetime.now(timezone.utc)
    tests = db.scalars(select(Test).where(Test.schedule_enabled.is_(True))).all()

    processed_tests = 0
    enqueued_runs = 0
    failed_to_enqueue = 0
    skipped_tests = 0
    enqueued_run_ids: list[int] = []

    for test in tests:
        if (
            not test.schedule_interval_minutes
            or test.schedule_next_run_at is None
            or ensure_utc_datetime(test.schedule_next_run_at) > now_utc
        ):
            skipped_tests += 1
            continue

        processed_tests += 1
        try:
            run = await queue_run_for_test(db, test)
        except HTTPException:
            failed_to_enqueue += 1
            continue

        enqueued_runs += 1
        enqueued_run_ids.append(run.id)
        test.schedule_next_run_at = compute_next_schedule_time(
            now_utc=now_utc,
            previous_next_run_at=test.schedule_next_run_at,
            interval_minutes=test.schedule_interval_minutes,
        )
        db.add(test)
        db.commit()
        record_audit_event(
            db,
            action="automation.schedule.enqueued",
            user=actor,
            entity_type="test",
            entity_id=test.id,
            details=f"run_id={run.id}",
            commit=True,
        )

    return ScheduleProcessResult(
        processed_tests=processed_tests,
        enqueued_runs=enqueued_runs,
        failed_to_enqueue=failed_to_enqueue,
        skipped_tests=skipped_tests,
        enqueued_run_ids=enqueued_run_ids,
    )


async def run_scheduler_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            result = await process_due_schedules(db)
            if result.enqueued_runs or result.failed_to_enqueue:
                logger.info(
                    "Scheduler tick: enqueued=%s failed=%s skipped=%s",
                    result.enqueued_runs,
                    result.failed_to_enqueue,
                    result.skipped_tests,
                )
        except Exception:
            logger.exception("Scheduler tick failed")
        finally:
            db.close()

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.scheduler_tick_seconds,
            )
        except asyncio.TimeoutError:
            continue
