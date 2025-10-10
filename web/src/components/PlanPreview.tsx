import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AsanaTaskSummary, PlanJson, QAGradeResponseData } from "../types";

interface PlanPreviewProps {
  planJson: PlanJson | null;
  planMarkdown: string;
  qaResult: QAGradeResponseData | null;
  asanaTasks: AsanaTaskSummary[];
}

export function PlanPreview({ planJson, planMarkdown, qaResult, asanaTasks }: PlanPreviewProps) {
  const [activeTab, setActiveTab] = useState<"markdown" | "json">("markdown");

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
      </div>

      <div className="plan-preview">
        {planJson ? (
          activeTab === "markdown" ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{planMarkdown}</ReactMarkdown>
          ) : (
            <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(planJson, null, 2)}</pre>
          )
        ) : (
          <p className="small">Draft a plan to see content here.</p>
        )}
      </div>

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
