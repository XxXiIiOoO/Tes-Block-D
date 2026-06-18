import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import { toErrorMessage } from "../utils";


export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, verifyTwoFactor } = useAuth();
  const { t } = useAppPreferences();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [twoFactorEmail, setTwoFactorEmail] = useState<string | null>(null);
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const notice =
    typeof location.state === "object" &&
    location.state !== null &&
    "notice" in location.state &&
    typeof (location.state as { notice?: unknown }).notice === "string"
      ? ((location.state as { notice: string }).notice)
      : null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);

    try {
      if (twoFactorEmail) {
        await verifyTwoFactor({ email: twoFactorEmail, code: twoFactorCode });
        navigate("/");
        return;
      }

      const result = await login({ email, password });
      if (result.twoFactorRequired) {
        setTwoFactorEmail(result.email);
        setTwoFactorCode("");
        setPassword("");
        setMessage(result.message || t("auth.login.twoFactorSent"));
        return;
      }
      navigate("/");
    } catch (submitError) {
      setError(toErrorMessage(submitError, t("auth.login.title")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <p className="eyebrow">BlockTest</p>
        <h1>{t("auth.login.title")}</h1>
        <p className="muted">
          {t("auth.login.subtitle")}
        </p>

        <form className="stack" onSubmit={handleSubmit}>
          {notice ? <div className="state-card">{notice}</div> : null}
          {message ? <div className="state-card">{message}</div> : null}

          {twoFactorEmail ? (
            <>
              <label className="field">
                <span>{t("auth.login.twoFactorCode")}</span>
                <input
                  value={twoFactorCode}
                  onChange={(event) => setTwoFactorCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="000000"
                  required
                  inputMode="numeric"
                  pattern="\d{6}"
                  autoComplete="one-time-code"
                />
              </label>
            </>
          ) : (
            <>
              <label className="field">
                <span>{t("auth.login.identifier")}</span>
                <input
                  type="text"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder={t("auth.login.identifierPlaceholder")}
                  required
                  autoComplete="username"
                />
              </label>

              <label className="field">
                <span>{t("auth.login.password")}</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={t("auth.login.passwordPlaceholder")}
                  required
                  autoComplete="current-password"
                />
              </label>
            </>
          )}

          {error ? <div className="state-card state-card-error">{error}</div> : null}

          <button className="button button-primary button-block" disabled={busy} type="submit">
            {busy
              ? t("auth.login.pending")
              : twoFactorEmail
                ? t("auth.login.twoFactorSubmit")
                : t("auth.login.submit")}
          </button>
          {twoFactorEmail ? (
            <button
              className="button button-ghost button-block"
              disabled={busy}
              type="button"
              onClick={() => {
                setTwoFactorEmail(null);
                setTwoFactorCode("");
                setMessage(null);
                setError(null);
              }}
            >
              {t("auth.login.twoFactorBack")}
            </button>
          ) : null}
        </form>

        <p className="auth-footer">
          {t("auth.login.noAccount")} <Link to="/register">{t("auth.login.register")}</Link>
        </p>

      </div>
    </div>
  );
}
