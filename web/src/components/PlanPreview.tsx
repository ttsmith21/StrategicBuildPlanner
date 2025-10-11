import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AsanaTaskSummary,
  EngineeringInstructions,
  PlanConflict,
  PlanJson,
  QAGradeResponseData,
  SuggestedTask,
  ContextPack,
  SessionSnapshotRecord,
} from "../types";

type PreviewTab = "markdown" | "json" | "engineering";

interface PlanPreviewProps {
  planJson: PlanJson | null;
  planMarkdown: string;
  qaResult: QAGradeResponseData | null;
  asanaTasks: AsanaTaskSummary[];
  publishUrl?: string | null;
  conflicts: PlanConflict[];
  qaBlocked: boolean;
  suggestedTasks?: { name: string; owner_hint?: string; fingerprint?: string }[];
  onCreateTasks?: (tasks: SuggestedTask[]) => void;
  creatingTasks?: boolean;
  contextPack?: ContextPack | null;
  sessionId?: string | null;
  sessionSnapshots?: SessionSnapshotRecord[];
  onRestoreSnapshot?: (plan: PlanJson, markdown?: string, contextPack?: ContextPack | null) => void;
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
  suggestedTasks = [],
  onCreateTasks,
  creatingTasks = false,
  contextPack,
  sessionId,
  sessionSnapshots,
  onRestoreSnapshot,
}: PlanPreviewProps) {
  const [activeTab, setActiveTab] = useState<PreviewTab>("markdown");
  const [selectedTaskKeys, setSelectedTaskKeys] = useState<Set<string>>(new Set());

  const engineeringInstructions = planJson?.engineering_instructions as EngineeringInstructions | undefined;

  // Engineering quick counts for tab badge
  const { exceptionalCount, qualityRoutingCount, dfmCount } = useMemo(() => {
    const ei: any = engineeringInstructions || {};
    const exceptional = Array.isArray(ei.exceptional_steps) ? ei.exceptional_steps : [];
    const dfm = Array.isArray(ei.dfm_actions) ? ei.dfm_actions : [];
    const qualityRouting = Array.isArray(ei.quality_routing) ? ei.quality_routing : [];
    return {
      exceptionalCount: exceptional.length,
      qualityRoutingCount: qualityRouting.length,
      dfmCount: dfm.length,
    };
  }, [engineeringInstructions]);

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
    const exceptional = (engineeringInstructions as any).exceptional_steps ?? [];
    const dfm = (engineeringInstructions as any).dfm_actions ?? [];
    const qualityRouting = (engineeringInstructions as any).quality_routing ?? [];

    if (exceptional.length > 0) {
      lines.push("### Exceptional Steps (Non‑standard)");
      lines.push("| Step | Workcenter | Input | Program | Notes | QC | Sources |");
      lines.push("| --- | --- | --- | --- | --- | --- | --- |");
      exceptional.forEach((step: any) => {
        const notes = step.notes?.length ? step.notes.join("<br />") : "—";
        const qc = step.qc?.length ? step.qc.join("<br />") : "—";
        const sources = step.sources?.length
          ? step.sources.map((s: any) => s.source_id).join(", ")
          : "—";
        lines.push(
          `| ${step.op_no} | ${step.workcenter} | ${step.input ?? "—"} | ${step.program ?? "—"} | ${notes} | ${qc} | ${sources} |`
        );
      });
      lines.push("");
    }

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

    if (qualityRouting.length > 0) {
      lines.push("### Quality Operation Placements");
      qualityRouting.forEach((q: any) => {
        const notes = q.notes?.length ? ` — ${q.notes.join("; ")}` : "";
        const sources = q.sources?.length ? ` _(Sources: ${q.sources.map((s: any) => s.source_id).join(", ")})_` : "";
        lines.push(`1. ${q.workcenter}: ${q.quality_operation}${notes}${sources}`);
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

    if (dfm.length > 0) {
      lines.push("### DFM Actions to Carry Through in Design");
      dfm.forEach((a: any) => {
        const tgt = a.target ? ` — Target: ${a.target}` : "";
        const why = a.rationale ? ` — Rationale: ${a.rationale}` : "";
        const sources = a.sources?.length ? ` _(Sources: ${a.sources.map((s: any) => s.source_id).join(", ")})_` : "";
        lines.push(`- ${a.action}${tgt}${why}${sources}`);
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
    if (activeTab === "engineering" && !hasEngineering) {
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

  let previewContent: JSX.Element | null;

  if (!planJson) {
    previewContent = <p className="small">Run specialist agents to see content here.</p>;
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
      
      default:
        previewContent = <ReactMarkdown remarkPlugins={[remarkGfm]}>{planMarkdown}</ReactMarkdown>;
    }
  }

  const qaScoreText = qaResult?.score !== undefined ? qaResult.score.toFixed(1) : "—";
  const qaReasons = qaResult?.reasons ?? [];
  const qaFixes = qaResult?.fixes ?? [];

  // --- Sources & citations helpers ---
  const sources = contextPack?.sources ?? [];
  const sourceCount = sources.length;
  const sourceIdToTitle = useMemo(() => {
    const map: Record<string, string> = {};
    sources.forEach((s) => (map[s.id] = s.title));
    return map;
  }, [sources]);
  const sourceIdToUrl = useMemo(() => {
    const map: Record<string, string> = {};
    (sources as any[]).forEach((s: any) => {
      if (s && typeof s === "object" && typeof s.url === "string") {
        map[s.id] = s.url;
      } else if (s && typeof s === "object" && typeof s.uri === "string") {
        map[s.id] = s.uri;
      }
    });
    return map;
  }, [sources]);

  const citationsSummary = useMemo(() => {
    const counts: Record<string, number> = { total: 0 };
    const inc = (key: string, n = 1) => {
      counts[key] = (counts[key] || 0) + n;
      counts.total += n;
    };
    const scan = (obj: any, path: string[] = []) => {
      if (!obj) return;
      if (Array.isArray(obj)) {
        obj.forEach((item, idx) => scan(item, path.concat(String(idx))));
        return;
      }
      if (typeof obj !== "object") return;
      // Count citations/sources arrays
      if (Array.isArray((obj as any).citations)) {
        inc("citations", (obj as any).citations.length);
      }
      if (Array.isArray((obj as any).sources)) {
        inc("sources", (obj as any).sources.length);
      }
      Object.keys(obj).forEach((k) => scan((obj as any)[k], path.concat(k)));
    };
    scan(planJson);
    return counts;
  }, [planJson]);

  // Suggested tasks selection helpers
  const taskKeyForIndex = useCallback(
    (idx: number) => {
      const t = suggestedTasks[idx] as any;
      return (t?.fingerprint as string) || `${t?.name || "task"}-${idx}`;
    },
    [suggestedTasks]
  );

  const toggleTaskSelected = useCallback(
    (idx: number) => {
      setSelectedTaskKeys((prev) => {
        const next = new Set(prev);
        const key = taskKeyForIndex(idx);
        if (next.has(key)) {
          next.delete(key);
        } else {
          next.add(key);
        }
        return next;
      });
    },
    [taskKeyForIndex]
  );

  const selectAllTasks = useCallback(() => {
    const next = new Set<string>();
    suggestedTasks.forEach((_, idx) => next.add(taskKeyForIndex(idx)));
    setSelectedTaskKeys(next);
  }, [suggestedTasks, taskKeyForIndex]);

  const clearSelectedTasks = useCallback(() => setSelectedTaskKeys(new Set()), []);

  const sendSelectedToAsana = useCallback(() => {
    if (!selectedTaskKeys.size || !suggestedTasks.length || !onCreateTasks) return;
    const toSend = suggestedTasks
      .map((t, idx) => ({ t, idx }))
      .filter(({ idx }) => selectedTaskKeys.has(taskKeyForIndex(idx)))
      .map(({ t }) => t as unknown as SuggestedTask);
    if (toSend.length) {
      onCreateTasks(toSend);
    }
  }, [selectedTaskKeys, suggestedTasks, taskKeyForIndex, onCreateTasks]);

  return (
    <div className="panel">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
        <h2 style={{ margin: 0 }}>Plan Preview</h2>
        {/* New sources badge, if coordinator attached hints */}
        {(() => {
          const changed = ((contextPack as any)?.project?.hints?.changed_sources || []) as string[];
          if (Array.isArray(changed) && changed.length > 0) {
            return (
              <span
                className="badge"
                title={changed.join("\n")}
                style={{ background: "#1e40af", color: "#dbeafe" }}
              >
                {changed.length} new source{changed.length > 1 ? "s" : ""}
              </span>
            );
          }
          return null;
        })()}
      </div>

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
          {hasEngineering && (exceptionalCount || dfmCount || qualityRoutingCount) ? (
            <span className="badge small" style={{ marginLeft: "0.5rem" }}>
              {exceptionalCount} / {dfmCount} / {qualityRoutingCount}
            </span>
          ) : null}
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

      {/* Snapshot diff + restore controls */}
      {sessionId && (sessionSnapshots?.length ?? 0) > 0 && (
        <section>
          <h3 style={{ marginTop: 0 }}>Snapshots</h3>
          {(() => {
            const snaps = sessionSnapshots || [];
            const last = snaps[snaps.length - 1];
            const prev = snaps.length > 1 ? snaps[snaps.length - 2] : undefined;
            const safeArr = (v: any) => (Array.isArray(v) ? v : []);
            const arrSet = (v: any[]) => new Set(v.map((x) => (typeof x === "string" ? x : JSON.stringify(x))));
            const a = (prev?.plan_json as any) || {};
            const b = (last?.plan_json as any) || {};
            const keysA: string[] = safeArr(a?.summary?.keys); const keysB: string[] = safeArr(b?.summary?.keys);
            const ctqA: string[] = safeArr(a?.quality_plan?.ctqs); const ctqB: string[] = safeArr(b?.quality_plan?.ctqs);
            const llA: any[] = safeArr(a?.purchasing?.long_lead_items); const llB: any[] = safeArr(b?.purchasing?.long_lead_items);
            const added = {
              keys: keysB.filter((k) => !arrSet(keysA).has(k)),
              ctqs: ctqB.filter((k) => !arrSet(ctqA).has(k)),
              long_leads: llB.filter((x) => !arrSet(llA).has(typeof x === "string" ? x : JSON.stringify(x))),
            };
            const removed = {
              keys: keysA.filter((k) => !arrSet(keysB).has(k)),
              ctqs: ctqA.filter((k) => !arrSet(ctqB).has(k)),
              long_leads: llA.filter((x) => !arrSet(llB).has(typeof x === "string" ? x : JSON.stringify(x))),
            };
            return (
              <div className="listing" style={{ padding: "0.5rem 0.75rem" }}>
                <div className="small" style={{ opacity: 0.8, marginBottom: "0.5rem" }}>
                  Latest: {new Date((last?.ts || 0) * 1000).toLocaleString()} {last?.note ? `· ${last?.note}` : ""}
                  {prev && (
                    <>
                      <br />
                      vs Previous: {new Date((prev.ts || 0) * 1000).toLocaleString()} {prev.note ? `· ${prev.note}` : ""}
                    </>
                  )}
                </div>
                <div className="badge">+ Keys: {added.keys.length}  − {removed.keys.length}</div>
                <div className="badge">+ CTQs: {added.ctqs.length}  − {removed.ctqs.length}</div>
                <div className="badge">+ Long-leads: {added.long_leads.length}  − {removed.long_leads.length}</div>
                <div style={{ marginTop: "0.5rem" }}>
                  <button
                    type="button"
                    className="secondary"
                    onClick={async () => {
                      if (!onRestoreSnapshot || !last) return;
                      onRestoreSnapshot((last.plan_json as any) || {}, undefined, (last.context_pack as any) || null);
                    }}
                  >
                    Restore latest snapshot
                  </button>
                </div>
              </div>
            );
          })()}
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

      {suggestedTasks.length > 0 && (
        <section>
          <h3 style={{ marginTop: 0, color: "#22c55e" }}>Suggested Tasks</h3>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <button type="button" className="secondary" onClick={selectAllTasks}>
              Select all
            </button>
            <button type="button" className="secondary" onClick={clearSelectedTasks}>
              Clear
            </button>
            <button
              type="button"
              className="primary"
              disabled={!onCreateTasks || creatingTasks || selectedTaskKeys.size === 0}
              onClick={sendSelectedToAsana}
            >
              {creatingTasks ? "Sending…" : `Send selected to Asana (${selectedTaskKeys.size})`}
            </button>
          </div>
          <div className="listing">
            {suggestedTasks.map((task, idx) => {
              const key = taskKeyForIndex(idx);
              const checked = selectedTaskKeys.has(key);
              return (
                <label key={task.fingerprint ?? `${task.name}-${idx}`} className="badge" style={{ cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleTaskSelected(idx)}
                    style={{ marginRight: "0.5rem" }}
                  />
                  ➕ {task.name} {task.owner_hint ? `— ${task.owner_hint}` : ""}
                </label>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <h3 style={{ marginTop: 0 }}>Sources & Citations</h3>
        {sourceCount > 0 ? (
          <div className="listing" style={{ padding: "0.5rem 0.75rem" }}>
            <div className="small" style={{ opacity: 0.8, marginBottom: "0.5rem" }}>
              Ingested sources: {sourceCount}
            </div>
            {sources.map((s) => {
              const url = (sourceIdToUrl as any)[s.id];
              return (
                <div key={s.id} className="badge" title={s.title}>
                  {url ? (
                    <a href={url} target="_blank" rel="noreferrer">{s.id}</a>
                  ) : (
                    <>{s.id}</>
                  )}
                  {" "}— {s.title} ({s.kind}; {s.authority})
                </div>
              );
            })}
            <div className="small" style={{ opacity: 0.8, marginTop: "0.75rem" }}>
              Citations found in plan: {citationsSummary.total} {citationsSummary.total > 0 && `— (sources: ${citationsSummary.sources || 0}, citations: ${citationsSummary.citations || 0})`}
            </div>
          </div>
        ) : (
          <div className="listing" style={{ padding: "0.5rem 0.75rem" }}>
            {(planJson?.source_files_used?.length ?? 0) > 0 ? (
              <>
                <div className="small" style={{ opacity: 0.8, marginBottom: "0.5rem" }}>
                  Sources used (filenames):
                </div>
                {planJson!.source_files_used!.map((name, idx) => (
                  <div key={`${name}-${idx}`} className="badge">📄 {name}</div>
                ))}
              </>
            ) : (
              <div className="small" style={{ opacity: 0.8 }}>No sources listed.</div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
