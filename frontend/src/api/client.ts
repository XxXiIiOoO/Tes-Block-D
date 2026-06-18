import type { AuthResponse } from "../types";
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "../auth/storage";
import { getCurrentLanguage, translate, translateBackendText } from "../preferences/i18n";


const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const UNAUTHORIZED_EVENT = "blocktest:unauthorized";


export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(message: string, status: number, details: unknown) {
    super(message);
    this.status = status;
    this.details = details;
  }
}


let refreshPromise: Promise<string | null> | null = null;


async function buildError(response: Response) {
  let payload: unknown = null;

  try {
    payload = await response.json();
  } catch {
    payload = { detail: response.statusText };
  }

  const rawDetail =
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
      ? payload.detail
      : translate(getCurrentLanguage(), "common.requestError");
  const detail = translateBackendText(getCurrentLanguage(), rawDetail);

  return new ApiError(detail, response.status, payload);
}


async function refreshAccessToken() {
  if (refreshPromise) {
    return refreshPromise;
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return null;
  }

  refreshPromise = (async () => {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearTokens();
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
      return null;
    }

    const data = (await response.json()) as AuthResponse;
    setTokens({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    });
    return data.access_token;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}


async function rawRequest(path: string, options: RequestInit = {}, retry = true) {
  const headers = new Headers(options.headers ?? {});
  const accessToken = getAccessToken();

  if (options.body && !headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && retry && getRefreshToken()) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      return rawRequest(path, options, false);
    }
  }

  if (!response.ok) {
    throw await buildError(response);
  }

  return response;
}


export async function apiRequest<T>(path: string, options: RequestInit = {}) {
  const response = await rawRequest(path, options);

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}


export async function downloadFile(path: string, filename: string) {
  const response = await rawRequest(path);
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}


export async function streamSse<T>(
  path: string,
  options: {
    signal?: AbortSignal;
    onEvent: (payload: T, eventName: string) => void;
  },
) {
  const response = await rawRequest(path, { signal: options.signal });
  const reader = response.body?.getReader();
  if (!reader) {
    throw new ApiError(translate(getCurrentLanguage(), "common.streamUnavailable"), response.status, null);
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    chunks.forEach((chunk) => {
      const lines = chunk.split("\n");
      const eventLine = lines.find((line) => line.startsWith("event:"));
      const dataLines = lines
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice("data:".length).trimStart());

      if (dataLines.length === 0) {
        return;
      }

      options.onEvent(
        JSON.parse(dataLines.join("\n")) as T,
        eventLine ? eventLine.slice("event:".length).trim() : "message",
      );
    });
  }
}


export { UNAUTHORIZED_EVENT };
