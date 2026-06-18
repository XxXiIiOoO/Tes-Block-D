import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getProject, getTest, getTestChatMessages, getTestRuns, postTestChatMessage, runTest } from "../api/blocktest";
import { useAuth } from "../auth/AuthContext";
import { PageState } from "../components/PageState";
import { StatusBadge } from "../components/StatusBadge";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import type { Run, TestChatMessage, TestItem } from "../types";
import { formatDate, localizeBackendText, toErrorMessage } from "../utils";

function roleToLabel(role: "admin" | "worker" | "viewer", t: (key: string) => string) {
  return t(`testDetails.role.${role}`);
}

export function TestDetailsPage() {
  const { user } = useAuth();
  const { autoRefreshMs, refreshOnFocus, t } = useAppPreferences();
  const params = useParams();
  const navigate = useNavigate();
  const testId = Number(params.testId);
  const [test, setTest] = useState<TestItem | null>(null);
  const [projectAccessRole, setProjectAccessRole] = useState<"admin" | "owner" | "developer" | "viewer" | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [chatMessages, setChatMessages] = useState<TestChatMessage[]>([]);
  const [chatDraft, setChatDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);

  async function loadData(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    setError(null);

    try {
      const [testResponse, runsResponse, chatResponse] = await Promise.all([
        getTest(testId),
        getTestRuns(testId, { sortBy: "created_at", order: "desc" }),
        getTestChatMessages(testId),
      ]);
      const projectResponse = await getProject(testResponse.project_id);

      setTest(testResponse);
      setProjectAccessRole(projectResponse.access_role);
      setRuns(runsResponse);
      setChatMessages(chatResponse);
    } catch (loadError) {
      setError(toErrorMessage(loadError, t("testDetails.loadError")));
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    if (!Number.isFinite(testId)) {
      setError(t("testDetails.invalidId"));
      setLoading(false);
      return;
    }

    void loadData();
  }, [testId]);

  const hasActiveRuns = useMemo(
    () => runs.some((run) => run.status === "queued" || run.status === "running"),
    [runs],
  );
  const canWrite = ["admin", "owner", "developer"].includes(projectAccessRole ?? "");

  useAutoRefresh(() => loadData(true), {
    enabled: hasActiveRuns || Boolean(test),
    intervalMs: hasActiveRuns ? 5000 : autoRefreshMs,
    refreshOnFocus,
  });

  async function handleRun() {
    setBusy(true);
    setError(null);

    try {
      const run = await runTest(testId);
      navigate(`/runs/${run.id}`);
    } catch (runError) {
      setError(toErrorMessage(runError, t("testDetails.runError")));
    } finally {
      setBusy(false);
    }
  }

  async function handleSendChatMessage() {
    const message = chatDraft.trim();
    if (!message) {
      setChatError(t("testDetails.emptyMessageError"));
      return;
    }

    setChatBusy(true);
    setChatError(null);
    try {
      const created = await postTestChatMessage(testId, { message });
      setChatMessages((current) => [...current, created]);
      setChatDraft("");
    } catch (submitError) {
      setChatError(toErrorMessage(submitError, t("testDetails.sendMessageError")));
    } finally {
      setChatBusy(false);
    }
  }

  const state =
    loading || (!test && error) ? (
      <PageState
        loading={loading}
        error={!test ? error : null}
        emptyMessage={t("testDetails.notFound")}
        hasData={Boolean(test)}
      />
    ) : null;

  if (state) {
    return state;
  }

  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">{t("testDetails.eyebrow")}</p>
          <h1>{test?.name}</h1>
          <p className="muted">{test?.description ?? t("testDetails.noDescription")}</p>
        </div>
        <div className="pill-row">
          <span className="counter-chip">{t("testDetails.sharedHistory")}</span>
          {canWrite ? (
            <button className="button button-primary" disabled={busy} onClick={handleRun} type="button">
              {busy ? t("testDetails.enqueueing") : t("testDetails.runTest")}
            </button>
          ) : null}
          {test?.project_id ? (
            <Link className="button button-ghost" to={`/projects/${test.project_id}`}>
              {t("testDetails.backToProject")}
            </Link>
          ) : null}
        </div>
      </section>

      {error ? <div className="state-card state-card-error">{error}</div> : null}

      <section className="grid-two">
        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("testDetails.scenario")}</p>
              <h2>{t("testDetails.executionParams")}</h2>
            </div>
          </div>
          <div className="stack">
            <div>
              <p className="eyebrow">{t("testDetails.scenarioDescription")}</p>
              <p>{test?.scenario}</p>
            </div>
            <div>
              <p className="eyebrow">{t("testForm.image")}</p>
              <code className="code-block">{test?.docker_image}</code>
            </div>
            {test?.repository_url ? (
              <>
                <div>
                  <p className="eyebrow">{t("testForm.repositoryUrl")}</p>
                  <code className="code-block">{test.repository_url}</code>
                </div>
                <div className="details-grid">
                  <div>
                    <span className="details-label">{t("testForm.repositoryBranch")}</span>
                    <p>{test.repository_branch ?? "main"}</p>
                  </div>
                  <div>
                    <span className="details-label">{t("testForm.repositorySubdir")}</span>
                    <p>{test.repository_subdir ?? "-"}</p>
                  </div>
                  <div>
                    <span className="details-label">{t("testForm.rpcUrl")}</span>
                    <p>{test.rpc_url ?? "-"}</p>
                  </div>
                  <div>
                    <span className="details-label">{t("testForm.chainId")}</span>
                    <p>{test.chain_id ?? "-"}</p>
                  </div>
                </div>
              </>
            ) : null}
            {test?.script ? (
              <div>
                <p className="eyebrow">{t("testForm.script")}</p>
                <pre className="code-block code-block-script">{test.script}</pre>
              </div>
            ) : null}
            {test?.setup_command ? (
              <div>
                <p className="eyebrow">{t("testForm.setupCommand")}</p>
                <pre className="code-block">{test.setup_command}</pre>
              </div>
            ) : null}
            {test?.command ? (
              <div>
                <p className="eyebrow">{test.repository_url ? t("testForm.testCommand") : t("testForm.command")}</p>
                <pre className="code-block">{test.command}</pre>
              </div>
            ) : null}
          </div>
        </article>

        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("testDetails.history")}</p>
              <h2>{t("testDetails.testRuns")}</h2>
            </div>
            <span className="counter-chip">{runs.length}</span>
          </div>

          <PageState
            loading={false}
            error={null}
            emptyMessage={t("testDetails.emptyRuns")}
            hasData={runs.length > 0}
          />

          {runs.length > 0 ? (
            <div className="list-grid">
              {runs.map((run) => (
                <article className="list-card" key={run.id}>
                  <div className="list-card-top">
                    <div>
                      <p className="eyebrow">{t("common.runWithId", { id: run.id })}</p>
                      <h3>{localizeBackendText(run.result_summary) || t("testDetails.awaitingWorker")}</h3>
                    </div>
                    <StatusBadge status={run.status} />
                  </div>
                  <div className="meta-row">
                    <span>{t("common.created")}: {formatDate(run.created_at)}</span>
                    <span>{t("runDetails.exitCode")}: {run.exit_code ?? t("common.pending")}</span>
                  </div>
                  <Link className="text-link" to={`/runs/${run.id}`}>
                    {t("runs.openDetails")}
                  </Link>
                </article>
              ))}
            </div>
          ) : null}
        </article>
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">{t("testDetails.chat")}</p>
            <h2>{t("testDetails.chatTitle")}</h2>
          </div>
          <span className="counter-chip">{chatMessages.length}</span>
        </div>

        <div className="stack">
          <div className="test-chat-feed">
            {chatMessages.length === 0 ? (
              <div className="state-card">{t("testDetails.noMessages")}</div>
            ) : (
              chatMessages.map((message) => {
                const isOwn = user?.id === message.user_id;
                return (
                  <article className={`chat-message ${isOwn ? "chat-message-own" : ""}`} key={message.id}>
                    <div className="list-card-top">
                      <strong>{message.username}</strong>
                      <span className="code-chip">{roleToLabel(message.role, t)}</span>
                    </div>
                    <p>{message.message}</p>
                    <div className="meta-row">
                      <span>{formatDate(message.created_at)}</span>
                    </div>
                  </article>
                );
              })
            )}
          </div>

          {canWrite ? (
            <>
              <label className="field">
                <span>{t("testDetails.newMessage")}</span>
                <textarea
                  rows={3}
                  value={chatDraft}
                  onChange={(event) => setChatDraft(event.target.value)}
                  placeholder={t("testDetails.messagePlaceholder")}
                />
              </label>

              {chatError ? <div className="state-card state-card-error">{chatError}</div> : null}

              <div className="actions-row">
                <button
                  className="button button-primary"
                  disabled={chatBusy}
                  onClick={handleSendChatMessage}
                  type="button"
                >
                  {chatBusy ? t("testDetails.sending") : t("testDetails.send")}
                </button>
              </div>
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
}
