import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import type { Project, ProjectPayload } from "../types";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import { toNullableText } from "../utils";


const initialState = {
  name: "",
  description: "",
  repository_url: "",
  repository_branch: "main",
  repository_subdir: "",
};

type Mode = "manual" | "github";

function repositoryNameFromUrl(value: string) {
  const normalized = value.trim().replace(/\.git$/, "");
  const parts = normalized.split(/[/:]/).filter(Boolean);
  return parts.length > 0 ? parts[parts.length - 1] : "";
}

export function ProjectForm({
  initialValue,
  onSubmit,
  onCancel,
  submitLabel,
  busy,
}: {
  initialValue?: Project | null;
  onSubmit: (payload: ProjectPayload) => Promise<void>;
  onCancel?: () => void;
  submitLabel: string;
  busy?: boolean;
}) {
  const { t } = useAppPreferences();
  const [mode, setMode] = useState<Mode>("manual");
  const [form, setForm] = useState(initialState);

  useEffect(() => {
    if (initialValue) {
      setMode(initialValue.repository_url ? "github" : "manual");
      setForm({
        name: initialValue.name,
        description: initialValue.description ?? "",
        repository_url: initialValue.repository_url ?? "",
        repository_branch: initialValue.repository_branch ?? "main",
        repository_subdir: initialValue.repository_subdir ?? "",
      });
    } else {
      setMode("manual");
      setForm(initialState);
    }
  }, [initialValue]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const isGithub = mode === "github";
    await onSubmit({
      name: form.name.trim(),
      description: toNullableText(form.description),
      repository_url: isGithub ? form.repository_url.trim() || null : null,
      repository_branch: isGithub ? form.repository_branch.trim() || null : null,
      repository_subdir: isGithub ? toNullableText(form.repository_subdir) : null,
    });

    if (!initialValue) {
      setMode("manual");
      setForm(initialState);
    }
  }

  return (
    <form className="stack" onSubmit={handleSubmit}>
      <div className="test-mode-toggle">
        <button
          className={mode === "manual" ? "active" : ""}
          onClick={() => setMode("manual")}
          type="button"
        >
          {t("projectForm.modeManual")}
        </button>
        <button
          className={mode === "github" ? "active" : ""}
          onClick={() => setMode("github")}
          type="button"
        >
          {t("projectForm.modeGithub")}
        </button>
      </div>

      <label className="field">
        <span>{t("projectForm.name")}</span>
        <input
          value={form.name}
          onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
          placeholder={t("projectForm.namePlaceholder")}
          required
        />
      </label>

      <label className="field">
        <span>{t("common.description")}</span>
        <textarea
          rows={4}
          value={form.description}
          onChange={(event) =>
            setForm((current) => ({ ...current, description: event.target.value }))
          }
          placeholder={t("projectForm.descriptionPlaceholder")}
        />
      </label>

      {mode === "github" ? (
        <>
          <label className="field">
            <span>{t("projectForm.repositoryUrl")}</span>
            <input
              value={form.repository_url}
              onChange={(event) => {
                const repositoryUrl = event.target.value;
                setForm((current) => {
                  const inferredName = repositoryNameFromUrl(repositoryUrl);
                  return {
                    ...current,
                    name: current.name.trim() ? current.name : inferredName,
                    repository_url: repositoryUrl,
                  };
                });
              }}
              placeholder={t("projectForm.repositoryUrlPlaceholder")}
              required
            />
          </label>
          <div className="settings-grid">
            <label className="field">
              <span>{t("projectForm.repositoryBranch")}</span>
              <input
                value={form.repository_branch}
                onChange={(event) =>
                  setForm((current) => ({ ...current, repository_branch: event.target.value }))
                }
                placeholder="main"
              />
            </label>
            <label className="field">
              <span>{t("projectForm.repositorySubdir")}</span>
              <input
                value={form.repository_subdir}
                onChange={(event) =>
                  setForm((current) => ({ ...current, repository_subdir: event.target.value }))
                }
                placeholder={t("projectForm.repositorySubdirPlaceholder")}
              />
            </label>
          </div>
        </>
      ) : null}

      <div className="actions-row">
        <button className="button button-primary" disabled={busy} type="submit">
          {busy ? t("common.savePending") : submitLabel}
        </button>
        {onCancel ? (
          <button className="button button-ghost" type="button" onClick={onCancel}>
            {t("common.cancel")}
          </button>
        ) : null}
      </div>
    </form>
  );
}
