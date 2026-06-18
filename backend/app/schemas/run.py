from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.models.run import RunStatus


class RunLogSource(str, Enum):
    stdout = "stdout"
    stderr = "stderr"
    system = "system"


class RunLogSeverity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"


class RunRead(BaseModel):
    id: int
    test_id: int
    status: RunStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None = None
    queue_time_seconds: float | None = None
    result_summary: str | None
    exit_code: int | None
    created_at: datetime
    test_name: str | None = None
    project_id: int | None = None
    project_name: str | None = None


class RunCreateResponse(RunRead):
    pass


class RunLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    message: str
    source: RunLogSource
    severity: RunLogSeverity
    created_at: datetime


class RunMetricsRead(BaseModel):
    duration_seconds: float | None
    queue_time_seconds: float | None
    total_logs: int
    stdout_lines: int
    stderr_lines: int
    system_lines: int
    info_count: int
    warning_count: int
    error_count: int


class RunSignalRead(BaseModel):
    severity: RunLogSeverity
    title: str
    detail: str


class RunQualityGateRead(BaseModel):
    enabled: bool
    passed: bool | None
    baseline_run_id: int | None
    baseline_delta_seconds: float | None
    reasons: list[str]


class RunInsightsRead(BaseModel):
    summary: str
    failure_category: str | None
    latest_error: str | None
    metrics: RunMetricsRead
    signals: list[RunSignalRead]
    recommendations: list[str]
    quality_gate: RunQualityGateRead | None = None


class RunComparisonMetricRead(BaseModel):
    key: str
    label: str
    current: float | int | str | None
    baseline: float | int | str | None
    delta: float | None = None
    delta_percent: float | None = None
    unit: str | None = None


class RunLogDiffRead(BaseModel):
    added: list[str]
    removed: list[str]
    added_count: int
    removed_count: int
    unchanged_count: int


class RunComparisonRead(BaseModel):
    current_run: RunRead
    baseline_run: RunRead | None
    metrics: list[RunComparisonMetricRead]
    status_changed: bool
    exit_code_changed: bool
    log_diff: RunLogDiffRead | None = None
