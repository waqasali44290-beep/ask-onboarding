// Chat page: conversation sidebar, history, streaming answer, citations, ticket offer.
import { useEffect, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import CitationPanel from "../components/CitationPanel";
import ConversationSidebar from "../components/ConversationSidebar";
import { SendIcon } from "../components/Icons";
import MessageList from "../components/MessageList";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useChat } from "../hooks/useChat";
import { useConversations } from "../hooks/useConversations";
import { useDocuments } from "../hooks/useDocuments";
import type { ConversationSummary, Source } from "../types";

// Shown until documents have suggested questions of their own.
const FALLBACK_QUESTIONS = [
  "How many vacation days do new employees get?",
  "What should I do if my laptop is stolen?",
  "How do I get access to Jira from home?",
];

export default function ChatPage() {
  const { messages, send, busy, history, conversationId, openConversation, startNewConversation } = useChat();
  const { conversations, refresh: refreshConversations } = useConversations();
  const { documents } = useDocuments();
  const [draft, setDraft] = useState("");
  const [openSource, setOpenSource] = useState<Source | null>(null);
  const [examples, setExamples] = useState<string[]>(FALLBACK_QUESTIONS);
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    api
      .suggestions()
      .then((questions) => questions.length > 0 && setExamples(questions))
      .catch(() => {}); // keep the fallback questions
  }, []);

  const hasReadyDocuments = documents?.some((document) => document.status === "ready") ?? true;

  function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || busy) return;
    setDraft("");
    send(trimmed).then(refreshConversations); // a new conversation appears in the sidebar
  }

  // A link like /chat?ask=How%20do%20I... starts a new conversation with that question.
  const askFromLink = searchParams.get("ask");
  useEffect(() => {
    if (!askFromLink || history !== "ready" || busy) return;
    setSearchParams({}, { replace: true }); // only once, even if the page re-renders
    startNewConversation();
    ask(askFromLink);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run when the link or readiness changes
  }, [askFromLink, history]);

  async function deleteConversation(conversation: ConversationSummary) {
    if (!window.confirm(`Delete the conversation "${conversation.title}"?`)) return;
    try {
      await api.deleteConversation(conversation.id);
    } catch {
      // already gone or server down: the refresh below shows the real state
    }
    if (conversation.id === conversationId) startNewConversation();
    refreshConversations();
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    ask(draft);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter adds a new line.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      ask(draft);
    }
  }

  const lastAnswer = messages[messages.length - 1];
  const announcement =
    lastAnswer?.status === "done" ? "Answer ready." : lastAnswer?.status === "no_answer" ? "No answer found." : "";

  return (
    <div className="chat-layout">
      <ConversationSidebar
        conversations={conversations}
        activeId={conversationId}
        disabled={busy}
        onOpen={openConversation}
        onNew={startNewConversation}
        onDelete={deleteConversation}
      />

      <section className="chat-page">
        <div className="chat-scroll">
          {history === "loading" && <LoadingState label="Loading conversation…" />}
          {history === "error" && (
            <ErrorState
              message="Couldn't load this conversation."
              onRetry={() => conversationId !== null && openConversation(conversationId)}
            />
          )}
          {history === "ready" && messages.length === 0 && (
            <div className="welcome">
              <h1>How can I help you get started?</h1>
              <p className="muted">I answer from the company handbook, engineering wiki and IT guides — with sources.</p>
              {hasReadyDocuments ? (
                <div className="examples">
                  {examples.map((question) => (
                    <button key={question} type="button" className="example" onClick={() => ask(question)}>
                      {question}
                    </button>
                  ))}
                </div>
              ) : (
                <EmptyState title="No documents yet">
                  <p className="muted">
                    <Link to="/upload">Upload some documents</Link> first.
                  </p>
                </EmptyState>
              )}
            </div>
          )}
          <MessageList messages={messages} conversationId={conversationId} onCite={setOpenSource} onRetry={ask} onAsk={ask} />
        </div>

        {/* Screen readers hear one short update instead of every streamed word. */}
        <p className="visually-hidden" aria-live="polite">
          {announcement}
        </p>

        <form className="composer" onSubmit={handleSubmit}>
          <label htmlFor="question" className="visually-hidden">
            Your question
          </label>
          <textarea
            id="question"
            className="composer-input"
            rows={1}
            placeholder="Ask a question…"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            maxLength={2000}
          />
          <button
            type="submit"
            className="send-button"
            disabled={busy || !draft.trim()}
            aria-label={busy ? "Answering" : "Send"}
          >
            {busy ? <span className="spinner spinner-light" aria-hidden="true" /> : <SendIcon />}
          </button>
        </form>
        <p className="composer-hint muted">Enter to send · Shift+Enter for a new line · Answers can take up to a minute</p>
      </section>

      <CitationPanel source={openSource} onClose={() => setOpenSource(null)} />
    </div>
  );
}
