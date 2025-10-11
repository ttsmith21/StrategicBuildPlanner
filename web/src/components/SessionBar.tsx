import { useMemo } from "react";
import { SessionRecord } from "../types";

interface SessionBarProps {
  sessions: SessionRecord[];
  currentSessionId?: string | null;
  onResume: (sessionId: string) => void;
}

export function SessionBar({ sessions, currentSessionId, onResume }: SessionBarProps) {
  const recent = useMemo(() => (sessions || []).slice(0, 8), [sessions]);
  if (!recent || recent.length === 0) {
    return null;
  }
  return (
    <div className="panel" style={{ marginBottom: "1rem" }}>
      <div className="section-header">
        <span>Recent Sessions</span>
      </div>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        {recent.map((s) => {
          const active = Boolean(currentSessionId && s.session_id === currentSessionId);
          const label = s.project_name || s.session_id.slice(0, 8);
          const updated = new Date((s.updated_ts || s.created_ts) * 1000).toLocaleString();
          return (
            <button
              key={s.session_id}
              type="button"
              className={active ? "secondary" : ""}
              title={`Updated ${updated}`}
              onClick={() => onResume(s.session_id)}
              disabled={active as boolean}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
