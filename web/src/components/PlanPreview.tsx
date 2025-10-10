import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AsanaTaskSummary,
  EngineeringInstructions,
  PlanJson,
  QAGradeResponseData,
} from "../types";

interface PlanPreviewProps {
  planJson: PlanJson | null;
  planMarkdown: string;
  qaResult: QAGradeResponseData | null;
  asanaTasks: AsanaTaskSummary[];
  publishUrl?: string | null;
}

export function PlanPreview({ planJson, planMarkdown, qaResult, asanaTasks, publishUrl }: PlanPreviewProps) {
  const [activeTab, setActiveTab] = useState<"markdown" | "json" | "engineering">("markdown");

  const engineeringInstructions = planJson?.engineering_instructions as EngineeringInstructions | undefined;

  const engineeringMarkdown = useMemo(() => {
    if (!engineeringInstructions) {
      return "";
    }
    const lines: string[] = [];
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
        lines.push(
          `| ${step.op_no} | ${step.workcenter} | ${step.input} | ${step.program || "—"} | ${notes} | ${qc} | ${sources} |`
        );
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
    } catch {
      const tempInput = document.createElement("input");
      tempInput.value = publishUrl;
      document.body.appendChild(tempInput);
      tempInput.select();
      document.execCommand("copy");
      document.body.removeChild(tempInput);
    }
  }, [publishUrl]);

  return (
    <div className="panel">
      <h2>Plan Preview</h2>

      <div className="preview-tabs">
        <button
          type="button"
          className={activeTab === "markdown" ? "active" : ""}
          onClick={() => setActiveTab("markdown")}
        >
          Markdown
        </button>
        <button
          type="button"
          className={activeTab === "json" ? "active" : ""}
          onClick={() => setActiveTab("json")}
        >
          JSON
        </button>
        <button
          type="button"
          className={`${activeTab === "engineering" ? "active" : ""} ${!hasEngineering ? "disabled" : ""}`.trim()}
          onClick={() => hasEngineering && setActiveTab("engineering")}
          disabled={!hasEngineering}
        >
          Engineering Instructions
        </button>
      </div>

      <div className="plan-preview">
        {planJson ? (
          activeTab === "markdown" ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{planMarkdown}</ReactMarkdown>
          ) : activeTab === "json" ? (
            <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(planJson, null, 2)}</pre>
          ) : hasEngineering ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{engineeringMarkdown}</ReactMarkdown>
          ) : (
            <p className="small">Run specialist agents to generate engineering instructions.</p>
          )
        ) : (
          <p className="small">Draft a plan to see content here.</p>
        )}
      </div>

      {publishUrl && (
        <div style={{ marginTop: "0.75rem", display: "flex", alignItems: "center" }}>
          <span className="small">Published to Confluence: {publishUrl}</span>
          <button type="button" className="copy-link-button" onClick={handleCopyLink}>
            Copy Link
          </button>
        </div>
      )}

      {qaResult && (
        <section>
          <div className="badge">QA Score: {qaResult.score.toFixed(1)} / 100</div>
          <div className="listing" style={{ padding: "0.75rem 0.85rem" }}>
            <div>
              <strong>Reasons</strong>
              <ul>
                {qaResult.reasons.map((reason, index) => (
                  <li key={`reason-${index}`}>{reason}</li>
                ))}
              </ul>
            </div>
            <div>
              <strong>Fixes</strong>
              <ul>
                {qaResult.fixes.map((fix, index) => (
                  <li key={`fix-${index}`}>{fix}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      {asanaTasks.length > 0 && (
        <section>
          <h3 style={{ marginTop: 0, color: "#a855f7" }}>Asana Tasks</h3>
          <div className="listing">
            {asanaTasks.map((task) => (
              <div key={task.gid ?? task.name} className="badge">
                ✅ {task.name}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
