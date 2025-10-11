import { useMemo } from "react";
import { SessionMessageRecord } from "../types";

interface Props {
  messages: SessionMessageRecord[];
}

export function SessionHistoryCompact({ messages }: Props) {
  const items = useMemo(() => (messages || []).slice(-50), [messages]);
  return (
    <div className="panel" style={{ padding: "0.75rem 0.9rem" }}>
      <div className="section-header" style={{ marginBottom: 6 }}>
        <span>Session History</span>
      </div>
      <select
        aria-label="Recent session messages"
        style={{ width: "100%", padding: 8, borderRadius: 10, background: "#0f172a", color: "#e5e7eb", border: "1px solid rgba(148,163,184,0.3)" }}
      >
        {items.length === 0 && <option>No messages yet</option>}
        {items.map((m, idx) => {
          const when = new Date(m.ts * 1000).toLocaleTimeString();
          const text = (m.text || "").replace(/\s+/g, " ").slice(0, 80);
          return (
            <option key={idx} title={new Date(m.ts * 1000).toLocaleString()}>
              {when} · {m.role}: {text}
            </option>
          );
        })}
      </select>
    </div>
  );
}
