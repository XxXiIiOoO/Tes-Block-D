import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import type { TestItem, TestPayload } from "../types";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import { toNullableText } from "../utils";

const PYTHON_IMAGE = "python:3.12-slim";
const NODE_IMAGE = "node:20-bookworm-slim";

function createInitialState(defaultScript: string) {
  return {
    name: "",
    description: "",
    scenario: "",
    docker_image: PYTHON_IMAGE,
    command: "",
    script: defaultScript,
    repository_url: "",
    repository_branch: "main",
    repository_subdir: "",
    setup_command: "npm ci",
    rpc_url: "",
    chain_id: "",
  };
}

type Mode = "python" | "advanced" | "github";

export function TestForm({
  initialValue,
  onSubmit,
  onCancel,
  submitLabel,
  busy,
}: {
  initialValue?: TestItem | null;
  onSubmit: (payload: TestPayload) => Promise<void>;
  onCancel?: () => void;
  submitLabel: string;
  busy?: boolean;
}) {
  const { t } = useAppPreferences();
  const defaultScript = t("testForm.defaultScript");
  const [mode, setMode] = useState<Mode>("python");
  const [form, setForm] = useState(() => createInitialState(defaultScript));

  useEffect(() => {
    if (initialValue) {
      const isGithub = Boolean(initialValue.repository_url);
      const isScript = Boolean(initialValue.script);
      setMode(isGithub ? "github" : isScript ? "python" : "advanced");
      setForm({
        name: initialValue.name,
        description: initialValue.description ?? "",
        scenario: initialValue.scenario,
        docker_image: initialValue.docker_image,
        command: initialValue.command ?? "",
        script: initialValue.script ?? defaultScript,
        repository_url: initialValue.repository_url ?? "",
        repository_branch: initialValue.repository_branch ?? "main",
        repository_subdir: initialValue.repository_subdir ?? "",
        setup_command: initialValue.setup_command ?? "",
        rpc_url: initialValue.rpc_url ?? "",
        chain_id: initialValue.chain_id?.toString() ?? "",
      });
    } else {
      setMode("python");
      setForm(createInitialState(defaultScript));
    }
  }, [initialValue, defaultScript]);

  function switchMode(next: Mode) {
    setMode(next);
    if (next === "python" && form.docker_image !== PYTHON_IMAGE) {
      setForm((current) => ({ ...current, docker_image: PYTHON_IMAGE }));
    }
    if (next === "github" && form.docker_image !== NODE_IMAGE) {
      setForm((current) => ({ ...current, docker_image: NODE_IMAGE }));
    }
  }

  function toNullableInteger(value: string) {
    const normalized = value.trim();
    return normalized ? Number(normalized) : null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const isGithub = mode === "github";
    await onSubmit({
      name: form.name.trim(),
      description: toNullableText(form.description),
      scenario: form.scenario.trim(),
      docker_image: form.docker_image.trim(),
      command: mode === "advanced" || isGithub ? form.command.trim() || null : null,
      script: mode === "python" ? form.script || null : null,
      repository_url: isGithub ? form.repository_url.trim() || null : null,
      repository_branch: isGithub ? form.repository_branch.trim() || null : null,
      repository_subdir: isGithub ? toNullableText(form.repository_subdir) : null,
      setup_command: isGithub ? toNullableText(form.setup_command) : null,
      rpc_url: isGithub ? toNullableText(form.rpc_url) : null,
      chain_id: isGithub ? toNullableInteger(form.chain_id) : null,
    });

    if (!initialValue) {
      setMode("python");
      setForm(createInitialState(defaultScript));
    }
  }

  return (
    <form className="stack" onSubmit={handleSubmit}>
      <div className="test-mode-toggle">
        <button
          className={mode === "python" ? "active" : ""}
          onClick={() => switchMode("python")}
          type="button"
        >
          {t("testForm.modePython")}
        </button>
        <button
          className={mode === "advanced" ? "active" : ""}
          onClick={() => switchMode("advanced")}
          type="button"
        >
          {t("testForm.modeAdvanced")}
        </button>
        <button
          className={mode === "github" ? "active" : ""}
          onClick={() => switchMode("github")}
          type="button"
        >
          {t("testForm.modeGithub")}
        </button>
      </div>

      <label className="field">
        <span>{t("testForm.name")}</span>
        <input
          value={form.name}
          onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
          placeholder={t("testForm.namePlaceholder")}
          required
        />
      </label>

      <label className="field">
        <span>{t("common.description")}</span>
        <textarea
          rows={2}
          value={form.description}
          onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
          placeholder={t("testForm.descriptionPlaceholder")}
        />
      </label>

      <label className="field">
        <span>{t("testForm.scenario")}</span>
        <textarea
          rows={3}
          value={form.scenario}
          onChange={(event) => setForm((current) => ({ ...current, scenario: event.target.value }))}
          placeholder={t("testForm.scenarioPlaceholder")}
          required
        />
      </label>

      {mode === "python" ? (
        <>
          <label className="field">
            <span>{t("testForm.script")}</span>
            <textarea
              className="code-textarea"
              rows={18}
              spellCheck={false}
              value={form.script}
              onChange={(event) => setForm((current) => ({ ...current, script: event.target.value }))}
              placeholder={t("testForm.scriptPlaceholder")}
              required
            />
          </label>
          <label className="field">
            <span>{t("testForm.image")}</span>
            <input
              value={form.docker_image}
              onChange={(event) =>
                setForm((current) => ({ ...current, docker_image: event.target.value }))
              }
              placeholder={PYTHON_IMAGE}
              required
            />
          </label>
          <p className="muted" style={{ fontSize: "0.85rem", marginTop: "-0.5rem" }}>
            {t("testForm.defaultImageHelp", { image: PYTHON_IMAGE })}
          </p>
        </>
      ) : mode === "advanced" ? (
        <>
          <label className="field">
            <span>{t("testForm.image")}</span>
            <input
              value={form.docker_image}
              onChange={(event) =>
                setForm((current) => ({ ...current, docker_image: event.target.value }))
              }
              placeholder={PYTHON_IMAGE}
              required
            />
          </label>
          <label className="field">
            <span>{t("testForm.command")}</span>
            <textarea
              rows={4}
              value={form.command}
              onChange={(event) => setForm((current) => ({ ...current, command: event.target.value }))}
              placeholder={t("testForm.commandPlaceholder")}
              required
            />
          </label>
        </>
      ) : (
        <>
          <label className="field">
            <span>{t("testForm.repositoryUrl")}</span>
            <input
              value={form.repository_url}
              onChange={(event) =>
                setForm((current) => ({ ...current, repository_url: event.target.value }))
              }
              placeholder={t("testForm.repositoryUrlPlaceholder")}
              required
            />
          </label>
          <div className="settings-grid">
            <label className="field">
              <span>{t("testForm.repositoryBranch")}</span>
              <input
                value={form.repository_branch}
                onChange={(event) =>
                  setForm((current) => ({ ...current, repository_branch: event.target.value }))
                }
                placeholder="main"
              />
            </label>
            <label className="field">
              <span>{t("testForm.repositorySubdir")}</span>
              <input
                value={form.repository_subdir}
                onChange={(event) =>
                  setForm((current) => ({ ...current, repository_subdir: event.target.value }))
                }
                placeholder={t("testForm.repositorySubdirPlaceholder")}
              />
            </label>
          </div>
          <label className="field">
            <span>{t("testForm.image")}</span>
            <input
              value={form.docker_image}
              onChange={(event) =>
                setForm((current) => ({ ...current, docker_image: event.target.value }))
              }
              placeholder={NODE_IMAGE}
              required
            />
          </label>
          <div className="settings-grid">
            <label className="field">
              <span>{t("testForm.rpcUrl")}</span>
              <input
                value={form.rpc_url}
                onChange={(event) => setForm((current) => ({ ...current, rpc_url: event.target.value }))}
                placeholder={t("testForm.rpcUrlPlaceholder")}
              />
            </label>
            <label className="field">
              <span>{t("testForm.chainId")}</span>
              <input
                min={1}
                type="number"
                value={form.chain_id}
                onChange={(event) => setForm((current) => ({ ...current, chain_id: event.target.value }))}
                placeholder="31337"
              />
            </label>
          </div>
          <label className="field">
            <span>{t("testForm.setupCommand")}</span>
            <textarea
              rows={3}
              value={form.setup_command}
              onChange={(event) => setForm((current) => ({ ...current, setup_command: event.target.value }))}
              placeholder={t("testForm.setupCommandPlaceholder")}
            />
          </label>
          <label className="field">
            <span>{t("testForm.testCommand")}</span>
            <textarea
              rows={4}
              value={form.command}
              onChange={(event) => setForm((current) => ({ ...current, command: event.target.value }))}
              placeholder={t("testForm.testCommandPlaceholder")}
              required
            />
          </label>
        </>
      )}

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
