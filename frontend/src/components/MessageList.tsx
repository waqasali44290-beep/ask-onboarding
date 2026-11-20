// Renders the conversation history and keeps the newest message in view.
import { useEffect, useRef } from "react";
import type { ChatMessage, Source } from "../types";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  conversationId: number | null;
  onCite: (source: Source) => void;
  onRetry: (question: string) => void;
  onAsk: (question: string) => void;
}

export default function MessageList({ messages, conversationId, onCite, onRetry, onAsk }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  return (
    <>
      <ol className="messages">
        {messages.map((message, index) => (
          <li key={message.key} className={`message message-${message.role}`}>
            <MessageBubble
              message={message}
              // Assistant messages always follow the user question they answer.
              question={messages[index - 1]?.content ?? ""}
              conversationId={conversationId}
              onCite={onCite}
              onRetry={onRetry}
              onAsk={onAsk}
              isLast={index === messages.length - 1}
            />
          </li>
        ))}
      </ol>
      <div ref={endRef} />
    </>
  );
}
