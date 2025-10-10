import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AsanaTaskSummary,
  EngineeringInstructions,
  ExecutionStrategy,
  PlanConflict,
  PlanJson,
  PurchasingPlan,
  QualityPlan,
  QAGradeResponseData,
  SchedulePlan,
} from "../types";

type PreviewTab = "markdown" | "json" | "engineering" | "quality" | "purchasing" | "schedule" | "execution";

interface PlanPreviewProps {
  planJson: PlanJson | null;
  planMarkdown: string;
  qaResult: QAGradeResponseData | null;
  asanaTasks: AsanaTaskSummary[];
  publishUrl?: string | null;
  conflicts: PlanConflict[];
  qaBlocked: boolean;
}

const formatCitationList = (citations?: { source_id?: string | null }[]) =>
  citations && citations.length
    ? citations
        .map((citation) => citation?.source_id)
        .filter((id): id is string => Boolean(id))
        .join(", ")
    : "—";

export function PlanPreview({
  planJson,
  planMarkdown,
  qaResult,
  asanaTasks,
  publishUrl,
  conflicts,
  qaBlocked,
}: PlanPreviewProps) {
  const [activeTab, setActiveTab] = useState<PreviewTab>("markdown");

  const engineeringInstructions = planJson?.engineering_instructions as EngineeringInstructions | undefined;
  const qualityPlan = planJson?.quality_plan as QualityPlan | undefined;
  const purchasingPlan = planJson?.purchasing as PurchasingPlan | undefined;
  const schedulePlan = planJson?.release_plan as SchedulePlan | undefined;
  const executionStrategy = planJson?.execution_strategy as ExecutionStrategy | undefined;

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
          `| ${step.op_no} | ${step.workcenter} | ${step.input ?? "—"} | ${step.program ?? "—"} | ${notes} | ${qc} | ${sources} |`
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

  const qualityMarkdown = useMemo(() => {
    if (!qualityPlan) {
      return "";
    }
    const lines: string[] = [];
    const pushList = (title: string, items?: string[]) => {
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
    const lines: string[] = [];

    if (purchasingPlan.long_leads?.length) {
      lines.push("### Long Lead Items");
      lines.push("| Item | Lead Time | Vendor | Sources |");
      lines.push("| --- | --- | --- | --- |");
      purchasingPlan.long_leads.forEach((item) => {
        lines.push(
          `| ${item.item} | ${item.lead_time ?? "—"} | ${item.vendor_hint ?? "—"} | ${formatCitationList(item.citations)} |`
        );
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
        lines.push(
          `- **${alt.item}** → ${alt.alternate}${rationale} _(Sources: ${formatCitationList(alt.citations)})_`
        );
      });
      lines.push("");
    }

    if (purchasingPlan.rfqs?.length) {
      lines.push("### RFQs");
      lines.push("| Item | Vendor | Due | Sources |");
      lines.push("| --- | --- | --- | --- |");
      purchasingPlan.rfqs.forEach((rfq) => {
        lines.push(
          `| ${rfq.item} | ${rfq.vendor ?? "—"} | ${rfq.due ?? "—"} | ${formatCitationList(rfq.citations)} |`
        );
      });
      lines.push("");
    }

    return lines.join("\n").trim();
  }, [purchasingPlan]);

  const scheduleMarkdown = useMemo(() => {
    if (!schedulePlan) {
      return "";
    }
    const lines: string[] = [];
    const pushList = (title: string, items?: string[]) => {
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
        lines.push(
          `| ${milestone.name} | ${milestone.start_hint ?? "—"} | ${milestone.end_hint ?? "—"} | ${milestone.owner ?? "—"} | ${formatCitationList(milestone.citations)} |`
        );
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
    const lines: string[] = [];

    if (executionStrategy.timeboxes?.length) {
      lines.push("### Timeboxes");
      lines.push("| Window | Focus | Owner | Notes | Sources |");
      lines.push("| --- | --- | --- | --- | --- |");
      executionStrategy.timeboxes.forEach((timebox) => {
        const notes = timebox.notes?.length ? timebox.notes.join("<br />") : "—";
        lines.push(
          `| ${timebox.window} | ${timebox.focus} | ${timebox.owner_hint ?? "—"} | ${notes} | ${formatCitationList(timebox.citations)} |`
        );
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
    } else if (activeTab === "quality" && !hasQuality) {
      setActiveTab("markdown");
    } else if (activeTab === "purchasing" && !hasPurchasing) {
      setActiveTab("markdown");
    } else if (activeTab === "schedule" && !hasSchedule) {
      setActiveTab("markdown");
    } else if (activeTab === "execution" && !hasExecution) {
      setActiveTab("markdown");
    }
  }, [activeTab, hasEngineering, hasQuality, hasPurchasing, hasSchedule, hasExecution]);

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

  let previewContent: JSX.Element | null;

  if (!planJson) {
    previewContent = <p className="small">Draft a plan to see content here.</p>;
  } else {
    switch (activeTab) {
      case "markdown":
        previewContent = <ReactMarkdown remarkPlugins={[remarkGfm]}>{planMarkdown}</ReactMarkdown>;
        break;
      case "json":
        previewContent = <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(planJson, null, 2)}</pre>;
        break;
      case "engineering":
        previewContent = hasEngineering ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{engineeringMarkdown}</ReactMarkdown>
        ) : (
          <p className="small">Run specialist agents to generate engineering instructions.</p>
        );
        break;
      case "quality":
        previewContent = hasQuality ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{qualityMarkdown}</ReactMarkdown>
        ) : (
          <p className="small">Run specialist agents to generate a quality plan.</p>
        );
        break;
      case "purchasing":
        previewContent = hasPurchasing ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{purchasingMarkdown}</ReactMarkdown>
        ) : (
          <p className="small">Run specialist agents to generate purchasing actions.</p>
        );
        break;
      case "schedule":
        previewContent = hasSchedule ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{scheduleMarkdown}</ReactMarkdown>
        ) : (
          <p className="small">Run specialist agents to generate a release plan.</p>
        );
        break;
      case "execution":
        previewContent = hasExecution ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{executionMarkdown}</ReactMarkdown>
        ) : (
          <p className="small">Run specialist agents to generate execution strategy guidance.</p>
        );
        break;
      default:
        previewContent = <ReactMarkdown remarkPlugins={[remarkGfm]}>{planMarkdown}</ReactMarkdown>;
    }
  }

  const qaScoreText = qaResult?.score !== undefined ? qaResult.score.toFixed(1) : "—";
  const qaReasons = qaResult?.reasons ?? [];
  const qaFixes = qaResult?.fixes ?? [];

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
          Engineering
        </button>
        <button
          type="button"
          className={`${activeTab === "quality" ? "active" : ""} ${!hasQuality ? "disabled" : ""}`.trim()}
          onClick={() => hasQuality && setActiveTab("quality")}
          disabled={!hasQuality}
        >
          Quality
        </button>
        <button
          type="button"
          className={`${activeTab === "purchasing" ? "active" : ""} ${!hasPurchasing ? "disabled" : ""}`.trim()}
          onClick={() => hasPurchasing && setActiveTab("purchasing")}
          disabled={!hasPurchasing}
        >
          Purchasing
        </button>
        <button
          type="button"
          className={`${activeTab === "schedule" ? "active" : ""} ${!hasSchedule ? "disabled" : ""}`.trim()}
          onClick={() => hasSchedule && setActiveTab("schedule")}
          disabled={!hasSchedule}
        >
          Schedule
        </button>
        <button
          type="button"
          className={`${activeTab === "execution" ? "active" : ""} ${!hasExecution ? "disabled" : ""}`.trim()}
          onClick={() => hasExecution && setActiveTab("execution")}
          disabled={!hasExecution}
        >
          Execution
        </button>
      </div>

      <div className="plan-preview">{previewContent}</div>

      {publishUrl && (
        <div style={{ marginTop: "0.75rem", display: "flex", alignItems: "center" }}>
          <span className="small">Published to Confluence: {publishUrl}</span>
          <button type="button" className="copy-link-button" onClick={handleCopyLink}>
            Copy Link
          </button>
        </div>
      )}

      {qaBlocked && (
        <div className="warning-banner" style={{ marginTop: "0.75rem" }}>
          QA is currently blocking publish. Address the highlighted fixes before publishing.
        </div>
      )}

      {qaResult && (
        <section>
          <div className="badge">
            QA Score: {qaScoreText} / 100{qaResult.blocked ? " — Blocked" : ""}
          </div>
          <div className="listing" style={{ padding: "0.75rem 0.85rem" }}>
            <div>
              <strong>Reasons</strong>
              <ul>
                {qaReasons.length > 0 ? (
                  qaReasons.map((reason, index) => <li key={`reason-${index}`}>{reason}</li>)
                ) : (
                  <li>No reasons provided.</li>
                )}
              </ul>
            </div>
            <div>
              <strong>Fixes</strong>
              <ul>
                {qaFixes.length > 0 ? (
                  qaFixes.map((fix, index) => <li key={`fix-${index}`}>{fix}</li>)
                ) : (
                  <li>No fixes provided.</li>
                )}
              </ul>
            </div>
          </div>
        </section>
      )}

      {conflicts.length > 0 && (
        <section>
          <h3 style={{ marginTop: 0, color: "#f97316" }}>Specialist Conflicts</h3>
          <div className="listing" style={{ padding: "0.75rem 0.85rem" }}>
            {conflicts.map((conflict, index) => {
              const sources = formatCitationList(conflict.citations);
              return (
                <div key={`${conflict.topic}-${index}`} style={{ marginBottom: "0.5rem" }}>
                  <strong>{conflict.topic}</strong>
                  <div className="small" style={{ marginTop: "0.25rem" }}>
                    {conflict.issue}
                  </div>
                  <div className="small" style={{ marginTop: "0.25rem", opacity: 0.7 }}>
                    Sources: {sources}
                  </div>
                </div>
              );
            })}
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
