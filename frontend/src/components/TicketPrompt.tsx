// Shown on 'no answer': the assistant drafts a ticket; the user confirms or edits it.
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, messageOf } from "../api/client";
import type { Ticket } from "../types";
import { SparkleIcon } from "./Icons";

const NAME_KEY = "ask-onboarding.userName";

function readName(): string {
  try {
    return localStorage.getItem(NAME_KEY) ?? "";
  } catch {
    return "";
  }
}

interface Props {
  question: string;
  conversationId: number | null;
}

export default function TicketPrompt({ question, conversationId }: Props) {
  const [title, setTitle] = useState<string | null>(null); // null = still drafting
  const [name, setName] = useState(readName);
  const [editingName, setEditingName] = useState(() => !readName()); // ask only the first time
  const [state, setState] = useState<"ready" | "saving" | "declined">("ready");
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Ask the backend for a suggested ticket title as soon as the prompt appears.
  useEffect(() => {
    let cancelled = false;
    api
      .draftTicket(question)
      .then((draft) => !cancelled && setTitle(draft.title))
      .catch(() => !cancelled && setTitle(question)); // offline: suggest the question itself
    return () => {
      cancelled = true;
    };
  }, [question]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!title) return;
    setState("saving");
    setError(null);
    try {
      setTicket(
        await api.createTicket({
          title: title.trim(),
          question,
          user_name: name.trim(),
          conversation_id: conversationId,
        }),
      );
      try {
        localStorage.setItem(NAME_KEY, name.trim()); // remember for next time
      } catch {
        // storage blocked: the user just types their name again next time
      }
    } catch (err) {
      setError(messageOf(err));
      setState("ready");
    }
  }

  if (ticket) {
    return (
      <p className="ticket-prompt ticket-done" role="status">
        ✓ Ticket #{ticket.id} opened. <Link to="/tickets">View tickets</Link>
      </p>
    );
  }
  if (state === "declined") {
    return <p className="ticket-prompt muted">No ticket opened.</p>;
  }
  if (title === null) {
    return (
      <p className="ticket-prompt muted" role="status">
        <SparkleIcon /> Drafting a ticket for you…
      </p>
    );
  }

  return (
    <form className="ticket-prompt ticket-card" onSubmit={submit}>
      <label htmlFor="ticket-title" className="ticket-label">
        <SparkleIcon /> Suggested ticket — edit it if you like
      </label>
      <textarea
        id="ticket-title"
        className="input"
        rows={2}
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        maxLength={120}
        required
      />

      {editingName ? (
        <>
          <label htmlFor="ticket-name" className="ticket-label">
            Your name
          </label>
          <input
            id="ticket-name"
            className="input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            maxLength={100}
            autoComplete="name"
          />
        </>
      ) : (
        <p className="muted ticket-as">
          Opening as <strong>{name}</strong> ·{" "}
          <button type="button" className="link-button" onClick={() => setEditingName(true)}>
            change
          </button>
        </p>
      )}

      <div className="ticket-row">
        <button
          type="submit"
          className="button button-primary"
          disabled={state === "saving" || !title.trim() || !name.trim()}
        >
          {state === "saving" ? "Opening…" : "Create ticket"}
        </button>
        <button type="button" className="button button-quiet" onClick={() => setState("declined")}>
          No thanks
        </button>
      </div>
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
