import { Link } from "react-router-dom";

import { useAppPreferences } from "../preferences/AppPreferencesContext";
import type { RunStatus, StatsOverview } from "../types";
import { formatDate, formatDurationSeconds, formatShortDate, humanizeToken, localizeBackendText } from "../utils";

export function StatsCharts({ stats, isAdmin }: { stats: StatsOverview; isAdmin?: boolean }) {
  const { t } = useAppPreferences();

  const statusLabelMap: Record<RunStatus, string> = {
    queued: t("charts.statusQueued"),
    running: t("charts.statusRunning"),
    finished: t("charts.statusFinished"),
    failed: t("charts.statusFailed"),
    cancelled: t("charts.statusCancelled"),
  };

  function severityLabel(value: "info" | "warning" | "error") {
    return t(`severity.${value}`);
  }

  const maxDailyRuns = Math.max(...stats.daily_runs.map((point) => point.total_runs), 1);
  const totalRuns = Math.max(stats.run_count, 1);

  return (
    <div className="dashboard-analytics-grid">
      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("statsCharts.activityTrend")}</p>
            <h2>{t("analytics.hourly")}</h2>
          </div>
          <span className="counter-chip">{t("statsCharts.dailyChart")}</span>
        </div>

        <div className="activity-chart">
          {stats.daily_runs.map((point) => {
            const height = Math.max((point.total_runs / maxDailyRuns) * 100, point.total_runs ? 16 : 6);
            return (
              <div className="activity-chart-item" key={point.day}>
                <span className="activity-chart-value">{point.total_runs}</span>
                <div className="activity-chart-column">
                  <div
                    className="activity-chart-bar"
                    style={{ height: `${height}%` }}
                    title={`${point.total_runs} ${t("analytics.runsCount")}`}
                  />
                </div>
                <span className="activity-chart-label">{formatShortDate(point.day)}</span>
                <span className="activity-chart-meta">
                  {point.successful_runs}/{point.failed_runs}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("statsCharts.statusDistribution")}</p>
            <h2>{t("analytics.statusDonut")}</h2>
          </div>
          <span className="counter-chip">{t("statsCharts.autoUpdate")}</span>
        </div>

        <div className="status-chart-list">
          {stats.runs_by_status.map((entry) => {
            const width = entry.count ? Math.max((entry.count / totalRuns) * 100, 8) : 0;
            return (
              <div className="status-chart-item" key={entry.status}>
                <div className="list-card-top">
                  <span className={`badge badge-${entry.status}`}>{statusLabelMap[entry.status]}</span>
                  <strong>{entry.count}</strong>
                </div>
                <div className="status-chart-track">
                  <div
                    className={`status-chart-fill status-chart-fill-${entry.status}`}
                    style={{ width: `${width}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="section-card dashboard-projects-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("statsCharts.projectEfficiency")}</p>
            <h2>{t("analytics.topProjects")}</h2>
          </div>
          <span className="counter-chip">{t("statsCharts.top5")}</span>
        </div>

        {stats.top_projects.length === 0 ? (
          <p className="muted">{t("statsCharts.noProjectData")}</p>
        ) : (
          <div className="project-performance-list">
            {stats.top_projects.map((project) => (
              <article className="project-performance-item" key={project.project_id}>
                <div className="list-card-top">
                  <div>
                    <h3>{project.project_name}</h3>
                    <p className="muted">
                      {isAdmin
                        ? `${t("statsCharts.ownerLabel")}: ${project.owner_username ?? t("statsCharts.unknownUser")}`
                        : t("statsCharts.projectStats")}
                    </p>
                  </div>
                  <span className="counter-chip">{project.run_count} {t("analytics.runsCount")}</span>
                </div>
                <div className="meta-row">
                  <span>{t("statsCharts.successfulLabel")}: {project.successful_run_count}</span>
                  <span>{t("statsCharts.failedLabel")}: {project.failed_run_count}</span>
                  <span>{t("statsCharts.successRateLabel")}: {project.success_rate}%</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("statsCharts.alertsTitle")}</p>
            <h2>{t("analytics.failure.subtitle")}</h2>
          </div>
          <span className="counter-chip">{stats.alerts.length}</span>
        </div>

        <div className="signal-list">
          {stats.alerts.map((alert, index) => (
            <article className={`signal-card signal-card-${alert.severity}`} key={`${alert.title}-${index}`}>
              <div className="list-card-top">
                <strong>{localizeBackendText(alert.title)}</strong>
                <span className={`badge badge-log-${alert.severity}`}>{severityLabel(alert.severity)}</span>
              </div>
              <p className="muted">{localizeBackendText(alert.detail)}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("statsCharts.failurePatterns")}</p>
            <h2>{t("analytics.failure")}</h2>
          </div>
          <span className="counter-chip">{t("statsCharts.top5")}</span>
        </div>

        {stats.failure_reasons.length === 0 ? (
          <p className="muted">{t("statsCharts.noFailures")}</p>
        ) : (
          <div className="status-chart-list">
            {stats.failure_reasons.map((reason) => {
              const width = Math.max((reason.count / Math.max(stats.failed_run_count, 1)) * 100, 10);
              return (
                <div className="status-chart-item" key={reason.category}>
                  <div className="list-card-top">
                    <span className="code-chip">{humanizeToken(reason.category)}</span>
                    <strong>{reason.count}</strong>
                  </div>
                  <div className="status-chart-track">
                    <div className="status-chart-fill status-chart-fill-failed" style={{ width: `${width}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("statsCharts.performanceTitle")}</p>
            <h2>{t("analytics.latency")}</h2>
          </div>
          <span className="counter-chip">{t("statsCharts.top5")}</span>
        </div>

        {stats.slowest_tests.length === 0 ? (
          <p className="muted">{t("statsCharts.noPerformance")}</p>
        ) : (
          <div className="project-performance-list">
            {stats.slowest_tests.map((test) => (
              <article className="project-performance-item" key={test.test_id}>
                <div className="list-card-top">
                  <div>
                    <h3>{test.test_name}</h3>
                    <p className="muted">{test.project_name ?? t("statsCharts.unknownProject")}</p>
                  </div>
                  <span className="counter-chip">{formatDurationSeconds(test.average_duration_seconds)}</span>
                </div>
                <div className="meta-row">
                  <span>{t("statsCharts.runsLabel")}: {test.run_count}</span>
                  <span>{t("statsCharts.successRateLabel")}: {test.success_rate}%</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("statsCharts.stability")}</p>
            <h2>{t("statsCharts.flakyTests")}</h2>
          </div>
          <span className="counter-chip">{t("statsCharts.mixedResults")}</span>
        </div>

        {stats.flaky_tests.length === 0 ? (
          <p className="muted">{t("statsCharts.noFlaky")}</p>
        ) : (
          <div className="project-performance-list">
            {stats.flaky_tests.map((test) => (
              <article className="project-performance-item" key={test.test_id}>
                <div className="list-card-top">
                  <div>
                    <h3>{test.test_name}</h3>
                    <p className="muted">{test.project_name ?? t("statsCharts.unknownProject")}</p>
                  </div>
                  <span className="counter-chip">{test.success_rate}% {t("statsCharts.successPct")}</span>
                </div>
                <div className="meta-row">
                  <span>{t("statsCharts.runsLabel")}: {test.run_count}</span>
                  <span>{t("statsCharts.avgDuration")}: {formatDurationSeconds(test.average_duration_seconds)}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="section-card dashboard-projects-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("statsCharts.recentErrors")}</p>
            <h2>{t("statsCharts.recentFailedRuns")}</h2>
          </div>
          <span className="counter-chip">{t("statsCharts.last5")}</span>
        </div>

        {stats.recent_failures.length === 0 ? (
          <p className="muted">{t("statsCharts.noRecentErrors")}</p>
        ) : (
          <div className="list-grid">
            {stats.recent_failures.map((failure) => (
              <article className="list-card" key={failure.run_id}>
                <div className="list-card-top">
                  <div>
                    <p className="eyebrow">{t("dashboard.runLabel")} #{failure.run_id}</p>
                    <h3>{failure.test_name ?? t("statsCharts.unknownTest")}</h3>
                  </div>
                  <span className="code-chip">{humanizeToken(failure.failure_category)}</span>
                </div>
                <p className="muted">{failure.project_name ?? t("statsCharts.unknownProject")}</p>
                <p className="muted">{localizeBackendText(failure.result_summary) || t("statsCharts.noSummary")}</p>
                <div className="meta-row">
                  <span>{formatDate(failure.created_at)}</span>
                  <Link className="text-link" to={`/runs/${failure.run_id}`}>
                    {t("dashboard.openRunDetails")}
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
