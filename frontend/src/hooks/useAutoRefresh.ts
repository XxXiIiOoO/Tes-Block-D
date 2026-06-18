import { useEffect, useRef } from "react";


interface AutoRefreshOptions {
  enabled?: boolean;
  intervalMs?: number;
  refreshOnFocus?: boolean;
}


export function useAutoRefresh(
  callback: () => void | Promise<void>,
  options: AutoRefreshOptions = {},
) {
  const { enabled = true, intervalMs = 15000, refreshOnFocus = true } = options;
  const callbackRef = useRef(callback);

  callbackRef.current = callback;

  useEffect(() => {
    if (!enabled || intervalMs <= 0) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void callbackRef.current();
    }, intervalMs);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [enabled, intervalMs]);

  useEffect(() => {
    if (!enabled || !refreshOnFocus) {
      return;
    }

    const runRefresh = () => {
      if (document.visibilityState === "visible") {
        void callbackRef.current();
      }
    };

    window.addEventListener("focus", runRefresh);
    document.addEventListener("visibilitychange", runRefresh);

    return () => {
      window.removeEventListener("focus", runRefresh);
      document.removeEventListener("visibilitychange", runRefresh);
    };
  }, [enabled, refreshOnFocus]);
}
