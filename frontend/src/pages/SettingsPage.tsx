import {
  type AnalyticsSessionScope,
  type AnalyticsWidget,
  useAppPreferences,
} from "../preferences/AppPreferencesContext";

const refreshOptions = [10000, 15000, 30000, 60000];

const widgetOrder: AnalyticsWidget[] = [
  "hourly",
  "statusMix",
  "failureReasons",
  "latency",
  "topTests",
];

const widgetLabels: Record<AnalyticsWidget, string> = {
  hourly: "analytics.hourly",
  statusMix: "analytics.statusDonut",
  failureReasons: "analytics.failure",
  latency: "analytics.latency",
  topTests: "analytics.topProjects",
};

const sessionScopes: AnalyticsSessionScope[] = ["latest_50", "latest_200", "latest_500", "all"];

export function SettingsPage() {
  const {
    language,
    theme,
    autoRefreshMs,
    refreshOnFocus,
    reducedMotion,
    compactCards,
    sidebarCollapsed,
    analyticsSessionScope,
    analyticsWidgets,
    setLanguage,
    setTheme,
    setAutoRefreshMs,
    setRefreshOnFocus,
    setReducedMotion,
    setCompactCards,
    setSidebarCollapsed,
    setAnalyticsSessionScope,
    setAnalyticsWidgetVisible,
    t,
  } = useAppPreferences();

  const sessionScopeLabels: Record<AnalyticsSessionScope, string> = {
    latest_50: t("analytics.sessions.50"),
    latest_200: t("analytics.sessions.200"),
    latest_500: t("analytics.sessions.500"),
    all: t("analytics.sessions.all"),
  };

  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">{t("nav.settings")}</p>
          <h1>{t("settings.title")}</h1>
          <p className="muted">{t("settings.subtitle")}</p>
        </div>
        <div className="pill-row">
          <span className="counter-chip">{t("settings.saved")}</span>
        </div>
      </section>

      <section className="settings-grid">
        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("settings.language")}</p>
              <h2>{t("settings.language")}</h2>
            </div>
          </div>
          <div className="stack">
            <label className="field">
              <span>{t("settings.language")}</span>
              <select
                value={language}
                onChange={(event) => setLanguage(event.target.value as "ru" | "en")}
              >
                <option value="ru">{t("language.ru")}</option>
                <option value="en">{t("language.en")}</option>
              </select>
            </label>
          </div>
        </article>

        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("settings.theme")}</p>
              <h2>{t("settings.theme")}</h2>
            </div>
          </div>
          <div className="stack">
            <label className="field">
              <span>{t("settings.theme")}</span>
              <select
                value={theme}
                onChange={(event) => setTheme(event.target.value as "light" | "dark")}
              >
                <option value="light">{t("settings.theme.light")}</option>
                <option value="dark">{t("settings.theme.dark")}</option>
              </select>
            </label>
          </div>
        </article>

        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("settings.refresh")}</p>
              <h2>{t("settings.refresh")}</h2>
            </div>
          </div>
          <div className="stack">
            <label className="field">
              <span>{t("settings.refresh")}</span>
              <select
                value={autoRefreshMs}
                onChange={(event) => setAutoRefreshMs(Number(event.target.value))}
              >
                {refreshOptions.map((value) => (
                  <option key={value} value={value}>
                    {`${Math.round(value / 1000)} s`}
                  </option>
                ))}
              </select>
            </label>

            <label className="toggle-row">
              <input
                checked={refreshOnFocus}
                onChange={(event) => setRefreshOnFocus(event.target.checked)}
                type="checkbox"
              />
              <span>{t("settings.refresh.focus")}</span>
            </label>
          </div>
        </article>

        <article className="section-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("settings.interface")}</p>
              <h2>{t("settings.interface")}</h2>
            </div>
          </div>
          <div className="stack">
            <label className="toggle-row">
              <input
                checked={reducedMotion}
                onChange={(event) => setReducedMotion(event.target.checked)}
                type="checkbox"
              />
              <span>{t("settings.motion")}</span>
            </label>
            <label className="toggle-row">
              <input
                checked={compactCards}
                onChange={(event) => setCompactCards(event.target.checked)}
                type="checkbox"
              />
              <span>{t("settings.dense")}</span>
            </label>
            <label className="toggle-row">
              <input
                checked={sidebarCollapsed}
                onChange={(event) => setSidebarCollapsed(event.target.checked)}
                type="checkbox"
              />
              <span>{t("settings.sidebar")}</span>
            </label>
          </div>
        </article>

        <article className="section-card settings-analytics-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">{t("nav.analytics")}</p>
              <h2>{t("settings.analyticsTitle")}</h2>
            </div>
          </div>
          <div className="stack">
            <label className="field">
              <span>{t("settings.sessionScope")}</span>
              <select
                value={analyticsSessionScope}
                onChange={(event) => setAnalyticsSessionScope(event.target.value as AnalyticsSessionScope)}
              >
                {sessionScopes.map((scope) => (
                  <option key={scope} value={scope}>
                    {sessionScopeLabels[scope]}
                  </option>
                ))}
              </select>
            </label>

            <div className="stack">
              <p className="muted">{t("settings.visibleMetrics")}</p>
              {widgetOrder.map((widget) => (
                <label className="toggle-row" key={widget}>
                  <input
                    checked={analyticsWidgets[widget]}
                    onChange={(event) => setAnalyticsWidgetVisible(widget, event.target.checked)}
                    type="checkbox"
                  />
                  <span>{t(widgetLabels[widget])}</span>
                </label>
              ))}
            </div>
          </div>
        </article>
      </section>
    </div>
  );
}
