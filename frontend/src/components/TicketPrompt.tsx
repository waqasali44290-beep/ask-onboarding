// Shown on 'no answer': offers to open a help-desk ticket for the question.
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, messageOf } from "../api/client";
import type { Ticket } from "../types";

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
  const [name, setName] = useState(readName);
  const [state, setState] = useState<"asking" | "saving" | "declined">("asking");
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setState("saving");
    setError(null);
    try {
      setTicket(await api.createTicket({ question, user_name: name.trim(), conversation_id: conversationId }));
      try {
        localStorage.setItem(NAME_KEY, name.trim()); // remember for next time
      } catch {
        // storage blocked: the user just types their name again next time
      }
    } catch (err) {
      setError(messageOf(err));
      setState("asking");
    }
  }

  if (ticket) {
    return (
      <p className="ticket-prompt" role="status">
        ✓ Ticket #{ticket.id} opened. <Link to="/tickets">View tickets</Link>
      </p>
    );
  }
  if (state === "declined") {
    return <p className="ticket-prompt muted">No ticket opened.</p>;
  }

  return (
    <form className="ticket-prompt" onSubmit={submit}>
      <label htmlFor="ticket-name">Your name</label>
      <div className="ticket-row">
        <input
          id="ticket-name"
          className="input"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          maxLength={100}
          autoComplete="name"
        />
        <button type="submit" className="button button-primary" disabled={state === "saving" || !name.trim()}>
          {state === "saving" ? "Opening…" : "Yes, open a ticket"}
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
