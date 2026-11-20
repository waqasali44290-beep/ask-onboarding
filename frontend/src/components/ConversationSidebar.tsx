// List of recent conversations: open one, start a new one, or delete one.
import type { ConversationSummary } from "../types";
import { PlusIcon, TrashIcon } from "./Icons";

interface Props {
  conversations: ConversationSummary[];
  activeId: number | null;
  disabled: boolean; // while an answer is streaming
  onOpen: (id: number) => void;
  onNew: () => void;
  onDelete: (conversation: ConversationSummary) => void;
}

export default function ConversationSidebar({ conversations, activeId, disabled, onOpen, onNew, onDelete }: Props) {
  return (
    <aside className="sidebar" aria-label="Conversations">
      <button type="button" className="button button-primary sidebar-new" onClick={onNew} disabled={disabled}>
        <PlusIcon /> New chat
      </button>
      {conversations.length === 0 ? (
        <p className="sidebar-empty muted">Your conversations will appear here.</p>
      ) : (
        <ul className="sidebar-list">
          {conversations.map((conversation) => (
            <li key={conversation.id} className={conversation.id === activeId ? "active" : undefined}>
              <button
                type="button"
                className="sidebar-item"
                onClick={() => onOpen(conversation.id)}
                disabled={disabled}
                aria-current={conversation.id === activeId ? "true" : undefined}
              >
                <span className="sidebar-title">{conversation.title}</span>
                <span className="sidebar-date">{new Date(conversation.updated_at).toLocaleDateString()}</span>
              </button>
              <button
                type="button"
                className="icon-button"
                onClick={() => onDelete(conversation)}
                disabled={disabled}
                aria-label={`Delete conversation: ${conversation.title}`}
              >
                <TrashIcon />
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
