import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
function useDebouncedValue(value, delay = 300) {
    const [debounced, setDebounced] = useState(value);
    useEffect(() => {
        const handle = window.setTimeout(() => setDebounced(value), delay);
        return () => window.clearTimeout(handle);
    }, [value, delay]);
    return debounced;
}
export function ChatPanel({ messages, input, onInputChange, onSend, sending, actions, confluenceParentId, onConfluenceParentIdChange, selectedAsanaProject, onSelectAsanaProject, manualAsanaProjectId, onManualAsanaProjectIdChange, newProjectName, onNewProjectNameChange, onCreateProject, creatingProject, publishUrl, qaSummary, qaBlocked, qaFixes, asanaStatus, statusMessage, errorMessage, disabled, agentStatuses, agentsRunning, }) {
    const handleSubmit = async (event) => {
        event.preventDefault();
        if (!input.trim() || sending || disabled) {
            return;
        }
        await onSend();
    };
    const [projectSearch, setProjectSearch] = useState("");
    const [projectFocused, setProjectFocused] = useState(false);
    useEffect(() => {
        if (selectedAsanaProject) {
            setProjectSearch(selectedAsanaProject.name);
        }
    }, [selectedAsanaProject]);
    const debouncedProjectQuery = useDebouncedValue(projectSearch);
    const { data: projectResults = [], isFetching: projectLoading } = useQuery({
        queryKey: ["asana-projects", debouncedProjectQuery],
        queryFn: async () => {
            if (!debouncedProjectQuery.trim()) {
                return [];
            }
            const { data } = await api.get("/asana/projects", {
                params: { q: debouncedProjectQuery },
            });
            return data;
        },
        enabled: debouncedProjectQuery.trim().length > 1,
        staleTime: 60000,
    });
    const filteredProjects = useMemo(() => {
        if (!projectResults || projectResults.length === 0) {
            return [];
        }
        const seen = new Set();
        return projectResults.filter((project) => {
            if (seen.has(project.gid)) {
                return false;
            }
            seen.add(project.gid);
            return true;
        });
    }, [projectResults]);
    const handleSelectProject = (project) => {
        onSelectAsanaProject(project);
        setProjectSearch(project.name);
        setProjectFocused(false);
    };
    const handleManualProjectChange = (event) => {
        onManualAsanaProjectIdChange(event.target.value);
        if (event.target.value.trim().length > 0) {
            setProjectSearch("");
        }
    };
    const manualProjectId = manualAsanaProjectId;
    const showProjectMenu = projectFocused && !disabled && projectSearch.trim().length > 1;
    const agentStatusItems = [
        { key: "qea", label: "QEA" },
        { key: "qdd", label: "QDD" },
        { key: "ema", label: "EMA" },
    ];
    const renderStatusIcon = (status) => {
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
    return (_jsxs("div", { className: "panel", children: [_jsx("h2", { children: "Chat & Actions" }), errorMessage && _jsx("div", { className: "error-banner", children: errorMessage }), statusMessage && _jsx("div", { className: "success-banner", children: statusMessage }), _jsxs("section", { children: [_jsx("label", { htmlFor: "confluence-parent", children: "Confluence Parent Page" }), _jsx("input", { id: "confluence-parent", type: "text", placeholder: "Optional parent page ID", value: confluenceParentId, onChange: (event) => onConfluenceParentIdChange(event.target.value) })] }), _jsxs("section", { children: [_jsx("label", { htmlFor: "asana-project-search", children: "Asana Project" }), _jsx("input", { id: "asana-project-search", type: "text", placeholder: "Search existing projects", value: projectSearch, onFocus: () => setProjectFocused(true), onBlur: () => setTimeout(() => setProjectFocused(false), 150), onChange: (event) => {
                            setProjectSearch(event.target.value);
                            if (event.target.value.trim().length > 0 && manualProjectId) {
                                onManualAsanaProjectIdChange("");
                            }
                            if (event.target.value.trim().length === 0) {
                                onSelectAsanaProject(null);
                            }
                        }, disabled: disabled }), showProjectMenu && (_jsxs("div", { className: "autocomplete-menu", children: [projectLoading && _jsx("div", { className: "autocomplete-empty", children: "Searching\u2026" }), !projectLoading && filteredProjects.length === 0 && (_jsx("div", { className: "autocomplete-empty", children: "No matches yet. Try another keyword." })), !projectLoading &&
                                filteredProjects.map((project) => (_jsxs("button", { type: "button", className: "autocomplete-item", onMouseDown: (event) => event.preventDefault(), onClick: () => handleSelectProject(project), children: [_jsx("div", { children: project.name }), project.team?.name && (_jsxs("div", { className: "small", style: { opacity: 0.75 }, children: ["Team: ", project.team.name] }))] }, project.gid)))] })), selectedAsanaProject && (_jsxs("div", { className: "badge", style: { marginTop: "0.35rem" }, children: ["Selected project: ", selectedAsanaProject.name, selectedAsanaProject.url && (_jsx("button", { type: "button", className: "link-button", style: { marginLeft: "0.5rem" }, onClick: () => window.open(selectedAsanaProject.url, "_blank", "noopener"), children: "Open \u2197" })), _jsx("button", { type: "button", className: "link-button", style: { marginLeft: "0.5rem" }, onClick: () => {
                                    onSelectAsanaProject(null);
                                    setProjectSearch("");
                                }, children: "Clear" })] })), _jsx("label", { htmlFor: "asana-project-id", style: { marginTop: "0.75rem" }, children: "Or paste project GID manually" }), _jsx("input", { id: "asana-project-id", type: "text", placeholder: "asana-project-gid", value: manualProjectId, onChange: handleManualProjectChange, disabled: disabled }), _jsx("label", { htmlFor: "asana-project-name", style: { marginTop: "0.75rem" }, children: "New project name" }), _jsxs("div", { style: { display: "flex", gap: "0.5rem" }, children: [_jsx("input", { id: "asana-project-name", type: "text", placeholder: "APQP \u2014 Customer \u2014 Family", value: newProjectName, onChange: (event) => onNewProjectNameChange(event.target.value), disabled: disabled || creatingProject }), _jsx("button", { type: "button", onClick: () => onCreateProject(), disabled: disabled || creatingProject || !newProjectName.trim(), children: creatingProject ? "Creating…" : "Create" })] })] }), _jsxs("section", { children: [_jsxs("div", { className: "section-header", children: [_jsx("span", { children: "Specialist Agents" }), agentsRunning && _jsx("span", { className: "small", children: "Running\u2026" })] }), _jsx("div", { className: "agent-status-list", children: agentStatusItems.map((item) => (_jsxs("div", { className: `agent-status agent-${agentStatuses[item.key]}`, children: [_jsx("span", { className: "agent-icon", children: renderStatusIcon(agentStatuses[item.key]) }), _jsx("span", { children: item.label })] }, item.key))) })] }), _jsx("section", { className: "action-grid", children: actions.map((action) => (_jsx("button", { type: "button", className: action.variant === "secondary" ? "secondary" : "", onClick: () => action.onClick(), disabled: action.disabled || disabled, children: action.label }, action.label))) }), publishUrl && (_jsxs("div", { className: "success-banner", children: ["Published to Confluence:", _jsx("button", { type: "button", className: "link-button", onClick: () => window.open(publishUrl, "_blank", "noopener"), children: "Open Page \u2197" })] })), qaSummary && _jsxs("div", { className: "success-banner", children: ["QA: ", qaSummary] }), qaBlocked && (_jsx("div", { className: "warning-banner", children: qaFixes && qaFixes.length > 0 ? (_jsxs(_Fragment, { children: ["QA blocking fixes:", _jsx("ul", { children: qaFixes.map((fix, index) => (_jsx("li", { children: fix }, `qa-fix-${index}`))) })] })) : (_jsx("span", { children: "QA is blocking publish. Address outstanding issues before pushing to Confluence." })) })), asanaStatus && _jsxs("div", { className: "success-banner", children: ["Asana: ", asanaStatus] }), _jsx("div", { className: "chat-messages", children: messages.length === 0 ? (_jsx("span", { className: "small", children: "No messages yet. Ask the planner to update sections." })) : (messages.map((message) => (_jsxs("div", { className: `chat-message ${message.role}`, children: [_jsxs("div", { className: "small", style: { marginBottom: "0.35rem" }, children: [new Date(message.timestamp).toLocaleTimeString([], {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                }), " \u2013 ", message.role === "assistant" ? "Planner" : "You"] }), _jsx("div", { children: message.content })] }, message.id)))) }), _jsxs("form", { onSubmit: handleSubmit, style: { marginTop: "0.75rem" }, children: [_jsx("label", { htmlFor: "chat-message", children: "Chat with Planner" }), _jsx("textarea", { id: "chat-message", placeholder: "Capture latest fixture updates, decisions, or TODOs that need to roll into the plan.", value: input, onChange: (event) => onInputChange(event.target.value), disabled: disabled }), _jsx("button", { type: "submit", disabled: sending || disabled, style: { marginTop: "0.75rem" }, children: sending ? "Sending…" : "Send Message" })] })] }));
}
