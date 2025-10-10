import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
function badgeClass(status) {
    if (status === "ok") {
        return "status-badge ok";
    }
    if (status === "error") {
        return "status-badge error";
    }
    return "status-badge unknown";
}
function authStatusLabel(status) {
    if (!status) {
        return { text: "Unknown", tone: "unknown" };
    }
    return status.ok
        ? { text: "OK", tone: "ok" }
        : { text: status.reason ? `Error: ${status.reason}` : "Error", tone: "error" };
}
export function StatusBar({ healthStatus, confluenceStatus, asanaStatus, onRefresh, onToggleAbout, aboutOpen, versionInfo, }) {
    const confluence = authStatusLabel(confluenceStatus);
    const asana = authStatusLabel(asanaStatus);
    return (_jsxs("header", { className: "status-bar", children: [_jsxs("div", { className: "status-items", children: [_jsxs("span", { className: badgeClass(healthStatus), children: ["API: ", healthStatus.toUpperCase()] }), _jsxs("span", { className: `status-badge ${confluence.tone}`, children: ["Confluence: ", confluence.text] }), _jsxs("span", { className: `status-badge ${asana.tone}`, children: ["Asana: ", asana.text] }), onRefresh && (_jsx("button", { type: "button", className: "secondary", onClick: onRefresh, children: "Refresh" }))] }), _jsxs("div", { className: "about-area", children: [_jsx("button", { type: "button", className: "secondary", onClick: onToggleAbout, children: "About" }), aboutOpen && versionInfo && (_jsxs("div", { className: "about-popover", children: [_jsxs("div", { children: [_jsx("strong", { children: "Version:" }), " ", versionInfo.version] }), _jsxs("div", { children: [_jsx("strong", { children: "Build:" }), " ", versionInfo.build_sha] }), versionInfo.build_time && _jsxs("div", { children: [_jsx("strong", { children: "Build Time:" }), " ", versionInfo.build_time] }), versionInfo.model && _jsxs("div", { children: [_jsx("strong", { children: "Model:" }), " ", versionInfo.model] }), versionInfo.prompt_version && _jsxs("div", { children: [_jsx("strong", { children: "Prompt:" }), " ", versionInfo.prompt_version] }), versionInfo.schema_version && _jsxs("div", { children: [_jsx("strong", { children: "Schema:" }), " ", versionInfo.schema_version] })] }))] })] }));
}
