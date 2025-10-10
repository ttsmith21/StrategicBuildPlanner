import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
export function PlanPreview({ planJson, planMarkdown, qaResult, asanaTasks, publishUrl }) {
    const [activeTab, setActiveTab] = useState("markdown");
    const engineeringInstructions = planJson?.engineering_instructions;
    const engineeringMarkdown = useMemo(() => {
        if (!engineeringInstructions) {
            return "";
        }
        const lines = [];
        const routing = engineeringInstructions.routing ?? [];
        const fixtures = engineeringInstructions.fixtures ?? [];
        const ctqs = engineeringInstructions.ctqs_for_routing ?? [];
        const programs = engineeringInstructions.programs ?? [];
        const openItems = engineeringInstructions.open_items ?? [];
        if (routing.length > 0) {
            lines.push("### Routing");
            lines.push("| Step | Workcenter | Input | Program | Notes | QC | Sources |");
            lines.push("| --- | --- | --- | --- | --- | --- | --- |");
            routing.forEach((step) => {
                const notes = step.notes?.length ? step.notes.join("<br />") : "—";
                const qc = step.qc?.length ? step.qc.join("<br />") : "—";
                const sources = step.sources?.length
                    ? step.sources.map((source) => source.source_id).join(", ")
                    : "—";
                lines.push(`| ${step.op_no} | ${step.workcenter} | ${step.input} | ${step.program || "—"} | ${notes} | ${qc} | ${sources} |`);
            });
            lines.push("");
        }
        if (fixtures.length > 0) {
            lines.push("### Fixtures");
            fixtures.forEach((fixture) => {
                const sources = fixture.citations?.map((c) => c.source_id).join(", ") || "—";
                lines.push(`- **${fixture.name}** — ${fixture.purpose} _(Sources: ${sources})_`);
            });
            lines.push("");
        }
        if (programs.length > 0) {
            lines.push("### CNC / Robot Programs");
            programs.forEach((program) => {
                const sources = program.citations?.map((c) => c.source_id).join(", ") || "—";
                lines.push(`- **${program.machine}** — Program ${program.program_id}: ${program.notes} _(Sources: ${sources})_`);
            });
            lines.push("");
        }
        if (ctqs.length > 0) {
            lines.push("### CTQ Callouts");
            ctqs.forEach((ctq) => {
                const sources = ctq.citations?.map((c) => c.source_id).join(", ") || "—";
                lines.push(`- **${ctq.ctq}** — ${ctq.measurement_plan} _(Sources: ${sources})_`);
            });
            lines.push("");
        }
        if (openItems.length > 0) {
            lines.push("### Open Items");
            openItems.forEach((item) => {
                const owner = item.owner || "Unassigned";
                const due = item.due ? ` (Due: ${item.due})` : "";
                const sources = item.citations?.map((c) => c.source_id).join(", ") || "—";
                lines.push(`- **${item.issue}** — Owner: ${owner}${due}. _(Sources: ${sources})_`);
            });
            lines.push("");
        }
        return lines.join("\n").trim();
    }, [engineeringInstructions]);
    const hasEngineering = Boolean(engineeringInstructions && engineeringMarkdown);
    useEffect(() => {
        if (!hasEngineering && activeTab === "engineering") {
            setActiveTab("markdown");
        }
    }, [activeTab, hasEngineering]);
    const handleCopyLink = useCallback(async () => {
        if (!publishUrl) {
            return;
        }
        try {
            await navigator.clipboard.writeText(publishUrl);
        }
        catch {
            const tempInput = document.createElement("input");
            tempInput.value = publishUrl;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand("copy");
            document.body.removeChild(tempInput);
        }
    }, [publishUrl]);
    return (_jsxs("div", { className: "panel", children: [_jsx("h2", { children: "Plan Preview" }), _jsxs("div", { className: "preview-tabs", children: [_jsx("button", { type: "button", className: activeTab === "markdown" ? "active" : "", onClick: () => setActiveTab("markdown"), children: "Markdown" }), _jsx("button", { type: "button", className: activeTab === "json" ? "active" : "", onClick: () => setActiveTab("json"), children: "JSON" }), _jsx("button", { type: "button", className: `${activeTab === "engineering" ? "active" : ""} ${!hasEngineering ? "disabled" : ""}`.trim(), onClick: () => hasEngineering && setActiveTab("engineering"), disabled: !hasEngineering, children: "Engineering Instructions" })] }), _jsx("div", { className: "plan-preview", children: planJson ? (activeTab === "markdown" ? (_jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: planMarkdown })) : activeTab === "json" ? (_jsx("pre", { style: { whiteSpace: "pre-wrap" }, children: JSON.stringify(planJson, null, 2) })) : hasEngineering ? (_jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: engineeringMarkdown })) : (_jsx("p", { className: "small", children: "Run specialist agents to generate engineering instructions." }))) : (_jsx("p", { className: "small", children: "Draft a plan to see content here." })) }), publishUrl && (_jsxs("div", { style: { marginTop: "0.75rem", display: "flex", alignItems: "center" }, children: [_jsxs("span", { className: "small", children: ["Published to Confluence: ", publishUrl] }), _jsx("button", { type: "button", className: "copy-link-button", onClick: handleCopyLink, children: "Copy Link" })] })), qaResult && (_jsxs("section", { children: [_jsxs("div", { className: "badge", children: ["QA Score: ", qaResult.score.toFixed(1), " / 100"] }), _jsxs("div", { className: "listing", style: { padding: "0.75rem 0.85rem" }, children: [_jsxs("div", { children: [_jsx("strong", { children: "Reasons" }), _jsx("ul", { children: qaResult.reasons.map((reason, index) => (_jsx("li", { children: reason }, `reason-${index}`))) })] }), _jsxs("div", { children: [_jsx("strong", { children: "Fixes" }), _jsx("ul", { children: qaResult.fixes.map((fix, index) => (_jsx("li", { children: fix }, `fix-${index}`))) })] })] })] })), asanaTasks.length > 0 && (_jsxs("section", { children: [_jsx("h3", { style: { marginTop: 0, color: "#a855f7" }, children: "Asana Tasks" }), _jsx("div", { className: "listing", children: asanaTasks.map((task) => (_jsxs("div", { className: "badge", children: ["\u2705 ", task.name] }, task.gid ?? task.name))) })] }))] }));
}
