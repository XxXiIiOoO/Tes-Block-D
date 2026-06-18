import { useEffect, useMemo, useState } from "react";

import { getRuns, getStatsOverview } from "../api/blocktest";
import {
  DailyTrendChart,
  FailureBarChart,
  HourlyBarChart,
  LatencyBarChart,
  StatusDonutChart,
  SuccessRateTrendChart,
} from "../components/AnalyticsCharts";
import { PageState } from "../components/PageState";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import {
  type AnalyticsSessionScope,
  type AnalyticsWidget,
  useAppPreferences,
} from "../preferences/AppPreferencesContext";
import type { Run, RunStatus, StatsOverview } from "../types";
import { formatDurationSeconds, humanizeToken, toErrorMessage } from "../utils";

type AnalyticsPeriod = "7d" | "30d" | "all";
type StatusFilter = "all" | RunStatus;

const sessionScopes: AnalyticsSessionScope[] = ["latest_50", "latest_200", "latest_500", "all"];

const sessionScopeLimits: Record<AnalyticsSessionScope, number | null> = {
  latest_50: 50,
  latest_200: 200,
  latest_500: 500,
  all: null,
};

const widgetOrder: AnalyticsWidget[] = [
  "hourly",
  "statusMix",
  "failureReasons",
  "latency",
  "topTests",
];

const widgetLabels: Record<AnalyticsWidget, string> = {
  hourly: "analytics.hourly",
  statusMix: "analytics.statusDonut",
  failureReasons: "analytics.failure",
  latency: "analytics.latency",
  topTests: "analytics.topProjects",
};

function getPeriodThreshold(period: AnalyticsPeriod): number | null {
  if (period === "all") {
    return null;
  }
  const days = period === "7d" ? 7 : 30;
  return Date.now() - days * 24 * 60 * 60 * 1000;
}

function getFailureCategory(summary: string | null): string {
  if (!summary) {
    return "unknown";
  }
  const firstLine = summary.split("\n")[0]?.trim() ?? "";
  if (!firstLine) {
    return "unknown";
  }
  const shortValue = firstLine.split(":")[0]?.trim() ?? firstLine;
  return shortValue.toLowerCase();
}

