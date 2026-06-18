import type { RunStatus } from "../types";
import { useAppPreferences } from "../preferences/AppPreferencesContext";

export function StatusBadge({ status }: { status: RunStatus }) {
  const { t } = useAppPreferences();
  return <span className={`badge badge-${status}`}>{t(`analytics.status.${status}`)}</span>;
}
