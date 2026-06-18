from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.api.routes.projects import project_access_filter
from app.db.session import get_db
from app.models.project import Project
from app.models.run import Run, RunStatus
from app.models.test import Test
from app.models.user import User
from app.services.observability import analyze_run, compute_queue_time_seconds
from app.schemas.stats import (
    StatsAlert,
    StatsDailyPoint,
    StatsFailureReason,
    StatsOverview,
    StatsProjectPerformance,
    StatsRecentFailure,
    StatsStatusBreakdown,
    StatsTestInsight,
)


router = APIRouter(prefix="/stats", tags=["stats"])


#Zdes sobrana logika overview, tak ee proshche podderzhivat.
@router.get("/overview", response_model=StatsOverview)
def overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StatsOverview:
    project_query = select(func.count(Project.id))
    test_query = select(func.count(Test.id)).join(Project, Test.project_id == Project.id)
    run_query = (
        select(func.count(Run.id))
        .join(Test, Run.test_id == Test.id)
        .join(Project, Test.project_id == Project.id)
    )
    successful_run_query = (
        select(func.count(Run.id))
        .join(Test, Run.test_id == Test.id)
        .join(Project, Test.project_id == Project.id)
        .where(Run.status == RunStatus.finished)
    )
    failed_run_query = (
        select(func.count(Run.id))
        .join(Test, Run.test_id == Test.id)
        .join(Project, Test.project_id == Project.id)
        .where(Run.status == RunStatus.failed)
    )

    if not current_user.is_admin:
        access_filter = project_access_filter(current_user)
        project_query = project_query.where(access_filter)
        test_query = test_query.where(access_filter)
        run_query = run_query.where(access_filter)
        successful_run_query = successful_run_query.where(access_filter)
        failed_run_query = failed_run_query.where(access_filter)

    project_count = db.scalar(project_query) or 0
    test_count = db.scalar(test_query) or 0
    run_count = db.scalar(run_query) or 0
    successful_run_count = db.scalar(successful_run_query) or 0
    failed_run_count = db.scalar(failed_run_query) or 0
    queued_run_count = db.scalar(
        run_query.where(Run.status == RunStatus.queued)
    ) or 0
    running_run_count = db.scalar(
        run_query.where(Run.status == RunStatus.running)
    ) or 0

    runs_scope_query = (
        select(Run)
        .options(
            joinedload(Run.logs),
            joinedload(Run.test).joinedload(Test.project).joinedload(Project.owner),
        )
        .join(Test, Run.test_id == Test.id)
        .join(Project, Test.project_id == Project.id)
        .order_by(Run.created_at.desc())
    )
    if not current_user.is_admin:
        runs_scope_query = runs_scope_query.where(project_access_filter(current_user))

    runs = db.execute(runs_scope_query).unique().scalars().all()

    success_rate = round((successful_run_count / run_count) * 100, 2) if run_count else 0.0
    last_run_at = runs[0].created_at if runs else None

    durations = [
        (run.finished_at - run.started_at).total_seconds()
        for run in runs
        if run.started_at is not None and run.finished_at is not None
    ]
    average_duration_seconds = round(sum(durations) / len(durations), 2) if durations else 0.0
    queue_times = [
        queue_time
        for run in runs
        if (queue_time := compute_queue_time_seconds(run)) is not None
    ]
    average_queue_time_seconds = (
        round(sum(queue_times) / len(queue_times), 2) if queue_times else 0.0
    )

    status_counts = {
        status: len([run for run in runs if run.status == status])
        for status in RunStatus
    }
    runs_by_status = [
        StatsStatusBreakdown(status=status, count=status_counts.get(status, 0))
        for status in RunStatus
    ]

    today = datetime.now(timezone.utc).date()
    daily_map = {
        today - timedelta(days=offset): {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
        }
        for offset in range(6, -1, -1)
    }
    for run in runs:
        run_day = run.created_at.astimezone(timezone.utc).date()
        if run_day in daily_map:
            daily_map[run_day]["total_runs"] += 1
            if run.status == RunStatus.finished:
                daily_map[run_day]["successful_runs"] += 1
            if run.status == RunStatus.failed:
                daily_map[run_day]["failed_runs"] += 1

    daily_runs = [
        StatsDailyPoint(day=day, **values)
        for day, values in daily_map.items()
    ]
    active_projects_last_7_days = len(
        {
            run.test.project.id
            for run in runs
            if run.test is not None
            and run.test.project is not None
            and run.created_at.astimezone(timezone.utc).date() in daily_map
        }
    )

    projects_map: dict[int, dict[str, object]] = defaultdict(
        lambda: {
            "project_name": "",
            "owner_username": None,
            "run_count": 0,
            "successful_run_count": 0,
            "failed_run_count": 0,
        }
    )
    for run in runs:
        if run.test is None or run.test.project is None:
            continue

        project = run.test.project
        project_stats = projects_map[project.id]
        project_stats["project_name"] = project.name
        project_stats["owner_username"] = project.owner_username
        project_stats["run_count"] = int(project_stats["run_count"]) + 1
        if run.status == RunStatus.finished:
            project_stats["successful_run_count"] = int(project_stats["successful_run_count"]) + 1
        if run.status == RunStatus.failed:
            project_stats["failed_run_count"] = int(project_stats["failed_run_count"]) + 1

    top_projects = []
    for project_id, metrics in projects_map.items():
        project_run_count = int(metrics["run_count"])
        successful_project_runs = int(metrics["successful_run_count"])
        failed_project_runs = int(metrics["failed_run_count"])
        project_success_rate = (
            round((successful_project_runs / project_run_count) * 100, 2)
            if project_run_count
            else 0.0
        )
        top_projects.append(
            StatsProjectPerformance(
                project_id=project_id,
                project_name=str(metrics["project_name"]),
                owner_username=metrics["owner_username"],
                run_count=project_run_count,
                successful_run_count=successful_project_runs,
                failed_run_count=failed_project_runs,
                success_rate=project_success_rate,
            )
        )

    top_projects.sort(key=lambda item: (-item.run_count, item.project_name.lower()))
    top_projects = top_projects[:5]

    test_metrics_map: dict[int, dict[str, object]] = defaultdict(
        lambda: {
            "test_name": "",
            "project_name": None,
            "run_count": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "durations": [],
        }
    )
    failure_counter: Counter[str] = Counter()
    recent_failures: list[StatsRecentFailure] = []
    for run in runs:
        if run.test is not None:
            test_metrics = test_metrics_map[run.test_id]
            test_metrics["test_name"] = run.test.name
            test_metrics["project_name"] = run.test.project.name if run.test.project else None
            test_metrics["run_count"] = int(test_metrics["run_count"]) + 1
            if run.status == RunStatus.finished:
                test_metrics["successful_runs"] = int(test_metrics["successful_runs"]) + 1
            if run.status == RunStatus.failed:
                test_metrics["failed_runs"] = int(test_metrics["failed_runs"]) + 1
            if run.started_at is not None and run.finished_at is not None:
                durations_list = list(test_metrics["durations"])
                durations_list.append((run.finished_at - run.started_at).total_seconds())
                test_metrics["durations"] = durations_list

        analysis = analyze_run(run)
        if run.status == RunStatus.failed:
            failure_counter[analysis.failure_category or "unknown"] += 1
            recent_failures.append(
                StatsRecentFailure(
                    run_id=run.id,
                    test_name=run.test.name if run.test else None,
                    project_name=run.test.project.name if run.test and run.test.project else None,
                    created_at=run.created_at,
                    result_summary=run.result_summary,
                    failure_category=analysis.failure_category,
                )
            )

    failure_reasons = [
        StatsFailureReason(category=category, count=count)
        for category, count in failure_counter.most_common(5)
    ]

    test_insights: list[StatsTestInsight] = []
    flaky_tests: list[StatsTestInsight] = []
    for test_id, metrics in test_metrics_map.items():
        run_count_for_test = int(metrics["run_count"])
        successful_runs_for_test = int(metrics["successful_runs"])
        failed_runs_for_test = int(metrics["failed_runs"])
        durations_for_test = list(metrics["durations"])
        average_test_duration = (
            round(sum(durations_for_test) / len(durations_for_test), 2)
            if durations_for_test
            else 0.0
        )
        success_rate_for_test = (
            round((successful_runs_for_test / run_count_for_test) * 100, 2)
            if run_count_for_test
            else 0.0
        )
        insight = StatsTestInsight(
            test_id=test_id,
            test_name=str(metrics["test_name"]),
            project_name=metrics["project_name"],
            run_count=run_count_for_test,
            success_rate=success_rate_for_test,
            average_duration_seconds=average_test_duration,
        )
        test_insights.append(insight)
        if successful_runs_for_test > 0 and failed_runs_for_test > 0:
            flaky_tests.append(insight)

    slowest_tests = sorted(
        [insight for insight in test_insights if insight.average_duration_seconds > 0],
        key=lambda item: (-item.average_duration_seconds, item.test_name.lower()),
    )[:5]
    flaky_tests = sorted(
        flaky_tests,
        key=lambda item: (item.success_rate, -item.run_count, item.test_name.lower()),
    )[:5]
    recent_failures = recent_failures[:5]

    alerts: list[StatsAlert] = []
    if run_count == 0:
        alerts.append(
            StatsAlert(
                severity="info",
                title="Пока нет запусков",
                detail="Запустите пресет или тест проекта, чтобы начать собирать диагностическую историю.",
            )
        )
    else:
        if success_rate < 70:
            alerts.append(
                StatsAlert(
                    severity="error" if success_rate < 50 else "warning",
                    title="Повышенный уровень ошибок",
                    detail=f"Текущая успешность составляет {success_rate}%, поэтому последние запуски требуют внимания.",
                )
            )
        if average_queue_time_seconds > 10:
            alerts.append(
                StatsAlert(
                    severity="warning",
                    title="Задержка в очереди воркера",
                    detail=(
                        f"Среднее ожидание в очереди — {average_queue_time_seconds}с, это может указывать на перегрузку воркеров."
                    ),
                )
            )
        if failure_counter.get("timeout", 0) > 0:
            alerts.append(
                StatsAlert(
                    severity="warning",
                    title="Обнаружены тайм-ауты",
                    detail="Как минимум один недавний запуск превысил заданный лимит времени.",
                )
            )
        if not alerts:
            alerts.append(
                StatsAlert(
                    severity="info",
                    title="Система работает стабильно",
                    detail="Недавние запуски завершаются без критичных системных предупреждений.",
                )
            )

    return StatsOverview(
        project_count=project_count,
        test_count=test_count,
        run_count=run_count,
        successful_run_count=successful_run_count,
        failed_run_count=failed_run_count,
        queued_run_count=queued_run_count,
        running_run_count=running_run_count,
        success_rate=success_rate,
        average_duration_seconds=average_duration_seconds,
        average_queue_time_seconds=average_queue_time_seconds,
        active_projects_last_7_days=active_projects_last_7_days,
        last_run_at=last_run_at,
        daily_runs=daily_runs,
        runs_by_status=runs_by_status,
        top_projects=top_projects,
        failure_reasons=failure_reasons,
        slowest_tests=slowest_tests,
        flaky_tests=flaky_tests,
        recent_failures=recent_failures,
        alerts=alerts,
    )
