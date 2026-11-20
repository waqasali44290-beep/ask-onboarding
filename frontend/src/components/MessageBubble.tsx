// One message; turns [1], [2] markers into clickable citation chips.
import type { ReactNode } from "react";
import type { ChatMessage, Source } from "../types";
import FeedbackButtons from "./FeedbackButtons";
import { ErrorState, LoadingState } from "./States";
import TicketPrompt from "./TicketPrompt";

interface Props {
  message: ChatMessage;
  question: string; // the user question this message answers
  conversationId: number | null;
  onCite: (source: Source) => void;
  onRetry: (question: string) => void;
  onAsk: (question: string) => void;
  isLast: boolean; // related questions only under the newest answer
}

export default function MessageBubble({ message, question, conversationId, onCite, onRetry, onAsk, isLast }: Props) {
  if (message.role === "user") {
    return <div className="bubble bubble-user">{message.content}</div>;
  }

  switch (message.status) {
    case "searching":
      return <LoadingState label="Searching the documents…" />;
    case "thinking":
      return (
        <LoadingState
          label={`Reading ${message.sources.length} source${message.sources.length === 1 ? "" : "s"}… the local model can take up to a minute.`}
        />
      );
    case "error":
      return <ErrorState message={message.content} onRetry={() => onRetry(question)} />;
    case "no_answer":
      return (
        <div className="bubble bubble-assistant bubble-no-answer">
          <p>{message.content}</p>
          {message.offerTicket && <TicketPrompt question={question} conversationId={conversationId} />}
        </div>
      );
    default:
      return (
        <div className="bubble bubble-assistant">
          <p className="answer">
            {withCitations(message.content, message.sources, onCite)}
            {message.status === "streaming" && <span className="caret" aria-hidden="true" />}
          </p>
          {message.status === "done" && message.citations.length > 0 && (
            <SourceList citations={message.citations} onCite={onCite} />
          )}
          {message.status === "done" && message.messageId !== null && (
            <FeedbackButtons
              messageId={message.messageId}
              initial={message.feedback}
              text={message.content}
              autoSpeak={message.spoken}
            />
          )}
          {isLast && message.suggestions.length > 0 && (
            <div className="related">
              <p className="sources-title">Related questions</p>
              {message.suggestions.map((suggestion) => (
                <button key={suggestion} type="button" className="related-question" onClick={() => onAsk(suggestion)}>
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>
      );
  }
}

/** Split "text [1] more [2]" into text and citation buttons. Unknown numbers stay plain text. */
function withCitations(text: string, sources: Source[], onCite: (source: Source) => void): ReactNode[] {
  return text.split(/(\[\d+\])/).map((part, index) => {
    const number = part.match(/^\[(\d+)\]$/)?.[1];
    const source = number ? sources.find((s) => s.n === Number(number)) : undefined;
    if (!source) return part;
    return (
      <button
        key={index}
        type="button"
        className="cite"
        onClick={() => onCite(source)}
        aria-label={`Source ${source.n}: ${source.filename}`}
      >
        {source.n}
      </button>
    );
  });
}

function SourceList({ citations, onCite }: { citations: Source[]; onCite: (source: Source) => void }) {
  return (
    <div className="sources">
      <p className="sources-title">Sources</p>
      <ul>
        {citations.map((source) => (
          <li key={source.chunk_id}>
            <button type="button" className="source-link" onClick={() => onCite(source)}>
              <span className="cite" aria-hidden="true">
                {source.n}
              </span>
              <span className="filename">{source.filename}</span>
              {source.page !== null && <span className="muted"> · page {source.page}</span>}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
