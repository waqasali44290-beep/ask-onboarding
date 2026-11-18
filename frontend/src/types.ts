// Shared TypeScript types matching the backend schemas (backend/app/schemas.py).

export type DocumentStatus = "processing" | "ready" | "failed";

export interface DocumentInfo {
  id: number;
  filename: string;
  mime_type: string;
  status: DocumentStatus;
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

export interface StoredMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: Source[];
  no_answer: boolean;
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
}

export interface Ticket {
  id: number;
  title: string;
  question: string;
  user_name: string;
  conversation_id: number | null;
  status: string;
  created_at: string;
}

export interface NewTicket {
  question: string;
  user_name: string;
  conversation_id: number | null;
}
