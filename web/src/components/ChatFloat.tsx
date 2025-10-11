import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChatPanel } from "./ChatPanel";
import type { AsanaProjectSummary, ChatMessage, SpecialistAgentKey } from "../types";

type AgentStatus = "idle" | "pending" | "ok" | "warn";

export interface ChatFloatProps {
  messages: ChatMessage[];
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => Promise<void> | void;
  sending: boolean;
  actions: { label: string; onClick: () => void | Promise<void>; disabled?: boolean; variant?: "primary" | "secondary" }[];
  confluenceParentId: string;
  onConfluenceParentIdChange: (value: string) => void;
  selectedAsanaProject: AsanaProjectSummary | null;
  onSelectAsanaProject: (project: AsanaProjectSummary | null) => void;
  manualAsanaProjectId: string;
  onManualAsanaProjectIdChange: (value: string) => void;
  newProjectName: string;
  onNewProjectNameChange: (value: string) => void;
  onCreateProject: () => Promise<void> | void;
  creatingProject: boolean;
  publishUrl?: string | null;
  qaSummary?: string | null;
  qaBlocked?: boolean;
  qaFixes?: string[];
  asanaStatus?: string | null;
  statusMessage?: string | null;
  errorMessage?: string | null;
  disabled?: boolean;
  agentStatuses: Record<SpecialistAgentKey, AgentStatus>;
  agentsRunning: boolean;
}

export function ChatFloat(props: ChatFloatProps) {
  const [open, setOpen] = useState(false);
  const [mount, setMount] = useState<HTMLElement | null>(null);
  const [unread, setUnread] = useState(0);
  const lastCountRef = useRef(0);
  useEffect(() => setMount(document.body), []);
  useEffect(() => {
    // Poll session messages count if available via parent props (fallback: no-op)
    const tick = async () => {
      try {
        // In this component we don't have sessionId; parent can extend this later.
        // For now, increment unread on close when new messages arrive via props.
        const n = props.messages?.length || 0;
        if (!open && n > lastCountRef.current) {
          setUnread((prev) => prev + (n - lastCountRef.current));
        }
        lastCountRef.current = n;
      } catch {}
    };
    const id = window.setInterval(tick, 5000);
    tick();
    return () => window.clearInterval(id);
  }, [open, props.messages?.length]);
  if (!mount) return null;

  const panel = (
    <div style={{ position: "fixed", bottom: 16, right: 16, zIndex: 1000 }}>
      {!open && (
        <button
          onClick={() => { setOpen(true); setUnread(0); }}
          style={{
            padding: "10px 14px",
            borderRadius: 999,
            background: "#2563eb",
            color: "white",
            border: "none",
            boxShadow: "0 6px 16px rgba(0,0,0,0.2)",
            cursor: "pointer",
            position: "relative",
          }}
          aria-label="Chat with Planner"
          title="Chat with Planner"
        >
          💬 Chat with Planner
          {unread > 0 && (
            <span
              style={{
                position: "absolute",
                top: -6,
                right: -6,
                background: "#ef4444",
                color: "white",
                borderRadius: 999,
                padding: "2px 6px",
                fontSize: 12,
                fontWeight: 700,
              }}
            >
              {unread}
            </span>
          )}
        </button>
      )}
      {open && (
        <div
          style={{
            width: "min(460px, 94vw)",
            height: "min(70vh, 80vh)",
            background: "#e6f0ff",
            color: "#0b1e3a",
            borderRadius: 14,
            boxShadow: "0 14px 28px rgba(0,0,0,0.3)",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            border: "1px solid #9ec0ff",
          }}
          role="dialog"
          aria-modal="false"
          aria-label="Chat with Planner"
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "10px 12px",
              background: "#cfe1ff",
              borderBottom: "1px solid #9ec0ff",
            }}
          >
            <div style={{ fontWeight: 700, color: "#0b1e3a" }}>Chat with Planner</div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => setOpen(false)}
                style={{
                  background: "#e6f0ff",
                  color: "#0b1e3a",
                  border: "1px solid #9ec0ff",
                  borderRadius: 8,
                  padding: "6px 10px",
                  cursor: "pointer",
                }}
                title="Close"
                aria-label="Close chat"
              >
                ✕
              </button>
            </div>
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ChatPanel
              messages={props.messages}
              input={props.input}
              onInputChange={props.onInputChange}
              onSend={props.onSend}
              sending={props.sending}
              actions={[]}
              confluenceParentId={""}
              onConfluenceParentIdChange={() => {}}
              selectedAsanaProject={null}
              onSelectAsanaProject={() => {}}
              manualAsanaProjectId={""}
              onManualAsanaProjectIdChange={() => {}}
              newProjectName={""}
              onNewProjectNameChange={() => {}}
              onCreateProject={() => {}}
              creatingProject={false}
              publishUrl={undefined}
              qaSummary={undefined}
              qaBlocked={false}
              qaFixes={undefined}
              asanaStatus={undefined}
              statusMessage={undefined}
              errorMessage={undefined}
              disabled={false}
              agentStatuses={{ qma: "idle", pma: "idle", sca: "idle", ema: "idle", sbpqa: "idle" }}
              agentsRunning={false}
              showControls={false}
              hideHeader
            />
          </div>
        </div>
      )}
    </div>
  );

  return createPortal(panel, mount);
}