export function AnalyticsPage() {
  const {
    t,
    autoRefreshMs,
    refreshOnFocus,
    analyticsSessionScope,
    analyticsWidgets,
    setAnalyticsSessionScope,
    setAnalyticsWidgetVisible,
  } = useAppPreferences();

  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [period, setPeriod] = useState<AnalyticsPeriod>("30d");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    setError(null);

    try {
      const [statsResponse, runsResponse] = await Promise.all([
        getStatsOverview(),
        getRuns({ sortBy: "created_at", order: "desc" }),
      ]);
      setStats(statsResponse);
      setRuns(runsResponse);
    } catch (loadError) {
      if (!silent || !stats) {
        setError(toErrorMessage(loadError, t("analytics.noData")));
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  useAutoRefresh(() => loadData(true), {
    intervalMs: autoRefreshMs,
    refreshOnFocus,
  });

  const sessionScopeLabels = useMemo<Record<AnalyticsSessionScope, string>>(
    () => ({
      latest_50: t("analytics.sessions.50"),
      latest_200: t("analytics.sessions.200"),
      latest_500: t("analytics.sessions.500"),
      all: t("analytics.sessions.all"),
    }),
    [t],
  );

  const periodFilteredRuns = useMemo(() => {
    const threshold = getPeriodThreshold(period);
    return runs.filter((run) => {
      if (threshold && new Date(run.created_at).getTime() < threshold) {
        return false;
      }
      if (statusFilter !== "all" && run.status !== statusFilter) {
        return false;
      }
      return true;
    });
  }, [period, runs, statusFilter]);

  const filteredRuns = useMemo(() => {
    const limit = sessionScopeLimits[analyticsSessionScope];
    if (!limit) {
      return periodFilteredRuns;
    }
    return periodFilteredRuns.slice(0, limit);
  }, [analyticsSessionScope, periodFilteredRuns]);

  const hourlyBuckets = useMemo(() => {
    const buckets = Array.from({ length: 24 }, () => 0);
    filteredRuns.forEach((run) => {
      const hour = new Date(run.created_at).getHours();
      buckets[hour] += 1;
    });
    return buckets;
  }, [filteredRuns]);

  const statusCounts = useMemo(() => {
    const counts: Record<RunStatus, number> = {
      queued: 0,
      running: 0,
      finished: 0,
      failed: 0,
      cancelled: 0,
    };
    filteredRuns.forEach((run) => {
      counts[run.status] += 1;
    });
    return counts;
  }, [filteredRuns]);

  const failureReasons = useMemo(() => {
    const map = new Map<string, number>();
    filteredRuns
      .filter((run) => run.status === "failed")
      .forEach((run) => {
        const category = getFailureCategory(run.result_summary);
        map.set(category, (map.get(category) ?? 0) + 1);
      });

    return [...map.entries()]
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count || a.category.localeCompare(b.category))
      .slice(0, 8);
  }, [filteredRuns]);

  const performanceByStatus = useMemo(() => {
    const buckets: Record<RunStatus, number[]> = {
      queued: [],
      running: [],
      finished: [],
      failed: [],
      cancelled: [],
    };
    filteredRuns.forEach((run) => {
      if (run.duration_seconds != null && run.duration_seconds > 0) {
        buckets[run.status].push(run.duration_seconds);
      }
    });
    return (Object.keys(buckets) as RunStatus[]).map((status) => {
      const values = buckets[status];
      const average = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
      return { status, average, count: values.length };
    });
  }, [filteredRuns]);

  const averageQueueTimeSeconds = useMemo(() => {
    const values = filteredRuns
      .map((run) => run.queue_time_seconds)
      .filter((value): value is number => typeof value === "number" && value >= 0);
    if (values.length === 0) {
      return stats?.average_queue_time_seconds ?? 0;
    }
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }, [filteredRuns, stats]);

  const topTests = useMemo(() => {
    const map = new Map<string, number>();
    filteredRuns.forEach((run) => {
      const name = run.test_name ?? t("dashboard.untitledTest");
      map.set(name, (map.get(name) ?? 0) + 1);
    });
    return [...map.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
      .slice(0, 8);
  }, [filteredRuns, t]);

  const visibleWidgets = useMemo(
    () => widgetOrder.filter((widget) => analyticsWidgets[widget]),
    [analyticsWidgets],
  );

  const statusToLabel = (status: RunStatus): string => {
    const map: Record<RunStatus, string> = {
      queued: t("charts.statusQueued"),
      running: t("charts.statusRunning"),
      finished: t("charts.statusFinished"),
      failed: t("charts.statusFailed"),
      cancelled: t("charts.statusCancelled"),
    };
    return map[status];
  };

  const state =
    loading || (!stats && error) ? (
      <PageState
        loading={loading}
        error={!stats ? error : null}
        emptyMessage={t("analytics.noData")}
        hasData={Boolean(stats)}
      />
    ) : null;

  if (state) {
    return state;
  }

  return (
    <div className="page-stack">
      <section className="hero-card hero-card-compact">
        <div>
          <p className="eyebrow">{t("nav.analytics")}</p>
          <h1>{t("analytics.title")}</h1>
          <p className="muted">{t("analytics.subtitle")}</p>
        </div>
        <div className="toolbar analytics-toolbar">
          <label className="field field-inline">
            <span>{t("analytics.period")}</span>
            <select value={period} onChange={(event) => setPeriod(event.target.value as AnalyticsPeriod)}>
              <option value="7d">{t("analytics.period.7")}</option>
              <option value="30d">{t("analytics.period.30")}</option>
              <option value="all">{t("analytics.period.all")}</option>
            </select>
          </label>
          <label className="field field-inline">
            <span>{t("analytics.status")}</span>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            >
              <option value="all">{t("analytics.status.all")}</option>
              <option value="queued">{t("analytics.status.queued")}</option>
              <option value="running">{t("analytics.status.running")}</option>
              <option value="finished">{t("analytics.status.finished")}</option>
              <option value="failed">{t("analytics.status.failed")}</option>
              <option value="cancelled">{t("analytics.status.cancelled")}</option>
            </select>
          </label>
          <label className="field field-inline">
            <span>{t("analytics.sessions")}</span>
            <select
              value={analyticsSessionScope}
              onChange={(event) => setAnalyticsSessionScope(event.target.value as AnalyticsSessionScope)}
            >
              {sessionScopes.map((scope) => (
                <option key={scope} value={scope}>
                  {sessionScopeLabels[scope]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="metrics-toggle-grid">
          {widgetOrder.map((widget) => (
            <label className="toggle-row" key={widget}>
              <input
                checked={analyticsWidgets[widget]}
                onChange={(event) => setAnalyticsWidgetVisible(widget, event.target.checked)}
                type="checkbox"
              />
              <span>{t(widgetLabels[widget])}</span>
            </label>
          ))}
        </div>
      </section>

      {error ? <div className="state-card state-card-error">{error}</div> : null}

      {visibleWidgets.length === 0 ? (
        <article className="section-card">
          <p className="muted">
            {t("analytics.enableWidget")}
          </p>
        </article>
      ) : (
        <section className="dashboard-analytics-grid analytics-grid-advanced">
          {analyticsWidgets.hourly ? (
            <article className="section-card">
              <div className="card-header">
                <div>
                  <p className="eyebrow">{t("analytics.hourly")}</p>
                  <h2>{t("analytics.hourly.subtitle")}</h2>
                </div>
                <span className="counter-chip">{filteredRuns.length} {t("analytics.runsCount")}</span>
              </div>
              <HourlyBarChart buckets={hourlyBuckets} />
            </article>
          ) : null}

          {analyticsWidgets.statusMix ? (
            <article className="section-card">
              <div className="card-header">
                <div>
                  <p className="eyebrow">{t("analytics.statusDonut")}</p>
                  <h2>{t("analytics.statusDonut.subtitle")}</h2>
                </div>
                <span className="counter-chip">{filteredRuns.length}</span>
              </div>
              <StatusDonutChart data={statusCounts} total={filteredRuns.length} />
            </article>
          ) : null}

          {analyticsWidgets.failureReasons ? (
            <article className="section-card">
              <div className="card-header">
                <div>
                  <p className="eyebrow">{t("analytics.failure")}</p>
                  <h2>{t("analytics.failure.subtitle")}</h2>
                </div>
                <span className="counter-chip">{failureReasons.length}</span>
              </div>
              {failureReasons.length === 0 ? (
                <p className="muted">{t("analytics.noFailures")}</p>
              ) : (
                <FailureBarChart data={failureReasons} />
              )}
            </article>
          ) : null}

          {analyticsWidgets.latency ? (
            <article className="section-card">
              <div className="card-header">
                <div>
                  <p className="eyebrow">{t("analytics.latency")}</p>
                  <h2>{t("analytics.latency.subtitle")}</h2>
                </div>
              </div>
              <LatencyBarChart
                data={[
                  ...performanceByStatus
                    .filter((r) => r.count > 0)
                    .map((r) => ({
                      label: statusToLabel(r.status),
                      value: r.average,
                      status: r.status,
                    })),
                  {
                    label: t("analytics.queueLabel"),
                    value: averageQueueTimeSeconds,
                    status: "running" as RunStatus,
                  },
                ]}
              />
            </article>
          ) : null}

          {analyticsWidgets.topTests ? (
            <article className="section-card dashboard-projects-card">
              <div className="card-header">
                <div>
                  <p className="eyebrow">{t("analytics.topProjects")}</p>
                  <h2>{t("analytics.topProjects.subtitle")}</h2>
                </div>
                <span className="counter-chip">{topTests.length}</span>
              </div>
              {topTests.length === 0 ? (
                <p className="muted">{t("analytics.noTests")}</p>
              ) : (
                <div className="top-tests-grid">
                  {topTests.map((test) => (
                    <article className="project-performance-item" key={test.name}>
                      <div className="list-card-top">
                        <h3>{test.name}</h3>
                        <span className="counter-chip">{test.count}</span>
                      </div>
                      <p className="muted">{t("analytics.testRunsLabel")}</p>
                    </article>
                  ))}
                </div>
              )}
            </article>
          ) : null}

          {/* Success rate trend */}
          {stats?.daily_runs && stats.daily_runs.length > 1 ? (
            <article className="section-card dashboard-projects-card">
              <div className="card-header">
                <div>
                  <p className="eyebrow">{t("analytics.monitoring")}</p>
                  <h2>{t("analytics.successTrend")}</h2>
                </div>
              </div>
              <SuccessRateTrendChart data={stats.daily_runs} />
            </article>
          ) : null}

          {/* Daily activity trend */}
          {stats?.daily_runs && stats.daily_runs.length > 1 ? (
            <article className="section-card dashboard-projects-card">
              <div className="card-header">
                <div>
                  <p className="eyebrow">{t("analytics.activity")}</p>
                  <h2>{t("analytics.dailyTrend")}</h2>
                </div>
              </div>
              <DailyTrendChart data={stats.daily_runs} />
            </article>
          ) : null}
        </section>
      )}
    </div>
  );
}
