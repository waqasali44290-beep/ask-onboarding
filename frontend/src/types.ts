// Shared TypeScript types matching the backend schemas (backend/app/schemas.py).

export interface User {
  id: number;
  username: string;
  display_name: string;
  role: "employee" | "manager" | "admin";
}

export type DocumentStatus = "processing" | "ready" | "failed";
export type Visibility = "everyone" | "managers";

export interface DocumentInfo {
  id: number;
  filename: string;
  mime_type: string;
  status: DocumentStatus;
  visibility: Visibility;
  error: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentInfo {
  full_text: string | null;
}

// One retrieved chunk the answer may cite as [n].
export interface Source {
  n: number;
  chunk_id: number;
  document_id: number;
  filename: string;
  content: string;
  start_char: number;
  end_char: number;
  page: number | null;
  score: number;
}

export type Rating = 1 | -1;

export interface AnswerLog {
  message_id: number;
  question: string;
  answer: string;
  user_name: string;
  created_at: string;
  latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cost_usd: number;
  no_answer: boolean;
  feedback: Rating | null;
}

export interface AdminStats {
  answers: number;
  no_answers: number;
  no_answer_rate: number;
  avg_latency_ms: number | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_cost_usd: number;
  thumbs_up: number;
  thumbs_down: number;
  tickets: Record<string, number>;
  recent: AnswerLog[];
}

export interface StoredMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: Source[];
  no_answer: boolean;
  feedback: Rating | null;
  created_at: string;
}

export interface Conversation {
  id: number;
  created_at: string;
  messages: StoredMessage[];
}

export interface DoneEvent {
  conversation_id: number;
  message_id: number;
  citations: Source[];
  no_answer: boolean;
}

// A message as the chat page shows it, including answers still streaming.
export type MessageStatus = "searching" | "thinking" | "streaming" | "done" | "no_answer" | "error";

export interface ChatMessage {
  key: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[]; // everything sent to the LLM, numbered like the [n] markers
  citations: Source[]; // the ones the answer actually cited
  status: MessageStatus;
  offerTicket: boolean; // only for live no-answer replies, not ones loaded from history
  messageId: number | null; // database id, known once the answer is saved
  feedback: Rating | null;
}

export type TicketStatus = "open" | "in_progress" | "resolved";

export interface Ticket {
  id: number;
  title: string;
  question: string;
  user_name: string;
  conversation_id: number | null;
  status: TicketStatus;
  response: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface ConversationSummary {
  id: number;
  title: string;
  updated_at: string;
  message_count: number;
}

export interface NewTicket {
  title: string;
  question: string;
  conversation_id: number | null;
}
