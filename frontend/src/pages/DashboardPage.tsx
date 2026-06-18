import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getRuns, getStatsOverview } from "../api/blocktest";
import { useAuth } from "../auth/AuthContext";
import { PageState } from "../components/PageState";
import { StatusBadge } from "../components/StatusBadge";
import { StatsCharts } from "../components/StatsCharts";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import type { Run, StatsOverview } from "../types";
import { formatDate, formatDurationSeconds, localizeBackendText, toErrorMessage } from "../utils";

export function DashboardPage() {
  const { user } = useAuth();
  const { t, autoRefreshMs, refreshOnFocus } = useAppPreferences();
  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
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
      setRuns(runsResponse.slice(0, 5));
    } catch (loadError) {
      if (!silent || !stats) {
        setError(toErrorMessage(loadError, t("dashboard.emptyRuns")));
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

  const state =
    loading || (!stats && error) ? (
      <PageState
        loading={loading}
        error={!stats ? error : null}
        emptyMessage={t("dashboard.emptyRuns")}
        hasData={Boolean(stats)}
      />
    ) : null;

  if (state) {
    return state;
  }

  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">{t("dashboard.eyebrow")}</p>
          <h1>{t("dashboard.title")}</h1>
          <p className="muted">{user?.is_admin ? t("dashboard.adminSubtitle") : t("dashboard.userSubtitle")}</p>
        </div>
        <div className="pill-row">
          <span className="counter-chip">{`${t("dashboard.autoSync")} ${Math.round(autoRefreshMs / 1000)}${t("common.secondsShort")}`}</span>
          <Link className="button button-primary" to="/projects">
            {t("dashboard.openProjects")}
          </Link>
          <Link className="button button-ghost" to="/runs">
            {t("dashboard.openRuns")}
          </Link>
        </div>
      </section>

      <section className="stats-grid">
        <article className="stat-card">
          <span>{t("stats.projects")}</span>
          <strong>{stats?.project_count ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.tests")}</span>
          <strong>{stats?.test_count ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.totalRuns")}</span>
          <strong>{stats?.run_count ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.successRuns")}</span>
          <strong>{stats?.successful_run_count ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.failedRuns")}</span>
          <strong>{stats?.failed_run_count ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.queuedRuns")}</span>
          <strong>{stats?.queued_run_count ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.runningRuns")}</span>
          <strong>{stats?.running_run_count ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.avgDuration")}</span>
          <strong>{formatDurationSeconds(stats?.average_duration_seconds)}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.avgQueue")}</span>
          <strong>{formatDurationSeconds(stats?.average_queue_time_seconds)}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.activeProjects")}</span>
          <strong>{stats?.active_projects_last_7_days ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>{t("stats.lastRun")}</span>
          <strong>{formatDate(stats?.last_run_at)}</strong>
        </article>
        <article className="stat-card stat-card-highlight">
          <span>{t("stats.successRate")}</span>
          <strong>{stats?.success_rate ?? 0}%</strong>
        </article>
      </section>

      {stats ? <StatsCharts isAdmin={user?.is_admin} stats={stats} /> : null}

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("dashboard.latestRuns")}</p>
            <h2>{t("dashboard.latestRuns")}</h2>
          </div>
          <Link className="button button-ghost" to="/runs">
            {t("dashboard.openRuns")}
          </Link>
        </div>

        {error ? <div className="state-card state-card-error">{error}</div> : null}

        {runs.length === 0 ? (
          <PageState emptyMessage={t("dashboard.emptyRuns")} hasData={false} />
        ) : (
          <div className="list-grid">
            {runs.map((run) => (
              <article className="list-card" key={run.id}>
                <div className="list-card-top">
                  <div>
                    <p className="eyebrow">{t("dashboard.runLabel")} #{run.id}</p>
                    <h3>{run.test_name ?? t("dashboard.untitledTest")}</h3>
                  </div>
                  <StatusBadge status={run.status} />
                </div>
                <p className="muted">{run.project_name ?? t("dashboard.unknownProject")}</p>
                <p className="muted">{localizeBackendText(run.result_summary) || t("dashboard.awaitingWorker")}</p>
                <div className="meta-row">
                  <span>{t("dashboard.created")}: {formatDate(run.created_at)}</span>
                  <span>{t("dashboard.exitCode")}: {run.exit_code ?? t("dashboard.exitCodePending")}</span>
                </div>
                <Link className="text-link" to={`/runs/${run.id}`}>
                  {t("dashboard.openRunDetails")}
                </Link>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
