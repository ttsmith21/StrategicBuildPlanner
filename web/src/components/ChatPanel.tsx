import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { AsanaProjectSummary, ChatMessage } from "../types";

type AgentStatus = "idle" | "pending" | "ok" | "warn";

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
  agentStatuses: Record<"qea" | "qdd" | "ema", AgentStatus>;
  agentsRunning: boolean;
}

function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(handle);
  }, [value, delay]);
  return debounced;
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
  selectedAsanaProject,
  onSelectAsanaProject,
  manualAsanaProjectId,
  onManualAsanaProjectIdChange,
  newProjectName,
  onNewProjectNameChange,
  onCreateProject,
  creatingProject,
  publishUrl,
  qaSummary,
  qaBlocked,
  qaFixes,
  asanaStatus,
  statusMessage,
  errorMessage,
  disabled,
  agentStatuses,
  agentsRunning,
}: ChatPanelProps) {
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim() || sending || disabled) {
      return;
    }
    await onSend();
  };

  const [projectSearch, setProjectSearch] = useState<string>("");
  const [projectFocused, setProjectFocused] = useState(false);

  useEffect(() => {
    if (selectedAsanaProject) {
      setProjectSearch(selectedAsanaProject.name);
    }
  }, [selectedAsanaProject]);

  const debouncedProjectQuery = useDebouncedValue(projectSearch);

  const { data: projectResults = [], isFetching: projectLoading } = useQuery<AsanaProjectSummary[]>(
    {
      queryKey: ["asana-projects", debouncedProjectQuery],
      queryFn: async () => {
        if (!debouncedProjectQuery.trim()) {
          return [];
        }
        const { data } = await api.get<AsanaProjectSummary[]>("/asana/projects", {
          params: { q: debouncedProjectQuery },
        });
        return data;
      },
      enabled: debouncedProjectQuery.trim().length > 1,
      staleTime: 60_000,
    }
  );

  const filteredProjects = useMemo(() => {
    if (!projectResults || projectResults.length === 0) {
      return [];
    }
    const seen = new Set<string>();
    return projectResults.filter((project) => {
      if (seen.has(project.gid)) {
        return false;
      }
      seen.add(project.gid);
      return true;
    });
  }, [projectResults]);

  const handleSelectProject = (project: AsanaProjectSummary) => {
    onSelectAsanaProject(project);
    setProjectSearch(project.name);
    setProjectFocused(false);
  };

  const handleManualProjectChange = (event: ChangeEvent<HTMLInputElement>) => {
    onManualAsanaProjectIdChange(event.target.value);
    if (event.target.value.trim().length > 0) {
      setProjectSearch("");
    }
  };

  const manualProjectId = manualAsanaProjectId;

  const showProjectMenu = projectFocused && !disabled && projectSearch.trim().length > 1;

  const agentStatusItems: { key: "qea" | "qdd" | "ema"; label: string }[] = [
    { key: "qea", label: "QEA" },
    { key: "qdd", label: "QDD" },
    { key: "ema", label: "EMA" },
  ];

  const renderStatusIcon = (status: AgentStatus) => {
    if (status === "ok") {
      return "✅";
    }
    if (status === "pending") {
      return "…";
    }
    if (status === "warn") {
      return "⚠";
    }
    return "▫";
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
        <label htmlFor="asana-project-search">Asana Project</label>
        <input
          id="asana-project-search"
          type="text"
          placeholder="Search existing projects"
          value={projectSearch}
          onFocus={() => setProjectFocused(true)}
          onBlur={() => setTimeout(() => setProjectFocused(false), 150)}
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            setProjectSearch(event.target.value);
            if (event.target.value.trim().length > 0 && manualProjectId) {
              onManualAsanaProjectIdChange("");
            }
            if (event.target.value.trim().length === 0) {
              onSelectAsanaProject(null);
            }
          }}
          disabled={disabled}
        />
        {showProjectMenu && (
          <div className="autocomplete-menu">
            {projectLoading && <div className="autocomplete-empty">Searching…</div>}
            {!projectLoading && filteredProjects.length === 0 && (
              <div className="autocomplete-empty">No matches yet. Try another keyword.</div>
            )}
            {!projectLoading &&
              filteredProjects.map((project) => (
                <button
                  type="button"
                  key={project.gid}
                  className="autocomplete-item"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleSelectProject(project)}
                >
                  <div>{project.name}</div>
                  {project.team?.name && (
                    <div className="small" style={{ opacity: 0.75 }}>
                      Team: {project.team.name}
                    </div>
                  )}
                </button>
              ))}
          </div>
        )}
        {selectedAsanaProject && (
          <div className="badge" style={{ marginTop: "0.35rem" }}>
            Selected project: {selectedAsanaProject.name}
            {selectedAsanaProject.url && (
              <button
                type="button"
                className="link-button"
                style={{ marginLeft: "0.5rem" }}
                onClick={() => window.open(selectedAsanaProject.url!, "_blank", "noopener")}
              >
                Open ↗
              </button>
            )}
            <button
              type="button"
              className="link-button"
              style={{ marginLeft: "0.5rem" }}
              onClick={() => {
                onSelectAsanaProject(null);
                setProjectSearch("");
              }}
            >
              Clear
            </button>
          </div>
        )}
        <label htmlFor="asana-project-id" style={{ marginTop: "0.75rem" }}>
          Or paste project GID manually
        </label>
        <input
          id="asana-project-id"
          type="text"
          placeholder="asana-project-gid"
          value={manualProjectId}
          onChange={handleManualProjectChange}
          disabled={disabled}
        />
        <label htmlFor="asana-project-name" style={{ marginTop: "0.75rem" }}>
          New project name
        </label>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <input
            id="asana-project-name"
            type="text"
            placeholder="APQP — Customer — Family"
            value={newProjectName}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onNewProjectNameChange(event.target.value)}
            disabled={disabled || creatingProject}
          />
          <button
            type="button"
            onClick={() => onCreateProject()}
            disabled={disabled || creatingProject || !newProjectName.trim()}
          >
            {creatingProject ? "Creating…" : "Create"}
          </button>
        </div>
      </section>

      <section>
        <div className="section-header">
          <span>Specialist Agents</span>
          {agentsRunning && <span className="small">Running…</span>}
        </div>
        <div className="agent-status-list">
          {agentStatusItems.map((item) => (
            <div key={item.key} className={`agent-status agent-${agentStatuses[item.key]}`}>
              <span className="agent-icon">{renderStatusIcon(agentStatuses[item.key])}</span>
              <span>{item.label}</span>
            </div>
          ))}
        </div>
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
    {qaBlocked && (
      <div className="warning-banner">
        {qaFixes && qaFixes.length > 0 ? (
          <>
            QA blocking fixes:
            <ul>
              {qaFixes.map((fix, index) => (
                <li key={`qa-fix-${index}`}>{fix}</li>
              ))}
            </ul>
          </>
        ) : (
          <span>QA is blocking publish. Address outstanding issues before pushing to Confluence.</span>
        )}
      </div>
    )}
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
