import { useAppPreferences } from "../preferences/AppPreferencesContext";

export function PageState({
  loading,
  error,
  emptyMessage,
  hasData,
}: {
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  hasData?: boolean;
}) {
  const { t } = useAppPreferences();

  if (loading) {
    return <div className="state-card">{t("common.loading")}</div>;
  }

  if (error) {
    return <div className="state-card state-card-error">{error}</div>;
  }

  if (emptyMessage && hasData === false) {
    return <div className="state-card">{emptyMessage}</div>;
  }

  return null;
}
