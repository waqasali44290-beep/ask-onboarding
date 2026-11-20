// Chat state: messages, streaming status and the current conversation.
// The conversation id is kept in localStorage so the history survives a page reload.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import { streamChat } from "../api/stream";
import type { ChatMessage, StoredMessage } from "../types";

const STORAGE_KEY = "ask-onboarding.conversationId";

function readStoredId(): number | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value ? Number(value) : null;
  } catch {
    return null; // storage blocked (private mode etc.): just start fresh
  }
}

function storeId(id: number | null) {
  try {
    if (id === null) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, String(id));
  } catch {
    // not critical: history just won't survive a reload
  }
}

function fromStored(message: StoredMessage): ChatMessage {
  return {
    key: `db-${message.id}`,
    role: message.role,
    content: message.content,
    sources: message.citations,
    citations: message.citations,
    status: message.no_answer ? "no_answer" : "done",
    offerTicket: false,
    messageId: message.id,
    feedback: message.feedback,
    suggestions: [],
    spoken: false,
  };
}

let nextKey = 0;
const newKey = () => `local-${nextKey++}`;

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(readStoredId);
  // The same id in a ref: state updates only apply on the next render, but send() may run
  // right after startNewConversation() (e.g. "Ask the assistant" links) and must see the new value.
  const currentId = useRef<number | null>(conversationId);
  const setId = (id: number | null) => {
    currentId.current = id;
    setConversationId(id);
  };
  const [history, setHistory] = useState<"loading" | "ready" | "error">(conversationId ? "loading" : "ready");

  const requestedId = useRef<number | null>(null); // ignore a slow load if the user already switched again

  const openConversation = useCallback(async (id: number) => {
    requestedId.current = id;
    setId(id);
    storeId(id);
    setMessages([]);
    setHistory("loading");
    try {
      const conversation = await api.getConversation(id);
      if (requestedId.current !== id) return;
      setMessages(conversation.messages.map(fromStored));
      setHistory("ready");
    } catch (err) {
      if (requestedId.current !== id) return;
      if (err instanceof ApiError && err.status === 404) {
        // conversation was deleted (e.g. database reset): start a new one
        storeId(null);
        setId(null);
        setHistory("ready");
      } else {
        setHistory("error");
      }
    }
  }, []);

  // Reopen the last conversation when the page loads.
  useEffect(() => {
    const id = readStoredId();
    if (id !== null) openConversation(id);
  }, [openConversation]);

  const busy = messages.some((m) => ["searching", "thinking", "streaming"].includes(m.status));

  function update(key: string, change: (message: ChatMessage) => Partial<ChatMessage>) {
    setMessages((previous) => previous.map((m) => (m.key === key ? { ...m, ...change(m) } : m)));
  }

  async function send(question: string, spoken = false) {
    const answerKey = newKey();
    setMessages((previous) => [
      ...previous,
      { key: newKey(), role: "user", content: question, sources: [], citations: [], status: "done", offerTicket: false, messageId: null, feedback: null, suggestions: [], spoken },
      { key: answerKey, role: "assistant", content: "", sources: [], citations: [], status: "searching", offerTicket: false, messageId: null, feedback: null, suggestions: [], spoken },
    ]);

    await streamChat(question, currentId.current, {
      onSources: (sources) => update(answerKey, () => ({ sources, status: "thinking" })),
      onToken: (text) => update(answerKey, (m) => ({ content: m.content + text, status: "streaming" })),
      onNoAnswer: (message) => update(answerKey, () => ({ content: message, status: "no_answer", offerTicket: true })),
      onDone: (done) => {
        setId(done.conversation_id);
        storeId(done.conversation_id);
        update(answerKey, () => ({
          citations: done.citations,
          status: done.no_answer ? "no_answer" : "done",
          messageId: done.message_id,
          suggestions: done.suggestions,
        }));
      },
      onError: (message) => update(answerKey, () => ({ content: message, status: "error" })),
    });
  }

  function startNewConversation() {
    requestedId.current = null;
    setHistory("ready");
    setMessages([]);
    setId(null);
    storeId(null);
  }

  return { messages, send, busy, history, conversationId, openConversation, startNewConversation };
}
