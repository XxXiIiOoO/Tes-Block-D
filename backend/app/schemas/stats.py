from datetime import date, datetime

from pydantic import BaseModel

from app.models.run import RunStatus


class StatsDailyPoint(BaseModel):
    day: date
    total_runs: int
    successful_runs: int
    failed_runs: int


class StatsStatusBreakdown(BaseModel):
    status: RunStatus
    count: int


class StatsProjectPerformance(BaseModel):
    project_id: int
    project_name: str
    owner_username: str | None = None
    run_count: int
    successful_run_count: int
    failed_run_count: int
    success_rate: float


class StatsFailureReason(BaseModel):
    category: str
    count: int


class StatsTestInsight(BaseModel):
    test_id: int
    test_name: str
    project_name: str | None = None
    run_count: int
    success_rate: float
    average_duration_seconds: float


class StatsRecentFailure(BaseModel):
    run_id: int
    test_name: str | None = None
    project_name: str | None = None
    created_at: datetime
    result_summary: str | None = None
    failure_category: str | None = None


class StatsAlert(BaseModel):
    severity: str
    title: str
    detail: str


class StatsOverview(BaseModel):
    project_count: int
    test_count: int
    run_count: int
    successful_run_count: int
    failed_run_count: int
    queued_run_count: int
    running_run_count: int
    success_rate: float
    average_duration_seconds: float
    average_queue_time_seconds: float
    active_projects_last_7_days: int
    last_run_at: datetime | None
    daily_runs: list[StatsDailyPoint]
    runs_by_status: list[StatsStatusBreakdown]
    top_projects: list[StatsProjectPerformance]
    failure_reasons: list[StatsFailureReason]
    slowest_tests: list[StatsTestInsight]
    flaky_tests: list[StatsTestInsight]
    recent_failures: list[StatsRecentFailure]
    alerts: list[StatsAlert]
