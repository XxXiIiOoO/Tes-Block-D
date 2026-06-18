import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { forgotPasswordRequest } from "../api/blocktest";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import { toErrorMessage } from "../utils";


export function ForgotPasswordPage() {
  const { t } = useAppPreferences();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);

    try {
      const response = await forgotPasswordRequest({ email });
      setMessage(response.message || t("auth.forgot.sent"));
    } catch (submitError) {
      setError(toErrorMessage(submitError, t("auth.forgot.title")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <p className="eyebrow">BlockTest</p>
        <h1>{t("auth.forgot.title")}</h1>
        <p className="muted">
          {t("auth.forgot.subtitle")}
        </p>

        <form className="stack" onSubmit={handleSubmit}>
          {message ? (
            <div className="state-card">
              <p>{message}</p>
            </div>
          ) : null}

          <label className="field">
            <span>{t("common.email")}</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
          </label>

          {error ? <div className="state-card state-card-error">{error}</div> : null}

          <button className="button button-primary button-block" disabled={busy} type="submit">
            {busy ? t("auth.forgot.pending") : t("auth.forgot.submit")}
          </button>
        </form>

        <p className="auth-footer">
          <Link to="/login">{t("auth.forgot.backToLogin")}</Link>
        </p>
      </div>
    </div>
  );
}
