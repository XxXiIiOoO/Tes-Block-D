import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { useAuth } from "../auth/AuthContext";
import { useAppPreferences } from "../preferences/AppPreferencesContext";
import { toErrorMessage } from "../utils";

function getInitials(name: string, fallback: string) {
  const normalized = name.trim();
  if (!normalized) {
    return fallback;
  }

  const parts = normalized.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

export function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const { t } = useAppPreferences();
  const [fullName, setFullName] = useState("");
  const [position, setPosition] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [bio, setBio] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    setFullName(user?.full_name ?? "");
    setPosition(user?.position ?? "");
    setAvatarUrl(user?.avatar_url ?? "");
    setBio(user?.bio ?? "");
  }, [user]);

  const displayName = useMemo(() => {
    return fullName.trim() || user?.username || t("profile.defaultUser");
  }, [fullName, t, user?.username]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);

    try {
      await updateProfile({
        full_name: fullName,
        position,
        avatar_url: avatarUrl,
        bio,
      });
      setSuccess(t("profile.saveSuccess"));
    } catch (submitError) {
      setError(toErrorMessage(submitError, t("profile.saveError")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="hero-card hero-card-compact">
        <div>
          <p className="eyebrow">{t("profile.eyebrow")}</p>
          <h1>{t("profile.title")}</h1>
          <p className="muted">{t("profile.subtitle")}</p>
        </div>
      </section>

      <section className="grid-two">
        <article className="section-card">
          <div className="profile-preview">
            <div className="profile-avatar-lg">
              {avatarUrl.trim() ? (
                <img alt={displayName} src={avatarUrl} />
              ) : (
                <span>{getInitials(displayName, t("profile.initialFallback"))}</span>
              )}
            </div>
            <div>
              <h2>{displayName}</h2>
              <p className="muted">{position.trim() || t("profile.positionEmpty")}</p>
              <p className="muted">{user?.email}</p>
            </div>
          </div>
          {bio.trim() ? <p>{bio}</p> : <p className="muted">{t("profile.bioEmpty")}</p>}
        </article>

        <article className="section-card">
          <form className="stack" onSubmit={handleSubmit}>
            <label className="field">
              <span>{t("profile.fullName")}</span>
              <input
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder={t("profile.fullNamePlaceholder")}
              />
            </label>

            <label className="field">
              <span>{t("profile.position")}</span>
              <input
                value={position}
                onChange={(event) => setPosition(event.target.value)}
                placeholder={t("profile.positionPlaceholder")}
              />
            </label>

            <label className="field">
              <span>{t("profile.avatarUrl")}</span>
              <input
                value={avatarUrl}
                onChange={(event) => setAvatarUrl(event.target.value)}
                placeholder="https://..."
              />
            </label>

            <label className="field">
              <span>{t("profile.bio")}</span>
              <textarea
                rows={5}
                value={bio}
                onChange={(event) => setBio(event.target.value)}
                placeholder={t("profile.bioPlaceholder")}
              />
            </label>

            {success ? <div className="state-card">{success}</div> : null}
            {error ? <div className="state-card state-card-error">{error}</div> : null}

            <button className="button button-primary" disabled={busy} type="submit">
              {busy ? t("common.savePending") : t("profile.save")}
            </button>
          </form>
        </article>
      </section>
    </div>
  );
}
