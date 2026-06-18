import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  cancelRun,
  downloadRunExport,
  type RunExportFormat,
  getRun,
  getRunComparison,
  getRunInsights,
  getRunLogs,
  getTestRuns,
  rerunRun,
  streamRunLogs,
} from "../api/blocktest";
import { PageState } from "../components/PageState";
import { StatusBadge } from "../components/StatusBadge";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import type { Run, RunComparison, RunComparisonMetric, RunInsights, RunLog } from "../types";
import { formatDate, formatDurationSeconds, humanizeToken, localizeBackendText, toErrorMessage } from "../utils";

function severityLabel(severity: "info" | "warning" | "error", t: (key: string) => string) {
  return t(`severity.${severity}`);
}

function sourceLabel(source: "stdout" | "stderr" | "system", t: (key: string) => string) {
  return t(`logSource.${source}`);
}

function formatComparisonValue(metric: RunComparisonMetric, value: number | string | null) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (typeof value === "number") {
    const formatted = Number.isInteger(value) ? String(value) : value.toFixed(2);
    return metric.unit ? `${formatted}${metric.unit}` : formatted;
  }
  return value;
}

export function RunDetailsPage() {
  const { autoRefreshMs, refreshOnFocus, t } = useAppPreferences();
  const params = useParams();
  const navigate = useNavigate();
  const runId = Number(params.runId);
  const [run, setRun] = useState<Run | null>(null);
  const [insights, setInsights] = useState<RunInsights | null>(null);
  const [comparison, setComparison] = useState<RunComparison | null>(null);
  const [compareRuns, setCompareRuns] = useState<Run[]>([]);
  const [selectedBaselineRunId, setSelectedBaselineRunId] = useState<number | undefined>();
  const [logs, setLogs] = useState<RunLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isLiveRun = Boolean(run && ["queued", "running"].includes(run.status));

  async function loadData(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    setError(null);

    try {
      const [runResponse, logsResponse, insightsResponse] = await Promise.all([
        getRun(runId),
        getRunLogs(runId),
        getRunInsights(runId),
      ]);
      setRun(runResponse);
      setLogs(logsResponse);
      setInsights(insightsResponse);
      const [comparisonResponse, candidateRuns] = await Promise.all([
        getRunComparison(runId, selectedBaselineRunId).catch(() => null),
        getTestRuns(runResponse.test_id, { sortBy: "created_at", order: "desc" }).catch(() => []),
      ]);
      setComparison(comparisonResponse);
      setCompareRuns(candidateRuns.filter((candidate) => candidate.id !== runId));
    } catch (loadError) {
      setError(toErrorMessage(loadError, t("runDetails.loadError")));
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    if (!Number.isFinite(runId)) {
      setError(t("runDetails.invalidId"));
      setLoading(false);
      return;
    }

    void loadData();
  }, [runId]);

  useAutoRefresh(() => loadData(true), {
    enabled: Boolean(run) && !isLiveRun,
    intervalMs: autoRefreshMs,
    refreshOnFocus,
  });

  useEffect(() => {
    if (!isLiveRun) {
      return;
    }

    const controller = new AbortController();
    setStreaming(true);

    streamRunLogs(runId, {
      signal: controller.signal,
      onSnapshot: (snapshot) => {
        setRun(snapshot.run);
        if (snapshot.logs.length) {
          setLogs((currentLogs) => {
            const knownLogIds = new Set(currentLogs.map((log) => log.id));
            return [
              ...currentLogs,
              ...snapshot.logs.filter((log) => !knownLogIds.has(log.id)),
            ].sort((left, right) => left.id - right.id);
          });
        }
        if (snapshot.done) {
          void loadData(true);
        }
      },
    })
      .catch((streamError) => {
        if (!controller.signal.aborted) {
          setError(toErrorMessage(streamError, t("runDetails.streamInterrupted")));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setStreaming(false);
        }
      });

    return () => {
      controller.abort();
      setStreaming(false);
    };
  }, [isLiveRun, runId]);

  async function handleRerun() {
    setBusy(true);
    setError(null);

    try {
      const newRun = await rerunRun(runId);
      navigate(`/runs/${newRun.id}`);
    } catch (rerunError) {
      setError(toErrorMessage(rerunError, t("runDetails.rerunError")));
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(format: RunExportFormat) {
    setBusy(true);
    setError(null);

    try {
      await downloadRunExport(runId, format);
    } catch (exportError) {
      setError(toErrorMessage(exportError, t("runDetails.exportError")));
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    setBusy(true);
    setError(null);

    try {
      const cancelledRun = await cancelRun(runId);
      setRun(cancelledRun);
      await loadData(true);
    } catch (cancelError) {
      setError(toErrorMessage(cancelError, t("runDetails.cancelError")));
    } finally {
      setBusy(false);
    }
  }

  async function handleBaselineChange(value: string) {
    const baselineRunId = value ? Number(value) : undefined;
    setSelectedBaselineRunId(baselineRunId);
    setError(null);
    try {
      const comparisonResponse = await getRunComparison(runId, baselineRunId);
      setComparison(comparisonResponse);
    } catch (compareError) {
      setComparison(null);
      setError(toErrorMessage(compareError, t("runDetails.compareError")));
    }
  }

  const state =
    loading || (!run && error) ? (
      <PageState
        loading={loading}
        error={!run ? error : null}
        emptyMessage={t("runDetails.notFound")}
        hasData={Boolean(run)}
      />
    ) : null;

  if (state) {
    return state;
  }

  const metricSummary = insights?.metrics;
  const heroSummary = localizeBackendText(insights?.summary ?? run?.result_summary) || t("runDetails.workerProcessing");

  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">{t("runDetails.eyebrow")}</p>
          <h1>{t("common.runWithId", { id: run?.id ?? "?" })}</h1>
          <p className="muted">{heroSummary}</p>
        </div>

        <div className="pill-row">
          {run ? <StatusBadge status={run.status} /> : null}
          <span className="counter-chip">
            {streaming ? t("runDetails.liveLogs") : t("runDetails.realtimeState")}
          </span>
          {insights?.failure_category ? (
            <span className="code-chip">{humanizeToken(insights.failure_category)}</span>
          ) : null}
          <button className="button button-primary" disabled={busy} onClick={handleRerun} type="button">
            {busy ? t("runDetails.processing") : t("runDetails.rerun")}
          </button>
          {isLiveRun ? (
            <button className="button button-danger" disabled={busy} onClick={handleCancel} type="button">
              {t("runDetails.cancel")}
            </button>
          ) : null}
          <button className="button button-ghost" disabled={busy} onClick={() => handleExport("json")} type="button">
            {t("runDetails.exportJson")}
          </button>
          <button className="button button-ghost" disabled={busy} onClick={() => handleExport("html")} type="button">
            {t("runDetails.exportHtml")}
          </button>
          <button className="button button-ghost" disabled={busy} onClick={() => handleExport("pdf")} type="button">
            {t("runDetails.exportPdf")}
          </button>
        </div>
      </section>

      {error ? <div className="state-card state-card-error">{error}</div> : null}

      <section className="grid-two">
        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("runDetails.metadata")}</p>
              <h2>{t("runDetails.summary")}</h2>
            </div>
          </div>
          <div className="details-grid">
            <div>
              <span className="details-label">{t("runDetails.project")}</span>
              {run?.project_id ? (
                <Link className="text-link" to={`/projects/${run.project_id}`}>
                  {run.project_name}
                </Link>
              ) : (
                <p>{run?.project_name ?? t("common.unavailable")}</p>
              )}
            </div>
            <div>
              <span className="details-label">{t("runDetails.test")}</span>
              {run?.test_id ? (
                <Link className="text-link" to={`/tests/${run.test_id}`}>
                  {run.test_name}
                </Link>
              ) : (
                <p>{run?.test_name ?? t("common.unavailable")}</p>
              )}
            </div>
            <div>
              <span className="details-label">{t("common.created")}</span>
              <p>{formatDate(run?.created_at)}</p>
            </div>
            <div>
              <span className="details-label">{t("runDetails.started")}</span>
              <p>{formatDate(run?.started_at)}</p>
            </div>
            <div>
              <span className="details-label">{t("runDetails.finished")}</span>
              <p>{formatDate(run?.finished_at)}</p>
            </div>
            <div>
              <span className="details-label">{t("runDetails.duration")}</span>
              <p>{formatDurationSeconds(run?.duration_seconds)}</p>
            </div>
            <div>
              <span className="details-label">{t("runDetails.queueWait")}</span>
              <p>{formatDurationSeconds(run?.queue_time_seconds)}</p>
            </div>
            <div>
              <span className="details-label">{t("runDetails.exitCode")}</span>
              <p>{run?.exit_code ?? t("common.pending")}</p>
            </div>
            <div>
              <span className="details-label">{t("runDetails.failureCategory")}</span>
              <p>{humanizeToken(insights?.failure_category)}</p>
            </div>
          </div>
        </article>

        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("runDetails.observability")}</p>
              <h2>{t("runDetails.signalsTitle")}</h2>
            </div>
            <span className="counter-chip">{t("runDetails.signalsCount", { count: insights?.signals.length ?? 0 })}</span>
          </div>

          {!insights ? (
            <PageState emptyMessage={t("runDetails.diagnosticsEmpty")} hasData={false} />
          ) : (
            <div className="stack">
              <div className="stats-grid compact-stats-grid">
                <article className="stat-card">
                  <span>{t("runDetails.totalLogs")}</span>
                  <strong>{metricSummary?.total_logs ?? 0}</strong>
                </article>
                <article className="stat-card">
                  <span>{t("runDetails.stdoutLines")}</span>
                  <strong>{metricSummary?.stdout_lines ?? 0}</strong>
                </article>
                <article className="stat-card">
                  <span>{t("runDetails.stderrLines")}</span>
                  <strong>{metricSummary?.stderr_lines ?? 0}</strong>
                </article>
                <article className="stat-card">
                  <span>{t("runDetails.warnings")}</span>
                  <strong>{metricSummary?.warning_count ?? 0}</strong>
                </article>
                <article className="stat-card">
                  <span>{t("runDetails.errors")}</span>
                  <strong>{metricSummary?.error_count ?? 0}</strong>
                </article>
              </div>

              {insights.latest_error ? (
                <div className="state-card state-card-error">
                  <strong>{t("runDetails.latestError")}</strong>
                  <p>{insights.latest_error}</p>
                </div>
              ) : null}

              <div className="signal-list">
                {insights.signals.map((signal, index) => (
                  <article className={`signal-card signal-card-${signal.severity}`} key={`${signal.title}-${index}`}>
                    <div className="list-card-top">
                      <strong>{localizeBackendText(signal.title)}</strong>
                      <span className={`badge badge-log-${signal.severity}`}>{severityLabel(signal.severity, t)}</span>
                    </div>
                    <p className="muted">{localizeBackendText(signal.detail)}</p>
                  </article>
                ))}
              </div>

              <div className="stack">
                <div>
                  <p className="eyebrow">{t("runDetails.recommendedSteps")}</p>
                  <h3>{t("runDetails.nextSteps")}</h3>
                </div>
                <div className="recommendation-list">
                  {insights.recommendations.map((recommendation, index) => (
                    <article className="recommendation-card" key={`${recommendation}-${index}`}>
                      {localizeBackendText(recommendation)}
                    </article>
                  ))}
                </div>
              </div>
            </div>
          )}
        </article>
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("runDetails.compareEyebrow")}</p>
            <h2>{t("runDetails.compareTitle")}</h2>
          </div>
          <label className="field compact-field">
            <span>{t("runDetails.compareBaseline")}</span>
            <select
              value={selectedBaselineRunId ?? ""}
              onChange={(event) => handleBaselineChange(event.target.value)}
            >
              <option value="">{t("runDetails.comparePrevious")}</option>
              {compareRuns.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  #{candidate.id} · {formatDate(candidate.created_at)} · {candidate.status}
                </option>
              ))}
            </select>
          </label>
        </div>

        {!comparison?.baseline_run ? (
          <PageState emptyMessage={t("runDetails.compareEmpty")} hasData={false} />
        ) : (
          <div className="stack">
            <div className="stats-grid compact-stats-grid">
              {comparison.metrics.map((metric) => (
                <article className="stat-card" key={metric.key}>
                  <span>{metric.label}</span>
                  <strong>{formatComparisonValue(metric, metric.current)}</strong>
                  <small>
                    {t("runDetails.compareBaselineShort")}: {formatComparisonValue(metric, metric.baseline)}
                  </small>
                  {metric.delta !== null ? (
                    <small>
                      {metric.delta > 0 ? "+" : ""}{metric.delta}
                      {metric.unit ?? ""}
                      {metric.delta_percent !== null ? ` (${metric.delta_percent > 0 ? "+" : ""}${metric.delta_percent}%)` : ""}
                    </small>
                  ) : null}
                </article>
              ))}
            </div>

            <div className="pill-row">
              <span className={comparison.status_changed ? "badge badge-log-warning" : "badge badge-log-info"}>
                {comparison.status_changed ? t("runDetails.compareStatusChanged") : t("runDetails.compareStatusSame")}
              </span>
              <span className={comparison.exit_code_changed ? "badge badge-log-warning" : "badge badge-log-info"}>
                {comparison.exit_code_changed ? t("runDetails.compareExitChanged") : t("runDetails.compareExitSame")}
              </span>
              {comparison.baseline_run ? (
                <Link className="text-link" to={`/runs/${comparison.baseline_run.id}`}>
                  {t("runDetails.compareOpenBaseline", { id: comparison.baseline_run.id })}
                </Link>
              ) : null}
            </div>

            {comparison.log_diff ? (
              <div className="grid-two">
                <article className="state-card">
                  <strong>{t("runDetails.compareAddedLogs", { count: comparison.log_diff.added_count })}</strong>
                  {comparison.log_diff.added.length ? (
                    <div className="log-console compact-log-console">
                      {comparison.log_diff.added.map((line, index) => (
                        <code key={`${line}-${index}`}>{line}</code>
                      ))}
                    </div>
                  ) : null}
                </article>
                <article className="state-card">
                  <strong>{t("runDetails.compareRemovedLogs", { count: comparison.log_diff.removed_count })}</strong>
                  {comparison.log_diff.removed.length ? (
                    <div className="log-console compact-log-console">
                      {comparison.log_diff.removed.map((line, index) => (
                        <code key={`${line}-${index}`}>{line}</code>
                      ))}
                    </div>
                  ) : null}
                </article>
              </div>
            ) : null}
          </div>
        )}
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("runDetails.logs")}</p>
            <h2>{t("runDetails.savedOutput")}</h2>
          </div>
          <div className="pill-row">
            <span className="counter-chip">{t("runDetails.rows", { count: logs.length })}</span>
            <span className="code-chip">{t("runDetails.output")} {metricSummary?.stdout_lines ?? 0}</span>
            <span className="code-chip">{t("runDetails.errorOutput")} {metricSummary?.stderr_lines ?? 0}</span>
          </div>
        </div>

        {logs.length === 0 ? (
          <PageState emptyMessage={t("runDetails.logsEmpty")} hasData={false} />
        ) : (
          <div className="log-console">
            {logs.map((log) => (
              <div className={`log-line log-line-${log.source} log-line-${log.severity}`} key={log.id}>
                <div className="log-line-meta">
                  <span>{formatDate(log.created_at)}</span>
                  <span className={`badge badge-log-${log.severity}`}>{sourceLabel(log.source, t)}</span>
                </div>
                <code>{log.message.replace(/^\[(stdout|stderr|system)\] /, "")}</code>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
