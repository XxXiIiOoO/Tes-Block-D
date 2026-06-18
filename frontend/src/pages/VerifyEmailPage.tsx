import { Link } from "react-router-dom";

import { useAppPreferences } from "../preferences/AppPreferencesContext";


export function VerifyEmailPage() {
  const { t } = useAppPreferences();

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <p className="eyebrow">BlockTest</p>
        <h1>{t("auth.verifyEmail.title")}</h1>
        <div className="state-card">{t("auth.verifyEmail.adminOnly")}</div>
        <p className="auth-footer">
          <Link to="/login">{t("auth.login.title")}</Link>
        </p>
      </div>
    </div>
  );
}
