// Reads the Server-Sent Events stream from POST /api/chat and calls a handler per event.
// (The browser's EventSource only supports GET, so we parse the stream from fetch ourselves.)
import type { DoneEvent, Source } from "../types";
import { SERVER_UNREACHABLE, errorMessage } from "./client";

export interface ChatHandlers {
  onSources: (sources: Source[]) => void;
  onToken: (text: string) => void;
  onNoAnswer: (message: string) => void;
  onDone: (done: DoneEvent) => void;
  onError: (message: string) => void;
}

export async function streamChat(question: string, conversationId: number | null, handlers: ChatHandlers) {
  let response: Response;
  try {
    response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, conversation_id: conversationId }),
    });
  } catch {
    handlers.onError(SERVER_UNREACHABLE);
    return;
  }
  if (!response.ok || !response.body) {
    handlers.onError(await errorMessage(response));
    return;
  }

  let finished = false; // true once we receive "done" or "error"
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;
      // Events end with a blank line. A network chunk can stop mid-event,
      // so the last (possibly incomplete) piece stays in the buffer.
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const block of events) {
        finished = dispatch(block, handlers) || finished;
      }
    }
  } catch {
    // connection dropped mid-stream; reported below
  }
  if (!finished) handlers.onError("The connection was lost before the answer finished. Please try again.");
}

/** Handle one "event: name\ndata: {json}" block. Returns true for the final event. */
function dispatch(block: string, handlers: ChatHandlers): boolean {
  let name = "";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) name = line.slice("event: ".length);
    else if (line.startsWith("data: ")) data += line.slice("data: ".length);
  }
  if (!data) return false;
  const payload = JSON.parse(data);

  switch (name) {
    case "sources":
      handlers.onSources(payload.sources);
      return false;
    case "token":
      handlers.onToken(payload.text);
      return false;
    case "no_answer":
      handlers.onNoAnswer(payload.message);
      return false;
    case "done":
      handlers.onDone(payload);
      return true;
    case "error":
      handlers.onError(payload.message);
      return true;
    default:
      return false;
  }
}
