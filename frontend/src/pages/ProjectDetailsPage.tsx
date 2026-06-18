import { startTransition, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  createTest,
  deleteTest,
  getProject,
  getProjectTests,
  updateTest,
} from "../api/blocktest";
import { useAuth } from "../auth/AuthContext";
import { PageState } from "../components/PageState";
import { TestForm } from "../components/TestForm";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import type { Project, TestItem, TestPayload } from "../types";
import { formatDate, toErrorMessage } from "../utils";


export function ProjectDetailsPage() {
  const { autoRefreshMs, refreshOnFocus, t } = useAppPreferences();
  const { user } = useAuth();
  const params = useParams();
  const projectId = Number(params.projectId);
  const [project, setProject] = useState<Project | null>(null);
  const [tests, setTests] = useState<TestItem[]>([]);
  const [editingTest, setEditingTest] = useState<TestItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [formBusy, setFormBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canWrite = ["admin", "owner", "developer"].includes(project?.access_role ?? "");

  async function loadData(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    setError(null);

    try {
      const [projectResponse, testsResponse] = await Promise.all([
        getProject(projectId),
        getProjectTests(projectId),
      ]);
      setProject(projectResponse);
      setTests(testsResponse);
    } catch (loadError) {
      setError(toErrorMessage(loadError, t("projectDetails.loadError")));
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    if (!Number.isFinite(projectId)) {
      setError(t("projectDetails.invalidId"));
      setLoading(false);
      return;
    }

    void loadData();
  }, [projectId]);

  useAutoRefresh(() => loadData(true), {
    intervalMs: autoRefreshMs,
    refreshOnFocus,
  });

  async function handleSubmit(payload: TestPayload) {
    setFormBusy(true);
    setError(null);

    try {
      if (editingTest) {
        await updateTest(editingTest.id, payload);
      } else {
        await createTest(projectId, payload);
      }

      setEditingTest(null);
      await loadData();
    } catch (submitError) {
      setError(toErrorMessage(submitError, t("projectDetails.saveTestError")));
    } finally {
      setFormBusy(false);
    }
  }

  async function handleDelete(testId: number) {
    const confirmed = window.confirm(t("projectDetails.confirmDeleteTest"));
    if (!confirmed) {
      return;
    }

    setError(null);
    try {
      await deleteTest(testId);
      if (editingTest?.id === testId) {
        setEditingTest(null);
      }
      await loadData();
    } catch (deleteError) {
      setError(toErrorMessage(deleteError, t("projectDetails.deleteTestError")));
    }
  }



  const state =
    loading || (!project && error) ? (
      <PageState
        loading={loading}
        error={!project ? error : null}
        emptyMessage={t("projectDetails.notFound")}
        hasData={Boolean(project)}
      />
    ) : null;

  if (state) {
    return state;
  }

  return (
    <div className="page-stack">
      <section className="hero-card hero-card-compact">
        <div>
          <p className="eyebrow">{t("projectDetails.eyebrow")}</p>
          <h1>{project?.name}</h1>
          <p className="muted">{project?.description ?? t("projectDetails.noDescription")}</p>
        </div>
        <div className="meta-column">
          {user?.is_admin ? (
            <span className="counter-chip">
              {t("common.owner")}: {project?.owner_username ?? t("common.userWithId", { id: project?.owner_id ?? "?" })}
            </span>
          ) : null}
          <span className="counter-chip">{t("projectDetails.syncChip")}</span>
          <span>{t("common.created")}: {formatDate(project?.created_at)}</span>
          <span>{t("common.updated")}: {formatDate(project?.updated_at)}</span>
          <Link className="button button-ghost" to="/projects">
            {t("projectDetails.backToProjects")}
          </Link>
        </div>
      </section>

      {project?.repository_url ? (
        <section className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("projectDetails.repositoryEyebrow")}</p>
              <h2>{t("projectDetails.repositoryTitle")}</h2>
            </div>
          </div>
          <code className="code-block">{project.repository_url}</code>
          <div className="meta-row">
            <span>{t("projectForm.repositoryBranch")}: {project.repository_branch ?? "main"}</span>
            <span>{t("projectForm.repositorySubdir")}: {project.repository_subdir ?? "-"}</span>
          </div>
        </section>
      ) : null}



      <section className="grid-two">
        {canWrite ? (
        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{editingTest ? t("projectDetails.editTestEyebrow") : t("projectDetails.createTestEyebrow")}</p>
              <h2>{editingTest ? t("projectDetails.updateTestTitle") : t("projectDetails.addTestTitle")}</h2>
            </div>
          </div>

          {error ? <div className="state-card state-card-error">{error}</div> : null}

          <TestForm
            busy={formBusy}
            initialValue={editingTest}
            onSubmit={handleSubmit}
            onCancel={editingTest ? () => setEditingTest(null) : undefined}
            submitLabel={editingTest ? t("projectDetails.saveTest") : t("projectDetails.createTest")}
          />
        </article>
        ) : null}

        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("projectDetails.testsEyebrow")}</p>
              <h2>{t("projectDetails.testsTitle")}</h2>
            </div>
            <span className="counter-chip">{tests.length}</span>
          </div>

          <PageState
            loading={false}
            error={null}
            emptyMessage={t("projectDetails.emptyTests")}
            hasData={tests.length > 0}
          />

          {tests.length > 0 ? (
            <div className="list-grid">
              {tests.map((test) => (
                <article className="list-card project-test-card" key={test.id}>
                  <div className="list-card-top">
                    <div>
                      <p className="eyebrow">{t("common.testWithId", { id: test.id })}</p>
                      <h3>{test.name}</h3>
                    </div>
                  </div>
                  <p className="muted">{test.description ?? t("projects.noDescription")}</p>
                  {test.repository_url ? (
                    <code className="code-block">{test.repository_url}</code>
                  ) : null}
                  <code className="code-block">{test.docker_image}</code>
                  <div className="meta-row project-test-meta">
                    <span>{t("common.created")}: {formatDate(test.created_at)}</span>
                    <span>{t("common.updated")}: {formatDate(test.updated_at)}</span>
                  </div>
                  <div className="actions-row project-test-actions">
                    <Link className="button button-primary" to={`/tests/${test.id}`}>
                      {t("projectDetails.openTest")}
                    </Link>
                    {canWrite ? (
                      <>
                        <button
                          className="button button-ghost"
                          type="button"
                          onClick={() => {
                            startTransition(() => {
                              setEditingTest(test);
                            });
                          }}
                        >
                          {t("common.edit")}
                        </button>
                        <button
                          className="button button-danger"
                          type="button"
                          onClick={() => handleDelete(test.id)}
                        >
                          {t("common.delete")}
                        </button>
                      </>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </article>
      </section>
    </div>
  );
}
