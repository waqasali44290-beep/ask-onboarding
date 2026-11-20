// All fetch calls to /api in one place. Streaming chat lives in stream.ts.
import type { AdminStats, Conversation, ConversationSummary, DocumentDetail, DocumentInfo, NewTicket, Ticket, Rating, TicketStatus, User, Visibility } from "../types";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

/** Fired on window when the API answers 401, so the app can show the login page. */
export const AUTH_EXPIRED_EVENT = "auth-expired";

export const SERVER_UNREACHABLE = "Can't reach the server. Check that the app is running (docker compose up).";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(SERVER_UNREACHABLE, 0); // network error, not an HTTP status
  }
  if (response.status === 401 && !path.startsWith("/auth/")) {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

/** Turn a FastAPI error body into a sentence a user can read. */
export async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    // 422 validation errors: a list of {msg, loc, ...}
    if (Array.isArray(body.detail)) return body.detail.map((item: { msg: string }) => item.msg).join(". ");
  } catch {
    // body wasn't JSON (e.g. an nginx error page); fall through to the generic message
  }
  return `Something went wrong (error ${response.status}). Please try again.`;
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  adminStats: () => request<AdminStats>("/admin/stats"),
  login: (username: string, password: string) => request<User>("/auth/login", json({ username, password })),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: () => request<User>("/auth/me"),
  listDocuments: () => request<DocumentInfo[]>("/documents"),
  getDocument: (id: number) => request<DocumentDetail>(`/documents/${id}`),
  uploadDocument: (file: File, visibility: Visibility) => {
    const body = new FormData();
    body.append("file", file);
    body.append("visibility", visibility);
    return request<DocumentInfo>("/documents", { method: "POST", body });
  },
  deleteDocument: (id: number) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  updateDocument: (id: number, visibility: Visibility) =>
    request<DocumentInfo>(`/documents/${id}`, { ...json({ visibility }), method: "PATCH" }),
  listConversations: () => request<ConversationSummary[]>("/conversations"),
  getConversation: (id: number) => request<Conversation>(`/conversations/${id}`),
  deleteConversation: (id: number) => request<void>(`/conversations/${id}`, { method: "DELETE" }),
  rateAnswer: (messageId: number, rating: Rating | 0) =>
    request<void>(`/messages/${messageId}/feedback`, json({ rating })),
  listTickets: () => request<Ticket[]>("/tickets"),
  draftTicket: (question: string) => request<{ title: string }>("/tickets/draft", json({ question })),
  createTicket: (ticket: NewTicket) => request<Ticket>("/tickets", json(ticket)),
  updateTicket: (id: number, change: { status?: TicketStatus; response?: string }) =>
    request<Ticket>(`/tickets/${id}`, { ...json(change), method: "PATCH" }),
};
