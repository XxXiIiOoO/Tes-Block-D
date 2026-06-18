import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import { toErrorMessage } from "../utils";


export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const { t } = useAppPreferences();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const notice = await register({ email, username, password });
      navigate("/login", { state: { notice } });
    } catch (submitError) {
      setError(toErrorMessage(submitError, t("auth.register.error")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <p className="eyebrow">BlockTest</p>
        <h1>{t("auth.register.title")}</h1>
        <p className="muted">
          {t("auth.register.subtitle")}
        </p>

        <form className="stack" onSubmit={handleSubmit}>
          <label className="field">
            <span>{t("common.email")}</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
            />
          </label>

          <label className="field">
            <span>{t("auth.register.username")}</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="qa_user"
              required
            />
          </label>

          <label className="field">
            <span>{t("auth.register.password")}</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t("auth.register.passwordPlaceholder")}
              required
            />
          </label>

          {error ? <div className="state-card state-card-error">{error}</div> : null}

          <button className="button button-primary button-block" disabled={busy} type="submit">
            {busy ? t("auth.register.pending") : t("auth.register.submit")}
          </button>
        </form>

        <p className="auth-footer">
          {t("auth.register.hasAccount")} <Link to="/login">{t("auth.register.login")}</Link>
        </p>
      </div>
    </div>
  );
}
