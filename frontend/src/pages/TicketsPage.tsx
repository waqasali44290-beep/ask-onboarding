// Tickets page. Employees: their own tickets, the help desk's reply, "mark as solved".
// Admins: every ticket, filter by status, change status and write a reply.
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageOf } from "../api/client";
import { useUser } from "../auth";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import type { Ticket, TicketStatus } from "../types";

const STATUS_LABELS: Record<TicketStatus, string> = { open: "Open", in_progress: "In progress", resolved: "Resolved" };
const FILTERS: (TicketStatus | "all")[] = ["all", "open", "in_progress", "resolved"];

export default function TicketsPage() {
  const user = useUser();
  const isAdmin = user.role === "admin";
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<TicketStatus | "all">(isAdmin ? "open" : "all");

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

  function replace(updated: Ticket) {
    setTickets((current) => current?.map((ticket) => (ticket.id === updated.id ? updated : ticket)) ?? null);
  }

  const count = (status: TicketStatus | "all") =>
    tickets?.filter((ticket) => status === "all" || ticket.status === status).length ?? 0;
  const shown = tickets?.filter((ticket) => filter === "all" || ticket.status === filter) ?? [];

  return (
    <section className="page">
      <h1>{isAdmin ? "Help-desk tickets" : "My tickets"}</h1>
      <p className="muted">
        {isAdmin
          ? "Questions employees couldn't answer from the documents. Reply, then mark them resolved."
          : "Questions you sent to the help desk. Their reply appears here."}
      </p>

      {tickets && tickets.length > 0 && (
        <div className="tabs" role="tablist" aria-label="Filter by status">
          {FILTERS.map((status) => (
            <button
              key={status}
              type="button"
              role="tab"
              aria-selected={filter === status}
              className={`tab${filter === status ? " tab-active" : ""}`}
              onClick={() => setFilter(status)}
            >
              {status === "all" ? "All" : STATUS_LABELS[status]} <span className="tab-count">{count(status)}</span>
            </button>
          ))}
        </div>
      )}

      {error && <ErrorState message={error} onRetry={load} />}
      {!error && tickets === null && <LoadingState label="Loading tickets…" />}
      {tickets?.length === 0 && (
        <EmptyState title="No tickets yet">
          <p className="muted">
            When the assistant can't answer a question in <Link to="/chat">Chat</Link>, it offers to open one.
          </p>
        </EmptyState>
      )}
      {tickets && tickets.length > 0 && shown.length === 0 && <EmptyState title="Nothing here" />}

      <ul className="ticket-list">
        {shown.map((ticket) => (
          <li key={ticket.id}>
            <TicketCard ticket={ticket} isAdmin={isAdmin} onChange={replace} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function TicketCard({ ticket, isAdmin, onChange }: { ticket: Ticket; isAdmin: boolean; onChange: (t: Ticket) => void }) {
  const [status, setStatus] = useState<TicketStatus>(ticket.status);
  const [response, setResponse] = useState(ticket.response ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(change: { status?: TicketStatus; response?: string }) {
    setSaving(true);
    setError(null);
    try {
      onChange(await api.updateTicket(ticket.id, change));
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setSaving(false);
    }
  }

  const changed = status !== ticket.status || response.trim() !== (ticket.response ?? "");

  return (
    <article className="ticket">
      <header className="ticket-header">
        <div>
          <h2 className="ticket-title">
            <span className="muted">#{ticket.id}</span> {ticket.title}
          </h2>
          <p className="muted ticket-meta">
            {isAdmin && <>{ticket.user_name} · </>}
            opened {new Date(ticket.created_at).toLocaleString()}
            {ticket.resolved_at && <> · resolved {new Date(ticket.resolved_at).toLocaleString()}</>}
          </p>
        </div>
        <span className={`badge badge-${ticket.status}`}>{STATUS_LABELS[ticket.status]}</span>
      </header>

      {ticket.title !== ticket.question && <p className="ticket-question">“{ticket.question}”</p>}

      {isAdmin ? (
        <div className="ticket-admin">
          <label htmlFor={`response-${ticket.id}`} className="ticket-label">
            Reply to {ticket.user_name}
          </label>
          <textarea
            id={`response-${ticket.id}`}
            className="input"
            rows={2}
            value={response}
            onChange={(event) => setResponse(event.target.value)}
            placeholder="Write the answer the employee will see…"
          />
          <div className="ticket-row">
            <select
              className="input select"
              value={status}
              onChange={(event) => setStatus(event.target.value as TicketStatus)}
              aria-label="Status"
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="button button-primary"
              disabled={saving || !changed}
              onClick={() => save({ status, response: response.trim() })}
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      ) : (
        <>
          {ticket.response ? (
            <div className="ticket-response">
              <p className="ticket-label">Help desk reply</p>
              <p>{ticket.response}</p>
            </div>
          ) : (
            <p className="muted ticket-waiting">Waiting for the help desk to reply.</p>
          )}
          {ticket.status !== "resolved" && (
            <button type="button" className="button" disabled={saving} onClick={() => save({ status: "resolved" })}>
              {saving ? "Saving…" : "Mark as solved"}
            </button>
          )}
        </>
      )}
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
    </article>
  );
}
