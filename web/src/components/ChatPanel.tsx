import { ChangeEvent, FormEvent } from "react";
import { ChatMessage } from "../types";

interface ChatAction {
  label: string;
  onClick: () => void | Promise<void>;
  disabled?: boolean;
  variant?: "primary" | "secondary";
}

interface ChatPanelProps {
  messages: ChatMessage[];
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => Promise<void> | void;
  sending: boolean;
  actions: ChatAction[];
  confluenceParentId: string;
  onConfluenceParentIdChange: (value: string) => void;
  asanaProjectId: string;
  onAsanaProjectIdChange: (value: string) => void;
  publishUrl?: string | null;
  qaSummary?: string | null;
  asanaStatus?: string | null;
  statusMessage?: string | null;
  errorMessage?: string | null;
  disabled?: boolean;
}

export function ChatPanel({
  messages,
  input,
  onInputChange,
  onSend,
  sending,
  actions,
  confluenceParentId,
  onConfluenceParentIdChange,
  asanaProjectId,
  onAsanaProjectIdChange,
  publishUrl,
  qaSummary,
  asanaStatus,
  statusMessage,
  errorMessage,
  disabled,
}: ChatPanelProps) {
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim() || sending || disabled) {
      return;
    }
    await onSend();
  };

  return (
    <div className="panel">
      <h2>Chat & Actions</h2>

      {errorMessage && <div className="error-banner">{errorMessage}</div>}
      {statusMessage && <div className="success-banner">{statusMessage}</div>}

      <section>
        <label htmlFor="confluence-parent">Confluence Parent Page</label>
        <input
          id="confluence-parent"
          type="text"
          placeholder="Optional parent page ID"
          value={confluenceParentId}
          onChange={(event: ChangeEvent<HTMLInputElement>) =>
            onConfluenceParentIdChange(event.target.value)
          }
        />
      </section>

      <section>
        <label htmlFor="asana-project">Asana Project ID</label>
        <input
          id="asana-project"
          type="text"
          placeholder="asana-project-gid"
          value={asanaProjectId}
          onChange={(event: ChangeEvent<HTMLInputElement>) =>
            onAsanaProjectIdChange(event.target.value)
          }
        />
      </section>

      <section className="action-grid">
        {actions.map((action) => (
          <button
            key={action.label}
            type="button"
            className={action.variant === "secondary" ? "secondary" : ""}
            onClick={() => action.onClick()}
            disabled={action.disabled || disabled}
          >
            {action.label}
          </button>
        ))}
      </section>

      {publishUrl && (
        <div className="success-banner">
          Published to Confluence: 
          <button
            type="button"
            className="link-button"
            onClick={() => window.open(publishUrl, "_blank", "noopener")}
          >
            Open Page ↗
          </button>
        </div>
      )}

    {qaSummary && <div className="success-banner">QA: {qaSummary}</div>}
    {asanaStatus && <div className="success-banner">Asana: {asanaStatus}</div>}

      <div className="chat-messages">
        {messages.length === 0 ? (
          <span className="small">No messages yet. Ask the planner to update sections.</span>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`chat-message ${message.role}`}>
              <div className="small" style={{ marginBottom: "0.35rem" }}>
                {new Date(message.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })} – {message.role === "assistant" ? "Planner" : "You"}
              </div>
              <div>{message.content}</div>
            </div>
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} style={{ marginTop: "0.75rem" }}>
        <label htmlFor="chat-message">Chat with Planner</label>
        <textarea
          id="chat-message"
          placeholder="Capture latest fixture updates, decisions, or TODOs that need to roll into the plan."
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          disabled={disabled}
        />
        <button type="submit" disabled={sending || disabled} style={{ marginTop: "0.75rem" }}>
          {sending ? "Sending…" : "Send Message"}
        </button>
      </form>
    </div>
  );
}
