from datetime import datetime

from pydantic import BaseModel, Field

from app.models.run import RunStatus


class TestAutomationRead(BaseModel):
    test_id: int
    baseline_run_id: int | None
    gate_enabled: bool
    gate_max_duration_seconds: float | None
    gate_max_error_logs: int | None
    schedule_enabled: bool
    schedule_interval_minutes: int | None
    schedule_next_run_at: datetime | None
    webhook_enabled: bool
    webhook_token_configured: bool


class TestAutomationUpdate(BaseModel):
    baseline_run_id: int | None = Field(default=None, ge=1)
    gate_enabled: bool | None = None
    gate_max_duration_seconds: float | None = Field(default=None, ge=0)
    gate_max_error_logs: int | None = Field(default=None, ge=0)
    schedule_enabled: bool | None = None
    schedule_interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    webhook_enabled: bool | None = None


class WebhookTokenRotateResponse(BaseModel):
    token: str


class AutomationRunTriggerResponse(BaseModel):
    run_id: int
    status: RunStatus
    created_at: datetime


class ScheduleTickResponse(BaseModel):
    processed_tests: int
    enqueued_runs: int
    failed_to_enqueue: int
    skipped_tests: int
    enqueued_run_ids: list[int]
