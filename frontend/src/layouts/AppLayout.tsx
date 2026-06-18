import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useAppPreferences } from "../preferences/AppPreferencesContext";

type NavIconName = "dashboard" | "analytics" | "admin" | "projects" | "runs" | "settings" | "logout";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return isActive ? "nav-link active" : "nav-link";
}

function NavIcon({ name }: { name: NavIconName }) {
  const paths: Record<NavIconName, JSX.Element> = {
    dashboard: (
      <>
        <path d="M4 4h7v7H4z" />
        <path d="M13 4h7v5h-7z" />
        <path d="M13 11h7v9h-7z" />
        <path d="M4 13h7v7H4z" />
      </>
    ),
    analytics: (
      <>
        <path d="M4 19V5" />
        <path d="M4 19h16" />
        <path d="m7 15 3-4 3 2 4-7" />
      </>
    ),
    admin: (
      <>
        <path d="M12 3 5 6v5c0 4.2 2.8 7.4 7 9 4.2-1.6 7-4.8 7-9V6z" />
        <path d="M9.5 12.5 11.5 14.5 15 10" />
      </>
    ),
    projects: (
      <>
        <path d="M3 6h7l2 2h9v10H3z" />
        <path d="M3 10h18" />
      </>
    ),
    runs: (
      <>
        <path d="M5 4h14v16H5z" />
        <path d="m10 8 5 4-5 4z" />
      </>
    ),
    settings: (
      <>
        <path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
        <path d="M12 2v3" />
        <path d="M12 19v3" />
        <path d="M4.9 4.9 7 7" />
        <path d="m17 17 2.1 2.1" />
        <path d="M2 12h3" />
        <path d="M19 12h3" />
        <path d="m4.9 19.1 2.1-2.1" />
        <path d="m17 7 2.1-2.1" />
      </>
    ),
    logout: (
      <>
        <path d="M10 5H5v14h5" />
        <path d="M14 8l4 4-4 4" />
        <path d="M18 12H9" />
      </>
    ),
  };

  return (
    <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">
      {paths[name]}
    </svg>
  );
}

function toInitials(value: string) {
  const normalized = value.trim();
  if (!normalized) {
    return "U";
  }
  const parts = normalized.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

export function AppLayout() {
  const { logout, user } = useAuth();
  const { sidebarCollapsed, toggleSidebarCollapsed, t } = useAppPreferences();
  const navigationItems = [
    { to: "/", labelKey: "nav.dashboard", icon: "dashboard" as const, end: true },
    { to: "/analytics", labelKey: "nav.analytics", icon: "analytics" as const },
    ...(user?.is_admin ? [{ to: "/admin", labelKey: "nav.admin", icon: "admin" as const }] : []),
    { to: "/projects", labelKey: "nav.projects", icon: "projects" as const },
    { to: "/runs", labelKey: "nav.runs", icon: "runs" as const },
    { to: "/settings", labelKey: "nav.settings", icon: "settings" as const },
  ];
  const displayName = user?.full_name?.trim() || user?.username || t("layout.defaultUser");
  const position = user?.position?.trim() || t("layout.defaultPosition");

  return (
    <div className={`app-shell app-shell-sidebar ${sidebarCollapsed ? "app-shell-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <NavLink className="brand" to="/">
            <NavIcon name="projects" />
            <span className="brand-text">BlockTest</span>
          </NavLink>
          <p className="topbar-note">{t("brand.subtitle")}</p>

          <button
            aria-label={sidebarCollapsed ? t("layout.expandSidebar") : t("layout.collapseSidebar")}
            className="button button-ghost sidebar-toggle"
            onClick={toggleSidebarCollapsed}
            title={sidebarCollapsed ? t("layout.expandSidebar") : t("layout.collapseSidebar")}
            type="button"
          >
            {sidebarCollapsed ? ">" : "<"}
          </button>
        </div>

        <nav className="sidebar-nav">
          {navigationItems.map((item) => (
            <NavLink
              key={item.to}
              className={navLinkClass}
              end={item.end}
              title={t(item.labelKey)}
              to={item.to}
            >
              <NavIcon name={item.icon} />
              <span className="nav-label">{t(item.labelKey)}</span>
            </NavLink>
          ))}
        </nav>

        <div className="topbar-meta sidebar-meta">
          <button
            aria-label={t("layout.logout")}
            className="button button-ghost sidebar-logout"
            onClick={logout}
            title={t("layout.logout")}
            type="button"
          >
            <NavIcon name="logout" />
            <span className="nav-label">{t("layout.logout")}</span>
          </button>
        </div>
      </aside>

      <div className="layout-content">
        <header className="topbar app-topbar">
          <div>
            <p className="eyebrow">{t("layout.mobileMenu")}</p>
            <strong>BlockTest</strong>
          </div>

          <button
            aria-label={sidebarCollapsed ? t("layout.expandSidebar") : t("layout.collapseSidebar")}
            className="button button-ghost sidebar-toggle"
            onClick={toggleSidebarCollapsed}
            title={sidebarCollapsed ? t("layout.expandSidebar") : t("layout.collapseSidebar")}
            type="button"
          >
            {sidebarCollapsed ? ">" : "<"}
          </button>

          <div className="topbar-meta app-topbar-actions">
            <NavLink className="profile-trigger" to="/profile">
              <span className="profile-avatar-sm">
                {user?.avatar_url?.trim() ? (
                  <img alt={displayName} src={user.avatar_url} />
                ) : (
                  <span>{toInitials(displayName)}</span>
                )}
              </span>
              <span className="profile-trigger-text">
                <strong>{displayName}</strong>
                <small>{position}</small>
              </span>
            </NavLink>
            <button className="button button-ghost" onClick={logout} type="button">
              {t("layout.logout")}
            </button>
          </div>
        </header>

        <main className="page-shell">
          <Outlet />
        </main>
      </div>

      <nav className="mobile-nav">
        {navigationItems.map((item) => (
          <NavLink
            key={item.to}
            className={navLinkClass}
            end={item.end}
            to={item.to}
          >
            {t(item.labelKey)}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
