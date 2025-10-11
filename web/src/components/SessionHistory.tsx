import { useMemo, useState } from "react";
import { SessionMessageRecord } from "../types";

interface SessionHistoryProps {
  messages: SessionMessageRecord[];
  onRename?: (newName: string) => Promise<void> | void;
  currentName?: string | null;
}

export function SessionHistory({ messages, onRename, currentName }: SessionHistoryProps) {
  const [name, setName] = useState<string>(currentName || "");
  const sorted = useMemo(() => (messages || []).slice(-50), [messages]);
  return (
    <div className="panel">
      <div className="section-header">
        <span>Session History</span>
      </div>
      {onRename && (
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
          <input
            type="text"
            placeholder="Session name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button type="button" onClick={() => onRename(name)} disabled={!name.trim()}>
            Rename
          </button>
        </div>
      )}
      <div className="chat-log" style={{ maxHeight: 240, overflow: "auto" }}>
        {sorted.length === 0 && <div className="small" style={{ opacity: 0.7 }}>No messages yet.</div>}
        {sorted.map((m, idx) => (
          <div key={idx} className="chat-message" style={{ marginBottom: 6 }}>
            <div className="small" style={{ opacity: 0.7 }}>
              {new Date(m.ts * 1000).toLocaleString()} — {m.role}
            </div>
            <div>{m.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
