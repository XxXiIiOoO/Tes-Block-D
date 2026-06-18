import { startTransition, useDeferredValue, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  createProject,
  deleteProject,
  getProjects,
  updateProject,
} from "../api/blocktest";
import { useAuth } from "../auth/AuthContext";
import { PageState } from "../components/PageState";
import { ProjectForm } from "../components/ProjectForm";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import type { Project, ProjectPayload } from "../types";
import { formatDate, toErrorMessage } from "../utils";


export function ProjectsPage() {
  const { user } = useAuth();
  const { t } = useAppPreferences();
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [formBusy, setFormBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(searchInput);

  async function loadProjects(search?: string) {
    setLoading(true);
    setError(null);

    try {
      const response = await getProjects(search);
      setProjects(response);
    } catch (loadError) {
      setError(toErrorMessage(loadError, t("projects.loadError")));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProjects(deferredSearch);
  }, [deferredSearch]);

  async function handleSubmit(payload: ProjectPayload) {
    setFormBusy(true);
    setError(null);

    try {
      if (editingProject) {
        await updateProject(editingProject.id, payload);
      } else {
        await createProject(payload);
      }

      setEditingProject(null);
      await loadProjects(deferredSearch);
    } catch (submitError) {
      setError(toErrorMessage(submitError, t("projects.saveError")));
    } finally {
      setFormBusy(false);
    }
  }

  async function handleDelete(projectId: number) {
    const confirmed = window.confirm(t("projects.confirmDelete"));
    if (!confirmed) {
      return;
    }

    setError(null);
    try {
      await deleteProject(projectId);
      if (editingProject?.id === projectId) {
        setEditingProject(null);
      }
      await loadProjects(deferredSearch);
    } catch (deleteError) {
      setError(toErrorMessage(deleteError, t("projects.deleteError")));
    }
  }

  return (
    <div className="page-stack">
      <section className="hero-card hero-card-compact">
        <div>
          <p className="eyebrow">{t("nav.projects")}</p>
          <h1>{t("projects.title")}</h1>
          <p className="muted">
            {user?.is_admin ? t("projects.subtitleAdmin") : t("projects.subtitleUser")}
          </p>
        </div>

        <label className="field field-inline">
          <span>{t("projects.searchLabel")}</span>
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={t("projects.searchPlaceholder")}
          />
        </label>
      </section>

      <section className="grid-two">
        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{editingProject ? t("projects.editEyebrow") : t("projects.createEyebrow")}</p>
              <h2>{editingProject ? t("projects.updateTitle") : t("projects.createTitle")}</h2>
            </div>
          </div>

          {error ? <div className="state-card state-card-error">{error}</div> : null}

          <ProjectForm
            busy={formBusy}
            initialValue={editingProject}
            onSubmit={handleSubmit}
            onCancel={editingProject ? () => setEditingProject(null) : undefined}
            submitLabel={editingProject ? t("projects.saveChanges") : t("projects.createProject")}
          />
        </article>

        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("projects.catalog")}</p>
              <h2>{user?.is_admin ? t("projects.allProjects") : t("projects.yourProjects")}</h2>
            </div>
            <span className="counter-chip">{projects.length}</span>
          </div>

          <PageState
            loading={loading}
            error={null}
            emptyMessage={t("projects.empty")}
            hasData={projects.length > 0}
          />

          {projects.length > 0 ? (
            <div className="list-grid">
              {projects.map((project) => (
                <article className="list-card" key={project.id}>
                  <div className="list-card-top">
                    <div>
                      <p className="eyebrow">{t("common.projectWithId", { id: project.id })}</p>
                      <h3>{project.name}</h3>
                    </div>
                  </div>
                  <p className="muted">{project.description ?? t("projects.noDescription")}</p>
                  {project.repository_url ? (
                    <code className="code-block">{project.repository_url}</code>
                  ) : null}
                  {user?.is_admin ? (
                    <p className="muted">
                      {t("common.owner")}: {project.owner_username ?? t("common.userWithId", { id: project.owner_id })}
                    </p>
                  ) : null}
                  <div className="meta-row">
                    <span>{t("common.created")}: {formatDate(project.created_at)}</span>
                    <span>{t("common.updated")}: {formatDate(project.updated_at)}</span>
                  </div>
                  <div className="actions-row">
                    <Link className="button button-primary" to={`/projects/${project.id}`}>
                      {t("common.open")}
                    </Link>
                    <button
                      className="button button-ghost"
                      type="button"
                      onClick={() => {
                        startTransition(() => {
                          setEditingProject(project);
                        });
                      }}
                    >
                      {t("common.edit")}
                    </button>
                    <button
                      className="button button-danger"
                      type="button"
                      onClick={() => handleDelete(project.id)}
                    >
                      {t("common.delete")}
                    </button>
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
