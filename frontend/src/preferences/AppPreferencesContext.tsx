import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import type { AppLanguage } from "./i18n";
import { translate } from "./i18n";

export type AppTheme = "light" | "dark";
export type AnalyticsSessionScope = "latest_50" | "latest_200" | "latest_500" | "all";
export type AnalyticsWidget = "hourly" | "statusMix" | "failureReasons" | "latency" | "topTests";

type AnalyticsWidgetMap = Record<AnalyticsWidget, boolean>;

interface AppPreferencesState {
  language: AppLanguage;
  theme: AppTheme;
  autoRefreshMs: number;
  refreshOnFocus: boolean;
  reducedMotion: boolean;
  compactCards: boolean;
  sidebarCollapsed: boolean;
  analyticsSessionScope: AnalyticsSessionScope;
  analyticsWidgets: AnalyticsWidgetMap;
}

interface AppPreferencesContextValue extends AppPreferencesState {
  setLanguage: (value: AppLanguage) => void;
  setTheme: (value: AppTheme) => void;
  setAutoRefreshMs: (value: number) => void;
  setRefreshOnFocus: (value: boolean) => void;
  setReducedMotion: (value: boolean) => void;
  setCompactCards: (value: boolean) => void;
  setSidebarCollapsed: (value: boolean) => void;
  setAnalyticsSessionScope: (value: AnalyticsSessionScope) => void;
  setAnalyticsWidgetVisible: (widget: AnalyticsWidget, value: boolean) => void;
  toggleSidebarCollapsed: () => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const STORAGE_KEY = "blocktest:preferences:v2";

const defaultAnalyticsWidgets: AnalyticsWidgetMap = {
  hourly: true,
  statusMix: true,
  failureReasons: true,
  latency: true,
  topTests: true,
};

const defaultPreferences: AppPreferencesState = {
  language: "ru",
  theme: "dark",
  autoRefreshMs: 15000,
  refreshOnFocus: true,
  reducedMotion: false,
  compactCards: false,
  sidebarCollapsed: false,
  analyticsSessionScope: "latest_200",
  analyticsWidgets: defaultAnalyticsWidgets,
};

const AppPreferencesContext = createContext<AppPreferencesContextValue | undefined>(undefined);

function normalizeTheme(theme: string | undefined): AppTheme {
  if (theme === "dark" || theme === "midnight") {
    return "dark";
  }
  return "light";
}

function parseStoredPreferences(value: string | null): AppPreferencesState {
  if (!value) {
    return defaultPreferences;
  }

  try {
    const parsed = JSON.parse(value) as Partial<AppPreferencesState> & { theme?: string };
    const analyticsWidgets = {
      ...defaultAnalyticsWidgets,
      ...parsed.analyticsWidgets,
    };
    return {
      ...defaultPreferences,
      ...parsed,
      theme: normalizeTheme(parsed.theme),
      analyticsWidgets,
    };
  } catch {
    return defaultPreferences;
  }
}

export function AppPreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<AppPreferencesState>(() =>
    parseStoredPreferences(localStorage.getItem(STORAGE_KEY)),
  );

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  }, [preferences]);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = preferences.theme;
    root.dataset.language = preferences.language;
    root.classList.toggle("reduced-motion", preferences.reducedMotion);
    root.classList.toggle("compact-cards", preferences.compactCards);
  }, [preferences]);

  const value = useMemo<AppPreferencesContextValue>(
    () => ({
      ...preferences,
      setLanguage: (language) => setPreferences((prev) => ({ ...prev, language })),
      setTheme: (theme) => setPreferences((prev) => ({ ...prev, theme })),
      setAutoRefreshMs: (autoRefreshMs) =>
        setPreferences((prev) => ({ ...prev, autoRefreshMs })),
      setRefreshOnFocus: (refreshOnFocus) =>
        setPreferences((prev) => ({ ...prev, refreshOnFocus })),
      setReducedMotion: (reducedMotion) =>
        setPreferences((prev) => ({ ...prev, reducedMotion })),
      setCompactCards: (compactCards) =>
        setPreferences((prev) => ({ ...prev, compactCards })),
      setSidebarCollapsed: (sidebarCollapsed) =>
        setPreferences((prev) => ({ ...prev, sidebarCollapsed })),
      setAnalyticsSessionScope: (analyticsSessionScope) =>
        setPreferences((prev) => ({ ...prev, analyticsSessionScope })),
      setAnalyticsWidgetVisible: (widget, visible) =>
        setPreferences((prev) => ({
          ...prev,
          analyticsWidgets: {
            ...prev.analyticsWidgets,
            [widget]: visible,
          },
        })),
      toggleSidebarCollapsed: () =>
        setPreferences((prev) => ({
          ...prev,
          sidebarCollapsed: !prev.sidebarCollapsed,
        })),
      t: (key, params) => translate(preferences.language, key, params),
    }),
    [preferences],
  );

  return (
    <AppPreferencesContext.Provider value={value}>{children}</AppPreferencesContext.Provider>
  );
}

export function useAppPreferences() {
  const context = useContext(AppPreferencesContext);
  if (!context) {
    throw new Error("useAppPreferences must be used within AppPreferencesProvider");
  }
  return context;
}
