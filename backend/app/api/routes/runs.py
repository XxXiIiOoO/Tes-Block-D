import asyncio
import json
from collections import Counter
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.api.routes.projects import get_project_access_role, project_access_filter
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMemberRole
from app.models.run import Run, RunLog, RunStatus
from app.models.test import Test
from app.models.user import User, UserRole
from app.schemas.run import (
    RunCreateResponse,
    RunComparisonMetricRead,
    RunComparisonRead,
    RunInsightsRead,
    RunLogDiffRead,
    RunQualityGateRead,
    RunLogRead,
    RunRead,
    RunSignalRead,
    RunMetricsRead,
)
from app.services.observability import (
    analyze_run,
    compute_duration_seconds,
    compute_queue_time_seconds,
    serialize_run_log_metadata,
)
from app.services.run_reports import RunReportData, build_run_report_html, build_run_report_pdf
from app.services.audit import record_audit_event
from app.workers.jobs import run_test_job


router = APIRouter(tags=["runs"])
SORT_FIELDS = {"created_at": Run.created_at, "started_at": Run.started_at}


#Tut ya vynes parse_date_filter, chtoby ne razduvat ostalnoy kod.
def parse_date_filter(value: str, *, end_of_day: bool) -> datetime:
    normalized = value.strip()
    try:
        if "T" in normalized:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        parsed_date = datetime.strptime(normalized, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный формат даты. Используйте YYYY-MM-DD или ISO datetime.",
        ) from exc

    selected_time = time.max if end_of_day else time.min
    return datetime.combine(parsed_date, selected_time, tzinfo=timezone.utc)


#Eto otdelnyy shag get_accessible_test, chtoby ne kopipastit odno i to zhe.
def get_accessible_test(db: Session, current_user: User, test_id: int) -> Test:
    query = (
        select(Test)
        .options(joinedload(Test.project))
        .join(Project, Test.project_id == Project.id)
        .where(Test.id == test_id)
    )
    if not current_user.is_admin:
        query = query.where(project_access_filter(current_user))

    test = db.scalar(query)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден")
    return test


def require_test_write_access(db: Session, current_user: User, test_id: int) -> Test:
    if current_user.role == UserRole.viewer.value and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль наблюдателя имеет только доступ на чтение",
        )
    test = get_accessible_test(db, current_user, test_id)
    role = get_project_access_role(db, current_user, test.project)
    if role not in {"admin", "owner", ProjectMemberRole.developer.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для запуска теста",
        )
    return test


#Tut ya vynes get_accessible_run, chtoby ne razduvat ostalnoy kod.
def get_accessible_run(db: Session, current_user: User, run_id: int) -> Run:
    query = (
        select(Run)
        .options(joinedload(Run.test).joinedload(Test.project), joinedload(Run.logs))
        .join(Test, Run.test_id == Test.id)
        .join(Project, Test.project_id == Project.id)
        .where(Run.id == run_id)
    )
    if not current_user.is_admin:
        query = query.where(project_access_filter(current_user))

    run = db.execute(query).unique().scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запуск не найден")
    return run


def require_run_write_access(db: Session, current_user: User, run_id: int) -> Run:
    if current_user.role == UserRole.viewer.value and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль наблюдателя имеет только доступ на чтение",
        )
    run = get_accessible_run(db, current_user, run_id)
    if run.test is None or run.test.project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запуск не найден")
    role = get_project_access_role(db, current_user, run.test.project)
    if role not in {"admin", "owner", ProjectMemberRole.developer.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления запуском",
        )
    return run


def get_accessible_run_summary(db: Session, current_user: User, run_id: int) -> Run:
    query = (
        select(Run)
        .options(joinedload(Run.test).joinedload(Test.project))
        .join(Test, Run.test_id == Test.id)
        .join(Project, Test.project_id == Project.id)
        .where(Run.id == run_id)
    )
    if not current_user.is_admin:
        query = query.where(project_access_filter(current_user))

    run = db.execute(query).unique().scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запуск не найден")
    return run


