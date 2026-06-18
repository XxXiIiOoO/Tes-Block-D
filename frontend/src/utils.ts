import { getCurrentLanguage, translate, translateBackendText } from "./preferences/i18n";

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return translate(getCurrentLanguage(), "common.notAvailable");
  }

  const language = getCurrentLanguage();
  return new Date(value).toLocaleString(language === "en" ? "en-US" : "ru-RU");
}


export function formatShortDate(value: string | null | undefined) {
  if (!value) {
    return "--";
  }

  const normalizedValue = /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00` : value;
  return new Date(normalizedValue).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}


export function formatDurationSeconds(value: number | null | undefined) {
  if (value == null || Number.isNaN(value) || value < 0) {
    return translate(getCurrentLanguage(), "common.notMeasured");
  }

  if (value < 60) {
    return `${Math.round(value)} ${translate(getCurrentLanguage(), "common.seconds")}`;
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes} ${translate(getCurrentLanguage(), "common.minutes")} ${seconds} ${translate(getCurrentLanguage(), "common.seconds")}`;
}


export function humanizeToken(value: string | null | undefined) {
  if (!value) {
    return translate(getCurrentLanguage(), "common.unavailable");
  }

  return value
    .split(/[_-]/g)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}

export function localizeBackendText(value: string | null | undefined) {
  return translateBackendText(getCurrentLanguage(), value);
}


export function toNullableText(value: string) {
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}


export function toErrorMessage(error: unknown, fallback = translate(getCurrentLanguage(), "common.genericError")) {
  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}
