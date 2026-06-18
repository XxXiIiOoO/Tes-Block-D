import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getRuns } from "../api/blocktest";
import { PageState } from "../components/PageState";
import { StatusBadge } from "../components/StatusBadge";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import type { Run, RunStatus } from "../types";
import { formatDate, localizeBackendText, toErrorMessage } from "../utils";


export function RunsPage() {
  const { autoRefreshMs, refreshOnFocus, t } = useAppPreferences();
  const [runs, setRuns] = useState<Run[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [order, setOrder] = useState("desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadRuns(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    setError(null);

    try {
      const response = await getRuns({
        status: statusFilter === "all" ? undefined : statusFilter,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        sortBy,
        order,
      });

      setRuns(response);
    } catch (loadError) {
      if (!silent || runs.length === 0) {
        setError(toErrorMessage(loadError, t("runs.loadError")));
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadRuns();
  }, [statusFilter, dateFrom, dateTo, sortBy, order]);

  useAutoRefresh(() => loadRuns(true), {
    intervalMs: autoRefreshMs,
    refreshOnFocus,
  });

  return (
    <div className="page-stack">
      <section className="hero-card hero-card-compact">
        <div>
          <p className="eyebrow">{t("nav.runs")}</p>
          <h1>{t("runs.title")}</h1>
          <p className="muted">{t("runs.subtitle")}</p>
        </div>

        <div className="toolbar">
          <span className="counter-chip">{t("runs.liveSync")}</span>
          <label className="field field-inline">
            <span>{t("analytics.status")}</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="all">{t("analytics.status.all")}</option>
              <option value="queued">{t("analytics.status.queued")}</option>
              <option value="running">{t("analytics.status.running")}</option>
              <option value="finished">{t("analytics.status.finished")}</option>
              <option value="failed">{t("analytics.status.failed")}</option>
              <option value="cancelled">{t("analytics.status.cancelled")}</option>
            </select>
          </label>

          <label className="field field-inline">
            <span>{t("runs.sort")}</span>
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
              <option value="created_at">{t("runs.sortCreated")}</option>
              <option value="started_at">{t("runs.sortStarted")}</option>
            </select>
          </label>

          <label className="field field-inline">
            <span>{t("runs.fromDate")}</span>
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>

          <label className="field field-inline">
            <span>{t("runs.toDate")}</span>
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>

          <label className="field field-inline">
            <span>{t("runs.order")}</span>
            <select value={order} onChange={(event) => setOrder(event.target.value)}>
              <option value="desc">{t("runs.orderDesc")}</option>
              <option value="asc">{t("runs.orderAsc")}</option>
            </select>
          </label>
        </div>
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("runs.journal")}</p>
            <h2>{t("runs.allRuns")}</h2>
          </div>
          <span className="counter-chip">{runs.length}</span>
        </div>

        {loading || (runs.length === 0 && error) ? (
          <PageState
            loading={loading}
            error={runs.length === 0 ? error : null}
            emptyMessage={t("runs.empty")}
            hasData={runs.length > 0}
          />
        ) : null}

        {error && runs.length > 0 ? <div className="state-card state-card-error">{error}</div> : null}

        {runs.length > 0 ? (
          <div className="list-grid">
            {runs.map((run) => (
              <article className="list-card" key={run.id}>
                <div className="list-card-top">
                  <div>
                    <p className="eyebrow">{t("common.runWithId", { id: run.id })}</p>
                    <h3>{run.test_name ?? t("runs.untitledTest")}</h3>
                  </div>
                  <StatusBadge status={run.status as RunStatus} />
                </div>
                <p className="muted">{run.project_name ?? t("runs.unknownProject")}</p>
                <p className="muted">{localizeBackendText(run.result_summary) || t("runs.awaitingOutput")}</p>
                <div className="meta-row">
                  <span>{t("common.created")}: {formatDate(run.created_at)}</span>
                  <span>{t("runs.start")}: {formatDate(run.started_at)}</span>
                </div>
                <Link className="text-link" to={`/runs/${run.id}`}>
                  {t("runs.openDetails")}
                </Link>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
