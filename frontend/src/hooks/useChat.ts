// Chat state: messages, streaming status and the current conversation.
// The conversation id is kept in localStorage so the history survives a page reload.
import { useEffect, useState } from "react";
import { api } from "../api/client";
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
  };
}

let nextKey = 0;
const newKey = () => `local-${nextKey++}`;

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(readStoredId);
  const [history, setHistory] = useState<"loading" | "ready" | "error">(conversationId ? "loading" : "ready");

  // Load the saved conversation once, when the page opens.
  useEffect(() => {
    const id = readStoredId();
    if (id === null) return;
    api
      .getConversation(id)
      .then((conversation) => {
        setMessages(conversation.messages.map(fromStored));
        setHistory("ready");
      })
      .catch((err) => {
        if (err.status === 404) {
          // conversation was deleted (e.g. database reset): start a new one
          storeId(null);
          setConversationId(null);
          setHistory("ready");
        } else {
          setHistory("error");
        }
      });
  }, []);

  const busy = messages.some((m) => ["searching", "thinking", "streaming"].includes(m.status));

  function update(key: string, change: (message: ChatMessage) => Partial<ChatMessage>) {
    setMessages((previous) => previous.map((m) => (m.key === key ? { ...m, ...change(m) } : m)));
  }

  async function send(question: string) {
    const answerKey = newKey();
    setMessages((previous) => [
      ...previous,
      { key: newKey(), role: "user", content: question, sources: [], citations: [], status: "done", offerTicket: false },
      { key: answerKey, role: "assistant", content: "", sources: [], citations: [], status: "searching", offerTicket: false },
    ]);

    await streamChat(question, conversationId, {
      onSources: (sources) => update(answerKey, () => ({ sources, status: "thinking" })),
      onToken: (text) => update(answerKey, (m) => ({ content: m.content + text, status: "streaming" })),
      onNoAnswer: (message) => update(answerKey, () => ({ content: message, status: "no_answer", offerTicket: true })),
      onDone: (done) => {
        setConversationId(done.conversation_id);
        storeId(done.conversation_id);
        update(answerKey, () => ({ citations: done.citations, status: done.no_answer ? "no_answer" : "done" }));
      },
      onError: (message) => update(answerKey, () => ({ content: message, status: "error" })),
    });
  }

  function startNewConversation() {
    setMessages([]);
    setConversationId(null);
    storeId(null);
  }

  return { messages, send, busy, history, conversationId, startNewConversation };
}
