import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { api } from "../api";
import { Toast } from "./ToastContainer";
import { AsanaProjectSummary, ChatMessage, SpecialistAgentKey } from "../types";

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
  agentStatuses: Record<SpecialistAgentKey, AgentStatus>;
  agentsRunning: boolean;
  hideChat?: boolean;
  showControls?: boolean;
  hideHeader?: boolean;
  pushToast: (type: Toast["type"], message: string) => void;
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
  hideChat,
  showControls = true,
  hideHeader = false,
  pushToast,
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

  const {
    data: projectResults = [],
    isFetching: projectLoading,
    error: projectError,
  } = useQuery<AsanaProjectSummary[]>(
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

  const projectErrorMessage = useMemo(() => {
    if (!projectError) {
      return null;
    }
    if (isAxiosError(projectError)) {
      const detail = projectError.response?.data?.detail;
      if (typeof detail === "string" && detail.trim().length > 0) {
        return detail;
      }
    }
    return "Unable to search Asana projects. Check your Asana credentials in the server .env.";
  }, [projectError]);

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
    const raw = event.target.value.trim();
    // Try to extract a project GID if a full Asana URL was pasted/typed
    const extractAsanaProjectGid = (text: string): string => {
      // common patterns:
      // https://app.asana.com/0/{workspace_or_team}/{project_gid}
      // https://app.asana.com/1/{workspace_or_team}/project/{project_gid}
      // https://app.asana.com/0/project/{project_gid}
      // or a raw numeric gid
      const urlMatch = text.match(/https?:\/\/[^\s]+/i);
      const source = urlMatch ? urlMatch[0] : text;
      // match \/project\/(digits)
      const m1 = source.match(/\/project\/(\d{6,})/);
      if (m1 && m1[1]) return m1[1];
      // match trailing \/(digits)
      const m2 = source.match(/\/(\d{6,})(?:\/?$|\?)/);
      if (m2 && m2[1]) return m2[1];
      // fallback: only digits
      const m3 = source.match(/^(\d{6,})$/);
      if (m3 && m3[1]) return m3[1];
      return text;
    };

    const gid = extractAsanaProjectGid(raw);
    onManualAsanaProjectIdChange(gid);
    if (event.target.value.trim().length > 0) {
      setProjectSearch("");
    }
  };

  const manualProjectId = manualAsanaProjectId;

  const showProjectMenu = projectFocused && !disabled && projectSearch.trim().length > 1;

  const agentStatusItems: { key: SpecialistAgentKey; label: string }[] = [
    { key: "qma", label: "Quality" },
    { key: "pma", label: "Purchasing" },
    { key: "sca", label: "Scheduling" },
    { key: "ema", label: "Engineering" },
    { key: "sbpqa", label: "QA Gate" },
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
      {!hideHeader && <h2>Chat & Actions</h2>}

      {showControls && (
        <>
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
            {projectErrorMessage && (
              <div className="error-banner" style={{ marginTop: "0.5rem" }}>
                Asana search error: {projectErrorMessage}
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
                    onClick={() => {
                      if (!selectedAsanaProject.url) {
                        pushToast("error", "No URL available to open");
                        return;
                      }
                      try {
                        window.open(selectedAsanaProject.url, "_blank", "noopener");
                      } catch (error) {
                        pushToast("error", "Failed to open URL. Popup may be blocked.");
                      }
                    }}
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
              onPaste={(e) => {
                // Ensure pasted URLs are parsed into a pure GID value
                const pasted = e.clipboardData.getData("text");
                if (pasted) {
                  e.preventDefault();
                  const synthetic = { target: { value: pasted } } as unknown as ChangeEvent<HTMLInputElement>;
                  handleManualProjectChange(synthetic);
                }
              }}
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
                onClick={() => {
                  if (!publishUrl) {
                    pushToast("error", "No URL available to open");
                    return;
                  }
                  try {
                    window.open(publishUrl, "_blank", "noopener");
                  } catch (error) {
                    pushToast("error", "Failed to open URL. Popup may be blocked.");
                  }
                }}
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
        </>
      )}

      {!hideChat && (
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
      )}

      {!hideChat && (
        <form onSubmit={handleSubmit} style={{ marginTop: "0.75rem" }}>
          <label htmlFor="chat-message">Chat with Planner</label>
          <textarea
            id="chat-message"
            placeholder="Capture latest fixture updates, decisions, or TODOs that need to roll into the plan."
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            disabled={false}
          />
          <button type="submit" disabled={sending || disabled} style={{ marginTop: "0.75rem" }}>
            {sending ? "Sending…" : "Send Message"}
          </button>
        </form>
      )}
    </div>
  );
}
