"use client";

import { useCallback, useEffect, useState } from "react";

import { adminFetch } from "@/lib/admin-api";

// Sprint 7.4: loads one admin API resource (a page of a list, the stats...).
// "Loading" is derived from which URL was last answered, so the effect only
// sets state in the request's callbacks (no synchronous setState, no stale
// answer: a response for an older URL is ignored).
export function useAdminResource<T>(url: string) {
  const [version, setVersion] = useState(0);
  const key = `${url}#${version}`;
  const [result, setResult] = useState<{ key: string; data: T | null; error: string }>({
    key: "",
    data: null,
    error: "",
  });

  useEffect(() => {
    let cancelled = false;
    adminFetch(url)
      .then((data) => {
        if (!cancelled) setResult({ key: `${url}#${version}`, data, error: "" });
      })
      .catch((err) => {
        if (!cancelled) {
          setResult((previous) => ({
            key: `${url}#${version}`,
            data: previous.data, // keep showing the last page on a transient error
            error: err instanceof Error ? err.message : "Erreur inconnue.",
          }));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [url, version]);

  const loadedKey = result.key;
  const reload = useCallback(() => setVersion((current) => current + 1), []);

  return { data: result.data, error: result.error, isLoading: loadedKey !== key, reload };
}
