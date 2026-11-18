// Document list state; polls every 2 seconds while any document is still 'processing'.
import { useCallback, useEffect, useState } from "react";
import { api, messageOf } from "../api/client";
import type { DocumentInfo } from "../types";

const POLL_MS = 2000;

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[] | null>(null); // null = not loaded yet
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await api.listDocuments());
      setError(null);
    } catch (err) {
      setError(messageOf(err));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const anyProcessing = documents?.some((document) => document.status === "processing") ?? false;
  useEffect(() => {
    if (!anyProcessing) return;
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [anyProcessing, refresh]);

  return { documents, error, refresh };
}