#Tut ya vynes serialize_run, chtoby ne razduvat ostalnoy kod.
def serialize_run(run: Run) -> RunRead:
    return RunRead(
        id=run.id,
        test_id=run.test_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_seconds=compute_duration_seconds(run),
        queue_time_seconds=compute_queue_time_seconds(run),
        result_summary=run.result_summary,
        exit_code=run.exit_code,
        created_at=run.created_at,
        test_name=run.test.name if run.test else None,
        project_id=run.test.project.id if run.test and run.test.project else None,
        project_name=run.test.project.name if run.test and run.test.project else None,
    )


#Eto otdelnyy shag serialize_run_log, chtoby ne kopipastit odno i to zhe.
def serialize_run_log(log: RunLog) -> RunLogRead:
    metadata = serialize_run_log_metadata(log)
    return RunLogRead(
        id=log.id,
        run_id=log.run_id,
        message=log.message,
        source=metadata.source,
        severity=metadata.severity,
        created_at=log.created_at,
    )


def encode_sse(event: str, data: object) -> str:
    payload = json.dumps(jsonable_encoder(data), ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


#Funkciya build_quality_gate_insight zakryvaet konkretnuyu zadachu v etom meste.
def build_quality_gate_insight(run: Run, analysis, db: Session) -> RunQualityGateRead:
    test = run.test
    if test is None or not test.gate_enabled:
        return RunQualityGateRead(
            enabled=False,
            passed=None,
            baseline_run_id=test.baseline_run_id if test else None,
            baseline_delta_seconds=None,
            reasons=[],
        )

    reasons: list[str] = []
    baseline_delta_seconds: float | None = None
    if run.status in {RunStatus.queued, RunStatus.running}:
        return RunQualityGateRead(
            enabled=True,
            passed=None,
            baseline_run_id=test.baseline_run_id,
            baseline_delta_seconds=None,
            reasons=["Запуск ещё не завершён, оценка гейта отложена"],
        )

    if run.status != RunStatus.finished:
        reasons.append("Запуск завершился неуспешно")

    if (
        test.gate_max_duration_seconds is not None
        and analysis.metrics.duration_seconds is not None
        and analysis.metrics.duration_seconds > test.gate_max_duration_seconds
    ):
        reasons.append(
            f"Длительность {analysis.metrics.duration_seconds:.2f}с выше порога {test.gate_max_duration_seconds:.2f}с"
        )

    if (
        test.gate_max_error_logs is not None
        and analysis.metrics.error_count > test.gate_max_error_logs
    ):
        reasons.append(
            f"Ошибочных строк в логах {analysis.metrics.error_count}, порог {test.gate_max_error_logs}"
        )

    if test.baseline_run_id is not None:
        baseline_run = db.scalar(select(Run).where(Run.id == test.baseline_run_id))
        if baseline_run is None or baseline_run.test_id != run.test_id:
            reasons.append("Базовый запуск не найден или относится к другому тесту")
        else:
            baseline_duration = compute_duration_seconds(baseline_run)
            current_duration = analysis.metrics.duration_seconds
            if baseline_duration is not None and current_duration is not None:
                baseline_delta_seconds = round(current_duration - baseline_duration, 2)
                if baseline_duration > 0 and current_duration > baseline_duration * 1.5:
                    reasons.append(
                        "Текущий запуск дольше базового более чем на 50%"
                    )

    return RunQualityGateRead(
        enabled=True,
        passed=len(reasons) == 0,
        baseline_run_id=test.baseline_run_id,
        baseline_delta_seconds=baseline_delta_seconds,
        reasons=reasons,
    )


#Tut obrabatyvayu serialize_run_insights, vse po delu i bez lishnego.
def serialize_run_insights(run: Run, db: Session) -> RunInsightsRead:
    analysis = analyze_run(run)
    quality_gate = build_quality_gate_insight(run, analysis, db)
    return RunInsightsRead(
        summary=analysis.summary,
        failure_category=analysis.failure_category,
        latest_error=analysis.latest_error,
        metrics=RunMetricsRead(
            duration_seconds=analysis.metrics.duration_seconds,
            queue_time_seconds=analysis.metrics.queue_time_seconds,
            total_logs=analysis.metrics.total_logs,
            stdout_lines=analysis.metrics.stdout_lines,
            stderr_lines=analysis.metrics.stderr_lines,
            system_lines=analysis.metrics.system_lines,
            info_count=analysis.metrics.info_count,
            warning_count=analysis.metrics.warning_count,
            error_count=analysis.metrics.error_count,
        ),
        signals=[
            RunSignalRead(severity=signal.severity, title=signal.title, detail=signal.detail)
            for signal in analysis.signals
        ],
        recommendations=analysis.recommendations,
        quality_gate=quality_gate,
    )


def build_run_report_data(run: Run, db: Session) -> RunReportData:
    return RunReportData(
        run=serialize_run(run),
        insights=serialize_run_insights(run, db),
        logs=[serialize_run_log(log) for log in run.logs],
    )


def build_run_export_payload(report: RunReportData) -> dict[str, object]:
    return {
        "run": report.run.model_dump(mode="json"),
        "insights": report.insights.model_dump(mode="json"),
        "logs": [log.model_dump(mode="json") for log in report.logs],
    }


def _metric_delta(current: float | int | None, baseline: float | int | None) -> tuple[float | None, float | None]:
    if current is None or baseline is None:
        return None, None
    delta = round(float(current) - float(baseline), 2)
    if baseline == 0:
        return delta, None
    return delta, round(delta / float(baseline) * 100, 2)


def _comparison_metric(
    key: str,
    label: str,
    current: float | int | str | None,
    baseline: float | int | str | None,
    unit: str | None = None,
) -> RunComparisonMetricRead:
    delta: float | None = None
    delta_percent: float | None = None
    if isinstance(current, (int, float)) and isinstance(baseline, (int, float)):
        delta, delta_percent = _metric_delta(current, baseline)
    return RunComparisonMetricRead(
        key=key,
        label=label,
        current=current,
        baseline=baseline,
        delta=delta,
        delta_percent=delta_percent,
        unit=unit,
    )


def _normalized_log_lines(run: Run) -> list[str]:
    return [
        serialize_run_log(log).message.replace("[stdout] ", "").replace("[stderr] ", "").strip()
        for log in run.logs
        if log.message.strip()
    ]


def _build_log_diff(current_run: Run, baseline_run: Run) -> RunLogDiffRead:
    current_counts = Counter(_normalized_log_lines(current_run))
    baseline_counts = Counter(_normalized_log_lines(baseline_run))
    added_counts = current_counts - baseline_counts
    removed_counts = baseline_counts - current_counts
    unchanged_count = sum((current_counts & baseline_counts).values())
    added = list(added_counts.elements())[:20]
    removed = list(removed_counts.elements())[:20]
    return RunLogDiffRead(
        added=added,
        removed=removed,
        added_count=sum(added_counts.values()),
        removed_count=sum(removed_counts.values()),
        unchanged_count=unchanged_count,
    )


def _find_previous_run(db: Session, current_run: Run) -> Run | None:
    query = (
        select(Run)
        .options(joinedload(Run.test).joinedload(Test.project), joinedload(Run.logs))
        .where(
            Run.test_id == current_run.test_id,
            Run.id != current_run.id,
            Run.created_at < current_run.created_at,
        )
        .order_by(Run.created_at.desc())
    )
    return db.execute(query).unique().scalars().first()


def build_run_comparison(current_run: Run, baseline_run: Run | None) -> RunComparisonRead:
    current_analysis = analyze_run(current_run)
    baseline_analysis = analyze_run(baseline_run) if baseline_run is not None else None

    metrics = [
        _comparison_metric(
            "duration_seconds",
            "Duration",
            current_analysis.metrics.duration_seconds,
            baseline_analysis.metrics.duration_seconds if baseline_analysis else None,
            "s",
        ),
        _comparison_metric(
            "queue_time_seconds",
            "Queue wait",
            current_analysis.metrics.queue_time_seconds,
            baseline_analysis.metrics.queue_time_seconds if baseline_analysis else None,
            "s",
        ),
        _comparison_metric(
            "total_logs",
            "Log lines",
            current_analysis.metrics.total_logs,
            baseline_analysis.metrics.total_logs if baseline_analysis else None,
        ),
        _comparison_metric(
            "warning_count",
            "Warnings",
            current_analysis.metrics.warning_count,
            baseline_analysis.metrics.warning_count if baseline_analysis else None,
        ),
        _comparison_metric(
            "error_count",
            "Errors",
            current_analysis.metrics.error_count,
            baseline_analysis.metrics.error_count if baseline_analysis else None,
        ),
        _comparison_metric(
            "failure_category",
            "Failure category",
            current_analysis.failure_category,
            baseline_analysis.failure_category if baseline_analysis else None,
        ),
    ]

    return RunComparisonRead(
        current_run=serialize_run(current_run),
        baseline_run=serialize_run(baseline_run) if baseline_run else None,
        metrics=metrics,
        status_changed=baseline_run is not None and current_run.status != baseline_run.status,
        exit_code_changed=baseline_run is not None and current_run.exit_code != baseline_run.exit_code,
        log_diff=_build_log_diff(current_run, baseline_run) if baseline_run else None,
    )


#Eto otdelnyy shag enqueue_run, chtoby ne kopipastit odno i to zhe.
async def enqueue_run(run_id: int, db: Session, run: Run) -> None:
    try:
        await run_test_job.kiq(run_id)
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


#Tut ya vynes run_test, chtoby ne razduvat ostalnoy kod.
@router.post("/tests/{test_id}/run", response_model=RunCreateResponse, status_code=status.HTTP_201_CREATED)
async def run_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunCreateResponse:
    test = require_test_write_access(db, current_user, test_id)
    run = Run(test_id=test.id, status=RunStatus.queued)
    db.add(run)
    db.commit()
    db.refresh(run)
    run.test = test
    await enqueue_run(run.id, db, run)
    record_audit_event(
        db,
        action="run.queued",
        user=current_user,
        entity_type="run",
        entity_id=run.id,
        details=f"test_id={test.id}",
        commit=True,
    )
    return RunCreateResponse(**serialize_run(run).model_dump())


#Tut ya vynes rerun_test, chtoby ne razduvat ostalnoy kod.
@router.post("/runs/{run_id}/rerun", response_model=RunCreateResponse, status_code=status.HTTP_201_CREATED)
async def rerun_test(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunCreateResponse:
    existing_run = require_run_write_access(db, current_user, run_id)
    run = Run(test_id=existing_run.test_id, status=RunStatus.queued)
    db.add(run)
    db.commit()
    db.refresh(run)
    run.test = existing_run.test
    await enqueue_run(run.id, db, run)
    record_audit_event(
        db,
        action="run.rerun.queued",
        user=current_user,
        entity_type="run",
        entity_id=run.id,
        details=f"source_run_id={existing_run.id}",
        commit=True,
    )
    return RunCreateResponse(**serialize_run(run).model_dump())


#Zdes sobrana logika list_runs, tak ee proshche podderzhivat.
@router.get("/runs", response_model=list[RunRead])
def list_runs(
    status_filter: RunStatus | None = Query(default=None, alias="status"),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    sort_by: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RunRead]:
    sort_field = SORT_FIELDS.get(sort_by, Run.created_at)
    ordering = desc(sort_field) if order.lower() == "desc" else asc(sort_field)

    query = (
        select(Run)
        .options(joinedload(Run.test).joinedload(Test.project))
        .join(Test, Run.test_id == Test.id)
        .join(Project, Test.project_id == Project.id)
        .order_by(ordering)
    )
    if not current_user.is_admin:
        query = query.where(project_access_filter(current_user))
    if status_filter is not None:
        query = query.where(Run.status == status_filter)
    if date_from:
        query = query.where(Run.created_at >= parse_date_filter(date_from, end_of_day=False))
    if date_to:
        query = query.where(Run.created_at <= parse_date_filter(date_to, end_of_day=True))

    runs = db.scalars(query).all()
    return [serialize_run(run) for run in runs]


#Funkciya list_test_runs zakryvaet konkretnuyu zadachu v etom meste.
@router.get("/tests/{test_id}/runs", response_model=list[RunRead])
def list_test_runs(
    test_id: int,
    status_filter: RunStatus | None = Query(default=None, alias="status"),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    sort_by: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RunRead]:
    get_accessible_test(db, current_user, test_id)
    sort_field = SORT_FIELDS.get(sort_by, Run.created_at)
    ordering = desc(sort_field) if order.lower() == "desc" else asc(sort_field)

    query = (
        select(Run)
        .options(joinedload(Run.test).joinedload(Test.project))
        .where(Run.test_id == test_id)
        .order_by(ordering)
    )
    if status_filter is not None:
        query = query.where(Run.status == status_filter)
    if date_from:
        query = query.where(Run.created_at >= parse_date_filter(date_from, end_of_day=False))
    if date_to:
        query = query.where(Run.created_at <= parse_date_filter(date_to, end_of_day=True))

    runs = db.scalars(query).all()
    return [serialize_run(run) for run in runs]


@router.post("/runs/{run_id}/cancel", response_model=RunRead)
def cancel_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunRead:
    run = require_run_write_access(db, current_user, run_id)
    if run.status not in {RunStatus.queued, RunStatus.running}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Можно отменить только запуск в очереди или в процессе выполнения",
        )

    run.status = RunStatus.cancelled
    run.finished_at = datetime.now(timezone.utc)
    run.exit_code = 130
    run.result_summary = "Запуск отменён пользователем"
    run.logs.append(RunLog(message="Запуск отменён пользователем"))
    db.add(run)
    db.commit()
    db.refresh(run)
    record_audit_event(
        db,
        action="run.cancelled",
        user=current_user,
        entity_type="run",
        entity_id=run.id,
        details=f"test_id={run.test_id}",
        commit=True,
    )
    return serialize_run(run)


#Eto otdelnyy shag get_run, chtoby ne kopipastit odno i to zhe.
@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunRead:
    run = get_accessible_run(db, current_user, run_id)
    return serialize_run(run)


@router.get("/runs/{run_id}/compare", response_model=RunComparisonRead)
def compare_run(
    run_id: int,
    baseline_run_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunComparisonRead:
    current_run = get_accessible_run(db, current_user, run_id)
    if baseline_run_id is None:
        baseline_run = _find_previous_run(db, current_run)
    else:
        baseline_run = get_accessible_run(db, current_user, baseline_run_id)
        if baseline_run.test_id != current_run.test_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Можно сравнивать только запуски одного теста",
            )
    return build_run_comparison(current_run, baseline_run)


#Funkciya get_run_logs zakryvaet konkretnuyu zadachu v etom meste.
@router.get("/runs/{run_id}/logs", response_model=list[RunLogRead])
def get_run_logs(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RunLogRead]:
    run = get_accessible_run(db, current_user, run_id)
    return [serialize_run_log(log) for log in run.logs]


@router.get("/runs/{run_id}/logs/stream")
async def stream_run_logs(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    get_accessible_run_summary(db, current_user, run_id)

    async def event_generator():
        last_log_id = 0
        while True:
            db.expire_all()
            run = get_accessible_run_summary(db, current_user, run_id)
            logs = db.scalars(
                select(RunLog)
                .where(RunLog.run_id == run_id, RunLog.id > last_log_id)
                .order_by(RunLog.id.asc())
            ).all()
            if logs:
                last_log_id = logs[-1].id

            done = run.status not in {RunStatus.queued, RunStatus.running}
            yield encode_sse(
                "snapshot",
                {
                    "run": serialize_run(run).model_dump(mode="json"),
                    "logs": [
                        serialize_run_log(log).model_dump(mode="json")
                        for log in logs
                    ],
                    "done": done,
                },
            )
            if done:
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


#Tut ya vynes get_run_insights, chtoby ne razduvat ostalnoy kod.
@router.get("/runs/{run_id}/insights", response_model=RunInsightsRead)
def get_run_insights(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunInsightsRead:
    run = get_accessible_run(db, current_user, run_id)
    return serialize_run_insights(run, db)


#Zdes sobrana logika export_run, tak ee proshche podderzhivat.
@router.get("/runs/{run_id}/export")
def export_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    run = get_accessible_run(db, current_user, run_id)
    report = build_run_report_data(run, db)
    return JSONResponse(
        content=build_run_export_payload(report),
        headers={"Content-Disposition": f'attachment; filename="run-{run.id}.json"'},
    )


@router.get("/runs/{run_id}/report.html")
def export_run_report_html(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    run = get_accessible_run(db, current_user, run_id)
    report = build_run_report_data(run, db)
    return HTMLResponse(
        content=build_run_report_html(report),
        headers={"Content-Disposition": f'attachment; filename="run-{run.id}-report.html"'},
    )


@router.get("/runs/{run_id}/report.pdf")
def export_run_report_pdf(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    run = get_accessible_run(db, current_user, run_id)
    report = build_run_report_data(run, db)
    return Response(
        content=build_run_report_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="run-{run.id}-report.pdf"'},
    )
