import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { resetPasswordRequest } from "../api/blocktest";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import { toErrorMessage } from "../utils";


export function ResetPasswordPage() {
  const { t } = useAppPreferences();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);

    if (newPassword !== confirmPassword) {
      setError(t("auth.reset.mismatch"));
      setBusy(false);
      return;
    }

    try {
      await resetPasswordRequest({ token, new_password: newPassword });
      setMessage(t("auth.reset.success"));
    } catch (submitError) {
      setError(toErrorMessage(submitError, t("auth.reset.title")));
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="auth-shell">
        <div className="auth-card">
          <p className="eyebrow">BlockTest</p>
          <h1>{t("auth.reset.title")}</h1>
          <p className="muted">{t("auth.reset.noToken")}</p>
          <p className="auth-footer">
            <Link to="/forgot-password">{t("auth.forgot.submit")}</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <p className="eyebrow">BlockTest</p>
        <h1>{t("auth.reset.title")}</h1>
        <p className="muted">
          {t("auth.reset.subtitle")}
        </p>

        <form className="stack" onSubmit={handleSubmit}>
          {message ? (
            <div className="state-card">
              {message}
              <p className="auth-footer" style={{ marginTop: "0.5rem" }}>
                <Link to="/login">{t("auth.forgot.backToLogin")}</Link>
              </p>
            </div>
          ) : null}

          {!message ? (
            <>
              <label className="field">
                <span>{t("auth.reset.newPassword")}</span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder={t("auth.reset.newPassword")}
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </label>

              <label className="field">
                <span>{t("auth.reset.confirmPassword")}</span>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder={t("auth.reset.confirmPassword")}
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </label>

              {error ? <div className="state-card state-card-error">{error}</div> : null}

              <button className="button button-primary button-block" disabled={busy} type="submit">
                {busy ? t("auth.reset.pending") : t("auth.reset.submit")}
              </button>
            </>
          ) : null}
        </form>

        <p className="auth-footer">
          <Link to="/login">{t("auth.forgot.backToLogin")}</Link>
        </p>
      </div>
    </div>
  );
}
