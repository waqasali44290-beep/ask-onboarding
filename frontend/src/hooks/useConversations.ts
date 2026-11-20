// Sidebar list of recent conversations.
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConversationSummary } from "../types";

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  const refresh = useCallback(async () => {
    try {
      setConversations(await api.listConversations());
    } catch {
      // The sidebar is optional: keep the last list rather than show an error.
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { conversations, refresh };
}
