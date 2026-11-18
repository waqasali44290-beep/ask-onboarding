// Tickets page: table of help-desk tickets created from unanswered questions.
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageOf } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import type { Ticket } from "../types";

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setTickets(await api.listTickets());
    } catch (err) {
      setError(messageOf(err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <section className="page">
      <h1>Help-desk tickets</h1>
      <p className="muted">Questions the assistant couldn't answer from the documents, sent to the help desk.</p>

      {error && <ErrorState message={error} onRetry={load} />}
      {!error && tickets === null && <LoadingState label="Loading tickets…" />}
      {tickets?.length === 0 && (
        <EmptyState title="No tickets yet">
          <p className="muted">
            When the assistant can't answer a question in <Link to="/chat">Chat</Link>, it offers to open one.
          </p>
        </EmptyState>
      )}
      {tickets && tickets.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th className="numeric">#</th>
              <th>Question</th>
              <th>From</th>
              <th>Status</th>
              <th>Opened</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((ticket) => (
              <tr key={ticket.id}>
                <td className="numeric">{ticket.id}</td>
                <td>
                  <span className="filename">{ticket.title}</span>
                  {ticket.title !== ticket.question && <p className="muted">{ticket.question}</p>}
                </td>
                <td>{ticket.user_name}</td>
                <td>
                  <span className="badge badge-open">{ticket.status}</span>
                </td>
                <td className="muted">{new Date(ticket.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
