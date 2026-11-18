// Chat page: conversation history, streaming answer, citations, "create ticket?" prompt.
import { useState, type FormEvent, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import CitationPanel from "../components/CitationPanel";
import MessageList from "../components/MessageList";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useChat } from "../hooks/useChat";
import { useDocuments } from "../hooks/useDocuments";
import type { Source } from "../types";

const EXAMPLE_QUESTIONS = [
  "How many vacation days do new employees get?",
  "What should I do if my laptop is stolen?",
  "How do I get access to Jira from home?",
];

export default function ChatPage() {
  const { messages, send, busy, history, conversationId, startNewConversation } = useChat();
  const { documents } = useDocuments();
  const [draft, setDraft] = useState("");
  const [openSource, setOpenSource] = useState<Source | null>(null);

  const hasReadyDocuments = documents?.some((document) => document.status === "ready") ?? true;

  function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || busy) return;
    setDraft("");
    send(trimmed);
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
    <section className="page chat-page">
      <header className="chat-header">
        <h1>Ask Onboarding</h1>
        {messages.length > 0 && (
          <button type="button" className="button button-quiet" onClick={startNewConversation} disabled={busy}>
            New conversation
          </button>
        )}
      </header>

      <div className="chat-scroll">
        {history === "loading" && <LoadingState label="Loading your conversation…" />}
        {history === "error" && (
          <ErrorState message="Couldn't load your previous conversation." onRetry={() => window.location.reload()} />
        )}
        {history === "ready" && messages.length === 0 && (
          <EmptyState title="Ask anything about the company handbook, wiki or IT guides">
            {hasReadyDocuments ? (
              <div className="examples">
                {EXAMPLE_QUESTIONS.map((question) => (
                  <button key={question} type="button" className="button" onClick={() => ask(question)}>
                    {question}
                  </button>
                ))}
              </div>
            ) : (
              <p className="muted">
                There are no documents yet. <Link to="/upload">Upload some documents</Link> first.
              </p>
            )}
          </EmptyState>
        )}
        <MessageList messages={messages} conversationId={conversationId} onCite={setOpenSource} onRetry={ask} />
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
          className="input"
          rows={2}
          placeholder="Ask a question… (Enter to send, Shift+Enter for a new line)"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={2000}
        />
        <button type="submit" className="button button-primary" disabled={busy || !draft.trim()}>
          {busy ? "Answering…" : "Send"}
        </button>
      </form>

      <CitationPanel source={openSource} onClose={() => setOpenSource(null)} />
    </section>
  );
}
