// Renders the conversation history and keeps the newest message in view.
import { useEffect, useRef } from "react";
import { useUser } from "../auth";
import type { ChatMessage, Source } from "../types";
import Avatar from "./Avatar";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  conversationId: number | null;
  onCite: (source: Source) => void;
  onRetry: (question: string) => void;
  onAsk: (question: string) => void;
}

export default function MessageList({ messages, conversationId, onCite, onRetry, onAsk }: Props) {
  const user = useUser();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  return (
    <>
      <ol className="messages">
        {messages.map((message, index) => (
          <li key={message.key} className={`message message-${message.role}`}>
            <Avatar name={user.display_name} assistant={message.role === "assistant"} />
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
