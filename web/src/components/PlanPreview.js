import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
const formatCitationList = (citations) => citations && citations.length
    ? citations
        .map((citation) => citation?.source_id)
        .filter((id) => Boolean(id))
        .join(", ")
    : "—";
export function PlanPreview({ planJson, planMarkdown, qaResult, asanaTasks, publishUrl, conflicts, qaBlocked, }) {
    const [activeTab, setActiveTab] = useState("markdown");
    const engineeringInstructions = planJson?.engineering_instructions;
    const qualityPlan = planJson?.quality_plan;
    const purchasingPlan = planJson?.purchasing;
    const schedulePlan = planJson?.release_plan;
    const executionStrategy = planJson?.execution_strategy;
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
                lines.push(`| ${step.op_no} | ${step.workcenter} | ${step.input ?? "—"} | ${step.program ?? "—"} | ${notes} | ${qc} | ${sources} |`);
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
    const qualityMarkdown = useMemo(() => {
        if (!qualityPlan) {
            return "";
        }
        const lines = [];
        const pushList = (title, items) => {
            if (!items || items.length === 0) {
                return;
            }
            lines.push(`### ${title}`);
            items.forEach((item) => lines.push(`- ${item}`));
            lines.push("");
        };
        pushList("Critical to Quality", qualityPlan.ctqs);
        pushList("Inspection Levels", qualityPlan.inspection_levels);
        if (qualityPlan.passivation || qualityPlan.cleanliness) {
            lines.push("### Special Processes");
            if (qualityPlan.passivation) {
                lines.push(`- **Passivation:** ${qualityPlan.passivation}`);
            }
            if (qualityPlan.cleanliness) {
                lines.push(`- **Cleanliness:** ${qualityPlan.cleanliness}`);
            }
            lines.push("");
        }
        pushList("Hold Points", qualityPlan.hold_points);
        pushList("Required Tests", qualityPlan.required_tests);
        pushList("Documentation", qualityPlan.documentation);
        pushList("Metrology", qualityPlan.metrology);
        return lines.join("\n").trim();
    }, [qualityPlan]);
    const purchasingMarkdown = useMemo(() => {
        if (!purchasingPlan) {
            return "";
        }
        const lines = [];
        if (purchasingPlan.long_leads?.length) {
            lines.push("### Long Lead Items");
            lines.push("| Item | Lead Time | Vendor | Sources |");
            lines.push("| --- | --- | --- | --- |");
            purchasingPlan.long_leads.forEach((item) => {
                lines.push(`| ${item.item} | ${item.lead_time ?? "—"} | ${item.vendor_hint ?? "—"} | ${formatCitationList(item.citations)} |`);
            });
            lines.push("");
        }
        if (purchasingPlan.coo_mtr) {
            lines.push(`**Country of Origin / Material Traceability:** ${purchasingPlan.coo_mtr}`);
            lines.push("");
        }
        if (purchasingPlan.alternates?.length) {
            lines.push("### Approved Alternates");
            purchasingPlan.alternates.forEach((alt) => {
                const rationale = alt.rationale ? ` — ${alt.rationale}` : "";
                lines.push(`- **${alt.item}** → ${alt.alternate}${rationale} _(Sources: ${formatCitationList(alt.citations)})_`);
            });
            lines.push("");
        }
        if (purchasingPlan.rfqs?.length) {
            lines.push("### RFQs");
            lines.push("| Item | Vendor | Due | Sources |");
            lines.push("| --- | --- | --- | --- |");
            purchasingPlan.rfqs.forEach((rfq) => {
                lines.push(`| ${rfq.item} | ${rfq.vendor ?? "—"} | ${rfq.due ?? "—"} | ${formatCitationList(rfq.citations)} |`);
            });
            lines.push("");
        }
        return lines.join("\n").trim();
    }, [purchasingPlan]);
    const scheduleMarkdown = useMemo(() => {
        if (!schedulePlan) {
            return "";
        }
        const lines = [];
        const pushList = (title, items) => {
            if (!items || items.length === 0) {
                return;
            }
            lines.push(`### ${title}`);
            items.forEach((item) => lines.push(`- ${item}`));
            lines.push("");
        };
        if (schedulePlan.milestones?.length) {
            lines.push("### Milestones");
            lines.push("| Milestone | Start | End | Owner | Sources |");
            lines.push("| --- | --- | --- | --- | --- |");
            schedulePlan.milestones.forEach((milestone) => {
                lines.push(`| ${milestone.name} | ${milestone.start_hint ?? "—"} | ${milestone.end_hint ?? "—"} | ${milestone.owner ?? "—"} | ${formatCitationList(milestone.citations)} |`);
            });
            lines.push("");
        }
        pushList("Do Earlier Than Baseline", schedulePlan.do_early);
        pushList("Schedule Risks", schedulePlan.risks);
        return lines.join("\n").trim();
    }, [schedulePlan]);
    const executionMarkdown = useMemo(() => {
        if (!executionStrategy) {
            return "";
        }
        const lines = [];
        if (executionStrategy.timeboxes?.length) {
            lines.push("### Timeboxes");
            lines.push("| Window | Focus | Owner | Notes | Sources |");
            lines.push("| --- | --- | --- | --- | --- |");
            executionStrategy.timeboxes.forEach((timebox) => {
                const notes = timebox.notes?.length ? timebox.notes.join("<br />") : "—";
                lines.push(`| ${timebox.window} | ${timebox.focus} | ${timebox.owner_hint ?? "—"} | ${notes} | ${formatCitationList(timebox.citations)} |`);
            });
            lines.push("");
        }
        if (executionStrategy.notes?.length) {
            lines.push("### Additional Notes");
            executionStrategy.notes.forEach((note) => lines.push(`- ${note}`));
            lines.push("");
        }
        return lines.join("\n").trim();
    }, [executionStrategy]);
    const hasEngineering = Boolean(engineeringInstructions && engineeringMarkdown);
    const hasQuality = Boolean(qualityPlan && qualityMarkdown);
    const hasPurchasing = Boolean(purchasingPlan && purchasingMarkdown);
    const hasSchedule = Boolean(schedulePlan && scheduleMarkdown);
    const hasExecution = Boolean(executionStrategy && executionMarkdown);
    useEffect(() => {
        if (activeTab === "engineering" && !hasEngineering) {
            setActiveTab("markdown");
        }
        else if (activeTab === "quality" && !hasQuality) {
            setActiveTab("markdown");
        }
        else if (activeTab === "purchasing" && !hasPurchasing) {
            setActiveTab("markdown");
        }
        else if (activeTab === "schedule" && !hasSchedule) {
            setActiveTab("markdown");
        }
        else if (activeTab === "execution" && !hasExecution) {
            setActiveTab("markdown");
        }
    }, [activeTab, hasEngineering, hasQuality, hasPurchasing, hasSchedule, hasExecution]);
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
    let previewContent;
    if (!planJson) {
        previewContent = _jsx("p", { className: "small", children: "Draft a plan to see content here." });
    }
    else {
        switch (activeTab) {
            case "markdown":
                previewContent = _jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: planMarkdown });
                break;
            case "json":
                previewContent = _jsx("pre", { style: { whiteSpace: "pre-wrap" }, children: JSON.stringify(planJson, null, 2) });
                break;
            case "engineering":
                previewContent = hasEngineering ? (_jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: engineeringMarkdown })) : (_jsx("p", { className: "small", children: "Run specialist agents to generate engineering instructions." }));
                break;
            case "quality":
                previewContent = hasQuality ? (_jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: qualityMarkdown })) : (_jsx("p", { className: "small", children: "Run specialist agents to generate a quality plan." }));
                break;
            case "purchasing":
                previewContent = hasPurchasing ? (_jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: purchasingMarkdown })) : (_jsx("p", { className: "small", children: "Run specialist agents to generate purchasing actions." }));
                break;
            case "schedule":
                previewContent = hasSchedule ? (_jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: scheduleMarkdown })) : (_jsx("p", { className: "small", children: "Run specialist agents to generate a release plan." }));
                break;
            case "execution":
                previewContent = hasExecution ? (_jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: executionMarkdown })) : (_jsx("p", { className: "small", children: "Run specialist agents to generate execution strategy guidance." }));
                break;
            default:
                previewContent = _jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: planMarkdown });
        }
    }
    const qaScoreText = qaResult?.score !== undefined ? qaResult.score.toFixed(1) : "—";
    const qaReasons = qaResult?.reasons ?? [];
    const qaFixes = qaResult?.fixes ?? [];
    return (_jsxs("div", { className: "panel", children: [_jsx("h2", { children: "Plan Preview" }), _jsxs("div", { className: "preview-tabs", children: [_jsx("button", { type: "button", className: activeTab === "markdown" ? "active" : "", onClick: () => setActiveTab("markdown"), children: "Markdown" }), _jsx("button", { type: "button", className: activeTab === "json" ? "active" : "", onClick: () => setActiveTab("json"), children: "JSON" }), _jsx("button", { type: "button", className: `${activeTab === "engineering" ? "active" : ""} ${!hasEngineering ? "disabled" : ""}`.trim(), onClick: () => hasEngineering && setActiveTab("engineering"), disabled: !hasEngineering, children: "Engineering" }), _jsx("button", { type: "button", className: `${activeTab === "quality" ? "active" : ""} ${!hasQuality ? "disabled" : ""}`.trim(), onClick: () => hasQuality && setActiveTab("quality"), disabled: !hasQuality, children: "Quality" }), _jsx("button", { type: "button", className: `${activeTab === "purchasing" ? "active" : ""} ${!hasPurchasing ? "disabled" : ""}`.trim(), onClick: () => hasPurchasing && setActiveTab("purchasing"), disabled: !hasPurchasing, children: "Purchasing" }), _jsx("button", { type: "button", className: `${activeTab === "schedule" ? "active" : ""} ${!hasSchedule ? "disabled" : ""}`.trim(), onClick: () => hasSchedule && setActiveTab("schedule"), disabled: !hasSchedule, children: "Schedule" }), _jsx("button", { type: "button", className: `${activeTab === "execution" ? "active" : ""} ${!hasExecution ? "disabled" : ""}`.trim(), onClick: () => hasExecution && setActiveTab("execution"), disabled: !hasExecution, children: "Execution" })] }), _jsx("div", { className: "plan-preview", children: previewContent }), publishUrl && (_jsxs("div", { style: { marginTop: "0.75rem", display: "flex", alignItems: "center" }, children: [_jsxs("span", { className: "small", children: ["Published to Confluence: ", publishUrl] }), _jsx("button", { type: "button", className: "copy-link-button", onClick: handleCopyLink, children: "Copy Link" })] })), qaBlocked && (_jsx("div", { className: "warning-banner", style: { marginTop: "0.75rem" }, children: "QA is currently blocking publish. Address the highlighted fixes before publishing." })), qaResult && (_jsxs("section", { children: [_jsxs("div", { className: "badge", children: ["QA Score: ", qaScoreText, " / 100", qaResult.blocked ? " — Blocked" : ""] }), _jsxs("div", { className: "listing", style: { padding: "0.75rem 0.85rem" }, children: [_jsxs("div", { children: [_jsx("strong", { children: "Reasons" }), _jsx("ul", { children: qaReasons.length > 0 ? (qaReasons.map((reason, index) => _jsx("li", { children: reason }, `reason-${index}`))) : (_jsx("li", { children: "No reasons provided." })) })] }), _jsxs("div", { children: [_jsx("strong", { children: "Fixes" }), _jsx("ul", { children: qaFixes.length > 0 ? (qaFixes.map((fix, index) => _jsx("li", { children: fix }, `fix-${index}`))) : (_jsx("li", { children: "No fixes provided." })) })] })] })] })), conflicts.length > 0 && (_jsxs("section", { children: [_jsx("h3", { style: { marginTop: 0, color: "#f97316" }, children: "Specialist Conflicts" }), _jsx("div", { className: "listing", style: { padding: "0.75rem 0.85rem" }, children: conflicts.map((conflict, index) => {
                            const sources = formatCitationList(conflict.citations);
                            return (_jsxs("div", { style: { marginBottom: "0.5rem" }, children: [_jsx("strong", { children: conflict.topic }), _jsx("div", { className: "small", style: { marginTop: "0.25rem" }, children: conflict.issue }), _jsxs("div", { className: "small", style: { marginTop: "0.25rem", opacity: 0.7 }, children: ["Sources: ", sources] })] }, `${conflict.topic}-${index}`));
                        }) })] })), asanaTasks.length > 0 && (_jsxs("section", { children: [_jsx("h3", { style: { marginTop: 0, color: "#a855f7" }, children: "Asana Tasks" }), _jsx("div", { className: "listing", children: asanaTasks.map((task) => (_jsxs("div", { className: "badge", children: ["\u2705 ", task.name] }, task.gid ?? task.name))) })] }))] }));
}
