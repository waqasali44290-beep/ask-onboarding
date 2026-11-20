// Admin page: usage, quality and cost numbers, plus a log of recent answers.
import { useCallback, useEffect, useState } from "react";
import { api, messageOf } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import type { AdminStats, AnswerLog, Gap } from "../types";

type Filter = "all" | "unhelpful" | "unanswered";

const FILTERS: { value: Filter; label: string; matches: (row: AnswerLog) => boolean }[] = [
  { value: "all", label: "All answers", matches: () => true },
  { value: "unhelpful", label: "👎 Not helpful", matches: (row) => row.feedback === -1 },
  { value: "unanswered", label: "Not in documents", matches: (row) => row.no_answer },
];

const seconds = (ms: number | null) => (ms === null ? "–" : `${(ms / 1000).toFixed(1)} s`);
const dollars = (usd: number) => (usd === 0 ? "$0" : `$${usd.toFixed(4)}`);

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [gaps, setGaps] = useState<Gap[] | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setStats(await api.adminStats());
      api.knowledgeGaps().then(setGaps).catch(() => setGaps([])); // slower: embeds the questions
    } catch (err) {
      setError(messageOf(err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!stats) return <LoadingState label="Loading stats…" />;

  const rows = stats.recent.filter(FILTERS.find((f) => f.value === filter)!.matches);
  const rated = stats.thumbs_up + stats.thumbs_down;

  return (
    <section className="page page-wide">
      <div className="page-header">
        <div>
          <h1>Admin</h1>
          <p className="muted">How the assistant is being used, how well it answers, and what it costs.</p>
        </div>
        <button type="button" className="button" onClick={load}>
          Refresh
        </button>
      </div>

      <div className="stat-grid">
        <Stat label="Answers given" value={String(stats.answers)} />
        <Stat
          label="Not in documents"
          value={`${Math.round(stats.no_answer_rate * 100)}%`}
          detail={`${stats.no_answers} questions`}
        />
        <Stat label="Average answer time" value={seconds(stats.avg_latency_ms)} />
        <Stat
          label="Helpful"
          value={rated ? `${Math.round((stats.thumbs_up / rated) * 100)}%` : "–"}
          detail={`👍 ${stats.thumbs_up} · 👎 ${stats.thumbs_down}`}
        />
        <Stat
          label="Tokens"
          value={(stats.prompt_tokens + stats.completion_tokens).toLocaleString()}
          detail={`${stats.prompt_tokens.toLocaleString()} in · ${stats.completion_tokens.toLocaleString()} out`}
        />
        <Stat label="LLM cost" value={dollars(stats.total_cost_usd)} detail="local model: free" />
        <Stat
          label="Open tickets"
          value={String((stats.tickets.open ?? 0) + (stats.tickets.in_progress ?? 0))}
          detail={`${stats.tickets.resolved ?? 0} resolved`}
        />
      </div>

      <h2>Knowledge gaps</h2>
      <p className="muted section-intro">
        What people asked that the documents don't cover, grouped by topic. Write a document for the top ones, or
        publish a ticket reply.
      </p>
      {gaps === null ? (
        <LoadingState label="Finding gaps…" />
      ) : gaps.length === 0 ? (
        <EmptyState title="No gaps found: every question had an answer 🎉" />
      ) : (
        <ol className="gaps">
          {gaps.map((gap, index) => (
            <li key={gap.topic} className="gap">
              <span className="gap-rank">{index + 1}</span>
              <div className="gap-text">
                <span className="filename">{gap.topic}</span>
                {gap.examples.length > 1 && (
                  <p className="muted">Also asked as: {gap.examples.slice(1).map((e) => `“${e}”`).join(", ")}</p>
                )}
              </div>
              <span className="gap-count">
                {gap.count} {gap.count === 1 ? "ask" : "asks"}
              </span>
            </li>
          ))}
        </ol>
      )}

      <h2>Recent answers</h2>
      <div className="tabs" role="tablist" aria-label="Filter answers">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            role="tab"
            aria-selected={filter === f.value}
            className={`tab${filter === f.value ? " tab-active" : ""}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label} <span className="tab-count">{stats.recent.filter(f.matches).length}</span>
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <EmptyState title="Nothing here yet" />
      ) : (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>When</th>
                <th>User</th>
                <th>Question → answer</th>
                <th className="numeric">Time</th>
                <th className="numeric">Tokens</th>
                <th className="numeric">Cost</th>
                <th>Rating</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.message_id}>
                  <td className="muted nowrap">{new Date(row.created_at).toLocaleString()}</td>
                  <td className="nowrap">{row.user_name}</td>
                  <td>
                    <span className="filename">{row.question}</span>
                    <p className={row.no_answer ? "muted" : undefined}>
                      {row.no_answer ? "Not in the documents" : row.answer}
                    </p>
                  </td>
                  <td className="numeric nowrap">{seconds(row.latency_ms)}</td>
                  <td className="numeric">
                    {row.prompt_tokens === null ? "–" : (row.prompt_tokens + (row.completion_tokens ?? 0)).toLocaleString()}
                  </td>
                  <td className="numeric">{dollars(row.cost_usd)}</td>
                  <td>{row.feedback === 1 ? "👍" : row.feedback === -1 ? "👎" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Stat({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="stat">
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
      {detail && <p className="stat-detail">{detail}</p>}
    </div>
  );
}
